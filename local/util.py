import argparse
from typing import Callable
from datetime import timedelta
from dataclasses import asdict
from pathlib import Path

from pretty_cli import PrettyCli

from local.request_schema import RefPanel


def display(cli: PrettyCli, obj) -> None:
    """
    Flattens `obj` so arrays are displayed as dicts mapping idx -> entry.
    """
    out = asdict(obj)

    def _flatten(d: dict) -> dict:
        keys = list(d.keys())

        for k in keys:
            if d[k] is None:
                del d[k]
            elif isinstance(d[k], list):
                if len(d[k]) > 0:
                    d[k] = { i: _flatten(val) for (i, val) in enumerate(d[k]) }
                else:
                    del d[k]

        return d

    _flatten(out)
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


REFPANEL_LOOKUP = {
    "dev": {
        "hapmap": RefPanel.DEV_HAPMAP_2,
        "hapmap2": RefPanel.DEV_HAPMAP_2,
        "r3": RefPanel.DEV_TOPMED_R3_DEV,
        "topmedr3": RefPanel.DEV_TOPMED_R3_DEV,
        "r3prod": RefPanel.DEV_TOPMED_R3_PROD,
        "topmedr3prod": RefPanel.DEV_TOPMED_R3_PROD,
    },
    "prod": {
        "r3": RefPanel.PROD_TOPMED_R3,
        "topmedr3": RefPanel.PROD_TOPMED_R3,
    },
}


def late_check_refpanel(parser: argparse.ArgumentParser, env: str, refpanel: str) -> RefPanel:
    assert env in REFPANEL_LOOKUP.keys()

    processed = refpanel.strip().lower().replace("-", "").replace("_", "")

    if processed in REFPANEL_LOOKUP[env]:
        return REFPANEL_LOOKUP[env][processed]
    else:
        parser.error(f"-r/--refpanel must be a known environment-specific panel. Found unrecognized value: {refpanel}")
