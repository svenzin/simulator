from collections import defaultdict

from .points import BasePoint

################################################################################

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
