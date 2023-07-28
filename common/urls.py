from django.urls import path

from .views import index, auth

urlpatterns = [
    path('', index.index, name='index'),

    path('login', auth.login, name='login'),
    path('logout', auth.logout, name='logout'),
    path('auth/google', auth.google, name='google_callback'),

    path('dev', index.dev, name='dev'),
]
