class Node:
    def __init__(self, dt):
        self.data:Node = dt
        self.children:list[Node] = []

    def add_children(self, node):
        assert isinstance(node, Node)
        self.children.append(node)