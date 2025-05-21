import json
import os

from aitutor.models import Conversation, UserMessage, AgentMessage


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

    response = client.responses.create(
        model="o4-mini",
        input=conversation.to_openai_json(),
    )

    agent_msg = AgentMessage.objects.create(
        conversation=conversation,
        message=response.output_text,
        agent=conversation.agent,
        role="agent",
        message_id=response.id
    )

    if not conversation.summary:
        generate_summary(conversation_id)

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
