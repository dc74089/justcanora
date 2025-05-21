from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt

from aitutor.models import Conversation, Agent, AgentMessage
from aitutor.utils import openai


# Create your views here.
def conversation_select(request):
    convs = Conversation.objects.filter(student=request.user.student)

    return render(request, "aitutor/conversation_select.html", {
        "conversations": convs
    })


@csrf_exempt
def conversation_start(request):
    if request.method == "GET":
        agents = Agent.objects.all().order_by('name')

        return render(request, "aitutor/conversation_start.html", {
            "agents": agents
        })
    else:
        data = request.POST
        agent = Agent.objects.get(id=data['agent_id'])

        conv = Conversation.objects.create(student=request.user.student, agent=agent)

        return JsonResponse({
            "redirect_url": reverse("conversation", args=[conv.id])
        })


def conversation(request, conv_id):
    conv = Conversation.objects.get(id=conv_id)
    messages = conv.messages()

    return render(request, "aitutor/conversation.html", {
        "conversation": conv,
        "messages": messages,
    })


@csrf_exempt
def send_message(request, conv_id):
    data = request.POST
    conv = Conversation.objects.get(id=conv_id)

    resp: AgentMessage = openai.send_message(conv.id, data["message"])

    return JsonResponse({
        "message": resp.message
    })