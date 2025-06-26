from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.db import models
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie

from aitutor.models import Conversation, Agent, AgentMessage, Assessment, AssessmentConversation
from aitutor.utils import openai


@login_required
def chat_home(request):
    empty_convs = Conversation.objects.filter(student=request.user.student).filter(message__isnull=True)
    empty_convs.delete()

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
        "agents": Agent.objects.all().exclude(id=Agent.get_assessment_agent().id).order_by('name')
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

    return HttpResponse(status=200)


@login_required
def start_assessment(request, assessment_id):
    assessment = Assessment.objects.get(id=assessment_id)

    ac, created = AssessmentConversation.objects.get_or_create(assessment=assessment, student=request.user.student, agent=Agent.get_assessment_agent())

    return redirect('chat_assessment', ac.id)


@login_required
def assessment(request, conversation_id):
    conversation = AssessmentConversation.objects.get(id=conversation_id)

    if conversation.student != request.user.student:
        return HttpResponseForbidden()

    if conversation.messages().count() == 0:
        openai.send_message_for_assessment(conversation.id, "I am ready to start.")

    return render(request, 'aitutor/assessment.html', {
        "conversation": conversation,
    })


@login_required
def assessment_get_messages(request, conversation_id):
    conversation = AssessmentConversation.objects.get(id=conversation_id)

    if conversation.student != request.user.student:
        return HttpResponseForbidden()

    messages = conversation.messages()
    return render(request, 'aitutor/partial_chat_conversation.html', {
        "conversation": conversation,
        "messages": messages,
        "is_assessment": True,
    })


@csrf_exempt
@login_required
def assessment_send_message(request):
    data = request.POST
    conv = AssessmentConversation.objects.get(id=data['conv_id'])

    if conv.student != request.user.student:
        return HttpResponseForbidden()

    resp: AgentMessage = openai.send_message_for_assessment(conv.id, data["message"])

    return HttpResponse(status=200)


@staff_member_required
def moderate(request):
    convs = Conversation.objects.annotate(last_activity=models.Max('message__time')).order_by('-last_activity')

    return render(request, "aitutor/moderation.html", {
        "conversations": convs
    })


@staff_member_required
def moderation_get_conversation(request):
    conv = Conversation.objects.get(id=request.GET['conv_id'])

    return render(request, 'aitutor/partial_chat_conversation.html', {
        "conversation": conv,
        "messages": conv.messages(),
        "hide_bar": True
    })
