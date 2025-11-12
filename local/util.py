import argparse
import tomllib
from pathlib import Path
from enum import Enum
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict, is_dataclass
from typing import Any, Iterable, Mapping, Sequence

from pretty_cli import PrettyCli


@dataclass
class ProjectInfo:
    name        : str
    version     : str
    description : str


def get_project_info() -> ProjectInfo:
    with open("pyproject.toml", "rb") as file:
        data = tomllib.load(file)

    project = data["project"]

    return ProjectInfo(
        name        = project["name"       ],
        version     = project["version"    ],
        description = project["description"],
    )


def get_user_agent() -> str:
    project_info = get_project_info()
    user_agent = f"{project_info.name}@{project_info.version}"
    return user_agent


def flatten_for_storage(obj: Any, skip_keys: Iterable[str]) -> Any:
    """
    Recursively converts dataclass and Mapping instances into dicts; Sequences into lists.

    Normalizes keys to lowercase strings with dash separators.

    Skips any fields whose key (after normalization) is in `skip_keys`.
    """

    skip_keys = set(skip_keys)

    def process_key(key: Any) -> str:
        return str(key).strip().lower().replace("_", "-")

    def process_mapping(map: Mapping) -> dict[str, Any]:
        d = dict()

        for (key, value) in map.items():
            key = process_key(key)
            if key in skip_keys:
                continue
            d[key] = flatten_for_storage(value, skip_keys)

        return d

    if isinstance(obj, str) or isinstance(obj, int) or isinstance(obj, float):
        # Handled explicitly to avoid recursion issues with str, and to keep it simple on basic types.
        return obj
    elif is_dataclass(obj) and not isinstance(obj, type):
        return process_mapping(asdict(obj))
    elif isinstance(obj, Mapping):
        return process_mapping(obj)
    elif isinstance(obj, Sequence):
        return [ flatten_for_storage(value, skip_keys) for value in obj ]
    else:
        return obj


def dictionarize(obj: Any) -> Any:
    """Recursively converts dataclass, Mapping, and Sequence instances into dicts. Skips `None` entries."""

    def process_key(key: Any) -> str:
        return str(key).strip()

    def process_mapping(map: Mapping) -> dict[str, Any]:
        return { process_key(key): dictionarize(value) for (key, value) in map.items() if value is not None }

    if isinstance(obj, str) or isinstance(obj, int) or isinstance(obj, float):
        # Handled explicitly to avoid recursion issues with str, and to keep it simple on basic types.
        return obj
    elif is_dataclass(obj) and not isinstance(obj, type):
        return process_mapping(asdict(obj))
    elif isinstance(obj, Mapping):
        return process_mapping(obj)
    elif isinstance(obj, Sequence):
        return process_mapping({ n: value for (n, value) in enumerate(obj) })
    else:
        return obj


def display(cli: PrettyCli, obj: Any) -> None:
    """
    Flattens `obj` so arrays are displayed as dicts mapping idx -> entry.
    """

    out = dictionarize(obj)
    cli.print(out)


def check_file(arg_value: str) -> Path:
    """
    Argparse helper. Converts the argument to a `Path` and ensures it is an existing file in the filesystem.
    """
    path = Path(arg_value)

    if not path.is_file():
        raise argparse.ArgumentTypeError(f"File not found: {arg_value}")

    return path


def check_timedelta(arg_value: str) -> timedelta:
    """
    Argparse helper. Converts an argument of shape `((hh:)mm:)ss` to a `timedelta` time amount expression.
    """

    try:
        parts = [ int(x) for x in arg_value.split(":") ]
        assert(1 <= len(parts) <= 3)

        if len(parts) == 1:
            h, m = 0, 0
            s = parts[0]
        elif len(parts) == 2:
            h = 0
            m, s = parts
        else:
            h, m, s = parts

        t = timedelta(hours=h, minutes=m, seconds=s)
    except:
        raise argparse.ArgumentTypeError(f"Invalid time expression; expected ((hh:)mm:)ss but found: {arg_value}")

    return t


def check_datetime(arg_value: str) -> datetime:
    """
    Argparse helper. Converts an ISO 8601 date-time expression to a `datetime` timestamp.
    """

    try:
        return datetime.fromisoformat(arg_value)
    except:
        raise argparse.ArgumentTypeError(f"Expected ISO 8601 date-time, but found: {arg_value}")


def json_default(value):
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    elif isinstance(value, datetime):
        return value.isoformat(sep=" ")
    elif isinstance(value, Enum):
        return value.name
    raise Exception(f"Value of type '{type(value)}' could not be parsed: {value}")


def parse_size(size: str) -> int:
    parts = size.split()
    assert len(parts) == 2, f"Expected <number> <unit>, but found: '{size}'"

    value = int(parts[0])
    units = parts[1]

    match units.lower():
        case "b" | "bytes":
            mutliplier = 1
        case "kb" | "kib":
            mutliplier = 1024
        case "mb" | "mib":
            mutliplier = 1024 ** 2
        case "gb" | "gib":
            mutliplier = 1024 ** 3
        case _:
            raise Exception(f"Units not recognized: {units}")

    return value * mutliplier
