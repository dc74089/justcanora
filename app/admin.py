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


@admin.register(SharkProject)
class SharkProjectAdmin(admin.ModelAdmin):
    list_display = ("label", "name", "domain", "year", "semester", "provisioned_at", "ssl_installed")
    list_filter = ("year", "semester", "period", "ssl_installed")
    search_fields = ("name", "domain", "username")
    filter_horizontal = ("members",)
admin.site.register(DanceRequestCategory)
admin.site.register(DanceRequest)
admin.site.register(HelpRequest)
