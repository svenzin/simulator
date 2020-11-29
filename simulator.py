from collections import namedtuple
from collections import defaultdict
import itertools

FULL_TESTS = True

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

def value_to_int(value):
    n = ''.join([ str(x) for x in value ])
    return int(n, base=2)

def int_to_value(n, width):
    n = n % 2**width
    n = '{:04b}'.format(n)
    n = [ int(x) for x in n ]
    return value(*n)

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
        if value == value_floating():
            value = value_floating(self.width)
        assert self.width == len(value), '{}: Invalid data width, expected {}, received {}'.format(self.name, self.width, value)
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
    def __init__(self, name=None):
        if name is None: name = self.__class__.__name__
        self.name = name
        self.wiring = Wiring()
        self._components = set()
    
    def _subname(self, name):
        return self.name + '.' + name
    
    def _subcomponent(self, cls, name=None):
        if name is None: name = cls.__name__
        component = cls(self._subname(name))
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

################################################################################

class FixedWidthComponent(Component):
    def __init__(self, width, name=None):
        super().__init__(name)
        self.width = width

class Register_173(FixedWidthComponent):
    def __init__(self, width, name=None):
        super().__init__(width, name)
        self.input = WidePoint(self._subname('input'), self.width).IN()
        self.output = WidePoint(self._subname('output'), self.width).HiZ()
        self.n_ie = SignalPoint(self._subname('/ie')).IN()
        self.n_oe = SignalPoint(self._subname('/oe')).IN()
        self.reset = SignalPoint(self._subname('reset')).IN()
        self.clock = TriggerPoint(self._subname('clock')).IN()
    
    def generate(self):
        if not self.n_oe.is_low():
            self.output.HiZ()
        else:
            if self.reset.is_high():
                self.output.OUT(value_low(self.width))
            else:
                if self.n_ie.is_low():
                    if self.clock.triggered():
                        self.output.OUT(self.input.get())
        self.clock.tick()

class Buffer_541(FixedWidthComponent):
    def __init__(self, width, name=None):
        super().__init__(width, name)
        self.n_oe = SignalPoint(self._subname('/oe')).IN()
        self.input = WidePoint(self._subname('input'), self.width).IN()
        self.output = WidePoint(self._subname('output'), self.width).HiZ()
    
    def generate(self):
        if self.n_oe.is_low():
            self.output.OUT(self.input.get())
        else:
            self.output.HiZ()

class Counter_161(FixedWidthComponent):
    def __init__(self, width, name=None):
        super().__init__(width, name)
        self.input = WidePoint(self._subname('input'), self.width).IN()
        self.output = WidePoint(self._subname('output'), self.width).OUT(value_floating(self.width))
        self.n_reset = SignalPoint(self._subname('/reset')).IN()
        self.clock = TriggerPoint(self._subname('clock')).IN()
        self.n_ie = SignalPoint(self._subname('/ie')).IN()
        self.cep = SignalPoint(self._subname('cep')).IN()
        self.cet = SignalPoint(self._subname('cet')).IN()
        self.tc = SignalPoint(self._subname('tc')).OUT(value_floating())
    
    def generate(self):
        self.tc.OUT(value_low())
        if self.n_reset.is_low():
            self.output.OUT(value_low(4))
        else:
            if self.n_ie.is_low():
                if self.clock.triggered():
                    self.output.OUT(self.input.get())
            else:
                if self.cep.is_high() and self.cet.is_high():
                    if self.clock.triggered():
                        n = value_to_int(self.output.get())
                        n += 1
                        n = int_to_value(n, self.width)
                        self.output.OUT(n)
            if self.output.get() == value_high(self.width):
                self.tc.OUT(self.cet.get())
        self.clock.tick()

