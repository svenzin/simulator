from .components import Component
from . import boolean
from ..points import Point

class HalfAdder(Component):
    def __init__(self, name=None):
        super().__init__(name)
        self._and = self._subcomponent(boolean.And)
        self._xor = self._subcomponent(boolean.Xor)
        self.a = Point(self._subname('A')).IN()
        self.b = Point(self._subname('B')).IN()
        self.s = Point(self._subname('S')).IN()
        self.c = Point(self._subname('C')).IN()
        (self.wiring
            .connect(self.a, self._xor.a)
            .connect(self.b, self._xor.b)
            .connect(self._xor.output, self.s)
            .connect(self.a, self._and.a)
            .connect(self.b, self._and.b)
            .connect(self._and.output, self.c)
        )

class FullAdder(Component):
    def __init__(self, name=None):
        super().__init__(name)
        self._ha1 = self._subcomponent(HalfAdder)
        self._ha2 = self._subcomponent(HalfAdder)
        self._or = self._subcomponent(boolean.Or)
        self.a = Point(self._subname('a')).IN()
        self.b = Point(self._subname('b')).IN()
        self.cin = Point(self._subname('cin')).IN()
        self.s = Point(self._subname('s')).IN()
        self.cout = Point(self._subname('cout')).IN()
        (self.wiring
            .connect(self.a, self._ha1.a)
            .connect(self.b, self._ha1.b)
            .connect(self.cin, self._ha2.a)
            .connect(self._ha1.s, self._ha2.b)
            .connect(self._ha2.s, self.s)
            .connect(self._ha1.c, self._or.a)
            .connect(self._ha2.c, self._or.b)
            .connect(self._or.output, self.cout)
        )
