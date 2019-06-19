import numpy as np
import sys
import time
from config import init, read_all, commands
from ticker import Ticker

SLEEP = 0.1  # s

# experiment setup
START_P = 50  # psi
END_P = 100  # psi
STEP_P = 1  # psi
FAST_P_THRESH = 10  # psi
CYCLES_PER_STEP = 1
LO_THRESH = 0.1  # psi
HI_PAUSE = 1  # s (plus dial/camera pauses)
LO_PAUSE = 1  # s (plus dial/camera pauses)
HI_MAX_TIME_FAST = 10  # s
HI_MAX_TIME_SLOW = 10  # s
LO_MAX_TIME = 20  # s
DIAL_RESET_PAUSE = 0.2  # s  0.2 is minimum
DIAL_RESET_POWERON_PAUSE = 1  # s
CAMERA_TRIGGER_PAUSE = 0.2  # s
CAMERA_PICTURE_TAKING_PAUSE = 4  # s

class State(object):
    def __init__(self, init_stat=''):
        self.status = init_stat  # 'VENTED', 'INFLATING', 'HOLDING', 'DEFLATING'
    def change(self, stat):
        if stat != self.status:
            self.status = stat
            print('STATE: {}'.format(stat))

def wait_and_log(pause):
    t = Ticker(pause)
    while not t.check:
        read_all()
        time.sleep(SLEEP)

def interlock(msg):
    commands['sol1_close']()
    commands['sol2_open']()
    print(msg)
    sys.exit()

def wait_log_stop(trip_time, var_str, stop_func, trip_msg):
    v = read_all()[var_str]
    t = Ticker(trip_time)
    while not stop_func(v):
        time.sleep(SLEEP)
        v = read_all()[var_str]
        if t.check:
            interlock(trip_msg)

'''
state machine: VENTED -> INFLATING -> HOLDING -> DEFLATING -> VENTED -> ...
'''

if __name__ == "__main__":
    # initialization
    init()
    S = State()
    commands['sol1_close']()
    commands['sol2_close']()
    commands['sol3_close']()
    commands['dial_off']()
    time.sleep(DIAL_RESET_PAUSE)
    commands['dial_on']()
    time.sleep(DIAL_RESET_POWERON_PAUSE)

    # inflation-deflation cycling
    inflating_trip_msg = 'inflating is taking too long, possible out-leak?'
    deflating_trip_msg = 'deflating is taking too long, possible in-leak?'
    S.change('DEFLATING')
    for p_set in np.arange(START_P, END_P, STEP_P):
        for c in range(CYCLES_PER_STEP):
            if S.status == 'VENTED':
                wait_and_log(LO_PAUSE)
                commands['dial_off']()
                commands['camera_on']()
                wait_and_log(max(DIAL_RESET_PAUSE, CAMERA_TRIGGER_PAUSE))
                commands['dial_on']()
                commands['camera_off']()
                wait_and_log(max(DIAL_RESET_POWERON_PAUSE, CAMERA_PICTURE_TAKING_PAUSE))
                S.change('INFLATING')
            if S.status == 'INFLATING':
                print('p_set = {}'.format(p_set))
                inflating_start = time.time()
                commands['sol1_close']()
                # fast pump
                p_thresh = p_set - FAST_P_THRESH
                if read_all()['p'] < p_thresh:
                    commands['sol3_open']()
                    wait_log_stop(HI_MAX_TIME_FAST, 'p', lambda p: p > p_thresh, inflating_trip_msg)
                    commands['sol3_stop']()
                commands['sol2_open']()
                wait_log_stop(HI_MAX_TIME, 'p', lambda p: p > p_set, inflating_trip_msg)
                commands['sol2_close']()
                inflating_time = time.time() - inflating_start
                print('    inflating completed in {:.1f} s'.format(inflating_time))
                S.change('HOLDING')
            if S.status == 'HOLDING':
                wait_and_log(HI_PAUSE)
                commands['camera_on']()
                wait_and_log(CAMERA_TRIGGER_PAUSE)
                commands['camera_off']()
                wait_and_log(CAMERA_PICTURE_TAKING_PAUSE)
                S.change('DEFLATING')
            if S.status == 'DEFLATING':
                deflating_start = time.time()
                commands['sol1_open']()
                wait_log_stop(LO_MAX_TIME, 'p', lambda p: p < LO_THRESH, deflating_trip_msg)
                deflating_time = time.time() - deflating_start
                print('    deflating completed in {:.1f} s'.format(deflating_time))
                S.change('VENTED')
