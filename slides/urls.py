from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='slides_index'),
    path('<str:module>/<int:lesson>', views.slides, name='slides'),
]