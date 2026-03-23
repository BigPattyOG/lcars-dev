"""LCARS loading animations."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import TypeVar

from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn

from lcars.cli.ui import theme

T = TypeVar("T")


def run_spinner(console: Console, description: str, action: Callable[[], T]) -> T:
    with Progress(
        SpinnerColumn(style=theme.HEADER_PURPLE),
        TextColumn(f"[{theme.HEADER_PURPLE}]{{task.description}}[/]"),
        console=console,
        transient=True,
    ) as progress:
        progress.add_task(description, total=None)
        return action()


def run_step_progress(
    console: Console,
    title: str,
    steps: Iterable[tuple[str, Callable[[], T]]],
) -> list[T]:
    step_list = list(steps)
    results: list[T] = []
    with Progress(
        TextColumn(f"[{theme.HEADER_PURPLE}]{{task.description}}[/]"),
        BarColumn(
            bar_width=None,
            complete_style=theme.PANEL_ORANGE,
            finished_style=theme.SUCCESS_GREEN,
        ),
        TextColumn(f"[{theme.VALUE_CYAN}]{{task.percentage:>3.0f}}%[/]"),
        console=console,
        expand=True,
        transient=True,
    ) as progress:
        task_id = progress.add_task(title, total=len(step_list))
        for label, action in step_list:
            progress.update(task_id, description=label)
            results.append(action())
            progress.advance(task_id)
    return results
