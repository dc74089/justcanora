from django.urls import path

from wrapped import views

urlpatterns = [
    path('', views.wrapped, name='wrapped'),
    path('demo/', views.wrapped_demo, name='wrapped_demo'),
    path('teacher/demo/', views.wrapped_teacher_demo, name='wrapped_teacher_demo'),
    path('teacher/<str:key>', views.wrapped_teacher, name='wrapped_teacher'),
]