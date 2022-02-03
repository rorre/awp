from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING, Union, cast

import rich
from rich.console import RenderableType
from rich.text import Text
from textual import events
from textual.message import Message, MessageTarget
from textual.reactive import Reactive
from textual.widgets import TreeClick, TreeControl, TreeNode

from siak_awp_python.parser import SubjectClass
from siak_awp_python.types import SubjectArray, SubjectClasses, SubjectTypeClasses

if TYPE_CHECKING:
    from siak_awp_python.tui import MyApp


@dataclass
class TreeType:
    data: Union[
        SubjectTypeClasses,
        SubjectClasses,
        SubjectArray,
        SubjectClass,
    ]
    is_class: bool = False


@rich.repr.auto
class ClassClick(Message, bubble=True):  # type: ignore
    def __init__(
        self,
        sender: MessageTarget,
        class_: SubjectClass,
    ) -> None:
        self.class_ = class_
        super().__init__(sender)


class MatkulTree(TreeControl[TreeType]):
    selections: Reactive[SubjectClasses] = Reactive({})

    def __init__(
        self,
        schedule: SubjectTypeClasses,
        name: str = None,
    ):
        self.schedule = schedule

        data = TreeType(schedule)
        super().__init__("Daftar Matkul", name=name, data=data)

    has_focus: Reactive[bool] = Reactive(False)

    def on_focus(self) -> None:
        self.has_focus = True

    def on_blur(self) -> None:
        self.has_focus = False

    def render_node(self, node: TreeNode[TreeType]) -> RenderableType:
        app = cast("MyApp", self.app)

        number = None
        if node.data.is_class:
            subject_data = node.data.data
            subject_name = subject_data["subject_name"]
            app.log("SELECTIONS", app.selections)
            if (
                subject_name in app.selections
                and subject_data in app.selections[subject_name]
            ):
                number = app.selections[subject_name].index(subject_data) + 1

        return self.render_tree_label(
            node,
            node.is_cursor,
            node.id == self.hover_node,
            self.has_focus,
            number,
        )

    @lru_cache(maxsize=1024 * 32)
    def render_tree_label(
        self,
        node: TreeNode[TreeType],
        is_cursor: bool,
        is_hover: bool,
        has_focus: bool,
        number: int,
    ) -> RenderableType:
        meta = {
            "@click": f"click_label({node.id})",
            "tree_node": node.id,
            "cursor": node.is_cursor,
        }
        label = Text(node.label) if isinstance(node.label, str) else node.label
        if is_hover:
            label.stylize("underline")

        if is_cursor and has_focus:
            label.stylize("reverse")

        if number is not None:
            icon = f"{number} |"
        elif node.data.is_class:
            icon = "- |"
        else:
            icon = ""

        icon_label = Text(f"{icon} ", no_wrap=True, overflow="ellipsis") + label
        icon_label.apply_meta(meta)
        return icon_label

    async def on_mount(self, event: events.Mount) -> None:
        await self.load_matkul(self.root)

    async def load_matkul(self, node: TreeNode[TreeType]):
        if isinstance(node.data.data, dict):
            for label, data in node.data.data.items():
                await node.add(label, TreeType(data))
        else:
            for subject in node.data.data:
                await node.add(subject["name"], TreeType(subject, True))

        node.loaded = True
        await node.expand()
        self.refresh(layout=True)

    async def handle_tree_click(self, message: TreeClick[TreeType]) -> None:
        data = message.node.data
        if data.is_class:
            await self.emit(ClassClick(self, data.data))
            return

        if not message.node.loaded:
            await self.load_matkul(message.node)
            await message.node.expand()
        else:
            await message.node.toggle()
