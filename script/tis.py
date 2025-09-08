#!/bin/env python3


import argparse
import time
from datetime import datetime
from pathlib import Path
from enum import StrEnum
from dataclasses import dataclass

from pretty_cli import PrettyCli

from local.api import TisV2Api
from local.request_schema import JobParams, Build, Phasing, Mode, AdminListJobsState
from local.response_schema import JobInfo
from local.util import display, check_file, late_check_refpanel, check_datetime


class Command(StrEnum):
    LIST_JOBS   = "list-jobs"
    GET_JOB     = "get-job"
    SUBMIT_JOB  = "submit-job"
    CANCEL_JOB  = "cancel-job"
    RESTART_JOB = "restart-job"
    ADMIN       = "admin"


class AdminCommand(StrEnum):
    LIST_JOBS = "list-jobs"
    KILL_ALL  = "kill-all"


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
    start_time : datetime | None
    end_time   : datetime | None

    def run_command(self, api: TisV2Api) -> None:
        jobs = api.list_jobs()
        jobs = self.filter_jobs(jobs)

        if not self.minimal_output:
            for job in jobs:
                display(api.cli, job)

    def filter_jobs(self, jobs: list[JobInfo]) -> list[JobInfo]:
        filtered = []

        for j in jobs:
            if self.start_time:
                if j.end_time < self.start_time:
                    continue
            if self.end_time:
                if j.start_time > self.end_time:
                    continue
            filtered.append(j)

        return filtered


@dataclass
class GetJobArgs(Args):
    job_id: str

    def run_command(self, api: TisV2Api) -> None:
        job = api.get_job(self.job_id)
        if not self.minimal_output:
            display(api.cli, job)


@dataclass
class CancelJobArgs(Args):
    job_id: str

    def run_command(self, api: TisV2Api) -> None:
        job = api.cancel_job(self.job_id)
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


@dataclass
class AdminArgs(Args):
    admin_command: AdminCommand


@dataclass
class AdminListJobs(AdminArgs):
    states: list[AdminListJobsState]

    def run_command(self, api: TisV2Api) -> None:
        jobs = api.admin_list_jobs(self.states)

        if not self.minimal_output:
            for job in jobs:
                display(api.cli, job)


@dataclass
class AdminKillAll(AdminArgs):
    def run_command(self, api: TisV2Api) -> None:
        response = api.admin_kill_all()

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

    subparsers = parser.add_subparsers(title="Commands", dest="command", required=True)

    list_jobs = subparsers.add_parser(Command.LIST_JOBS, help="List all of the user's jobs.")
    list_jobs.add_argument("--start-time", help="Only display results for jobs that were running after this time.", type=check_datetime, default=None)
    list_jobs.add_argument("--end-time", help="Only display results for jobs that were running before this time.", type=check_datetime, default=None)

    get_job = subparsers.add_parser(Command.GET_JOB, help="Get one job visible by the user, by ID.")
    get_job.add_argument("job_id", help="ID of the job to retrieve")

    cancel_job = subparsers.add_parser(Command.CANCEL_JOB, help="Cancel one job visible by the user, by ID.")
    cancel_job.add_argument("job_id", help="ID of the job to cancel")

    restart_job = subparsers.add_parser(Command.RESTART_JOB, help="Restart one job visible by the user, by ID.")
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

    admin = subparsers.add_parser(Command.ADMIN, help="Issue admin commands")
    admin_parsers = admin.add_subparsers(title="Admin Commands", dest="admin_command", required=True)

    admin_list_jobs = admin_parsers.add_parser(AdminCommand.LIST_JOBS, help="List jobs from all users.")
    admin_list_jobs.add_argument("--state", help="Job state filter.", choices=[ state for state in AdminListJobsState ], required=True, action="append")

    admin_kill_all = admin_parsers.add_parser(AdminCommand.KILL_ALL, help="Cancel all running or waiting jobs.")

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
            return ListJobsArgs(**global_args, start_time=args.start_time, end_time=args.end_time)
        case Command.GET_JOB:
            return GetJobArgs(**global_args, job_id=args.job_id)
        case Command.CANCEL_JOB:
            return CancelJobArgs(**global_args, job_id=args.job_id)
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

        case Command.ADMIN:
            admin_command = AdminCommand(args.admin_command)
            global_args["admin_command"] = admin_command

            match admin_command:
                case AdminCommand.LIST_JOBS:
                    return AdminListJobs(**global_args, states=args.state)
                case AdminCommand.KILL_ALL:
                    return AdminKillAll(**global_args)

            assert False, f"Unrecognized admin command: {admin_command}"

    assert False, f"Unrecognized command: {command}"


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
