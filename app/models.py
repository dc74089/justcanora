import json
import random
import re
import string

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.utils import timezone
from urllib3 import request


class FeatureFlag(models.Model):
    id = models.CharField(max_length=100, primary_key=True)
    enabled = models.BooleanField(default=False, null=False, blank=False)
    config = models.TextField(default='{}')

    class Meta:
        ordering = ['id']

    def __str__(self):
        return self.id

    def __bool__(self):
        return self.enabled

    def get_config(self):
        return json.loads(self.config)

    def write_config(self, config: dict):
        self.config = json.dumps(config)


class Student(models.Model):
    id = models.PositiveBigIntegerField(null=False, blank=False, primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True, related_name='student')
    fname = models.TextField(null=False, blank=False)
    lname = models.TextField(null=False, blank=False)
    picture = models.ImageField(null=True, blank=True, upload_to='propics')
    grade = models.IntegerField(null=True, blank=True)
    bday = models.DateField(null=True, blank=True)
    email = models.TextField(null=True, blank=True)
    should_show_entire_last_name = models.BooleanField(default=False)

    def full_name(self):
        return f"{self.fname} {self.lname}"

    def name(self):
        return f"{self.fname} {self.last_initial()}"

    def last_initial(self):
        if self.should_show_entire_last_name:
            return self.lname

        names = re.split("[, ]", self.lname)
        first_letters = [a[0] for a in names]
        return "".join(first_letters)

    def is_active(self, enforce_semester=False):
        if enforce_semester:
            return (
                    self.courses.filter(year=settings.CURRENT_ACADEMIC_YEAR, semester=settings.CURRENT_SEMESTER) |
                    self.courses.filter(year=settings.CURRENT_ACADEMIC_YEAR, name__contains="YR")
            ).exists()
        else:
            return self.courses.filter(year=settings.CURRENT_ACADEMIC_YEAR).exists()

    def all_courses_str(self):
        q = self.courses.filter(
            year=settings.CURRENT_ACADEMIC_YEAR,
            semester=settings.CURRENT_SEMESTER
        ) | self.courses.filter(
            year=settings.CURRENT_ACADEMIC_YEAR,
            name__contains="YR"
        )

        return "\n".join([
            c.name for c in q
        ])

    def has_web_credential(self):
        try:
            self.webservercredential
            return True
        except ObjectDoesNotExist:
            return False

    def __str__(self):
        return f"{self.fname} {self.lname} ({self.id})"

    def __bool__(self):
        return self.courses.exists()


class Course(models.Model):
    course_types = (
        ("advisory", "Advisory"),
        ("CS1", "Web Dev"),
        ("CS2", "Python"),
        ("speech", "Public Speaking"),
        ("team", "Robotics Team"),
        ("other", "Other")
    )

    academic_years = (
        ("23/24", "2023-24"),
        ("24/25", "2023-24"),
    )

    course_id = models.IntegerField(null=False, blank=False)
    section_id = models.IntegerField(null=False, blank=False)
    period = models.IntegerField(null=True, blank=True)
    semester = models.IntegerField(null=True, blank=True)
    year = models.CharField(max_length=100, choices=academic_years, default="24/25")
    name = models.TextField()
    students = models.ManyToManyField("Student", related_name="courses")
    type = models.CharField(max_length=100, choices=course_types, default="other")
    playlist_id = models.CharField(max_length=100, null=True, blank=True)

    def students_sorted(self):
        return self.students.all().exclude(grade__gt=8).order_by('fname')

    def short_name(self):
        return f"S{self.semester}P{self.period}"

    def music_suggestions(self):
        return MusicSuggestion.objects.filter(
            student__courses=self,
            investigated=False,
            for_playlist=True,
            is_null=False
        )

    def __str__(self):
        return self.name


class MusicSuggestion(models.Model):
    song = models.TextField(null=False, blank=False)
    artist = models.TextField(null=True, blank=True)
    student = models.ForeignKey("Student", on_delete=models.CASCADE)
    for_playlist = models.BooleanField()
    investigated = models.BooleanField(default=False)
    investigated_date = models.DateTimeField(null=True, blank=True)
    spotify_uri = models.CharField(max_length=100, null=True, blank=True)
    added = models.DateTimeField(auto_now_add=True)
    is_null = models.BooleanField(default=False, null=False, blank=False)
    is_rejected = models.BooleanField(default=False, null=False, blank=False)
    data = models.TextField(null=True, blank=True)

    def get_spotify_data(self, request):
        if self.data:
            return json.loads(self.data)
        else:
            from app.spotify import search

            data = search.get_by_uri(request, self.spotify_uri)

            self.data = json.dumps(data)
            self.save()

            return data

    def is_expired(self):
        if self.investigated_date:
            return timezone.now() > self.investigated_date + timezone.timedelta(days=30)
        else:
            return True

    def is_expiring_soon(self):
        if self.investigated_date:
            return not self.is_expired() and timezone.now() > self.investigated_date + timezone.timedelta(days=27)
        else:
            return False

    def __str__(self):
        if self.artist:
            return f"{str(self.student)} suggested {self.song} by {self.artist}{'*' if not self.investigated else ''}"
        else:
            return f"{str(self.student)} suggested {self.song}{'*' if not self.investigated else ''}"


