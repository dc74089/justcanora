import json
import os
import uuid

from pydantic import BaseModel, ValidationError

from aitutor.models import Conversation, UserMessage, AgentMessage, AssessmentConversation


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
        response = client.responses.parse(
            model="o4-mini",
            input=conversation.to_openai_json(student=student),
            text_format=AgentResponse
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
            conversation.locked = True
            conversation.lock_reason = response.output_parsed.abuse_description
            conversation.save()

        return agent_msg
    except ValidationError as e:
        agent_msg = AgentMessage.objects.create(
            conversation=conversation,
            message="I'm sorry, I can't help with that.",
            agent=conversation.agent,
            role="agent",
            message_id=f"safety-{uuid.uuid4()}"
        )

        conversation.locked = True
        conversation.lock_reason = "OpenAI Safety"
        conversation.save()

        return agent_msg


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
            model="o3",
            input=conversation.to_openai_json(),
            text_format=AssessmentAgentResponse
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
        model="o4-mini",
        input=prompt
    )

    conversation.summary = response.output_text
    conversation.save()
