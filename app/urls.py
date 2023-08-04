from django.urls import path

from .views import index, auth, misc, admin, music

urlpatterns = [
    path('', index.index, name='index'),

    path('login', auth.login, name='login'),
    path('logout', auth.logout, name='logout'),
    path('auth/google', auth.google, name='google_callback'),
    path('auth/spotify', auth.spotify_response, name='spotify_callback'),

    path('admin', admin.admin, name='admin'),
    path('admin/setflag', admin.set_flag, name='set_flag'),
    path('admin/rosters', admin.rosters, name='rosters'),
    path('admin/music/queue', music.music_queue, name='music_queue'),
    path('admin/music/edit', music.edit_playlist, name='music_edit_playlist'),
    path('admin/music/search', music.search_table, name='spotify_search'),
    path('admin/music/add', music.add_song, name='spotify_add'),

    path('music/nowplaying', music.get_now_playing, name='now_playing'),

    path('do', misc.misc_action, name='misc_action'),
    path('dev', index.dev, name='dev'),
]
