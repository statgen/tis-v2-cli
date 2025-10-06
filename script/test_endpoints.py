#!/bin/env python3


from pathlib import Path
from pretty_cli import PrettyCli

from local.api import TisV2Api
from local.request_schema import JobParams, RefPanel, Build, Phasing, Mode
from local.util import display


TEST_FILE = Path("data/chr20.R50.merged.1.330k.recode.unphased.small.vcf.gz")
assert TEST_FILE.is_file()


def get_vcf():
    file_handle = open(TEST_FILE, "rb")
    return file_handle


def main() -> None:
    cli = PrettyCli()
    cli.main_title("TIS V2 API")

    api = TisV2Api(
        env = "dev",
        cli = cli  ,
        # print_request_headers  = True,
        # print_request_body     = True,
        # print_response_headers = True,
        # print_response_body    = True,
    )

    # ================================================================ #
    cli.chapter("List Jobs")

    jobs = api.list_jobs()
    for job in jobs:
        display(cli, job)

    # ================================================================ #
    cli.chapter("Get Job")

    latest_job = api.get_job(jobs[0].id)
    display(cli, latest_job)

    # ================================================================ #
    cli.chapter("Submit Job")

    params = JobParams(
        job_name   = "api-test",
        refpanel   = RefPanel.TOPMED_DEV_HAPMAP_2,
        file       = TEST_FILE,
        build      = Build.HG19,
        r2_filter  = 0.0,
        phasing    = Phasing.EAGLE,
        population = "EUR",
        mode       = Mode.IMPUTATION,
    )

    response = api.submit_job(params)
    cli.print(response)


if __name__ == "__main__":
    main()
