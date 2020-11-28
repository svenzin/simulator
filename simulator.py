from collections import namedtuple
from collections import defaultdict
import itertools

elements = set()

IN = 'in'
OUT = 'out'
HiZ = 'hiZ'

LO = 0
HI = 1

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
        return '<{}> {} {}'.format(self.name, self.direction, self.value)

class Point(BasePoint):
    def __init__(self, name):
        super().__init__(name)
        self.IN().set(value_floating())

    def HiZ(self):
        super().HiZ(value_hi_z())
        return self

class WidePoint(BasePoint):
    def __init__(self, name, width):
        super().__init__(name)
        self.width = width
        self.IN().set(value_floating(self.width))

    def _set_value(self, value):
        assert self.width == len(value), 'Invalid data width'
        super()._set_value(value)
        return self

    def HiZ(self):
        super().HiZ(value_hi_z(self.width))
        return self

class SignalPoint(WidePoint):
    def __init__(self, name):
        super().__init__(name, 1)
    
    def is_high(self):
        return self.get() == value_high()
    
    def is_low(self):
        return self.get() == value_low()

class TriggerPoint(SignalPoint):
    def __init__(self, name):
        super().__init__(name)
        self._was_low = False
    
    def _set_value(self, value):
        self._was_low = self.is_low()
        super()._set_value(value)
        return self
    
    def triggered(self):
        return self._was_low and self.is_high()

class Wiring:
    def __init__(self):
        self.connections = defaultdict(set)
    
    def connect(self, point_a, point_b):
        assert isinstance(point_a, BasePoint)
        assert isinstance(point_b, BasePoint)
        self.connections[point_a].add(point_a)
        self.connections[point_a].add(point_b)
        self.connections[point_b].add(point_b)
        self.connections[point_b].add(point_a)
        return self
    
    def disconnect(self, point_a, point_b):
        assert isinstance(point_a, BasePoint)
        assert isinstance(point_b, BasePoint)
        self.connections[point_a].remove(point_b)
        self.connections[point_b].remove(point_a)
        return self
    
    def points(self):
        return set(( point for point, connections in self.connections.items() if len(connections) > 0 ))
    
    def neighbours(self, point):
        neighbours = set()
        visited = set()
        to_visit = {point}
        while len(to_visit) > 0:
            visit = to_visit.pop()
            neighbours.update(self.connections[visit])
            visited.add(visit)
            to_visit.update(self.connections[visit])
            to_visit.difference_update(visited)
        return neighbours - {point}

def propagate(wiring):
    points = wiring.points()
    while len(points) > 0:
        point = points.pop()
        neighbours = { point }
        neighbours |= wiring.neighbours(point)
        points -= neighbours
        values = [ p.get() for p in neighbours if p.direction == OUT ]
        v = util_resolve_values(values)
        for p in neighbours:
            p.set(v)


class Constant:
    def __init__(self, value):
        self.point = Point(self.__class__.__name__).OUT(value)
    def __repr__(self):
        return '<Constant> = {}'.format(self.point)

class Probe:
    def __init__(self):
        self.point = Point(self.__class__.__name__).IN()
    def __repr__(self):
        return '<Probe> = {}'.format(self.point)

class Element:
    elements = set()

class Buffer:
    def __init__(self):
        Element.elements.add(self)
        self.input = Point('A').IN()
        self.n_enable = SignalPoint('/OE').IN()
        self.output = Point('Y').HiZ()

    def generate(self):
        if self.n_enable.is_low():
            self.output.OUT(self.input.value)
        else:
            self.output.HiZ()
    
    def __repr__(self):
        if self.n_enable.is_low():
            return '<Buffer> {} -> {}'.format(self.input, self.output)
        else:
            return '<Buffer> {} || {}'.format(self.input, self.output)

class Inverter:
    def __init__(self):
        Element.elements.add(self)
        self.input = Point('A').IN()
        self.output = Point('Y').OUT(value_floating())

    def generate(self):
        def invert(x):
            if x == LO: return HI
            if x == HI: return LO
            return FLOATING
        out = (invert(x) for x in self.input.value)
        self.output.OUT(value(*out))
    
    def __repr__(self):
        return '<Inverter> {} -> {}'.format(self.input, self.output)

