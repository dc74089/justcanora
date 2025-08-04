from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt

from aitutor.models import Assessment, AssessmentConversation, AgentMessage, Agent
from aitutor.utils import openai


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


@login_required
def assessment_results(request):
    assessments = AssessmentConversation.objects.filter(student=request.user.student, locked=True)

    return (render(request, "aitutor/assessment_results.html", {
        'convos': assessments
    }))


@login_required
def assessment_results_get_convo(request):
    conv = AssessmentConversation.objects.get(id=request.GET['conv_id'])

    if conv.student != request.user.student or not conv.locked:
        return HttpResponseForbidden()

    return render(request, 'aitutor/partial_chat_conversation.html', {
        "conversation": conv,
        "messages": conv.messages(),
        "hide_bar": True
    })