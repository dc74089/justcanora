from django.urls import path

from aitutor.views import chat, assessment, moderation

urlpatterns = [
    path('', chat.chat_home, name='chat_home'),
    path('new', chat.chat_new_conversation, name='chat_new'),
    path('conversation', chat.chat_load_conversation, name='chat_conversation'),
    path('send', chat.chat_send_message, name='chat_send'),

    path('assessment/begin/<str:assessment_id>', assessment.start_assessment, name='chat_start_assessment'),
    path('assessment/conversation/<str:conversation_id>', assessment.assessment, name='chat_assessment'),
    path('assessment/conversation/<str:conversation_id>/partial', assessment.assessment_get_messages, name='chat_assessment_conversation'),
    path('assessment/send', assessment.assessment_send_message, name='chat_assessment_send'),
    path('assessment/results', assessment.assessment_results, name='chat_assessment_results'),
    path('assessment/results/full_convo', assessment.assessment_results_get_convo, name='chat_assessment_results_convo'),

    path('moderate', moderation.moderate, name='chat_moderate'),
    path('moderate/conversation', moderation.moderation_get_conversation, name='chat_moderate_get_conversation'),
]
