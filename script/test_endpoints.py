#!/bin/env python3


from pathlib import Path
from dataclasses import asdict

from pretty_cli import PrettyCli

from local.api import TisV2Api
from local.request_schema import JobParams, RefPanel, Build, Phasing, Mode


TEST_FILE = Path("data/chr20.R50.merged.1.330k.recode.unphased.small.vcf.gz")
assert TEST_FILE.is_file()


def get_vcf():
    file_handle = open(TEST_FILE, "rb")
    return file_handle


def display(cli: PrettyCli, obj) -> None:
    out = asdict(obj)

    def _flatten(d: dict) -> dict:
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
        refpanel   = RefPanel.DEV_HAPMAP_2,
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
