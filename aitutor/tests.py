"""Tests for the tutor's access enforcement and its failure handling.

These cover the two things that are easiest to regress silently: rules that used
to live only in a template (so a stale tab bypassed them), and the behaviour when
a model call fails (which must never cost a student a strike or their work).
"""

import base64
import html
import io
import re
import shutil
import tempfile
from itertools import count
from pathlib import Path
from uuid import uuid4
from unittest.mock import MagicMock, patch

import httpx
from PIL import Image as PILImage
from anthropic import APIConnectionError
from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from app.models import Course, FeatureFlag, Student
from aitutor.models import (Agent, AgentMessage, Assessment, AssessmentConversation, Conversation,
                            Message, Strike, UserMessage)
from aitutor.templatetags.djmark2 import auto_code_highlight, lexer_for, markdown_format
from aitutor.utils import claude
from aitutor.utils.claude import AgentResponse, AssessmentAgentResponse, TransientAgentError
from aitutor.utils.context import context_processor
from aitutor.utils.agents import (AgentImageError, build_language_bases, find_photo,
                                  sync_photo, verify_image)
from aitutor.utils.enrollment import COURSE_TYPE_TO_FLAG, tutor_languages
from aitutor.utils.prompts import (BASE_MARKER, COMMON_MARKER, DESCRIPTION_START,
                                   PROMPT_MARKER, PromptTemplateError,
                                   extract_description, splice)


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
            # Real ints — a bare MagicMock coerces to 1 and makes the cache log lie.
            response.usage = MagicMock(input_tokens=120, cache_read_input_tokens=1400,
                                       cache_creation_input_tokens=0)
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


class MessageRenderingTests(TestCase):
    """Student messages are never interpreted and never discarded; agent
    messages are Markdown with raw HTML escaped."""

    @staticmethod
    def visible(rendered):
        """What the student actually sees. Pygments splits text across <span>s,
        so assert on the rendered text rather than raw substrings."""
        return html.unescape(re.sub(r"<[^>]+>", "", rendered))

    def test_pasted_html_is_shown_not_deleted(self):
        """The old filter ran prose through BeautifulSoup.get_text(), so a Web
        Dev student's markup vanished from their own transcript."""
        out = auto_code_highlight("<h1>My Page</h1>\n<p>Hello</p>", "html")

        self.assertIn("<h1>My Page</h1>", self.visible(out))
        self.assertIn("<p>Hello</p>", self.visible(out))
        self.assertNotIn("<h1>", out)  # escaped, not executed

    def test_blank_line_does_not_split_a_pasted_function(self):
        out = auto_code_highlight('def greet(name):\n    print(name)\n\ngreet("Ada")', "python")

        self.assertEqual(out.count("codehilite"), 1)  # one block, not two
        self.assertIn('greet("Ada")', self.visible(out))

    def test_real_markdown_fences_are_honoured(self):
        out = auto_code_highlight("Here it is:\n\n```python\nprint(1)\n```\n\nwhy broken?", "python")

        self.assertNotIn("```", out)
        self.assertIn("codehilite", out)
        self.assertIn("Here it is:", out)
        self.assertIn("why broken?", out)

    def test_single_line_of_code_is_still_boxed(self):
        self.assertIn("codehilite", auto_code_highlight('print("hello")', "python"))

    def test_prose_is_not_boxed(self):
        for prose in ["I don't get why my loop won't stop.",
                      "Note: this is tricky for me",
                      "I tried it yesterday and it broke"]:
            with self.subTest(prose=prose):
                self.assertNotIn("codehilite", auto_code_highlight(prose, "python"))

    def test_one_code_ish_line_inside_prose_stays_prose(self):
        out = auto_code_highlight("I tried this yesterday\nx = 5\nbut it did not work", "python")
        self.assertNotIn("codehilite", out)

    def test_student_html_cannot_execute(self):
        out = auto_code_highlight('<script>alert(1)</script>', "html")
        self.assertNotIn("<script>", out)
        self.assertIn("<script>alert(1)</script>", self.visible(out))

    def test_student_whitespace_is_preserved(self):
        """Indentation is meaningful in Python; <p> used to collapse it."""
        self.assertIn("chat-text", auto_code_highlight("hello\nthere", "python"))

    def test_agent_raw_html_is_escaped(self):
        out = markdown_format("Nice work! <img src=x onerror=alert(1)>")
        self.assertNotIn("<img", out)
        self.assertIn("&lt;img", out)

    def test_agent_code_block_is_syntax_highlighted(self):
        """highlightjs-lang used to suppress Pygments and emit a class for a
        highlighter this project never loaded."""
        out = markdown_format("```python\nfor i in range(3):\n    print(i)\n```")

        self.assertIn("codehilite", out)
        self.assertIn('class="k"', out)          # a real Pygments token
        self.assertNotIn("language-python", out)  # the dead highlight.js hook

    def test_student_code_is_syntax_highlighted_too(self):
        out = auto_code_highlight("for i in range(3):\n    print(i)", "python")
        self.assertIn('class="k"', out)

    def test_agent_single_newlines_become_line_breaks(self):
        self.assertIn("<br", markdown_format("Line one\nLine two"))

    def test_agent_inline_code_renders(self):
        self.assertIn("<code>len()</code>", markdown_format("Use the `len()` function."))

    def test_language_hint_picks_the_lexer(self):
        """An unlabelled paste should use the course's language, not a guess."""
        self.assertEqual(lexer_for("python", "x = 1").name, "Python")
        self.assertEqual(lexer_for("java", "int x = 1;").name, "Java")
        self.assertEqual(lexer_for("html", "<h1>hi</h1>").name, "HTML")

    def test_empty_and_none_messages_are_safe(self):
        for value in ["", None, "   "]:
            with self.subTest(value=value):
                self.assertEqual(auto_code_highlight(value, "python"), "")
                self.assertEqual(markdown_format(value).strip(), "")


