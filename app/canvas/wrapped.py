from contextlib import suppress
from datetime import timedelta

from dateutil import parser
from tqdm import tqdm

from app.canvas.canvas import get_canvas
from app.models import Student, Wrapped, MusicSuggestion


def get_all():
    for student in tqdm(Student.objects.all().exclude(id__in=[2224])):
        try:
            get_all_for_student(student)
        except:
            print(f"Problem with {student.name()}")


def get_all_for_student(student: Student):
    get_song_stats(student)
    get_assignment_stats(student)
    get_pageview_stats(student)


def get_all_for_student_by_id(sid: int):
    stu = Student.objects.get(id=sid)
    get_all_for_student(stu)


def rank_all():
    num_songs = sorted([x.num_songs for x in Wrapped.objects.all() if x.num_songs], reverse=True)
    num_assignments = sorted([x.num_assignments for x in Wrapped.objects.all() if x.num_assignments], reverse=True)
    num_late = sorted([x.num_late for x in Wrapped.objects.all() if x.num_late], reverse=True)
    num_canvas_minutes = sorted([x.num_canvas_minutes for x in Wrapped.objects.all() if x.num_canvas_minutes],
                                reverse=True)
    num_canvas_clicks = sorted([x.num_canvas_clicks for x in Wrapped.objects.all() if x.num_canvas_clicks],
                               reverse=True)

    for wrapped in Wrapped.objects.all():
        with suppress(ValueError): wrapped.rank_songs = num_songs.index(wrapped.num_songs)
        with suppress(ValueError): wrapped.rank_assignments = num_assignments.index(wrapped.num_assignments)
        with suppress(ValueError): wrapped.rank_late = num_late.index(wrapped.num_late)
        with suppress(ValueError): wrapped.rank_canvas_minutes = num_canvas_minutes.index(wrapped.num_canvas_minutes)
        with suppress(ValueError): wrapped.rank_canvas_clicks = num_canvas_clicks.index(wrapped.num_canvas_clicks)

        wrapped.save()


def get_assignment_stats(student: Student):
    canvas = get_canvas()
    cs = canvas.get_user(student.id)

    assignments = 0
    late = 0

    for course in cs.get_courses():
        cc = canvas.get_course(course.id)
        for sub in cc.get_multiple_submissions(
                student_ids=[cs.id],
                submitted_since="2024-08-01T00:00:00Z"
        ):
            assignments += 1
            if sub.late:
                late += 1

    sw, _ = Wrapped.objects.get_or_create(student=student)

    sw.num_assignments = assignments
    sw.num_late = late

    sw.save()


def get_pageview_stats(student: Student):
    canvas = get_canvas()
    cs = canvas.get_user(student.id)

    pageviews = 0
    sessions = 0
    seconds = 0

    session_start = None
    last_req = None

    for req in cs.get_page_views(start_time="2024-08-01T00:00:00Z"):
        # Starts at now, goes backwards
        pageviews += 1

        if not session_start:
            session_start = parser.parse(req.created_at)
            last_req = req
            continue

        time = parser.parse(req.created_at)
        last_time = parser.parse(last_req.created_at)

        if last_time - time > timedelta(minutes=30):
            sessions += 1
            session_len = (session_start - last_time).seconds

            if session_len // 60 // 60 < 8:
                print("Finishing Session")
                seconds += session_len
            else:
                print("DISCARDING LONG SESSION")

            session_start = None

        last_req = req

    print(f"Pageviews: {pageviews}")
    print(f"Sessions: {sessions}")
    print(f"Seconds: {seconds}")

    sw, _ = Wrapped.objects.get_or_create(student=student)

    sw.num_canvas_clicks = pageviews
    sw.num_canvas_minutes = seconds // 60

    sw.save()


def get_song_stats(student: Student):
    sw, _ = Wrapped.objects.get_or_create(student=student)

    sw.num_songs = MusicSuggestion.objects.filter(student=student).count()
    sw.num_songs_rejected = MusicSuggestion.objects.filter(student=student, is_rejected=True).count()

    sw.save()
