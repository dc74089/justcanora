from django.contrib.auth.decorators import login_required
from django.db import models
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt

from aitutor.models import Conversation, Agent, AgentMessage
from aitutor.utils import openai


@login_required
def chat_home(request):
    empty_convs = Conversation.objects.filter(student=request.user.student).filter(message__isnull=True)
    empty_convs.delete()

    convs = (Conversation.objects
    .filter(student=request.user.student)
    .annotate(last_activity=models.Max('message__time'))
    .order_by(models.Case(
        models.When(last_activity__isnull=True, then=0),
        default=1),
        '-last_activity'))

    conversations = render_to_string("aitutor/partial_chat_conversations.html", {
        "conversations": convs
    })

    return render(request, "aitutor/chat.html", {
        "conversations_bar": conversations,
        "agents": Agent.objects.all().order_by('name')
    })


@login_required
@csrf_exempt
def chat_new_conversation(request):
    data = request.POST
    agent = Agent.objects.get(id=data['agent_id'])

    empty_convs = Conversation.objects.filter(student=request.user.student).filter(message__isnull=True)
    empty_convs.delete()

    conv = Conversation.objects.create(student=request.user.student, agent=agent)

    return JsonResponse({
        "conv_id": conv.id
    })


@login_required
def chat_load_conversation(request):
    convs = (Conversation.objects
    .filter(student=request.user.student)
    .annotate(last_activity=models.Max('message__time'))
    .order_by(models.Case(
        models.When(last_activity__isnull=True, then=0),
        default=1),
        '-last_activity'))

    conv = Conversation.objects.get(id=request.GET['conv_id'], student=request.user.student)
    messages = conv.messages()

    conversations = render_to_string("aitutor/partial_chat_conversations.html", {
        "conversations": convs
    })

    content = render_to_string("aitutor/partial_chat_conversation.html", {
        "conversation": conv,
        "messages": messages,
    })

    return JsonResponse({
        "conversations": conversations,
        "content": content
    })


@login_required
@csrf_exempt
def chat_send_message(request):
    data = request.POST
    conv = Conversation.objects.get(id=data['conv_id'])

    if conv.student != request.user.student:
        return HttpResponseForbidden()

    resp: AgentMessage = openai.send_message(conv.id, data["message"])

    return HttpResponse(status=200)
