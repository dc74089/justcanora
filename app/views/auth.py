import pprint

from django.contrib.auth import authenticate, login as do_login, logout as do_logout
from django.contrib.auth.models import User
from django.http import HttpResponseBadRequest
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from google.auth.transport import requests
from google.oauth2 import id_token

from app.models import Student
from app.spotify import spotify


def login(request):
    if request.method == 'GET':
        return render(request, 'app/login.html', {
            'next': request.GET.get('next', ''),
        })
    else:
        data = request.POST
        if 'username' in data and 'password' in data:
            user = authenticate(request, username=data['username'], password=data['password'])

            if user is not None:
                do_login(request, user)
                if request.GET.get('next', ""):
                    return redirect(request.GET['next'])

                return redirect('index')
            else:
                return render(request, 'app/login.html', {
                    'next': request.GET.get('next', ''),
                    'error': "Incorrect username or password."
                })

    return HttpResponseBadRequest()


def logout(request):
    request.session.clear()
    request.session.save()
    do_logout(request)
    return redirect('index')


@csrf_exempt
def google(request):
    data = request.POST

    try:
        # Specify the CLIENT_ID of the app that accesses the backend:
        idinfo = id_token.verify_oauth2_token(data['credential'], requests.Request(),
                                              "966461905987-nsfekbdp870jo9sarfkn078hle1hbj0u.apps.googleusercontent.com")
        print(idinfo)

        # ID token is valid. Get the user's Google Account ID from the decoded token.
        email = idinfo['email']

        if 'hd' not in idinfo or idinfo['hd'] != 'lhprep.org':
            return render(request, 'app/error.html', {
                "short": "This site is available for LHPS students only",
                "message": f"Please make sure you select your @lhprep.org email when you log in.\n\nYou tried to sign in as {email}."
            })

        uq = User.objects.filter(email=email)

        if uq.exists():
            user = uq.first()
            student = user.student

            if not student.is_active():
                return render(request, 'app/error.html', {
                    "short": "This site is available for Tr. Canora's current students only",
                    "message": f"We found a student with that email address, but they are not in any active classes. Please show this screen to Tr. Canora so they can fix it.\n\n{pprint.pformat(idinfo)}"
                })

            do_login(request, uq.first(), backend='django.contrib.auth.backends.ModelBackend')

            return redirect('index')
        else:
            # New User
            sq = Student.objects.filter(email=email)

            if sq.exists():
                stu: Student = sq.first()

                if not stu.is_active():
                    return render(request, 'app/error.html', {
                        "short": "This site is available for Tr. Canora's current students only",
                        "message": f"We found a student with that email address, but they are not in any active classes. Please show this screen to Tr. Canora so they can fix it.\n\n{pprint.pformat(idinfo)}"
                    })

                u = User(username=email, email=email)
                u.save()

                stu.user = u
                stu.save()

                do_login(request, u, backend='django.contrib.auth.backends.ModelBackend')
                return redirect('index')
            else:
                return render(request, 'app/error.html', {
                    "short": "I don't know of a student with that email",
                    "message": f"We can't find a student with that email address. Please show this screen to Tr. Canora so they can fix it.\n\n{pprint.pformat(idinfo)}"
                })

    except ValueError as e:
        # Invalid token
        print(e)


def spotify_response(request):
    if 'error' in request.GET:
        return render(request, 'app/error.html')

    print("Setting token for DB")
    spotify.get_auth_manager(request).get_access_token(request.GET.get('code'), check_cache=False)

    return redirect(request.session.pop('next', 'index'))
