from django.urls import path

from gaime.views import *

urlpatterns = [
    path('', index, name="gaime_index"),
]
