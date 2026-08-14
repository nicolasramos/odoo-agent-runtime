import os
import tempfile
import unittest
from http.cookiejar import Cookie
from unittest.mock import MagicMock, patch

import requests

import daemon
from daemon import OdooAgentRuntime


class DatabaseBootstrapTests(unittest.TestCase):
    def make_runtime(self, database=None):
        runtime = OdooAgentRuntime(
            odoo_url='https://odoo.example.com',
            api_key='runtime-secret',
            name='test-runtime',
            database=database,
        )
        runtime.session = MagicMock()
        runtime.bootstrap_session = MagicMock()
        runtime.bootstrap_session.headers = {}
        return runtime

    def bootstrap_response(self, url='https://odoo.example.com/web/login?db=acme', history=()):
        response = MagicMock(url=url, history=list(history))
        response.cookies = {}
        response.raise_for_status.return_value = None
        return response

    def configure_bootstrap_cookie(
        self,
        runtime,
        value='odoo-session',
        domain='odoo.example.com',
        path='/',
        secure=True,
    ):
        if value is None:
            runtime.bootstrap_session.cookies = []
            return
        runtime.bootstrap_session.cookies = [
            Cookie(
                version=0,
                name='session_id',
                value=value,
                port=None,
                port_specified=False,
                domain=domain,
                domain_specified=True,
                domain_initial_dot=domain.startswith('.'),
                path=path,
                path_specified=True,
                secure=secure,
                expires=None,
                discard=True,
                comment=None,
                comment_url=None,
                rest={},
                rfc2109=False,
            )
        ]

    def test_bootstraps_url_encoded_database_session_before_heartbeat(self):
        runtime = self.make_runtime(database='acme & partners')
        runtime.bootstrap_session.get.return_value = self.bootstrap_response(
            'https://odoo.example.com/web/login?db=acme+%26+partners'
        )
        self.configure_bootstrap_cookie(runtime)
        api_response = MagicMock(
            content=b'{"status": "ok"}',
            json=lambda: {'status': 'ok'},
        )
        runtime.session.request.side_effect = lambda *args, **kwargs: self._api_request_after_bootstrap(
            runtime,
            api_response,
        )

        runtime.send_heartbeat()

        runtime.bootstrap_session.get.assert_called_once_with(
            'https://odoo.example.com/web/login?db=acme+%26+partners',
            allow_redirects=True,
            timeout=30,
        )
        runtime.session.request.assert_called_once()

    def _api_request_after_bootstrap(self, runtime, response):
        self.assertTrue(runtime.bootstrap_session.get.called)
        return response

    def test_bootstrap_never_sends_api_key_even_when_redirected(self):
        runtime = self.make_runtime(database='acme')
        runtime.bootstrap_session.get.return_value = self.bootstrap_response(
            'https://odoo.example.com/web/login',
            history=[MagicMock(url='https://odoo.example.com/web/login?db=acme')],
        )
        self.configure_bootstrap_cookie(runtime)
        runtime.session.request.return_value = MagicMock(
            content=b'{"status": "ok"}',
            json=lambda: {'status': 'ok'},
        )

        runtime.send_heartbeat()

        self.assertNotIn('X-API-Key', runtime.bootstrap_session.headers)
        runtime.bootstrap_session.get.assert_called_once_with(
            'https://odoo.example.com/web/login?db=acme',
            allow_redirects=True,
            timeout=30,
        )
        runtime.session.request.assert_called_once()

    def test_database_bootstrap_failure_prevents_runtime_api_request(self):
        runtime = self.make_runtime(database='acme')
        runtime.bootstrap_session.get.side_effect = requests.exceptions.ConnectionError('unreachable')

        with self.assertLogs('odoo-agent-runtime', level='ERROR') as logs:
            result = runtime.send_heartbeat()

        self.assertIsNone(result)
        runtime.session.request.assert_not_called()
        self.assertIn('Database bootstrap failed for ODOO_DATABASE', '\n'.join(logs.output))

    def test_selector_redirect_fails_bootstrap_before_runtime_api_request(self):
        runtime = self.make_runtime(database='acme')
        runtime.bootstrap_session.get.return_value = self.bootstrap_response(
            url='https://odoo.example.com/web/database/selector',
        )

        with self.assertLogs('odoo-agent-runtime', level='ERROR') as logs:
            result = runtime.send_heartbeat()

        self.assertIsNone(result)
        runtime.session.request.assert_not_called()
        self.assertIn('web/database/selector', '\n'.join(logs.output))

    def test_selector_in_redirect_history_fails_bootstrap_before_runtime_api_request(self):
        runtime = self.make_runtime(database='acme')
        runtime.bootstrap_session.get.return_value = self.bootstrap_response(
            'https://odoo.example.com/web/login',
            history=[MagicMock(url='https://odoo.example.com/web/database/selector')],
        )
        self.configure_bootstrap_cookie(runtime)

        with self.assertLogs('odoo-agent-runtime', level='ERROR') as logs:
            result = runtime.send_heartbeat()

        self.assertIsNone(result)
        runtime.session.request.assert_not_called()
        self.assertIn('web/database/selector', '\n'.join(logs.output))

    def test_cross_origin_redirect_fails_before_runtime_api_request(self):
        runtime = self.make_runtime(database='acme')
        runtime.bootstrap_session.get.return_value = self.bootstrap_response(
            'https://odoo.example.com/web/login',
            history=[MagicMock(url='https://evil.example/redirect')],
        )
        self.configure_bootstrap_cookie(runtime)

        with self.assertLogs('odoo-agent-runtime', level='ERROR') as logs:
            result = runtime.send_heartbeat()

        self.assertIsNone(result)
        runtime.session.request.assert_not_called()
        self.assertIn('cross-origin', '\n'.join(logs.output))
        self.assertIn('Runtime API calls were not attempted', '\n'.join(logs.output))

    def test_cross_origin_final_url_fails_before_runtime_api_request(self):
        runtime = self.make_runtime(database='acme')
        runtime.bootstrap_session.get.return_value = self.bootstrap_response(
            'https://evil.example/web/login',
        )
        self.configure_bootstrap_cookie(runtime)

        with self.assertLogs('odoo-agent-runtime', level='ERROR') as logs:
            result = runtime.send_heartbeat()

        self.assertIsNone(result)
        runtime.session.request.assert_not_called()
        self.assertIn('cross-origin', '\n'.join(logs.output))

    def test_cookie_less_bootstrap_fails_before_runtime_api_request(self):
        runtime = self.make_runtime(database='acme')
        runtime.bootstrap_session.get.return_value = self.bootstrap_response()
        self.configure_bootstrap_cookie(runtime, value=None)

        with self.assertLogs('odoo-agent-runtime', level='ERROR') as logs:
            result = runtime.send_heartbeat()

        self.assertIsNone(result)
        runtime.session.request.assert_not_called()
        self.assertIn('session cookie', '\n'.join(logs.output))
        self.assertIn('Runtime API calls were not attempted', '\n'.join(logs.output))

    def test_session_cookie_for_another_host_fails_before_runtime_api_request(self):
        runtime = self.make_runtime(database='acme')
        runtime.bootstrap_session.get.return_value = self.bootstrap_response()
        self.configure_bootstrap_cookie(runtime, domain='evil.example')

        with self.assertLogs('odoo-agent-runtime', level='ERROR') as logs:
            result = runtime.send_heartbeat()

        self.assertIsNone(result)
        runtime.session.request.assert_not_called()
        self.assertIn('does not apply to the runtime API URL', '\n'.join(logs.output))

    def test_session_cookie_for_another_path_fails_before_runtime_api_request(self):
        runtime = self.make_runtime(database='acme')
        runtime.bootstrap_session.get.return_value = self.bootstrap_response()
        self.configure_bootstrap_cookie(runtime, path='/web')

        with self.assertLogs('odoo-agent-runtime', level='ERROR') as logs:
            result = runtime.send_heartbeat()

        self.assertIsNone(result)
        runtime.session.request.assert_not_called()
        self.assertIn('does not apply to the runtime API URL', '\n'.join(logs.output))

    def test_secure_session_cookie_fails_for_http_api_url(self):
        runtime = self.make_runtime(database='acme')
        runtime.odoo_url = 'http://odoo.example.com'
        runtime.bootstrap_session.get.return_value = self.bootstrap_response(
            'http://odoo.example.com/web/login?db=acme'
        )
        self.configure_bootstrap_cookie(runtime, secure=True)

        with self.assertLogs('odoo-agent-runtime', level='ERROR') as logs:
            result = runtime.send_heartbeat()

        self.assertIsNone(result)
        runtime.session.request.assert_not_called()
        self.assertIn('does not apply to the runtime API URL', '\n'.join(logs.output))

    def test_transient_bootstrap_failure_can_be_retried(self):
        runtime = self.make_runtime(database='acme')
        runtime.bootstrap_session.get.side_effect = [
            requests.exceptions.ConnectionError('unreachable'),
            self.bootstrap_response(),
        ]
        self.configure_bootstrap_cookie(runtime)
        runtime.session.request.return_value = MagicMock(
            content=b'{"status": "ok"}',
            json=lambda: {'status': 'ok'},
        )

        self.assertIsNone(runtime.send_heartbeat())
        self.assertFalse(runtime._database_bootstrap_failed)
        self.assertEqual({'status': 'ok'}, runtime.send_heartbeat())
        self.assertEqual(2, runtime.bootstrap_session.get.call_count)
        runtime.session.request.assert_called_once()

    def test_transient_bootstrap_http_status_failure_can_be_retried(self):
        runtime = self.make_runtime(database='acme')
        failed_response = self.bootstrap_response()
        failed_response.raise_for_status.side_effect = requests.exceptions.HTTPError('503 unavailable')
        runtime.bootstrap_session.get.side_effect = [failed_response, self.bootstrap_response()]
        self.configure_bootstrap_cookie(runtime)
        runtime.session.request.return_value = MagicMock(
            content=b'{"status": "ok"}',
            json=lambda: {'status': 'ok'},
        )

        self.assertIsNone(runtime.send_heartbeat())
        self.assertFalse(runtime._database_bootstrap_failed)
        self.assertEqual({'status': 'ok'}, runtime.send_heartbeat())
        self.assertEqual(2, runtime.bootstrap_session.get.call_count)

    def test_single_database_mode_skips_bootstrap(self):
        runtime = self.make_runtime()
        runtime.session.request.return_value = MagicMock(
            content=b'{"status": "ok"}',
            json=lambda: {'status': 'ok'},
        )

        runtime.send_heartbeat()

        runtime.bootstrap_session.get.assert_not_called()
        runtime.session.request.assert_called_once()

    def test_whitespace_only_database_skips_bootstrap(self):
        runtime = self.make_runtime(database='  \t ')
        runtime.session.request.return_value = MagicMock(
            content=b'{"status": "ok"}',
            json=lambda: {'status': 'ok'},
        )

        runtime.send_heartbeat()

        runtime.bootstrap_session.get.assert_not_called()
        runtime.session.request.assert_called_once()


