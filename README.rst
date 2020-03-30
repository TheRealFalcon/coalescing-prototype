Running
-------
Requires Python 3.7. Enter prototype directory and ``python3 compare_algorithms.py``

Everything exists in the ``prototype`` directory and no additional downloads needed.

Design
------
I'm comparing three different algorithms in three different configurations.

The three algorithms are:
 - TCP_NODELAY disabled (Nagle)
 - TCP_NODELAY enabled
 - TCP_NODELAY enabled with manual coalescing

The three configurations are:
 - Simple - spinning in a for loop until we get through all messages
 - Threaded - using threads with a queue to share messages
 - Async - using asyncio instead of threads

I test the time it takes to send 1 million messages to a (local) server, and then calculate throughput and latencies.

The algorithm I use for coalescing is to collect messages until 10 microseconds have elapsed.
The non-coalescing versions send as soon as the data is received.

Results
-------
From an arbitrary run::

  Run time (s):
    async coalescing tester                 :  4.4608571529
    async no_delay tester                   :  6.3047845364
    async nagle tester                      :  5.3005564213
    threaded coalescing tester              :  8.2327237129
    threaded no_delay tester                :  17.2464625835
    threaded_nagle_tester                   :  17.6398150921
    simple coalescing                       :  3.5081682205
    simple no_delay                         :  4.9324331284
    simple nagle                            :  3.4172878265
  Throughput (ops/s):
    async coalescing tester                 :  224172.1637154853
    async no_delay tester                   :  158609.7025572694
    async nagle tester                      :  188659.4388440702
    threaded coalescing tester              :  121466.4836171429
    threaded no_delay tester                :  57982.9049091082
    threaded_nagle_tester                   :  56689.9366450048
    simple coalescing                       :  285049.0447267574
    simple no_delay                         :  202739.6974225406
    simple nagle                            :  292629.7258996351
  Min (s):
    async coalescing tester                 :  0.0002143383
    async no_delay tester                   :  0.0004105568
    async nagle tester                      :  0.0003552437
    threaded coalescing tester              :  0.0006275177
    threaded no_delay tester                :  0.0006711483
    threaded_nagle_tester                   :  0.0006721020
    simple coalescing                       :  0.0000052452
    simple no_delay                         :  0.0000040531
    simple nagle                            :  0.0000047684
  Max (s):
    async coalescing tester                 :  0.0975129604
    async no_delay tester                   :  0.0977141857
    async nagle tester                      :  0.1080279350
    threaded coalescing tester              :  0.1073188782
    threaded no_delay tester                :  0.0969240665
    threaded_nagle_tester                   :  0.0984201431
    simple coalescing                       :  0.1063480377
    simple no_delay                         :  0.1006393433
    simple nagle                            :  0.1041200161
  Avg (s):
    async coalescing tester                 :  0.0005091909
    async no_delay tester                   :  0.0010126891
    async nagle tester                      :  0.0007697209
    threaded coalescing tester              :  0.0016748953
    threaded no_delay tester                :  0.0041312786
    threaded_nagle_tester                   :  0.0041998828
    simple coalescing                       :  0.0000999472
    simple no_delay                         :  0.0012616609
    simple nagle                            :  0.0005747096
  P99 (s):
    async coalescing tester                 :  0.0010488033
    async no_delay tester                   :  0.0179173946
    async nagle tester                      :  0.0059802532
    threaded coalescing tester              :  0.0022656918
    threaded no_delay tester                :  0.0347113609
    threaded_nagle_tester                   :  0.0355284214
    simple coalescing                       :  0.0005433559
    simple no_delay                         :  0.0383641720
    simple nagle                            :  0.0207934380
  P9999 (s):
    async coalescing tester                 :  0.0770001411
    async no_delay tester                   :  0.0970644951
    async nagle tester                      :  0.1075153351
    threaded coalescing tester              :  0.1071014404
    threaded no_delay tester                :  0.0965712070
    threaded_nagle_tester                   :  0.0980396271
    simple coalescing                       :  0.0188133717
    simple no_delay                         :  0.0619621277
    simple nagle                            :  0.0408947468


Conclusions
-----------
Based on the test runs, it appears we can get a modest boost to throughput without significantly affecting latency.
Manually coalescing messages won for all three configurations.
While the simple configuration affords us the greatest throughput, it's also not very practical as in the real world,
most requests don't come from spinning through a single loop.
Asyncio pretty clearly beats threads which makes sense given that there's a greater overhead to context switching
threads without much parallelism benefit due to the GIL.

I had a hard time getting much more than 200k ops/s, even for a simple use case and while waiting for a much longer period of time.
It seems there's a lot more overhead to using python in general, including just sending data on a socket.
It'd be interesting to further see what kind of performance boost could be gained cythonizing parts of this code.

Disclaimers
-----------
All of these tests were run locally with the server and client on the same developer laptop with unrelated processes running in the background.
Ideally, I would have had client and server on different machines so one isn't affecting the performance of the other.
It'd be best if neither of those machines was my laptop so the test can be repeatable and benchmarkable.
Client and server on a laptop is also especially bad for simulating Nagle's algorithm, because the algorithm involves waiting for ACKs.
Since there's no network latency in localhost, we'll get the ACK back almost immediately which isn't realistic.

Discarded Attempts
------------------
I played with some other algorithms and configurations, but since the results weren't notable or comparable,
and I didn't want the test runs to to take forever, I didn't keep them.

Among the failed attempts are:

Setting TCP_CORK
  I attempted setting TCP_CORK and then disabling it immediately after sending all of the messages.
  This yielded better results than TCP_NODELAY on its own, but worse than manually coalescing. I'm assuming this is because the socket send call is the bottleneck.
Using Multiprocessing
  Threading is bad because of the GIL, but IPC is worse.
Too many timers
  My initial stab at asyncio involved creating a timer for every batch of messages and then sending the batch once the timer expired.
  The constant creating and destroying of timers took way too much time.
