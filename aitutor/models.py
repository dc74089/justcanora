import datetime
import json
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class Agent(models.Model):
    name = models.CharField(max_length=100)
    language = models.CharField(max_length=100, choices=(("python", "Python"), ("java", "Java"), ("html", "HTML/CSS"), ("na", "N/A" )))
    description = models.TextField()
    dev_message = models.TextField()
    photo = models.ImageField(upload_to="agent_photos", null=True, blank=True)
    hidden = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} ({self.get_language_display()})"

    @classmethod
    def get_assessment_agent(cls):
        return cls.objects.get_or_create(name="Quick Check", language="na")[0]


class Conversation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey("app.Student", on_delete=models.CASCADE, null=False, blank=False)
    agent = models.ForeignKey("Agent", on_delete=models.CASCADE, null=False, blank=False)
    summary = models.TextField(null=True, blank=True)
    course_id = models.IntegerField(null=True, blank=True)
    assignment_id = models.IntegerField(null=True, blank=True)
    locked = models.BooleanField(default=False)
    lock_reason = models.TextField(null=True, blank=True)

    def get_last_message_id(self):
        return self.message_set.filter(role="agent").last().message_id

    def to_claude_messages(self, student=None):
        system = self.agent.dev_message

        if student:
            system += f"\n\nYou are speaking with a student named {student.fname}."

        messages = []
        for message in self.message_set.all().order_by('time'):
            messages.append({
                "role": "user" if message.is_user() else "assistant",
                "content": message.message
            })

        return system, messages


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


    def has_strike(self):
        return Strike.objects.filter(conversation=self).exists()


    def user_facing_str(self):
        out = f"Talking with <b>{self.agent.name}</b>"

        if self.summary:
            out += f"<br>about <b>{self.summary}</b>"

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

        if days == 1:
            return "1 day ago"
        elif days >= 1:
            return f"{int(days)} days ago"
        elif hours == 1:
            return "1 hour ago"
        elif hours >= 1:
            return f"{int(hours)} hours ago"
        elif minutes == 1:
            return "1 minute ago"
        elif minutes >= 1:
            return f"{int(minutes)} minutes ago"
        else:
            return "just now"

    def __str__(self):
        out = f"{self.student.name()} talking with {self.agent.name}"

        if self.course_id or self.assignment_id:
            out +=  f" about {self.course_id}::{self.assignment_id}"

        return out


class Strike(models.Model):
    student = models.ForeignKey("app.Student", on_delete=models.CASCADE, null=False, blank=False)
    conversation = models.ForeignKey("Conversation", on_delete=models.SET_NULL, null=True, blank=True)
    reason = models.TextField(null=False, blank=False)
    time = models.DateTimeField(auto_now_add=True)

    @classmethod
    def is_banned(cls, student):
        week_ago = timezone.now() - datetime.timedelta(days=7)
        if Strike.objects.filter(student=student, time__gt=week_ago).count() >= 3:
            return True
        if Strike.objects.filter(student=student).count() >= 5:
            return True

        return False

    def __str__(self):
        return f"{self.student.name()} has been striked for {self.reason}"


class Assessment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    short_name = models.CharField(max_length=100, unique=True)
    course = models.ForeignKey("app.Course", on_delete=models.CASCADE, null=False, blank=False)
    canvas_assignment_id = models.IntegerField(null=False, blank=False)
    prompt = models.TextField(null=False, blank=False)

    # Course-specific framing injected into the assessment agent's dev message
    # (see AssessmentConversation.to_claude_messages). Keyed by Course.type so a
    # Python or web-dev assessment isn't told it's assessing AP CSA.
    COURSE_CONTEXTS = {
        "APCSA": "a student in AP Computer Science A. Your assessment aligns with "
                 "the College Board's AP CSA curriculum and focuses on Java programming.",
        "CS2": "a student in Computer Science 2, a Python programming course.",
        "CS1": "a student in Web Development, an introductory HTML and CSS course.",
    }

    def course_context(self):
        return self.COURSE_CONTEXTS.get(self.course.type, "a computer science student.")

    def __str__(self):
        return f"{self.short_name} ({self.course.name})"


class AssessmentConversation(Conversation):
    assessment = models.ForeignKey("Assessment", on_delete=models.CASCADE, null=False, blank=False)
    credit_awarded = models.BooleanField(default=False)
    understanding_score = models.IntegerField(null=True, blank=True)
    feedback = models.TextField(null=True, blank=True)

    def score_as_percent(self):
        if self.understanding_score is None:
            return 0
        else:
            return self.understanding_score * 100 / 5

    def to_claude_messages(self):
        dir = settings.BASE_DIR / "aitutor/agents/assessment"
        with open(dir / 'base.txt', 'r') as f:
            dev_msg = f.read()

        dev_msg = dev_msg.replace("%%COURSE_CONTEXT%%", self.assessment.course_context())
        dev_msg = dev_msg.replace("-----", self.assessment.prompt)

        messages = []
        for message in self.message_set.all().order_by('time'):
            messages.append({
                "role": "user" if message.is_user() else "assistant",
                "content": message.message
            })

        return dev_msg, messages


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
