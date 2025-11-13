"""
Provides user-level commands for interacting with the user's own jobs.
"""


from datetime import datetime
from pathlib import Path
from enum import StrEnum
from dataclasses import dataclass, asdict
from typing import Any

from local.server import Server
from local.api import TisV2Api
from local.request_schema import JobParams, Build, Phasing, Mode
from local.util import check_file, check_datetime

from . import base


class JobCommand(StrEnum):
    LIST     = "list"
    GET      = "get"
    SUBMIT   = "submit"
    CANCEL   = "cancel"
    RESTART  = "restart"
    DOWNLOAD = "download"


@dataclass
class JobArgs(base.ApiArgs):
    job_command: JobCommand


@dataclass
class JobList(JobArgs):
    start_time : datetime | None
    end_time   : datetime | None

    def run_subcommand(self, api: TisV2Api) -> None:
        jobs = api.list_jobs()
        jobs = base.filter_jobs(jobs, self.start_time, self.end_time)
        self.output(api.cli, jobs)


@dataclass
class JobGet(JobArgs):
    job_id: str

    def run_subcommand(self, api: TisV2Api) -> None:
        job = api.get_job(self.job_id)
        self.output(api.cli, job)


@dataclass
class JobCancel(JobArgs):
    job_id: str

    def run_subcommand(self, api: TisV2Api) -> None:
        job = api.cancel_job(self.job_id)
        self.output(api.cli, job)


@dataclass
class JobRestart(JobArgs):
    job_id: str

    def run_subcommand(self, api: TisV2Api) -> None:
        response = api.restart_job(self.job_id)
        self.output(api.cli, response)


@dataclass
class JobSubmit(JobArgs):
    job_params: JobParams

    def run_subcommand(self, api: TisV2Api) -> None:
        response = api.submit_job(self.job_params)
        self.output(api.cli, response)


@dataclass
class JobDownload(JobArgs):
    download_dir: Path
    job_id: str

    def run_subcommand(self, api: TisV2Api) -> None:
        response = api.download(self.download_dir, self.job_id)
        self.output(api.cli, response)


def register_job_parser(subparsers: base.Subparser) -> None:
    job = subparsers.add_parser(base.Command.JOB, help="Interact with your own jobs.")
    job_parsers = job.add_subparsers(title="Job Commands", dest="job_command", required=True)

    list_jobs = job_parsers.add_parser(JobCommand.LIST, help="List all your jobs.")
    base.register_server_variable(list_jobs)
    list_jobs.add_argument("--start-time", help="Only display results for jobs that were running after this time." , type=check_datetime, default=None)
    list_jobs.add_argument("--end-time"  , help="Only display results for jobs that were running before this time.", type=check_datetime, default=None)

    get_job = job_parsers.add_parser(JobCommand.GET, help="Get one job visible by the user, by ID.")
    base.register_server_variable(get_job)
    get_job.add_argument("job_id", help="ID of the job to retrieve")

    cancel_job = job_parsers.add_parser(JobCommand.CANCEL, help="Cancel one job visible by the user, by ID.")
    base.register_server_variable(cancel_job)
    cancel_job.add_argument("job_id", help="ID of the job to cancel")

    restart_job = job_parsers.add_parser(JobCommand.RESTART, help="Restart one job visible by the user, by ID.")
    base.register_server_variable(restart_job)
    restart_job.add_argument("job_id", help="ID of the job to retry")

    submit_job = job_parsers.add_parser(JobCommand.SUBMIT, help="Submit a job for processing.")
    base.register_server_variable(submit_job)
    submit_job.add_argument("-f", "--file"          , help="VCF file to upload for testing. Repeat for a multi-file upload."      , type=check_file, required=True, action="append")
    submit_job.add_argument("-r", "--refpanel"      , help="Reference panel used for imputation."                                 , type=str       , required=True)
    submit_job.add_argument("-b", "--build"         , help="Data format (HG19 vs. HG38)."                                         , type=Build     , default=None)
    submit_job.add_argument("-n", "--name"          , help="Optional name for this job (will be assigned a unique ID regardless).", type=str       , default=None)
    submit_job.add_argument("-R", "--r2-filter"     , help="rsq filter.                                 "                         , type=float     , default=None)
    submit_job.add_argument("-p", "--phasing"       , help="Phasing engine to use."                                               , type=Phasing   , default=None)
    submit_job.add_argument("-P", "--population"    , help="Reference population used for the allele frequency check."            , type=str       , default="off")
    submit_job.add_argument("-m", "--mode"          , help="Run QC only, or do QC + Imputation."                                  , type=Mode      , default=None)
    submit_job.add_argument("-e", "--aes-encryption", help="Use AES 256 encryption instead of the default."                       , type=bool      , default=None)
    submit_job.add_argument("-M", "--meta-file"     , help="Generate a meta-imputation file."                                     , type=bool      , default=None)
    submit_job.add_argument(      "--password"      , help="Enforce this password for encryption instead of the random default."  , type=str       , default=None)

    download_job = job_parsers.add_parser(JobCommand.DOWNLOAD, help="Download all files for the given job.")
    base.register_server_variable(download_job)
    download_job.add_argument("--download-dir", help="Directory used for file downloads. If the job contains outputs, a sub-dir named <job-id>/ will be created, and used to store all outputs.", type=Path, default=Path(".").resolve())
    download_job.add_argument("job_id", help="ID of the job to download.")


def parse_job_command(raw_args: Any, global_args: base.Args) -> JobArgs:
    job_command = JobCommand(raw_args.job_command)
    server: Server = raw_args.server

    dict_args = asdict(global_args)
    dict_args["job_command"] = job_command
    dict_args["server"] = server

    match job_command:
        case JobCommand.LIST:
            return JobList(**dict_args, start_time=raw_args.start_time, end_time=raw_args.end_time)
        case JobCommand.GET:
            return JobGet(**dict_args, job_id=raw_args.job_id)
        case JobCommand.CANCEL:
            return JobCancel(**dict_args, job_id=raw_args.job_id)
        case JobCommand.RESTART:
            return JobRestart(**dict_args, job_id=raw_args.job_id)
        case JobCommand.SUBMIT:
            refpanel = server.get_refpanel(raw_args.refpanel)
            population = refpanel.get_population(raw_args.population)

            job_params = JobParams(
                refpanel       = refpanel,
                population     = population.id,
                files          = raw_args.file,
                job_name       = raw_args.name,
                build          = raw_args.build,
                r2_filter      = raw_args.r2_filter,
                phasing        = raw_args.phasing,
                mode           = raw_args.mode,
                aes_encryption = raw_args.aes_encryption,
                meta_file      = raw_args.meta_file,
                password       = raw_args.password,
            )
            return JobSubmit(**dict_args, job_params=job_params)
        case JobCommand.DOWNLOAD:
            return JobDownload(**dict_args, job_id=raw_args.job_id, download_dir=raw_args.download_dir)

    assert False, f"Unrecognized job command: {job_command}"