################################################################################

class Component:
    def __init__(self):
        self.wiring = Wiring()
        self._components = set()
    
    def _subcomponent(self, cls):
        component = cls()
        self._components.add(component)
        return component

    def generate(self):
        pass
    
    def components(self):
        yield self
        for component in self._components:
            for c in component.components():
                yield c
    
    def wirings(self):
        for component in self.components():
            yield component.wiring

################################################################################

class Boolean(Component):
    def __init__(self):
        super().__init__()
        self.a = Point(self.__class__.__name__+'.A').IN()
        self.b = Point(self.__class__.__name__+'.B').IN()
        self.output = Point(self.__class__.__name__+'.Y').OUT(value_floating())
        self._truth_table = { input: { input: UNDECIDED for input in [ LOW, HIGH, FLOATING, HI_Z, CONFLICT, UNDECIDED ] } for input in [ LOW, HIGH, FLOATING, HI_Z, CONFLICT, UNDECIDED ] }

    def generate(self):
        out = ( self._truth_table[a][b] for a, b in zip(self.a.value, self.b.value) )
        self.output.OUT(value(*out))
    
    def __repr__(self):
        return '<{}> {} {} -> {}'.format(self.__class__.__name__, self.a, self.b, self.output)

class And(Boolean):
    def __init__(self):
        super().__init__()
        self._truth_table[LOW][LOW] = LOW
        self._truth_table[LOW][HIGH] = LOW
        self._truth_table[HIGH][LOW] = LOW
        self._truth_table[HIGH][HIGH] = HIGH

class Xor(Boolean):
    def __init__(self):
        super().__init__()
        self._truth_table[LOW][LOW] = LOW
        self._truth_table[LOW][HIGH] = HIGH
        self._truth_table[HIGH][LOW] = HIGH
        self._truth_table[HIGH][HIGH] = LOW

class Or(Boolean):
    def __init__(self):
        super().__init__()
        self._truth_table[LOW][LOW] = LOW
        self._truth_table[LOW][HIGH] = HIGH
        self._truth_table[HIGH][LOW] = HIGH
        self._truth_table[HIGH][HIGH] = HIGH

################################################################################

class FixedWidthComponent(Component):
    def __init__(self, width):
        self.width = width

class Register_173(FixedWidthComponent):
    def __init__(self, width):
        super().__init__(width)
        self.input = WidePoint('input', self.width).IN()
        self.output = WidePoint('output', self.width).HiZ()
        self.n_ie = SignalPoint('/ie').IN()
        self.n_oe = SignalPoint('/oe').IN()
        self.reset = SignalPoint('reset').IN()
        self.clock = TriggerPoint('clock').IN()
    
    def generate(self):
        if self.n_ie.is_low():
            if self.clock.triggered():
                self.output.OUT(self.input.get())
        if self.reset.is_high():
            self.output.OUT(value_low(self.width))
        if not self.n_oe.is_low():
            self.output.HiZ()
        self._clock0 = self.clock.get()

class Buffer_541(FixedWidthComponent):
    def __init__(self, width):
        super().__init__(width)
        self.n_oe = SignalPoint('/oe').IN()
        self.input = WidePoint('input', self.width).IN()
        self.output = WidePoint('output', self.width).HiZ()
    
    def generate(self):
        if self.n_oe.is_low():
            self.output.OUT(self.input.get())
        else:
            self.output.HiZ()

class Counter_161(FixedWidthComponent):
    def __init__(self, width):
        super().__init__(width)
        self.input = WidePoint('input', self.width).IN()
        self.output = WidePoint('output', self.width).OUT(value_floating(self.width))
        self.n_reset = SignalPoint('/reset').IN()
        self.clock = SignalPoint('clock').IN()
        self.n_ie = SignalPoint('/ie').IN()
        self.cep = SignalPoint('cep').IN()
        self.cet = SignalPoint('cet').IN()
        self.tc = SignalPoint('tc').OUT(value_floating())
    
    def generate(self):
        pass

