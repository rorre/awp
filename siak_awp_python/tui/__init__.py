import asyncio
import importlib.resources as pkg_resources
import os
from typing import List

from rich.console import Console
from rich.markdown import Markdown
from rich.prompt import Confirm
from textual import events
from textual.app import App
from textual.reactive import Reactive
from textual.widgets import Footer, Header, ScrollView

from siak_awp_python import static
from siak_awp_python.config import SubjectSelection, write_config
from siak_awp_python.parser import Schedule
from siak_awp_python.request import SIAKClient
from siak_awp_python.tui.components.listing import Listing
from siak_awp_python.tui.components.matkul_tree import ClassClick, MatkulTree
from siak_awp_python.types import StrOrBytesPath, SubjectClasses
from siak_awp_python.utils import subject_to_config


class MyApp(App):
    """An example of a very simple Textual App"""

    selections: Reactive[SubjectClasses] = Reactive({})
    current_menu = Reactive("main")

    def __init__(
        self,
        username: str,
        password: str,
        config_path: StrOrBytesPath,
        schedule: Schedule,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.username = username
        self.password = password
        self.config_path = config_path
        self.schedule = schedule

    async def on_load(self, event: events.Load) -> None:
        """Bind keys with the app loads (but before entering application mode)"""
        await self.bind("b", "view.toggle('sidebar')", "Toggle sidebar")
        await self.bind("s", "save()", "Save to config")
        await self.bind("h", "toggle_help()", "Toggle help")
        await self.bind("q", "quit", "Quit")

    async def on_mount(self, event: events.Mount) -> None:
        """Create and dock the widgets."""

        async def load_help():
            md = pkg_resources.read_text(static, "help.md")
            self.help_content = Markdown(md)

        self.help_content = Markdown("")
        self.main_content = MatkulTree(self.schedule.classes)
        self.body = body = ScrollView(self.main_content)
        self.selection_body = s_body = Listing(self.selections, name="listing")

        # Header / footer / dock
        await self.view.dock(Header(), edge="top")
        await self.view.dock(Footer(), edge="bottom")
        await self.view.dock(
            s_body,
            edge="left",
            size=30,
            name="sidebar",
        )

        # Dock the body in the remaining space
        await self.view.dock(body, edge="right", name="main")

        await self.call_later(load_help)

    async def action_toggle_help(self):
        if self.current_menu == "help":
            self.current_menu = "main"
            await self.body.update(self.main_content)
        else:
            self.current_menu = "help"
            await self.body.update(self.help_content)
        self.body.refresh(layout=True)

    async def action_save(self):
        res: List[SubjectSelection] = []
        for selections in self.selections.values():
            res.append(subject_to_config(selections))

        write_config(
            self.config_path,
            {
                "username": self.username,
                "password": self.password,
                "fallback": "available",
                "selections": res,
            },
        )

    async def handle_class_click(self, message: ClassClick):
        subject_id = message.class_["subject_name"]
        if (
            subject_id in self.selections
            and message.class_ in self.selections[subject_id]
        ):
            self.selections[subject_id].remove(message.class_)
            if len(self.selections[subject_id]) == 0:
                self.selections.pop(subject_id)
        else:
            self.selections[subject_id] = [
                *self.selections.get(subject_id, []),
                message.class_,
            ]

        self.selection_body.refresh()

    async def watch_selections(self, value: SubjectClasses):
        self.selection_body.selections = value


async def get_schedule(c: SIAKClient, config: StrOrBytesPath, console: Console):
    if os.path.exists(config):
        console.print("[red bold]This will REPLACE your current config.")
        if not Confirm.ask("Are you sure you want to proceed?", console=console):
            console.print("Exitting...")
            return

    username = console.input("[b]Username: ")
    password = console.input("[b]Password: ")

    with console.status("Logging in..."):
        if not await c.login(username, password):
            console.print("[red]Failed to log in!")
            return

    console.print("[green]Logged in.")

    with console.status("Fetching schedules..."):
        schedule = await c.get_schedule()

    await c.aclose()
    return username, password, schedule


async def main(c: SIAKClient, config: StrOrBytesPath, console: Console):
    c = SIAKClient(console)
    username, password, schedule = await get_schedule(c, config, console)
    await MyApp(
        username=username,
        password=password,
        config_path=config,
        schedule=schedule,
        screen=True,
        title="SIAK AWP Configurator",
        log="textual.log",
    ).process_messages()
