"""
Provides everything needed to run commands from the CLI.
"""


import argparse

from pretty_cli import PrettyCli

from . import base, version, job, admin, server


def parse_arguments() -> base.Args:
    parser = argparse.ArgumentParser(description="Query the TOPMed Imputation Server API")

    base.register_base_args(parser)

    subparsers = parser.add_subparsers(title="Commands", dest="command", required=True)

    version.register_version_parser(subparsers)
    server.register_server_parser(subparsers)
    job.register_job_parser(subparsers)
    admin.register_admin_parser(subparsers)

    raw_args = parser.parse_args()

    command = base.Command(raw_args.command)

    global_args = base.Args(
        debug        = raw_args.debug,
        output_style = raw_args.output_style,
        token_file   = raw_args.token_file,
        command      = command,
    )

    match command:
        case base.Command.VERSION:
            return version.parse_version_command(raw_args, global_args)
        case base.Command.SERVER:
            return server.parse_server_command(raw_args, global_args)
        case base.Command.JOB:
            return job.parse_job_command(raw_args, global_args)
        case base.Command.ADMIN:
            return admin.parse_admin_command(raw_args, global_args)
        case _:
            raise ValueError(f"Unrecognized command: {command}")

    assert False, f"Unrecognized command: {command}"


def run_cli() -> None:
    cli = PrettyCli()
    args = parse_arguments()
    args.run_command(cli)
