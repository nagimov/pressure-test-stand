import sys
import time

class Ticker(object):

    def __init__(self, pause):
        self.started = time.time()
        self.pause = pause

    @property
    def check(self):
        if time.time() - self.started > self.pause:
            return True
        return False

if __name__ == "__main__":
    print('started ticker')
    t = Ticker(3)
    while True:
        if t.check:
            print('stopped ticker')
            sys.exit()
        time.sleep(0.1)