class Counter_193(FixedWidthComponent):
    def __init__(self, width, name=None):
        super().__init__(width, name)
        self.input = WidePoint(self._subname('input'), self.width).IN()
        self.output = WidePoint(self._subname('output'), self.width).OUT(value_floating(self.width))
        self.reset = SignalPoint(self._subname('reset')).IN()
        self.n_ie = SignalPoint(self._subname('/ie')).IN()
        self.cpu = TriggerPoint(self._subname('cpu')).IN()
        self.cpd = TriggerPoint(self._subname('cpd')).IN()
        self.n_tcu = SignalPoint(self._subname('/tcu')).OUT(value_floating())
        self.n_tcd = SignalPoint(self._subname('/tcd')).OUT(value_floating())
    
    def generate(self):
        if self.reset.is_high():
            # Reset
            self.output.OUT(value_low(self.width))
            self.n_tcu.OUT(value_high())
            self.n_tcd.OUT(self.cpd.get())
        else:
            if self.n_ie.is_low():
                # Load
                self.output.OUT(self.input.get())
                self.n_tcu.OUT(value_high())
                self.n_tcd.OUT(value_high())
                if self.output.get() == value_low(self.width):
                    self.n_tcd.OUT(self.cpd.get())
                if self.output.get() == value_high(self.width):
                    self.n_tcu.OUT(self.cpu.get())
            else:
                self.n_tcu.OUT(value_high())
                self.n_tcd.OUT(value_high())
                if self.cpu.triggered() and self.cpd.is_high():
                    # Count up
                    n = value_to_int(self.output.get())
                    n += 1
                    n = int_to_value(n, self.width)
                    self.output.OUT(n)
                elif self.cpu.is_high() and self.cpd.triggered():
                    # Count down
                    n = value_to_int(self.output.get())
                    n -= 1
                    n = int_to_value(n, self.width)
                    self.output.OUT(n)
                else:
                    # Hold
                    if self.output.get() == value_low(self.width):
                        self.n_tcd.OUT(self.cpd.get())
                    if self.output.get() == value_high(self.width):
                        self.n_tcu.OUT(self.cpu.get())
        self.cpu.tick()
        self.cpd.tick()

class Decoder_139(Component):
    def __init__(self, name=None):
        super().__init__(name)
        self.input = WidePoint(self._subname('input'), 2).IN()
        self.output_0 = SignalPoint(self._subname('output_0')).OUT(value_floating())
        self.output_1 = SignalPoint(self._subname('output_1')).OUT(value_floating())
        self.output_2 = SignalPoint(self._subname('output_2')).OUT(value_floating())
        self.output_3 = SignalPoint(self._subname('output_3')).OUT(value_floating())
        self.n_ie = SignalPoint(self._subname('n_ie')).IN()
    
    def generate(self):
        self.output_0.OUT(value_high())
        self.output_1.OUT(value_high())
        self.output_2.OUT(value_high())
        self.output_3.OUT(value_high())
        if self.n_ie.is_low():
            n = value_to_int(self.input.get())
            if n == 0:
                self.output_0.OUT(value_low())
            elif n == 1:
                self.output_1.OUT(value_low())
            elif n == 2:
                self.output_2.OUT(value_low())
            elif n == 3:
                self.output_3.OUT(value_low())

################################################################################

class HalfAdder(Component):
    def __init__(self, name=None):
        super().__init__(name)
        self._and = self._subcomponent(And)
        self._xor = self._subcomponent(Xor)
        self.a = Point(self._subname('A')).IN()
        self.b = Point(self._subname('B')).IN()
        self.s = Point(self._subname('S')).IN()
        self.c = Point(self._subname('C')).IN()
        w = self.wiring
        w.connect(self.a, self._xor.a)
        w.connect(self.b, self._xor.b)
        w.connect(self._xor.output, self.s)
        w.connect(self.a, self._and.a)
        w.connect(self.b, self._and.b)
        w.connect(self._and.output, self.c)

class FullAdder(Component):
    def __init__(self, name=None):
        super().__init__(name)
        self._ha1 = self._subcomponent(HalfAdder)
        self._ha2 = self._subcomponent(HalfAdder)
        self._or = self._subcomponent(Or)
        self.a = Point(self._subname('a')).IN()
        self.b = Point(self._subname('b')).IN()
        self.cin = Point(self._subname('cin')).IN()
        self.s = Point(self._subname('s')).IN()
        self.cout = Point(self._subname('cout')).IN()
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

def nop(): pass

class HookPoint(WidePoint):
    def __init__(self, name, width, callback):
        self.callback = nop
        super().__init__(name, width)
        self.callback = callback
    
    def set(self, value):
        super().set(value)
        if (set(value) & { LOW, HIGH }) == set(value):
            self.callback()
        return self

