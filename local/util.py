from enum import Enum
import argparse
from datetime import datetime, timedelta
from dataclasses import asdict, is_dataclass
from pathlib import Path

from pretty_cli import PrettyCli

from local.env import Environment
from local.request_schema import RefPanel


def display(cli: PrettyCli, obj) -> None:
    """
    Flattens `obj` so arrays are displayed as dicts mapping idx -> entry.
    """
    out = asdict(obj)

    def _flatten(d) -> dict:
        if not isinstance(d, dict):
            return d

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


def check_datetime(arg_value: str) -> datetime:
    """
    Argparse helper. Converts an ISO 8601 date-time expression to a `datetime` timestamp.
    """

    try:
        return datetime.fromisoformat(arg_value)
    except:
        raise argparse.ArgumentTypeError(f"Expected ISO 8601 date-time, but found: {arg_value}")


REFPANEL_LOOKUP = {
    Environment.TOPMED_DEV: {
        "hapmap"       : RefPanel.TOPMED_DEV_HAPMAP_2,
        "hapmap2"      : RefPanel.TOPMED_DEV_HAPMAP_2,
        "r3"           : RefPanel.TOPMED_DEV_TOPMED_R3_DEV,
        "topmedr3"     : RefPanel.TOPMED_DEV_TOPMED_R3_DEV,
        "r3prod"       : RefPanel.TOPMED_DEV_TOPMED_R3_PROD,
        "topmedr3prod" : RefPanel.TOPMED_DEV_TOPMED_R3_PROD,
    },
    Environment.TOPMED_PROD: {
        "r3"       : RefPanel.TOPMED_PROD_TOPMED_R3,
        "topmedr3" : RefPanel.TOPMED_PROD_TOPMED_R3,
    },
    Environment.MICHIGAN: {
        "1000gphase1"          : RefPanel.MICHIGAN_1KG_P1_V3,
        "1000gp1"              : RefPanel.MICHIGAN_1KG_P1_V3,
        "1000gphase1v3"        : RefPanel.MICHIGAN_1KG_P1_V3,
        "1000gp1v3"            : RefPanel.MICHIGAN_1KG_P1_V3,

        "1000gphase3"          : RefPanel.MICHIGAN_1KG_P3,
        "1000gp3"              : RefPanel.MICHIGAN_1KG_P3,
        "1000gphase3low"       : RefPanel.MICHIGAN_1KG_P3,
        "1000gp3low"           : RefPanel.MICHIGAN_1KG_P3,

        "1000gphase3deep"      : RefPanel.MICHIGAN_1KG_P3_30X,
        "1000gphase330x"       : RefPanel.MICHIGAN_1KG_P3_30X,
        "1000gp3deep"          : RefPanel.MICHIGAN_1KG_P3_30X,
        "1000gp330x"           : RefPanel.MICHIGAN_1KG_P3_30X,

        "1000gphase3v5"        : RefPanel.MICHIGAN_1KG_P3_V5,
        "1000gp3v5"            : RefPanel.MICHIGAN_1KG_P3_V5,

        "caapa"                : RefPanel.MICHIGAN_CAAPA,
        "africanamericanpanel" : RefPanel.MICHIGAN_CAAPA,
        "africanamerican"      : RefPanel.MICHIGAN_CAAPA,

        "gasp"                 : RefPanel.MICHIGAN_GASP,
        "genomeasiapilot"      : RefPanel.MICHIGAN_GASP,
        "genomeasia"           : RefPanel.MICHIGAN_GASP,
        "asiapilot"            : RefPanel.MICHIGAN_GASP,

        "hrc"                  : RefPanel.MICHIGAN_HRC_R11,
        "r11"                  : RefPanel.MICHIGAN_HRC_R11,
        "hrcr11"               : RefPanel.MICHIGAN_HRC_R11,

        "hapmap"               : RefPanel.MICHIGAN_HAPMAP_2,
        "hapmap2"              : RefPanel.MICHIGAN_HAPMAP_2,

        "samoan"               : RefPanel.MICHIGAN_SAMOAN,
    },
    Environment.MCPS: {
        "hapmap"  : RefPanel.MCPS_HAPMAP_2,
        "hapmap2" : RefPanel.MCPS_HAPMAP_2,
        "mcps"    : RefPanel.MCPS_MCPS,
    }
}


def late_check_refpanel(parser: argparse.ArgumentParser, env: Environment, refpanel: str) -> RefPanel:
    """
    Validates the `refpanel` argument based on the passed `env`; used for late argument parsing.

    If the provided `refpanel` argument is a recognized alias for `hapmap-2`, `r3`, or `r3-prod`,
    returns the corresponding `RefPanel` value. The comparison ignores case, spacing, dashes,
    and underscores.

    Otherwise, uses the `parser` to raise a "bad formatting" error and exit.
    """
    assert env in REFPANEL_LOOKUP.keys()

    processed = refpanel.strip().lower().replace("-", "").replace("_", "").replace(".", "")

    if processed in REFPANEL_LOOKUP[env]:
        return REFPANEL_LOOKUP[env][processed]
    else:
        parser.error(f"-r/--refpanel must be a known environment-specific panel. In environment '{env}', found unrecognized value: {refpanel}")


def json_default(value):
    if is_dataclass(value):
        return asdict(value)
    elif isinstance(value, datetime):
        return value.isoformat(sep=" ")
    elif isinstance(value, Enum):
        return value.name
    raise Exception(f"Value of type '{type(value)}' could not be parsed: {value}")
