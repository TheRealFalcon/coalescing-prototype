""" Things here are used by both async and non-async tests """

import random
from collections import namedtuple

import settings

rng = random.Random()
rng.seed(1)  # So the results are repeatable

DataPoint = namedtuple('DataPoint', 'data timestamp')


def get_message(size_low=1, size_high=500):
    """ Get a "random" sized number of bytes between the sizes specified """
    size = rng.randint(size_low, size_high)
    message = b'a' * (size - 1) + settings.MESSAGE_END
    return message


