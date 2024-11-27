from django.contrib import admin

from app.models import *

# Register your models here.
admin.site.register(Student)
admin.site.register(Course)
admin.site.register(MusicSuggestion)
admin.site.register(FeatureFlag)
admin.site.register(News)
admin.site.register(DataCollectionQuestion)
admin.site.register(DataCollectionAnswer)
admin.site.register(SpeechRubric)
admin.site.register(SpeechRating)
admin.site.register(WebserverCredential)
admin.site.register(Wrapped2025)
admin.site.register(TeacherWrapped2025)
admin.site.register(DanceRequestCategory)
admin.site.register(DanceRequest)