class SpeechRubric(models.Model):
    speech = models.TextField(null=False, blank=False)
    rating_fields = models.TextField(default="[]")
    comment_fields = models.TextField(default="[]")
    available_to_view = models.BooleanField(default=False)

    def get_rating_fields(self):
        return json.loads(self.rating_fields)

    def get_comment_fields(self):
        return json.loads(self.comment_fields)

    def __str__(self):
        return self.speech


class SpeechRating(models.Model):
    author = models.ForeignKey("Student", null=True, on_delete=models.SET_NULL, related_name="given_ratings")
    speaker = models.ForeignKey("Student", on_delete=models.CASCADE, related_name="received_ratings")
    rubric = models.ForeignKey("SpeechRubric", on_delete=models.CASCADE)
    data = models.TextField()
    available_to_view = models.BooleanField(default=False)

    def set_data(self, data: dict):
        self.data = json.dumps(data)

    def get_data(self):
        return json.loads(self.data)

    def get_ratings(self):
        return self.get_data().get("rating")

    def get_comments(self):
        return self.get_data().get("comment")

    def __str__(self):
        return f"{self.author.name()} evaluating {self.speaker.name()} on {self.rubric.speech}"


class News(models.Model):
    student = models.ForeignKey('Student', on_delete=models.CASCADE)
    news = models.TextField()
    added = models.DateTimeField(auto_now_add=True)
    is_null = models.BooleanField(default=False, null=False, blank=False)

    class Meta:
        verbose_name_plural = "News"

    def __str__(self):
        return f"{self.student.name()}'s news from {str(self.added.date())}"


class DataCollectionQuestion(models.Model):
    question = models.TextField()
    courses = models.ManyToManyField('Course')
    is_open = models.BooleanField(default=True, null=False, blank=False)

    def __str__(self):
        return self.question


class DataCollectionAnswer(models.Model):
    student = models.ForeignKey('Student', on_delete=models.CASCADE)
    question = models.ForeignKey('DataCollectionQuestion', on_delete=models.CASCADE, related_name='answers')
    answer = models.TextField()

    def __str__(self):
        return f"{self.student} answered {self.question}"


class WebserverCredential(models.Model):
    student = models.OneToOneField("Student", on_delete=models.SET_NULL, null=True, blank=True)
    directory = models.TextField(null=True, blank=True)
    password = models.TextField(null=True, blank=True)
    uid = models.IntegerField(null=False, blank=False, unique=True)
    shark = models.BooleanField(default=False, null=False, blank=False)

    def username(self):
        return self.directory.split("/")[-1] if self.directory else None

    @classmethod
    def gen_password(cls):
        return ''.join(random.SystemRandom().choice(string.ascii_letters + string.digits) for _ in range(20))

    @classmethod
    def gen_uid(cls, student):
        if student.id == 0:
            raise Exception()

        id = student.id

        while True:
            if id > 1000 and not WebserverCredential.objects.filter(uid=id).exists():
                return id

            id *= 10

    def __str__(self):
        return f"Webserver Creds for {self.student.full_name()} (/{self.directory}; {self.uid})"


class Wrapped2025(models.Model):
    student = models.OneToOneField("Student", on_delete=models.CASCADE, null=False, blank=False, primary_key=True)
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
    personal_note = models.TextField(null=True, blank=True)

    def percentile_string(self, pct):
        if pct < 0.01:
            return "1%"
        elif pct < 0.05:
            return "5%"
        elif pct < 0.1:
            return "10%"
        elif pct < 0.2:
            return "20%"
        elif pct < 0.25:
            return "25%"

        return None

    def song_percentile(self):
        if self.rank_songs:
            return self.percentile_string(self.rank_songs / Wrapped2025.objects.count())

    def canvas_minutes_percentile(self):
        if self.rank_canvas_minutes:
            return self.percentile_string(self.rank_canvas_minutes / Wrapped2025.objects.count())

    def canvas_clicks_percentile(self):
        if self.rank_canvas_clicks:
            return self.percentile_string(self.rank_canvas_clicks / Wrapped2025.objects.count())

    def canvas_minutes_per_day(self):
        return self.num_canvas_minutes // 180

    def class_string(self):
        ps = False
        cs = False
        adv = False

        for course in self.student.courses.all():
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


class TeacherWrapped2025(models.Model):
    teacher_id = models.IntegerField(null=False, blank=False, unique=True, primary_key=True)
    email = models.EmailField(unique=True)
    name = models.TextField(null=False, blank=False)
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


class DanceRequestCategory(models.Model):
    name = models.TextField()

    def __str__(self):
        return self.name


class DanceRequest(models.Model):
    requestor = models.TextField()
    category = models.ForeignKey(DanceRequestCategory, on_delete=models.CASCADE)
    spotify_uri = models.CharField(max_length=255)
    data = models.TextField(null=True, blank=True)

    def get_spotify_data(self, request):
        if self.data:
            return json.loads(self.data)
        elif request:
            from app.spotify import search

            data = search.get_by_uri(request, self.spotify_uri)

            self.data = json.dumps(data)
            self.save()

            return data
        else:
            return None


    def __str__(self):
        return f"{self.requestor}: {self.category}"
