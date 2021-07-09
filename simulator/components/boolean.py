from .components import Component
from ..points import Point
from ..value import *

class Boolean(Component):
    def __init__(self, name=None):
        super().__init__(name)
        self.a = Point(self._subname('A')).IN()
        self.b = Point(self._subname('B')).IN()
        self.output = Point(self._subname('Y')).OUT(value_floating())
        self._truth_table = { input: { input: UNDECIDED for input in [ LOW, HIGH, FLOATING, HI_Z, CONFLICT, UNDECIDED ] } for input in [ LOW, HIGH, FLOATING, HI_Z, CONFLICT, UNDECIDED ] }

    def generate(self):
        out = ( self._truth_table[a][b] for a, b in zip(self.a.value, self.b.value) )
        self.output.OUT(value(*out))
    
    def __repr__(self):
        return '<{}> {} {} -> {}'.format(self.__class__.__name__, self.a, self.b, self.output)

class And(Boolean):
    def __init__(self, name=None):
        super().__init__(name)
        self._truth_table[LOW][LOW] = LOW
        self._truth_table[LOW][HIGH] = LOW
        self._truth_table[HIGH][LOW] = LOW
        self._truth_table[HIGH][HIGH] = HIGH

class Xor(Boolean):
    def __init__(self, name=None):
        super().__init__(name)
        self._truth_table[LOW][LOW] = LOW
        self._truth_table[LOW][HIGH] = HIGH
        self._truth_table[HIGH][LOW] = HIGH
        self._truth_table[HIGH][HIGH] = LOW

class Or(Boolean):
    def __init__(self, name=None):
        super().__init__(name)
        self._truth_table[LOW][LOW] = LOW
        self._truth_table[LOW][HIGH] = HIGH
        self._truth_table[HIGH][LOW] = HIGH
        self._truth_table[HIGH][HIGH] = HIGH
