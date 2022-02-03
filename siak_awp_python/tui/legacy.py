import os
from typing import List, Literal, Tuple, overload

from rich.console import Console
from rich.prompt import Confirm, Prompt

from siak_awp_python.config import write_config
from siak_awp_python.external.pick import pick
from siak_awp_python.parser import Schedule, SubjectClass
from siak_awp_python.request import SIAKClient
from siak_awp_python.types import MaybeList
from siak_awp_python.utils import selection_to_config


def pick_subject(schedule: Schedule):
    title = "Select Subject"
    options: List[str] = []
    for s in schedule.classes.values():
        options.extend(s.keys())

    options.sort()
    options.append("Cancel")

    selected_subject: Tuple[str, int] = pick(options, title)
    if selected_subject[0] == options[-1]:
        return

    class_type = [
        ctype for ctype, val in schedule.classes.items() if selected_subject[0] in val
    ][0]
    classes = schedule.classes[class_type][selected_subject[0]]
    return classes


@overload
def pick_class(
    classes: List[SubjectClass],
    multiselect: Literal[True],
) -> List[SubjectClass]:
    ...


@overload
def pick_class(
    classes: List[SubjectClass],
    multiselect: Literal[False],
) -> SubjectClass:
    ...


@overload
def pick_class(
    classes: List[SubjectClass],
    multiselect: bool,
) -> MaybeList[SubjectClass]:
    ...


def pick_class(classes: List[SubjectClass], multiselect: bool = False):
    title = "Select Class"
    if multiselect:
        title += "\nSelect at least one by marking it with SPACE, finish with ENTER."
        title += "\nThe number is preference, with lowest being preferred."
        title += "\nTo cancel, just mark cancel and press ENTER"
    options = [f"{c['name']} | {c['teachers']}" for c in classes]
    options.append("Cancel")

    selected_class: MaybeList[Tuple[str, int]] = pick(
        options,
        title,
        multiselect=multiselect,
        min_selection_count=1,
    )

    if isinstance(selected_class, list):
        if selected_class[0][0] == options[-1]:
            return
        return [classes[opt[1]] for opt in selected_class]
    else:
        if selected_class[0] == options[-1]:
            return
        return classes[selected_class[1]]


async def configure(c: SIAKClient, config: os.PathLike, console: Console):
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

    selected: List[SubjectClass] = []
    while True:
        title = "What to do?"
        options = ["Add Classes", "Remove Class", "View", "Exit"]
        action: Tuple[str, int] = pick(options, title)
        if action[1] == 0:
            classes = pick_subject(schedule)
            if not classes:
                continue

            selected_class = pick_class(classes, True)
            if selected_class:
                selected.extend(selected_class)

        elif action[1] == 1:
            removed_class = pick_class(selected, False)
            if removed_class:
                selected.remove(removed_class)

        elif action[1] == 2:
            title_token = ["Selected classes:"]
            for cls in selected:
                title_token.append("- " + cls["name"])
            options = ["OK"]
            pick(options, "\n".join(title_token))

        elif action[1] == 3:
            break

    console.print("Select fallback strategy if all classes are full:")
    console.print(
        "[yellow]1.[/yellow]",
        "Select preferred class, but with lowest registrant",
        "[bold](Default)[/bold]",
    )
    console.print("[yellow]2.[/yellow] Select any available class")
    console.print("[red]3. Simply don't care and pick most preferred class")
    choice = Prompt.ask("Select", console=console, choices=["1", "2", "3"])
    if choice == "1":
        fallback = "lowest"
    elif choice == "2":
        fallback = "available"
    elif choice == "3":
        fallback = "dontcare"

    write_config(
        config,
        {
            "username": username,
            "password": password,
            "fallback": fallback,  # type: ignore
            "selections": selection_to_config(selected),
        },
    )
