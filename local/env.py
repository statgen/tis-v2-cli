"""
Defines the available environments.
"""


from enum import StrEnum


class Environment(StrEnum):
    DEV  = "dev"
    PROD = "prod"
    MCPS = "mcps"


_BASE_URL = {
    Environment.DEV  : "https://topmed.dev.imputationserver.org",
    Environment.PROD : "https://imputation.biodatacatalyst.nhlbi.nih.gov",
    Environment.MCPS : "https://imputationserver-reg.sph.umich.edu",
}


def get_base_url(env: Environment) -> str:
    return _BASE_URL[env]
