import argparse
import asyncio
from typing import Awaitable, Callable, Dict, List, Literal

from rich.console import Console

from siak_awp_python.config import Config, load_config
from siak_awp_python.parser import IRSClass, IRSEdit
from siak_awp_python.request import SIAKClient, SIAKException
from siak_awp_python.tui import main as configure
from siak_awp_python.types import StrOrBytesPath


def fallback(
    preference: List[int],
    classes: List[IRSClass],
    strategy: Literal["available", "lowest"],
    console: Console,
):
    if strategy == "available":
        available = list(filter(lambda x: x.capacity > x.registrant, classes))
        if not available:
            console.log("[red]No classes found with available strategy")
            console.log(
                "[red]Falling back to lowest strategy with all possible classes"
            )
            return fallback(list(range(len(classes))), classes, "lowest", console)
        return min(available, key=lambda x: x.registrant)

    preferred_class = [classes[i] for i in preference]
    return min(preferred_class, key=lambda x: x.registrant)


def select_classes(cfg: Config, console: Console, irs: IRSEdit):
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
                console,
            )
            console.log("[green]Got class " + selected[pref["name"]].name)
    return selected


async def main(c: SIAKClient, config: StrOrBytesPath, console: Console):
    cfg = load_config(config)
    while True:
        try:
            with console.status("Logging in..."):
                await c.login(cfg["username"], cfg["password"])

            break
        except SIAKException as e:
            console.log(f"[yellow]{e.message}, logging out and retrying...")
            c.logout()

    while True:
        try:
            with console.status("Fetching IRS page..."):
                irs = await c.get_irs()
                console.log(irs.classes_by_id)

            break

        except SIAKException as e:
            console.log(f"[yellow]{e.message}, retrying...")
            if "opened" in e.message:
                console.log("[yellow]Relogging in")
                c.logout()
                await c.login(cfg["username"], cfg["password"])
            continue

    post_data = {}
    post_data["tokens"] = irs.token

    try:
        with console.status("Selecting..."):
            selected = select_classes(cfg, console, irs)

        console.rule("Result")
        console.print("[bold]Selected class")
        left_length = max(len(x["name"]) + 2 for x in cfg["selections"])

        for cls in cfg["selections"]:
            cls_info = "[white on red]Cannot get any class."
            if cls["name"] in selected:
                cls_info = "[black on cyan]" + selected[cls["name"]].name
            console.print("-", f"{cls['name']:<{left_length}}:", cls_info)

        # if not Confirm.ask("Are you sure you want to proceed?", console=console):
        #     console.print("Exitting...")
        #     return

        for cls_data in selected.values():
            post_data[cls_data.subject_id] = cls_data.class_id
    except BaseException:
        console.print_exception()
        console.log("[red]Error selecting classes, using defaults...")
        post_data.update(cfg["default"])

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
    console = Console()
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

    async def wrapper(f: Callable[[SIAKClient, StrOrBytesPath, Console], Awaitable]):
        c = SIAKClient(console)
        await f(c, args.config, console)
        await c.aclose()

    if args.init:
        asyncio.run(wrapper(configure))
    else:
        asyncio.run(wrapper(main))


if __name__ == "__main__":
    cli()
