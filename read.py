import time
from config import init, read_all, commands
from ticker import Ticker

SLEEP = 0.5  # s

def wait_and_print(pause):
    t = Ticker(pause)
    while not t.check:
        read_all(logging=False)
        time.sleep(SLEEP)

if __name__ == "__main__":
    wait_and_print(60)
