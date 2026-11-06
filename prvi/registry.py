class Registry:
    def __init__(self):
        self.podaci = {}

    def contains(self, sekvenca):
        return sekvenca in self.podaci

    def add(self, sekvenca, ocene):
        self.podaci[sekvenca] = ocene

    def update(self, sekvenca, ocene):
        self.podaci[sekvenca] = ocene

    def get(self, sekvenca):
        return self.podaci[sekvenca]

    def size(self):
        return len(self.podaci)

    def get_ocenjene(self):
        #vraca listu svih sekvenci koje imaju dodeljenu ocenu
        ocenjene = []

        for sekvenca, ocena in self.podaci.items():
            if ocena is not None:
                ocenjene.append((sekvenca, ocena))

        return ocenjene