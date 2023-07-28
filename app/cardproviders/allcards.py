from .account import allcards as all_acct
from .fun import allcards as all_fun
from .music import allcards as all_music


def allcards(request):
    ret = []
    ret.extend(all_fun(request))
    ret.extend(all_acct(request))
    ret.extend(all_music(request))
    return ret
