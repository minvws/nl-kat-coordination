# Rocky

---

## `DJANGO_BASE_DIR`

*Optional* `DirectoryPath`

---


## `DJANGO_DEBUG`

*Optional* `bool`, default value: `False`

---


## `DJANGO_DEBUG_PROPAGATE_EXCEPTIONS`

*Optional* `bool`, default value: `False`

---


## `DJANGO_ADMINS`

*Optional* `Tuple`

---


## `DJANGO_INTERNAL_IPS`

*Optional* `IPvAnyAddress`, default value: `[]`

---


## `ALLOWED_HOSTS`

*Optional* `str`, default value: ``

---


## `DJANGO_TIME_ZONE`

*Optional* `str`, default value: `UTC`

---


## `DJANGO_USE_TZ`

*Optional* `bool`, default value: `True`

---


## `DJANGO_LANGUAGE_CODE`

*Optional* `str`, default value: `en`

---


## `DJANGO_LANGUAGES`

*Optional* `Any`, default value: `[('en', 'en'), ('nl', 'nl'), ('pap', 'pap')]`

---


## `DJANGO_LANGUAGES_BIDI`

*Optional* `str`, default value: `['he', 'ar', 'ar-dz', 'ckb', 'fa', 'ur']`

---


## `DJANGO_USE_I18N`

*Optional* `bool`, default value: `True`

---


## `DJANGO_LOCALE_PATHS`

*Optional* `Any`, default value: `(PosixPath('../rocky/locale'),)`

---


## `DJANGO_LANGUAGE_COOKIE_NAME`

*Optional* `str`, default value: `language`

---


## `DJANGO_LANGUAGE_COOKIE_AGE`

*Optional* `int`

---


## `DJANGO_LANGUAGE_COOKIE_DOMAIN`

*Optional* `str`

---


## `DJANGO_LANGUAGE_COOKIE_PATH`

*Optional* `str`, default value: `/`

---


## `DJANGO_LANGUAGE_COOKIE_SECURE`

*Optional* `bool`, default value: `False`

---


## `DJANGO_LANGUAGE_COOKIE_HTTPONLY`

*Optional* `bool`, default value: `False`

---


## `DJANGO_LANGUAGE_COOKIE_SAMESITE`

*Optional* `Literal`

### Possible values

`Lax`, `Strict`, `None`

---


## `DJANGO_USE_L10N`

*Optional* `bool`, default value: `True`

---


## `DJANGO_MANAGERS`

*Optional* `Tuple`, default value: `[]`

---


## `DJANGO_DEFAULT_CHARSET`

*Optional* `str`, default value: `utf-8`

---


## `DJANGO_SERVER_EMAIL`

*Optional* `str`, default value: ``

---


## `DJANGO_DATABASES`

*Optional* `Any`, default value: `{'default': {'ENGINE': 'django.db.backends.postgresql', 'NAME': None, 'USER': None, 'PASSWORD': None, 'HOST': None, 'PORT': 5432}}`

---


## `DJANGO_DATABASE_ROUTERS`

*Optional* `str`, default value: `[]`

---


## `DJANGO_EMAIL_BACKEND`

*Optional* `str`, default value: `django.core.mail.backends.console.EmailBackend`

---


## `DJANGO_EMAIL_HOST`

*Optional* `str`, default value: `localhost`

---


## `DJANGO_EMAIL_PORT`

*Optional* `int`, default value: `25`

---


## `DJANGO_EMAIL_USE_LOCALTIME`

*Optional* `bool`, default value: `False`

---


## `DJANGO_EMAIL_HOST_USER`

*Optional* `str`, default value: ``

---


## `DJANGO_EMAIL_HOST_PASSWORD`

*Optional* `str`, default value: ``

---


## `DJANGO_EMAIL_USE_TLS`

*Optional* `bool`, default value: `False`

---


## `DJANGO_EMAIL_USE_SSL`

*Optional* `bool`, default value: `False`

---


## `DJANGO_EMAIL_SSL_CERTFILE`

*Optional* `str`

---


## `DJANGO_EMAIL_SSL_KEYFILE`

*Optional* `str`

---


## `DJANGO_EMAIL_TIMEOUT`

*Optional* `int`, default value: `30`

---


## `DJANGO_INSTALLED_APPS`

*Optional* `str`, default value: `['django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes', 'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles', 'django.forms', 'django_otp', 'django_otp.plugins.otp_static', 'django_otp.plugins.otp_totp', 'two_factor', 'account', 'tools', 'fmea', 'crisis_room', 'onboarding', 'katalogus', 'django_password_validators', 'django_password_validators.password_history', 'rest_framework', 'tagulous', 'csp']`

---


## `DJANGO_TEMPLATES`

