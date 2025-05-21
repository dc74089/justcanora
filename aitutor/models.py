import json
import uuid

from django.db import models
from django.utils import timezone


class Agent(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    dev_message = models.TextField()
    photo = models.ImageField(upload_to="agent_photos", null=True, blank=True)

    def __str__(self):
        return self.name


class Conversation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey("app.Student", on_delete=models.CASCADE, null=False, blank=False)
    agent = models.ForeignKey("Agent", on_delete=models.CASCADE, null=False, blank=False)
    summary = models.TextField(null=True, blank=True)
    course_id = models.IntegerField(null=True, blank=True)
    assignment_id = models.IntegerField(null=True, blank=True)
    locked = models.BooleanField(default=False)

    def get_last_message_id(self):
        return self.message_set.filter(role="agent").last().message_id

    def to_openai_json(self):
        out = []

        out.append({
            "role": "developer",
            "content": self.agent.dev_message
        })

        for message in self.message_set.all().order_by('time'):
            out.append({
                "role": "user" if message.is_user() else "assistant",
                "content": message.message
            })

        return out


    def info_for_summary(self):
        out = []

        for message in self.message_set.all().order_by('time'):
            out.append({
                "role": "user" if message.is_user() else "assistant",
                "content": message.message
            })

        return out


    def messages(self):
        return self.message_set.all()


    def user_facing_str(self):
        out = f"<b>Talking with {self.agent.name}</b>"

        if self.summary:
            out += f" about<br>{self.summary}"

        return out
    
    
    def last_message_ago(self):
        last_message = self.message_set.order_by('-time').first()
        if not last_message:
            return "No messages"

        now = timezone.now()
        diff = now - last_message.time

        minutes = diff.total_seconds() / 60
        hours = minutes / 60
        days = hours / 24

        if days >= 1:
            return f"{int(days)} days ago"
        elif hours >= 1:
            return f"{int(hours)} hours ago"
        elif minutes >= 1:
            return f"{int(minutes)} minutes ago"
        else:
            return "just now"

    def __str__(self):
        out = f"{self.student.name()} talking with {self.agent.name}"

        if self.course_id or self.assignment_id:
            out +=  f" about {self.course_id}::{self.assignment_id}"

        return out


class Message(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.CharField(max_length=10, choices=[('user', 'User'), ('agent', 'Agent')])
    conversation = models.ForeignKey("Conversation", on_delete=models.CASCADE, null=False, blank=False)
    message = models.TextField()
    time = models.DateTimeField(auto_now_add=True)

    def is_agent(self):
        return self.role == "agent"

    def is_user(self):
        return self.role == "user"

    def author(self):
        if self.is_agent():
            return self.conversation.agent.name
        else:
            return self.conversation.student.name()

    class Meta:
        ordering = ['-time']

    def __str__(self):
        return f"{str(self.conversation)}::{self.message}"


class AgentMessage(Message):
    agent = models.ForeignKey("Agent", on_delete=models.CASCADE, null=False, blank=False)
    message_id = models.CharField(max_length=100, unique=True)


class UserMessage(Message):
    student = models.ForeignKey("app.Student", on_delete=models.CASCADE, null=False, blank=False)
