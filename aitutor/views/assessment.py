from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.views.decorators.http import require_POST

from app.models import Course
from aitutor.models import Assessment, AssessmentConversation, Agent
from aitutor.utils import claude
from aitutor.utils.grades import post_assessment_grade


@login_required
def start_assessment(request, assessment_id):
    assessment = Assessment.objects.get(id=assessment_id)
    student = request.user.student

    # Only students enrolled in the assessment's course may start it (staff can
    # always launch, e.g. to preview). Otherwise anyone with the UUID could.
    if not request.user.is_staff and not student.courses.filter(pk=assessment.course_id).exists():
        return HttpResponseForbidden()

    ac, created = AssessmentConversation.objects.get_or_create(assessment=assessment, student=student, agent=Agent.get_assessment_agent())

    return redirect('chat_assessment', ac.id)


@login_required
def assessment(request, conversation_id):
    conversation = AssessmentConversation.objects.get(id=conversation_id)

    if conversation.student != request.user.student:
        return HttpResponseForbidden()

    start_failed = False
    if conversation.messages().count() == 0 and not conversation.locked:
        try:
            claude.send_message_for_assessment(conversation.id, "I am ready to start.")
        except claude.TransientAgentError:
            # Couldn't get the opening question. The conversation is untouched, so
            # reloading retries cleanly rather than leaving a dead blank page.
            start_failed = True

    return render(request, 'aitutor/assessment.html', {
        "conversation": conversation,
        "start_failed": start_failed,
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


@login_required
@require_POST
def assessment_send_message(request):
    data = request.POST
    conv = get_object_or_404(AssessmentConversation, id=data.get('conv_id'))

    if conv.student != request.user.student:
        return HttpResponseForbidden()

    # A finished/locked assessment is immutable — ignore further messages so a
    # student can't re-run scoring and overwrite their own result.
    if conv.locked:
        return HttpResponse(status=200)

    message = data.get("message", "").strip()
    if not message:
        return HttpResponseBadRequest("Message cannot be empty.")

    try:
        claude.send_message_for_assessment(conv.id, message)
    except claude.TransientAgentError:
        # Answer rolled back and the assessment is still open — resend to retry.
        return HttpResponse("The tutor is temporarily unavailable. Please try again.", status=503)

    return HttpResponse(status=200)


def gradebook_row(student, conv, enrolled=True):
    """One roster row for the staff gradebook: the student and, if they've
    engaged, the state of their assessment conversation."""
    if conv is None:
        status = "not_started"
    elif not conv.locked:
        status = "in_progress"
    elif conv.lock_reason == "Assessment Finished":
        status = "completed"
    else:
        status = "locked"

    return {
        "student": student,
        "conv": conv,
        "status": status,
        "score": conv.understanding_score if conv else None,
        "score_pct": conv.score_as_percent() if conv else 0,
        "credit": conv.credit_awarded if conv else False,
        "feedback": conv.feedback if conv else "",
        "lock_reason": conv.lock_reason if conv else "",
        "enrolled": enrolled,
    }


def build_gradebook():
    """Assemble a per-assessment gradebook: the course roster crossed with each
    student's conversation, plus summary stats. Surfaces students who have not
    started (invisible in the raw AssessmentConversation list)."""
    books = []

    for assessment in Assessment.objects.select_related("course").order_by("course__name", "short_name"):
        convos = {
            c.student_id: c
            for c in AssessmentConversation.objects.filter(assessment=assessment).select_related("student")
        }

        rows = []
        seen = set()
        for student in assessment.course.students_sorted():
            rows.append(gradebook_row(student, convos.get(student.id)))
            seen.add(student.id)

        # Conversations from students no longer on the roster (transfers, etc.).
        for student_id, conv in convos.items():
            if student_id not in seen:
                rows.append(gradebook_row(conv.student, conv, enrolled=False))

        completed = [r for r in rows if r["status"] == "completed"]
        scored = [r["score"] for r in completed if r["score"] is not None]
        credited = sum(1 for r in completed if r["credit"])

        books.append({
            "assessment": assessment,
            "rows": rows,
            "stats": {
                "roster": len(rows),
                "started": sum(1 for r in rows if r["status"] != "not_started"),
                "completed": len(completed),
                "completion_pct": round(len(completed) * 100 / len(rows)) if rows else 0,
                "avg_score": round(sum(scored) / len(scored), 1) if scored else None,
                "credit_pct": round(credited * 100 / len(completed)) if completed else 0,
            },
        })

    return books


@login_required
def assessment_results(request):
    if request.user.is_staff:
        return render(request, "aitutor/assessment_gradebook.html", {
            "gradebook": build_gradebook(),
            "courses": Course.objects.order_by('-year', 'name'),
        })

    return render(request, "aitutor/assessment_results.html", {
        "convos": AssessmentConversation.objects.filter(student=request.user.student, locked=True),
    })


@login_required
def assessment_results_get_convo(request):
    conv = AssessmentConversation.objects.get(id=request.GET['conv_id'])

    # Staff may read any transcript; a student may read only their own finished one.
    if not request.user.is_staff and (conv.student != request.user.student or not conv.locked):
        return HttpResponseForbidden()

    return render(request, 'aitutor/partial_chat_conversation.html', {
        "conversation": conv,
        "messages": conv.messages(),
        "hide_bar": True
    })


@staff_member_required
@require_POST
def assessment_repost(request):
    """Re-push a finished assessment's grade to Canvas — useful when the original
    passback failed (post_assessment_grade logs and swallows Canvas errors)."""
    conv = AssessmentConversation.objects.get(id=request.POST['conv_id'])
    post_assessment_grade(conv)
    return HttpResponse(status=200)


@staff_member_required
@require_POST
def assessment_reopen(request):
    """Unlock a finished/locked assessment so the student can continue or redo it."""
    conv = AssessmentConversation.objects.get(id=request.POST['conv_id'])
    conv.locked = False
    conv.lock_reason = None
    conv.save()
    return HttpResponse(status=200)


@staff_member_required
@require_POST
def assessment_override(request):
    """Manually set a student's score/credit/feedback and re-sync to Canvas."""
    conv = AssessmentConversation.objects.get(id=request.POST['conv_id'])

    try:
        score = max(1, min(5, int(request.POST['score'])))
    except (KeyError, ValueError):
        return HttpResponseBadRequest()

    conv.understanding_score = score
    conv.credit_awarded = request.POST.get('credit') == 'true'
    if request.POST.get('feedback'):
        conv.feedback = request.POST['feedback']
    conv.locked = True
    conv.lock_reason = "Overridden by teacher"
    conv.save()

    post_assessment_grade(conv)

    return HttpResponse(status=200)


@staff_member_required
def assessment_detail(request):
    """Return an assessment's fields as JSON so the gradebook can pre-fill the
    form when cloning."""
    a = Assessment.objects.get(id=request.GET['assessment_id'])
    return JsonResponse({
        "short_name": a.short_name,
        "course_id": a.course_id,
        "canvas_assignment_id": a.canvas_assignment_id,
        "prompt": a.prompt,
    })


@staff_member_required
@require_POST
def assessment_save(request):
    """Create an assessment from the gradebook form (also the target for a
    cloned assessment — the form is pre-filled from the source, saved as new)."""
    data = request.POST
    short_name = data.get('short_name', '').strip()
    prompt = data.get('prompt', '').strip()

    if not short_name or not prompt:
        return HttpResponseBadRequest("Short name and prompt are required.")

    if Assessment.objects.filter(short_name=short_name).exists():
        return HttpResponseBadRequest("An assessment with that short name already exists.")

    try:
        course = Course.objects.get(id=data['course_id'])
        canvas_assignment_id = int(data['canvas_assignment_id'])
    except (KeyError, ValueError, Course.DoesNotExist):
        return HttpResponseBadRequest("Pick a course and enter a numeric Canvas assignment ID.")

    Assessment.objects.create(
        short_name=short_name,
        course=course,
        canvas_assignment_id=canvas_assignment_id,
        prompt=prompt,
    )

    return HttpResponse(status=200)
