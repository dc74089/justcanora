from django.urls import path

from .views import index, auth, misc, admin, music, speech, curriculum, webserver, wrapped

urlpatterns = [
    path('', index.index, name='index'),

    path('login', auth.login, name='login'),
    path('logout', auth.logout, name='logout'),
    path('auth/google', auth.google, name='google_callback'),
    path('auth/spotify', auth.spotify_response, name='spotify_callback'),

    path('admin', admin.admin, name='admin'),
    path('admin/setflag', admin.set_flag, name='set_flag'),
    path('admin/rosters', admin.rosters, name='rosters'),
    path('admin/answers', admin.view_answers, name='datacollection_answers'),
    path('admin/music/queue', music.music_queue, name='music_queue'),
    path('admin/music/search', music.search_table, name='spotify_search'),
    path('admin/music/add', music.add_song, name='spotify_add'),
    path('admin/music/preview', music.queue_song, name='spotify_queue'),
    path('admin/music/deny', music.deny_song, name='spotify_deny'),

    path('speech/evals/view', speech.view_evals, name='speech_view_evals'),
    path('speech/evals/all', speech.all_evals, name='speech_all_evals'),

    path('music/nowplaying', music.get_now_playing, name='now_playing'),

    path('webserver/instructions', webserver.instructions, name='webserver_guide'),
    path('webserver/all_creds', webserver.all_table, name='webserver_all'),

    path('wrapped/2024', wrapped.wrapped2024, name='wrapped_2024'),
    path('wrapped/demo', wrapped.wrapped_demo, name='wrapped_2024_demo'),

    path('cn', curriculum.index),
    path('cn/dark', curriculum.index_dark),
    path('cn/bigqr', curriculum.big_qr),

    path('do', misc.misc_action, name='misc_action'),
    path('dev', index.dev, name='dev'),
]
