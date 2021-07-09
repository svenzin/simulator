LOW = 0
HIGH = 1
FLOATING = 'F'
HI_Z = 'Z'
CONFLICT = '!'
UNDECIDED = '?'

def value(*args):
    return list(args)

def value_low(width = 1):
    return [ LOW ] * width

def value_high(width = 1):
    return [ HIGH ] * width

def value_floating(width = 1):
    return [ FLOATING ] * width

def value_hi_z(width = 1):
    return [ HI_Z ] * width

def value_conflict(width = 1):
    return [ CONFLICT ] * width

def value_undecided(width = 1):
    return [ UNDECIDED ] * width

def value_to_int(value):
    n = ''.join([ str(x) for x in value ])
    return int(n, base=2)

def int_to_value(n, width):
    n = n % 2**width
    n = '{:0{}b}'.format(n, width)
    n = [ int(x) for x in n ]
    return value(*n)
