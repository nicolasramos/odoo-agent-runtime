#!/usr/bin/env python3
"""
Odoo Agent Runtime Daemon

Connects to an Odoo instance, polls for pending executions assigned to its agents,
and executes them via the agent CLI configured by Odoo.

Usage:
    python daemon.py --odoo-url https://odoo.example.com --api-key <key> --name my-runtime
"""

import argparse
import json
import logging
import os
import platform
import shlex
import shutil
import subprocess
import sys
import time
from datetime import datetime

import requests
from dotenv import load_dotenv

logger = logging.getLogger('odoo-agent-runtime')


DEFAULT_TIMEOUT_SECONDS = 600


def get_hostname():
    """Return a cross-platform hostname."""
    return platform.node() or os.getenv('COMPUTERNAME') or os.getenv('HOSTNAME') or 'unknown-host'


def get_device_info():
    """Return platform-safe device info for heartbeat payloads."""
    parts = [get_hostname(), platform.system() or sys.platform, platform.machine()]
    return ' · '.join(part for part in parts if part)


def _first_present(*values):
    for value in values:
        if value not in (None, ''):
            return value
    return None


class OdooAgentRuntime:
    """Runtime daemon that connects to Odoo and executes agent work."""

    def __init__(self, odoo_url, api_key, name, poll_interval=10, max_concurrent=3):
        self.odoo_url = odoo_url.rstrip('/')
        self.api_key = api_key
        self.name = name
        self.poll_interval = poll_interval
        self.max_concurrent = max_concurrent
        self.active_tasks = {}
        self.session = requests.Session()
        self.session.headers.update({
            'X-API-Key': api_key,
            'Content-Type': 'application/json',
        })

    def _api_url(self, path):
        return f'{self.odoo_url}{path}'

    def _request(self, method, path, **kwargs):
        """Make an API request with error handling."""
        try:
            resp = self.session.request(method, self._api_url(path), timeout=30, **kwargs)
            resp.raise_for_status()
            if not resp.content:
                return {'status': 'ok'}
            return resp.json()
        except requests.exceptions.RequestException as e:
            logger.error(f'API request failed: {e}')
            return None
        except ValueError as e:
            logger.error(f'API response was not JSON: {e}')
            return None

    def _request_prefer_new(self, method, new_path, legacy_path, **kwargs):
        """Call the execution API first, then fall back to legacy task routes."""
        result = self._request(method, new_path, **kwargs)
        if result is not None:
            return result
        logger.debug(f'Falling back to legacy API route: {legacy_path}')
        return self._request(method, legacy_path, **kwargs)

    def _is_ok(self, result):
        return bool(result) and result.get('status', 'ok') == 'ok'

    def send_heartbeat(self):
        """Send heartbeat to Odoo."""
        data = {
            'version': '0.2.1',
            'runtime_name': self.name,
            'device_info': get_device_info(),
        }
        result = self._request('POST', '/api/agent/runtime/heartbeat', json=data)
        if result:
            logger.debug(f'Heartbeat OK: {result.get("runtime_name")}')
        return result

    def poll_tasks(self):
        """Poll for pending executions.

        Newer Odoo versions return an ``executions`` list. Older versions returned
        ``tasks``; keep that fallback only for compatibility.
        """
        result = self._request('GET', '/api/agent/runtime/poll', params={'limit': 10})
        if not result:
            return []
        if isinstance(result.get('executions'), list):
            return result['executions']
        if isinstance(result.get('tasks'), list):
            return result['tasks']
        return []

    def start_task(self, task_id):
        """Mark an execution as in progress."""
        result = self._request_prefer_new(
            'POST',
            f'/api/agent/execution/{task_id}/start',
            f'/api/agent/task/{task_id}/start',
        )
        return self._is_ok(result)

    def complete_task(self, task_id, status='completed', result_text=None, error=None):
        """Report execution completion or failure."""
        data = {}
        if result_text:
            data['result'] = result_text
        if error:
            data['error_message'] = error

        if status == 'failed':
            result = self._request_prefer_new(
                'POST',
                f'/api/agent/execution/{task_id}/fail',
                f'/api/agent/task/{task_id}/complete',
                json={**data, 'status': 'failed'},
            )
        else:
            result = self._request_prefer_new(
                'POST',
                f'/api/agent/execution/{task_id}/complete',
                f'/api/agent/task/{task_id}/complete',
                json={**data, 'status': status},
            )
        return self._is_ok(result)

    def send_log(self, task_id, level, message, command=None, exit_code=None):
        """Send a log entry for an execution."""
        data = {'level': level, 'message': message}
        if command:
            data['command'] = command
        if exit_code is not None:
            data['exit_code'] = exit_code
        result = self._request_prefer_new(
            'POST',
            f'/api/agent/execution/{task_id}/log',
            f'/api/agent/task/{task_id}/log',
            json=data,
        )
        return self._is_ok(result)

    def send_message(self, task_id, message):
        """Send an intermediate agent chat message for an execution."""
        result = self._request(
            'POST',
            f'/api/agent/execution/{task_id}/message',
            json={'message': message},
        )
        return self._is_ok(result)

    def execute_task(self, task):
        """Execute a task using the configured agent CLI."""
        task_id = task['id']
        task_name = task.get('name') or task.get('task_name') or f'Execution {task_id}'
        task_source = task.get('source') or 'task'
        task_prompt = _first_present(task.get('prompt'), task.get('description'), task.get('task_description'), '')
        agent_config = self._extract_agent_config(task)
        agent_name = agent_config.get('name') or task.get('agent_name') or 'unknown'
        conversation = task.get('conversation') if isinstance(task.get('conversation'), list) else []

        logger.info(f'Starting task {task_id}: {task_name} (agent: {agent_name})')
        self.send_log(task_id, 'info', f'Starting task: {task_name}', command='init')

        if not self.start_task(task_id):
            logger.error(f'Failed to start task {task_id}')
            self.send_log(task_id, 'error', 'Failed to start task', command='start')
            return

        try:
            instruction = self._build_instruction(
                task_name,
                task_prompt,
                agent_config,
                conversation=conversation,
                source=task_source,
            )
            self.send_log(task_id, 'info', f'Agent: {agent_name}', command='agent')
            self.send_log(task_id, 'info', f'Instruction prepared ({len(instruction)} chars)')

            result = self._run_agent_cli(agent_config, instruction, task_name, task_id)

            if result['success']:
                output = result.get('output') or ''
                self.send_log(task_id, 'info', 'Task completed successfully', exit_code=0)
                self.complete_task(task_id, 'completed', result_text=output)
                logger.info(f'Task {task_id} completed successfully')
            else:
                error = result.get('error') or 'Unknown execution error'
                self.send_log(task_id, 'error', f'Task failed: {error}', exit_code=1)
                self.complete_task(task_id, 'failed', error=error)
                logger.error(f'Task {task_id} failed: {error}')

        except Exception as e:
            logger.exception(f'Task {task_id} crashed')
            self.send_log(task_id, 'error', f'Task crashed: {str(e)}', exit_code=-1)
            self.complete_task(task_id, 'failed', error=str(e))

    def _extract_agent_config(self, task):
        """Return Odoo agent config with legacy task fields as fallback."""
        agent = task.get('agent') if isinstance(task.get('agent'), dict) else {}
        return {
            'name': _first_present(agent.get('name'), task.get('agent_name')),
            'engine': _first_present(agent.get('engine'), task.get('agent_engine')),
            'cli_command': _first_present(agent.get('cli_command'), task.get('cli_command')),
            'timeout_seconds': _first_present(agent.get('timeout_seconds'), task.get('timeout_seconds')),
            'model': _first_present(agent.get('model'), task.get('model')),
            'instructions': _first_present(agent.get('instructions'), task.get('agent_instructions')),
            'skills': _first_present(agent.get('skills'), task.get('skills')),
            'mcp_servers': _first_present(agent.get('mcp_servers'), task.get('mcp_servers')),
        }

    def _build_instruction(self, task_name, task_prompt, agent_config, conversation=None, source='task'):
        """Build the instruction sent to the external CLI."""
        if source == 'chat':
            sections = []
            if task_prompt:
                sections.append(f'User message:\n{task_prompt}')
        else:
            sections = [f'Task:\n{task_name}']
            if task_prompt:
                sections.append(f'Prompt:\n{task_prompt}')
        if conversation:
            sections.append(f'Conversation:\n{self._format_conversation(conversation)}')
        if agent_config.get('instructions'):
            sections.append(f'Agent instructions:\n{agent_config["instructions"]}')
        if agent_config.get('skills'):
            sections.append(f'Skills:\n{self._format_config_value(agent_config["skills"])}')
        if agent_config.get('mcp_servers'):
            sections.append(f'MCP servers:\n{self._format_config_value(agent_config["mcp_servers"])}')
        return '\n\n'.join(sections)

    def _format_config_value(self, value):
        if isinstance(value, str):
            return value
        return json.dumps(value, indent=2, sort_keys=True)

    def _format_conversation(self, conversation):
        lines = []
        for message in conversation[-20:]:
            if not isinstance(message, dict):
                continue
            author = message.get('author_type') or 'unknown'
            content = message.get('content') or ''
            if content:
                lines.append(f'{author}: {content}')
        return '\n'.join(lines)

    def _split_cli_command(self, cli_command):
        """Split a configured CLI command into argv tokens."""
        return shlex.split(cli_command, posix=True)

    def _render_cli_tokens(self, tokens, template_values):
        """Replace placeholders after splitting so long values remain one argv item."""
        rendered = []
        for token in tokens:
            for placeholder, value in template_values.items():
                token = token.replace(placeholder, value)
            rendered.append(token)
        return rendered

    def _resolve_command(self, agent_config, instruction, task_name, task_id):
        """Resolve configured command first, then legacy engine/name fallbacks."""
        cli_command = agent_config.get('cli_command')
        model = agent_config.get('model') or ''
        engine = (agent_config.get('engine') or '').lower()
        agent_name = agent_config.get('name') or 'unknown'

        template_values = {
            '{instruction}': instruction,
            '{task_name}': task_name,
            '{task_id}': str(task_id or ''),
            '{model}': model,
        }

        if cli_command:
            tokens = self._split_cli_command(cli_command)
            cmd = self._render_cli_tokens(tokens, template_values)
            if '{instruction}' not in cli_command and '{task_name}' not in cli_command:
                cmd.append(instruction)
            return cmd

        cli_map = {
            'hermes': ['hermes', 'run', '--task', task_name, '--context', instruction],
            'opencode': ['opencode', 'run', '--instruction', instruction],
            'openclaw': ['openclaw', 'agent', '--task', task_name, '--context', instruction],
        }

        legacy_key = None
        for key in cli_map:
            if key == engine or key in agent_name.lower():
                legacy_key = key
                break

        if not legacy_key:
            return None

        cmd = list(cli_map[legacy_key])
        if model and legacy_key in {'opencode', 'openclaw'}:
            cmd.extend(['--model', model])
        return cmd

    def _run_agent_cli(self, agent_config, instruction, task_name, task_id=None):
        """Run the agent CLI and return success/error state."""
        cmd = self._resolve_command(agent_config, instruction, task_name, task_id)
        agent_name = agent_config.get('name') or 'unknown'
        timeout = int(agent_config.get('timeout_seconds') or DEFAULT_TIMEOUT_SECONDS)

        if not cmd:
            msg = f'No CLI command configured for agent {agent_name}'
            logger.error(msg)
            if task_id:
                self.send_log(task_id, 'error', msg)
            return {'success': False, 'error': msg}

        executable = cmd[0]
        if not shutil.which(executable):
            msg = f'CLI not found: {executable}'
            logger.error(msg)
            if task_id:
                self.send_log(task_id, 'error', msg, command=' '.join(cmd), exit_code=127)
            return {'success': False, 'error': msg}

        try:
            logger.info(f'Running: {" ".join(cmd)}')
            if task_id:
                self.send_log(task_id, 'info', f'Running: {" ".join(cmd)}', command=' '.join(cmd))

            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout,
                check=False,
            )

            stdout_text = process.stdout.rstrip()
            stderr_text = process.stderr.rstrip()

            if stdout_text and task_id:
                for line in stdout_text.splitlines():
                    self.send_log(task_id, 'info', line)
            if stderr_text and task_id:
                for line in stderr_text.splitlines():
                    level = 'warn' if 'warn' in line.lower() else 'error'
                    self.send_log(task_id, level, line)

            if task_id:
                level = 'info' if process.returncode == 0 else 'error'
                self.send_log(task_id, level, f'Exit code: {process.returncode}', exit_code=process.returncode)

            if process.returncode == 0:
                return {'success': True, 'output': stdout_text}
            return {'success': False, 'error': stderr_text or f'Exit code: {process.returncode}'}

        except subprocess.TimeoutExpired:
            return {'success': False, 'error': f'Task timed out after {timeout} seconds'}

    def run(self):
        """Main loop: heartbeat + poll + execute."""
        logger.info(f'Starting Odoo Agent Runtime: {self.name}')
        logger.info(f'Connecting to: {self.odoo_url}')

        if not self.send_heartbeat():
            logger.error('Failed to connect to Odoo. Check URL and API key.')
            return False

        logger.info('Connected to Odoo. Starting poll loop...')

        while True:
            try:
                self.send_heartbeat()
                tasks = self.poll_tasks()
                if tasks:
                    logger.info(f'Found {len(tasks)} pending execution(s)')

                for task in tasks:
                    task_id = task['id']
                    if task_id not in self.active_tasks:
                        self.active_tasks[task_id] = task
                        self.execute_task(task)

                active_ids = {task['id'] for task in self.poll_tasks()}
                self.active_tasks = {
                    tid: t for tid, t in self.active_tasks.items()
                    if t['id'] in active_ids
                }

                time.sleep(self.poll_interval)

            except KeyboardInterrupt:
                logger.info('Shutting down...')
                break
            except Exception as e:
                logger.exception(f'Error in main loop: {e}')
                time.sleep(self.poll_interval * 2)

        return True


def setup_logging(verbose=False):
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description='Odoo Agent Runtime Daemon')
    parser.add_argument('--odoo-url', default=os.getenv('ODOO_URL', 'http://localhost:8069'),
                        help='Odoo instance URL')
    parser.add_argument('--api-key', default=os.getenv('API_KEY', ''),
                        help='Runtime API key')
    parser.add_argument('--name', default=os.getenv('RUNTIME_NAME', get_hostname()),
                        help='Runtime name')
    parser.add_argument('--poll-interval', type=int, default=int(os.getenv('POLL_INTERVAL', '10')),
                        help='Poll interval in seconds')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Verbose logging')
    args = parser.parse_args()

    setup_logging(args.verbose)

    if not args.api_key:
        logger.error('API key is required. Set API_KEY env var or pass --api-key.')
        sys.exit(1)

    runtime = OdooAgentRuntime(
        odoo_url=args.odoo_url,
        api_key=args.api_key,
        name=args.name,
        poll_interval=args.poll_interval,
    )

    success = runtime.run()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
