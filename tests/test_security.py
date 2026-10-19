"""Security regression tests; no real Firebase calls, registry writes or power actions."""
import ast
import base64
import os
from pathlib import Path
import re
import sys
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import security
from test_runtime import extract, load


class SecurityTests(unittest.TestCase):
    def test_password_dpapi_roundtrip_and_tamper(self):
        if os.name != 'nt':
            self.skipTest('DPAPI requires Windows')
        password = '테스트-Password-123!'
        encrypted = security.protect_password(password)
        self.assertTrue(encrypted.startswith('dpapi:'))
        self.assertNotIn(password, encrypted)
        self.assertEqual(security.unprotect_password(encrypted), password)
        damaged = bytearray(base64.b64decode(encrypted[6:]))
        damaged[-1] ^= 1
        with self.assertRaises(OSError):
            security.unprotect_password('dpapi:' + base64.b64encode(damaged).decode())

    def test_legacy_password_can_migrate(self):
        import uuid
        key = str(uuid.getnode()).encode()
        plaintext = 'legacy-비밀번호'
        legacy = base64.b64encode(bytes(c ^ key[i % len(key)] for i, c in enumerate(plaintext.encode()))).decode()
        self.assertEqual(security.unprotect_password(legacy), plaintext)

    def test_auto_logon_uses_lsa_and_removes_registry_password(self):
        registry, store = Mock(), Mock()
        namespace = {'winreg': registry, 'store_logon_secret': store}
        enable = load(extract('set_auto_logon'), namespace)
        self.assertTrue(enable('test-user', 'test-password'))
        store.assert_called_once_with('test-password')
        self.assertFalse(any(call.args[1] == 'DefaultPassword' for call in registry.SetValueEx.call_args_list))
        registry.DeleteValue.assert_called_once_with(registry.OpenKey.return_value, 'DefaultPassword')
        store.side_effect = PermissionError()
        registry.reset_mock()
        self.assertFalse(enable('test-user', 'test-password'))
        registry.SetValueEx.assert_not_called()

    def test_only_public_settings_leave_device(self):
        data = {'db_secret': 'admin-secret', 'encrypted_password': 'password', 'pc_id': 'other',
                'auto_unlock_enabled': True, 'school_info': {'name': 'school', 'api_key': 'key'},
                '월': {'1교시': {'enabled': True}}, 'minutes_before': 5}
        result = security.public_config(data)
        self.assertEqual(set(result), {'school_info', '월', 'minutes_before'})
        self.assertNotIn('api_key', result['school_info'])
        self.assertEqual(data['school_info']['api_key'], 'key')
        self.assertNotIn('pc_id', security.remote_config(data))
        self.assertEqual(security.remote_config(data)['school_info']['api_key'], 'key')

    def test_download_and_socket_url_boundaries(self):
        trusted = 'https://github.com/JunHyuk1203/autoshutdown/releases/download/v1.2.3/auto_shutdown.exe'
        self.assertEqual(security.validate_download_url(trusted), trusted)
        for value in ['http://github.com/JunHyuk1203/autoshutdown/releases/download/v1/a.exe',
                      trusted.replace('github.com', 'github.com.evil.test'),
                      trusted.replace('JunHyuk1203', 'attacker'),
                      trusted.replace('https://', 'https://user@'),
                      'file:///C:/evil.exe', trusted + '#fragment']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                security.validate_download_url(value)
        for value in ['ws://localhost:8765', 'https://example.test', 'wss://user:pass@example.test']:
            with self.assertRaises(ValueError):
                security.validate_ws_url(value)
        self.assertEqual(security.validate_ws_url('wss://host.test'), 'wss://host.test')

    def test_shell_injection_never_reaches_command_interpreter(self):
        with patch.object(security.subprocess, 'run') as run:
            for pid in ['1 & calc', '-1', '0', True, '1 /IM explorer.exe']:
                with self.assertRaises(ValueError):
                    security.kill_remote_process(pid)
            run.assert_not_called()
            security.kill_remote_process('123')
            self.assertEqual(run.call_args.args[0], ['taskkill', '/F', '/PID', '123'])
        with patch.object(security.os, 'startfile', create=True) as start:
            for url in ['file:///C:/evil.exe', 'javascript:alert(1)', 'ftp://host/file', 'https://host/\nrun']:
                with self.assertRaises(ValueError):
                    security.open_remote_url(url)
            security.open_remote_url('https://example.test/?x=1&calc')
            start.assert_called_once_with('https://example.test/?x=1&calc')

    def test_commands_require_recent_numeric_timestamp(self):
        with patch.object(security.time, 'time', return_value=1000):
            self.assertTrue(security.fresh_command(995))
            for timestamp in [0, 900, 1001, None, '995', True, float('nan'), float('inf')]:
                self.assertFalse(security.fresh_command(timestamp))

    def test_websocket_roles_claims_and_approval(self):
        source = ast.parse((Path(__file__).resolve().parents[1] / 'custom_server.py').read_text(encoding='utf-8'))
        node = next(n for n in source.body if isinstance(n, ast.FunctionDef) and n.name == '_check_auth')
        verifier, requests = Mock(), Mock()
        namespace = {'_verify_firebase_token': verifier, 'requests': requests, 're': re,
                     'MASTER_EMAIL': 'master@example.test', 'FIREBASE_DB_URL': 'https://db.test'}
        check = load(node, namespace)
        verifier.return_value = (None, 'invalid token')
        self.assertTrue(check('', 'client')[0])
        verifier.assert_not_called()
        self.assertFalse(check('token', 'admin')[0])
        verifier.return_value = ({'sub': 'user', 'email': 'master@example.test', 'email_verified': False}, None)
        self.assertFalse(check('token', 'admin')[0])
        verifier.return_value = ({'sub': 'teacher', 'email': 'teacher@example.test', 'email_verified': True, 'exp': time.time()+100}, None)
        requests.get.return_value.json.return_value = {'approved': True}
        self.assertTrue(check('token', 'admin')[0])
        self.assertEqual(requests.get.call_args.kwargs['params'], {'auth': 'token'})
        requests.get.return_value.json.return_value = {'approved': False}
        self.assertFalse(check('token', 'admin')[0])

    def test_real_jwt_signature_audience_issuer_and_expiry(self):
        import jwt
        from datetime import datetime, timedelta, timezone
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509.oid import NameOID
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        now = datetime.now(timezone.utc)
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'test')])
        cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
                .serial_number(1).not_valid_before(now-timedelta(minutes=1))
                .not_valid_after(now+timedelta(days=1)).sign(key, hashes.SHA256()))
        source = ast.parse((Path(__file__).resolve().parents[1] / 'custom_server.py').read_text(encoding='utf-8'))
        node = next(n for n in source.body if isinstance(n, ast.FunctionDef) and n.name == '_verify_firebase_token')
        namespace = {'jwt': jwt, '_get_google_public_keys': lambda: {'test': cert.public_bytes(serialization.Encoding.PEM).decode()},
                     'load_pem_x509_certificate': x509.load_pem_x509_certificate,
                     'default_backend': lambda: None}
        verify = load(node, namespace)
        claims = {'sub': 'test', 'iat': now, 'exp': now+timedelta(minutes=5),
                  'aud': 'atss-a1f9e', 'iss': 'https://securetoken.google.com/atss-a1f9e'}
        def signed(data, algorithm='RS256', signing_key=key):
            return jwt.encode(data, signing_key, algorithm=algorithm, headers={'kid': 'test'})
        self.assertIsNotNone(verify(signed(claims))[0])
        for override in [{'exp': now-timedelta(seconds=10)}, {'aud': 'other'}, {'iss': 'other'}]:
            self.assertIsNone(verify(signed(dict(claims, **override)))[0])
        no_exp = {k: v for k, v in claims.items() if k != 'exp'}
        self.assertIsNone(verify(signed(no_exp))[0])
        self.assertIsNone(verify(signed(claims, 'HS256', 'untrusted'))[0])
        wrong_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.assertIsNone(verify(signed(claims, signing_key=wrong_key))[0])


if __name__ == '__main__':
    unittest.main()
