import logging

from app.canvas.canvas import get_canvas

logger = logging.getLogger(__name__)


def post_assessment_grade(conversation):
    """Push a finished AssessmentConversation to its Canvas assignment.

    Posts a complete/incomplete grade based on ``credit_awarded`` and attaches
    the assessment feedback as a submission comment. Only meant to be called on
    a good-faith completion — abuse-locked conversations are never posted.

    Never raises: a Canvas outage must not break assessment completion for the
    student, so failures are logged and swallowed.
    """
    assessment = conversation.assessment

    try:
        canvas = get_canvas()
        course = canvas.get_course(assessment.course.course_id)
        assignment = course.get_assignment(assessment.canvas_assignment_id)
        submission = assignment.get_submission(conversation.student.id)

        kwargs = {
            "submission": {
                "posted_grade": "complete" if conversation.credit_awarded else "incomplete"
            }
        }
        if conversation.feedback:
            kwargs["comment"] = {"text_comment": conversation.feedback}

        submission.edit(**kwargs)

        logger.info(
            "Posted assessment '%s' (%s) for student %s to Canvas assignment %s",
            assessment.short_name,
            "complete" if conversation.credit_awarded else "incomplete",
            conversation.student.id,
            assessment.canvas_assignment_id,
        )
    except Exception:
        logger.exception(
            "Failed to post assessment grade to Canvas for conversation %s",
            conversation.id,
        )
