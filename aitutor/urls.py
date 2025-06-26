from django.urls import path

from aitutor import views

urlpatterns = [
    path('', views.chat_home, name='chat_home'),
    path('new', views.chat_new_conversation, name='chat_new'),
    path('conversation', views.chat_load_conversation, name='chat_conversation'),
    path('send', views.chat_send_message, name='chat_send'),
]