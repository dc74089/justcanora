from django.http import HttpResponseBadRequest
from django.shortcuts import redirect

from app.models import MusicSuggestion, News, DataCollectionAnswer, DataCollectionQuestion, Course, Student, \
    SpeechRating, SpeechRubric


def misc_action(request):
    if request.method == 'POST':
        data = request.POST

        if 'action' not in data: return HttpResponseBadRequest()

        if data['action'] == 'setgrade':
            s = request.user.student
            s.grade = int(data['grade'])
            s.save()
        elif data['action'] == 'setbday':
            s = request.user.student
            s.bday = data['bday']
            s.save()
        elif data['action'] == 'music':
            ms = MusicSuggestion(
                student=request.user.student,
                song=data['song_name'],
                artist=data['song_artist'],
                for_playlist=data['song_type'] == 'class'
            )
            ms.save()
        elif data['action'] == 'news':
            news = News(
                student=request.user.student,
                news=data['news'],
            )
            news.save()
        elif data['action'] == 'addquestion':
            dcq = DataCollectionQuestion(
                question=data['question']
            )
            dcq.save()
            dcq.courses.set(Course.objects.all())
            dcq.save()
        elif data['action'] == 'datacollection':
            dca = DataCollectionAnswer(
                student=request.user.student,
                question_id=data['qid'],
                answer=data['answer']
            )
            dca.save()
        elif data['action'] == 'speech_eval':
            speaker = Student.objects.get(id=data['speaker'])
            rubric = SpeechRubric.objects.get(id=data['rubric'])

            sr = SpeechRating(
                speaker=speaker,
                author=request.user.student,
                rubric=rubric
            )

            sr.save()

            ratings = {
                "rating": {rat[1]: data[rat[0]] for rat in rubric.get_rating_fields()},
                "comment": {com[1]: data[com[0]] for com in rubric.get_comment_fields()}
            }

            sr.set_data(ratings)
            sr.save()

        return redirect('index')
    elif request.method == 'GET':
        data = request.GET

        if 'action' not in data: return HttpResponseBadRequest()

        if data['action'] == 'dismissmusic':
            ms = MusicSuggestion(
                student=request.user.student,
                song='NULL',
                for_playlist=False,
                is_null=True
            )

            ms.save()
        elif data['action'] == 'dismissnews':
            n = News(
                student=request.user.student,
                is_null=True
            )

            n.save()
        elif data['action'] == 'approvespeechrating':
            evl = SpeechRating.objects.get(id=data['id'])
            evl.available_to_view = True

            evl.save()

        return redirect('index')
