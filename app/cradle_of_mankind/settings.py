"""
Django settings for cradle_of_mankind project.

Generated by 'django-admin startproject' using Django 3.1.2.

For more information on this file, see
https://docs.djangoproject.com/en/3.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.1/ref/settings/
"""

import os
import json

from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

try:
    with open(os.path.join(BASE_DIR, 'config.json')) as config_file:
        config = json.load(config_file)
except IOError:
    config = {}


def get_var(name, default_value=None):
    """
    The function first searches for a environmental variable called by the
    name. Then, if not found, it searches for the value from config.json file.
    If the variable is not found on either place, then it returns default_value.
    """
    return os.environ.get(name, config.get(name, default_value))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.1/howto/deployment/checklist/


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = get_var('SECRET_KEY', 'development_key')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = bool(int(get_var('DEBUG', 1)))

ALLOWED_HOSTS = []
ALLOWED_HOSTS_ENV = get_var('ALLOWED_HOSTS', None)
if ALLOWED_HOSTS_ENV:
    ALLOWED_HOSTS.extend(ALLOWED_HOSTS_ENV.split(','))
else:
    ALLOWED_HOSTS.append('*')

CSRF_TRUSTED_ORIGINS = []
TRUSTED_ORIGINS_ENV = os.environ.get('TRUSTED_ORIGINS', None)
if TRUSTED_ORIGINS_ENV:
    CSRF_TRUSTED_ORIGINS.extend(TRUSTED_ORIGINS_ENV.split(','))

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'main.apps.MainConfig',
    'users.apps.UsersConfig',
    'scans.apps.ScansConfig',
    'zooniverse.apps.ZooniverseConfig',
    'quality_control.apps.QualityControlConfig',
    'masterdata.apps.MasterdataConfig',
    'contact.apps.ContactConfig',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.orcid',
    'crispy_forms',
    'simple_history',
    'django_userforeignkey',
]

SITE_ID = 1

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'simple_history.middleware.HistoryRequestMiddleware',
    'django_userforeignkey.middleware.UserForeignKeyMiddleware',
]

ROOT_URLCONF = 'cradle_of_mankind.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

SOCIALACCOUNT_PROVIDERS = {
    'orcid': {
        'BASE_DOMAIN': 'orcid.org',
        'MEMBER_API': False,
        'APP': {
            'client_id': get_var('ORCID_CLIENT_ID', ''),
            'secret': get_var('ORCID_SECRET', ''),
            'key': '',
        }
    }
}

ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_CONFIRM_EMAIL_ON_GET = True
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_SESSION_REMEMBER = True
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True

WSGI_APPLICATION = 'cradle_of_mankind.wsgi.application'


# Database
# https://docs.djangoproject.com/en/3.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'HOST': get_var('DB_HOST'),
        'NAME': get_var('DB_NAME'),
        'USER': get_var('DB_USER'),
        'PASSWORD': get_var('DB_PASSWORD'),
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'charset': 'utf8mb4',
        },
    }
}


# Password validation
# https://docs.djangoproject.com/en/3.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

AUTH_USER_MODEL = 'users.User'


# Internationalization
# https://docs.djangoproject.com/en/3.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Europe/Helsinki'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.1/howto/static-files/

STATIC_ROOT = get_var('STATIC_ROOT', os.path.join(BASE_DIR, 'static'))
STATIC_URL = '/static/'

MEDIA_ROOT = get_var('MEDIA_ROOT', os.path.join(BASE_DIR, 'media'))
MEDIA_URL = '/media/'

LOGIN_REDIRECT_URL = 'index'

LOGIN_URL = 'account_login'

SENDGRID_API_KEY = get_var('SENDGRID_API_KEY')

EMAIL_BACKEND = get_var(
    'EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = 'smtp.sendgrid.net'
EMAIL_HOST_USER = 'apikey' # this is exactly the value 'apikey'
EMAIL_HOST_PASSWORD = SENDGRID_API_KEY
EMAIL_PORT = 587
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = get_var('DEFAULT_FROM_EMAIL')

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'formatters': {
        'my_formatter': {
            'format': '[{asctime}] {levelname} {threadName} {processName} {pathname}:{lineno} {name} {funcName} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler',
            'include_html': True,
        },
        'console': {
            'level': get_var('CONSOLE_LOG_LEVEL', 'INFO'),
            'class': 'logging.StreamHandler',
            'formatter': 'my_formatter',
        },
        'info_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'info.log'),
            'mode': 'a',
            'encoding': 'utf-8',
            'formatter': 'my_formatter',
            'backupCount': 5,
            'maxBytes': 10485760,
        },
        'debug_file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'debug.log'),
            'mode': 'a',
            'encoding': 'utf-8',
            'formatter': 'my_formatter',
            'backupCount': 5,
            'maxBytes': 10485760,
        },
    },
    'loggers': {
        '': {
            'level': get_var('ROOT_LOG_LEVEL', 'DEBUG'),
            'handlers': ['console', 'mail_admins', 'info_file', 'debug_file', ],
        },
        'django': {
            'level': get_var('DJANGO_LOG_LEVEL', 'DEBUG'),
            'handlers': ['console', 'mail_admins', 'info_file', 'debug_file', ],
            'propagate': False,
        },
        'django.server': {
            'propagate': False,
        }
    },
}
