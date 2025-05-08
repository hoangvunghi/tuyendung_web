from pathlib import Path
from datetime import timedelta
import os
import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'False') == 'True'

ALLOWED_HOSTS = ['tuyendungtlu.site', 'api.tuyendungtlu.site','www.api.tuyendungtlu.site','www.tuyendungtlu.site',"3.1.71.16","127.0.0.1","localhost"]

# Cloudinary configuration
cloudinary.config( 
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET'),
    secure=True
)

# Application definition
INSTALLED_APPS = [
    "unfold",
    "unfold.contrib.filters", 
    "unfold.contrib.forms", 
    "unfold.contrib.inlines",  
    "unfold.contrib.import_export",  
    "unfold.contrib.guardian",  
    "unfold.contrib.simple_history",  
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'base.apps.BaseConfig',
    "accounts",
    "enterprises",
    "profiles",
    "transactions",
    # "services",
    "notifications",
    'interviews',  
    'chat',  
    'gemini_chat',  # Thêm ứng dụng Gemini Chat
    'rest_framework',
    'rest_framework.authtoken',
    'rest_framework_simplejwt',
    'drf_yasg',
    'channels',
    'social_django',  # Dùng cho Google Login
    'corsheaders',
    'django_filters',
    'channels_redis',
    # 'daphne',
]

# Site ID
SITE_ID = 1

# Authentication backends
AUTHENTICATION_BACKENDS = [
    'social_core.backends.google.GoogleOAuth2', 
    'django.contrib.auth.backends.ModelBackend',  
]

# Google OAuth2 settings
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = os.getenv('GOOGLE_OAUTH2_KEY')
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = os.getenv('GOOGLE_OAUTH2_SECRET')
SOCIAL_AUTH_GOOGLE_OAUTH2_SCOPE = [
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
    'openid'
]
SOCIAL_AUTH_GOOGLE_OAUTH2_AUTH_EXTRA_ARGUMENTS = {
    'access_type': 'offline',
    'prompt': 'consent',
}

# Social Auth Pipeline
SOCIAL_AUTH_PIPELINE = (
    'social_core.pipeline.social_auth.social_details',
    'social_core.pipeline.social_auth.social_uid',
    'social_core.pipeline.social_auth.auth_allowed',
    'social_core.pipeline.social_auth.social_user',
    'accounts.pipeline.associate_by_email',
    'accounts.pipeline.custom_social_user',
    'accounts.pipeline.handle_auth_already_associated',
    'accounts.pipeline.create_user_profile',
    'accounts.pipeline.get_token_for_frontend',
)

# Social Auth settings
SOCIAL_AUTH_LOGIN_REDIRECT_URL = '/api/auth/callback/'
SOCIAL_AUTH_LOGIN_ERROR_URL = 'https://tuyendungtlu.site/login-error'
SOCIAL_AUTH_URL_NAMESPACE = 'social'
SOCIAL_AUTH_USER_MODEL = 'accounts.UserAccount'
SOCIAL_AUTH_USERNAME_IS_FULL_EMAIL = True
SOCIAL_AUTH_EMAIL_UNIQUE = True
SOCIAL_AUTH_EMAIL_REQUIRED = True
SOCIAL_AUTH_SANITIZE_REDIRECTS = False
SOCIAL_AUTH_RAISE_EXCEPTIONS = True
SOCIAL_AUTH_STORAGE = 'social_django.models.DjangoStorage'
SOCIAL_AUTH_STRATEGY = 'social_django.strategy.DjangoStrategy'

# Đường dẫn API
API_URL_PREFIX = '/api'  # Prefix cho tất cả các API endpoints

# Social Auth URL settings - Đảm bảo khớp với Google Cloud Console
SOCIAL_AUTH_URL_PREFIX = API_URL_PREFIX  # Thêm /api vào đầu các URL của social auth

# Cấu hình Allauth
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = 'optional'
ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_UNIQUE_EMAIL = True

# URL Frontend cho redirect sau khi login
# FRONTEND_URL = 'http://localhost:5173'
FRONTEND_URL = 'https://tuyendungtlu.site'

# CHANNEL_LAYERS = {
#     'default': {
#         'BACKEND': 'channels.layers.InMemoryChannelLayer',
#     },
# }

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [('127.0.0.1', 6379)],
        },
    },
}
AUTH_USER_MODEL = 'accounts.UserAccount'

CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://3.1.71.16",
    "http://3.1.71.16:8001",

    "http://3.1.71.16:5173",
    "http://3.1.71.16:3000",
    # "http://tuyendungtlu.site",
    "https://tuyendungtlu.site",
    "https://www.tuyendungtlu.site",
    # "https://tuyendungtlu.site:5173",
    # "http://api.tuyendungtlu.site",
    "https://api.tuyendungtlu.site",
    "https://www.api.tuyendungtlu.site",
]

SECURITY_PASSWORD_SALT = "@bfjkh189721!@#kjds905-222ss"
BACKEND_URL = "https://api.tuyendungtlu.site/api"
FRONTEND_URL = "https://tuyendungtlu.site"
# FRONT_END_URL = "http://localhost:5173"
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'social_django.middleware.SocialAuthExceptionMiddleware',  # Middleware cho social_django
]
# CORS_ALLOW_ALL_ORIGINS = True
ROOT_URLCONF = 'tuyendung.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, "templates"),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.static',
                'social_django.context_processors.backends',  # Cần cho social_django
            ],
        },
    },
]

WSGI_APPLICATION = 'tuyendung.wsgi.application'
ASGI_APPLICATION = 'tuyendung.asgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST'),
        'PORT': os.getenv('DB_PORT'),
        'OPTIONS': {
            'sslmode': 'require',
        },
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'vi'
TIME_ZONE = 'Asia/Ho_Chi_Minh'
USE_I18N = True
USE_TZ = True
LANGUAGES = [
    ('en', 'English'),
    ('vi', 'Vietnamese'),
]

# Static files
STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "staticfiles"),
]

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Email settings
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
EMAIL_USE_TLS = True

# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

# Simple JWT settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
}

# Swagger settings
SWAGGER_SETTINGS = {
    'SECURITY_DEFINITIONS': {
        'Bearer': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header'
        }
    },
    'USE_SESSION_AUTH': False,
}

# Unfold Admin Configuration
from .admin_config import UNFOLD, get_dashboard_config

UNFOLD = {
    **UNFOLD,
}

# Admin site configuration
JAZZMIN_SETTINGS = None
ADMIN_SITE_TITLE = UNFOLD["SITE_TITLE"]
ADMIN_SITE_HEADER = UNFOLD["SITE_HEADER"]
ADMIN_INDEX_TITLE = UNFOLD["SITE_SUBHEADER"]

# Cache settings
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
        'TIMEOUT': 300,  # 5 minutes
    }
}

# AWS S3 settings
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME')
AWS_S3_URL = f"https://{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/"
AWS_REGION = os.getenv('AWS_REGION')

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'debug.log'),
            'formatter': 'verbose',
            'mode': 'a',  # Append mode
        },
        'error_file': {
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'error.log'),
            'formatter': 'verbose',
            'mode': 'a',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file', 'error_file'],
            'level': 'INFO',
            'propagate': True,
        },
        'accounts': {  # Logger cho app accounts
            'handlers': ['console', 'file', 'error_file'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'social_core': {  # Logger cho social auth
            'handlers': ['console', 'file', 'error_file'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'social_django': {  # Logger cho social django
            'handlers': ['console', 'file', 'error_file'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
    'root': {
        'handlers': ['console', 'file', 'error_file'],
        'level': 'INFO',
    },
}

# Celery Configuration
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 phút

# Celery Beat Configuration
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'check-premium-expiry': {
        'task': 'accounts.tasks.check_premium_expiry',
        'schedule': crontab(hour=7, minute=0),  # Chạy lúc 7 giờ sáng hàng ngày
    },
}

# Gemini API Configuration
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', 'YOUR_GEMINI_API_KEY_HERE')  # Thay thế bằng API key thực tế


SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True 
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

CSRF_TRUSTED_ORIGINS = [
    'https://tuyendungtlu.site',
    'https://www.*.tuyendungtlu.site',
    'https://*.tuyendungtlu.site',
    'http://3.1.71.16:8001',
    'https://www.*.tuyendungtlu.site',
    'https://*.api.tuyendungtlu.site',
    # 'http://api.tuyendungtlu.site',
    # 'http://localhost:5173',  # Add for local development if needed
    # 'http://localhost:3000',  # Add for local development if needed
]
CORS_ALLOW_CREDENTIALS = True