from django.urls import path

from . import views

urlpatterns = [
    path('', views.create_team, name='scavenger-create-team'),
]
