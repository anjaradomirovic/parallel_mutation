import time
import numpy as np
from oceni import oceni
from population import Population
from archive import Archive
from registry import Registry
from hypervolume import hv3d, normalizuj

# PARAMETRI
B        = 200
N        = 20
K_MUT    = 3
M        = 5
LAMBDA   = 2.0
G        = 100
HV_LO    = (0.0, 0.0, 0.0)
HV_HI    = (10.0, 10.0, 10.0)
HV_REF   = (-0.1, -0.1, -0.1)
SEKVENCA = "TEIYQAGSTPCNGVEGFNCYFPLQSYGFQPTN"
ALFABET  = list("ACDEFGHIKLMNPQRSTVWY")


def drugo(rng, staro):
    return rng.choice([a for a in ALFABET if a != staro])


for SEME in [42, 123, 999]:
    print("\nPokretanje P1: 1x1")
    print("Seme:", SEME)

    rng          = np.random.default_rng(SEME)
    registry     = Registry()
    populacija   = Population(N)          # bez pool-a: čista jednonitna baza
    arhiva       = Archive()
    iter_vremena = []

    def mutiraj_pocetni(seq):
        s = list(seq)
        n = int(rng.integers(1, K_MUT + 1))
        for p in rng.choice(len(s), size=min(n, len(s)), replace=False):
            s[p] = drugo(rng, s[p])
        return "".join(s)

    def generisi(populacija):
        kand = populacija.kandidati
        i, j = rng.choice(len(kand), size=2, replace=False)
        r1, r2 = kand[i][0], kand[j][0]
        t = int(rng.integers(1, len(r1)))
        novi = list(r1[:t] + r2[t:])
        s = min(int(rng.poisson(LAMBDA)), len(novi))
        if s > 0:
            for p in rng.choice(len(novi), size=s, replace=False):
                novi[p] = drugo(rng, novi[p])
        return "".join(novi)

    pocetni = []
    oc = oceni(SEKVENCA)
    registry.add(SEKVENCA, oc)
    pocetni.append((SEKVENCA, oc))

    while len(pocetni) < N:
        m = mutiraj_pocetni(SEKVENCA)
        if not registry.contains(m):
            oc = oceni(m)
            registry.add(m, oc)
            pocetni.append((m, oc))

    for seq, oc in pocetni:
        populacija.add(seq, oc)
    arhiva.azuriraj(pocetni)
    budzet    = registry.size()
    neuspesni = 0
    gotovo    = False
    t_ukupno  = time.perf_counter()

    while budzet < B and not gotovo:
        t_iter = time.perf_counter()
        novi   = []

        while len(novi) < M and budzet < B and not gotovo:
            kandidat = generisi(populacija)
            if registry.contains(kandidat):
                neuspesni += 1
                if neuspesni >= G:
                    gotovo = True
                continue
            neuspesni = 0
            oc = oceni(kandidat)
            registry.add(kandidat, oc)
            novi.append((kandidat, oc))
            budzet += 1

        if novi:
            populacija.azuriraj(novi, arhiva.kandidati)
            arhiva.azuriraj(populacija.kandidati + novi)

        iter_vremena.append(time.perf_counter() - t_iter)

    ukupno_vreme = time.perf_counter() - t_ukupno
    ocene_arhive = [oc for _, oc in arhiva.kandidati]
    prosek_ms    = sum(iter_vremena) / len(iter_vremena) * 1000 if iter_vremena else 0

    print(f"Ukupno vreme:     {ukupno_vreme:.3f}s")
    print(f"Iteracije:        {len(iter_vremena)}")
    print(f"Iter prosek:      {prosek_ms:.1f}ms")
    print(f"Evaluacije:       {registry.size()}")
    print(f"Arhiva:           {len(ocene_arhive)} kandidata")
    if ocene_arhive:
        for i, naziv in enumerate(["par1", "par2", "par3"]):
            vrednosti = [o[i] for o in ocene_arhive]
            print(f"  {naziv}: [{min(vrednosti):.3f}, {max(vrednosti):.3f}]")
        norm = normalizuj(ocene_arhive, HV_LO, HV_HI)
        print(f"Hypervolume:      {hv3d(norm, HV_REF):.6f}")

    print("\nPareto arhiva:")
    for seq, oc in arhiva.kandidati:
        print(f"  {seq} → {oc}")