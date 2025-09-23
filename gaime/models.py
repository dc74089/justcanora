import uuid

from django.db import models

# Create your models here.

states = (
    ("title", "Welcome Screen"),
    ("instructions", "Instructions"),
    ("question", "Question"),
    ("review", "Answer"),
    ("scores", "Leaderboard"),
    ("results", "Final Results")
)


class Game(models.Model):
    state = models.CharField(max_length=30, choices=states)
    question = models.ForeignKey("Question", null=True, blank=True, on_delete=models.SET_NULL)
    teams = models.BooleanField(default=True)


media_types = (
    ("image", "Image"),
    ("video", "Video"),
    ("text", "Text")
)


class Question(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    media_type=models.CharField(max_length=30, choices=media_types)
    image = models.ImageField(null=True, blank=True)
    video = models.FileField(null=True, blank=True)
    text = models.TextField(null=True, blank=True)
    prompt = models.TextField(null=True, blank=True)
    is_ai = models.BooleanField()
    used = models.BooleanField(default=False)


    def __str__(self):
        return f"{self.prompt}" if self.prompt else f"{self.id}"


groups = (
    ("1", "Tensor Titans"),
    ("2", "The Hidden Layers"),
    ("3", "Overfit & Ready"),
    ("4", "Cache Me If You Can")
)


class Player(models.Model):
    name = models.TextField()
    group = models.CharField(max_length=10, choices=groups)
    points = models.IntegerField(default=0)

    def first_name(self):
        return self.name.split(" ")[0]

    def __str__(self):
        return f"{self.name}"
