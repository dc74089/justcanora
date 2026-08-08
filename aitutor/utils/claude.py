import json
import logging
import uuid

from anthropic import APIError
from django.conf import settings
from pydantic import BaseModel, ValidationError

from aitutor.models import Conversation, UserMessage, AgentMessage, AssessmentConversation, Strike
from aitutor.utils.grades import post_assessment_grade

logger = logging.getLogger(__name__)


class TransientAgentError(Exception):
    """The model call failed in a way that is nobody's fault and is safe to retry
    (API outage, rate limit, timeout, or a response that didn't match the schema).

    The student's message is rolled back before this is raised, so resending is a
    clean retry. Callers should surface a "try again" to the user — never a strike
    and never a lock, since neither the student nor the conversation did anything
    wrong."""


class AgentResponse(BaseModel):
    output_text: str
    end_convo_for_abuse: bool
    abuse_description: str


class AssessmentAgentResponse(BaseModel):
    output_text: str
    end_convo_for_abuse: bool
    abuse_description: str
    convo_finished: bool
    credit_awarded: bool
    understanding_score: int
    feedback: str


def get_client():
    from anthropic import Anthropic
    # Reads ANTHROPIC_API_KEY from the environment.
    return Anthropic()


def log_cache_usage(label, conversation, usage):
    """Record what the prompt cache actually did on this turn.

    ``cache_read`` staying at 0 across a conversation's turns is the signal that
    caching has silently broken — something is varying inside the cached prefix.
    Total prompt size is the three figures summed; ``input`` alone is only the
    uncached remainder.
    """
    if usage is None:
        return

    read = getattr(usage, "cache_read_input_tokens", 0) or 0
    written = getattr(usage, "cache_creation_input_tokens", 0) or 0
    uncached = getattr(usage, "input_tokens", 0) or 0
    total = read + written + uncached

    logger.info(
        "%s %s: prompt %d tokens (cache read %d, cache write %d, uncached %d) — %d%% served from cache",
        label, conversation.id, total, read, written, uncached,
        round(read * 100 / total) if total else 0,
    )


def helper_lock_with_strike(conversation, reason):
    agent_msg = AgentMessage.objects.create(
        conversation=conversation,
        message="I'm sorry, I can't help with that.",
        agent=conversation.agent,
        role="agent",
        message_id=f"safety-{uuid.uuid4()}"
    )

    conversation.locked = True
    conversation.lock_reason = reason
    conversation.save()

    strike = Strike(
        student=conversation.student,
        conversation=conversation,
        reason=reason
    )

    strike.save()

    return agent_msg


def helper_lock_no_strike(conversation, reason):
    """Lock a chat conversation without penalising the student.

    Used when Claude's safety classifier declines the request: worth ending the
    conversation and leaving it for staff to review, but a refusal is not proof
    of abuse — only ``end_convo_for_abuse`` is — so no strike is recorded."""
    agent_msg = AgentMessage.objects.create(
        conversation=conversation,
        message="I'm sorry, I can't help with that.",
        agent=conversation.agent,
        role="agent",
        message_id=f"safety-{uuid.uuid4()}"
    )

    conversation.locked = True
    conversation.lock_reason = reason
    conversation.save()

    return agent_msg


def helper_lock_assessment(conversation, reason):
    """Lock an assessment conversation without awarding credit or posting to
    Canvas. Used when a response can't be trusted (safety / refusal), so nothing
    is pushed to the gradebook. Assessments do not accrue strikes."""
    agent_msg = AgentMessage.objects.create(
        conversation=conversation,
        message="I'm sorry, I can't help with that. This assessment has ended.",
        agent=conversation.agent,
        role="agent",
        message_id=f"safety-{uuid.uuid4()}"
    )

    conversation.locked = True
    conversation.credit_awarded = False
    conversation.lock_reason = reason
    conversation.save()

    return agent_msg