@override_settings(MEDIA_ROOT=tempfile.mkdtemp(prefix="aitutor-test-thumbs-"))
class ThumbnailTests(TestCase):
    """Agent portraits are 300-1400px originals shown at 50-100px. Serving the
    originals meant ~1.3MB of images per chat page load."""

    def setUp(self):
        self.student = make_student(course_types=("CS2",))
        self.client.force_login(self.student.user)
        self.agent = make_agent(name="Yzma", language="python")
        buffer = io.BytesIO()
        PILImage.new("RGB", (800, 800), (120, 20, 140)).save(buffer, format="JPEG")
        self.agent.photo.save("yzma.jpg", ContentFile(buffer.getvalue()), save=True)

    def rendered_image_srcs(self, html):
        return re.findall(r'src="(/media/[^"]+)"', html)

    def test_picker_serves_thumbnails_not_originals(self):
        html = self.client.get(reverse("chat_home")).content.decode()
        srcs = self.rendered_image_srcs(html)

        self.assertTrue(srcs, "no agent image rendered on the picker")
        for src in srcs:
            self.assertIn("/cache/", src)
            self.assertNotIn("yzma.jpg", src)

    def test_thumbnail_is_far_smaller_than_the_original(self):
        html = self.client.get(reverse("chat_home")).content.decode()
        src = self.rendered_image_srcs(html)[0]

        thumb = Path(settings.MEDIA_ROOT) / src.replace("/media/", "")
        self.assertTrue(thumb.exists())
        self.assertLess(thumb.stat().st_size, self.agent.photo.size / 4)

        with PILImage.open(thumb) as im:
            self.assertEqual(im.size, (200, 200))  # 2x the 100px display size

    def test_conversation_view_also_thumbnails(self):
        conv = Conversation.objects.create(student=self.student, agent=self.agent)
        UserMessage.objects.create(conversation=conv, message="hi",
                                   student=self.student, role="user")
        AgentMessage.objects.create(conversation=conv, message="hello", agent=self.agent,
                                    role="agent", message_id=f"msg_{uuid4()}")

        html = self.client.get(reverse("chat_conversation"), {"conv_id": str(conv.id)}).content.decode()
        srcs = re.findall(r'src=\\"(/media/[^\\"]+)\\"', html) or self.rendered_image_srcs(html)

        self.assertTrue(srcs, "no agent image rendered in the conversation")
        for src in srcs:
            self.assertIn("/cache/", src)


