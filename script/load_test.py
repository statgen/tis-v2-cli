#!/bin/env python3


import os
import time
import random
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from multiprocessing import Process
from dataclasses import dataclass

from requests.exceptions import RequestException
from pretty_cli import PrettyCli

from local.api import TisV2Api
from local.request_schema import JobParams, RefPanel, Build, Phasing, Mode
from local.util import check_file, check_timedelta
from local.ansi_colors import FG_SELECTION, RESET


@dataclass
class ProgramArgs:
    min_delay   : timedelta
    max_delay   : timedelta
    submissions : int
    token_files : list[Path]
    vcf_files   : list[Path]


@dataclass
class ChildArgs:
    min_delay   : timedelta
    max_delay   : timedelta
    submissions : int
    token_file  : Path
    vcf_files   : list[Path]


def parse_arguments() -> ProgramArgs:
    parser = argparse.ArgumentParser(description="Load test the TOPMed Imputation Server dev env")

    parser.add_argument("--min-delay", help="Time expression indicating the minimum wait before next submission for a given account", type=check_timedelta, required=True)
    parser.add_argument("--max-delay", help="Time expression indicating the maximum wait before next submission for a given account", type=check_timedelta, required=True)
    parser.add_argument("--submissions", help="Number of submissions to be attempted per identity.", type=int, required=True)
    parser.add_argument("--token-file", help="Path to a text file containing a valid auth token. Repeat for multiple identities.", type=check_file, required=True, action="append")
    parser.add_argument("--vcf-file", help="VCF file to upload for testing. Repeat for a multi-file upload.", type=check_file, required=True, action="append")

    args = parser.parse_args()

    assert len(args.token_file) > 0
    assert len(args.vcf_file  ) > 0

    return ProgramArgs(
        min_delay   = args.min_delay  ,
        max_delay   = args.max_delay  ,
        submissions = args.submissions,
        token_files = args.token_file ,
        vcf_files   = args.vcf_file   ,
    )


def call_api(args: ChildArgs) -> None:
    cli = PrettyCli()
    color = FG_SELECTION[random.randint(0, len(FG_SELECTION)-1)]

    def log(msg: str) -> None:
        msg = f"{color}[{args.token_file}]{RESET} {msg}"
        cli.print(msg)

    log("New identity starting")

    api = TisV2Api(env="dev", cli=cli, token_file=args.token_file)

    t = args.min_delay.total_seconds()
    T = args.max_delay.total_seconds()

    rng = random.Random()
    seed = os.urandom(128)
    rng.seed(seed)

    log(f"Random seed: {seed.hex()}")

    job_params = JobParams(
        refpanel   = RefPanel.DEV_TOPMED_R3_PROD,
        files      = args.vcf_files,
        build      = Build.HG38,
        r2_filter  = 0.0,
        phasing    = Phasing.EAGLE,
        population = "all",
        mode       = Mode.IMPUTATION,
    )

    for _ in range(args.submissions):
        sleep_seconds = rng.uniform(t, T)

        log(f"Sleeping {sleep_seconds:.02f} seconds.")
        time.sleep(sleep_seconds)

        start = datetime.now()
        log("Submitting job")
        try:
            api.submit_job(job_params)
            end = datetime.now()
            log(f"Submission took {(end - start).total_seconds()} seconds.")
        except RequestException:
            log(f"Submission failed.")
            continue



def main() -> None:
    program_args = parse_arguments()

    cli = PrettyCli()
    cli.main_title("LOAD TEST")

    cli.section("Program Args")
    cli.print(program_args)

    children: list[Process] = []

    try:

        for token_file in program_args.token_files:
            child_args = ChildArgs(
                min_delay   = program_args.min_delay  ,
                max_delay   = program_args.max_delay  ,
                submissions = program_args.submissions,
                token_file  = token_file              ,
                vcf_files   = program_args.vcf_files  ,
            )

            p = Process(target=call_api, args=(child_args,))
            p.start()

            children.append(p)

        for p in children:
            p.join()

    except KeyboardInterrupt as e:
        for p in children:
            p.kill()
        raise e


if __name__ == "__main__":
    main()
