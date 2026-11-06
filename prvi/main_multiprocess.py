import time
import argparse
import numpy as np
from multiprocessing import Process, Queue
from queue import Empty
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from oceni import oceni
from population import Population
from archive import Archive
from registry import Registry
from pareto import crowding_distance
from hypervolume import hv3d, normalizuj

parser = argparse.ArgumentParser()
parser.add_argument("--B",          type=int,   default=200)
parser.add_argument("--N",          type=int,   default=20)
parser.add_argument("--K_MUT",      type=int,   default=3)
parser.add_argument("--M",          type=int,   default=5)
parser.add_argument("--T",          type=int,   default=1)
parser.add_argument("--P",          type=int,   default=4)
parser.add_argument("--K_EXCH",     type=int,   default=3)
parser.add_argument("--E",          type=int,   default=2)
parser.add_argument("--topologija", type=str,   default="ring")
parser.add_argument("--seme",       type=int,   default=42)
parser.add_argument("--lambde",     type=float, nargs="+", default=[2.0, 2.0, 2.0, 2.0])
args = parser.parse_args()

B          = args.B
N          = args.N
K_MUT      = args.K_MUT
M          = args.M
G          = 100
T          = args.T
P          = args.P
K_EXCH     = args.K_EXCH
E          = args.E
TOPOLOGIJA = args.topologija
SEME       = args.seme
LAMBDE     = args.lambde
TIMEOUT    = 120   # ukupni rok (s) za prikupljanje rezultata

HV_LO  = (0.0, 0.0, 0.0)
HV_HI  = (10.0, 10.0, 10.0)
HV_REF = (-0.1, -0.1, -0.1)

SEKVENCA = "TEIYQAGSTPCNGVEGFNCYFPLQSYGFQPTN"
ALFABET  = list("ACDEFGHIKLMNPQRSTVWY")


def drugo(rng, staro):
    return rng.choice([a for a in ALFABET if a != staro])


def get_susede(proc_id, rng=None):
    if TOPOLOGIJA == "ring":
        return [(proc_id + 1) % P]
    elif TOPOLOGIJA == "star":
        return [i for i in range(P) if i != proc_id] if proc_id == 0 else [0]
    elif TOPOLOGIJA == "all_to_all":
        return [i for i in range(P) if i != proc_id]
    elif TOPOLOGIJA == "random":
        ostali = [i for i in range(P) if i != proc_id]
        return [int(rng.choice(ostali))]
    else:
        raise ValueError(f"Nepoznata topologija: {TOPOLOGIJA}")


def _radnik(populacija, registry, iter_st, proc_st, lam, rng, rng_lock, st_lock):
    while True:
        with rng_lock:
            kand = populacija.kandidati
            if len(kand) < 2:
                break
            i, j = rng.choice(len(kand), size=2, replace=False)
            r1, r2 = kand[i][0], kand[j][0]
            t = int(rng.integers(1, len(r1)))
            novi = list(r1[:t] + r2[t:])
            s = min(int(rng.poisson(lam)), len(novi))
            if s > 0:
                for p in rng.choice(len(novi), size=s, replace=False):
                    novi[p] = drugo(rng, novi[p])
            kandidat = "".join(novi)

        with st_lock:
            if iter_st['zaustavi'] or proc_st['gotovo']:
                break
            if registry.contains(kandidat):
                proc_st['neuspesni'] += 1
                if proc_st['neuspesni'] >= G:
                    proc_st['gotovo']   = True
                    iter_st['zaustavi'] = True
                continue
            if iter_st['budzet'] <= 0:
                iter_st['zaustavi'] = True
                proc_st['gotovo']   = True
                break
            registry.add(kandidat, None)
            iter_st['budzet']      -= 1
            iter_st['prikupljeno'] += 1
            proc_st['neuspesni']    = 0
            slot = [kandidat, None]
            iter_st['novi'].append(slot)
            if iter_st['prikupljeno'] >= M:
                iter_st['zaustavi'] = True

        ocene = oceni(kandidat)
        with st_lock:
            registry.update(kandidat, ocene)
            slot[1] = ocene


