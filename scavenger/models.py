import json

from django.db import models
from django.db.models import SET_NULL


# Create your models here.
class Hunt(models.Model):
    name = models.TextField()
    final_password = models.TextField()
    riddles = models.ManyToManyField("Riddle", related_name="hunts", blank=True)

    def __str__(self):
        return self.name


class Kiosk(models.Model):
    hunt = models.ForeignKey(Hunt, related_name="kiosks", on_delete=models.CASCADE)
    location = models.TextField()
    state = models.TextField(default="{}")
    active = models.BooleanField(default=True)

    def get_state(self):
        return json.loads(self.state)

    def get_state_display(self):
        state = self.get_state()
        return state["state"]

    def set_state(self, state):
        self.state = json.dumps(state)

    def set_state_qr(self):
        state = self.get_state()
        state['state'] = 'qr'
        self.set_state(state)
        self.save()

    def set_state_message(self, message):
        state = self.get_state()
        state['state'] = "message"
        state['message'] = message
        self.set_state(state)
        self.save()


    def __str__(self):
        return self.location


class Team(models.Model):
    hunt = models.ForeignKey("Hunt", on_delete=models.CASCADE)
    name = models.TextField()
    state = models.TextField(default="{}")
    destination = models.ForeignKey("Kiosk", related_name="teams_targeting", on_delete=models.SET_NULL, null=True, blank=True)
    solved = models.ManyToManyField("Riddle", related_name="+", blank=True)
    final_password_order = models.TextField()
    final_password_progression = models.IntegerField(default=0)

    def get_state(self):
        state = json.loads(self.state)
        state['letters'] = self.final_password_order[:self.final_password_progression]
        return state

    def get_state_display(self):
        state = self.get_state()
        return state["state"]

    def set_state(self, state):
        self.state = json.dumps(state)

    def set_state_message(self, message):
        state = json.loads(self.state)
        state['state'] = "message"
        state['message'] = message
        self.set_state(state)
        self.save()

    def set_state_riddle(self, riddle_id):
        state = json.loads(self.state)
        state['state'] = "entry"
        state['riddle'] = riddle_id
        self.set_state(state)
        self.save()

    def set_state_qr(self, location):
        state = json.loads(self.state)
        state['state'] = "qr"
        state['location'] = location
        self.set_state(state)
        self.save()

    def set_state_final(self):
        state = json.loads(self.state)
        state['state'] = "final"
        self.set_state(state)
        self.save()

    def set_new_destination(self, destination: Kiosk):
        self.destination = destination
        self.save()
        self.set_state_qr(destination.location)
        self.save()

    def send_popup(self, message):
        state = self.get_state()
        state['popup'] = message
        self.set_state(state)
        self.save()

    def acknowledge_popup(self):
        state = self.get_state()

        if 'popup' in state:
            del state['popup']

        self.set_state(state)
        self.save()

    def __str__(self):
        return self.name


class Riddle(models.Model):
    question = models.TextField()
    answer = models.TextField()

    def __str__(self):
        return self.question
