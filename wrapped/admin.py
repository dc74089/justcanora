from django.contrib import admin

from wrapped.models import Wrapped, TeacherWrapped

# Register your models here.
admin.site.register(Wrapped)
admin.site.register(TeacherWrapped)