*Optional* `Any`, default value: `[{'BACKEND': 'django.template.backends.django.DjangoTemplates', 'DIRS': [PosixPath('../rocky/templates')], 'APP_DIRS': True, 'OPTIONS': {'context_processors': ['django.template.context_processors.debug', 'django.template.context_processors.request', 'django.contrib.auth.context_processors.auth', 'django.contrib.messages.context_processors.messages', 'tools.context_processors.languages', 'tools.context_processors.organizations_including_blocked', 'tools.context_processors.rocky_version'], 'builtins': ['tools.templatetags.ooi_extra']}}]`

---


## `DJANGO_FORM_RENDERER`

*Optional* `str`, default value: `django.forms.renderers.TemplatesSetting`

---


## `DJANGO_DEFAULT_FROM_EMAIL`

*Optional* `str`, default value: ``

---


## `DJANGO_EMAIL_SUBJECT_PREFIX`

*Optional* `str`, default value: `KAT - `

---


## `DJANGO_APPEND_SLASH`

*Optional* `bool`, default value: `True`

---


## `DJANGO_PREPEND_WWW`

*Optional* `bool`, default value: `False`

---


## `DJANGO_FORCE_SCRIPT_NAME`

*Optional* `str`

---


## `DJANGO_DISALLOWED_USER_AGENTS`

*Optional* `Pattern`, default value: `[]`

---


## `DJANGO_ABSOLUTE_URL_OVERRIDES`

*Optional* `Callable`, default value: `{}`

---


## `DJANGO_IGNORABLE_404_URLS`

*Optional* `Pattern`, default value: `[]`

---


## `DJANGO_SECRET_KEY`

*Optional* `str`

---


## `DJANGO_DEFAULT_FILE_STORAGE`

*Optional* `str`, default value: `django.core.files.storage.FileSystemStorage`

---


## `DJANGO_MEDIA_ROOT`

*Optional* `str`, default value: ``

---


## `DJANGO_MEDIA_URL`

*Optional* `str`, default value: ``

---


## `DJANGO_STATIC_ROOT`

*Optional* `Path`, default value: `../static`

---


## `DJANGO_STATIC_URL`

*Optional* `str`, default value: `/static/`

---


## `DJANGO_FILE_UPLOAD_HANDLERS`

*Optional* `str`, default value: `['django.core.files.uploadhandler.MemoryFileUploadHandler', 'django.core.files.uploadhandler.TemporaryFileUploadHandler']`

---


## `DJANGO_FILE_UPLOAD_MAX_MEMORY_SIZE`

*Optional* `int`, default value: `2621440`

---


## `DJANGO_DATA_UPLOAD_MAX_MEMORY_SIZE`

*Optional* `int`, default value: `2621440`

---


## `DJANGO_DATA_UPLOAD_MAX_NUMBER_FIELDS`

*Optional* `int`, default value: `1000`

---


## `DJANGO_FILE_UPLOAD_TEMP_DIR`

*Optional* `DirectoryPath`

---


## `DJANGO_FILE_UPLOAD_PERMISSIONS`

*Optional* `int`, default value: `420`

---


## `DJANGO_FILE_UPLOAD_DIRECTORY_PERMISSIONS`

*Optional* `int`

---


## `DJANGO_FORMAT_MODULE_PATH`

*Optional* `str`

---


## `DJANGO_DATE_FORMAT`

*Optional* `str`, default value: `N j, Y`

---


## `DJANGO_DATETIME_FORMAT`

*Optional* `str`, default value: `N j, Y, P`

---


## `DJANGO_TIME_FORMAT`

*Optional* `str`, default value: `P`

---


## `DJANGO_YEAR_MONTH_FORMAT`

*Optional* `str`, default value: `F Y`

---


## `DJANGO_MONTH_DAY_FORMAT`

*Optional* `str`, default value: `F j`

---


## `DJANGO_SHORT_DATE_FORMAT`

*Optional* `str`, default value: `m/d/Y`

---


## `DJANGO_SHORT_DATETIME_FORMAT`

*Optional* `str`, default value: `m/d/Y P`

---


## `DJANGO_DATE_INPUT_FORMATS`

*Optional* `str`, default value: `['%Y-%m-%d', '%m/%d/%Y', '%m/%d/%y', '%b %d %Y', '%b %d, %Y', '%d %b %Y', '%d %b, %Y', '%B %d %Y', '%B %d, %Y', '%d %B %Y', '%d %B, %Y']`

---


## `DJANGO_TIME_INPUT_FORMATS`

*Optional* `str`, default value: `['%H:%M:%S', '%H:%M:%S.%f', '%H:%M']`

---


## `DJANGO_DATETIME_INPUT_FORMATS`

*Optional* `str`, default value: `['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M', '%m/%d/%Y %H:%M:%S', '%m/%d/%Y %H:%M:%S.%f', '%m/%d/%Y %H:%M', '%m/%d/%y %H:%M:%S', '%m/%d/%y %H:%M:%S.%f', '%m/%d/%y %H:%M']`

---


## `DJANGO_FIRST_DAY_OF_WEEK`

