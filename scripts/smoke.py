#!/usr/bin/env python3
"""Offline smoke checks for Odoo Agent Runtime."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from daemon import OdooAgentRuntime, get_device_info, get_hostname


class RecordingRuntime(OdooAgentRuntime):
    def __init__(self):
        super().__init__('http://odoo.example.test', 'test-key', 'smoke')
        self.calls = []
        self.fail_new_routes = False

    def _request(self, method, path, **kwargs):
        self.calls.append((method, path, kwargs))
        if self.fail_new_routes and '/api/agent/execution/' in path:
            return None
        return {'status': 'ok'}


def main():
    assert get_hostname()
    assert get_device_info()

    runtime = OdooAgentRuntime('http://odoo.example.test', 'test-key', 'smoke')
    instruction = runtime._build_instruction(
        'Smoke task',
        'Primary prompt text.',
        {
            'instructions': 'Use the runtime contract.',
            'skills': ['example-skill'],
            'mcp_servers': {'example': {'enabled': True}},
        },
        conversation=[
            {'author_type': 'user', 'content': 'Can you check this?'},
            {'author_type': 'agent', 'content': 'I am checking it.'},
        ],
    )
    assert 'Smoke task' in instruction
    assert 'Prompt:\nPrimary prompt text.' in instruction
    assert 'Conversation:' in instruction
    assert 'user: Can you check this?' in instruction
    assert 'example-skill' in instruction

    cmd = runtime._resolve_command(
        {
            'name': 'Example',
            'engine': 'custom',
            'cli_command': 'python -c "print(1)"',
            'timeout_seconds': 5,
        },
        'hello',
        'Smoke task',
        1,
    )
    assert cmd[:3] == ['python', '-c', 'print(1)']
    assert cmd[-1] == 'hello'

    complex_instruction = 'line one with spaces\nline two with "quotes" and \'single quotes\''
    cmd = runtime._resolve_command(
        {
            'name': 'Example',
            'engine': 'custom',
            'cli_command': 'agent-cli run --instruction {instruction} --name "{task_name}"',
        },
        complex_instruction,
        'Task with spaces',
        42,
    )
    assert cmd == [
        'agent-cli',
        'run',
        '--instruction',
        complex_instruction,
        '--name',
        'Task with spaces',
    ]

    cmd = runtime._resolve_command(
        {
            'name': 'Windows Example',
            'engine': 'custom',
            'cli_command': '"C:\\Program Files\\Agent\\agent.exe" run "{instruction}"',
        },
        complex_instruction,
        'Smoke task',
        43,
    )
    assert cmd[0] == 'C:\\Program Files\\Agent\\agent.exe'
    assert cmd[-1] == complex_instruction

    task = {
        'id': 44,
        'name': 'Prompt task',
        'prompt': 'Use this prompt.',
        'description': 'Do not use this description.',
    }
    task_instruction = runtime._build_instruction(
        task['name'],
        task.get('prompt') or task.get('description') or '',
        {},
    )
    assert 'Use this prompt.' in task_instruction
    assert 'Do not use this description.' not in task_instruction

    chat_instruction = runtime._build_instruction(
        '[NF-102] Implement synchronizer — message to OpenCode N100',
        'Hola',
        {},
        conversation=[
            {'author_type': 'user', 'content': 'Hola'},
        ],
        source='chat',
    )
    assert 'User message:\nHola' in chat_instruction
    assert 'Conversation:' in chat_instruction
    assert 'Task:' not in chat_instruction
    assert '[NF-102]' not in chat_instruction

    recorder = RecordingRuntime()
    assert recorder.start_task(50) is True
    assert recorder.calls[-1][1] == '/api/agent/execution/50/start'
    assert recorder.send_log(50, 'info', 'hello') is True
    assert recorder.calls[-1][1] == '/api/agent/execution/50/log'
    assert recorder.complete_task(50, 'completed', result_text='ok') is True
    assert recorder.calls[-1][1] == '/api/agent/execution/50/complete'
    assert recorder.complete_task(50, 'failed', error='boom') is True
    assert recorder.calls[-1][1] == '/api/agent/execution/50/fail'
    assert recorder.send_message(50, 'intermediate reply') is True
    assert recorder.calls[-1][1] == '/api/agent/execution/50/message'

    recorder.fail_new_routes = True
    assert recorder.start_task(51) is True
    assert recorder.calls[-1][1] == '/api/agent/task/51/start'

    missing = runtime._run_agent_cli(
        {'name': 'Missing', 'cli_command': 'definitely-missing-runtime-cli'},
        'hello',
        'Smoke task',
        None,
    )
    assert missing['success'] is False
    assert 'CLI not found' in missing['error']

    print('Smoke checks passed')


if __name__ == '__main__':
    main()
