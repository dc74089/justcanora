from django.urls import path

from aitutor import views

urlpatterns = [
    path('', views.conversation_select, name='conversation_select'),
    path('new', views.conversation_start, name='conversation_start'),
    path('conversation/<str:conv_id>', views.conversation, name='conversation'),
    path('conversation/<str:conv_id>/send', views.send_message, name='conversation_send_message'),
]