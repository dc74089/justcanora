"""
ASGI config for justcanora project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os

import socketio

from django.core.asgi import get_asgi_application

from justcanora.sio import sio

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'justcanora.settings')

application = socketio.ASGIApp(sio, get_asgi_application())
