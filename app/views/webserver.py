from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render

from app.models import WebserverCredential


def instructions(request):
    creds: WebserverCredential = WebserverCredential.objects.filter(student=request.user.student).first()

    return render(request, "app/webserver/instructions.html", {
        "creds": creds,
    })


@staff_member_required
def all_table(request):
    return render(request, "app/webserver/all_table.html", {
        "creds": WebserverCredential.objects.all().order_by('student__lname')
    })