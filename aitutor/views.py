from django.shortcuts import render

from aitutor.models import Conversation


# Create your views here.
def conversation_select(request):
    convs = Conversation.objects.filter(student=request.user.student)

    return render(request, "aitutor/conversation_select.html", {
        "conversations": convs
    })


def conversation(request, conv_id):
    pass