"""
WSGI config for Backend project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/2.2/howto/deployment/wsgi/
"""

import os
import configparser
from django.core.wsgi import get_wsgi_application

if not os.environ.get("DJANGO_SETTINGS_MODULE"):
    parser = configparser.RawConfigParser()
    parser.read("/etc/dp-backend/backend.ini")
    for name, val in parser['mod_wsgi'].items():
        os.environ[name.upper()] = val

application = get_wsgi_application()
