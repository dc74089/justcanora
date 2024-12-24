from .account import allcards as all_acct
from .fun import allcards as all_fun
from .links import allcards as all_links
from .lunch import allcards as all_lunch
from .music import allcards as all_music
from .speech import allcards as all_speech


def allcards(request):
    ret = []
    ret.extend(all_fun(request))
    ret.extend(all_links(request))
    ret.extend(all_lunch(request))
    ret.extend(all_acct(request))
    ret.extend(all_speech(request))
    ret.extend(all_music(request))
    return ret
