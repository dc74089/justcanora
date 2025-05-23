from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.db import models
from django.db.models import Count

from aitutor.models import Conversation, Agent, AgentMessage
from aitutor.utils import openai


# Create your views here.
@login_required
def conversation_select(request):
    # Delete conversations with no messages
    Conversation.objects.annotate(
        message_count=Count('message')
    ).filter(message_count=0).delete()

    convs = (Conversation.objects
             .filter(student=request.user.student)
             .annotate(last_activity=models.Max('message__time'))
             .order_by('-last_activity'))

    return render(request, "aitutor/conversation_select.html", {
        "conversations": convs
    })


@csrf_exempt
@login_required
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


@login_required
def conversation(request, conv_id):
    conv = Conversation.objects.get(id=conv_id)
    messages = conv.messages()

    if conv.student != request.user.student:
        return HttpResponseForbidden()

    return render(request, "aitutor/conversation.html", {
        "conversation": conv,
        "messages": messages,
    })


@csrf_exempt
@login_required()
def send_message(request, conv_id):
    data = request.POST
    conv = Conversation.objects.get(id=conv_id)

    if conv.student != request.user.student:
        return HttpResponseForbidden()

    resp: AgentMessage = openai.send_message(conv.id, data["message"])

    return JsonResponse({
        "message": resp.message
    })