class Splitter(Component):
    def __init__(self, *widths):
        wide_width = sum(widths)
        self.narrows = [ HookPoint('', width, self.narrow_2_wide) for width in widths ]
        self.wide = HookPoint('', wide_width, self.wide_to_narrow)
    
    def narrow_2_wide(self):
        wide_value = []
        for narrow in self.narrows:
            wide_value += narrow.value
        self.wide.OUT(wide_value)

    def wide_to_narrow(self):
        wide_value = self.wide.get()
        i = 0
        for narrow in self.narrows:
            narrow.OUT(wide_value[i:i + narrow.width])
            i += narrow.width
    
    def generate(self):
        print('Splitter')
        for narrow in self.narrows:
            narrow.IN()
        self.wide.IN()

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
        # print(neighbours, values, v)
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
    
    # Basic
    ONE = SignalPoint('ONE').OUT(value_high())
    ZERO = SignalPoint('ZERO').OUT(value_low())
    # Buses
    ALU = WidePoint('ALU', 2)
    WIDE = WidePoint('WIDE', 6)
    ADDR = WidePoint('ADDR', 6)
    # Points of interest
    PC = WidePoint('PC', 6)
    SP = WidePoint('SP', 6)
    MAR = WidePoint('MAR', 6)
    # Control
    MAR_IN = WidePoint('MAR_IN', 2)
    MAR_OUT = SignalPoint('MAR_OUT')
    PC_IN = SignalPoint('PC_IN')
    PC_OUT = SignalPoint('PC_OUT')
    SP_IN = SignalPoint('SP_IN')
    SP_OUT = SignalPoint('SP_OUT')
    WIDE_OUT = SignalPoint('WIDE_OUT')
    CLOCK = SignalPoint('CLOCK')
    # Plate
    plate_0 = Circuit('Plate_0')
    PC_IC = Counter_161(6, 'PC')
    SP_IC = Counter_193(6, 'SP')
    MAR0 = Register_173(2, 'MAR0')
    MAR1 = Register_173(2, 'MAR1')
    MAR2 = Register_173(2, 'MAR2')
    MAR_IN_DECODER = Decoder_139('MAR_IN_DECODER')
    MAR012_2_MAR = Splitter(2, 2, 2)
    PC_2_WIDE = Buffer_541(6, 'PC_2_WIDE')
    SP_2_WIDE = Buffer_541(6, 'SP_2_WIDE')
    MAR_2_WIDE = Buffer_541(6, 'MAR_2_WIDE')
    WIDE_2_ADDR = Buffer_541(6, 'WIDE_2_ADDR')
    plate_0.add(PC_IC)
    plate_0.add(SP_IC)
    plate_0.add(MAR0)
    plate_0.add(MAR1)
    plate_0.add(MAR2)
    plate_0.add(MAR_IN_DECODER)
    plate_0.add(PC_2_WIDE)
    plate_0.add(SP_2_WIDE)
    plate_0.add(MAR_2_WIDE)
    plate_0.add(WIDE_2_ADDR)
    # PC
    plate_0.connect(PC_IC.input, WIDE)
    plate_0.connect(PC_IC.output, PC)
    plate_0.connect(PC_IC.n_reset, ONE)
    plate_0.connect(PC_IC.clock, CLOCK)
    plate_0.connect(PC_IC.n_ie, PC_IN)
    plate_0.connect(PC_IC.cep, ZERO)
    plate_0.connect(PC_IC.cet, ZERO)
    # PC_IC.tc
    # SP
    plate_0.connect(SP_IC.input, WIDE)
    plate_0.connect(SP_IC.output, SP)
    plate_0.connect(SP_IC.reset, ZERO)
    plate_0.connect(SP_IC.n_ie, SP_IN)
    plate_0.connect(SP_IC.cpu, ONE)
    plate_0.connect(SP_IC.cpd, ONE)
    # SP_IC.n_tcu
    # SP_IC.n_tcd
    # MAR0
    plate_0.connect(MAR0.input, ALU)
    # MAR0.output
    plate_0.connect(MAR0.n_ie, MAR_IN_DECODER.output_0)
    plate_0.connect(MAR0.n_oe, ZERO)
    plate_0.connect(MAR0.reset, ZERO)
    plate_0.connect(MAR0.clock, CLOCK)
    # MAR1
    plate_0.connect(MAR1.input, ALU)
    # MAR1.output
    plate_0.connect(MAR1.n_ie, MAR_IN_DECODER.output_1)
    plate_0.connect(MAR1.n_oe, ZERO)
    plate_0.connect(MAR1.reset, ZERO)
    plate_0.connect(MAR1.clock, CLOCK)
    # MAR2
    plate_0.connect(MAR2.input, ALU)
    # MAR2.output
    plate_0.connect(MAR2.n_ie, MAR_IN_DECODER.output_2)
    plate_0.connect(MAR2.n_oe, ZERO)
    plate_0.connect(MAR2.reset, ZERO)
    plate_0.connect(MAR2.clock, CLOCK)
    # MAR_IN_DECODER
    plate_0.connect(MAR_IN_DECODER.input, MAR_IN)
    # MAR_IN_DECODER.output_0
    # MAR_IN_DECODER.output_1
    # MAR_IN_DECODER.output_2
    # MAR_IN_DECODER.output_3
    plate_0.connect(MAR_IN_DECODER.n_ie, ZERO)
    # MAR012_2_MAR
    plate_0.connect(MAR012_2_MAR.narrows[0], MAR0.output)
    plate_0.connect(MAR012_2_MAR.narrows[1], MAR1.output)
    plate_0.connect(MAR012_2_MAR.narrows[2], MAR2.output)
    plate_0.connect(MAR012_2_MAR.wide, MAR)
    # PC_2_WIDE
    plate_0.connect(PC_2_WIDE.n_oe, PC_OUT)
    plate_0.connect(PC_2_WIDE.input, PC)
    plate_0.connect(PC_2_WIDE.output, WIDE)
    # SP_2_WIDE
    plate_0.connect(SP_2_WIDE.n_oe, SP_OUT)
    plate_0.connect(SP_2_WIDE.input, SP)
    plate_0.connect(SP_2_WIDE.output, WIDE)
    # MAR_2_WIDE
    plate_0.connect(MAR_2_WIDE.n_oe, MAR_OUT)
    plate_0.connect(MAR_2_WIDE.input, MAR)
    plate_0.connect(MAR_2_WIDE.output, WIDE)
    # WIDE_2_ADDR
    plate_0.connect(WIDE_2_ADDR.n_oe, WIDE_OUT)
    plate_0.connect(WIDE_2_ADDR.input, WIDE)
    plate_0.connect(WIDE_2_ADDR.output, ADDR)
    
    elements = [ PC, SP, MAR, ALU, WIDE, ADDR ]
    # elements = [ ALU, MAR0.input, MAR1.input, MAR2.input, MAR012_2_MAR.narrows, MAR012_2_MAR.wide, MAR]
    print(elements)

    def setup(xMAR_IN, xMAR_OUT, xPC_IN, xPC_OUT, xSP_IN, xSP_OUT, xWIDE_OUT, xCLOCK):
        MAR_IN.OUT(value(*xMAR_IN))
        MAR_OUT.OUT(value(xMAR_OUT))
        PC_IN.OUT(value(xPC_IN))
        PC_OUT.OUT(value(xPC_OUT))
        SP_IN.OUT(value(xSP_IN))
        SP_OUT.OUT(value(xSP_OUT))
        WIDE_OUT.OUT(value(xWIDE_OUT))
        CLOCK.OUT(value(xCLOCK))
    def execute(xMAR_IN, xMAR_OUT, xPC_IN, xPC_OUT, xSP_IN, xSP_OUT, xWIDE_OUT):
        setup(xMAR_IN, xMAR_OUT, xPC_IN, xPC_OUT, xSP_IN, xSP_OUT, xWIDE_OUT, 0)
        step(plate_0)
        setup(xMAR_IN, xMAR_OUT, xPC_IN, xPC_OUT, xSP_IN, xSP_OUT, xWIDE_OUT, 1)
        step(plate_0)
    # 011011 > MAR
    print()
    print('011011 > MAR')
    ALU.OUT(value(0, 1))
    execute([0, 0], 1, 1, 1, 1, 1, 1)
    print(elements)
    ALU.OUT(value(1, 0))
    execute([0, 1], 1, 1, 1, 1, 1, 1)
    print(elements)
    ALU.OUT(value(1, 1))
    execute([1, 0], 1, 1, 1, 1, 1, 1)
    print(elements)
    ALU.IN()
    # 111111 > PC, SP
    print()
    print('111111 > PC, SP')
    WIDE.OUT(value(1, 1, 1, 1, 1, 1))
    execute([1, 1], 1, 0, 1, 0, 1, 1)
    print(elements)
    WIDE.IN()
    # MAR > PC, ADDR
    print()
    print('MAR > PC, ADDR')
    execute([1, 1], 0, 0, 1, 1, 1, 0)
    print(elements)
    # SP > ADDR
    print()
    print('SP > ADDR')
    execute([1, 1], 1, 1, 1, 1, 0, 0)
    print(elements)


