"""Tests for the tutor's access enforcement and its failure handling.

These cover the two things that are easiest to regress silently: rules that used
to live only in a template (so a stale tab bypassed them), and the behaviour when
a model call fails (which must never cost a student a strike or their work).
"""

from itertools import count
from unittest.mock import MagicMock, patch

import httpx
from anthropic import APIConnectionError
from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from app.models import Course, FeatureFlag, Student
from aitutor.models import Agent, Assessment, AssessmentConversation, Conversation, Message, Strike
from aitutor.utils import claude
from aitutor.utils.claude import AgentResponse, AssessmentAgentResponse, TransientAgentError
from aitutor.utils.context import context_processor
from aitutor.utils.enrollment import COURSE_TYPE_TO_FLAG, tutor_languages


def enable_tutor(*course_types):
    """Set the per-course tutor flags, switching every other one off."""
    for ctype, flag_id in COURSE_TYPE_TO_FLAG.items():
        FeatureFlag.objects.update_or_create(id=flag_id, defaults={"enabled": ctype in course_types})


def make_student(student_id=1, fname="Ada", course_types=("CS2",), enable_flags=True):
    user = User.objects.create_user(username=f"student{student_id}", password="pw")
    student = Student.objects.create(id=student_id, user=user, fname=fname, lname="Lovelace")
    for offset, course_type in enumerate(course_types):
        course = Course.objects.create(course_id=1000 * student_id + offset, section_id=1,
                                       name=f"Test {course_type}", type=course_type)
        course.students.add(student)
    if enable_flags:
        enable_tutor(*course_types)
    return student


def make_agent(name="Toot", language="python", hidden=False):
    return Agent.objects.create(name=name, language=language, hidden=hidden,
                                description="d", dev_message="You are a tutor.")


def fake_client(parsed=None, stop_reason="end_turn", side_effect=None):
    """A stand-in Anthropic client. ``messages.create`` (the summary call) always
    returns something harmless so it can't interfere with the assertion."""
    client = MagicMock()
    if side_effect is not None:
        client.messages.parse.side_effect = side_effect
    else:
        # A fresh response per call: real message ids are unique, and
        # AgentMessage.message_id has a unique constraint.
        counter = count()

        def respond(*args, **kwargs):
            response = MagicMock()
            response.id = f"msg_{next(counter)}_{id(parsed)}"
            response.stop_reason = stop_reason
            response.parsed_output = parsed
            return response

        client.messages.parse.side_effect = respond
    client.messages.create.return_value.content = []
    return client


def chat_reply(text="Sure!", abuse=False, reason=""):
    return AgentResponse(output_text=text, end_convo_for_abuse=abuse, abuse_description=reason)


def api_error():
    return APIConnectionError(request=httpx.Request("POST", "https://api.anthropic.com/v1/messages"))


def schema_error():
    """A real pydantic ValidationError, as messages.parse would raise on a
    response that doesn't fit the output model."""
    try:
        AgentResponse.model_validate({})
    except Exception as exc:
        return exc


# --------------------------------------------------------------------------
# #2 — server-side enforcement
# --------------------------------------------------------------------------

class ChatEnforcementTests(TestCase):
    def setUp(self):
        self.student = make_student()
        self.agent = make_agent()
        self.client.force_login(self.student.user)
        self.conv = Conversation.objects.create(student=self.student, agent=self.agent)

    def post_message(self):
        return self.client.post(reverse("chat_send"), {"conv_id": str(self.conv.id), "message": "hello"})

    @patch("aitutor.utils.claude.get_client")
    def test_normal_send_succeeds(self, get_client):
        get_client.return_value = fake_client(parsed=chat_reply())
        self.assertEqual(self.post_message().status_code, 200)
        self.assertEqual(self.conv.message_set.count(), 2)

    @patch("aitutor.utils.claude.get_client")
    def test_locked_conversation_rejects_further_messages(self, get_client):
        get_client.return_value = fake_client(parsed=chat_reply())
        self.conv.locked = True
        self.conv.save()

        self.assertEqual(self.post_message().status_code, 403)
        self.assertEqual(self.conv.message_set.count(), 0)
        get_client.assert_not_called()

    @patch("aitutor.utils.claude.get_client")
    def test_banned_student_cannot_send(self, get_client):
        get_client.return_value = fake_client(parsed=chat_reply())
        for i in range(3):
            Strike.objects.create(student=self.student, reason=f"strike {i}")
        self.assertTrue(Strike.is_banned(self.student))

        self.assertEqual(self.post_message().status_code, 403)
        self.assertEqual(self.conv.message_set.count(), 0)
        get_client.assert_not_called()

    def test_cannot_send_to_another_students_conversation(self):
        other = make_student(student_id=2, fname="Grace")
        other_conv = Conversation.objects.create(student=other, agent=self.agent)
        resp = self.client.post(reverse("chat_send"), {"conv_id": str(other_conv.id), "message": "hi"})
        self.assertEqual(resp.status_code, 403)

    def test_empty_message_rejected(self):
        self.assertEqual(self.client.post(reverse("chat_send"), {"conv_id": str(self.conv.id), "message": "   "}).status_code, 400)

    def test_send_requires_post(self):
        self.assertEqual(self.client.get(reverse("chat_send")).status_code, 405)


