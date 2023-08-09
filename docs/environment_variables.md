# Environment Variables

## Django

- [SECRET_KEY](https://docs.djangoproject.com/en/4.2/ref/settings/#allowed-hosts) is the secret key django will use. App defaults to "development_key" if not set. Should be unique in production. 
- [DEBUG](https://docs.djangoproject.com/en/4.2/ref/settings/#debug) turns [Django's debug mode] on/off. Defaults automatically to 1. Should be set to 0 in production.
- [ALLOWED_HOSTS](https://docs.djangoproject.com/en/4.2/ref/settings/#allowed-hosts) defaults automatically to '*'. But if you want to define certain hosts, they need to seperated by `,`. For example, `127.0.0.1,localhost`.
- [TRUSTED_ORIGINS](https://docs.djangoproject.com/en/4.2/ref/settings/#csrf-trusted-origins) is needed on production. Set it as the same as the domain. 
- [STATIC_ROOT](https://docs.djangoproject.com/en/4.2/ref/settings/#static-root) should be set as "/vol/web/static".
- [MEDIA_ROOT](https://docs.djangoproject.com/en/4.2/ref/settings/#media-root) should be set as "/vol/web/media".

## Database

- DB_HOST is the host of the database (should be set to "db" because mariadb container is called that)
- DB_NAME is the name of the database. 
- DB_USER is the name of the database user.
- DB_PASSWORD is the password for the user. 
- DB_ROOT_PASSWORD is the root password for the database. 

## Email
- EMAIL_BACKEND defines the email backend django will use. In development, it is usually set as `django.core.mail.backends.console.EmailBackend` so that the emails go to the logs/terminal.
- DEFAULT_FROM_EMAIL is the default sender email. Not needed development enviroment's console email.
- SENDGRID_API_KEY is the api key for the sendgrid service (used on staging and prod)

## ORCID

- ORCID_CLIENT_ID is client id for the orcid authentication. ORCID OAuth will not work without it. 
- ORCID_SECRET is secret for the orcid authentication. ORCID OAuth will not work without it.

## Site

- SITE_NAME is the name for the website. It can be set as "Cradle of Humanity".
- SITE_DOMAIN is the domain for the website. In development it can be set as "localhost:8000".

## PhpMyAdmin

- PMA_UPLOAD_LIMIT sets the maximum upload file size in for PMA in production.
- PMA_MEMORY_LIMIT sets the memory limit for PMA in production.

## Docker Container Initialization
- DJANGO_SUPERUSER_USERNAME is the username the django container uses to create a superuser at startup.
- DJANGO_SUPERUSER_PASSWORD is the password the django container uses to create a superuser at startup.
- DJANGO_SUPERUSER_EMAIL is the email the django container uses to create a superuser at startup.

## Docker Compose
- [COMPOSE_FILE](https://docs.docker.com/compose/environment-variables/envvars/#compose_file) can  be used to specify the default compose file when running docker compose.
