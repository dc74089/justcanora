import random
import string

from django.db import models

from app.models import Student
from justcanora import settings


class Wrapped(models.Model):
    student = models.OneToOneField(Student, on_delete=models.CASCADE, null=False, blank=False, primary_key=True)
    num_songs = models.IntegerField(null=True, blank=True)
    rank_songs = models.IntegerField(null=True, blank=True)
    num_songs_rejected = models.IntegerField(null=True, blank=True)
    num_assignments = models.IntegerField(null=True, blank=True)
    rank_assignments = models.IntegerField(null=True, blank=True)
    num_late = models.IntegerField(null=True, blank=True)
    rank_late = models.IntegerField(null=True, blank=True)
    num_canvas_minutes = models.IntegerField(null=True, blank=True)
    rank_canvas_minutes = models.IntegerField(null=True, blank=True)
    num_canvas_clicks = models.IntegerField(null=True, blank=True)
    rank_canvas_clicks = models.IntegerField(null=True, blank=True)
    robotics = models.BooleanField(default=False)
    personal_note = models.TextField(null=True, blank=True)

    def percentile_string(self, pct):
        if pct < 0.01:
            return "1%"
        elif pct < 0.02:
            return "2%"
        elif pct < 0.03:
            return "3%"
        elif pct < 0.04:
            return "4%"
        elif pct < 0.05:
            return "5%"
        elif pct < 0.1:
            return "10%"
        elif pct < 0.15:
            return "15%"
        elif pct < 0.2:
            return "20%"
        elif pct < 0.25:
            return "25%"
        elif pct < 0.30:
            return "30%"
        elif pct < 0.4:
            return "40%"

        return None

    def song_percentile(self):
        if self.rank_songs:
            return self.percentile_string(self.rank_songs / Wrapped.objects.count())

    def canvas_minutes_percentile(self):
        if self.rank_canvas_minutes:
            return self.percentile_string(self.rank_canvas_minutes / Wrapped.objects.count())

    def canvas_clicks_percentile(self):
        if self.rank_canvas_clicks:
            return self.percentile_string(self.rank_canvas_clicks / Wrapped.objects.count())

    def canvas_minutes_per_day(self):
        return self.num_canvas_minutes // 180

    def class_string(self):
        ps = False
        cs = False
        adv = False

        for course in self.student.courses.filter(year=settings.CURRENT_ACADEMIC_YEAR):
            print(course.type)
            if course.type == "CS1" or course.type == "CS2":
                cs = True

            if course.type == "advisory":
                adv = True

            if course.type == "speech":
                ps = True

        if ps and cs and adv:
            return "Computer Science, Public Speaking, and Advisory"
        elif ps and cs:
            return "Computer Science and Public Speaking"
        elif cs and adv:
            return "Computer Science and Advisory"
        elif ps and adv:
            return "Public Speaking and Advisory"
        elif ps:
            return "Public Speaking"
        elif cs:
            return "Computer Science"
        elif adv:
            return "Advisory"
        else:
            return "class"

    def __str__(self):
        return f"{self.student.name()}'s 2025 SY Wrapped"


def generate_wrapped_key():
    return ''.join(random.SystemRandom().choice(string.ascii_letters + string.digits) for _ in range(20))


class TeacherWrapped(models.Model):
    teacher_id = models.IntegerField(null=False, blank=False, unique=True, primary_key=True)
    key = models.CharField(max_length=50, null=False, blank=False, unique=True, default=generate_wrapped_key)
    email = models.EmailField(unique=True)
    name = models.TextField(null=False, blank=False)
    display_name = models.TextField(null=False, blank=False)
    num_announcements = models.IntegerField(null=True, blank=True)
    num_assignments = models.IntegerField(null=True, blank=True)
    num_graded = models.IntegerField(null=True, blank=True)
    num_late = models.IntegerField(null=True, blank=True)
    num_zeros = models.IntegerField(null=True, blank=True)
    num_canvas_minutes = models.IntegerField(null=True, blank=True)
    num_canvas_clicks = models.IntegerField(null=True, blank=True)
    kulaqua = models.BooleanField(default=False)
    nc = models.BooleanField(default=False)
    new_to_ccc = models.BooleanField(default=False)
    personal_note = models.TextField(null=True, blank=True)

    def canvas_minutes_per_day(self):
        return self.num_canvas_minutes // 180

    def fname(self):
        return self.name.split()[0]

    def __str__(self):
        return f"{self.name}'s 2025 SY Wrapped"