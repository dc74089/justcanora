from django.urls import path

from gaime.views import *

urlpatterns = [
    path('', index, name="gaime_index"),
    path('tv', tv, name="gaime_tv"),

    path('admin', admin, name="gaime_admin"),
    path('players', players, name="gaime_players"),
]
