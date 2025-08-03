import json
import os
import uuid
from pprint import pprint

from django.conf import settings
from pydantic import BaseModel, ValidationError

from aitutor.models import Conversation, UserMessage, AgentMessage, AssessmentConversation, Strike


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
    from openai import OpenAI
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))


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


def send_message(conversation_id, message, student=None):
    client = get_client()
    conversation = Conversation.objects.get(id=conversation_id)

    UserMessage.objects.create(
        conversation=conversation,
        message=message,
        student=conversation.student,
        role="user"
    )

    try:
        mod_response = client.moderations.create(
            model="omni-moderation-latest",
            input=conversation.info_for_moderation(),
        )

        # pprint(conversation.info_for_moderation())
        # pprint(dict(mod_response.results[0]))

        if mod_response.results[0].flagged:
            cats = dict(mod_response.results[0].categories)
            flagged_cats = [k for k, v in cats.items() if v]

            return helper_lock_with_strike(conversation, f"OpenAI Moderation: {', '.join(flagged_cats)}")

        response = client.responses.parse(
            model=settings.OPENAI_MODEL_FOR_CHAT,
            input=conversation.to_openai_json(student=student),
            text_format=AgentResponse,
            user=str(conversation.student.id)
        )

        agent_msg = AgentMessage.objects.create(
            conversation=conversation,
            message=response.output_parsed.output_text,
            agent=conversation.agent,
            role="agent",
            message_id=response.id
        )

        if not conversation.summary or conversation.messages().count() in (4, 5):
            generate_summary(conversation_id)

        if response.output_parsed.end_convo_for_abuse:
            return helper_lock_with_strike(conversation, response.output_parsed.abuse_description)

        return agent_msg
    except ValidationError as e:
        return helper_lock_with_strike(conversation, "OpenAI Safety")


def send_message_for_assessment(conversation_id, message):
    client = get_client()
    conversation = AssessmentConversation.objects.get(id=conversation_id)

    UserMessage.objects.create(
        conversation=conversation,
        message=message,
        student=conversation.student,
        role="user"
    )

    try:
        response = client.responses.parse(
            model=settings.OPENAI_MODEL_FOR_ASSESSMENT,
            input=conversation.to_openai_json(),
            text_format=AssessmentAgentResponse,
            user=str(conversation.student.id)
        )

        agent_msg = AgentMessage.objects.create(
            conversation=conversation,
            message=response.output_parsed.output_text,
            agent=conversation.agent,
            role="agent",
            message_id=response.id
        )

        if response.output_parsed.end_convo_for_abuse:
            conversation.locked = True
            conversation.credit_awarded = False
            conversation.lock_reason = response.output_parsed.abuse_description
            conversation.save()
        elif response.output_parsed.convo_finished:
            conversation.locked = True
            conversation.lock_reason = "Assessment Finished"
            conversation.credit_awarded = response.output_parsed.credit_awarded
            conversation.understanding_score = response.output_parsed.understanding_score
            conversation.feedback = response.output_parsed.feedback
            conversation.save()

        return agent_msg
    except ValidationError as e:
        agent_msg = AgentMessage.objects.create(
            conversation=conversation,
            message="There was en error. Please contact Tr. Canora.",
            agent=conversation.agent,
            role="agent",
            message_id=f"safety-{uuid.uuid4()}"
        )

        conversation.locked = True
        conversation.credit_awarded = False
        conversation.lock_reason = "OpenAI Safety"
        conversation.save()

        return agent_msg


def generate_summary(conversation_id):
    client = get_client()
    conversation = Conversation.objects.get(id=conversation_id)

    prompt = [
        {"role": "system",
         "content": "Respond with a few words reflecting the purpose of the conversation. " +
                    "This will be displayed in the format 'talking with an assistant about <blank>'. " +
                    "Respond only with what should replace the <blank> placeholder."},
        {"role": "user", "content": json.dumps(conversation.info_for_summary())}
    ]

    response = client.responses.create(
        model=settings.OPENAI_MODEL_FOR_SUMMARY,
        input=prompt,
        user=str(conversation.student.id)
    )

    conversation.summary = response.output_text
    conversation.save()
