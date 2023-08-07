from .account import allcards as all_acct
from .datacollection import allcards as all_data
from .fun import allcards as all_fun
from .music import allcards as all_music
from .social import allcards as all_social


def allcards(request):
    ret = []
    ret.extend(all_fun(request))
    ret.extend(all_acct(request))
    ret.extend(all_data(request))
    ret.extend(all_social(request))
    ret.extend(all_music(request))
    return ret
