"""
Server runs as a separate process (via multiprocessing).
It receives data on the socket and passes it back to the test application.
"""

import socket
import time
from contextlib import suppress
from multiprocessing import Process

import settings
from utilities import DataPoint


def server(queue):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((settings.SERVER_IP, settings.PORT))
    server.listen(1)
    c, addr = server.accept()
    server.settimeout(30)
    c.settimeout(30)
    print('Server ready')

    while True:
        with suppress(socket.timeout):
            data = c.recv(5000)
            if data:
                queue.put(DataPoint(data, time.time()))


def start_server_process(queue):
    process = Process(target=server, args=(queue,))
    process.daemon = True
    process.start()
    time.sleep(1)  # So server has enough time to start listening before we try connecting
    return process


