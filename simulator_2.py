from collections import namedtuple
from collections import defaultdict
import itertools

from simulator.value import *
from simulator.points import *
from simulator.components.components import Component
from simulator.components import boolean
from simulator.components import example

from simulator.circuit import Circuit


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
    def __init__(self, *widths, name=None):
        super().__init__(name)
        wide_width = sum(widths)
        self.narrows = [
            HookPoint(self._subname('narrow_{}'.format(n)), width, self.narrow_2_wide)
            for n, width in enumerate(widths)
        ]
        self.wide = HookPoint(self._subname('wide'), wide_width, self.wide_to_narrow)
    
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

def main():
    # ControlSignal = namedtuple('ControlSignal', ['name', 'active_high'])
    # [
    #     ControlSignal('MAR_IN_B0', True),
    #     ControlSignal('MAR_IN_B1', True),
    #     ControlSignal('MAR_OUT',   False),
    #     ControlSignal('PC_IN',     False),
    #     ControlSignal('PC_OUT',    False),
    #     ControlSignal('PC_UP',     True),
    #     ControlSignal('SP_IN',     False),
    #     ControlSignal('SP_OUT',    False),
    #     ControlSignal('SP_UP',     False),
    #     ControlSignal('SP_DOWN',   False),
    #     ControlSignal('WIDE_OUT',  False),
    # ]
    # class Plate_0_Control:
    #     def __init__(self):
    #         self.MAR_IN_B0 = (', True),
    #         self.MAR_IN_B1', True),
    #         self.MAR_OUT',   False),
    #         self.PC_IN',     False),
    #         self.PC_OUT',    False),
    #         self.PC_UP',     True),
    #         self.SP_IN',     False),
    #         self.SP_OUT',    False),
    #         self.SP_UP',     False),
    #         self.SP_DOWN',   False),
    #         self.WIDE_OUT',  False),
    
    # # Basic
    # ONE = SignalPoint('ONE').OUT(value_high())
    # ZERO = SignalPoint('ZERO').OUT(value_low())
    # # Buses
    # ALU = WidePoint('ALU', 2)
    # WIDE = WidePoint('WIDE', 6)
    # ADDR = WidePoint('ADDR', 6)
    # # Points of interest
    # PC = WidePoint('PC', 6)
    # SP = WidePoint('SP', 6)
    # MAR = WidePoint('MAR', 6)
    # # Control
    # MAR_IN = WidePoint('MAR_IN', 2)
    # MAR_OUT = SignalPoint('MAR_OUT')
    # PC_IN = SignalPoint('PC_IN')
    # PC_OUT = SignalPoint('PC_OUT')
    # PC_UP = SignalPoint('PC_UP')
    # SP_IN = SignalPoint('SP_IN')
    # SP_OUT = SignalPoint('SP_OUT')
    # SP_UP = SignalPoint('SP_UP')
    # SP_DOWN = SignalPoint('SP_DOWN')
    # WIDE_OUT = SignalPoint('WIDE_OUT')
    # CLOCK = SignalPoint('CLOCK')
    # # Plate
    # plate_0 = Circuit('Plate_0')
    # PC_IC = Counter_161(6, 'PC')
    # SP_IC = Counter_193(6, 'SP')
    # MAR0 = Register_173(2, 'MAR0')
    # MAR1 = Register_173(2, 'MAR1')
    # MAR2 = Register_173(2, 'MAR2')
    # MAR_IN_DECODER = Decoder_139(2, 'MAR_IN_DECODER')
    # MAR012_2_MAR = Splitter(2, 2, 2, name='MAR012_2_MAR')
    # PC_2_WIDE = Buffer_541(6, 'PC_2_WIDE')
    # SP_2_WIDE = Buffer_541(6, 'SP_2_WIDE')
    # MAR_2_WIDE = Buffer_541(6, 'MAR_2_WIDE')
    # WIDE_2_ADDR = Buffer_541(6, 'WIDE_2_ADDR')
    # plate_0.add(PC_IC)
    # plate_0.add(SP_IC)
    # plate_0.add(MAR0)
    # plate_0.add(MAR1)
    # plate_0.add(MAR2)
    # plate_0.add(MAR_IN_DECODER)
    # plate_0.add(PC_2_WIDE)
    # plate_0.add(SP_2_WIDE)
    # plate_0.add(MAR_2_WIDE)
    # plate_0.add(WIDE_2_ADDR)
    # # PC
    # plate_0.connect(PC_IC.input, WIDE)
    # plate_0.connect(PC_IC.output, PC)
    # plate_0.connect(PC_IC.n_reset, ONE)
    # plate_0.connect(PC_IC.clock, CLOCK)
    # plate_0.connect(PC_IC.n_ie, PC_IN)
    # plate_0.connect(PC_IC.cep, PC_UP)
    # plate_0.connect(PC_IC.cet, PC_UP)
    # # PC_IC.tc
    # # SP
    # plate_0.connect(SP_IC.input, WIDE)
    # plate_0.connect(SP_IC.output, SP)
    # plate_0.connect(SP_IC.reset, ZERO)
    # plate_0.connect(SP_IC.n_ie, SP_IN)
    # plate_0.connect(SP_IC.cpu, SP_UP)
    # plate_0.connect(SP_IC.cpd, SP_DOWN)
    # # SP_IC.n_tcu
    # # SP_IC.n_tcd
    # # MAR0
    # plate_0.connect(MAR0.input, ALU)
    # # MAR0.output
    # plate_0.connect(MAR0.n_ie, MAR_IN_DECODER.outputs[0])
    # plate_0.connect(MAR0.n_oe, ZERO)
    # plate_0.connect(MAR0.reset, ZERO)
    # plate_0.connect(MAR0.clock, CLOCK)
    # # MAR1
    # plate_0.connect(MAR1.input, ALU)
    # # MAR1.output
    # plate_0.connect(MAR1.n_ie, MAR_IN_DECODER.outputs[1])
    # plate_0.connect(MAR1.n_oe, ZERO)
    # plate_0.connect(MAR1.reset, ZERO)
    # plate_0.connect(MAR1.clock, CLOCK)
    # # MAR2
    # plate_0.connect(MAR2.input, ALU)
    # # MAR2.output
    # plate_0.connect(MAR2.n_ie, MAR_IN_DECODER.outputs[2])
    # plate_0.connect(MAR2.n_oe, ZERO)
    # plate_0.connect(MAR2.reset, ZERO)
    # plate_0.connect(MAR2.clock, CLOCK)
    # # MAR_IN_DECODER
    # plate_0.connect(MAR_IN_DECODER.input, MAR_IN)
    # # MAR_IN_DECODER.output_0
    # # MAR_IN_DECODER.output_1
    # # MAR_IN_DECODER.output_2
    # # MAR_IN_DECODER.output_3
    # plate_0.connect(MAR_IN_DECODER.n_ie, ZERO)
    # # MAR012_2_MAR
    # plate_0.connect(MAR012_2_MAR.narrows[0], MAR0.output)
    # plate_0.connect(MAR012_2_MAR.narrows[1], MAR1.output)
    # plate_0.connect(MAR012_2_MAR.narrows[2], MAR2.output)
    # plate_0.connect(MAR012_2_MAR.wide, MAR)
    # # PC_2_WIDE
    # plate_0.connect(PC_2_WIDE.n_oe, PC_OUT)
    # plate_0.connect(PC_2_WIDE.input, PC)
    # plate_0.connect(PC_2_WIDE.output, WIDE)
    # # SP_2_WIDE
    # plate_0.connect(SP_2_WIDE.n_oe, SP_OUT)
    # plate_0.connect(SP_2_WIDE.input, SP)
    # plate_0.connect(SP_2_WIDE.output, WIDE)
    # # MAR_2_WIDE
    # plate_0.connect(MAR_2_WIDE.n_oe, MAR_OUT)
    # plate_0.connect(MAR_2_WIDE.input, MAR)
    # plate_0.connect(MAR_2_WIDE.output, WIDE)
    # # WIDE_2_ADDR
    # plate_0.connect(WIDE_2_ADDR.n_oe, WIDE_OUT)
    # plate_0.connect(WIDE_2_ADDR.input, WIDE)
    # plate_0.connect(WIDE_2_ADDR.output, ADDR)
    
    # elements = [ PC, SP, MAR, ALU, WIDE, ADDR ]
    # # elements = [ ALU, MAR0.input, MAR1.input, MAR2.input, MAR012_2_MAR.narrows, MAR012_2_MAR.wide, MAR]
    # print(elements)

    # def setup(xMAR_IN, xMAR_OUT,
    #     xPC_IN, xPC_OUT, xPC_UP,
    #     xSP_IN, xSP_OUT, xSP_UP, xSP_DOWN,
    #     xWIDE_OUT, xCLOCK):
    #     MAR_IN.OUT(value(*xMAR_IN))
    #     MAR_OUT.OUT(value(xMAR_OUT))
    #     PC_IN.OUT(value(xPC_IN))
    #     PC_OUT.OUT(value(xPC_OUT))
    #     PC_UP.OUT(value(xPC_UP))
    #     SP_IN.OUT(value(xSP_IN))
    #     SP_OUT.OUT(value(xSP_OUT))
    #     SP_UP.OUT(value(xSP_UP))
    #     SP_DOWN.OUT(value(xSP_DOWN))
    #     WIDE_OUT.OUT(value(xWIDE_OUT))
    #     CLOCK.OUT(value(xCLOCK))
    # def execute(xMAR_IN, xMAR_OUT,
    #     xPC_IN, xPC_OUT, xPC_UP,
    #     xSP_IN, xSP_OUT, xSP_UP, xSP_DOWN,
    #     xWIDE_OUT):
    #     # print(xMAR_IN, xMAR_OUT, xPC_IN, xPC_OUT, xPC_UP, xSP_IN, xSP_OUT, xSP_UP, xSP_DOWN, xWIDE_OUT)
    #     setup(xMAR_IN, xMAR_OUT, xPC_IN, xPC_OUT, xPC_UP, xSP_IN, xSP_OUT, xSP_UP, xSP_DOWN, xWIDE_OUT, 0)
    #     step(plate_0)
    #     setup(xMAR_IN, xMAR_OUT, xPC_IN, xPC_OUT, xPC_UP, xSP_IN, xSP_OUT, xSP_UP, xSP_DOWN, xWIDE_OUT, 1)
    #     step(plate_0)
    # # 011011 > MAR
    # print()
    # print('011011 > MAR')
    # ALU.OUT(value(0, 1))
    # execute([0, 0], 1, 1, 1, 0, 1, 1, 1, 1, 1)
    # print(elements)
    # ALU.OUT(value(1, 0))
    # execute([0, 1], 1, 1, 1, 0, 1, 1, 1, 1, 1)
    # print(elements)
    # ALU.OUT(value(1, 1))
    # execute([1, 0], 1, 1, 1, 0, 1, 1, 1, 1, 1)
    # print(elements)
    # ALU.IN()
    # # 111111 > PC, SP
    # print()
    # print('111111 > PC, SP')
    # WIDE.OUT(value(1, 1, 1, 1, 1, 1))
    # execute([1, 1], 1, 0, 1, 0, 0, 1, 1, 1, 1)
    # print(elements)
    # WIDE.IN()
    # # ++PC
    # print('++PC')
    # execute([1, 1], 1, 1, 1, 1, 1, 1, 1, 1, 0)
    # print(elements)
    # # --SP
    # print('--SP')
    # execute([1, 1], 1, 1, 1, 0, 1, 1, 1, 0, 0)
    # print(elements)
    # execute([1, 1], 1, 1, 1, 0, 1, 1, 1, 1, 0)
    # print(elements)
    # # MAR > PC, ADDR
    # print()
    # print('MAR > PC, ADDR')
    # execute([1, 1], 0, 0, 1, 0, 1, 1, 1, 1, 0)
    # print(elements)
    # # SP > ADDR
    # print()
    # print('SP > ADDR')
    # execute([1, 1], 1, 1, 1, 0, 1, 0, 1, 1, 0)
    # print(elements)

    # # MAR_IN, MAR_OUT
    # # PC_IN, PC_OUT, PC_UP
    # # SP_IN, SP_OUT, SP_UP, SP_DOWN
    # # WIDE_OUT
    # oNOP = {
    #     MAR_IN: [1, 1], MAR_OUT: 1,
    #     PC_IN: 1, PC_OUT: 1, PC_UP: 0,
    #     SP_IN: 1, SP_OUT: 1, SP_UP: 1, SP_DOWN: 1,
    #     WIDE_OUT: 1
    # }
    # oMAR0_IN = { MAR_IN: [0, 0] }
    # oMAR1_IN = { MAR_IN: [0, 1] }
    # oMAR2_IN = { MAR_IN: [1, 0] }
    # oMAR_OUT = { MAR_OUT: 0, PC_OUT: 1, SP_OUT: 1 }
    # oPC_IN = { PC_IN: 0 }
    # oPC_OUT = { MAR_OUT: 1, PC_OUT: 0, SP_OUT: 1 }
    # oPC_UP = { PC_IN: 1, PC_UP: 1 }
    # oSP_IN = { SP_IN: 0 }
    # oSP_OUT = { MAR_OUT: 1, PC_OUT: 1, SP_OUT: 0 }
    # oSP_UP = { SP_IN: 1, SP_UP: 0, SP_DOWN: 1 }
    # oSP_DOWN = { SP_IN: 1, SP_UP: 1, SP_DOWN: 0 }
    # oWIDE_OUT = { WIDE_OUT: 0 }
    # def micro_op(*commands):
    #     uops = {}
    #     for command in commands:
    #         assert len(uops.keys() & command.keys()) == 0
    #         uops.update(command)
    #     uop = oNOP.copy()
    #     uop.update(uops)
    #     return (
    #         uop[MAR_IN], uop[MAR_OUT],
    #         uop[PC_IN], uop[PC_OUT], uop[PC_UP],
    #         uop[SP_IN], uop[SP_OUT], uop[SP_UP], uop[SP_DOWN],
    #         uop[WIDE_OUT]
    #         )

    # print()
    # print('000000 > MAR')
    # ALU.OUT(value(0, 0))
    # execute(*micro_op(oMAR0_IN))
    # print(elements)
    # execute(*micro_op(oMAR1_IN))
    # print(elements)
    # execute(*micro_op(oMAR2_IN))
    # print(elements)
    # ALU.IN()
    # print()
    # print('MAR > PC, SP')
    # execute(*micro_op(oMAR_OUT, oPC_IN, oSP_IN))
    # print(elements)
    # print('++PC')
    # execute(*micro_op(oPC_UP))
    # print(elements)
    # print('--SP')
    # execute(*micro_op(oSP_DOWN))
    # print(elements)
    # execute(*micro_op(oNOP))
    # print(elements)
    # print()
    # print('MAR > PC, ADDR')
    # execute(*micro_op(oMAR_OUT, oPC_IN, oWIDE_OUT))
    # print(elements)
    # print()
    # print('SP > ADDR')
    # execute(*micro_op(oSP_OUT, oWIDE_OUT))
    # print(elements)

    # # Plate 1
    # plate_1 = Circuit('Plate 1')
    pass

################################################################################

if __name__ == "__main__":
    main()

