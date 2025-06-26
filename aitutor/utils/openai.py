import json
import os
import uuid

from pydantic import BaseModel, ValidationError

from aitutor.models import Conversation, UserMessage, AgentMessage


class AgentResponse(BaseModel):
    output_text: str
    end_convo_for_abuse: bool
    abuse_description: str


def get_client():
    from openai import OpenAI
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))


def send_message(conversation_id, message):
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
            input=conversation.to_openai_json(),
            text_format=AgentResponse
        )

        agent_msg = AgentMessage.objects.create(
            conversation=conversation,
            message=response.output_parsed.output_text,
            agent=conversation.agent,
            role="agent",
            message_id=response.id
        )

        if not conversation.summary:
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
