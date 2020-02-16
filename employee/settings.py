"""
Django settings for employee project.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.7/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
import sys
import getpass
BASE_DIR = os.path.dirname(os.path.dirname(__file__))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '@p5sj45=(^$_b=%3^qzs$=tw72j01+6ay076w)6gogwwaj#if7'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']
NUMBER_GROUPING = 3

DATA_UPLOAD_MAX_NUMBER_FIELDS = None

# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'django_filters',
    'rest_framework',
    'eb',
    'flow',
    'contract',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'employee.urls'

WSGI_APPLICATION = 'employee.wsgi.application'

SESSION_COOKIE_AGE = 60 * 60 * 24

# Database
# https://docs.djangoproject.com/en/1.7/ref/settings/#databases

# AWS docker
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'wt_sales',
        'USER': 'root',
        'PASSWORD': os.environ['MYSQL_ENV_MYSQL_ROOT_PASSWORD'],
        'HOST': os.environ['MYSQL_PORT_3306_TCP_ADDR'],
        'PORT': os.environ['MYSQL_PORT_3306_TCP_PORT'],
    },
}

# DATABASE_ROUTERS = ['employee.db_router.DbRouter']

# Internationalization
# https://docs.djangoproject.com/en/1.7/topics/i18n/

# LANGUAGE_CODE = 'en-us'
LANGUAGE_CODE = 'ja'

# TIME_ZONE = 'UTC'
TIME_ZONE = 'Asia/Tokyo'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.7/howto/static-files/

STATIC_URL = '/static/'
STATICFILES_DIRS = (
    os.path.join(BASE_DIR, "static"),
)

MEDIA_ROOT = os.path.join(BASE_DIR, "media")
MEDIA_URL = '/media/'
GENERATED_FILES_ROOT = os.path.join(os.path.abspath(os.path.dirname(BASE_DIR)), "sales_files")

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

REST_FRAMEWORK = {
    # 'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'DEFAULT_FILTER_BACKENDS': ('django_filters.rest_framework.DjangoFilterBackend',),
    # 'PAGE_SIZE': 15
}

LOG_ROOT = os.path.join(BASE_DIR, 'log')
if not os.path.exists(LOG_ROOT):
    os.mkdir(LOG_ROOT)
    os.mkdir(os.path.join(LOG_ROOT, 'batch'))

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': "[%(asctime)s] %(levelname)s [PROCESS:%(process)d] [%(module)s:%(lineno)s] %(message)s",
            'datefmt': "%Y/%m/%d %H:%M:%S"
        },
    },
    'handlers': {
        'sync_members': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'formatter': 'standard',
            'filename': os.path.join(BASE_DIR, "log/batch/sync_members.log"),
        },
        'sync_members_cost': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'formatter': 'standard',
            'filename': os.path.join(BASE_DIR, "log/batch/sync_members_cost.log"),
        },
        'member_status': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'formatter': 'standard',
            'filename': os.path.join(BASE_DIR, "log/batch/member_status.log"),
        },
        'send_attendance_format': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'formatter': 'standard',
            'filename': os.path.join(BASE_DIR, "log/batch/send_attendance_format.log"),
        },
        'push_new_member': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'formatter': 'standard',
            'filename': os.path.join(BASE_DIR, "log/batch/push_new_member.log"),
        },
        'push_birthday': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'formatter': 'standard',
            'filename': os.path.join(BASE_DIR, "log/batch/push_birthday.log"),
        },
        'push_waiting_member': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'formatter': 'standard',
            'filename': os.path.join(BASE_DIR, "log/batch/push_waiting_member.log"),
        },
        'sync_contract': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'formatter': 'standard',
            'filename': os.path.join(BASE_DIR, "log/batch/sync_contract.log"),
        },
        'sync_bp_contract': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'formatter': 'standard',
            'filename': os.path.join(BASE_DIR, "log/batch/sync_bp_contract.log"),
        },
        'wt_sales': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'formatter': 'standard',
            'filename': os.path.join(BASE_DIR, "log/wt_sales.log"),
        },
        # 'console': {
        #     'level': 'DEBUG',
        #     'class': 'logging.StreamHandler',
        #     'formatter': 'standard'
        # },
    },
    'loggers': {
        'eb.management.commands.sync_members': {
            'handlers': ['sync_members'],
            'level': 'INFO',
            'propagate': True,
        },
        'eb.management.commands.sync_members_cost': {
            'handlers': ['sync_members_cost'],
            'level': 'INFO',
            'propagate': True,
        },
        'eb.management.commands.member_status': {
            'handlers': ['member_status'],
            'level': 'INFO',
            'propagate': True,
        },
        'eb.management.commands.send_attendance_format': {
            'handlers': ['send_attendance_format'],
            'level': 'INFO',
            'propagate': True,
        },
        'eb.management.commands.push_new_member': {
            'handlers': ['push_new_member'],
            'level': 'INFO',
            'propagate': True,
        },
        'eb.management.commands.push_birthday': {
            'handlers': ['push_birthday'],
            'level': 'INFO',
            'propagate': True,
        },
        'eb.management.commands.push_waiting_member': {
            'handlers': ['push_waiting_member'],
            'level': 'INFO',
            'propagate': True,
        },
        'eb.management.commands.sync_contract': {
            'handlers': ['sync_contract'],
            'level': 'INFO',
            'propagate': True,
        },
        'eb.management.commands.sync_bp_contract': {
            'handlers': ['sync_bp_contract'],
            'level': 'INFO',
            'propagate': True,
        },
        'wt_sales': {
            'handlers': ['wt_sales'],
            'level': 'INFO',
            'propagate': True,
        },
        # 'django': {
        #     'handlers': ['console'],
        #     'level': 'DEBUG',
        #     'propagate': True,
        # },
    }
}
