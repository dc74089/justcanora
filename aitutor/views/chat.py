from django.contrib.auth.decorators import login_required
from django.db import models
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse, HttpResponseBadRequest
from django.shortcuts import render, get_object_or_404
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

from aitutor.models import Conversation, Agent, AgentMessage, Strike
from aitutor.utils import claude
from aitutor.utils.enrollment import tutor_languages


def selectable_agents(student):
    """Agents a student is allowed to open a conversation with: visible, matching
    a language they're enrolled in, and never the internal assessment agent
    (whose language is 'na', so the language filter already excludes it)."""
    return (Agent.objects
            .exclude(id=Agent.get_assessment_agent().id)
            .filter(hidden=False, language__in=tutor_languages(student)))


@login_required
def chat_home(request):
    if Strike.is_banned(request.user.student):
        return render(request, 'aitutor/ban.html')

    languages = tutor_languages(request.user.student)

    # Every course they're in has the tutor switched off (or they're in none).
    # Reachable by bookmark even though the nav link is hidden.
    if not languages:
        return render(request, 'aitutor/unavailable.html')

    empty_convs = Conversation.objects.filter(student=request.user.student).filter(message__isnull=True)
    empty_convs.delete()

    agents = selectable_agents(request.user.student).order_by('name', 'language')

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


@login_required
@require_POST
def chat_new_conversation(request):
    if Strike.is_banned(request.user.student):
        return HttpResponseForbidden()

    # Validate the agent against what this student may actually use — otherwise
    # any agent_id opens a conversation, including hidden agents and agents for
    # a language they aren't enrolled in.
    try:
        agent_id = int(request.POST['agent_id'])
    except (KeyError, TypeError, ValueError):
        return HttpResponseBadRequest("Missing or malformed agent_id.")

    agent = get_object_or_404(selectable_agents(request.user.student), id=agent_id)

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


@login_required
@require_POST
def chat_send_message(request):
    data = request.POST
    conv = get_object_or_404(Conversation, id=data.get('conv_id'))

    if conv.student != request.user.student:
        return HttpResponseForbidden()

    # These two were previously enforced only by the template (which hides the
    # composer) — so a stale tab or a direct POST bypassed both. A banned student
    # could keep chatting indefinitely, and a conversation locked for abuse could
    # be continued.
    if Strike.is_banned(request.user.student):
        return HttpResponseForbidden("You are currently blocked from using the tutor.")

    if conv.locked:
        return HttpResponseForbidden("This conversation is locked.")

    # The tutor has been switched off for this conversation's course, so existing
    # threads go read-only rather than staying reachable from an open tab.
    if conv.agent.language not in tutor_languages(request.user.student):
        return HttpResponseForbidden("The tutor is not available for this class right now.")

    message = data.get("message", "").strip()
    if not message:
        return HttpResponseBadRequest("Message cannot be empty.")

    try:
        resp: AgentMessage = claude.send_message(conv.id, message, student=request.user.student)
    except claude.TransientAgentError:
        # Nothing was written; the student can just send again.
        return HttpResponse("The tutor is temporarily unavailable. Please try again.", status=503)

    if resp.conversation.has_strike():
        return HttpResponseForbidden()

    return HttpResponse(status=200)