class NewConversationValidationTests(TestCase):
    def setUp(self):
        self.student = make_student(course_types=("CS2",))  # python only
        self.client.force_login(self.student.user)

    def test_can_open_conversation_with_enrolled_language(self):
        agent = make_agent(language="python")
        resp = self.client.post(reverse("chat_new"), {"agent_id": agent.id})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Conversation.objects.count(), 1)

    def test_agent_for_unenrolled_language_rejected(self):
        agent = make_agent(language="java")
        self.assertEqual(self.client.post(reverse("chat_new"), {"agent_id": agent.id}).status_code, 404)
        self.assertEqual(Conversation.objects.count(), 0)

    def test_hidden_agent_rejected(self):
        agent = make_agent(language="python", hidden=True)
        self.assertEqual(self.client.post(reverse("chat_new"), {"agent_id": agent.id}).status_code, 404)
        self.assertEqual(Conversation.objects.count(), 0)

    def test_assessment_agent_rejected(self):
        agent = Agent.get_assessment_agent()
        self.assertEqual(self.client.post(reverse("chat_new"), {"agent_id": agent.id}).status_code, 404)
        self.assertEqual(Conversation.objects.count(), 0)

    def test_malformed_agent_id_is_a_bad_request_not_a_crash(self):
        self.assertEqual(self.client.post(reverse("chat_new"), {"agent_id": "nope"}).status_code, 400)
        self.assertEqual(self.client.post(reverse("chat_new"), {}).status_code, 400)


class CsrfTests(TestCase):
    """The POST endpoints were all @csrf_exempt, including the staff ones that
    write grades to Canvas. A tokenless POST must now be rejected."""

    def setUp(self):
        self.csrf_client = Client(enforce_csrf_checks=True)
        self.student = make_student()
        self.agent = make_agent()
        self.conv = Conversation.objects.create(student=self.student, agent=self.agent)

    def test_student_endpoints_require_csrf_token(self):
        self.csrf_client.force_login(self.student.user)
        for url, payload in [
            (reverse("chat_new"), {"agent_id": self.agent.id}),
            (reverse("chat_send"), {"conv_id": str(self.conv.id), "message": "hi"}),
            (reverse("chat_assessment_send"), {"conv_id": str(self.conv.id), "message": "hi"}),
        ]:
            with self.subTest(url=url):
                self.assertEqual(self.csrf_client.post(url, payload).status_code, 403)

    def test_staff_endpoints_require_csrf_token(self):
        staff = User.objects.create_user(username="teacher", password="pw", is_staff=True, is_superuser=True)
        self.csrf_client.force_login(staff)
        for url in [reverse("chat_assessment_repost"), reverse("chat_assessment_reopen"),
                    reverse("chat_assessment_override"), reverse("chat_assessment_save"),
                    reverse("chat_clear_strike")]:
            with self.subTest(url=url):
                self.assertEqual(self.csrf_client.post(url, {}).status_code, 403)

    def test_token_carrying_request_is_accepted(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.student.user)
        client.get(reverse("chat_home"))  # sets the CSRF cookie
        token = client.cookies["csrftoken"].value
        resp = client.post(reverse("chat_new"), {"agent_id": self.agent.id}, HTTP_X_CSRFTOKEN=token)
        self.assertEqual(resp.status_code, 200)


# --------------------------------------------------------------------------
# #4 — failure handling
# --------------------------------------------------------------------------

