from oceni import oceni
from registry import Registry


def evaluiraj(sekvenca, registry):
    if registry.contains(sekvenca):
        return None  # duplikati
    ocene = oceni(sekvenca)
    registry.add(sekvenca, ocene)
    return ocene