from ..points import *
from ..wiring import Wiring

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

class FixedWidthComponent(Component):
    def __init__(self, width, name=None):
        super().__init__(name)
        self.width = width

################################################################################

class ROM_28C256(FixedWidthComponent):
    def __init__(self, data_width, address_width, name=None):
        super().__init__(data_width, name)
        self.address_width = address_width
        self.address = WidePoint(self._subname('address'), self.address_width).IN()
        self.data = WidePoint(self._subname('data'), self.width).HiZ()
        self.n_ce = SignalPoint(self._subname('/ce')).IN()
        self.n_oe = SignalPoint(self._subname('/oe')).IN()
        self._content = [0] * 2**self.address_width
    
    def set_content(self, content):
        assert len(content) == 2**self.address_width
        for value in content:
            assert 0 <= value < 2**self.width
        self._content = content
        return self
    
    def generate(self):
        if self.n_ce.is_high() or self.n_oe.is_high():
            self.data.HiZ()
        else:
            index = value_to_int(self.address.get())
            data = self._content[index]
            data_value = int_to_value(data, self.width)
            self.data.OUT(data_value)
