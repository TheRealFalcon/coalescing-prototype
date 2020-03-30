import math
import operator
import socket
import time
from collections import namedtuple
from functools import reduce
from multiprocessing import Queue as MultiprocessingQueue

import settings
from asyncio_tests import test_asyncio_coalesce, test_asyncio_no_coalesce
from non_async_tests import test_threaded_coalesce, test_threaded_no_coalesce, test_simple, \
    test_simple_coalescing
from server import start_server_process
from utilities import DataPoint

algorithm_tester = namedtuple('AlgorithmTester', 'name test use_tcp_nodelay')
metrics = namedtuple('Metrics', 'name run_time throughput first_latency last_latency min_latency '
                                'max_latency avg_latency p99_latency p9999_latency')


def percentile(latencies, percent):
    """ Get a pXX latency given a list of latencies """
    # See https://stackoverflow.com/a/15589202
    size = len(latencies)
    return sorted(latencies)[int(math.ceil((size * percent) / 100)) - 1]


def calculate_latencies(start_times, end_times, client_sizes, server_sizes):
    # In order to calculate our latencies, we need to line up the messages
    # we've sent with the time they were read from the server.
    # We can determine which client messages line up with which server messages based
    # on how large each server message is

    # Reversing list to avoid popping from front
    end_times = list(reversed(end_times))
    server_sizes = list(reversed(server_sizes))

    current_size = 0
    current_end_time = None

    for index, client_size in enumerate(client_sizes):
        if current_size < 1:
            current_size += server_sizes.pop()
            current_end_time = end_times.pop()
        latency = current_end_time - start_times[index]
        yield latency
        current_size -= client_size


def display_stats(stats):
    for display_name, attribute in [
        ('Run time (s)', 'run_time'),
        ('Throughput (ops/s)', 'throughput'),
        ('Min (s)', 'min_latency'),
        ('Max (s)', 'max_latency'),
        ('Avg (s)', 'avg_latency'),
        ('P99 (s)', 'p99_latency'),
        ('P9999 (s)', 'p9999_latency'),
    ]:
        print('{}:'.format(display_name))
        for test_stats in stats:
            print('  {test: <40}: {stat: .10f}'.format(test=test_stats.name, stat=getattr(test_stats, attribute)))


def get_stats(name, test_start_time, end_times, latencies):
    last_server_time = end_times[-1]
    run_time = last_server_time - test_start_time
    throughput = settings.TOTAL_MESSAGES / run_time
    first_latency = latencies[0]
    last_latency = latencies[-1]
    min_latency = min(latencies)
    max_latency = max(latencies)
    avg_latency = reduce(operator.add, latencies) / len(latencies)
    p99_latency = percentile(latencies, 99)
    p9999_latency = percentile(latencies, 99.99)

    return metrics(name, run_time, throughput, first_latency, last_latency, min_latency, max_latency,
                   avg_latency, p99_latency, p9999_latency)


def _collect_server_data(server_queue):
    """ Collect the data back from the server until we get our STOP_MESSAGE """
    done = False
    while not done:
        datapoint = server_queue.get()
        if datapoint.data.endswith(settings.STOP_MESSAGE):
            datapoint = DataPoint(datapoint.data.split(settings.STOP_MESSAGE)[0], datapoint.timestamp)
            done = True
        yield datapoint


def execute_test(tester, client, server_queue):
    test_start_time = time.time()
    client.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, tester.use_tcp_nodelay)
    client_data = list(tester.test(client))

    server_data = list(_collect_server_data(server_queue))
    end_times = [server_point.timestamp for server_point in server_data]

    latencies = list(
        calculate_latencies(
            [client_point.timestamp for client_point in client_data],
            end_times,
            [len(client_point.data) for client_point in client_data],
            [len(server_point.data) for server_point in server_data],
        )
    )

    assert len(latencies) == settings.TOTAL_MESSAGES, \
        'Latencies have {} but expected {}'.format(len(latencies), settings.TOTAL_MESSAGES)

    stats = get_stats(tester.name, test_start_time, end_times, latencies)
    return stats


def start_client():
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((settings.SERVER_IP, settings.PORT))
    return client


def main():
    server_queue = MultiprocessingQueue()
    server = start_server_process(server_queue)
    client = start_client()

    testers = [
        algorithm_tester('async coalescing tester', test_asyncio_coalesce, use_tcp_nodelay=True),
        algorithm_tester('async no_delay tester', test_asyncio_no_coalesce, use_tcp_nodelay=True),
        algorithm_tester('async nagle tester', test_asyncio_no_coalesce, use_tcp_nodelay=False),
        algorithm_tester('threaded coalescing tester', test_threaded_coalesce, use_tcp_nodelay=True),
        algorithm_tester('threaded no_delay tester', test_threaded_no_coalesce, use_tcp_nodelay=True),
        algorithm_tester('threaded_nagle_tester', test_threaded_no_coalesce, use_tcp_nodelay=False),
        algorithm_tester('simple coalescing', test_simple_coalescing, use_tcp_nodelay=True),
        algorithm_tester('simple no_delay', test_simple, use_tcp_nodelay=True),
        algorithm_tester('simple nagle', test_simple, use_tcp_nodelay=False),
    ]

    stats = []
    try:
        for tester in testers:
            assert server_queue.empty()
            tester_stats = execute_test(tester, client, server_queue)
            stats.append(tester_stats)
    finally:
        client.close()
        server.kill()
    display_stats(stats)


if __name__ == '__main__':
    main()