################################################################################

class HalfAdder(Component):
    def __init__(self):
        super().__init__()
        self._and = self._subcomponent(And)
        self._xor = self._subcomponent(Xor)
        self.a = Point(self.__class__.__name__+'.A').IN()
        self.b = Point(self.__class__.__name__+'.B').IN()
        self.s = Point(self.__class__.__name__+'.S').IN()
        self.c = Point(self.__class__.__name__+'.C').IN()
        w = self.wiring
        w.connect(self.a, self._xor.a)
        w.connect(self.b, self._xor.b)
        w.connect(self._xor.output, self.s)
        w.connect(self.a, self._and.a)
        w.connect(self.b, self._and.b)
        w.connect(self._and.output, self.c)

class FullAdder(Component):
    def __init__(self):
        super().__init__()
        self._ha1 = self._subcomponent(HalfAdder)
        self._ha2 = self._subcomponent(HalfAdder)
        self._or = self._subcomponent(Or)
        self.a = Point(self.__class__.__name__+'.a').IN()
        self.b = Point(self.__class__.__name__+'.b').IN()
        self.cin = Point(self.__class__.__name__+'.cin').IN()
        self.s = Point(self.__class__.__name__+'.s').IN()
        self.cout = Point(self.__class__.__name__+'.cout').IN()
        w = self.wiring
        w.connect(self.a, self._ha1.a)
        w.connect(self.b, self._ha1.b)
        w.connect(self.cin, self._ha2.a)
        w.connect(self._ha1.s, self._ha2.b)
        w.connect(self._ha2.s, self.s)
        w.connect(self._ha1.c, self._or.a)
        w.connect(self._ha2.c, self._or.b)
        w.connect(self._or.output, self.cout)

################################################################################

class Circuit(Component):
    def add(self, component):
        if component is not self:
            self._components.add(component)
        return self

    def connect(self, point_a, point_b):
        self.wiring.connect(point_a, point_b)
        return self

################################################################################

def signature(points):
    return [p.value for p in points]

def generation(components):
    for component in components:
        component.generate()

def propagation(wiring):
    points = wiring.points()
    while len(points) > 0:
        point = points.pop()
        neighbours = { point }
        neighbours |= wiring.neighbours(point)
        points -= neighbours
        values = [ p.get() for p in neighbours if p.direction == OUT ]
        v = util_resolve_values(values)
        for p in neighbours:
            p.set(v)

def iteration(component):
    wiring = Wiring()
    for w in component.wirings():
        for point, connections in w.connections.items():
            wiring.connections[point] |= connections
    
    points = wiring.points()
    before = signature(points)
    generation(component.components())
    propagation(wiring)
    after = signature(points)
    return after == before

def step(circuit, *, limit=10):
    assert isinstance(circuit, Circuit)
    n = 0
    while not iteration(circuit) and n < limit:
        n += 1
    return (n < limit, n)

################################################################################

w = Wiring()

def util_resolve_values(values):
    if len(values) == 0:
        return value_floating()
    if len(values) == 1:
        return values[0]
    return value_conflict()

