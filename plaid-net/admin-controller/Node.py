from __future__ import annotations
from typing import Hashable, Any, Dict


class KeyedNode:
    def __init__(self, key: Hashable):
        self.key: Hashable = key

        self.edges: Dict[Hashable, Edge] = {}

    def add_edge(self, edge: Edge):
        self.edges[edge.head.key] = edge

    def remove_edge(self, key: Hashable):
        self.edges.pop(key)

    def __str__(self):
        return str(self.key)


class Node(KeyedNode):
    def __init__(self):
        super().__init__(self)


class DataNode(Node):
    def __init__(self, data: Any):
        super().__init__()
        self.data: Any = data


class Edge:
    def __init__(self, tail: KeyedNode, head: KeyedNode, weight: int = 0):
        self.head: KeyedNode = head
        self.tail: KeyedNode = tail
        self.weight: int = weight
