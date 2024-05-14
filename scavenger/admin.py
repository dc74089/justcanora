from django.contrib import admin

from .models import Hunt, Riddle, Team

# Register your models here.
admin.site.register(Hunt)
admin.site.register(Riddle)
admin.site.register(Team)