import json
import re

from django.contrib.auth.models import User
from django.db import models


class FeatureFlag(models.Model):
    id = models.CharField(max_length=100, primary_key=True)
    enabled = models.BooleanField(default=True, null=False, blank=False)
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

    def __str__(self):
        return f"{self.fname} {self.lname} ({self.id})"

    def __bool__(self):
        return self.courses.exists()


class PicRequest(models.Model):
    student = models.ForeignKey('Student', on_delete=models.CASCADE)
    picture = models.ImageField(upload_to='requested')
    approved = models.BooleanField(null=True, blank=True)


class Course(models.Model):
    course_types = (
        ("advisory", "Advisory"),
        ("CS1", "CS 1"),
        ("CS2", "CS 2"),
        ("speech", "Public Speaking"),
        ("team", "Robotics Team"),
        ("other", "Other")
    )

    academic_years = (
        ("23/24", "2023-24"),
    )

    course_id = models.IntegerField(null=False, blank=False)
    section_id = models.IntegerField(null=False, blank=False)
    period = models.IntegerField(null=True, blank=True)
    semester = models.IntegerField(null=True, blank=True)
    year = models.CharField(max_length=100, choices=academic_years, default="23/24")
    name = models.TextField()
    students = models.ManyToManyField("Student", related_name="courses", null=True, blank=True)
    type = models.CharField(max_length=100, choices=course_types, default="other")

    def students_sorted(self):
        return self.students.all().order_by('fname')

    def __str__(self):
        return self.name


class MusicSuggestion(models.Model):
    song = models.TextField(null=False, blank=False)
    artist = models.TextField(null=True, blank=True)
    student = models.ForeignKey("Student", on_delete=models.CASCADE)
    for_playlist = models.BooleanField()
    investigated = models.BooleanField(default=False)
    added = models.DateTimeField(auto_now_add=True)
    is_null = models.BooleanField(default=False, null=False, blank=False)

    def __str__(self):
        if self.artist:
            return f"{str(self.student)} suggested {self.song} by {self.artist}{'*' if not self.investigated else ''}"
        else:
            return f"{str(self.student)} suggested {self.song}{'*' if not self.investigated else ''}"