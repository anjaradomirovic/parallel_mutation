from pareto import dominates

class Archive:
    def __init__(self):
        self.kandidati = []  # lista (sekvenca, ocene)

# cuvaju se samo nedominirani kandidati
    def azuriraj(self, novi_kandidati):
        recnik = {}

        for seq, ocene in self.kandidati:
            recnik[seq] = tuple(ocene)

        for seq, ocene in novi_kandidati:
            recnik[seq] = tuple(ocene)

        svi = list(recnik.items())

        nedominirani = []

        for seq, ocena in svi:
            dominiran = False

            for _, druga_ocena in svi:
                if druga_ocena != ocena:
                    if dominates(druga_ocena, ocena):
                        dominiran = True
                        break

            if not dominiran:
                nedominirani.append((seq, ocena))

        self.kandidati = nedominirani

    def get_ocene(self):
        ocene_lista = []

        for kandidat in self.kandidati:
            ocene_lista.append(kandidat[1])

        return ocene_lista