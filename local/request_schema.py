"""
Provides typed objects for request payloads.
"""

from os import PathLike
from enum import StrEnum
from dataclasses import dataclass


# ================================ SUBMIT JOB ================================ #


class RefPanel(StrEnum):
    """Valid reference panel strings for dev and prod (see prefix)."""

    # TOPMed dev
    TOPMED_DEV_HAPMAP_2       = "hapmap-2"
    TOPMED_DEV_TOPMED_R3_DEV  = "topmed-r3"
    TOPMED_DEV_TOPMED_R3_PROD = "topmed-r3-prod"

    # TOPMed prod
    TOPMED_PROD_TOPMED_R3 = "topmed-r3"

    # Michigan
    MICHIGAN_1KG_P1_V3  = "1000g-phase-1"
    MICHIGAN_1KG_P3     = "1000g-phase3-low"
    MICHIGAN_1KG_P3_30X = "1000g-phase3-deep"
    MICHIGAN_1KG_P3_V5  = "1000g-phase-3-v5"
    MICHIGAN_CAAPA      = "caapa"
    MICHIGAN_GASP       = "genome-asia-panel"
    MICHIGAN_HRC_R11    = "hrc-r1.1"
    MICHIGAN_HAPMAP_2   = "hapmap-2"
    MICHIGAN_SAMOAN     = "samoan"

    # mcps
    MCPS_HAPMAP_2 = "hapmap-2"
    MCPS_MCPS     = "mcps"


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