def _iteracija(populacija, registry, budzet_ostalo, proc_st, lam, rng, rng_lock, st_lock):
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
                iter_st, proc_st, lam, rng, rng_lock, st_lock
            )
            futures.append(f)

    for f in futures:
        f.result()

    gotovi = []

    for s, o in iter_st['novi']:
        gotovi.append((s, tuple(o)))

    utroseno = budzet_ostalo - iter_st['budzet']

    return gotovi, utroseno


def _posalji(proc_id, arhiva, queues, rng):
    #salje najvise K_EXCH kandidata iz arhive (najveća razredjenost);
    #ako je arhiva manja od K, salje se cela
    kand = arhiva.kandidati
    if len(kand) > K_EXCH:
        cd  = crowding_distance([o for _, o in kand])
        red = sorted(range(len(kand)), key=lambda k: cd[k], reverse=True)
        kand = [kand[k] for k in red[:K_EXCH]]
    poslato = 0
    for s in get_susede(proc_id, rng):
        for seq, oc in kand:
            queues[s].put((seq, oc))
            poslato += 1
    return poslato


def _primi(inbox, registry):
    primljeni = []
    while True:
        try:
            seq, oc = inbox.get_nowait()
        except Empty:
            break
        if not registry.contains(seq):
            registry.add(seq, tuple(oc))
            primljeni.append((seq, tuple(oc)))
    return primljeni


def proces_funkcija(proc_id, queues, lam, budzet_procesa, rezultat_queue):
    rng      = np.random.default_rng(SEME + proc_id)
    rng_lock = Lock()
    st_lock  = Lock()

    pareto_pool = ThreadPoolExecutor(max_workers=T)
    registry    = Registry()
    populacija  = Population(N, pareto_pool)
    arhiva      = Archive()
    proc_st     = {'neuspesni': 0, 'gotovo': False}

    strani           = set()   # sekvence primljene od drugih procesa
    iter_vremena     = []
    ukupno_poslato   = 0
    ukupno_primljeno = 0

    t_ukupno = time.perf_counter()

    # pocetna populacija
    oc = oceni(SEKVENCA)
    registry.add(SEKVENCA, oc)
    pocetni = [(SEKVENCA, oc)]

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

    budzet    = registry.size()
    iteracija = 0
    inbox     = queues[proc_id]

    while budzet < budzet_procesa and not proc_st['gotovo']:
        # 1. prijem (bez cekanja, ne resetuje brojac neuspesnih)
        primljeni = _primi(inbox, registry)

        if primljeni:
            for seq, ocene in primljeni:
                strani.add(seq)

            ukupno_primljeno += len(primljeni)

        # 2. iteracija
        t_iter = time.perf_counter()
        gotovi, utroseno = _iteracija(
            populacija, registry,
            budzet_procesa - budzet,
            proc_st, lam, rng, rng_lock, st_lock
        )
        budzet    += utroseno
        iteracija += 1
        iter_vremena.append(time.perf_counter() - t_iter)

        # 3. updajt populacije i arhive
        svi_novi = gotovi + primljeni
        if svi_novi:
            populacija.azuriraj(svi_novi, arhiva.kandidati)
            arhiva.azuriraj(populacija.kandidati + svi_novi)

        # 4. razmena (samo svake E-te iteracije)
        if iteracija % E == 0:
            ukupno_poslato += _posalji(proc_id, arhiva, queues, rng)

        # 5. prag G
        if proc_st['gotovo']:
            print(f"[P{proc_id}] Prag G dostignut.")
            break

    ukupno_vreme    = time.perf_counter() - t_ukupno
    strani_u_arhivi = 0
    for seq, ocene in arhiva.kandidati:
        if seq in strani:
            strani_u_arhivi += 1

    pareto_pool.shutdown()
    # neprocitane poruke u ulaznim redovima se namerno gube: to su samo kopije
    # kandidata koje posiljalac i dalje ima u svojoj arhivi
    for q in queues:
        q.cancel_join_thread()

    rezultat_queue.put({
        'proc_id':         proc_id,
        'arhiva':          arhiva.kandidati,
        'evaluacije':      budzet,
        'poslato':         ukupno_poslato,
        'primljeno':       ukupno_primljeno,
        'strani':          list(strani),
        'strani_u_arhivi': strani_u_arhivi,
        'iter_vremena':    iter_vremena,
        'ukupno_vreme':    ukupno_vreme,
    })