*Optional* `int`, default value: `0`

---


## `DJANGO_DECIMAL_SEPARATOR`

*Optional* `str`, default value: `.`

---


## `DJANGO_USE_THOUSAND_SEPARATOR`

*Optional* `bool`, default value: `False`

---


## `DJANGO_THOUSAND_SEPARATOR`

*Optional* `str`, default value: `,`

---


## `DJANGO_DEFAULT_TABLESPACE`

*Optional* `str`, default value: ``

---


## `DJANGO_DEFAULT_INDEX_TABLESPACE`

*Optional* `str`, default value: ``

---


## `DJANGO_X_FRAME_OPTIONS`

*Optional* `str`, default value: `DENY`

---


## `DJANGO_USE_X_FORWARDED_HOST`

*Optional* `bool`, default value: `False`

---


## `DJANGO_USE_X_FORWARDED_PORT`

*Optional* `bool`, default value: `False`

---


## `DJANGO_WSGI_APPLICATION`

*Optional* `str`, default value: `rocky.wsgi.application`

---


## `DJANGO_SECURE_PROXY_SSL_HEADER`

*Optional* `Tuple`

---


## `DJANGO_DEFAULT_HASHING_ALGORITHM`

*Optional* `Literal`

### Possible values

`sha1`, `sha256`

---


## `DJANGO_MIDDLEWARE`

*Optional* `str`, default value: `['django.middleware.security.SecurityMiddleware', 'django.contrib.sessions.middleware.SessionMiddleware', 'django.middleware.locale.LocaleMiddleware', 'django.middleware.common.CommonMiddleware', 'django.middleware.csrf.CsrfViewMiddleware', 'django.contrib.auth.middleware.AuthenticationMiddleware', 'rocky.middleware.remote_user.RemoteUserMiddleware', 'django_otp.middleware.OTPMiddleware', 'rocky.middleware.auth_required.AuthRequiredMiddleware', 'django.contrib.messages.middleware.MessageMiddleware', 'django.middleware.clickjacking.XFrameOptionsMiddleware', 'rocky.middleware.onboarding.OnboardingMiddleware', 'csp.middleware.CSPMiddleware']`

---


## `DJANGO_SESSION_CACHE_ALIAS`

*Optional* `str`, default value: `default`

---


## `DJANGO_SESSION_COOKIE_NAME`

*Optional* `str`, default value: `sessionid`

---


## `DJANGO_SESSION_COOKIE_AGE`

*Optional* `int`, default value: `7200`

---


## `DJANGO_SESSION_COOKIE_DOMAIN`

*Optional* `str`

---


## `DJANGO_SESSION_COOKIE_SECURE`

*Optional* `bool`, default value: `True`

---


## `DJANGO_SESSION_COOKIE_PATH`

*Optional* `str`, default value: `/`

---


## `DJANGO_SESSION_COOKIE_HTTPONLY`

*Optional* `bool`, default value: `True`

---


## `DJANGO_SESSION_COOKIE_SAMESITE`

*Optional* `str`, default value: `Strict`

---


## `DJANGO_SESSION_SAVE_EVERY_REQUEST`

*Optional* `bool`, default value: `False`

---


## `DJANGO_SESSION_EXPIRE_AT_BROWSER_CLOSE`

*Optional* `bool`, default value: `False`

---


## `DJANGO_SESSION_ENGINE`

*Optional* `str`, default value: `django.contrib.sessions.backends.db`

---


## `DJANGO_SESSION_FILE_PATH`

*Optional* `DirectoryPath`

---


## `DJANGO_SESSION_SERIALIZER`

*Optional* `str`, default value: `django.contrib.sessions.serializers.JSONSerializer`

---


## `DJANGO_CACHES`

*Optional* `Any`, default value: `{'default': {'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache', 'LOCATION': '/var/tmp/django_cache', 'TIMEOUT': 60, 'OPTIONS': {'MAX_ENTRIES': 1000}}}`

---


## `DJANGO_CACHE_MIDDLEWARE_KEY_PREFIX`

*Optional* `str`, default value: ``

---


## `DJANGO_CACHE_MIDDLEWARE_SECONDS`

*Optional* `int`, default value: `600`

---


## `DJANGO_CACHE_MIDDLEWARE_ALIAS`

*Optional* `str`, default value: `default`

---


## `DJANGO_AUTH_USER_MODEL`

*Optional* `str`, default value: `account.KATUser`

---


## `DJANGO_AUTHENTICATION_BACKENDS`

*Optional* `Any`, default value: `['rocky.auth.remote_user.RemoteUserBackend', 'django.contrib.auth.backends.ModelBackend']`

---


## `DJANGO_LOGIN_URL`

*Optional* `str`, default value: `two_factor:login`

---


## `DJANGO_LOGIN_REDIRECT_URL`

*Optional* `str`, default value: `crisis_room`

---


