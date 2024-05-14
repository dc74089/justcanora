import json

from django.db import models
from django.db.models import SET_NULL


# Create your models here.
class Hunt(models.Model):
    name = models.TextField()
    final_password = models.TextField()
    riddles = models.ManyToManyField("Riddle", related_name="hunts", null=True, blank=True)

    def __str__(self):
        return self.name


class Kiosk(models.Model):
    hunt = models.ForeignKey(Hunt, related_name="kiosks", on_delete=models.CASCADE)
    location = models.TextField()
    state = models.TextField(default="{}")

    def get_state(self):
        return json.loads(self.state)

    def set_state(self, state):
        self.state = json.dumps(state)

    def __str__(self):
        return self.location


class Team(models.Model):
    hunt = models.ForeignKey("Hunt", on_delete=models.CASCADE)
    name = models.TextField()
    state = models.TextField(default="{}")
    solved = models.ManyToManyField("Riddle", related_name="+", null=True, blank=True)
    final_password_order = models.TextField()
    final_password_progression = models.IntegerField(default=0)

    def get_state(self):
        state = json.loads(self.state)
        state['letters'] = self.final_password_order[:self.final_password_progression]
        return state

    def set_state(self, state):
        self.state = json.dumps(state)

    def __str__(self):
        return self.name


class Riddle(models.Model):
    question = models.TextField()
    answer = models.TextField()

    def __str__(self):
        return self.question
