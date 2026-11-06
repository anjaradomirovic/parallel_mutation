from pareto import pareto_ranks, crowding_distance


class Population:
    def __init__(self, max_size, pool=None):
        self.max_size = max_size
        self.pool = pool
        self.kandidati = []

    def azuriraj(self, novi_kandidati, arhiva_kandidati):

        svi = self.kandidati + arhiva_kandidati + novi_kandidati
        jedinstveni = {}

        for seq, o in svi:
            jedinstveni[seq] = tuple(o)

        svi = list(jedinstveni.items())
        ocene = []

        for seq, o in svi:
            ocene.append(o)

        rangovi = pareto_ranks(ocene, self.pool)
        slojevi = {}

        for seq, ocena in svi:
            rang = rangovi[ocena]

            if rang not in slojevi:
                slojevi[rang] = []

            slojevi[rang].append((seq, ocena))

        nova = []
        rangovi_slojeva = sorted(slojevi.keys())

        for rang in rangovi_slojeva:
            sloj = slojevi[rang]

            if len(nova) + len(sloj) <= self.max_size:
                nova.extend(sloj)

            else:
                potrebno = self.max_size - len(nova)
                ocene_sloja = []

                for seq, ocena in sloj:
                    ocene_sloja.append(ocena)

                cd = crowding_distance(ocene_sloja)
                redosled = list(range(len(sloj)))
                redosled.sort(reverse=True, key=cd.__getitem__)
                for k in redosled[:potrebno]:
                    nova.append(sloj[k])

                break

        self.kandidati = nova

    def add(self, sekvenca, ocene):
        self.kandidati.append((sekvenca, ocene))

    def get_ocene(self):
        rezultat = []
        for seq, ocene in self.kandidati:
            rezultat.append(ocene)
        return rezultat