def send_message(conversation_id, message, student=None):
    client = get_client()
    conversation = Conversation.objects.get(id=conversation_id)

    user_msg = UserMessage.objects.create(
        conversation=conversation,
        message=message,
        student=conversation.student,
        role="user"
    )

    system, messages = conversation.to_claude_messages(student=student)

    try:
        response = client.messages.parse(
            model=settings.CLAUDE_MODEL_FOR_CHAT,
            max_tokens=2048,
            thinking={"type": "disabled"},
            system=system,
            messages=messages,
            output_format=AgentResponse,
            metadata={"user_id": str(conversation.student.id)},
        )

        # Safety classifiers may decline the request (HTTP 200, no parsed output).
        refused = response.stop_reason == "refusal"
        parsed = None if refused else response.parsed_output
        log_cache_usage("chat", conversation, response.usage)
    except (APIError, ValidationError):
        # An outage, a rate limit, or a response that didn't fit the schema. None
        # of these are the student's doing, so roll their message back and let
        # them resend rather than locking the conversation or issuing a strike.
        logger.exception("Chat turn failed for conversation %s", conversation.id)
        user_msg.delete()
        raise TransientAgentError

    if refused:
        return helper_lock_no_strike(conversation, "Claude Safety")

    if parsed is None:
        logger.error("No parsed output for conversation %s (stop_reason=%s)", conversation.id, response.stop_reason)
        user_msg.delete()
        raise TransientAgentError

    agent_msg = AgentMessage.objects.create(
        conversation=conversation,
        message=parsed.output_text,
        agent=conversation.agent,
        role="agent",
        message_id=response.id
    )

    if not conversation.summary or conversation.messages().count() in (4, 5):
        # Cosmetic sidebar label — a failure here must not cost the student a turn
        # they've already paid for.
        try:
            generate_summary(conversation_id)
        except Exception:
            logger.exception("Summary generation failed for conversation %s", conversation.id)

    if parsed.end_convo_for_abuse:
        return helper_lock_with_strike(conversation, parsed.abuse_description)

    return agent_msg


def send_message_for_assessment(conversation_id, message):
    client = get_client()
    conversation = AssessmentConversation.objects.get(id=conversation_id)

    user_msg = UserMessage.objects.create(
        conversation=conversation,
        message=message,
        student=conversation.student,
        role="user"
    )

    system, messages = conversation.to_claude_messages()

    try:
        response = client.messages.parse(
            model=settings.CLAUDE_MODEL_FOR_ASSESSMENT,
            max_tokens=2048,
            thinking={"type": "disabled"},
            system=system,
            messages=messages,
            output_format=AssessmentAgentResponse,
            metadata={"user_id": str(conversation.student.id)},
        )

        refused = response.stop_reason == "refusal"
        parsed = None if refused else response.parsed_output
        log_cache_usage("assessment", conversation, response.usage)
    except (APIError, ValidationError):
        # Transient failure mid-assessment. Roll the answer back and let the
        # student resend: locking here would strand them on a graded activity
        # they'd need a teacher to reopen. Nothing is posted to Canvas.
        logger.exception("Assessment turn failed for conversation %s", conversation.id)
        user_msg.delete()
        raise TransientAgentError

    if refused:
        # Safety refusal — lock without posting to Canvas.
        return helper_lock_assessment(conversation, "Claude Safety")

    if parsed is None:
        logger.error("No parsed output for assessment %s (stop_reason=%s)", conversation.id, response.stop_reason)
        user_msg.delete()
        raise TransientAgentError

    agent_msg = AgentMessage.objects.create(
        conversation=conversation,
        message=parsed.output_text,
        agent=conversation.agent,
        role="agent",
        message_id=response.id
    )

    if parsed.end_convo_for_abuse:
        conversation.locked = True
        conversation.credit_awarded = False
        conversation.lock_reason = parsed.abuse_description
        conversation.save()
        # Abuse-locked assessments are intentionally never posted to Canvas.
    elif parsed.convo_finished:
        conversation.locked = True
        conversation.lock_reason = "Assessment Finished"
        conversation.credit_awarded = parsed.credit_awarded
        # Clamp to the 1-5 range the prompt promises so score_as_percent stays sane.
        conversation.understanding_score = max(1, min(5, parsed.understanding_score))
        conversation.feedback = parsed.feedback
        conversation.save()

        post_assessment_grade(conversation)

    return agent_msg


def generate_summary(conversation_id):
    """Deliberately uncached: this runs on Haiku, whose minimum cacheable prefix
    is 4096 tokens — far above this ~60-token system prompt — and it fires at
    most twice per conversation, so there's no prefix to reuse anyway."""
    client = get_client()
    conversation = Conversation.objects.get(id=conversation_id)

    response = client.messages.create(
        model=settings.CLAUDE_MODEL_FOR_SUMMARY,
        max_tokens=64,
        thinking={"type": "disabled"},
        system="Respond with a few words reflecting the purpose of the conversation. "
               "This will be displayed in the format 'talking with an assistant about <blank>'. "
               "Respond only with what should replace the <blank> placeholder.",
        messages=[{"role": "user", "content": json.dumps(conversation.info_for_summary())}],
        metadata={"user_id": str(conversation.student.id)},
    )

    conversation.summary = next((b.text for b in response.content if b.type == "text"), "")
    conversation.save()