################################################################################

import unittest

def test_signals():
    return [ value_low(), value_high() ]

def test_clocks():
    return [ TriggerPoint.LOW, TriggerPoint.HIGH, TriggerPoint.TRIGGERED ]

def test_inputs(width):
    return [ value(*x) for x in itertools.product([LO, HI], repeat=width) ]

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
    
    def test_full_173(self):
        def make(input, n_ie, n_oe, reset, clock):
            width = len(input)
            register = Register_173(width)
            register.input.set(input)
            register.n_ie.set(n_ie)
            register.n_oe.set(n_oe)
            register.reset.set(reset)
            register.clock._test_set(clock)
            return register
        
        if not FULL_TESTS: return
        width = 4
        # Output enabled
        n_oe = value_high()
        for input in test_inputs(width):
            for n_ie in test_signals():
                for reset in test_signals():
                    for clock in test_clocks():
                        register = make(input, n_ie, n_oe, reset, clock)
                        register.generate()
                        self.assertEqual(register.output.get(), value_hi_z(width))
        # Reset
        n_oe = value_low()
        reset = value_high()
        for input in test_inputs(width):
            for n_ie in test_signals():
                for clock in test_clocks():
                    register = make(input, n_ie, n_oe, reset, clock)
                    register.generate()
                    self.assertEqual(register.output.get(), value_low(width))
        # Load
        n_oe = value_low()
        reset = value_low()
        n_ie = value_low()
        for input in test_inputs(width):
            for clock in [ TriggerPoint.LOW, TriggerPoint.HIGH ]:
                register = make(input, n_ie, n_oe, reset, clock)
                x0 = register.output.get()
                register.generate()
                self.assertEqual(register.output.get(), x0)
            for clock in [ TriggerPoint.TRIGGERED ]:
                register = make(input, n_ie, n_oe, reset, clock)
                register.generate()
                self.assertEqual(register.output.get(), input)
        # Hold
        n_oe = value_low()
        reset = value_low()
        n_ie = value_high()
        for input in test_inputs(width):
            for clock in test_clocks():
                register = make(input, n_ie, n_oe, reset, clock)
                x0 = register.output.get()
                register.generate()
                self.assertEqual(register.output.get(), x0)

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
    
    def test_full_541(self):
        def make(input, n_oe):
            width = len(input)
            buffer = Buffer_541(width)
            buffer.input.set(input)
            buffer.n_oe.set(n_oe)
            return buffer
        
        if not FULL_TESTS: return
        width = 4
        # Output enabled
        for input in test_inputs(width):
            buffer = make(input, value_low())
            buffer.generate()
            self.assertEqual(buffer.output.get(), input)
        # Output disabled
        for input in test_inputs(width):
            buffer = make(input, value_high())
            buffer.generate()
            self.assertEqual(buffer.output.get(), value_hi_z(width))