class ChatFailureHandlingTests(TestCase):
    def setUp(self):
        self.student = make_student()
        self.agent = make_agent()
        self.conv = Conversation.objects.create(student=self.student, agent=self.agent)

    def send(self):
        return claude.send_message(self.conv.id, "explain loops", student=self.student)

    @patch("aitutor.utils.claude.get_client")
    def test_schema_error_is_transient_and_costs_the_student_nothing(self, get_client):
        get_client.return_value = fake_client(side_effect=schema_error())

        with self.assertRaises(TransientAgentError):
            self.send()

        self.conv.refresh_from_db()
        self.assertFalse(self.conv.locked)
        self.assertEqual(Strike.objects.count(), 0)
        # The student's message is rolled back so resending is a clean retry.
        self.assertEqual(Message.objects.count(), 0)

    @patch("aitutor.utils.claude.get_client")
    def test_api_outage_is_transient_and_costs_the_student_nothing(self, get_client):
        get_client.return_value = fake_client(side_effect=api_error())

        with self.assertRaises(TransientAgentError):
            self.send()

        self.conv.refresh_from_db()
        self.assertFalse(self.conv.locked)
        self.assertEqual(Strike.objects.count(), 0)
        self.assertEqual(Message.objects.count(), 0)

    @patch("aitutor.utils.claude.get_client")
    def test_refusal_locks_but_does_not_strike(self, get_client):
        get_client.return_value = fake_client(parsed=None, stop_reason="refusal")

        self.send()

        self.conv.refresh_from_db()
        self.assertTrue(self.conv.locked)
        self.assertEqual(self.conv.lock_reason, "Claude Safety")
        self.assertEqual(Strike.objects.count(), 0)

    @patch("aitutor.utils.claude.get_client")
    def test_abuse_still_locks_and_strikes(self, get_client):
        get_client.return_value = fake_client(parsed=chat_reply(abuse=True, reason="Repeated slurs"))

        self.send()

        self.conv.refresh_from_db()
        self.assertTrue(self.conv.locked)
        self.assertEqual(Strike.objects.count(), 1)
        self.assertEqual(Strike.objects.first().reason, "Repeated slurs")

    @patch("aitutor.utils.claude.get_client")
    def test_summary_failure_does_not_lose_the_turn(self, get_client):
        client = fake_client(parsed=chat_reply("Here you go"))
        client.messages.create.side_effect = api_error()
        get_client.return_value = client

        agent_msg = self.send()

        self.assertEqual(agent_msg.message, "Here you go")
        self.conv.refresh_from_db()
        self.assertFalse(self.conv.locked)

    @patch("aitutor.utils.claude.get_client")
    def test_transient_failure_surfaces_as_503(self, get_client):
        get_client.return_value = fake_client(side_effect=api_error())
        self.client.force_login(self.student.user)

        resp = self.client.post(reverse("chat_send"), {"conv_id": str(self.conv.id), "message": "hi"})

        self.assertEqual(resp.status_code, 503)
        self.assertEqual(Message.objects.count(), 0)


class AssessmentFailureHandlingTests(TestCase):
    def setUp(self):
        self.student = make_student(course_types=("CS2",))
        self.course = self.student.courses.first()
        self.assessment = Assessment.objects.create(
            short_name="loops", course=self.course, canvas_assignment_id=42, prompt="Loops.")
        self.conv = AssessmentConversation.objects.create(
            student=self.student, agent=Agent.get_assessment_agent(), assessment=self.assessment)

    @patch("aitutor.utils.claude.post_assessment_grade")
    @patch("aitutor.utils.claude.get_client")
    def test_schema_error_leaves_assessment_open_and_ungraded(self, get_client, post_grade):
        get_client.return_value = fake_client(side_effect=schema_error())

        with self.assertRaises(TransientAgentError):
            claude.send_message_for_assessment(self.conv.id, "my answer")

        self.conv.refresh_from_db()
        # Previously this locked the assessment, stranding the student until a
        # teacher reopened it. It must stay open and retryable.
        self.assertFalse(self.conv.locked)
        self.assertEqual(Message.objects.count(), 0)
        post_grade.assert_not_called()

    @patch("aitutor.utils.claude.post_assessment_grade")
    @patch("aitutor.utils.claude.get_client")
    def test_refusal_locks_without_grading(self, get_client, post_grade):
        get_client.return_value = fake_client(parsed=None, stop_reason="refusal")

        claude.send_message_for_assessment(self.conv.id, "my answer")

        self.conv.refresh_from_db()
        self.assertTrue(self.conv.locked)
        self.assertFalse(self.conv.credit_awarded)
        self.assertEqual(Strike.objects.count(), 0)
        post_grade.assert_not_called()

    @patch("aitutor.utils.claude.post_assessment_grade")
    @patch("aitutor.utils.claude.get_client")
    def test_completion_still_grades(self, get_client, post_grade):
        parsed = AssessmentAgentResponse(
            output_text="Nice work.", end_convo_for_abuse=False, abuse_description="",
            convo_finished=True, credit_awarded=True, understanding_score=4, feedback="Good.")
        get_client.return_value = fake_client(parsed=parsed)

        claude.send_message_for_assessment(self.conv.id, "my answer")

        self.conv.refresh_from_db()
        self.assertTrue(self.conv.locked)
        self.assertTrue(self.conv.credit_awarded)
        self.assertEqual(self.conv.understanding_score, 4)
        post_grade.assert_called_once()


