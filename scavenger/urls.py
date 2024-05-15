from django.urls import path

from .views import admin
from .views import views

urlpatterns = [
    path('', views.create_team, name='scavenger-create-team'),
    path('jointeam', views.join_team, name='scavenger-join-team'),
    path('team', views.team_home, name='scavenger-team-home'),
    path('team/state', views.get_team_state, name='scavenger-team-state'),
    path('team/answer', views.answer_question, name='scavenger-team-answer-question'),


    path('kiosk', views.kiosk, name='scavenger-kiosk'),
    path('kiosk/state', views.kiosk_state, name='scavenger-kiosk-state'),

    path('admin', admin.admin, name='scavenger-admin'),
    path('admin/table', admin.table, name='scavenger-admin-table'),
    path('admin/do', admin.do_action, name='scavenger-admin-action'),
]