## `DJANGO_PASSWORD_RESET_TIMEOUT_DAYS`

*Optional* `int`

---


## `DJANGO_PASSWORD_RESET_TIMEOUT`

*Optional* `int`, default value: `259200`

---


## `DJANGO_PASSWORD_HASHERS`

*Optional* `str`, default value: `['django.contrib.auth.hashers.PBKDF2PasswordHasher', 'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher', 'django.contrib.auth.hashers.Argon2PasswordHasher', 'django.contrib.auth.hashers.BCryptSHA256PasswordHasher', 'django.contrib.auth.hashers.ScryptPasswordHasher']`

---


## `DJANGO_AUTH_PASSWORD_VALIDATORS`

*Optional* `Any`, default value: `[{'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 12}}, {'NAME': 'django_password_validators.password_character_requirements.password_validation.PasswordCharacterValidator', 'OPTIONS': {'min_length_digit': 2, 'min_length_alpha': 2, 'min_length_special': 2, 'min_length_lower': 2, 'min_length_upper': 2, 'special_characters': ' ~!@#$%^&*()_+{}":;\'[]'}}]`

---


## `DJANGO_SIGNING_BACKEND`

*Optional* `str`, default value: `django.core.signing.TimestampSigner`

---


## `DJANGO_CSRF_FAILURE_VIEW`

*Optional* `str`, default value: `django.views.csrf.csrf_failure`

---


## `DJANGO_CSRF_COOKIE_NAME`

*Optional* `str`, default value: `csrftoken`

---


## `DJANGO_CSRF_COOKIE_AGE`

*Optional* `int`, default value: `31449600`

---


## `DJANGO_CSRF_COOKIE_DOMAIN`

*Optional* `str`

---


## `DJANGO_CSRF_COOKIE_PATH`

*Optional* `str`, default value: `/`

---


## `DJANGO_CSRF_COOKIE_SECURE`

*Optional* `bool`, default value: `True`

---


## `DJANGO_CSRF_COOKIE_HTTPONLY`

*Optional* `bool`, default value: `True`

---


## `DJANGO_CSRF_COOKIE_SAMESITE`

*Optional* `str`, default value: `Strict`

---


## `DJANGO_CSRF_HEADER_NAME`

*Optional* `str`, default value: `HTTP_X_CSRFTOKEN`

---


## `DJANGO_CSRF_TRUSTED_ORIGINS`

*Optional* `Any`, default value: `[]`

---


## `DJANGO_CSRF_USE_SESSIONS`

*Optional* `bool`, default value: `False`

---


## `DJANGO_MESSAGE_STORAGE`

*Optional* `str`, default value: `django.contrib.messages.storage.fallback.FallbackStorage`

---


## `DJANGO_LOGGING_CONFIG`

*Optional* `str`, default value: `logging.config.dictConfig`

---


## `DJANGO_LOGGING`

*Optional* `dict`, default value: `{}`

---


## `DJANGO_DEFAULT_EXCEPTION_REPORTER`

*Optional* `str`, default value: `django.views.debug.ExceptionReporter`

---


## `DJANGO_DEFAULT_EXCEPTION_REPORTER_FILTER`

*Optional* `str`, default value: `django.views.debug.SafeExceptionReporterFilter`

---


## `DJANGO_TEST_RUNNER`

*Optional* `str`, default value: `django.test.runner.DiscoverRunner`

---


## `DJANGO_TEST_NON_SERIALIZED_APPS`

*Optional* `str`, default value: `[]`

---


## `DJANGO_FIXTURE_DIRS`

*Optional* `DirectoryPath`, default value: `[]`

---


## `DJANGO_STATICFILES_DIRS`

*Optional* `Any`, default value: `(PosixPath('../assets'),)`

---


## `DJANGO_STATICFILES_STORAGE`

*Optional* `str`, default value: `django.contrib.staticfiles.storage.StaticFilesStorage`

---


## `DJANGO_STATICFILES_FINDERS`

*Optional* `str`, default value: `['django.contrib.staticfiles.finders.FileSystemFinder', 'django.contrib.staticfiles.finders.AppDirectoriesFinder']`

---


## `DJANGO_MIGRATION_MODULES`

*Optional* `str`, default value: `{}`

---


## `DJANGO_SILENCED_SYSTEM_CHECKS`

*Optional* `str`, default value: `[]`

---


## `DJANGO_SECURE_BROWSER_XSS_FILTER`

*Optional* `bool`, default value: `True`

---


## `DJANGO_SECURE_CONTENT_TYPE_NOSNIFF`

*Optional* `bool`, default value: `True`

---


## `DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS`

*Optional* `bool`, default value: `False`

---


## `DJANGO_SECURE_HSTS_PRELOAD`

*Optional* `bool`, default value: `False`

---


## `DJANGO_SECURE_HSTS_SECONDS`

*Optional* `int`, default value: `0`

---