class Test_Counter_161(unittest.TestCase):
    def test_161(self):
        def counter():
            cnt = Counter_161(4)
            cnt.n_reset.set(value_high())
            cnt.clock.set(value_low())
            cnt.cep.set(value_low())
            cnt.cet.set(value_low())
            cnt.n_ie.set(value_high())
            return cnt
        def clock(counter):
            counter.clock.set(value_low())
            counter.generate()
            counter.clock.set(value_high())
            counter.generate()
        # Load on clock
        # Load 0101
        cnt = counter()
        x0 = cnt.output.get()
        assert x0 == value_floating(4)
        x = value(LO, HI, LO, HI)
        cnt.input.set(x)
        cnt.n_ie.set(value_low())
        cnt.generate()
        self.assertEqual(cnt.output.get(), x0)
        cnt.clock.set(value_high())
        cnt.generate()
        self.assertEqual(cnt.output.get(), x)
        # Load 1010
        cnt = counter()
        x = value(HI, LO, HI, LO)
        cnt.input.set(x)
        cnt.n_ie.set(value_low())
        clock(cnt)
        self.assertEqual(cnt.output.get(), x)
        # Reset
        cnt = counter()
        cnt.n_reset.set(value_low())
        cnt.generate()
        self.assertEqual(cnt.output.get(), value_low(4))
        # Load 1111, CET 0 => TC 0
        cnt = counter()
        cnt.input.set(value_high(4))
        cnt.n_ie.set(value_low())
        clock(cnt)
        self.assertTrue(cnt.tc.is_low())
        # Load 1111, CET 1 => TC 1
        cnt = counter()
        cnt.input.set(value_high(4))
        cnt.n_ie.set(value_low())
        cnt.cet.set(value_high())
        clock(cnt)
        self.assertTrue(cnt.tc.is_high())
        # Load 1110, count, 1111 => TC 1, loop to 0
        cnt = counter()
        cnt.input.set(value(HI, HI, HI, LO))
        cnt.n_ie.set(value_low())
        clock(cnt)
        cnt.n_ie.set(value_high())
        self.assertEqual(cnt.output.get(), value(HI, HI, HI, LO))
        self.assertTrue(cnt.tc.is_low())
        cnt.cep.set(value_high())
        cnt.cet.set(value_high())
        clock(cnt)
        self.assertEqual(cnt.output.get(), value(HI, HI, HI, HI))
        self.assertTrue(cnt.tc.is_high())
        clock(cnt)
        self.assertEqual(cnt.output.get(), value(LO, LO, LO, LO))
        self.assertTrue(cnt.tc.is_low())
        # Hold 1110, hold CET 0, CEP 1 => TC 0, hold CET 1, CEP 0 => TC 0
        cnt = counter()
        cnt.input.set(value(HI, HI, HI, LO))
        cnt.n_ie.set(value_low())
        clock(cnt)
        cnt.n_ie.set(value_high())
        self.assertEqual(cnt.output.get(), value(HI, HI, HI, LO))
        cnt.cep.set(value_low())
        cnt.cet.set(value_low())
        cnt.generate()
        self.assertEqual(cnt.output.get(), value(HI, HI, HI, LO))
        self.assertTrue(cnt.tc.is_low())
        cnt.cep.set(value_high())
        cnt.cet.set(value_low())
        cnt.generate()
        self.assertEqual(cnt.output.get(), value(HI, HI, HI, LO))
        self.assertTrue(cnt.tc.is_low())
        cnt.cep.set(value_low())
        cnt.cet.set(value_high())
        cnt.generate()
        self.assertEqual(cnt.output.get(), value(HI, HI, HI, LO))
        self.assertTrue(cnt.tc.is_low())
        # Hold 1111, hold CET 0, CEP 1 => TC 0, hold CET 1, CEP 0 => TC 0
        cnt = counter()
        cnt.input.set(value(HI, HI, HI, HI))
        cnt.n_ie.set(value_low())
        clock(cnt)
        cnt.n_ie.set(value_high())
        self.assertEqual(cnt.output.get(), value(HI, HI, HI, HI))
        cnt.cep.set(value_low())
        cnt.cet.set(value_low())
        cnt.generate()
        self.assertEqual(cnt.output.get(), value(HI, HI, HI, HI))
        self.assertTrue(cnt.tc.is_low())
        cnt.cep.set(value_high())
        cnt.cet.set(value_low())
        cnt.generate()
        self.assertEqual(cnt.output.get(), value(HI, HI, HI, HI))
        self.assertTrue(cnt.tc.is_low())
        cnt.cep.set(value_low())
        cnt.cet.set(value_high())
        cnt.generate()
        self.assertEqual(cnt.output.get(), value(HI, HI, HI, HI))
        self.assertTrue(cnt.tc.is_high())
    
    def test_full_161(self):
        def set(counter, n_ie, n_reset, cep, cet, clock):
            counter.n_ie.set(n_ie)
            counter.n_reset.set(n_reset)
            counter.cep.set(cep)
            counter.cet.set(cet)
            counter.clock._test_set(clock)
            return counter
        
        def make(input, n_ie, n_reset, cep, cet, clock):
            width = len(input)
            counter = Counter_161(width)
            counter.input.set(input)
            return set(counter, n_ie, n_reset, cep, cet, clock)

        if not FULL_TESTS: return
        width = 4
        # Reset
        n_reset = value_low()
        for input in test_inputs(width):
            for n_ie in test_signals():
                for cep in test_signals():
                    for cet in test_signals():
                        for clock in test_clocks():
                            counter = make(input, n_ie, n_reset, cep, cet, clock)
                            counter.generate()
                            self.assertEqual(counter.output.get(), value_low(4))
                            self.assertTrue(counter.tc.is_low())
        # Load
        n_reset = value_high()
        n_ie = value_low()
        clock = TriggerPoint.TRIGGERED
        for input in test_inputs(width):
            for cep in test_signals():
                for cet in test_signals():
                    counter = make(input, n_ie, n_reset, cep, cet, clock)
                    counter.generate()
                    self.assertEqual(counter.output.get(), input)
                    if input == value_high(width) and cet == value_high():
                        self.assertTrue(counter.tc.is_high())
                    else:
                        self.assertTrue(counter.tc.is_low())
        def load(input, n_ie, n_reset, cep, cet, clock):
            counter = make(input, value_low(), value_high(), value_low(), value_low(), TriggerPoint.TRIGGERED)
            counter.generate()
            return set(counter, n_ie, n_reset, cep, cet, clock)
        # Hold, not 1111
        x0 = value_floating(width)
        n_reset = value_high()
        n_ie = value_high()
        for input in test_inputs(width):
            for cep in test_signals():
                for cet in test_signals():
                    if cep == value_high() and cet == value_high():
                        continue
                    for clock in test_clocks():
                        counter = load(x0, n_ie, n_reset, cep, cet, clock)
                        counter.input.set(input)
                        counter.generate()
                        self.assertEqual(counter.output.get(), x0)
                        self.assertTrue(counter.tc.is_low())
        # Hold 1111
        x0 = value_high(width)
        n_reset = value_high()
        n_ie = value_high()
        for input in test_inputs(width):
            for cep in test_signals():
                for cet in test_signals():
                    if cep == value_high() and cet == value_high():
                        continue
                    for clock in test_clocks():
                        counter = load(x0, n_ie, n_reset, cep, cet, clock)
                        counter.input.set(input)
                        counter.generate()
                        self.assertEqual(counter.output.get(), x0)
                        if cet == value_high():
                            self.assertTrue(counter.tc.is_high())
                        else:
                            self.assertTrue(counter.tc.is_low())
        # Count
        n_reset = value_high()
        n_ie = value_high()
        inputs = test_inputs(width)
        incremented = inputs[1:] + [ inputs[0] ]
        for input, count in zip(inputs, incremented):
            for cep in test_signals():
                for cet in test_signals():
                    for clock in [ TriggerPoint.TRIGGERED ]:
                        if cep == value_high() and cet == value_high():
                            counter = load(input, n_ie, n_reset, cep, cet, clock)
                            counter.generate()
                            self.assertEqual(counter.output.get(), count)
                            if count == value_high(width) and cet == value_high():
                                self.assertTrue(counter.tc.is_high())
                            else:
                                self.assertTrue(counter.tc.is_low())
                    for clock in [ TriggerPoint.LOW, TriggerPoint.HIGH ]:
                        if cep == value_high() and cet == value_high():
                            counter = load(input, n_ie, n_reset, cep, cet, clock)
                            counter.generate()
                            self.assertEqual(counter.output.get(), input)
                            if input == value_high(width) and cet == value_high():
                                self.assertTrue(counter.tc.is_high())
                            else:
                                self.assertTrue(counter.tc.is_low())

