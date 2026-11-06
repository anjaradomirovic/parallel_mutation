import time
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
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
T        = 4
HV_LO    = (0.0, 0.0, 0.0)
HV_HI    = (10.0, 10.0, 10.0)
HV_REF   = (-0.1, -0.1, -0.1)
SEKVENCA = "TEIYQAGSTPCNGVEGFNCYFPLQSYGFQPTN"
ALFABET  = list("ACDEFGHIKLMNPQRSTVWY")


def drugo(rng, staro):
    return rng.choice([a for a in ALFABET if a != staro])


def _generisi(populacija, rng, rng_lock):
    with rng_lock:
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


def _radnik(populacija, registry, iter_st, proc_st, rng, rng_lock, st_lock):
    while True:
        kandidat = _generisi(populacija, rng, rng_lock)
        with st_lock:
            if iter_st['zaustavi'] or proc_st['gotovo']:
                break
            if registry.contains(kandidat):
                proc_st['neuspesni'] += 1
                if proc_st['neuspesni'] >= G:
                    proc_st['gotovo'] = True
                    iter_st['zaustavi'] = True
                continue
            if iter_st['budzet'] <= 0:
                iter_st['zaustavi'] = True
                proc_st['gotovo'] = True
                break
            registry.add(kandidat, None)
            iter_st['budzet'] -= 1
            iter_st['prikupljeno'] += 1
            proc_st['neuspesni'] = 0
            slot = [kandidat, None]
            iter_st['novi'].append(slot)
            if iter_st['prikupljeno'] >= M:
                iter_st['zaustavi'] = True

        ocene = oceni(kandidat)
        with st_lock:
            registry.update(kandidat, ocene)
            slot[1] = ocene


def _iteracija(populacija, registry, budzet_ostalo, proc_st, rng, rng_lock, st_lock):
    iter_st = {
        'budzet': budzet_ostalo,
        'prikupljeno': 0,
        'zaustavi': False,
        'novi': []
    }

    with ThreadPoolExecutor(max_workers=T) as ex:
        futures = []

        for i in range(T):
            f = ex.submit(
                _radnik, populacija, registry,
                iter_st, proc_st, rng, rng_lock, st_lock
            )
            futures.append(f)

    for f in futures:
        f.result()

    gotovi = []

    for s, o in iter_st['novi']:
        gotovi.append((s, tuple(o)))

    utroseno = budzet_ostalo - iter_st['budzet']

    return gotovi, utroseno


for SEME in [42, 123, 999]:
    print("\nPokretanje P2: 1x" + str(T))
    print("Seme:", SEME)

    rng      = np.random.default_rng(SEME)
    rng_lock = Lock()
    st_lock  = Lock()

    pareto_pool  = ThreadPoolExecutor(max_workers=T)
    registry     = Registry()
    populacija   = Population(N, pareto_pool)
    arhiva       = Archive()
    iter_vremena = []

    pocetni = []
    oc = oceni(SEKVENCA)
    registry.add(SEKVENCA, oc)
    pocetni.append((SEKVENCA, oc))

    while len(pocetni) < N:
        s = list(SEKVENCA)
        n = int(rng.integers(1, K_MUT + 1))
        for p in rng.choice(len(s), size=min(n, len(s)), replace=False):
            s[p] = drugo(rng, s[p])
        mutant = "".join(s)
        if not registry.contains(mutant):
            oc = oceni(mutant)
            registry.add(mutant, oc)
            pocetni.append((mutant, oc))

    for seq, oc in pocetni:
        populacija.add(seq, oc)
    arhiva.azuriraj(pocetni)
    budzet   = registry.size()
    proc_st  = {'neuspesni': 0, 'gotovo': False}
    t_ukupno = time.perf_counter()

    while budzet < B and not proc_st['gotovo']:
        t_iter = time.perf_counter()
        gotovi, utroseno = _iteracija(
            populacija, registry, B - budzet, proc_st, rng, rng_lock, st_lock
        )
        budzet += utroseno
        iter_vremena.append(time.perf_counter() - t_iter)
        if gotovi:
            populacija.azuriraj(gotovi, arhiva.kandidati)
            arhiva.azuriraj(populacija.kandidati + gotovi)

    ukupno_vreme = time.perf_counter() - t_ukupno
    ocene_arhive = []
    for kandidat in arhiva.kandidati:
        ocene_arhive.append(kandidat[1])
    prosek_ms = 0

    if len(iter_vremena) > 0:
        prosek_ms = sum(iter_vremena) / len(iter_vremena) * 1000

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

    pareto_pool.shutdown()