if __name__ == "__main__":
    budzet_procesa = B // P

    if len(LAMBDE) != P:
        LAMBDE = list(np.linspace(0.5, 4.0, P))

    queues = []
    for i in range(P):
        queues.append(Queue())

    rezultat_queue = Queue()

    print(f"{P}×{T} | {TOPOLOGIJA} | E={E} | λ={LAMBDE} | seme={SEME} ")
    t_main = time.perf_counter()

    procesi = []
    for i in range(P):
        p = Process(
            target=proces_funkcija,
            args=(i, queues, LAMBDE[i], budzet_procesa, rezultat_queue)
        )
        procesi.append(p)

    for p in procesi:
        p.start()

    # prikupljanje: staje kad stignu svi rezultati, kad svi procesi umru ili istekne rok
    rezultati = []
    rok = time.perf_counter() + TIMEOUT
    while len(rezultati) < P and time.perf_counter() < rok:
        try:
            rezultati.append(rezultat_queue.get(timeout=1))
        except Empty:
            if not any(p.is_alive() for p in procesi):
                try:
                    while True:
                        rezultati.append(rezultat_queue.get(timeout=1))
                except Empty:
                    pass
                break

    if len(rezultati) < P:
        print(f"Upozorenje: stiglo je {len(rezultati)} od {P} rezultata.")

    for p in procesi:
        p.join(timeout=5)
        if p.is_alive():
            p.terminate()

    ukupno_vreme_main = time.perf_counter() - t_main

    # metrike po procesu
    print(f"\nMETRIKE PO PROCESU ")
    ukupno_eval = 0
    for r in sorted(rezultati, key=lambda x: x['proc_id']):
        pid = r['proc_id']
        itr = r['iter_vremena']
        prosek_ms = sum(itr) / len(itr) * 1000 if itr else 0
        print(f"  P{pid} λ={LAMBDE[pid]}: "
              f"eval={r['evaluacije']}  "
              f"iter={len(itr)}  "
              f"iter_prosek={prosek_ms:.1f}ms  "
              f"vreme={r['ukupno_vreme']:.3f}s  "
              f"poslato={r['poslato']}  "
              f"primljeno={r['primljeno']}  "
              f"strani_u_lokalnoj_arhivi={r['strani_u_arhivi']}")
        ukupno_eval += r['evaluacije']

    print(f"\nUkupno evaluacija: {ukupno_eval}")
    print(f"Ukupno vreme:      {ukupno_vreme_main:.3f}s")

    # spajanje arhiva
    sve_arhive = []
    for r in rezultati:
        sve_arhive.extend(r['arhiva'])

    finalna_arhiva = Archive()
    finalna_arhiva.azuriraj(sve_arhive)

    finalne_seq = set()

    for seq, ocene in finalna_arhiva.kandidati:
        finalne_seq.add(seq)

    print(f"\nStrani kandidati u konačnoj arhivi (po procesu koji ih je primio):")

    rezultati.sort(key=lambda x: x['proc_id'])

    for r in rezultati:
        broj = len(finalne_seq & set(r['strani']))
        print("P" + str(r['proc_id']) + ":", broj)

    ocene_arhive = []
    for kandidat in finalna_arhiva.kandidati:
        ocene_arhive.append(kandidat[1])

    print(f"\nFINALNA ARHIVA")
    print(f"Veličina: {len(ocene_arhive)}")

    if ocene_arhive:
        for i, naziv in enumerate(["par1", "par2", "par3"]):
            vrednosti = [o[i] for o in ocene_arhive]
            print(f"  {naziv}: [{min(vrednosti):.3f}, {max(vrednosti):.3f}]")
        norm = normalizuj(ocene_arhive, HV_LO, HV_HI)
        print(f"Hypervolume (3D): {hv3d(norm, HV_REF):.6f}")

    print("\nSekvence:")
    for seq, oc in finalna_arhiva.kandidati:
        print(f"  {seq} → {oc}")