from datetime import timedelta

from app.canvas.canvas import get_canvas
from app.models import TeacherWrapped

from dateutil import parser


def get_all_for_teacher(canvas_id=11862):
    get_user_info(canvas_id)
    get_course_stats(canvas_id)
    get_pageview_stats(canvas_id)


def get_user_info(teacher_id):
    canvas = get_canvas()
    u = canvas.get_user(teacher_id)

    tw, _ = TeacherWrapped.objects.get_or_create(teacher_id=teacher_id)
    tw.email = u.email
    tw.name = u.name

    tw.save()


def get_course_stats(teacher_id):
    canvas = get_canvas()
    ct = canvas.get_user(teacher_id)

    assignments = set()

    graded = 0
    late = 0
    zero = 0

    announcements = 0

    for course in ct.get_courses(enrollment_type="teacher"):
        cc = canvas.get_course(course.id)

        for ann in canvas.get_announcements(
                context_codes=[
                    f"course_{course.id}"
                ],
                start_date="2024-08-01T00:00:00Z"
        ):
            if ann.author.get("id", 0) == teacher_id:
                announcements += 1

        for sub in cc.get_multiple_submissions(
                student_ids=["all"],
                submitted_since="2024-08-01T00:00:00Z",
                include=["total_scores"]
        ):
            if sub.workflow_state == "graded" and sub.grader_id == teacher_id:
                graded += 1

                assignments.add(sub.assignment_id)

                if sub.late:
                    late += 1

                if sub.score == 0:
                    zero += 1

    tw, _ = TeacherWrapped.objects.get_or_create(teacher_id=teacher_id)

    tw.num_announcements = announcements
    tw.num_assignments = len(assignments)
    tw.num_graded = graded
    tw.num_late = late
    tw.num_zeros = zero

    tw.save()


def get_pageview_stats(teacher_id):
    canvas = get_canvas()
    cs = canvas.get_user(teacher_id)

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

    tw, _ = TeacherWrapped.objects.get_or_create(teacher_id=teacher_id)

    tw.num_canvas_clicks = pageviews
    tw.num_canvas_minutes = seconds // 60

    tw.save()