class Test_Counter_193(unittest.TestCase):
    def test_full_193(self):
        def setup(counter, n_ie, reset, cpu, cpd):
            counter.n_ie.set(n_ie)
            counter.reset.set(reset)
            counter.cpu._test_set(cpu)
            counter.cpd._test_set(cpd)
            return counter

        def make(input, n_ie, reset, cpu, cpd):
            width = len(input)
            counter = Counter_193(width)
            counter.input.set(input)
            return setup(counter, n_ie, reset, cpu, cpd)
        
        if not FULL_TESTS: return
        width = 4
        # Reset, CPD 0
        reset = value_high()
        cpd = TriggerPoint.LOW
        for input in test_inputs(width):
            for n_ie in test_signals():
                for cpu in test_clocks():
                    counter = make(input, n_ie, reset, cpu, cpd)
                    counter.generate()
                    self.assertEqual(counter.output.get(), value_low(width))
                    self.assertTrue(counter.n_tcu.is_high())
                    self.assertTrue(counter.n_tcd.is_low())
        # Reset, CPD 1
        reset = value_high()
        cpd = TriggerPoint.HIGH
        for input in test_inputs(width):
            for n_ie in test_signals():
                for cpu in test_clocks():
                    counter = make(input, n_ie, reset, cpu, cpd)
                    counter.generate()
                    self.assertEqual(counter.output.get(), value_low(width))
                    self.assertTrue(counter.n_tcu.is_high())
                    self.assertTrue(counter.n_tcd.is_high())
        # Load, not 0000, not 1111
        reset = value_low()
        n_ie = value_low()
        for input in test_inputs(width)[1:-1]: # skip 0000, 1111
            for cpu in test_clocks():
                for cpd in test_clocks():
                    counter = make(input, n_ie, reset, cpu, cpd)
                    counter.generate()
                    self.assertEqual(counter.output.get(), input)
                    self.assertTrue(counter.n_tcu.is_high())
                    self.assertTrue(counter.n_tcd.is_high())
        # Load 0000
        reset = value_low()
        n_ie = value_low()
        input = value_low(width)
        cpd = TriggerPoint.LOW
        for cpu in test_clocks():
            counter = make(input, n_ie, reset, cpu, cpd)
            counter.generate()
            self.assertEqual(counter.output.get(), input)
            self.assertTrue(counter.n_tcu.is_high())
            self.assertTrue(counter.n_tcd.is_low())
        cpd = TriggerPoint.HIGH
        for cpu in test_clocks():
            counter = make(input, n_ie, reset, cpu, cpd)
            counter.generate()
            self.assertEqual(counter.output.get(), input)
            self.assertTrue(counter.n_tcu.is_high())
            self.assertTrue(counter.n_tcd.is_high())
        # Load 1111
        reset = value_low()
        n_ie = value_low()
        input = value_high(width)
        cpu = TriggerPoint.LOW
        for cpd in test_clocks():
            counter = make(input, n_ie, reset, cpu, cpd)
            counter.generate()
            self.assertEqual(counter.output.get(), input)
            self.assertTrue(counter.n_tcu.is_low())
            self.assertTrue(counter.n_tcd.is_high())
        cpu = TriggerPoint.HIGH
        for cpd in test_clocks():
            counter = make(input, n_ie, reset, cpu, cpd)
            counter.generate()
            self.assertEqual(counter.output.get(), input)
            self.assertTrue(counter.n_tcu.is_high())
            self.assertTrue(counter.n_tcd.is_high())
        
        def load(input, n_ie, reset, cpu, cpd):
            counter = make(input, value_low(), value_low(), TriggerPoint.HIGH, TriggerPoint.HIGH)
            counter.generate()
            return setup(counter, n_ie, reset, cpu, cpd)
        # Counting
        reset = value_low()
        n_ie = value_high()
        inputs = test_inputs(width)
        increments = inputs[1:] + [ inputs[0] ]
        decrements = [ inputs[-1] ] + inputs[:-1]
        for input, count_up, count_down in zip(inputs, increments, decrements):
            for cpu in test_clocks():
                for cpd in test_clocks():
                    if cpu == TriggerPoint.TRIGGERED and not cpd == TriggerPoint.LOW:
                        # Count up
                        counter = load(input, n_ie, reset, cpu, cpd)
                        counter.generate()
                        self.assertEqual(counter.output.get(), count_up)
                        self.assertTrue(counter.n_tcu.is_high())
                        self.assertTrue(counter.n_tcd.is_high())
                    elif not cpu == TriggerPoint.LOW and cpd == TriggerPoint.TRIGGERED:
                        # Count down
                        counter = load(input, n_ie, reset, cpu, cpd)
                        counter.generate()
                        self.assertEqual(counter.output.get(), count_down)
                        self.assertTrue(counter.n_tcu.is_high())
                        self.assertTrue(counter.n_tcd.is_high())
                    else:
                        # Hold
                        counter = load(input, n_ie, reset, cpu, cpd)
                        counter.input.set(value_floating(width))
                        counter.generate()
                        self.assertEqual(counter.output.get(), input)
                        if input == value_high(width):
                            if cpu == TriggerPoint.LOW:
                                self.assertTrue(counter.n_tcu.is_low())
                        else:
                            self.assertTrue(counter.n_tcu.is_high())
                        if input == value_low(width):
                            if cpd == TriggerPoint.LOW:
                                self.assertTrue(counter.n_tcd.is_low())
                        else:
                            self.assertTrue(counter.n_tcd.is_high())

