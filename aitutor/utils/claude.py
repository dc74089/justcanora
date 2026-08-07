import json
import uuid

from django.conf import settings
from pydantic import BaseModel, ValidationError

from aitutor.models import Conversation, UserMessage, AgentMessage, AssessmentConversation, Strike
from aitutor.utils.grades import post_assessment_grade


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

    UserMessage.objects.create(
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
        if response.stop_reason == "refusal":
            return helper_lock_with_strike(conversation, "Claude Safety")

        parsed = response.parsed_output

        agent_msg = AgentMessage.objects.create(
            conversation=conversation,
            message=parsed.output_text,
            agent=conversation.agent,
            role="agent",
            message_id=response.id
        )

        if not conversation.summary or conversation.messages().count() in (4, 5):
            generate_summary(conversation_id)

        if parsed.end_convo_for_abuse:
            return helper_lock_with_strike(conversation, parsed.abuse_description)

        return agent_msg
    except ValidationError:
        return helper_lock_with_strike(conversation, "Claude Safety")


def send_message_for_assessment(conversation_id, message):
    client = get_client()
    conversation = AssessmentConversation.objects.get(id=conversation_id)

    UserMessage.objects.create(
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

        if response.stop_reason == "refusal":
            # Safety refusal — lock without posting to Canvas.
            return helper_lock_assessment(conversation, "Claude Safety")

        parsed = response.parsed_output

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
    except ValidationError:
        agent_msg = AgentMessage.objects.create(
            conversation=conversation,
            message="There was en error. Please contact Tr. Canora.",
            agent=conversation.agent,
            role="agent",
            message_id=f"safety-{uuid.uuid4()}"
        )

        conversation.locked = True
        conversation.credit_awarded = False
        conversation.lock_reason = "Claude Safety"
        conversation.save()

        return agent_msg


def generate_summary(conversation_id):
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
