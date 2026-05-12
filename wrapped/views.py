import queue
import threading
import traceback

from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponseForbidden, HttpResponseBadRequest
from django.shortcuts import render

from app.canvas.canvas import get_canvas

_generation_queue: queue.Queue = queue.Queue()


def _generation_worker():
    while True:
        student = _generation_queue.get()
        try:
            print(f"[wrapped] Starting generation for {student.full_name()} ({student.id})")
            get_all_for_student(student)
            rank_all()
            print(f"[wrapped] Finished generation for {student.full_name()} ({student.id})")
        except Exception:
            traceback.print_exc()
        finally:
            _generation_queue.task_done()


threading.Thread(target=_generation_worker, daemon=True).start()
from app.models import Student
from .models import Wrapped, TeacherWrapped
from .utils.wrapped_student import get_all_for_student, rank_all


def wrapped(request):
    if not request.user.is_authenticated:
        return HttpResponseForbidden()

    if not Wrapped.objects.filter(student=request.user.student).exists():
        return HttpResponseBadRequest()

    return render(request, 'wrapped/wrapped2026.html', {
        'data': Wrapped.objects.get(student=request.user.student),
        'now_playing_available': False
    })


def wrapped_direct(request, key):
    return render(request, 'wrapped/wrapped2026.html', {
        'data': Wrapped.objects.get(direct_link=key),
        'now_playing_available': False
    })


@staff_member_required
def ranks(request):
    wrappeds = list(Wrapped.objects.select_related('student').all())

    categories = [
        ("Songs", "rank_songs", "num_songs"),
        ("Assignments", "rank_assignments", "num_assignments"),
        ("Late", "rank_late", "num_late"),
        ("Canvas Minutes", "rank_canvas_minutes", "num_canvas_minutes"),
        ("Canvas Clicks", "rank_canvas_clicks", "num_canvas_clicks"),
    ]

    data = [
        {
            "label": label,
            "items": [
                {"student": w.student, "value": getattr(w, value_field)}
                for w in sorted(wrappeds, key=lambda w: getattr(w, rank_field) or float('inf'))
                if getattr(w, rank_field) is not None
            ],
        }
        for label, rank_field, value_field in categories
    ]

    return render(request, "wrapped/ranks.html", {"data": data})


@staff_member_required
def student_data(request):
    ctx = {}

    if request.method == 'POST':
        raw_id = request.POST.get('canvas_id', '').strip()
        try:
            canvas_id = int(raw_id)
        except ValueError:
            ctx['error'] = f"'{raw_id}' is not a valid Canvas ID."
        else:
            try:
                canvas = get_canvas()
                canvas_user = canvas.get_user(canvas_id)
            except Exception as e:
                ctx['error'] = f"Canvas user {canvas_id} not found: {e}"
            else:
                student, student_created = Student.objects.get_or_create(id=canvas_id)
                if student_created or not (student.fname and student.lname):
                    student.lname = canvas_user.sortable_name.split(',')[0].strip()
                    student.fname = canvas_user.sortable_name.split(',')[-1].strip()
                    try:
                        student.email = canvas_user.login_id
                    except AttributeError:
                        pass
                    student.save()

                wrapped, _ = Wrapped.objects.get_or_create(student=student)
                wrapped.manual = True
                wrapped.save()

                _generation_queue.put(student)
                ctx['queued'] = student

    ctx['manual_wrappeds'] = Wrapped.objects.filter(manual=True).order_by('student__fname')
    ctx['data'] = Wrapped.objects.all().order_by('student__fname')
    return render(request, "wrapped/student_data.html", ctx)


@staff_member_required
def teacher_data(request):
    return render(request, "wrapped/teacher_data.html", {
        "data": TeacherWrapped.objects.all().order_by('name')
    })


def wrapped_teacher(request, key):
    tw = TeacherWrapped.objects.get(key=key)

    return render(request, 'wrapped/teacherwrapped2026.html', {
        'data': tw,
        'now_playing_available': False
    })


def wrapped_demo(request):
    if 'student' in request.GET:
        return render(request, 'wrapped/wrapped2026.html', {
            'data': Wrapped.objects.get(student=Student.objects.get(id=int(request.GET['student']))),
            'now_playing_available': False
        })
    else:
        return render(request, 'wrapped/wrapped2026.html', {
            'data': Wrapped.objects.get(student=Student.objects.get(id=3345)),
            'now_playing_available': False
        })


def wrapped_teacher_demo(request):
    return render(request, 'wrapped/teacherwrapped2026.html', {
        'data': TeacherWrapped.objects.get(teacher_id=11862),
        'now_playing_available': False
    })



@staff_member_required
def admin(request):
    all_wrappeds = Wrapped.objects.all()
    return render(request, 'wrapped/admin.html', {
        'total': all_wrappeds.count(),
        'manual_count': all_wrappeds.filter(manual=True).count(),
        'no_data_count': all_wrappeds.filter(num_assignments__isnull=True).count(),
        'queue_size': _generation_queue.qsize(),
    })