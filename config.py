import time
import platform

# analog inputs
AINS = {
    'AN_CH_SG_1': 4,  # AIN4
    'AN_CH_SG_2': 5,  # AIN5
    'AN_CH_SG_3': 6,  # AIN6
    'AN_CH_SG_4': 7,  # AIN7
    'AN_CH_P': 12,  # AIN12
}
# pressure transducer setup
AN_RES = 250  # Ohm
AN_LO_CUR = 0.004  # A
AN_HI_CUR = 0.020  # A
AN_LO_VOLT = AN_LO_CUR * AN_RES
AN_HI_VOLT = AN_HI_CUR * AN_RES
AN_LO = 0  # psi
AN_HI = 300  # psi
# digital outputs
DOS = {
    'DI_CH_SOL1': 7,  # FIO7
    'DI_CH_SOL2': 1,  # FIO1
    'DI_CH_DIAL_PWR': 5,  # FIO5
    'DI_CH_CAMERA_TRIG': 0,  # FIO0
}
DOS_STATES = {k: -1 for (k, v) in DOS.items()}

# Open first found U6
if platform.system() != 'Windows':
    import u6
    d = u6.U6()
    d.getCalibrationData()
else:
    u6 = None
    d = None

# read binary command constructor
read_bin = lambda ch: u6.AIN24(
    PositiveChannel=ch,
    ResolutionIndex=12,
    GainIndex=0,
    SettlingFactor=0,
    Differential=False,
)

# analog conversion command
bin_to_volt = lambda x: d.binaryToCalibratedAnalogVoltage(
    gainIndex=0,
    bytesVoltage=x,
    is16Bits=False,
    resolutionIndex=12,
)

# read voltage command
read_volt = lambda ch: bin_to_volt(d.getFeedback(read_bin(ch))[0])

# digital write command constructor
# IONumber: 0-7=FIO, 8-15=EIO, 16-19=CIO
digital_set = lambda ch, state: u6.BitStateWrite(ch, state)

# digital direction set command
# Direction: 1 = Output, 0 = Input
digital_dir_set = lambda ch, state: u6.BitDirWrite(ch, state)

# digital write command with logging
def digital_write(ch_id, state):
    DOS_STATES[ch_id] = state
    d.getFeedback(digital_set(DOS[ch_id], state))

# readbacks data
NO_UNIT = '-'
readbacks = [
    ('t', {
        'read': time.time,
        'unit': 's',
        'print': lambda x: '{:.1f} s'.format(x),
    }),
    ('p', {
        'read': lambda: read_volt(AINS['AN_CH_P']),
        'conv': lambda v: AN_LO + (v - AN_LO_VOLT) * (AN_HI - AN_LO) / (AN_HI_VOLT - AN_LO_VOLT) - 14.696,
        'unit': 'psi',
        'print': lambda x: '{:.2f} psi'.format(x),
    }),
	('sg1', {
        'read': lambda: read_volt(AINS['AN_CH_SG_1']),
        'unit': 'V',
        'print': lambda x: '{:.3f} V'.format(x),
    }),
    ('sg2', {
        'read': lambda: read_volt(AINS['AN_CH_SG_2']),
        'unit': 'V',
        'print': lambda x: '{:.3f} V'.format(x),
    }),
    ('sg3', {
        'read': lambda: read_volt(AINS['AN_CH_SG_3']),
        'unit': 'V',
        'print': lambda x: '{:.3f} V'.format(x),
    }),
    ('sg4', {
        'read': lambda: read_volt(AINS['AN_CH_SG_4']),
        'unit': 'V',
        'print': lambda x: '{:.3f} V'.format(x),
    }),
    ('sol1', {
        'read': lambda: DOS_STATES['DI_CH_SOL1'],
        'print': lambda x: 'open' if x == 0 else 'closed',
    }),
    ('sol2', {
        'read': lambda: DOS_STATES['DI_CH_SOL2'],
        'print': lambda x: 'open' if x == 0 else 'closed',
    }),
    ('dial_reset', {
        'read': lambda: DOS_STATES['DI_CH_DIAL_PWR'],
        'print': lambda x: 'on' if x == 0 else 'off',
    }),
    ('camera_trigger', {
        'read': lambda: DOS_STATES['DI_CH_CAMERA_TRIG'],
        'print': lambda x: 'on' if x == 0 else 'off',
    }),
]

# extract operations
_header = []
_units = []
_readers = []
_converters = []
_printers = []
for (pv, r) in readbacks:
    _header.append(pv)
    _readers.append(r['read'])
    _printers.append(r['print'])
    if 'unit' in r:
        _units.append(r['unit'])
    else:
        _units.append(NO_UNIT)
    if 'conv' in r:
        _converters.append(r['conv'])
    else:
        _converters.append(lambda x: x)

# drive commands
commands = {
    'sol1_open': lambda: digital_write('DI_CH_SOL1', 0),
    'sol1_close': lambda: digital_write('DI_CH_SOL1', 1),
    'sol2_open': lambda: digital_write('DI_CH_SOL2', 0),
    'sol2_close': lambda: digital_write('DI_CH_SOL2', 1),
    'dial_on': lambda: digital_write('DI_CH_DIAL_PWR', 0),
    'dial_off': lambda: digital_write('DI_CH_DIAL_PWR', 1),
    'camera_on': lambda: digital_write('DI_CH_CAMERA_TRIG', 0),
    'camera_off': lambda: digital_write('DI_CH_CAMERA_TRIG', 1),
}

# file paths
timestamp = time.time()
timestamp_struct = time.gmtime(timestamp)
timestring = time.strftime('%Y-%m-%d-%H-%M-%S', timestamp_struct)
log_file_path = './log_{}.txt'.format(timestring)

def init():
    # prepare output csv file
    header_str = ', '.join(_header) + '\n'
    units_str = ', '.join(['[{}]'.format(u) for u in _units]) + '\n'
    with open(log_file_path, 'w') as f:
        f.write(header_str)
        f.write(units_str)
    # configure all digital output pins as outputs
    for dio in DOS:
        digital_dir_set(DOS[dio], 1)

def read_all(logging=True):
    raw = [r() for r in _readers]
    reads = [c(r) for (r, c) in zip(raw, _converters)]
    print_str = ''
    for (pr, pv, v) in zip(_printers, _header, reads):
        print_str += pv + ' = ' + pr(v) + '; '
    print(print_str)
    if logging:
        reads_str = map(str, reads)
        write_str = ', '.join(reads_str) + '\n'
        with open(log_file_path, 'a') as f:
            f.write(write_str)
    read_dict = {k:v for (k, v) in zip(_header, reads)}
    return read_dict


if __name__ == "__main__":
    pass
    