class PromptAssemblyTests(TestCase):
    """The prompt files splice into each other, so a bad marker silently
    produces a prompt that's missing a rulebook or has one twice."""

    def setUp(self):
        self.dir = settings.BASE_DIR / "aitutor/agents"

    def test_every_language_base_carries_the_shared_rules(self):
        bases = build_language_bases(self.dir)
        self.assertEqual(set(bases), {"java", "python", "html"})
        for language, base in bases.items():
            with self.subTest(language=language):
                self.assertIn("Abuse Protocol", base)
                self.assertIn("Holding the Line", base)
                self.assertIn("abuse_description", base)
                self.assertNotIn(COMMON_MARKER, base)  # fully spliced

    def test_every_persona_file_assembles(self):
        bases = build_language_bases(self.dir)
        personas = [f for f in self.dir.glob("*.txt") if not f.name.startswith("base-")]
        self.assertTrue(personas)

        for f in personas:
            with self.subTest(persona=f.name):
                built = splice(f.read_text(), BASE_MARKER, bases["python"], source=f.name)
                self.assertNotIn(BASE_MARKER, built)
                self.assertIn("Abuse Protocol", built)

    def test_markdown_rule_no_longer_corrupts_a_template(self):
        """The old '-----' marker was also a Markdown horizontal rule."""
        persona = "You are a tutor.\n\n-----\n\n%%BASE%%\n"
        built = splice(persona, BASE_MARKER, "RULES", source="persona.txt")
        self.assertEqual(built, "You are a tutor.\n\n-----\n\nRULES\n")

    def test_missing_or_duplicated_marker_raises(self):
        with self.assertRaises(PromptTemplateError):
            splice("nothing here", BASE_MARKER, "x")
        with self.assertRaises(PromptTemplateError):
            splice("%%BASE%% twice %%BASE%%", BASE_MARKER, "x")

    def test_assessment_prompt_containing_a_markdown_rule_survives(self):
        student = make_student(course_types=("CS2",))
        assessment = Assessment.objects.create(
            short_name="rules", course=student.courses.first(), canvas_assignment_id=1,
            prompt="Explain loops.\n\n-----\n\nBe specific.")
        conv = AssessmentConversation.objects.create(
            student=student, agent=Agent.get_assessment_agent(), assessment=assessment)
        UserMessage.objects.create(conversation=conv, message="ready", student=student, role="user")

        system, _ = conv.to_claude_messages()
        text = system[0]["text"]

        # The teacher's rule survives verbatim, and the base was spliced once.
        self.assertIn("Explain loops.\n\n-----\n\nBe specific.", text)
        self.assertEqual(text.count("Abuse Protocol"), 1)
        self.assertNotIn(PROMPT_MARKER, text)
        self.assertNotIn("%%COURSE_CONTEXT%%", text)

    def test_no_prompt_treats_persistence_as_abuse(self):
        """A pushy student must not trip the flag — it costs a strike in chat and
        withheld credit on an assessment."""
        bases = build_language_bases(self.dir)
        prompts = dict(bases, assessment=(self.dir / "assessment" / "base.txt").read_text())

        retired_triggers = [
            "repeated demands for answers despite refusal",
            "pushing you too hard for an answer",
            "very first mention",
        ]
        for label, text in prompts.items():
            with self.subTest(prompt=label):
                lowered = text.lower()
                for trigger in retired_triggers:
                    self.assertNotIn(trigger, lowered)
                # ...and each prompt still tells the agent to keep refusing.
                self.assertIn("holding the line", lowered)

    def test_every_prompt_still_refuses_full_solutions(self):
        """Relaxing the abuse flag must not relax the actual refusal."""
        bases = build_language_bases(self.dir)
        for language, base in bases.items():
            with self.subTest(language=language):
                lowered = base.lower()
                self.assertIn("never provide full solutions", lowered)
                self.assertIn("decline again", lowered)
                self.assertIn("fill in", lowered)  # no "just the structure" loophole

    def test_html_base_has_no_leftover_python_wording(self):
        html = build_language_bases(self.dir)["html"]
        self.assertNotIn("function implementations", html)
        self.assertNotIn("pseudocode", html.lower())
        self.assertIn("flexbox", html)  # course content preserved

    def test_toot_is_the_flavourless_agent(self):
        toot = (self.dir / "Toot.txt").read_text()
        self.assertIn("no persona voice", toot)
        self.assertIn(BASE_MARKER, toot)

    def test_every_persona_declares_a_description(self):
        for f in self.dir.glob("*.txt"):
            if f.name.startswith("base-"):
                continue
            with self.subTest(persona=f.name):
                description, remaining = extract_description(f.read_text(), source=f.name)
                self.assertTrue(description)
                # Card copy is for students, not an instruction to the model.
                self.assertNotIn(DESCRIPTION_START, remaining)
                self.assertNotIn(description, remaining)
                self.assertIn(BASE_MARKER, remaining)


