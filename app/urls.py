from django.urls import path

from .views import index, auth, misc, admin

urlpatterns = [
    path('', index.index, name='index'),

    path('login', auth.login, name='login'),
    path('logout', auth.logout, name='logout'),
    path('auth/google', auth.google, name='google_callback'),

    path('admin', admin.admin, name='admin'),
    path('admin/setflag', admin.set_flag, name='set_flag'),
    path('admin/rosters', admin.rosters, name='rosters'),

    path('do', misc.misc_action, name='misc_action'),
    path('dev', index.dev, name='dev'),
]
