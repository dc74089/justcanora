from django.contrib.admin.views.decorators import staff_member_required
from django.db import models
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from aitutor.models import Agent, Assessment, AssessmentConversation, Conversation, Strike


@staff_member_required
def staff_dashboard(request):
    # Chat conversations (not assessments) that were locked for abuse/safety.
    flagged = Conversation.objects.filter(assessmentconversation__isnull=True, locked=True).count()

    # Students who currently trip the ban thresholds (3 strikes/week or 5 total).
    striked_students = {s.student for s in Strike.objects.select_related('student')}
    banned = sum(1 for s in striked_students if Strike.is_banned(s))

    recent_completions = (AssessmentConversation.objects
                          .filter(locked=True, lock_reason="Assessment Finished")
                          .select_related('student', 'assessment')
                          .annotate(last_activity=models.Max('message__time'))
                          .order_by('-last_activity')[:8])

    return render(request, 'aitutor/dashboard.html', {
        "flagged": flagged,
        "banned": banned,
        "assessment_count": Assessment.objects.count(),
        "agent_count": Agent.objects.exclude(id=Agent.get_assessment_agent().id).count(),
        "recent_completions": recent_completions,
    })


@staff_member_required
def strikes_panel(request):
    by_student = {}
    for strike in Strike.objects.select_related('student', 'conversation').order_by('-time'):
        by_student.setdefault(strike.student, []).append(strike)

    rows = [{
        "student": student,
        "strikes": strikes,
        "count": len(strikes),
        "banned": Strike.is_banned(student),
    } for student, strikes in by_student.items()]

    # Banned students first, then by strike count.
    rows.sort(key=lambda r: (not r["banned"], -r["count"]))

    return render(request, 'aitutor/strikes.html', {
        "rows": rows,
    })


@csrf_exempt
@staff_member_required
def clear_strike(request):
    """Delete a single strike — clears it toward the ban thresholds."""
    Strike.objects.filter(id=request.POST['strike_id']).delete()
    return HttpResponse(status=200)
