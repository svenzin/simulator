from .value import *

################################################################################

IN = 'in'
OUT = 'out'
HiZ = 'hiZ'

################################################################################

class BasePoint:
    def __init__(self, name):
        self.name = name
        self.value = None
        self.direction = None

    def _set_value(self, value):
        self.value = value
        return self
    
    def _set_direction(self, direction):
        self.direction = direction
        return self

    def IN(self): return self._set_direction(IN)
    def OUT(self, value): return self._set_direction(OUT)._set_value(value)
    def HiZ(self, value): return self._set_direction(HiZ)._set_value(value)

    def get(self):
        return self.value

    def set(self, value):
        if self.direction == IN:
            self._set_value(value)
        return self
    
    def __repr__(self):
        value = ''.join(( str(x) for x in self.value ))
        return '<{}> {} {}'.format(self.name, self.direction, value)

################################################################################

class Point(BasePoint):
    def __init__(self, name):
        super().__init__(name)
        self.IN().set(value_floating())

    def HiZ(self):
        super().HiZ(value_hi_z())
        return self

################################################################################

class WidePoint(BasePoint):
    def __init__(self, name, width):
        super().__init__(name)
        self.width = width
        self.IN().set(value_floating(self.width))

    def _set_value(self, value):
        if value == value_floating():
            value = value_floating(self.width)
        assert self.width == len(value), '{}: Invalid data width, expected {}, received {}'.format(self.name, self.width, value)
        super()._set_value(value)
        return self

    def HiZ(self):
        super().HiZ(value_hi_z(self.width))
        return self

################################################################################

class SignalPoint(WidePoint):
    def __init__(self, name):
        super().__init__(name, 1)
    
    def is_high(self):
        return self.get() == value_high()
    
    def is_low(self):
        return self.get() == value_low()

################################################################################

class TriggerPoint(SignalPoint):
    def __init__(self, name):
        super().__init__(name)
        self._was_low = False

    def tick(self):
        self._was_low = self.is_low()
        return self
    
    def triggered(self):
        return self._was_low and self.is_high()
    
    LOW = 'LOW'
    HIGH = 'HIGH'
    TRIGGERED = 'TRIGGERED'
    def _test_set(self, state):
        if state == TriggerPoint.LOW:
            self._set_value(value_low())
        elif state == TriggerPoint.HIGH:
            self._set_value(value_high())
        elif state == TriggerPoint.TRIGGERED:
            self._was_low = True
            self._set_value(value_high())
        else:
            raise ValueError('state')
        return self
