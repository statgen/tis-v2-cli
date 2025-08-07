#!/bin/env python3


import argparse
import time
from enum import StrEnum
from dataclasses import dataclass

from pretty_cli import PrettyCli

from local.api import TisV2Api
from local.request_schema import JobParams, RefPanel, Build, Phasing, Mode
from local.util import display, check_file, late_check_refpanel


class Command(StrEnum):
    LIST_JOBS  = "list-jobs"
    GET_JOB    = "get-job"
    SUBMIT_JOB = "submit-job"


@dataclass
class GlobalArgs:
    env            : str
    debug          : bool
    repeat         : int
    delay          : float
    minimal_output : bool
    command        : Command


@dataclass
class ListJobsArgs:
    global_args : GlobalArgs


@dataclass
class GetJobArgs:
    global_args : GlobalArgs
    job_id      : str


@dataclass
class SubmitJobArgs:
    global_args : GlobalArgs
    job_params  : JobParams


Args = ListJobsArgs | GetJobArgs | SubmitJobArgs


def parse_arguments() -> Args:
    parser = argparse.ArgumentParser(description="Query the TOPMed Imputation Server API")

    parser.add_argument("env", choices=["dev", "prod"], help="Target environment ('dev' or 'prod').")
    parser.add_argument("--debug", action="store_true", help="Activates additional debug printing.")
    parser.add_argument("--repeat", help="Number of times to repeat the requested call.", type=int, default=1)
    parser.add_argument("--delay", help="Time in seconds to wait before performing the call.", type=float, default=0.0)
    parser.add_argument("--minimal-output", help="Only print the request-response header, supressing normal output.", action="store_true")

    subparsers = parser.add_subparsers(title="Commands", dest="command")

    list_jobs = subparsers.add_parser(Command.LIST_JOBS, help="List all of the user's jobs.")

    get_job = subparsers.add_parser(Command.GET_JOB, help="Get one of the user's jobs, by ID.")
    get_job.add_argument("job_id", help="ID of the job to retrieve")

    submit_job = subparsers.add_parser(Command.SUBMIT_JOB, help="Submit a job for processing.")
    submit_job.add_argument("-n", "--name", help="Optional name for this job (will be assigned a unique ID regardless).")
    submit_job.add_argument("-r", "--refpanel", help="Reference panel used for imputation.", type=str, required=True)
    submit_job.add_argument("-b", "--build", help="Data format (HG19 vs. HG38)", type=Build, required=True)
    submit_job.add_argument("-R", "--r2-filter", help="rsq filter. Set to 0 or leave blank for none", type=float, default=0.0)
    submit_job.add_argument("-p", "--phasing", help="Phasing engine to use.", type=Phasing, default=Phasing.EAGLE)
    submit_job.add_argument("-P", "--population", help="Reference population used for the allele frequency check", type=str, default=None)
    submit_job.add_argument("-m", "--mode", help="Run QC only, or do QC + Imputation.", type=Mode, default=Mode.IMPUTATION)
    submit_job.add_argument("-f", "--file", help="VCF file to upload for testing.", type=check_file, required=True)

    args = parser.parse_args()

    global_args = GlobalArgs(
        env            = args.env,
        debug          = args.debug,
        repeat         = args.repeat,
        delay          = args.delay,
        minimal_output = args.minimal_output,
        command        = Command(args.command),
    )

    if global_args.command == Command.LIST_JOBS:
        return ListJobsArgs(global_args=global_args)

    elif global_args.command == Command.GET_JOB:
        return GetJobArgs(global_args=global_args, job_id=args.job_id)

    elif global_args.command == Command.SUBMIT_JOB:
        refpanel = late_check_refpanel(submit_job, global_args.env, args.refpanel)

        job_params = JobParams(
            job_name   = args.name,
            refpanel   = refpanel,
            build      = args.build,
            r2_filter  = args.r2_filter,
            phasing    = args.phasing,
            population = args.population,
            mode       = args.mode,
            file       = args.file,
        )
        return SubmitJobArgs(global_args=global_args, job_params=job_params)

    assert False, "UNREACHABLE"


def main() -> None:
    cli = PrettyCli()
    args = parse_arguments()

    api = TisV2Api(
        env = "dev",
        cli = cli  ,
        print_request_headers  = args.global_args.debug,
        print_request_body     = args.global_args.debug,
        print_response_headers = args.global_args.debug,
        print_response_body    = args.global_args.debug,
    )

    if args.global_args.repeat < 1:
        return

    for _ in range(args.global_args.repeat):
        if args.global_args.delay > 0:
            time.sleep(args.global_args.delay)

        match args.global_args.command:
            case Command.LIST_JOBS:
                assert isinstance(args, ListJobsArgs)
                jobs = api.list_jobs()

                if not args.global_args.minimal_output:
                    for job in jobs:
                        display(cli, job)

            case Command.GET_JOB:
                assert isinstance(args, GetJobArgs)
                job = api.get_job(args.job_id)
                if not args.global_args.minimal_output:
                    display(cli, job)

            case Command.SUBMIT_JOB:
                assert isinstance(args, SubmitJobArgs)
                response = api.submit_job(args.job_params)
                if not args.global_args.minimal_output:
                    cli.print(response)


if __name__ == "__main__":
    main()
