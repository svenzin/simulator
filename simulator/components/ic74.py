from ..points import *
from ..wiring import Wiring
from .components import FixedWidthComponent

################################################################################

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

################################################################################

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

################################################################################

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
            self.output.OUT(value_low(self.width))
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

################################################################################

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

################################################################################

class Decoder_139(FixedWidthComponent):
    def __init__(self, width, name=None):
        super().__init__(width, name)
        self.input = WidePoint(self._subname('input'), width).IN()
        self.outputs = [
            SignalPoint(self._subname('output_{}'.format(n))).OUT(value_floating())
            for n in range(2**self.width)
        ]
        self.n_ie = SignalPoint(self._subname('/ie')).IN()
    
    def generate(self):
        for output in self.outputs:
            output.OUT(value_high())
        if self.n_ie.is_low():
            n = value_to_int(self.input.get())
            self.outputs[n].OUT(value_low())
