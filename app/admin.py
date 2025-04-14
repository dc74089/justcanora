from django.contrib import admin

from app.models import *

# Register your models here.
admin.site.register(Student)
admin.site.register(Course)
admin.site.register(MusicSuggestion)
admin.site.register(FeatureFlag)
admin.site.register(SpeechRubric)
admin.site.register(SpeechRating)
admin.site.register(WebserverCredential)
admin.site.register(DanceRequestCategory)
admin.site.register(DanceRequest)