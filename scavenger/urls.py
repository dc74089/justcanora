from django.urls import path

from . import views

urlpatterns = [
    path('', views.create_team, name='scavenger-create-team'),
    path('jointeam', views.join_team, name='scavenger-join-team'),
    path('team', views.team_home, name='scavenger-team-home'),
    path('team/state', views.get_team_state, name='scavenger-team-state'),
    path('team/answer', views.answer_question, name='scavenger-team-answer-question'),


    path('kiosk', views.kiosk, name='scavenger-kiosk'),
    path('kiosk/state', views.kiosk_state, name='scavenger-kiosk-state'),
]
