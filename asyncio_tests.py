import asyncio
import errno
import socket
import time

import settings
from utilities import get_message, DataPoint


async def sendall(client, messages):
    """ Like client.sendall but faster and non-blocking """
    while len(messages):
        try:
            sent = client.send(messages)
            messages = messages[sent:]
        except socket.error as e:
            if e.errno != errno.EAGAIN:
                raise e
            await asyncio.sleep(0)


async def async_producer(queue):
    """ Produces all messages to send to server and puts them into the queue """
    message_times = []
    for index in range(settings.TOTAL_MESSAGES):
        message = get_message()
        message_times.append(DataPoint(message, time.time()))
        await queue.put(message)
    await queue.put(settings.STOP_MESSAGE)
    return message_times


async def simple_flusher(queue, client):
    """ Consumes all messages from queue and sends them to server without any additional processing """
    while True:
        message = await queue.get()
        await sendall(client, message)
        queue.task_done()


async def coalescing_flusher(queue, client):
    """ Consumes all messages from queue, batches, and sends them after QUEUE_WAIT_TIME has elapsed """
    start_time = None
    messages = b''
    messages_queued = 0
    while True:
        try:
            message = queue.get_nowait()
            if not start_time:
                start_time = time.time()
            messages += message
            messages_queued += 1
        except asyncio.QueueEmpty:
            await asyncio.sleep(0)

        if start_time and (time.time() - start_time > settings.QUEUE_WAIT_TIME):
            await sendall(client, messages)
            for _ in range(messages_queued):
                queue.task_done()
            messages_queued = 0
            messages = b''
            start_time = None


async def test_asyncio(client, flusher):
    queue = asyncio.Queue(maxsize=settings.MAX_QUEUE_SIZE)
    producer_task = asyncio.create_task(async_producer(queue))
    flusher_task = asyncio.create_task(flusher(queue, client))

    message_times = await producer_task
    await queue.join()

    flusher_task.cancel()
    return message_times


def test_asyncio_coalesce(client):
    return asyncio.run(test_asyncio(client, coalescing_flusher))


def test_asyncio_no_coalesce(client):
    return asyncio.run(test_asyncio(client, simple_flusher))