## `DJANGO_SECURE_REDIRECT_EXEMPT`

*Optional* `Pattern`, default value: `[]`

---


## `DJANGO_SECURE_REFERRER_POLICY`

*Optional* `Literal`, default value: `same-origin`

### Possible values

- `no-referrer`
- `no-referrer-when-downgrade`
- `origin`
- `origin-when-cross-origin`
- `same-origin`
- `strict-origin`
- `strict-origin-when-cross-origin`
- `unsafe-url`

---


## `DJANGO_SECURE_SSL_HOST`

*Optional* `str`

---


## `DJANGO_SECURE_SSL_REDIRECT`

*Optional* `bool`, default value: `False`

---


## `DJANGO_ROOT_URLCONF`

*Optional* `str`, default value: `rocky.urls`

---


## `DATABASE_URL`

*Optional* `DatabaseDsn`

---


## `CACHE_URL`

*Optional* `DatabaseDsn`

---


## `DJANGO_SCHEDULER_API`

*Optional* `str`, default value: ``

---


## `DJANGO_SPAN_EXPORT_GRPC_ENDPOINT`

*Optional* `str`

---


## `DJANGO_REMOTE_USER_HEADER`

*Optional* `str`

---


## `DJANGO_REMOTE_USER_FALLBACK`

*Optional* `bool`, default value: `False`

---


## `DJANGO_TWOFACTOR_ENABLED`

*Optional* `bool`, default value: `False`

---


## `DJANGO_CSP_HEADER`

*Optional* `str`, default value: `True`

---


## `DJANGO_GITPOD_WORKSPACE_URL`

*Optional* `str`

---


## `DJANGO_GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN`

*Optional* `str`

---


## `DJANGO_SERIALIZATION_MODULES`

*Optional* `Any`, default value: `{'xml': 'tagulous.serializers.xml_serializer', 'json': 'tagulous.serializers.json', 'python': 'tagulous.serializers.python', 'yaml': 'tagulous.serializers.pyyaml'}`

---


## `DJANGO_KEIKO_API`

*Optional* `str`, default value: ``

---


## `DJANGO_OCTOPOES_API`

*Optional* `str`, default value: ``

---


## `DJANGO_KEIKO_REPORT_TIMEOUT`

*Optional* `int`, default value: `60`

---


## `DJANGO_REMOTE_USER_DEFAULT_ORGANIZATIONS`

*Optional* `list`, default value: `[]`

---


## `DJANGO_TAG_COLORS`

*Optional* `list`, default value: `[('color-1-light', 'Blue light'), ('color-1-medium', 'Blue medium'), ('color-1-dark', 'Blue dark'), ('color-2-light', 'Green light'), ('color-2-medium', 'Green medium'), ('color-2-dark', 'Green dark'), ('color-3-light', 'Yellow light'), ('color-3-medium', 'Yellow medium'), ('color-3-dark', 'Yellow dark'), ('color-4-light', 'Orange light'), ('color-4-medium', 'Orange medium'), ('color-4-dark', 'Orange dark'), ('color-5-light', 'Red light'), ('color-5-medium', 'Red medium'), ('color-5-dark', 'Red dark'), ('color-6-light', 'Violet light'), ('color-6-medium', 'Violet medium'), ('color-6-dark', 'Violet dark')]`

---


## `DJANGO_TAG_BORDER_TYPES`

*Optional* `list`, default value: `[('plain', 'Plain'), ('solid', 'Solid'), ('dashed', 'Dashed'), ('dotted', 'Dotted')]`

---


## `DJANGO_POSTGRES_DB`

*Optional* `dict`, default value: `{'ENGINE': 'django.db.backends.postgresql', 'NAME': None, 'USER': None, 'PASSWORD': None, 'HOST': None, 'PORT': 5432}`

---


## `DJANGO_EMAIL_FILE_PATH`

*Optional* `Path`, default value: `/home/user/PycharmProjects/rocky/email_logs`

---


## `DJANGO_HELP_DESK_EMAIL`

*Optional* `str`, default value: ``

---


## `DJANGO_EXTRA_LANG_INFO`

*Optional* `dict`, default value: `{'pap': {'bidi': False, 'code': 'pap', 'name': 'Papiamentu', 'name_local': 'Papiamentu'}}`

---


## `DJANGO_LANG_INFO`

