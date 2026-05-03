from django.urls import path

from wrapped import views

urlpatterns = [
    path('', views.wrapped, name='wrapped'),
    path('admin', views.admin, name='wrapped_admin'),
    path('<uuid:key>', views.wrapped_direct, name='wrapped_direct'),
    path('ranks', views.ranks, name='ranks'),
    path('demo/', views.wrapped_demo, name='wrapped_demo'),
    path('teacherdemo/', views.wrapped_teacher_demo, name='wrapped_teacher_demo'),
    path('generate/', views.generate_manual, name='wrapped_generate_manual'),
    path('studentdata/', views.student_data, name='wrapped_student_data'),
    path('teacherdata/', views.teacher_data, name='wrapped_teacher_data'),
    path('teacher/<str:key>', views.wrapped_teacher, name='wrapped_teacher'),
]