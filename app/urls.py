from django.urls import path

from .views import index, auth, misc, admin, music, speech, curriculum, webserver, wrapped, jetbrains, dance

urlpatterns = [
    path('', index.index, name='index'),

    path('login/', auth.login, name='login'),
    path('logout/', auth.logout, name='logout'),
    path('auth/google', auth.google, name='google_callback'),
    path('auth/spotify', auth.spotify_response, name='spotify_callback'),
    path('auth/jetbrains/userdata', jetbrains.userdata, name='jetbrains_userdata'),

    path('admin/', admin.admin, name='admin'),
    path('admin/setflag/', admin.set_flag, name='set_flag'),
    path('admin/rosters/', admin.rosters, name='rosters'),
    path('admin/music/queue/', music.music_queue, name='music_queue'),
    path('admin/music/search/', music.search_table, name='spotify_search'),
    path('admin/music/add/', music.add_song, name='spotify_add'),
    path('admin/music/preview/', music.queue_song, name='spotify_queue'),
    path('admin/music/deny/', music.deny_song, name='spotify_deny'),

    path('speech/evals/view/', speech.view_evals, name='speech_view_evals'),
    path('speech/evals/all/', speech.all_evals, name='speech_all_evals'),

    path('music/nowplaying/', music.get_now_playing, name='now_playing'),
    path('music/nowplaying/json/', music.get_now_playing_json, name='now_playing_json'),
    path('music/next/json/', music.get_next_song_json, name='now_playing_json'),
    path('music/playpause/', music.do_play_pause, name='now_playing_json'),
    path('music/skiptrack/', music.do_skip, name='skip_track'),

    path('webserver/instructions/', webserver.instructions, name='webserver_guide'),
    path('webserver/all_creds/', webserver.all_table, name='webserver_all'),

    path('pycharm/instructions/', jetbrains.setup_instructions, name='jetbrains_setup_instructions'),

    path('wrapped/', wrapped.wrapped, name='wrapped'),
    path('wrapped/demo/', wrapped.wrapped_demo, name='wrapped_demo'),
    path('wrapped/teacher/<str:key>', wrapped.wrapped_teacher, name='wrapped_teacher'),
    path('wrapped/teacher/demo/', wrapped.wrapped_teacher_demo, name='wrapped_teacher_demo'),

    path('cn/', curriculum.index),
    path('cn/bigqr/', curriculum.big_qr),

    path('dance', dance.dance_index, name='dance_index'),
    path('dance/search', dance.dance_search, name='dance_search'),
    path('dance/choose', dance.dance_choose, name='dance_choose'),
    path('dance/results', dance.dance_view, name='dance_view'),

    path('robotics', misc.redirect_robotics),
    path('8ba10e6f-748f-4599-929c-a83585ef8869', misc.back_to_work),

    path('do/', misc.misc_action, name='misc_action'),
    path('dev/', index.dev, name='dev'),
]
