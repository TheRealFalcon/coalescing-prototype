import errno
import socket
import time
from contextlib import suppress
from queue import Queue, Empty
from threading import Thread

import settings
from utilities import get_message, DataPoint

QUEUE_GET_TIMEOUT = .000001  # Basically just a context switch


def sendall(client, messages):
    """ Like client.sendall but faster and non-blocking """
    while len(messages):
        try:
            sent = client.send(messages)
            messages = messages[sent:]
        except socket.error as e:
            if e.errno != errno.EAGAIN:
                raise e
            time.sleep(.000001)  # basically just a context switch


def coalescing_flusher(queue, client):
    """ Consumes all messages from queue, batches, and sends them after QUEUE_WAIT_TIME has elapsed """
    start_time = None
    messages = b''
    message_count = 0
    while message_count <= settings.TOTAL_MESSAGES or messages:
        with suppress(Empty):
            message = queue.get(timeout=QUEUE_GET_TIMEOUT)
            messages += message
            message_count += 1
            if not start_time:
                start_time = time.time()
        if start_time and (time.time() - start_time > settings.QUEUE_WAIT_TIME):
            sendall(client, messages)
            messages = b''
            start_time = None


def simple_flusher(queue, client):
    """ Consumes all messages from queue and sends them to server without any additional processing """
    message_count = 0
    while message_count <= settings.TOTAL_MESSAGES:
        with suppress(Empty):
            message = queue.get(timeout=QUEUE_GET_TIMEOUT)
            sendall(client, message)
            message_count += 1


def send(queue, message):
    queue.put(message)


def test_threaded(client, flusher):
    queue = Queue(settings.MAX_QUEUE_SIZE)
    t = Thread(target=flusher, args=(queue, client))
    t.start()

    try:
        for index in range(settings.TOTAL_MESSAGES):
            message = get_message()
            yield DataPoint(message, time.time())
            send(queue, message)
        send(queue, settings.STOP_MESSAGE)
    finally:
        t.join()


def test_threaded_coalesce(client):
    return test_threaded(client, coalescing_flusher)


def test_threaded_no_coalesce(client):
    return test_threaded(client, simple_flusher)


def test_simple_coalescing(client):
    messages = b''
    start_time = time.time()
    for index in range(settings.TOTAL_MESSAGES):
        message = get_message()
        arrived_time = time.time()
        yield DataPoint(message, arrived_time)
        messages += message
        if arrived_time - start_time > settings.QUEUE_WAIT_TIME or index == settings.TOTAL_MESSAGES - 1:
            sendall(client, messages)
            messages = b''
            start_time = time.time()
    sendall(client, settings.STOP_MESSAGE)


def test_simple(client):
    for index in range(settings.TOTAL_MESSAGES):
        message = get_message()
        yield DataPoint(message, time.time())
        sendall(client, message)
    sendall(client, settings.STOP_MESSAGE)
