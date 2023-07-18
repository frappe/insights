from collections import deque


class Graph:
    def __init__(self):
        self.nodes = []
        self.edges = {}
        self.metadata = {}

    def add_node(self, node):
        if node in self.nodes:
            return
        self.nodes.append(node)
        self.edges[node] = []

    def add_edge(self, node1, node2, metadata=None):
        if node2 in self.edges[node1]:
            return
        self.edges[node1].append(node2)
        if metadata:
            self.metadata[(node1, node2)] = metadata

    def __str__(self):
        return str(self.edges)

    def bfs(self, start, end):
        queue = deque()
        queue.append(start)
        visited = set()
        visited.add(start)
        while queue:
            node = queue.popleft()
            if node == end:
                return True
            for neighbor in self.edges[node]:
                if neighbor not in visited:
                    queue.append(neighbor)
                    visited.add(neighbor)
        return False

    def shortest_path(self, start, end):
        queue = deque()
        queue.append([start])
        visited = set()
        visited.add(start)
        while queue:
            path = queue.popleft()
            node = path[-1]
            if node == end:
                return path
            for neighbor in self.edges[node]:
                if neighbor not in visited:
                    queue.append(path + [neighbor])
                    visited.add(neighbor)

    def get_all_possible_path_from_source(self, source):
        queue = deque()
        queue.append([source])
        visited = set()
        visited.add(source)
        while queue:
            path = queue.popleft()
            node = path[-1]
            for neighbor in self.edges[node]:
                if neighbor not in visited:
                    queue.append(path + [neighbor])
                    visited.add(neighbor)
        visited.remove(source)
        return visited
