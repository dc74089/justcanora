import logging
import os

from canvasapi import Canvas


def get_canvas():
    logging.getLogger("canvasapi").setLevel(logging.WARNING)
    return Canvas('https://lhps.instructure.com', os.getenv('CANVAS_TOKEN', '123'))
