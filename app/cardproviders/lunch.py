import requests
from django.template.loader import render_to_string
from django.utils import timezone


def allcards(request):
    return [x for x in [lunch_menu(request)] if x is not None]


def lunch_menu(request):
    try:
        date = timezone.now().date()
        resp = requests.get(
            f"https://lhps.api.flikisdining.com/menu/api/weeks/school/charles-clayton-middle-school-campus-dining-hall/menu-type/lhp-us-lunch-available-daily-sides-651807093912170/{str(date.year)}/{str(date.month).zfill(2)}/{str(date.day).zfill(2)}/"
        ).json()

        out = None

        for day in resp['days']:
            if date.strftime("%Y-%m-%d") != day['date']: continue

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

            out = {key: value for key, value in out.items() if value}

        if out:
            return render_to_string("app/cards/lunch_menu.html", request=request, context={
                "date": date,
                "menu": out
            })

    except:
        return None
