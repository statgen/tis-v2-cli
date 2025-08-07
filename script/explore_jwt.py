#!/bin/env python3


import base64
import json
import argparse
from pathlib import Path

from typing import Any
from dataclasses import dataclass

from pretty_cli import PrettyCli


def check_file(arg_value: str) -> Path:
    path = Path(arg_value)

    if not path.is_file():
        raise argparse.ArgumentTypeError(f"File not found: {arg_value}")

    return path


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


def parse_args() -> str:
    parser = argparse.ArgumentParser(description="Decode a JWT token and display its parts.")

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-f", "--file", type=check_file, help="Path to the token file.")
    group.add_argument("-t", "--token", type=str, help="The token string.")

    args = parser.parse_args()

    if args.file is not None:
        assert args.token is None

        with open(args.file, "r") as file_handle:
            token = file_handle.read().strip()

        return token
    else:
        assert args.token is not None
        return args.token


def main() -> None:
    token = parse_args()
    decode(token)


if __name__ == "__main__":
    main()
