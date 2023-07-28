from django.urls import path

from .spotify import search as spotify_search
from .views import index, auth, misc, admin

urlpatterns = [
    path('', index.index, name='index'),

    path('login', auth.login, name='login'),
    path('logout', auth.logout, name='logout'),
    path('auth/google', auth.google, name='google_callback'),
    path('auth/spotify', auth.spotify_response, name='spotify_callback'),

    path('admin', admin.admin, name='admin'),
    path('admin/setflag', admin.set_flag, name='set_flag'),
    path('admin/rosters', admin.rosters, name='rosters'),
    path('admin/music/queue', admin.music_queue, name='music_queue'),
    path('admin/music/search', spotify_search.search, name='spotify_search'),

    path('do', misc.misc_action, name='misc_action'),
    path('dev', index.dev, name='dev'),
]
