from dataclasses import dataclass


@dataclass
class Population:
    id           : str
    display_name : str


@dataclass
class RefPanel:
    id          : str
    aliases     : list[str]
    populations : dict[str, Population]

    def get_population(self, population: str) -> Population:
        # ASSUMPTION: Population IDs are ALWAYS in normalized form!

        population_norm = normalize_name(population)

        if not population_norm in self.populations:
            raise ValueError(f"Refpanel '{self.id}': population not recognized: '{population}' (normalized form: {population_norm}). Accepted values: {[ k for k in self.populations.keys() ]}")

        return self.populations[population_norm]


@dataclass
class Server:
    id              : str
    url             : str
    aliases         : list[str]
    refpanels       : dict[str, RefPanel] # Canonical mapping: (original ID) -> RefPanel
    refpanel_lookup : dict[str, RefPanel] # Lookup: (any possible NORMALIZED name) -> RefPanel

    def get_refpanel(self, refpanel: str) -> RefPanel:
        refpanel_norm = normalize_name(refpanel)

        if not refpanel_norm in self.refpanel_lookup:
            raise ValueError(f"Server '{self.id}': refpanel not recognized: '{refpanel}' (normalized form: {refpanel_norm}). Accepted values: {[ k for k in self.refpanel_lookup.keys() ]}")

        return self.refpanel_lookup[refpanel_norm]


def normalize_name(name: str) -> str:
    """Produces a normalized name representation that ignores whitespace, casing, and the common joiners `-_.`"""

    without_whitespace = "".join(name.split()) # Also removes internal whitespace
    without_punctuation = without_whitespace.replace("-", "").replace("_", "").replace(".", "") # Removes [-_.]+
    lowercase = without_punctuation.lower()

    return lowercase