class Test_Decoder_139(unittest.TestCase):
    def test_full_139(self):
        def make(input, n_ie):
            decoder = Decoder_139()
            decoder.input.set(input)
            decoder.n_ie.set(n_ie)
            return decoder

        if not FULL_TESTS: return
        width = 2
        # Disabled
        n_ie = value_high()
        for input in test_inputs(width):
            decoder = make(input, n_ie)
            decoder.generate()
            self.assertEqual(decoder.output_0.get(), value_high())
            self.assertEqual(decoder.output_1.get(), value_high())
            self.assertEqual(decoder.output_2.get(), value_high())
            self.assertEqual(decoder.output_3.get(), value_high())
        # Decode
        n_ie = value_low()
        decoder = make(value(LO, LO), n_ie)
        decoder.generate()
        self.assertEqual(decoder.output_0.get(), value_low())
        self.assertEqual(decoder.output_1.get(), value_high())
        self.assertEqual(decoder.output_2.get(), value_high())
        self.assertEqual(decoder.output_3.get(), value_high())
        decoder = make(value(LO, HI), n_ie)
        decoder.generate()
        self.assertEqual(decoder.output_0.get(), value_high())
        self.assertEqual(decoder.output_1.get(), value_low())
        self.assertEqual(decoder.output_2.get(), value_high())
        self.assertEqual(decoder.output_3.get(), value_high())
        decoder = make(value(HI, LO), n_ie)
        decoder.generate()
        self.assertEqual(decoder.output_0.get(), value_high())
        self.assertEqual(decoder.output_1.get(), value_high())
        self.assertEqual(decoder.output_2.get(), value_low())
        self.assertEqual(decoder.output_3.get(), value_high())
        decoder = make(value(HI, HI), n_ie)
        decoder.generate()
        self.assertEqual(decoder.output_0.get(), value_high())
        self.assertEqual(decoder.output_1.get(), value_high())
        self.assertEqual(decoder.output_2.get(), value_high())
        self.assertEqual(decoder.output_3.get(), value_low())


if __name__ == "__main__":
    # unittest.main()
    main()

