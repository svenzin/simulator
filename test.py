import itertools
import unittest

from simulator.value import *
from simulator.points import *
from simulator.wiring import *
from simulator.components.components import *
from simulator.components import boolean, ic74, memory

from simulator_1 import Buffer, Inverter

def test_signals():
    return [ value_low(), value_high() ]

def test_clocks():
    return [ TriggerPoint.LOW, TriggerPoint.HIGH, TriggerPoint.TRIGGERED ]

def test_inputs(width):
    return [ value(*x) for x in itertools.product([LOW, HIGH], repeat=width) ]

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
        bits = [
            value(LOW, LOW),
            value(LOW, HIGH),
            value(HIGH, LOW),
            value(HIGH, HIGH)
        ]
        not_bits = [
            value(HIGH, HIGH),
            value(HIGH, LOW),
            value(LOW, HIGH),
            value(LOW, LOW)
        ]
        for x, not_x in zip(bits, not_bits):
            b.input.set(x)
            b.generate()
            self.assertEqual(b.output.get(), not_x)

class Test_And(unittest.TestCase):
    def test_and_bit(self):
        e = boolean.And()
        for a0, b0 in itertools.product([LOW, HIGH], repeat=2):
            r0 = a0 and b0
            e.a.set(value(a0))
            e.b.set(value(b0))
            e.generate()
            self.assertEqual(e.output.get(), value(r0))

    def test_and_bits(self):
        e = boolean.And()
        for a0, a1, b0, b1 in itertools.product([LOW, HIGH], repeat=4):
            r0 = a0 and b0
            r1 = a1 and b1
            e.a.set(value(a0, a1))
            e.b.set(value(b0, b1))
            e.generate()
            self.assertEqual(e.output.get(), value(r0, r1))

class Test_Register_173(unittest.TestCase):
    def test_full_173(self):
        def make(input, n_ie, n_oe, reset, clock):
            width = len(input)
            register = ic74.Register_173(width)
            register.input.set(input)
            register.n_ie.set(n_ie)
            register.n_oe.set(n_oe)
            register.reset.set(reset)
            register.clock._test_set(clock)
            return register
        
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
    def test_full_541(self):
        def make(input, n_oe):
            width = len(input)
            buffer = ic74.Buffer_541(width)
            buffer.input.set(input)
            buffer.n_oe.set(n_oe)
            return buffer
        
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
            counter = ic74.Counter_161(width)
            counter.input.set(input)
            return set(counter, n_ie, n_reset, cep, cet, clock)

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
            counter = ic74.Counter_193(width)
            counter.input.set(input)
            return setup(counter, n_ie, reset, cpu, cpd)
        
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
            decoder = ic74.Decoder_139(2)
            decoder.input.set(input)
            decoder.n_ie.set(n_ie)
            return decoder

        width = 2
        # Disabled
        n_ie = value_high()
        for input in test_inputs(width):
            decoder = make(input, n_ie)
            decoder.generate()
            self.assertEqual(decoder.outputs[0].get(), value_high())
            self.assertEqual(decoder.outputs[1].get(), value_high())
            self.assertEqual(decoder.outputs[2].get(), value_high())
            self.assertEqual(decoder.outputs[3].get(), value_high())
        # Decode
        n_ie = value_low()
        decoder = make(value(LOW, LOW), n_ie)
        decoder.generate()
        self.assertEqual(decoder.outputs[0].get(), value_low())
        self.assertEqual(decoder.outputs[1].get(), value_high())
        self.assertEqual(decoder.outputs[2].get(), value_high())
        self.assertEqual(decoder.outputs[3].get(), value_high())
        decoder = make(value(LOW, HIGH), n_ie)
        decoder.generate()
        self.assertEqual(decoder.outputs[0].get(), value_high())
        self.assertEqual(decoder.outputs[1].get(), value_low())
        self.assertEqual(decoder.outputs[2].get(), value_high())
        self.assertEqual(decoder.outputs[3].get(), value_high())
        decoder = make(value(HIGH, LOW), n_ie)
        decoder.generate()
        self.assertEqual(decoder.outputs[0].get(), value_high())
        self.assertEqual(decoder.outputs[1].get(), value_high())
        self.assertEqual(decoder.outputs[2].get(), value_low())
        self.assertEqual(decoder.outputs[3].get(), value_high())
        decoder = make(value(HIGH, HIGH), n_ie)
        decoder.generate()
        self.assertEqual(decoder.outputs[0].get(), value_high())
        self.assertEqual(decoder.outputs[1].get(), value_high())
        self.assertEqual(decoder.outputs[2].get(), value_high())
        self.assertEqual(decoder.outputs[3].get(), value_low())

class Test_ROM_28C256(unittest.TestCase):
    def test_full_28c256(self):
        def make(width, address, n_ce, n_oe):
            address_width = len(address)
            rom = memory.ROM_28C256(width, address_width)
            rom_content = [ n % 2**width for n in range(2**address_width) ]
            rom.set_content(rom_content)
            rom.address.set(address)
            rom.n_ce.set(n_ce)
            rom.n_oe.set(n_oe)
            return rom
        
        width = 4
        address_width = 8
        # Output disabled
        n_oe = value_high()
        for address in test_inputs(address_width):
            for n_ce in test_signals():
                rom = make(width, address, n_ce, n_oe)
                rom.generate()
                self.assertEqual(rom.data.get(), value_hi_z(width))
        # Chip disabled
        n_ce = value_high()
        for address in test_inputs(address_width):
            for n_oe in test_signals():
                rom = make(width, address, n_ce, n_oe)
                rom.generate()
                self.assertEqual(rom.data.get(), value_hi_z(width))
        # Read
        n_ce = value_low()
        n_oe = value_low()
        for address in test_inputs(address_width):
            rom = make(width, address, n_ce, n_oe)
            rom.generate()
            expected = int_to_value(value_to_int(address), width)
            self.assertEqual(rom.data.get(), expected)
    
    def test_set_content(self):
        rom = memory.ROM_28C256(4, 4)

        correct_content = [ n for n in range(16) ]
        # Don't raise exception
        rom.set_content(correct_content)

        too_short = correct_content[:-1]
        self.assertRaises(AssertionError, rom.set_content, too_short)

        too_long = correct_content + [0]
        self.assertRaises(AssertionError, rom.set_content, too_long)

        too_big = correct_content
        too_big[0] = 16
        self.assertRaises(AssertionError, rom.set_content, too_big)

if __name__ == "__main__":
    unittest.main()

