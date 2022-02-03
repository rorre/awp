from rich.panel import Panel
from rich.tree import Tree
from textual.reactive import Reactive
from textual.widget import Widget

from siak_awp_python.types import SubjectClasses


class Listing(Widget):
    def __init__(self, selections: Reactive[SubjectClasses], name=None):
        self.selections = selections
        super().__init__(name=name)

    def render(self):
        tree = Tree("Matkul Terpilih")
        for matkul, classes in self.selections.items():
            subtree = Tree(matkul)
            for cls in classes:
                subtree.add(cls["name"])
            tree.add(subtree)
        return Panel(tree)
