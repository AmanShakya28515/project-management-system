"""Explicit production runtime; local development uses config.settings."""
from django.core.exceptions import ImproperlyConfigured

from .settings import *


def required(name):
    value = os.environ.get(name, '')
    if not value.strip():
        raise ImproperlyConfigured(f'{name} must be supplied and nonblank.')
    return value


if os.environ.get('DJANGO_DEBUG', '0') != '0':
    raise ImproperlyConfigured('DJANGO_DEBUG must be 0 in production.')
DEBUG = False

SECRET_KEY = required('DJANGO_SECRET_KEY')
if (SECRET_KEY.startswith('django-insecure-') or len(SECRET_KEY) < 50
        or len(set(SECRET_KEY)) < 5):
    raise ImproperlyConfigured('DJANGO_SECRET_KEY must be a strong production key.')

ALLOWED_HOSTS = [host.strip() for host in required('DJANGO_ALLOWED_HOSTS').split(',')
                 if host.strip()]
if not ALLOWED_HOSTS or any('*' in host for host in ALLOWED_HOSTS):
    raise ImproperlyConfigured('DJANGO_ALLOWED_HOSTS must contain explicit hosts.')

DATABASES = {'default': {
    'ENGINE': 'django.db.backends.postgresql',
    'NAME': required('DJANGO_DB_NAME'),
    'USER': required('DJANGO_DB_USER'),
    'PASSWORD': required('DJANGO_DB_PASSWORD'),
    'HOST': required('DJANGO_DB_HOST'),
    'PORT': os.environ.get('DJANGO_DB_PORT', '5432'),
}}
if DATABASES['default']['PASSWORD'] == 'pms-dev-only-password':
    raise ImproperlyConfigured('DJANGO_DB_PASSWORD must not use the development value.')
try:
    port = int(DATABASES['default']['PORT'])
    if not 1 <= port <= 65535:
        raise ValueError
except ValueError:
    raise ImproperlyConfigured('DJANGO_DB_PORT must be a valid port number.') from None
