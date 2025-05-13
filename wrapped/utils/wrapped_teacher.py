from datetime import timedelta

from tqdm import tqdm

from app.canvas.canvas import get_canvas

from dateutil import parser

from wrapped.models import TeacherWrapped

all_ms_teachers = [
    1544, # Bartz
    1549, # Brewer
    8035, # Capers
    1592, # Cortelyou
    8045, # Darden
    1723, # Daugherty
    1546, # Denard
    11858, # Fitz
    11862, # Funston
    14543, # Gaudreault
    4542, # Glascock
    8000, # Goodman
    4219, # Gower
    2618, # Harris
    9881, # Higgs
    1552, # Hujik
    1553, # R. Lee
    13153, # Mercado
    1635, # Pazmino
    4220, # Rassa
    1705, # Robelo
    1687, # Schaeffer
    8015, # Shaffer
    9880, # Stein
    1557, # Sweet
    1558, # Vander Meulen
    11859, # Walsh
    4644, # Wang
    1690, # Young
    14546, # Ziegler
]


def do_all():
    for teacher_id in tqdm(all_ms_teachers):
        try:
            get_all_for_teacher(teacher_id)
        except:
            print(f"Problem with {teacher_id}")


def get_sample():
    get_all_for_teacher(11862)


def get_all_for_teacher(canvas_id):
    get_user_info(canvas_id)
    get_course_stats(canvas_id)
    get_pageview_stats(canvas_id)


def get_user_info(teacher_id):
    canvas = get_canvas()
    u = canvas.get_user(teacher_id)

    tw, _ = TeacherWrapped.objects.get_or_create(teacher_id=teacher_id)
    tw.email = u.email
    tw.name = u.name
    tw.display_name = u.short_name

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
