"""
Defines the available environments.
"""


from enum import StrEnum
from local.request_schema import RefPanel


class Environment(StrEnum):
    TOPMED_DEV     = "topmed-dev"
    TOPMED_STAGING = "topmed-staging"
    TOPMED_PROD    = "topmed"
    MICHIGAN       = "michigan"
    MCPS           = "mcps"


_BASE_URL = {
    Environment.TOPMED_DEV     : "https://topmed.dev.imputationserver.org",
    Environment.TOPMED_STAGING : "https://staging.topmed.imputationserver.org",
    Environment.TOPMED_PROD    : "https://imputation.biodatacatalyst.nhlbi.nih.gov",
    Environment.MICHIGAN       : "https://imputationserver.sph.umich.edu/",
    Environment.MCPS           : "https://imputationserver-reg.sph.umich.edu",
}


def get_base_url(env: Environment) -> str:
    return _BASE_URL[env]

_REFPANEL_LOOKUP = {
    Environment.TOPMED_DEV: {
        "hapmap"       : RefPanel.TOPMED_DEV_HAPMAP_2,
        "hapmap2"      : RefPanel.TOPMED_DEV_HAPMAP_2,

        "r3"           : RefPanel.TOPMED_DEV_TOPMED_R3_DEV,
        "topmedr3"     : RefPanel.TOPMED_DEV_TOPMED_R3_DEV,

        "r3prod"       : RefPanel.TOPMED_DEV_TOPMED_R3_PROD,
        "topmedr3prod" : RefPanel.TOPMED_DEV_TOPMED_R3_PROD,
    },
    Environment.TOPMED_STAGING: {
        "r3"       : RefPanel.TOPMED_STAGING_TOPMED_R3,
        "topmedr3" : RefPanel.TOPMED_STAGING_TOPMED_R3,
    },
    Environment.TOPMED_PROD: {
        "r3"       : RefPanel.TOPMED_PROD_TOPMED_R3,
        "topmedr3" : RefPanel.TOPMED_PROD_TOPMED_R3,
    },
    Environment.MICHIGAN: {
        "1000gphase1"          : RefPanel.MICHIGAN_1KG_P1_V3,
        "1000gp1"              : RefPanel.MICHIGAN_1KG_P1_V3,
        "1000gphase1v3"        : RefPanel.MICHIGAN_1KG_P1_V3,
        "1000gp1v3"            : RefPanel.MICHIGAN_1KG_P1_V3,

        "1000gphase3"          : RefPanel.MICHIGAN_1KG_P3,
        "1000gp3"              : RefPanel.MICHIGAN_1KG_P3,
        "1000gphase3low"       : RefPanel.MICHIGAN_1KG_P3,
        "1000gp3low"           : RefPanel.MICHIGAN_1KG_P3,

        "1000gphase3deep"      : RefPanel.MICHIGAN_1KG_P3_30X,
        "1000gphase330x"       : RefPanel.MICHIGAN_1KG_P3_30X,
        "1000gp3deep"          : RefPanel.MICHIGAN_1KG_P3_30X,
        "1000gp330x"           : RefPanel.MICHIGAN_1KG_P3_30X,

        "1000gphase3v5"        : RefPanel.MICHIGAN_1KG_P3_V5,
        "1000gp3v5"            : RefPanel.MICHIGAN_1KG_P3_V5,

        "caapa"                : RefPanel.MICHIGAN_CAAPA,
        "africanamericanpanel" : RefPanel.MICHIGAN_CAAPA,
        "africanamerican"      : RefPanel.MICHIGAN_CAAPA,

        "gasp"                 : RefPanel.MICHIGAN_GASP,
        "genomeasiapilot"      : RefPanel.MICHIGAN_GASP,
        "genomeasia"           : RefPanel.MICHIGAN_GASP,
        "asiapilot"            : RefPanel.MICHIGAN_GASP,

        "hrc"                  : RefPanel.MICHIGAN_HRC_R11,
        "r11"                  : RefPanel.MICHIGAN_HRC_R11,
        "hrcr11"               : RefPanel.MICHIGAN_HRC_R11,

        "hapmap"               : RefPanel.MICHIGAN_HAPMAP_2,
        "hapmap2"              : RefPanel.MICHIGAN_HAPMAP_2,

        "samoan"               : RefPanel.MICHIGAN_SAMOAN,
    },
    Environment.MCPS: {
        "hapmap"  : RefPanel.MCPS_HAPMAP_2,
        "hapmap2" : RefPanel.MCPS_HAPMAP_2,

        "mcps"    : RefPanel.MCPS_MCPS,
    }
}

def normalize_refpanel_key(key: str) -> str:
    return key.strip().lower().replace("-", "").replace("_", "").replace(".", "")

def match_refpanel(env: Environment, refpanel: str) -> RefPanel | None:
    assert env in _REFPANEL_LOOKUP.keys()
    env_lookup = _REFPANEL_LOOKUP[env]

    processed = normalize_refpanel_key(refpanel)
    return env_lookup.get(processed, None)
