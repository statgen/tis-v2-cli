"""
Provides typed objects for request payloads.
"""

from os import PathLike
from enum import StrEnum
from dataclasses import dataclass

from local.server import RefPanel


# ================================ SUBMIT JOB ================================ #


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
    refpanel       : RefPanel
    population     : str
    files          : list[PathLike]
    job_name       : str     | None = None
    build          : Build   | None = None
    r2_filter      : float   | None = None
    phasing        : Phasing | None = None
    mode           : Mode    | None = None
    aes_encryption : bool    | None = None
    meta_file      : bool    | None = None
    password       : str     | None = None

    def get_params(self) -> list[tuple[str, tuple]]:
        """
        Returns a list of form fields in the format expected by the `files` parameter in `requests.post()`.

        * Skips `None` fields.
        * Opens handles for all files in `self.files`. The file contents will be uploaded as octet streams.
        """

        assert len(self.population) > 0
        assert len(self.files) > 0

        form_fields = {
            "refpanel"      : self.refpanel.id,
            "population"    : self.population,
            "job-name"      : self.job_name,
            "build"         : self.build,
            "r2Filter"      : self.r2_filter,
            "phasing"       : self.phasing,
            "mode"          : self.mode,
            "aesEncryption" : self.aes_encryption,
            "meta"          : self.meta_file,
            "password"      : self.password,
        }

        params = []

        for (header, value) in form_fields.items():
            if value is None:
                continue

            value = str(value).strip()

            if len(value) == 0:
                continue

            #        header   file  value
            entry = (header, (None, value))
            params.append(entry)

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
