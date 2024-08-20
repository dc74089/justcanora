from datetime import timedelta

import requests
from django.template.loader import render_to_string
from django.utils import timezone

from app.models import FeatureFlag


def allcards(request):
    return [x for x in [lunch_menu(request)] if x is not None]


def helper_build_menu(day):
    try:
        out = {}
        station = "Other"

        for item in day['menu_items']:
            if item.get("is_section_title"):
                station = item.get("text")

                if not station:
                    station = item.get("image_alt")

                if not station:
                    station = "Other"

                if station not in out:
                    out[station] = []
            elif item.get("food"):
                food = item['food']

                if food.get("name"):
                    out[station].append(food['name'])

        return {key: value for key, value in out.items() if value}
    except:
        return {}


def lunch_menu(request):
    flag, _ = FeatureFlag.objects.get_or_create(name='card_lunch')

    if not flag: return None

    try:
        date = timezone.now().astimezone(timezone.get_default_timezone()).date()
        tomorrow = date + timedelta(days=1)

        resp = requests.get(
            f"https://lhps.api.flikisdining.com/menu/api/weeks/school/charles-clayton-middle-school-campus-dining-hall/menu-type/lhp-us-lunch-available-daily-sides-651807093912170/{str(date.year)}/{str(date.month).zfill(2)}/{str(date.day).zfill(2)}/"
        ).json()

        menu_today = {}
        menu_tomorrow = {}

        for day in resp['days']:
            if date.strftime("%Y-%m-%d") == day['date']:
                menu_today = helper_build_menu(day)
            elif tomorrow.strftime("%Y-%m-%d") == day['date']:
                menu_tomorrow = helper_build_menu(day)

        if menu_today or menu_tomorrow:
            return render_to_string("app/cards/lunch_menu.html", request=request, context={
                "date_today": date.strftime("Today, %b %-d"),
                "date_tomorrow": tomorrow.strftime("Tomorrow, %b %-d"),
                "menu_today": menu_today,
                "menu_tomorrow": menu_tomorrow
            })

    except:
        return None
