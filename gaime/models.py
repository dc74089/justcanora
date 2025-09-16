import uuid

from django.db import models

# Create your models here.

states = (
    ("welcome", "Welcome Screen"),
    ("intro", "Instructions"),
    ("tf", "True/False"),
    ("review", "Question Review"),
    ("results", "Final Results")
)


class Game(models.Model):
    state = models.CharField(max_length=30, choices=states)
    question = models.ForeignKey("Question", null=True, blank=True, on_delete=models.SET_NULL)


media_types = (
    ("image", "Image"),
    ("video", "Video"),
    ("text", "Text")
)


class Question(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    media_type=models.CharField(max_length=30, choices=media_types)
    image = models.ImageField()
    video = models.FileField()
    text = models.TextField()
    prompt = models.TextField()


groups = (
    ("1", "Tensor Titans"),
    ("2", "The Hidden Layers"),
    ("3", "Overfit & Ready"),
    ("4", "Cache Me If You Can")
)


class Player(models.Model):
    name = models.TextField()
    group = models.CharField(max_length=10, choices=groups)
    points = models.IntegerField()