class DotenvTests(unittest.TestCase):
    def test_runtime_dotenv_keeps_dollar_expressions_literal(self):
        old_value = os.environ.pop('RUNTIME_SECRET', None)
        with tempfile.NamedTemporaryFile('w', delete=False) as dotenv_file:
            dotenv_file.write('RUNTIME_SECRET=abc${HOME}\n')
            dotenv_path = dotenv_file.name

        try:
            daemon.load_runtime_dotenv(dotenv_path)
            self.assertEqual('abc${HOME}', os.environ['RUNTIME_SECRET'])
        finally:
            os.unlink(dotenv_path)
            if old_value is None:
                os.environ.pop('RUNTIME_SECRET', None)
            else:
                os.environ['RUNTIME_SECRET'] = old_value


class SplitCliCommandTests(unittest.TestCase):
    """Tests for _split_cli_command platform-specific behavior."""

    def test_split_posix_true_handles_spaces_in_path(self):
        """posix=True: quoted paths with spaces stay as single token."""
        runtime = daemon.OdooAgentRuntime(
            odoo_url='https://odoo.example.com',
            api_key='test-key',
            name='test-runtime',
        )
        # With posix=True, a quoted path with spaces is one token
        result = runtime._split_cli_command('/path/to/my script.py arg1')
        self.assertEqual(result, ['/path/to/my', 'script.py', 'arg1'])

    @patch('daemon.platform.system', return_value='Windows')
    def test_split_posix_false_handles_spaces_in_path(self, mock_platform):
        """posix=False: unquoted spaces split tokens (no shell quoting)."""
        runtime = daemon.OdooAgentRuntime(
            odoo_url='https://odoo.example.com',
            api_key='test-key',
            name='test-runtime',
        )
        # With posix=False, unquoted spaces split the path — no shell quoting support
        result = runtime._split_cli_command('/path/to/my script.py arg1')
        self.assertEqual(result, ['/path/to/my', 'script.py', 'arg1'])

    @patch('daemon.platform.system', return_value='Windows')
    def test_split_posix_false_treats_quotes_as_literal(self, mock_platform):
        """posix=False: double quotes are literal characters, not shell metacharacters."""
        runtime = daemon.OdooAgentRuntime(
            odoo_url='https://odoo.example.com',
            api_key='test-key',
            name='test-runtime',
        )
        # With posix=False, double quotes are NOT interpreted as quoting
        result = runtime._split_cli_command('python script.py "hello world"')
        self.assertEqual(result, ['python', 'script.py', '"hello world"'])

    def test_split_posix_true_handles_quoted_args(self):
        """posix=True: quoted arguments with spaces stay as single token."""
        runtime = daemon.OdooAgentRuntime(
            odoo_url='https://odoo.example.com',
            api_key='test-key',
            name='test-runtime',
        )
        result = runtime._split_cli_command("python script.py 'hello world'")
        self.assertEqual(result, ['python', 'script.py', 'hello world'])

    def test_split_posix_false_handles_quoted_args(self):
        """posix=False: quoted arguments with spaces stay as single token."""
        runtime = daemon.OdooAgentRuntime(
            odoo_url='https://odoo.example.com',
            api_key='test-key',
            name='test-runtime',
        )
        result = runtime._split_cli_command("python script.py 'hello world'")
        self.assertEqual(result, ['python', 'script.py', 'hello world'])

    def test_split_posix_true_handles_escaped_quotes(self):
        """posix=True: escaped quotes inside quoted strings."""
        runtime = daemon.OdooAgentRuntime(
            odoo_url='https://odoo.example.com',
            api_key='test-key',
            name='test-runtime',
        )
        result = runtime._split_cli_command("python script.py \"say \\\"hi\\\"\"")
        self.assertEqual(result, ['python', 'script.py', 'say "hi"'])

    def test_split_posix_false_handles_escaped_quotes(self):
        """posix=False: escaped quotes inside quoted strings."""
        runtime = daemon.OdooAgentRuntime(
            odoo_url='https://odoo.example.com',
            api_key='test-key',
            name='test-runtime',
        )
        result = runtime._split_cli_command("python script.py \"say \\\"hi\\\"\"")
        self.assertEqual(result, ['python', 'script.py', 'say "hi"'])

    def test_split_handles_empty_string(self):
        """Empty command returns empty list."""
        runtime = daemon.OdooAgentRuntime(
            odoo_url='https://odoo.example.com',
            api_key='test-key',
            name='test-runtime',
        )
        result = runtime._split_cli_command('')
        self.assertEqual(result, [])

    def test_split_handles_simple_command(self):
        """Simple unquoted command splits correctly."""
        runtime = daemon.OdooAgentRuntime(
            odoo_url='https://odoo.example.com',
            api_key='test-key',
            name='test-runtime',
        )
        result = runtime._split_cli_command('python script.py arg1 arg2')
        self.assertEqual(result, ['python', 'script.py', 'arg1', 'arg2'])


if __name__ == '__main__':
    unittest.main()
