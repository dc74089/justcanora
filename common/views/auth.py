from django.contrib.auth import authenticate, login as do_login, logout as do_logout
from django.http import HttpResponseBadRequest
from django.shortcuts import render, redirect

from google.oauth2 import id_token
from google.auth.transport import requests


def login(request):
    if request.method == 'GET':
        return render(request, 'common/login.html')
    else:
        data = request.POST
        if 'username' in data and 'password' in data:
            user = authenticate(request, username=data['username'], password=data['password'])

            if user is not None:
                do_login(request, user)
                if data.get('next', ""):
                    return redirect(data['next'])

                return redirect('index')
            else:
                return render(request, 'common/login.html', {
                    'next': data['next'],
                    'error': "Incorrect username or password."
                })

    return HttpResponseBadRequest()


def logout(request):
    do_logout(request)
    return redirect('index')


def google(request):
    data = request.POST

    try:
        # Specify the CLIENT_ID of the app that accesses the backend:
        idinfo = id_token.verify_oauth2_token(data['credential'], requests.Request(), "966461905987-kopaakbqkpt7ac1bnku461tc32ineed3.apps.googleusercontent.com")

        # ID token is valid. Get the user's Google Account ID from the decoded token.
        domain = idinfo['hd']
        email = idinfo['email']

        # TODO: Finish auth flow

    except ValueError:
        # Invalid token
        pass
