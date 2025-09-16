"""
WSGI config for justcanora project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/
"""

import os

import socketio

from django.core.wsgi import get_wsgi_application

from justcanora.sio import sio

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'justcanora.settings')

application = socketio.WSGIApp(sio, get_wsgi_application())