*Optional* `dict`, default value: `{'af': {'bidi': False, 'code': 'af', 'name': 'Afrikaans', 'name_local': 'Afrikaans'}, 'ar': {'bidi': True, 'code': 'ar', 'name': 'Arabic', 'name_local': 'العربيّة'}, 'ar-dz': {'bidi': True, 'code': 'ar-dz', 'name': 'Algerian Arabic', 'name_local': 'العربية الجزائرية'}, 'ast': {'bidi': False, 'code': 'ast', 'name': 'Asturian', 'name_local': 'asturianu'}, 'az': {'bidi': True, 'code': 'az', 'name': 'Azerbaijani', 'name_local': 'Azərbaycanca'}, 'be': {'bidi': False, 'code': 'be', 'name': 'Belarusian', 'name_local': 'беларуская'}, 'bg': {'bidi': False, 'code': 'bg', 'name': 'Bulgarian', 'name_local': 'български'}, 'bn': {'bidi': False, 'code': 'bn', 'name': 'Bengali', 'name_local': 'বাংলা'}, 'br': {'bidi': False, 'code': 'br', 'name': 'Breton', 'name_local': 'brezhoneg'}, 'bs': {'bidi': False, 'code': 'bs', 'name': 'Bosnian', 'name_local': 'bosanski'}, 'ca': {'bidi': False, 'code': 'ca', 'name': 'Catalan', 'name_local': 'català'}, 'ckb': {'bidi': True, 'code': 'ckb', 'name': 'Central Kurdish (Sorani)', 'name_local': 'کوردی'}, 'cs': {'bidi': False, 'code': 'cs', 'name': 'Czech', 'name_local': 'česky'}, 'cy': {'bidi': False, 'code': 'cy', 'name': 'Welsh', 'name_local': 'Cymraeg'}, 'da': {'bidi': False, 'code': 'da', 'name': 'Danish', 'name_local': 'dansk'}, 'de': {'bidi': False, 'code': 'de', 'name': 'German', 'name_local': 'Deutsch'}, 'dsb': {'bidi': False, 'code': 'dsb', 'name': 'Lower Sorbian', 'name_local': 'dolnoserbski'}, 'el': {'bidi': False, 'code': 'el', 'name': 'Greek', 'name_local': 'Ελληνικά'}, 'en': {'bidi': False, 'code': 'en', 'name': 'English', 'name_local': 'English'}, 'en-au': {'bidi': False, 'code': 'en-au', 'name': 'Australian English', 'name_local': 'Australian English'}, 'en-gb': {'bidi': False, 'code': 'en-gb', 'name': 'British English', 'name_local': 'British English'}, 'eo': {'bidi': False, 'code': 'eo', 'name': 'Esperanto', 'name_local': 'Esperanto'}, 'es': {'bidi': False, 'code': 'es', 'name': 'Spanish', 'name_local': 'español'}, 'es-ar': {'bidi': False, 'code': 'es-ar', 'name': 'Argentinian Spanish', 'name_local': 'español de Argentina'}, 'es-co': {'bidi': False, 'code': 'es-co', 'name': 'Colombian Spanish', 'name_local': 'español de Colombia'}, 'es-mx': {'bidi': False, 'code': 'es-mx', 'name': 'Mexican Spanish', 'name_local': 'español de Mexico'}, 'es-ni': {'bidi': False, 'code': 'es-ni', 'name': 'Nicaraguan Spanish', 'name_local': 'español de Nicaragua'}, 'es-ve': {'bidi': False, 'code': 'es-ve', 'name': 'Venezuelan Spanish', 'name_local': 'español de Venezuela'}, 'et': {'bidi': False, 'code': 'et', 'name': 'Estonian', 'name_local': 'eesti'}, 'eu': {'bidi': False, 'code': 'eu', 'name': 'Basque', 'name_local': 'Basque'}, 'fa': {'bidi': True, 'code': 'fa', 'name': 'Persian', 'name_local': 'فارسی'}, 'fi': {'bidi': False, 'code': 'fi', 'name': 'Finnish', 'name_local': 'suomi'}, 'fr': {'bidi': False, 'code': 'fr', 'name': 'French', 'name_local': 'français'}, 'fy': {'bidi': False, 'code': 'fy', 'name': 'Frisian', 'name_local': 'frysk'}, 'ga': {'bidi': False, 'code': 'ga', 'name': 'Irish', 'name_local': 'Gaeilge'}, 'gd': {'bidi': False, 'code': 'gd', 'name': 'Scottish Gaelic', 'name_local': 'Gàidhlig'}, 'gl': {'bidi': False, 'code': 'gl', 'name': 'Galician', 'name_local': 'galego'}, 'he': {'bidi': True, 'code': 'he', 'name': 'Hebrew', 'name_local': 'עברית'}, 'hi': {'bidi': False, 'code': 'hi', 'name': 'Hindi', 'name_local': 'हिंदी'}, 'hr': {'bidi': False, 'code': 'hr', 'name': 'Croatian', 'name_local': 'Hrvatski'}, 'hsb': {'bidi': False, 'code': 'hsb', 'name': 'Upper Sorbian', 'name_local': 'hornjoserbsce'}, 'hu': {'bidi': False, 'code': 'hu', 'name': 'Hungarian', 'name_local': 'Magyar'}, 'hy': {'bidi': False, 'code': 'hy', 'name': 'Armenian', 'name_local': 'հայերեն'}, 'ia': {'bidi': False, 'code': 'ia', 'name': 'Interlingua', 'name_local': 'Interlingua'}, 'io': {'bidi': False, 'code': 'io', 'name': 'Ido', 'name_local': 'ido'}, 'id': {'bidi': False, 'code': 'id', 'name': 'Indonesian', 'name_local': 'Bahasa Indonesia'}, 'ig': {'bidi': False, 'code': 'ig', 'name': 'Igbo', 'name_local': 'Asụsụ Ìgbò'}, 'is': {'bidi': False, 'code': 'is', 'name': 'Icelandic', 'name_local': 'Íslenska'}, 'it': {'bidi': False, 'code': 'it', 'name': 'Italian', 'name_local': 'italiano'}, 'ja': {'bidi': False, 'code': 'ja', 'name': 'Japanese', 'name_local': '日本語'}, 'ka': {'bidi': False, 'code': 'ka', 'name': 'Georgian', 'name_local': 'ქართული'}, 'kab': {'bidi': False, 'code': 'kab', 'name': 'Kabyle', 'name_local': 'taqbaylit'}, 'kk': {'bidi': False, 'code': 'kk', 'name': 'Kazakh', 'name_local': 'Қазақ'}, 'km': {'bidi': False, 'code': 'km', 'name': 'Khmer', 'name_local': 'Khmer'}, 'kn': {'bidi': False, 'code': 'kn', 'name': 'Kannada', 'name_local': 'Kannada'}, 'ko': {'bidi': False, 'code': 'ko', 'name': 'Korean', 'name_local': '한국어'}, 'ky': {'bidi': False, 'code': 'ky', 'name': 'Kyrgyz', 'name_local': 'Кыргызча'}, 'lb': {'bidi': False, 'code': 'lb', 'name': 'Luxembourgish', 'name_local': 'Lëtzebuergesch'}, 'lt': {'bidi': False, 'code': 'lt', 'name': 'Lithuanian', 'name_local': 'Lietuviškai'}, 'lv': {'bidi': False, 'code': 'lv', 'name': 'Latvian', 'name_local': 'latviešu'}, 'mk': {'bidi': False, 'code': 'mk', 'name': 'Macedonian', 'name_local': 'Македонски'}, 'ml': {'bidi': False, 'code': 'ml', 'name': 'Malayalam', 'name_local': 'മലയാളം'}, 'mn': {'bidi': False, 'code': 'mn', 'name': 'Mongolian', 'name_local': 'Mongolian'}, 'mr': {'bidi': False, 'code': 'mr', 'name': 'Marathi', 'name_local': 'मराठी'}, 'ms': {'bidi': False, 'code': 'ms', 'name': 'Malay', 'name_local': 'Bahasa Melayu'}, 'my': {'bidi': False, 'code': 'my', 'name': 'Burmese', 'name_local': 'မြန်မာဘာသာ'}, 'nb': {'bidi': False, 'code': 'nb', 'name': 'Norwegian Bokmal', 'name_local': 'norsk (bokmål)'}, 'ne': {'bidi': False, 'code': 'ne', 'name': 'Nepali', 'name_local': 'नेपाली'}, 'nl': {'bidi': False, 'code': 'nl', 'name': 'Dutch', 'name_local': 'Nederlands'}, 'nn': {'bidi': False, 'code': 'nn', 'name': 'Norwegian Nynorsk', 'name_local': 'norsk (nynorsk)'}, 'no': {'bidi': False, 'code': 'no', 'name': 'Norwegian', 'name_local': 'norsk'}, 'os': {'bidi': False, 'code': 'os', 'name': 'Ossetic', 'name_local': 'Ирон'}, 'pa': {'bidi': False, 'code': 'pa', 'name': 'Punjabi', 'name_local': 'Punjabi'}, 'pl': {'bidi': False, 'code': 'pl', 'name': 'Polish', 'name_local': 'polski'}, 'pt': {'bidi': False, 'code': 'pt', 'name': 'Portuguese', 'name_local': 'Português'}, 'pt-br': {'bidi': False, 'code': 'pt-br', 'name': 'Brazilian Portuguese', 'name_local': 'Português Brasileiro'}, 'ro': {'bidi': False, 'code': 'ro', 'name': 'Romanian', 'name_local': 'Română'}, 'ru': {'bidi': False, 'code': 'ru', 'name': 'Russian', 'name_local': 'Русский'}, 'sk': {'bidi': False, 'code': 'sk', 'name': 'Slovak', 'name_local': 'Slovensky'}, 'sl': {'bidi': False, 'code': 'sl', 'name': 'Slovenian', 'name_local': 'Slovenščina'}, 'sq': {'bidi': False, 'code': 'sq', 'name': 'Albanian', 'name_local': 'shqip'}, 'sr': {'bidi': False, 'code': 'sr', 'name': 'Serbian', 'name_local': 'српски'}, 'sr-latn': {'bidi': False, 'code': 'sr-latn', 'name': 'Serbian Latin', 'name_local': 'srpski (latinica)'}, 'sv': {'bidi': False, 'code': 'sv', 'name': 'Swedish', 'name_local': 'svenska'}, 'sw': {'bidi': False, 'code': 'sw', 'name': 'Swahili', 'name_local': 'Kiswahili'}, 'ta': {'bidi': False, 'code': 'ta', 'name': 'Tamil', 'name_local': 'தமிழ்'}, 'te': {'bidi': False, 'code': 'te', 'name': 'Telugu', 'name_local': 'తెలుగు'}, 'tg': {'bidi': False, 'code': 'tg', 'name': 'Tajik', 'name_local': 'тоҷикӣ'}, 'th': {'bidi': False, 'code': 'th', 'name': 'Thai', 'name_local': 'ภาษาไทย'}, 'tk': {'bidi': False, 'code': 'tk', 'name': 'Turkmen', 'name_local': 'Türkmençe'}, 'tr': {'bidi': False, 'code': 'tr', 'name': 'Turkish', 'name_local': 'Türkçe'}, 'tt': {'bidi': False, 'code': 'tt', 'name': 'Tatar', 'name_local': 'Татарча'}, 'udm': {'bidi': False, 'code': 'udm', 'name': 'Udmurt', 'name_local': 'Удмурт'}, 'uk': {'bidi': False, 'code': 'uk', 'name': 'Ukrainian', 'name_local': 'Українська'}, 'ur': {'bidi': True, 'code': 'ur', 'name': 'Urdu', 'name_local': 'اردو'}, 'uz': {'bidi': False, 'code': 'uz', 'name': 'Uzbek', 'name_local': 'oʻzbek tili'}, 'vi': {'bidi': False, 'code': 'vi', 'name': 'Vietnamese', 'name_local': 'Tiếng Việt'}, 'zh-cn': {'fallback': ['zh-hans']}, 'zh-hans': {'bidi': False, 'code': 'zh-hans', 'name': 'Simplified Chinese', 'name_local': '简体中文'}, 'zh-hant': {'bidi': False, 'code': 'zh-hant', 'name': 'Traditional Chinese', 'name_local': '繁體中文'}, 'zh-hk': {'fallback': ['zh-hant']}, 'zh-mo': {'fallback': ['zh-hant']}, 'zh-my': {'fallback': ['zh-hans']}, 'zh-sg': {'fallback': ['zh-hans']}, 'zh-tw': {'fallback': ['zh-hant']}, 'pap': {'bidi': False, 'code': 'pap', 'name': 'Papiamentu', 'name_local': 'Papiamentu'}}`

