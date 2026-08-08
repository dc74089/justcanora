import json
import random
import re
import string

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.utils import timezone


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

    def is_active_enforcing_semester(self):
        return self.is_active(enforce_semester=True)

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

    class Meta:
        ordering = ['fname', 'lname']


class Course(models.Model):
    course_types = (
        ("advisory", "Advisory"),
        ("CS1", "Web Dev"),
        ("CS2", "Python"),
        ("APCSA", "AP Computer Science A"),
        ("speech", "Public Speaking"),
        ("team", "Robotics Team"),
        ("other", "Other")
    )

    academic_years = (
        ("23/24", "2023-24"),
        ("24/25", "2024-25"),
        ("25/26", "2025-26"),
        ("26/27", "2026-27"),
    )

    course_id = models.IntegerField(null=False, blank=False)
    section_id = models.IntegerField(null=False, blank=False)
    period = models.IntegerField(null=True, blank=True)
    semester = models.IntegerField(null=True, blank=True)
    year = models.CharField(max_length=100, choices=academic_years, default="26/27")
    name = models.TextField()
    students = models.ManyToManyField("Student", related_name="courses")
    type = models.CharField(max_length=100, choices=course_types, default="other")
    playlist_id = models.CharField(max_length=100, null=True, blank=True)

    def students_sorted(self):
        return self.students.all().exclude(grade__gt=12).order_by('fname')

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
        if self.semester:
            return f"{self.get_year_display()} P{self.period} - {self.get_type_display()} (S{self.semester})"

        return f"{self.get_year_display()} P{self.period} - {self.get_type_display()}"

    class Meta:
        ordering = ['year', 'semester', 'period']


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


class ApprovedSong(models.Model):
    spotify_uri = models.CharField(max_length=100, unique=True)
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


class SpeechRubric(models.Model):
    # The peer-eval card is driven by one flag: enabled == "collecting", and its
    # config names the rubric students are evaluating right now.
    ACTIVE_FLAG = "card_speech"

    speech = models.TextField(null=False, blank=False)
    rating_fields = models.TextField(default="[]")
    comment_fields = models.TextField(default="[]")
    available_to_view = models.BooleanField(default=False)

    def get_rating_fields(self):
        return json.loads(self.rating_fields)

    def get_comment_fields(self):
        return json.loads(self.comment_fields)

    @classmethod
    def get_active(cls):
        """The rubric students are being asked to fill out, or None if collection is off."""
        flag, _ = FeatureFlag.objects.get_or_create(id=cls.ACTIVE_FLAG)

        if not flag: return None

        config = flag.get_config()
        rubric = cls.objects.filter(id=config.get("rubric_id")).first()

        if not rubric:  # older configs only stored the speech title
            rubric = cls.objects.filter(speech=config.get("rubric_name")).first()

        return rubric

    @classmethod
    def set_active(cls, rubric):
        """Point the peer-eval card at a rubric, or pass None to stop collecting."""
        flag, _ = FeatureFlag.objects.get_or_create(id=cls.ACTIVE_FLAG)

        config = flag.get_config()
        config["rubric_id"] = rubric.id if rubric else None
        config["rubric_name"] = rubric.speech if rubric else None

        flag.write_config(config)
        flag.enabled = rubric is not None
        flag.save()

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


def gen_web_password():
    """A 20-char password students paste into their sftp.json."""
    return ''.join(random.SystemRandom().choice(string.ascii_letters + string.digits) for _ in range(20))


class WebserverCredential(models.Model):
    """A student's personal HestiaCP account: <username>.lhpscs.com, behind
    the shared mscs/mscs basic-auth prompt."""
    student = models.OneToOneField("Student", on_delete=models.SET_NULL, null=True, blank=True)
    username = models.TextField(null=True, blank=True)  # Hestia login == email prefix
    password = models.TextField(null=True, blank=True)  # stored plaintext for sftp.json
    provisioned_at = models.DateTimeField(null=True, blank=True)
    ssl_installed = models.BooleanField(default=False, null=False)

    @property
    def subdomain(self):
        return f"{self.username}.{settings.HESTIA_BASE_DOMAIN}" if self.username else None

    @property
    def url(self):
        return f"https://{self.subdomain}" if self.username else None

    @property
    def remote_path(self):
        return f"/web/{self.subdomain}/public_html" if self.username else None

    @classmethod
    def gen_password(cls):
        return gen_web_password()

    def __str__(self):
        who = self.student.full_name() if self.student else "unknown"
        return f"Webserver Creds for {who} ({self.subdomain})"


class SharkProject(models.Model):
    """A shark-tank group project: a real registered domain (its own DNS + LE
    cert), shared by 2-4 students via one group login. No basic auth.
    Identified by period-group, e.g. 1-4."""
    name = models.TextField()
    domain = models.TextField(null=True, blank=True)  # real registered domain
    members = models.ManyToManyField("Student", blank=True, related_name="shark_projects")
    username = models.TextField(null=True, blank=True)  # shared Hestia group login
    password = models.TextField(null=True, blank=True)
    year = models.CharField(max_length=100, choices=Course.academic_years, default="26/27")
    semester = models.IntegerField(null=True, blank=True)
    period = models.IntegerField(null=True, blank=True)
    group_number = models.IntegerField(null=True, blank=True)
    provisioned_at = models.DateTimeField(null=True, blank=True)
    ssl_installed = models.BooleanField(default=False, null=False)

    def label(self):
        if self.period is not None and self.group_number is not None:
            return f"{self.period}-{self.group_number}"
        return self.name

    @property
    def url(self):
        return f"https://{self.domain}" if self.domain else None

    @property
    def remote_path(self):
        return f"/web/{self.domain}/public_html" if self.domain else None

    @classmethod
    def gen_password(cls):
        return gen_web_password()

    def __str__(self):
        return f"Shark Project {self.label()} ({self.domain or 'no domain'})"


class HelpRequest(models.Model):
    student = models.ForeignKey("Student", on_delete=models.CASCADE)
    reason = models.TextField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    satisfied = models.BooleanField(default=False, null=False)

    def __str__(self):
        return f"{self.student.full_name()} needs help with {self.reason} ({self.timestamp})"


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