class DescriptionBlockTests(TestCase):
    def test_description_is_extracted_and_collapsed(self):
        description, remaining = extract_description(
            "%%DESCRIPTION%%\nA tutor who\nspans two lines.\n%%END_DESCRIPTION%%\n\nYou are X.\n%%BASE%%\n")
        self.assertEqual(description, "A tutor who spans two lines.")
        self.assertEqual(remaining, "You are X.\n%%BASE%%\n")

    def test_missing_block_raises(self):
        with self.assertRaises(PromptTemplateError):
            extract_description("You are X.\n%%BASE%%\n", source="x.txt")

    def test_empty_block_raises(self):
        with self.assertRaises(PromptTemplateError):
            extract_description("%%DESCRIPTION%%\n   \n%%END_DESCRIPTION%%\nYou are X.")

    def test_duplicated_or_reversed_markers_raise(self):
        with self.assertRaises(PromptTemplateError):
            extract_description("%%DESCRIPTION%%a%%END_DESCRIPTION%%%%DESCRIPTION%%b%%END_DESCRIPTION%%")
        with self.assertRaises(PromptTemplateError):
            extract_description("%%END_DESCRIPTION%%a%%DESCRIPTION%%")


@override_settings(MEDIA_ROOT=tempfile.mkdtemp(prefix="aitutor-test-media-"))
class AgentPhotoImportTests(TestCase):
    """A 1x1 PNG is enough — we only care about the copy/skip/replace logic."""

    PNG_A = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")
    PNG_B = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")

    def setUp(self):
        self.agent = make_agent(name="Ms. Frizzle")
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def write(self, filename, data):
        path = self.tmp / filename
        path.write_bytes(data)
        return path

    @staticmethod
    def encode(fmt, colour=(200, 40, 40)):
        """A genuine 8x8 image in the given format, not a hand-pasted blob."""
        buffer = io.BytesIO()
        PILImage.new("RGB", (8, 8), colour).save(buffer, format=fmt)
        return buffer.getvalue()

    def test_finds_an_image_beside_the_persona_file(self):
        self.write("Ms. Frizzle.png", self.PNG_A)
        self.assertEqual(find_photo(self.tmp, "Ms. Frizzle").name, "Ms. Frizzle.png")
        self.assertIsNone(find_photo(self.tmp, "Nobody"))

    def test_every_supported_format_imports(self):
        for extension, fmt in [(".png", "PNG"), (".jpg", "JPEG"), (".jpeg", "JPEG"),
                               (".webp", "WEBP"), (".gif", "GIF")]:
            with self.subTest(extension=extension):
                shutil.rmtree(self.tmp, ignore_errors=True)
                self.tmp.mkdir(parents=True, exist_ok=True)
                agent = Agent.objects.create(name=f"Agent{extension}", language="python",
                                             description="d", dev_message="m")

                data = self.encode(fmt)
                path = self.write(f"Agent{extension}{extension}", data)

                self.assertEqual(verify_image(path), fmt)
                found = find_photo(self.tmp, f"Agent{extension}")
                self.assertIsNotNone(found)
                self.assertTrue(sync_photo(agent, found))

                agent.refresh_from_db()
                self.assertTrue(agent.photo.name.endswith(extension))
                with agent.photo.open("rb") as f:
                    self.assertEqual(f.read(), data)

    def test_uppercase_extensions_are_found(self):
        """Phone cameras and downloads routinely produce .JPG / .PNG."""
        for filename in ["Shouty.JPG", "Shouty.PNG", "Shouty.WebP"]:
            with self.subTest(filename=filename):
                shutil.rmtree(self.tmp, ignore_errors=True)
                self.tmp.mkdir(parents=True, exist_ok=True)
                fmt = {"jpg": "JPEG", "png": "PNG", "webp": "WEBP"}[filename.split(".")[1].lower()]
                self.write(filename, self.encode(fmt))
                self.assertEqual(find_photo(self.tmp, "Shouty").name, filename)

    def test_stored_extension_is_normalised_to_lowercase(self):
        self.write("Ms. Frizzle.JPG", self.encode("JPEG"))
        sync_photo(self.agent, find_photo(self.tmp, "Ms. Frizzle"))
        self.agent.refresh_from_db()
        self.assertTrue(self.agent.photo.name.endswith(".jpg"))

    def test_a_file_that_is_not_an_image_is_rejected(self):
        path = self.write("Ms. Frizzle.png", b"I am plainly not a PNG.")
        with self.assertRaises(AgentImageError):
            verify_image(path)
        with self.assertRaises(AgentImageError):
            sync_photo(self.agent, path)
        self.agent.refresh_from_db()
        self.assertFalse(self.agent.photo)  # nothing stored

    def test_truncated_image_is_rejected(self):
        path = self.write("Ms. Frizzle.png", self.encode("PNG")[:20])
        with self.assertRaises(AgentImageError):
            verify_image(path)

    def test_two_images_for_one_agent_is_an_error(self):
        self.write("Ms. Frizzle.png", self.encode("PNG"))
        self.write("Ms. Frizzle.jpg", self.encode("JPEG"))
        with self.assertRaises(AgentImageError) as caught:
            find_photo(self.tmp, "Ms. Frizzle")
        self.assertIn("more than one image", str(caught.exception))

    def test_unsupported_format_is_ignored(self):
        """Pillow reads TIFF; browsers don't render it, so it isn't a candidate."""
        self.write("Ms. Frizzle.tiff", self.encode("TIFF"))
        self.assertIsNone(find_photo(self.tmp, "Ms. Frizzle"))

    def test_first_import_stores_the_image(self):
        path = self.write("Ms. Frizzle.png", self.PNG_A)
        self.assertTrue(sync_photo(self.agent, path))
        self.agent.refresh_from_db()
        self.assertTrue(self.agent.photo)
        with self.agent.photo.open("rb") as f:
            self.assertEqual(f.read(), self.PNG_A)

    def test_reimport_is_a_no_op(self):
        """Import runs repeatedly; unconditional saves would pile up copies."""
        path = self.write("Ms. Frizzle.png", self.PNG_A)
        sync_photo(self.agent, path)
        stored = self.agent.photo.name

        for _ in range(3):
            self.assertFalse(sync_photo(self.agent, path))

        self.agent.refresh_from_db()
        self.assertEqual(self.agent.photo.name, stored)

    def test_changed_image_replaces_the_old_file(self):
        path = self.write("Ms. Frizzle.png", self.PNG_A)
        sync_photo(self.agent, path)
        storage, folder = self.agent.photo.storage, "agent_photos"

        path.write_bytes(self.PNG_B)
        self.assertTrue(sync_photo(self.agent, path))

        self.agent.refresh_from_db()
        with self.agent.photo.open("rb") as f:
            self.assertEqual(f.read(), self.PNG_B)
        # Deleting first frees the deterministic name, so the replacement reuses
        # it rather than leaving a suffixed orphan behind.
        self.assertEqual(len(storage.listdir(folder)[1]), 1)

    def test_recovers_when_the_stored_file_has_vanished(self):
        path = self.write("Ms. Frizzle.png", self.PNG_A)
        sync_photo(self.agent, path)
        self.agent.photo.storage.delete(self.agent.photo.name)

        self.assertTrue(sync_photo(self.agent, path))
        with self.agent.photo.open("rb") as f:
            self.assertEqual(f.read(), self.PNG_A)


