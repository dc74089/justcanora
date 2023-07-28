import os

from canvasapi import Canvas


def get_canvas():
    return Canvas('https://lhps.instructure.com', os.getenv('CANVAS_TOKEN', '123'))