class PerCourseFlagTests(TestCase):
    """Access is enrollment AND that course's flag. A student in several courses
    keeps the languages that are still switched on."""

    @staticmethod
    def request_for(student):
        request = MagicMock()
        request.user = student.user  # a real User is already is_authenticated
        return request

    def test_languages_follow_the_flags(self):
        student = make_student(course_types=("CS2", "APCSA", "CS1"))
        self.assertEqual(tutor_languages(student), ["java", "python", "html"])

        enable_tutor("CS2")
        self.assertEqual(tutor_languages(student), ["python"])

        enable_tutor("APCSA", "CS1")
        self.assertEqual(tutor_languages(student), ["java", "html"])

        enable_tutor()
        self.assertEqual(tutor_languages(student), [])

    def test_enrollment_is_still_required(self):
        student = make_student(course_types=("CS2",))
        enable_tutor("CS2", "APCSA", "CS1")  # everything on
        # Enrolled in CS2 only, so Java/HTML stay out of reach.
        self.assertEqual(tutor_languages(student), ["python"])

    def test_nav_link_follows_the_flags(self):
        student = make_student(course_types=("CS2",))
        self.assertTrue(context_processor(self.request_for(student))["tutor_available"])

        enable_tutor("APCSA")  # a course this student isn't in
        self.assertFalse(context_processor(self.request_for(student))["tutor_available"])

    def test_unenrolled_student_never_sees_the_tutor(self):
        other = make_student(student_id=9, fname="Bob", course_types=())
        enable_tutor("CS2", "APCSA", "CS1")
        self.assertFalse(context_processor(self.request_for(other))["tutor_available"])


class FlagEnforcementTests(TestCase):
    """A disabled flag has to actually block, not just hide the entry point."""

    def setUp(self):
        self.student = make_student(course_types=("CS2", "APCSA"))
        self.client.force_login(self.student.user)
        self.python_agent = make_agent(name="Toot", language="python")
        self.java_agent = make_agent(name="Yoda", language="java")

    def test_picker_only_offers_enabled_languages(self):
        enable_tutor("CS2")
        agents = list(self.client.get(reverse("chat_home")).context["agents"])
        self.assertEqual(agents, [self.python_agent])

    def test_cannot_open_conversation_in_a_disabled_language(self):
        enable_tutor("CS2")
        self.assertEqual(self.client.post(reverse("chat_new"), {"agent_id": self.java_agent.id}).status_code, 404)
        self.assertEqual(self.client.post(reverse("chat_new"), {"agent_id": self.python_agent.id}).status_code, 200)

    @patch("aitutor.utils.claude.get_client")
    def test_existing_conversation_goes_read_only_when_flag_is_off(self, get_client):
        get_client.return_value = fake_client(parsed=chat_reply())
        conv = Conversation.objects.create(student=self.student, agent=self.java_agent)

        # Java on: the student can chat.
        resp = self.client.post(reverse("chat_send"), {"conv_id": str(conv.id), "message": "hi"})
        self.assertEqual(resp.status_code, 200)

        # AP switched off mid-conversation: the open tab stops working.
        enable_tutor("CS2")
        resp = self.client.post(reverse("chat_send"), {"conv_id": str(conv.id), "message": "hi again"})
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(conv.message_set.count(), 2)  # nothing new was written

        # Their Python conversations are unaffected.
        py_conv = Conversation.objects.create(student=self.student, agent=self.python_agent)
        resp = self.client.post(reverse("chat_send"), {"conv_id": str(py_conv.id), "message": "hi"})
        self.assertEqual(resp.status_code, 200)

    def test_chat_home_explains_itself_when_everything_is_off(self):
        enable_tutor()
        resp = self.client.get(reverse("chat_home"))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "aitutor/unavailable.html")

    @patch("aitutor.utils.claude.get_client")
    def test_assessments_are_not_gated_by_the_flags(self, get_client):
        """Quick Checks are assigned deliberately via Canvas, so a flag being off
        must not strand a student partway through a graded activity."""
        parsed = AssessmentAgentResponse(
            output_text="Question one.", end_convo_for_abuse=False, abuse_description="",
            convo_finished=False, credit_awarded=False, understanding_score=1, feedback="")
        get_client.return_value = fake_client(parsed=parsed)
        enable_tutor()  # everything off

        course = self.student.courses.get(type="CS2")
        assessment = Assessment.objects.create(short_name="q1", course=course,
                                               canvas_assignment_id=7, prompt="Loops.")
        conv = AssessmentConversation.objects.create(
            student=self.student, agent=Agent.get_assessment_agent(), assessment=assessment)

        resp = self.client.post(reverse("chat_assessment_send"),
                                {"conv_id": str(conv.id), "message": "my answer"})
        self.assertEqual(resp.status_code, 200)