class PromptCacheTests(TestCase):
    """Caching is a prefix match, so these assert the *shape* of the prompt:
    a stable prefix, volatile content strictly after it, and a rolling
    breakpoint on the newest turn."""

    def setUp(self):
        self.student = make_student(fname="Ada")
        self.agent = make_agent()
        self.conv = Conversation.objects.create(student=self.student, agent=self.agent)

    def turn(self, user_text, agent_text=None):
        UserMessage.objects.create(conversation=self.conv, message=user_text,
                                   student=self.student, role="user")
        if agent_text:
            AgentMessage.objects.create(conversation=self.conv, message=agent_text,
                                        agent=self.agent, role="agent",
                                        message_id=f"msg_{uuid4()}")

    def test_system_prefix_is_cached_and_identical_across_students(self):
        other = make_student(student_id=2, fname="Grace")
        self.turn("hi")

        mine, _ = self.conv.to_claude_messages(student=self.student)
        theirs, _ = Conversation.objects.create(
            student=other, agent=self.agent).to_claude_messages(student=other)

        # The cached block is byte-identical for both students...
        self.assertEqual(mine[0], theirs[0])
        self.assertEqual(mine[0]["text"], self.agent.dev_message)
        self.assertEqual(mine[0]["cache_control"], {"type": "ephemeral"})

        # ...and the per-student name sits after it, uncached. Folding the name
        # into the cached block would make the prefix per-student and destroy
        # all cross-student sharing.
        self.assertIn("Ada", mine[1]["text"])
        self.assertIn("Grace", theirs[1]["text"])
        self.assertNotIn("cache_control", mine[1])
        self.assertNotIn("Ada", mine[0]["text"])

    def test_breakpoint_rolls_to_the_newest_message(self):
        self.turn("first", "reply one")
        self.turn("second")

        _, messages = self.conv.to_claude_messages(student=self.student)

        self.assertEqual(len(messages), 3)
        # Only the last message carries a breakpoint; earlier turns stay plain
        # strings and are served from the entry written on the previous turn.
        self.assertEqual(messages[-1]["content"],
                         [{"type": "text", "text": "second", "cache_control": {"type": "ephemeral"}}])
        for earlier in messages[:-1]:
            self.assertIsInstance(earlier["content"], str)

    def test_breakpoint_count_stays_within_the_four_allowed(self):
        for i in range(12):
            self.turn(f"q{i}", f"a{i}")

        system, messages = self.conv.to_claude_messages(student=self.student)
        breakpoints = sum(1 for b in system if "cache_control" in b)
        breakpoints += sum(
            1 for m in messages if isinstance(m["content"], list)
            for b in m["content"] if "cache_control" in b
        )
        self.assertLessEqual(breakpoints, 4)
        self.assertEqual(breakpoints, 2)  # system prefix + rolling turn

    def test_assessment_prefix_is_shared_across_students(self):
        course = self.student.courses.first()
        assessment = Assessment.objects.create(short_name="loops", course=course,
                                               canvas_assignment_id=1, prompt="Explain loops.")
        other = make_student(student_id=3, fname="Alan")
        course.students.add(other)
        agent = Agent.get_assessment_agent()

        convs = [AssessmentConversation.objects.create(student=s, agent=agent, assessment=assessment)
                 for s in (self.student, other)]
        for c in convs:
            UserMessage.objects.create(conversation=c, message="ready", student=c.student, role="user")

        first, _ = convs[0].to_claude_messages()
        second, _ = convs[1].to_claude_messages()

        self.assertEqual(first, second)
        self.assertEqual(first[0]["cache_control"], {"type": "ephemeral"})
        self.assertIn("Explain loops.", first[0]["text"])

    def test_prompt_is_stable_across_identical_rebuilds(self):
        """No timestamps, UUIDs, or unordered iteration inside the prefix."""
        self.turn("hello", "hi there")
        first = self.conv.to_claude_messages(student=self.student)
        second = self.conv.to_claude_messages(student=self.student)
        self.assertEqual(first, second)

    def test_cache_usage_log_reports_the_full_prompt_size(self):
        """input_tokens alone is only the uncached remainder — the log has to sum
        all three or it understates the prompt by the cached portion."""
        usage = MagicMock(input_tokens=120, cache_read_input_tokens=1400,
                          cache_creation_input_tokens=480)
        with self.assertLogs("aitutor.utils.claude", level="INFO") as logs:
            claude.log_cache_usage("chat", self.conv, usage)

        line = logs.output[0]
        self.assertIn("prompt 2000 tokens", line)
        self.assertIn("70% served from cache", line)

    def test_cache_usage_log_survives_a_zero_token_response(self):
        usage = MagicMock(input_tokens=0, cache_read_input_tokens=0,
                          cache_creation_input_tokens=0)
        with self.assertLogs("aitutor.utils.claude", level="INFO") as logs:
            claude.log_cache_usage("chat", self.conv, usage)  # must not divide by zero
        self.assertIn("0% served from cache", logs.output[0])

    @patch("aitutor.utils.claude.get_client")
    def test_cached_prompt_is_what_reaches_the_api(self, get_client):
        client = fake_client(parsed=chat_reply())
        get_client.return_value = client

        claude.send_message(self.conv.id, "explain loops", student=self.student)

        kwargs = client.messages.parse.call_args.kwargs
        self.assertEqual(kwargs["system"][0]["cache_control"], {"type": "ephemeral"})
        self.assertEqual(kwargs["messages"][-1]["content"][0]["cache_control"], {"type": "ephemeral"})


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
