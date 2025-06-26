from django.urls import path

from aitutor import views

urlpatterns = [
    path('', views.chat_home, name='chat_home'),
    path('new', views.chat_new_conversation, name='chat_new'),
    path('conversation', views.chat_load_conversation, name='chat_conversation'),
    path('send', views.chat_send_message, name='chat_send'),

    path('assessment/begin/<str:assessment_id>', views.start_assessment, name='chat_start_assessment'),
    path('assessment/conversation/<str:conversation_id>', views.assessment, name='chat_assessment'),
    path('assessment/conversation/<str:conversation_id>/partial', views.assessment_get_messages, name='chat_assessment_conversation'),
    path('assessment/send', views.assessment_send_message, name='chat_assessment_send'),

    path('moderate', views.moderate, name='chat_moderate'),
    path('moderate/conversation', views.moderation_get_conversation, name='chat_moderate_get_conversation'),
]