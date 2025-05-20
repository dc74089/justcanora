from django.urls import path

from aitutor import views

urlpatterns = [
    path('', views.conversation_select, name='conversation_select'),
    path('conversation/<str:conv_id>', views.conversation, name='conversation'),
]