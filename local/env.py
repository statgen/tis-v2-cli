"""
Defines the available environments.
"""


from enum import StrEnum


class Environment(StrEnum):
    TOPMED_DEV  = "topmed-dev"
    TOPMED_PROD = "topmed"
    MICHIGAN    = "michigan"
    MCPS        = "mcps"


_BASE_URL = {
    Environment.TOPMED_DEV  : "https://topmed.dev.imputationserver.org",
    Environment.TOPMED_PROD : "https://imputation.biodatacatalyst.nhlbi.nih.gov",
    Environment.MICHIGAN    : "https://imputationserver.sph.umich.edu/",
    Environment.MCPS        : "https://imputationserver-reg.sph.umich.edu",
}


def get_base_url(env: Environment) -> str:
    return _BASE_URL[env]