def main():
    elements = []

    probe = Probe()
    elements.append(probe)

    vcc = Constant(value_high())
    gnd = Constant(value_low())
    elements.append(vcc)
    elements.append(gnd)

    print(elements)

    w.connect(probe.point, vcc.point)

    print(w.connections)

    propagate(w)

    print(elements)

    w.connect(probe.point, gnd.point)
    propagate(w)

    print(elements)

    w.disconnect(probe.point, vcc.point)
    propagate(w)

    print(elements)

    w.disconnect(probe.point, gnd.point)
    propagate(w)

    print(elements)

    b = Buffer()
    elements.append(b)
    i = Inverter()
    elements.append(i)
    w.connect(vcc.point, i.input)
    w.connect(i.output, b.input)
    w.connect(b.output, probe.point)
    w.connect(vcc.point, b.n_enable)

    def iterate(wirings = [w]):
        wiring = Wiring()
        for w in wirings:
            for point, connections in w.connections.items():
                wiring.connections[point] |= connections
        points = wiring.points()
        signature_before = [p.value for p in points]
        for e in Element.elements:
            e.generate()
        propagate(wiring)
        signature_after = [p.value for p in points]
        return signature_after == signature_before
    print(elements)
    iterate()
    iterate()
    iterate()
    iterate()
    iterate()
    print(elements)
    w.disconnect(vcc.point, b.n_enable)
    w.connect(gnd.point, b.n_enable)
    print()
    print(elements)
    iterate()
    print(elements)
    iterate()
    print(elements)

    circuit = Circuit()
    a = Point('a')
    b = Point('b')
    s = Probe()
    c = Probe()
    opand = And()
    opxor = Xor()
    (
        circuit.add(opand).add(opxor)
        .connect(a, opand.a)
        .connect(b, opand.b)
        .connect(opand.output, s.point)
        .connect(a, opxor.a)
        .connect(b, opxor.b)
        .connect(opxor.output, c.point)
    )
    
    elements = [a, b, opand, opxor, s, c]
    for va, vb in itertools.product([value_low(), value_high()], repeat=2):
        a.OUT(va)
        b.OUT(vb)
        step(circuit)
        print(elements)

    half_adder = Circuit()
    ha = HalfAdder()
    half_adder.add(ha).connect(a, ha.a).connect(b, ha.b)
    elements = [a, b, ha.s, ha.c]
    for va, vb in itertools.product([value_low(), value_high()], repeat=2):
        a.OUT(va)
        b.OUT(vb)
        step(half_adder)
        print(elements)

    cin = Point('cin')
    full_adder = Circuit()
    fa = FullAdder()
    full_adder.add(fa).connect(a, fa.a).connect(b, fa.b).connect(cin, fa.cin)
    elements = [a, b, cin, fa.s, fa.cout]
    for va, vb, vc in itertools.product([value_low(), value_high()], repeat=3):
        a.OUT(va)
        b.OUT(vb)
        cin.OUT(vc)
        step(full_adder)
        print(elements)


################################################################################

import unittest

class PointTests(unittest.TestCase):
    def test_set_value(self):
        v0 = value_low()
        v1 = value_high()

        p = Point('').IN().set(v1)
        self.assertEqual(p.value, v1)

        p = Point('').OUT(v0).set(v1)
        self.assertEqual(p.value, v0)

        p = Point('').HiZ().set(v1)
        self.assertEqual(p.value, value_hi_z())

class WiringTests(unittest.TestCase):
    def test_simple_wires(self):
        a = Point('')
        b = Point('')
        c = Point('')

        w = Wiring()
        self.assertEqual(w.neighbours(a), set())
        self.assertEqual(w.neighbours(b), set())
        self.assertEqual(w.neighbours(c), set())
        
        w.connect(a, b)
        self.assertEqual(w.neighbours(a), {b})
        self.assertEqual(w.neighbours(b), {a})
        self.assertEqual(w.neighbours(c), set())

        w.connect(b, c)
        self.assertEqual(w.neighbours(a), {b, c})
        self.assertEqual(w.neighbours(b), {a, c})
        self.assertEqual(w.neighbours(c), {a, b})

        w.connect(c, a)
        self.assertEqual(w.neighbours(a), {b, c})
        self.assertEqual(w.neighbours(b), {a, c})
        self.assertEqual(w.neighbours(c), {a, b})

class Test_Buffer(unittest.TestCase):
    def test_forward_bit(self):
        b = Buffer()
        
        for data in [ value_low(), value_high() ]:
            b.input.set(data)
            
            b.n_enable.set(value_high())
            b.generate()
            self.assertEqual(b.output.get(), value_hi_z())

            b.n_enable.set(value_low())
            b.generate()
            self.assertEqual(b.output.get(), data)

