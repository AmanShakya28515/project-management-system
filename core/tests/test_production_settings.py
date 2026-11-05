"""Production environment contract (spec 11 AC-4/5/8). No database needed."""
import json
import os
from pathlib import Path
import subprocess
import sys

from django.test import SimpleTestCase


class ProductionSettingsTests(SimpleTestCase):
    valid = {
        'DJANGO_SECRET_KEY': 'verification-only-0123456789-ABCDEFGHIJKLMNOPQRSTUVWXYZ-abcdef',
        'DJANGO_ALLOWED_HOSTS': 'localhost, 127.0.0.1',
        'DJANGO_DB_HOST': 'db', 'DJANGO_DB_NAME': 'rehearsal',
        'DJANGO_DB_USER': 'rehearsal', 'DJANGO_DB_PASSWORD': 'verification-only-password',
    }

    def load(self, changes=None, module='config.settings_production'):
        env = {k: v for k, v in os.environ.items() if not k.startswith('DJANGO_')}
        env.update(self.valid)
        for key, value in (changes or {}).items():
            if value is None:
                env.pop(key, None)
            else:
                env[key] = value
        code = (
            'import importlib,json; '
            f's=importlib.import_module({module!r}); '
            'print(json.dumps([s.DEBUG,s.ALLOWED_HOSTS,s.DATABASES],default=str))'
        )
        return subprocess.run([sys.executable, '-c', code], env=env,
                              cwd=Path(__file__).resolve().parents[2],
                              capture_output=True, text=True, timeout=15)

    def test_valid_environment(self):
        """AC-4/5: DEBUG off, explicit hosts, PostgreSQL and default port."""
        result = self.load()
        self.assertEqual(result.returncode, 0, result.stderr)
        debug, hosts, databases = json.loads(result.stdout)
        self.assertFalse(debug)
        self.assertEqual(hosts, ['localhost', '127.0.0.1'])
        database = databases['default']
        self.assertEqual(database['ENGINE'], 'django.db.backends.postgresql')
        for field in ('HOST', 'NAME', 'USER', 'PASSWORD'):
            self.assertEqual(database[field], self.valid['DJANGO_DB_' + field])
        self.assertEqual(database['PORT'], '5432')
        self.assertEqual(self.load({'DJANGO_DEBUG': '0', 'DJANGO_DB_PORT': '5433'}).returncode, 0)

    def test_required_values(self):
        """AC-5: each missing/blank required value fails without secret output."""
        for name in self.valid:
            for value in (None, '', '   '):
                with self.subTest(name=name, value=value):
                    result = self.load({name: value})
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(name, result.stderr)
                    self.assertNotIn(self.valid['DJANGO_SECRET_KEY'], result.stderr)
                    self.assertNotIn(self.valid['DJANGO_DB_PASSWORD'], result.stderr)

    def test_unsafe_values(self):
        """AC-4/5: unsafe production configuration is rejected."""
        cases = {
            'DJANGO_DEBUG': ['1', 'true', 'False', ''],
            'DJANGO_SECRET_KEY': ['django-insecure-dev-only-change-me',
                                  'django-insecure-docker-dev-only', 'short', 'a' * 60],
            'DJANGO_ALLOWED_HOSTS': ['*', 'localhost,*', ',', '*.example.com'],
            'DJANGO_DB_PASSWORD': ['pms-dev-only-password'],
            'DJANGO_DB_PORT': ['', 'abc', '0', '65536'],
        }
        for name, values in cases.items():
            for value in values:
                with self.subTest(name=name, value=value):
                    result = self.load({name: value})
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(name, result.stderr)
                    self.assertNotIn(self.valid['DJANGO_SECRET_KEY'], result.stderr)
                    self.assertNotIn(self.valid['DJANGO_DB_PASSWORD'], result.stderr)

    def test_development_defaults_unchanged(self):
        """AC-8: base settings still default to DEBUG on and SQLite."""
        result = self.load({key: None for key in self.valid}, module='config.settings')
        self.assertEqual(result.returncode, 0, result.stderr)
        debug, hosts, databases = json.loads(result.stdout)
        self.assertTrue(debug)
        self.assertEqual(databases['default']['ENGINE'], 'django.db.backends.sqlite3')
