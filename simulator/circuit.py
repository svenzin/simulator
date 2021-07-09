from .components.components import Component
from .wiring import Wiring
from .points import OUT
from .value import *

################################################################################################

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
        drivers = [ p for p in neighbours if p.direction == OUT ]
        if len(drivers) == 0:
            for p in neighbours:
                p.set(value_floating())
        elif len(drivers) == 1:
            driver = drivers[0]
            value = driver.get()
            for p in neighbours:
                if p != driver:
                    p.set(value)
        else:
            for p in neighbours:
                p.set(value_conflict())
        # print(neighbours, drivers)

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

################################################################

class Circuit(Component):
    def add(self, component):
        if component is not self:
            self._components.add(component)
        return self

    def connect(self, point_a, point_b):
        self.wiring.connect(point_a, point_b)
        return self

    def disconnect(self, point_a, point_b):
        self.wiring.disconnect(point_a, point_b)
        return self

    def step(self, *, limit=100):
        n = 0
        while not iteration(self) and n < limit:
            n += 1
        return (n < limit, n)
