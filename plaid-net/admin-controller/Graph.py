from __future__ import annotations
from typing import Hashable, Dict, Any
from Node import KeyedNode, Edge
from queue import Queue, LifoQueue, PriorityQueue


class DirectedGraph:
    def __init__(self):
        self.nodes: Dict[Hashable, KeyedNode] = {}

    def add_node(self, node: KeyedNode):
        self.nodes[node.key] = node

    def add_edge(self, tail: Hashable, head: Hashable, weight: int = 0):
        self.nodes[tail].add_edge(Edge(self.nodes[tail], self.nodes[head], weight))

    def remove_edge(self, tail: Hashable, head: Hashable):
        self.nodes[tail].remove_edge(head)

    def iter_breadth_first(self, start: Hashable):
        discovered: Dict[KeyedNode, bool] = {}
        for node in self.nodes.values():
            discovered[node] = False

        queue = Queue()
        queue.put(self.nodes[start])

        while not queue.empty():
            node = queue.get()
            yield node

            if not discovered[node]:
                discovered[node] = True
                for incident in node.edges.values():
                    if not discovered[incident.head]:
                        queue.put(incident.head)

    def iter_depth_first(self):
        pass

    def __str__(self):
        out = ""
        for node in self.nodes.values():
            out += str(node)
            if len(node.edges) > 0:
                out += ":"
            for edge in node.edges.values():
                out += " -> "
                out += str(edge.head)
                if edge.weight != 0:
                    out += " (" + str(edge.weight) + ")"
            out += "\n"
        return out


class UndirectedGraph(DirectedGraph):
    def add_edge(self, tail: Hashable, head: Hashable, weight: int = 0):
        super().add_edge(tail, head, weight)
        self.nodes[head].add_edge(Edge(self.nodes[head], self.nodes[tail], weight))

    def remove_edge(self, tail: Hashable, head: Hashable):
        super().remove_edge(tail, head)
        self.nodes[head].remove_edge(tail)
