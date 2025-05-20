import json
import uuid

from django.db import models


class Agent(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    dev_message = models.TextField()
    photo = models.ImageField(upload_to="agent_photos", null=True, blank=True)


class Conversation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey("app.Student", on_delete=models.CASCADE, null=False, blank=False)
    agent = models.ForeignKey("Agent", on_delete=models.CASCADE, null=False, blank=False)
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

        return json.dumps(out)


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

    class Meta:
        ordering = ['-time']


class AgentMessage(Message):
    agent = models.ForeignKey("Agent", on_delete=models.CASCADE, null=False, blank=False)
    message_id = models.CharField(max_length=100, unique=True)


class UserMessage(Message):
    student = models.ForeignKey("app.Student", on_delete=models.CASCADE, null=False, blank=False)