---


## `DJANGO_DEFAULT_AUTO_FIELD`

*Optional* `str`, default value: `django.db.models.BigAutoField`

---


## `DJANGO_SESSION_EXPIRE_SECONDS`

*Optional* `int`, default value: `7200`

---


## `DJANGO_SESSION_EXPIRE_AFTER_LAST_ACTIVITY`

*Optional* `bool`, default value: `True`

---


## `DJANGO_CSP_DEFAULT_SRC`

*Optional* `list`, default value: `["'none'"]`

---


## `DJANGO_CSP_IMG_SRC`

*Optional* `list`, default value: `["'self'"]`

---


## `DJANGO_CSP_FONT_SRC`

*Optional* `list`, default value: `["'self'"]`

---


## `DJANGO_CSP_STYLE_SRC`

*Optional* `list`, default value: `["'self'"]`

---


## `DJANGO_CSP_FRAME_ANCESTORS`

*Optional* `list`, default value: `["'none'"]`

---


## `DJANGO_CSP_BASE`

*Optional* `list`, default value: `["'none'"]`

---


## `DJANGO_CSP_FORM_ACTION`

*Optional* `list`, default value: `["'self'"]`

---


## `DJANGO_CSP_INCLUDE_NONCE_IN`

*Optional* `list`, default value: `['script-src']`

---


## `DJANGO_CSP_CONNECT_SRC`

*Optional* `list`, default value: `["'self'"]`

---


## `DJANGO_CSP_BLOCK_ALL_MIXED_CONTENT`

*Optional* `bool`, default value: `True`

---


## `DJANGO_DEFAULT_RENDERER_CLASSES`

*Optional* `list`, default value: `['rest_framework.renderers.JSONRenderer']`

---


## `DJANGO_BROWSABLE_API`

*Optional* `bool`, default value: `False`

---


## `DJANGO_REST_FRAMEWORK`

*Optional* `dict`, default value: `{'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAdminUser'], 'DEFAULT_RENDERER_CLASSES': ['rest_framework.renderers.JSONRenderer'], 'EXCEPTION_HANDLER': 'drf_standardized_errors.handler.exception_handler'}`

---


## `DJANGO_TAGULOUS_SLUG_ALLOW_UNICODE`

*Optional* `bool`, default value: `True`

---


