#!/bin/env python3


import base64
import json
import argparse
from pathlib import Path

from typing import Any
from dataclasses import dataclass

from pretty_cli import PrettyCli


def decode_part(part: str) -> Any:
    """
    Receives a part of a JWT token (JSON encoded as a URL64 string), and returns the parsed JSON.
    """

    padding = "=" * (4 - (len(part) % 4))
    padded_part = part + padding

    decoded = base64.urlsafe_b64decode(padded_part)
    as_json = json.loads(decoded)

    return as_json


def decode(token: str) -> None:
    """
    Decodes and pretty-prints the parts of a JWT token.
    """

    cli = PrettyCli()

    # JWT tokens are composed of three parts, encoded as Base64URL and separated by dots:
    #   * A header (JSON dict) indicating the algorithm used for the signature (and in theory it should also say `"typ": "JWT"`)
    #   * A body (JSON dict) with the actual information (there is a specification for this as well, but it's beyond this script's scope).
    #   * A signature proving that the payload was made by the origin server.

    parts = token.split(".")
    assert(len(parts) == 3), f"Expected three URL64-encoded parts separated by dots; found {len(parts)} parts."
    [ header_url64, body_url64, signature_url64 ] = parts

    cli.section("Header")
    header_json = decode_part(header_url64)
    cli.print(header_json)

    cli.section("Body")
    body_json = decode_part(body_url64)
    cli.print(body_json)

    cli.section("Signature")
    cli.print(signature_url64)


@dataclass
class Arguments:
    file  : Path | None
    token : str  | None


def parse_args() -> Arguments:
    parser = argparse.ArgumentParser(description="Decode a JWT token and display its parts.")

    parser.add_argument("-f", "--file", type=Path, help="Path to the token file.")
    parser.add_argument("-t", "--token", type=str, help="The token string.")

    args = parser.parse_args()
    file: Path | None = args.file
    token: str | None = args.token

    if file is not None:
        assert token is None, "Only one of --file or --token should be provided; found both."
        assert file.is_file(), f"--file should receive an existing file; found: {file}"
        return Arguments(file=file, token=None)
    elif token is not None:
        assert len(token) > 0, "--token should receive a non-empty string."
        return Arguments(file=None, token=token)
    else:
        parser.print_help()
        exit(1)


def main() -> None:
    args = parse_args()

    if args.file is not None:
        with open(args.file, "r") as handle:
            token = handle.read().strip()
    else:
        assert args.token is not None
        token = args.token.strip()

    decode(token)


if __name__ == "__main__":
    main()
