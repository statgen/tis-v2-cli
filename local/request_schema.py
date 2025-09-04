"""
Provides typed objects for request payloads.
"""

from os import PathLike
from enum import StrEnum
from dataclasses import dataclass


# ================================ SUBMIT JOB ================================ #


class RefPanel(StrEnum):
    """Valid reference panel strings for dev and prod (see prefix)."""

    # dev
    DEV_HAPMAP_2       = "apps@hapmap-2@2.0.0"
    DEV_TOPMED_R3_DEV  = "apps@topmed-r3@1.0.0"
    DEV_TOPMED_R3_PROD = "apps@topmed-r3-prod@1.0.0"

    # prod
    PROD_TOPMED_R3     = "apps@topmed-r3@1.0.0"


class Build(StrEnum):
    """Data format used in the VCF file (HG-19 vs. HG-38)."""

    HG19 = "hg19"
    HG38 = "hg38"


class Phasing(StrEnum):
    """Which engine should be used for phasing, if any."""

    EAGLE      = "eagle"
    BEAGLE     = "beagle"
    NO_PHASING = "no_phasing"


class Mode(StrEnum):
    """Processing mode: full imputation vs. QC-only."""
    IMPUTATION = "imputation"
    QC_ONLY    = "qc_only"


@dataclass
class JobParams:
    """
    Parameters passed to `api.submit_job(params)`.
    Equivalent to the job submission form at `/index.html#!run/imputationserver2@<version>`

    * `params.get_params()` returns a list of form submission headers, in the format
      expected by the `files` parameter in `requests.post()`.
    """
    refpanel   : RefPanel
    files      : list[PathLike]
    build      : Build
    r2_filter  : float
    phasing    : Phasing
    population : str
    mode       : Mode
    job_name   : str | None = None

    def get_params(self) -> list[tuple[str, tuple]]:
        params = [
            # header        file  value
            ("job-name"  , (None, self.job_name      )),
            ("refpanel"  , (None, str(self.refpanel) )),
            ("build"     , (None, str(self.build)    )),
            ("r2Filter"  , (None, str(self.r2_filter))),
            ("phasing"   , (None, str(self.phasing)  )),
            ("population", (None, self.population    )),
            ("mode"      , (None, str(self.mode)     )),
            ("check1"    , (None, "accepted"         )),
            ("check2"    , (None, "accepted"         )),
        ]

        #            header    name       data              MIME-type
        params += [ ("files", (str(file), open(file, "rb"), "application/octet-stream")) for file in self.files ]

        return params


# ================================ OTHER ================================ #


class AdminListJobsState(StrEnum):
    """Job status filter options accepted by the `admin/jobs` endpoint for job listing."""

    LONG_TIME_QUEUE = "running-ltq"
    # SHORT_TIME_QUEUE = "running-stq" # Looks deprecated
    CURRENT = "current"
    RETIRED = "retired"
