def hv2d(tacke, ref):
    povrsina, najbolji_y = 0.0, ref[1]
    for x, y in sorted(tacke, reverse=True):
        if y > najbolji_y:
            povrsina += (x - ref[0]) * (y - najbolji_y)
            najbolji_y = y
    return povrsina


def hv3d(tacke, ref):
    tacke = sorted(tacke, key=lambda t: t[2], reverse=True)
    zapremina = 0.0
    for i, (_, _, z) in enumerate(tacke):
        sledeci_z = tacke[i + 1][2] if i + 1 < len(tacke) else ref[2]
        visina = z - sledeci_z
        if visina > 0:
            sloj = [(x, y) for x, y, _ in tacke[:i + 1]]
            zapremina += hv2d(sloj, ref[:2]) * visina
    return zapremina


def normalizuj(tacke, lo, hi):
    return [tuple((v - l) / (h - l) for v, l, h in zip(t, lo, hi)) for t in tacke]