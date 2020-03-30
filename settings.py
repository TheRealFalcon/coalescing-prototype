TOTAL_MESSAGES = 1000000
MESSAGE_END = b'b'
STOP_MESSAGE = b'z'
SERVER_IP = '127.0.0.1'
PORT = 12345
MAX_QUEUE_SIZE = 200  # This was fairly arbitrary. Too high and latencies spike. Too low and too much context switching
QUEUE_WAIT_TIME = .00001  # 10 microseconds