class Test_Inverter(unittest.TestCase):
    def test_invert_bit(self):
        b = Inverter()
        for x, not_x in [ (value_low(), value_high()), (value_high(), value_low()) ]:
            b.input.set(x)
            b.generate()
            self.assertEqual(b.output.get(), not_x)
    
    def test_invert_bits(self):
        b = Inverter()
        bits = [ value(LO, LO), value(LO, HI), value(HI, LO), value(HI, HI) ]
        not_bits = [ value(HI, HI), value(HI, LO), value(LO, HI), value(LO, LO) ]
        for x, not_x in zip(bits, not_bits):
            b.input.set(x)
            b.generate()
            self.assertEqual(b.output.get(), not_x)

class Test_And(unittest.TestCase):
    def test_and_bit(self):
        e = And()
        for a0, b0 in itertools.product([LO, HI], repeat=2):
            r0 = a0 and b0
            e.a.set(value(a0))
            e.b.set(value(b0))
            e.generate()
            self.assertEqual(e.output.get(), value(r0))

    def test_and_bits(self):
        e = And()
        for a0, a1, b0, b1 in itertools.product([LO, HI], repeat=4):
            r0 = a0 and b0
            r1 = a1 and b1
            e.a.set(value(a0, a1))
            e.b.set(value(b0, b1))
            e.generate()
            self.assertEqual(e.output.get(), value(r0, r1))

class Test_Register_173(unittest.TestCase):
    def test_173(self):
        reg = Register_173(4)
        reg.clock.set(value_low())
        reg.generate()
        
        x0 = reg.output.get()

        # Load on clock
        # Load 0101
        x = value(LO, HI, LO, HI)
        reg.input.set(x)
        reg.n_ie.set(value_low())
        reg.n_oe.set(value_low())
        reg.reset.set(value_low())
        reg.clock.set(value_low())
        reg.generate()
        self.assertEqual(reg.output.get(), x0)
        
        reg.clock.set(value_high())
        reg.generate()
        self.assertEqual(reg.output.get(), x)
        
        # Load 1010
        x = value(HI, LO, HI, LO)
        reg.input.set(x)
        reg.clock.set(value_low())
        reg.generate()
        reg.clock.set(value_high())
        reg.generate()
        self.assertEqual(reg.output.get(), x)
        
        # Hold
        x0 = x
        x = value_low(4)
        reg.input.set(x)
        reg.n_ie.set(value_high())
        reg.clock.set(value_low())
        reg.generate()
        reg.clock.set(value_high())
        reg.generate()
        self.assertEqual(reg.output.get(), x0)
        
        # Reset
        reg.reset.set(value_high())
        reg.generate()
        self.assertEqual(reg.output.get(), value_low(4))
        
        # Disable
        reg.n_oe.set(value_high())
        reg.generate()
        self.assertEqual(reg.output.get(), value_hi_z(4))

class Test_Buffer_541(unittest.TestCase):
    def test_541(self):
        buf = Buffer_541(4)
        buf.n_oe.set(value_low())
        # Drive 0101
        x = value(LO, HI, LO, HI)
        buf.input.set(x)
        buf.generate()
        self.assertEqual(buf.output.get(), x)
        # Drive 1010
        x = value(HI, LO, HI, LO)
        buf.input.set(x)
        buf.generate()
        self.assertEqual(buf.output.get(), x)
        # Disable
        buf.n_oe.set(value_high())
        buf.generate()
        self.assertEqual(buf.output.get(), value_hi_z(4))

class Test_Counter_161(unittest.TestCase):
    def test_161(self):
        # Load on clock
        # Load 0101
        # Load 1010
        # Reset
        # Load 1111, CET 1 => TC 1
        # Load 1100, count, 1111 & CET 1 => TC 1
        # Count, loop to 0000
        # Load 1110, hold CET 0 => TC 0, hold CEP 0 => TC 0
        # Count, hold CET 0, hold CEP 0 => TC 1
        pass


if __name__ == "__main__":
    unittest.main()
    main()

