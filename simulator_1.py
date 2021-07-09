from collections import namedtuple
from collections import defaultdict
import itertools

from simulator.value import *
from simulator.points import *
from simulator.components.components import Component
from simulator.components import boolean
from simulator.components import example

from simulator.circuit import Circuit


LO = 0
HI = 1


class Buffer(Component):
    def __init__(self):
        super().__init__()
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

class Inverter(Component):
    def __init__(self):
        super().__init__()
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

def main():
    vcc = SignalPoint('VCC').OUT(value_high())
    gnd = SignalPoint('GND').OUT(value_low())
    probe = Point('Probe')
    
    elements = [ probe, vcc, gnd ]

    circuit = Circuit()
    # circuit.add(vcc).add(gnd).add(probe)
    circuit.connect(probe, vcc)
    print(circuit.wiring.connections)
    print(elements)

    circuit.step()
    print(elements)

    circuit.connect(probe, gnd)
    circuit.step()
    print(elements)

    circuit.disconnect(probe, vcc)
    circuit.step()
    print(elements)

    circuit.disconnect(probe, gnd)
    circuit.step()
    print(elements)

    b = Buffer()
    i = Inverter()
    elements = [ probe, vcc, gnd, b, i ]
    
    (circuit
        .add(b).add(i)
        .connect(vcc, i.input)
        .connect(i.output, b.input)
        .connect(b.output, probe)
        .connect(vcc, b.n_enable)
    )

    print(elements)
    circuit.step()
    print(elements)
    (circuit
        .disconnect(vcc, b.n_enable)
        .connect(gnd, b.n_enable)
    )
    circuit.step()
    print(elements)

    circuit = Circuit()
    a = Point('a')
    b = Point('b')
    s = Point('Probe')
    c = Point('Probe')
    opand = boolean.And()
    opxor = boolean.Xor()
    (
        circuit.add(opand).add(opxor)
        .connect(a, opand.a)
        .connect(b, opand.b)
        .connect(opand.output, s)
        .connect(a, opxor.a)
        .connect(b, opxor.b)
        .connect(opxor.output, c)
    )
    
    elements = [a, b, opand, opxor, s, c]
    for va, vb in itertools.product([value_low(), value_high()], repeat=2):
        a.OUT(va)
        b.OUT(vb)
        circuit.step()
        print(elements)

    half_adder = Circuit()
    ha = example.HalfAdder()
    half_adder.add(ha).connect(a, ha.a).connect(b, ha.b)
    elements = [a, b, ha.s, ha.c]
    for va, vb in itertools.product([value_low(), value_high()], repeat=2):
        a.OUT(va)
        b.OUT(vb)
        half_adder.step()
        print(elements)

    cin = Point('cin')
    full_adder = Circuit()
    fa = example.FullAdder()
    full_adder.add(fa).connect(a, fa.a).connect(b, fa.b).connect(cin, fa.cin)
    elements = [a, b, cin, fa.s, fa.cout]
    for va, vb, vc in itertools.product([value_low(), value_high()], repeat=3):
        a.OUT(va)
        b.OUT(vb)
        cin.OUT(vc)
        full_adder.step()
        print(elements)

################################################################################

if __name__ == "__main__":
    main()

