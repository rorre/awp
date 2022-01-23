import argparse
import asyncio
import os
from typing import Dict, List, Literal, Tuple, TypeVar, Union, overload

from rich import inspect
from rich.console import Console
from rich.prompt import Confirm, Prompt

from siak_awp_python.config import load_config, write_config
from siak_awp_python.external.pick import pick
from siak_awp_python.parser import IRSClass, Schedule, SubjectClass
from siak_awp_python.request import SIAKClient, SIAKException
from siak_awp_python.utils import selection_to_config

console = Console()
T = TypeVar("T")
MaybeList = Union[T, List[T]]


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


def fallback(
    preference: List[int],
    classes: List[IRSClass],
    strategy: Literal["available", "lowest"],
):
    if strategy == "available":
        available = list(filter(lambda x: x.capacity > x.registrant, classes))
        if not available:
            return fallback(list(range(len(classes))), classes, "lowest")
        return min(available, key=lambda x: x.registrant)

    preferred_class = [classes[i] for i in preference]
    return min(preferred_class, key=lambda x: x.registrant)


async def configure(c: SIAKClient, config: os.PathLike):
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


async def main(c: SIAKClient, config: os.PathLike):
    cfg = load_config(config)
    while True:
        try:
            with console.status("Logging in..."):
                await c.login(cfg["username"], cfg["password"])

            with console.status("Fetching IRS page..."):
                irs = await c.get_irs()

            break
        except SIAKException:
            console.log("[yellow]IRS not yet opened, logging out and retrying...")
            c.logout()

    with console.status("Selecting..."):
        selected: Dict[str, IRSClass] = {}
        for pref in cfg["selections"]:
            console.log(f"Selecting for [cyan]{pref['name']}")
            subject_classes = irs.get_classes_by_id(pref["code"], pref["curriculum"])
            for i in pref["preference"]:
                current_cls = subject_classes[i]
                if (
                    current_cls.registrant >= current_cls.capacity
                    and cfg["fallback"] != "dontcare"
                ):
                    console.log(
                        f"Class [cyan]{current_cls.name}[/cyan] is [red]full[/red]."
                        + f" [gray]({current_cls.registrant}/{current_cls.capacity})[/gray]"
                        + " Skipping..."
                    )
                    continue

                console.log("[green]Got class " + current_cls.name)
                selected[pref["name"]] = current_cls
                break
            else:
                console.log(
                    "[red]Running fallback with",
                    f"[bold]{cfg['fallback']}[/bold]",
                    "[red]strategy...",
                )
                selected[pref["name"]] = fallback(
                    pref["preference"],
                    subject_classes,
                    cfg["fallback"],  # type: ignore
                )

    console.rule("Result")
    console.print("[bold]Selected class")
    left_length = max(len(x["name"]) + 2 for x in cfg["selections"])

    for cls in cfg["selections"]:
        cls_info = "[white on red]Cannot get any class."
        if cls["name"] in selected:
            cls_info = "[black on cyan]" + selected[cls["name"]].name
        console.print("-", f"{cls['name']:<{left_length}}:", cls_info)

    if not Confirm.ask("Are you sure you want to proceed?", console=console):
        console.print("Exitting...")
        return

    post_data = {}
    post_data["tokens"] = irs.token
    for cls_data in selected.values():
        post_data[cls_data.subject_id] = cls_data.class_id

    # inspect(post_data)
    await c.post_irs(post_data)
    console.print("Done!")

    console.rule("Verification")
    console.print(
        "To verify, go to https://academic.ui.ac.id/ and insert the following JS code:"
    )
    console.print()
    for name, value in c._client.cookies.items():
        console.print(f'document.cookie ="{name}={value}; path=/; secure"')
    console.print(
        'window.location = "https://academic.ui.ac.id/main/CoursePlan/CoursePlanViewSummary"'
    )


def cli():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--init",
        "-i",
        default=False,
        type=bool,
        action=argparse.BooleanOptionalAction,
    )
    parser.add_argument("--config", "-c", default="config.yaml")
    args = parser.parse_args()

    async def wrapper(f):
        c = SIAKClient(console)
        await f(c, args.config)
        await c.aclose()

    if args.init:
        asyncio.run(wrapper(configure))
    else:
        asyncio.run(wrapper(main))


if __name__ == "__main__":
    cli()
