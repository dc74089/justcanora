from django.contrib.admin.views.decorators import staff_member_required
from django.db import models
from django.shortcuts import render

from aitutor.models import Conversation


@staff_member_required
def moderate(request):
    convs = (Conversation.objects
             .filter(assessmentconversation__isnull=True)
             .annotate(last_activity=models.Max('message__time'))
             .order_by('-last_activity'))

    return render(request, "aitutor/moderation.html", {
        "conversations": convs
    })


@staff_member_required
def moderation_get_conversation(request):
    conv = Conversation.objects.get(id=request.GET['conv_id'])

    return render(request, 'aitutor/partial_chat_conversation.html', {
        "conversation": conv,
        "messages": conv.messages(),
        "hide_bar": True
    })
