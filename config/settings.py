import os
from pathlib import Path
import dj_database_url

BASE_DIR=Path(__file__).resolve().parent.parent
SECRET_KEY=os.getenv("SECRET_KEY","dev-only-change-me")
DEBUG=os.getenv("DEBUG","1")=="1"
ALLOWED_HOSTS=[h.strip() for h in os.getenv("ALLOWED_HOSTS","localhost,127.0.0.1").split(",") if h.strip()]
CSRF_TRUSTED_ORIGINS=[u.strip() for u in os.getenv("CSRF_TRUSTED_ORIGINS","").split(",") if u.strip()]

INSTALLED_APPS=[
"django.contrib.admin","django.contrib.auth","django.contrib.contenttypes",
"django.contrib.sessions","django.contrib.messages","django.contrib.staticfiles","core",
]
MIDDLEWARE=[
"django.middleware.security.SecurityMiddleware",
"whitenoise.middleware.WhiteNoiseMiddleware",
"django.contrib.sessions.middleware.SessionMiddleware",
"django.middleware.common.CommonMiddleware",
"django.middleware.csrf.CsrfViewMiddleware",
"django.contrib.auth.middleware.AuthenticationMiddleware",
"django.contrib.messages.middleware.MessageMiddleware",
"django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF="config.urls"
TEMPLATES=[{"BACKEND":"django.template.backends.django.DjangoTemplates","DIRS":[BASE_DIR/"templates"],"APP_DIRS":True,
"OPTIONS":{"context_processors":["django.template.context_processors.request","django.contrib.auth.context_processors.auth","django.contrib.messages.context_processors.messages"]}}]
WSGI_APPLICATION="config.wsgi.application"
DATABASES={"default":dj_database_url.config(default=f"sqlite:///{BASE_DIR/'db.sqlite3'}",conn_max_age=600)}
if os.getenv("DATABASE_URL"):
    DATABASES["default"].setdefault("OPTIONS", {})
    DATABASES["default"]["OPTIONS"]["sslmode"]="require"
    DATABASES["default"]["OPTIONS"]["options"]="-c search_path=rose_app,public"
AUTH_PASSWORD_VALIDATORS=[
{"NAME":"django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
{"NAME":"django.contrib.auth.password_validation.MinimumLengthValidator"},
{"NAME":"django.contrib.auth.password_validation.CommonPasswordValidator"},
{"NAME":"django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LANGUAGE_CODE="pt-br"
TIME_ZONE="America/Sao_Paulo"
USE_I18N=True
USE_TZ=True
STATIC_URL="static/"
STATIC_ROOT=BASE_DIR/"staticfiles"
STATICFILES_DIRS=[BASE_DIR/"static"]
STORAGES={"staticfiles":{"BACKEND":"whitenoise.storage.CompressedManifestStaticFilesStorage"}}
DEFAULT_AUTO_FIELD="django.db.models.BigAutoField"
LOGIN_URL="/painel/entrar/"
LOGIN_REDIRECT_URL="/painel/"
LOGOUT_REDIRECT_URL="/"
SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTO","https")
SESSION_COOKIE_SECURE=not DEBUG
CSRF_COOKIE_SECURE=not DEBUG
X_FRAME_OPTIONS="DENY"
SECURE_CONTENT_TYPE_NOSNIFF=True

EMAIL_HOST=os.getenv("EMAIL_HOST","")
EMAIL_PORT=int(os.getenv("EMAIL_PORT","587"))
EMAIL_HOST_USER=os.getenv("EMAIL_HOST_USER","")
EMAIL_HOST_PASSWORD=os.getenv("EMAIL_HOST_PASSWORD","")
EMAIL_USE_TLS=os.getenv("EMAIL_USE_TLS","1")=="1"
DEFAULT_FROM_EMAIL=os.getenv("DEFAULT_FROM_EMAIL","Rose Freitas <no-reply@example.com>")
EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend" if EMAIL_HOST else "django.core.mail.backends.console.EmailBackend"
