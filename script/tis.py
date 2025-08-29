#!/bin/env python3


import argparse
import time
from pathlib import Path
from enum import StrEnum
from dataclasses import dataclass

from pretty_cli import PrettyCli

from local.api import TisV2Api
from local.request_schema import JobParams, Build, Phasing, Mode
from local.util import display, check_file, late_check_refpanel


class Command(StrEnum):
    LIST_JOBS   = "list-jobs"
    GET_JOB     = "get-job"
    SUBMIT_JOB  = "submit-job"
    RESTART_JOB = "restart-job"


@dataclass
class Args:
    env            : str
    debug          : bool
    repeat         : int
    delay          : float
    minimal_output : bool
    token_file     : Path | None
    command        : Command

    def run_command(self, api: TisV2Api) -> None:
        raise NotImplementedError()


@dataclass
class ListJobsArgs(Args):
    def run_command(self, api: TisV2Api) -> None:
        jobs = api.list_jobs()

        if not self.minimal_output:
            for job in jobs:
                display(api.cli, job)


@dataclass
class GetJobArgs(Args):
    job_id: str

    def run_command(self, api: TisV2Api) -> None:
        job = api.get_job(self.job_id)
        if not self.minimal_output:
            display(api.cli, job)


@dataclass
class RestartJobArgs(Args):
    job_id: str

    def run_command(self, api: TisV2Api) -> None:
        response = api.restart_job(self.job_id)
        if not self.minimal_output:
            display(api.cli, response)


@dataclass
class SubmitJobArgs(Args):
    job_params: JobParams

    def run_command(self, api: TisV2Api) -> None:
        response = api.submit_job(self.job_params)
        if not self.minimal_output:
            display(api.cli, response)


def parse_arguments() -> Args:
    parser = argparse.ArgumentParser(description="Query the TOPMed Imputation Server API")

    parser.add_argument("env", choices=["dev", "prod"], help="Target environment ('dev' or 'prod').")
    parser.add_argument("--debug", action="store_true", help="Activates additional debug printing.")
    parser.add_argument("--repeat", help="Number of times to repeat the requested call.", type=int, default=1)
    parser.add_argument("--delay", help="Time in seconds to wait before performing the call.", type=float, default=0.0)
    parser.add_argument("--minimal-output", help="Only print the request-response header, supressing normal output.", action="store_true")
    parser.add_argument("--token-file", help="Path to a text file containing the authentication token.", type=check_file, default=None)

    subparsers = parser.add_subparsers(title="Commands", dest="command")

    list_jobs = subparsers.add_parser(Command.LIST_JOBS, help="List all of the user's jobs.")

    get_job = subparsers.add_parser(Command.GET_JOB, help="Get one of the user's jobs, by ID.")
    get_job.add_argument("job_id", help="ID of the job to retrieve")

    restart_job = subparsers.add_parser(Command.RESTART_JOB, help="Restart one of the user's jobs, by ID.")
    restart_job.add_argument("job_id", help="ID of the job to retry")

    submit_job = subparsers.add_parser(Command.SUBMIT_JOB, help="Submit a job for processing.")
    submit_job.add_argument("-n", "--name", help="Optional name for this job (will be assigned a unique ID regardless).")
    submit_job.add_argument("-r", "--refpanel", help="Reference panel used for imputation.", type=str, required=True)
    submit_job.add_argument("-b", "--build", help="Data format (HG19 vs. HG38)", type=Build, required=True)
    submit_job.add_argument("-R", "--r2-filter", help="rsq filter. Set to 0 or leave blank for none", type=float, default=0.0)
    submit_job.add_argument("-p", "--phasing", help="Phasing engine to use.", type=Phasing, default=Phasing.EAGLE)
    submit_job.add_argument("-P", "--population", help="Reference population used for the allele frequency check", type=str, default=None)
    submit_job.add_argument("-m", "--mode", help="Run QC only, or do QC + Imputation.", type=Mode, default=Mode.IMPUTATION)
    submit_job.add_argument("-f", "--file", help="VCF file to upload for testing. Repeat for a multi-file upload.", type=check_file, required=True, action="append")

    args = parser.parse_args()
    command = Command(args.command)

    global_args = {
        "env"            : args.env,
        "debug"          : args.debug,
        "repeat"         : args.repeat,
        "delay"          : args.delay,
        "minimal_output" : args.minimal_output,
        "token_file"     : args.token_file,
        "command"        : command,
    }

    match command:
        case Command.LIST_JOBS:
            return ListJobsArgs(**global_args)
        case Command.GET_JOB:
            return GetJobArgs(**global_args, job_id=args.job_id)
        case Command.RESTART_JOB:
            return RestartJobArgs(**global_args, job_id=args.job_id)
        case Command.SUBMIT_JOB:
            refpanel = late_check_refpanel(submit_job, args.env, args.refpanel)

            job_params = JobParams(
                job_name   = args.name,
                refpanel   = refpanel,
                build      = args.build,
                r2_filter  = args.r2_filter,
                phasing    = args.phasing,
                population = args.population,
                mode       = args.mode,
                files      = args.file,
            )
            return SubmitJobArgs(**global_args, job_params=job_params)

    assert False, "UNREACHABLE"


def main() -> None:
    cli = PrettyCli()
    args = parse_arguments()

    api = TisV2Api(
        env = "dev",
        cli = cli  ,
        print_request_headers  = args.debug,
        print_request_body     = args.debug,
        print_response_headers = args.debug,
        print_response_body    = args.debug,
        token_file             = args.token_file,
    )

    if args.repeat < 1:
        return

    for _ in range(args.repeat):
        if args.delay > 0:
            time.sleep(args.delay)

        args.run_command(api)


if __name__ == "__main__":
    main()
