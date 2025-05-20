import os

from aitutor.models import Conversation, UserMessage, AgentMessage


def get_client():
    from openai import OpenAI
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))


def send_message(message, conversation_id):
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
        role="assistant"
    )

    return agent_msg