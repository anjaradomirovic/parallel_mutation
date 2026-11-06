def dominates(a, b):
    for i in range(len(a)):
        if a[i] < b[i]:
            return False

    for i in range(len(a)):
        if a[i] > b[i]:
            return True

    return False

def _je_dominiran(args):
    s, preostali = args
    for t in preostali:
        if t != s:
            if dominates(t, s):
                return s, True

    return s, False


def pareto_ranks(scores, pool=None):
    preostali = list(scores)
    rangovi = {}
    rang = 1

    while len(preostali) > 0:
        front = []

        for s in preostali:
            dominiran = False

            for t in preostali:
                if t != s and dominates(t, s):
                    dominiran = True
                    break

            if not dominiran:
                front.append(s)

        for s in front:
            rangovi[s] = rang
            preostali.remove(s)

        rang += 1

    return rangovi

def crowding_distance(scores):
    n = len(scores)
    if n <= 2:
        return [float('inf')] * n
    d = [0.0] * n

    broj_kriterijuma = len(scores[0])
    for i in range(broj_kriterijuma):
        idx = list(range(n))
        idx.sort(key=lambda k: scores[k][i])

        najmanji = idx[0]
        najveci = idx[-1]

        raspon = scores[najveci][i] - scores[najmanji][i]

        d[najmanji] = float('inf')
        d[najveci] = float('inf')

        if raspon == 0:
            continue

        for p in range(1, n - 1):
            prethodni = idx[p - 1]
            sledeci = idx[p + 1]
            trenutni = idx[p]

            d[trenutni] += (scores[sledeci][i] - scores[prethodni][i]) / raspon

    return d