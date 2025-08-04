from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.db import models
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie

from aitutor.models import Conversation, Agent, AgentMessage, Assessment, AssessmentConversation, Strike
from aitutor.utils import openai


@login_required
def chat_home(request):
    if Strike.is_banned(request.user.student):
        return render(request, 'aitutor/ban.html')

    empty_convs = Conversation.objects.filter(student=request.user.student).filter(message__isnull=True)
    empty_convs.delete()

    agents = Agent.objects.all().exclude(id=Agent.get_assessment_agent().id).order_by('name')
    languages = []

    if 'APCSA' in request.user.student.courses.values_list('type', flat=True):
        languages.append("java")
    if 'CS2' in request.user.student.courses.values_list('type', flat=True):
        languages.append("python")

    print(languages)

    agents = agents.filter(language__in=languages)

    convs = (Conversation.objects
    .filter(student=request.user.student)
    .exclude(agent=Agent.get_assessment_agent())
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
        "agents": agents,
        "show_lang": len(languages) > 1,
    })


@csrf_exempt
@login_required
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
    .exclude(agent=Agent.get_assessment_agent())
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


@csrf_exempt
@login_required
def chat_send_message(request):
    data = request.POST
    conv = Conversation.objects.get(id=data['conv_id'])

    if conv.student != request.user.student:
        return HttpResponseForbidden()

    resp: AgentMessage = openai.send_message(conv.id, data["message"], student=request.user.student)

    if resp.conversation.has_strike():
        return HttpResponseForbidden()

    return HttpResponse(status=200)
