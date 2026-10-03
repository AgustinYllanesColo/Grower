#!/usr/bin/env python3
"""Lluvia MEDIDA por las estaciones del SMN, leída de los partes SYNOP que publica Ogimet.

Cada parte trae, cuando corresponde, el grupo 6RRRt: milímetros (RRR) en las últimas tR horas.
El día local (UTC-3) d se arma con los cuatro períodos de 6 h que terminan a las 12 y 18 UTC de d
y a las 00 y 06 UTC de d+1. Si falta alguno, se usa el acumulado de 24 h de las 12 UTC de d+1.
"""
import sys, time, urllib.request, datetime as dt

ESTACIONES = {"87585": "Buenos Aires Observatorio", "87582": "Aeroparque", "87576": "Ezeiza"}
HORAS = {"1": 6, "2": 12, "3": 18, "4": 24, "5": 1, "6": 2, "7": 3, "8": 9, "9": 15}


def rrr(v):
    n = int(v)
    if n == 990: return 0.0
    if n > 990: return (n - 990) / 10
    return float(n)


def leer(bloque, desde, hasta):
    url = (f"https://www.ogimet.com/cgi-bin/getsynop?block={bloque}"
           f"&begin={desde:%Y%m%d}0000&end={hasta:%Y%m%d}2300")
    txt = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=60).read().decode("latin-1")
    partes = []
    for linea in txt.splitlines():
        p = linea.split(",")
        if len(p) < 7 or "AAXX" not in p[6]: continue
        cuando = dt.datetime(int(p[1]), int(p[2]), int(p[3]), int(p[4]))
        g = p[6].replace("=", "").split()
        try: i = g.index(bloque)
        except ValueError: continue
        sec1, resto = [], g[i + 1:]
        for t in resto:
            if t == "333": break
            sec1.append(t)
        sec3 = resto[len(sec1) + 1:] if "333" in resto else []
        def precip(grupos, saltar):
            ult = 0
            for t in grupos[saltar:]:
                if len(t) != 5 or not t[0].isdigit(): continue
                d = int(t[0])
                if d == 6 and ult < 6 and t[1:4].isdigit() and t[4] in HORAS:
                    return rrr(t[1:4]), HORAS[t[4]]
                if d < ult: break
                ult = d
            return None
        r = precip(sec1, 2) or precip(sec3, 0)
        iR = sec1[0][0] if sec1 else "4"
        if r is None and iR == "3": r = (0.0, 6 if cuando.hour % 6 == 0 else 1)
        if r is not None: partes.append((cuando, r[1], r[0]))
    return partes


def por_dia(partes, dias):
    seis = seis_horas(partes)
    out = {}
    for d in dias:
        f = dt.datetime.fromisoformat(d)
        fines = [f.replace(hour=12), f.replace(hour=18), f + dt.timedelta(days=1), f + dt.timedelta(days=1, hours=6)]
        v = [seis.get((t, 6)) for t in fines]
        if all(x is not None for x in v):
            out[d] = round(sum(v), 1)
        elif seis.get((f + dt.timedelta(days=1, hours=12), 24)) is not None:
            out[d] = seis[(f + dt.timedelta(days=1, hours=12), 24)]
    return out


def seis_horas(partes):
    """{(fin UTC, 6): mm}, con el tramo 06-12 UTC sacado del acumulado de 24 h cuando falta."""
    seis = {(c, h): mm for c, h, mm in partes}
    for (c, h), mm in list(seis.items()):
        if h == 24 and c.hour == 12 and (c, 6) not in seis:
            prev = [seis.get((c - dt.timedelta(hours=k), 6)) for k in (18, 12, 6)]
            if all(x is not None for x in prev):
                seis[(c, 6)] = round(max(0.0, mm - sum(prev)), 1)
    return seis


def lluvia_hoy(hoy):
    """Lo medido en el día local que está corriendo (desde las 3 h): {"mm", "hasta" (hora local), "est"}."""
    f = dt.datetime.fromisoformat(hoy)
    por_est, hasta = {}, None
    for i, (b, nombre) in enumerate(ESTACIONES.items()):
        if i: time.sleep(25)
        try:
            seis = seis_horas(leer(b, f.date() - dt.timedelta(days=1), f.date()))
            tramos = [(t, seis.get((t, 6))) for t in (f.replace(hour=12), f.replace(hour=18))]
            ok = [(t, v) for t, v in tramos if v is not None]
            # solo tramos consecutivos desde el primero
            if ok and ok[0][0] == tramos[0][0]:
                por_est[nombre] = round(sum(v for _, v in ok), 1)
                h = ok[-1][0].hour - 3
                hasta = h if hasta is None else min(hasta, h)
        except Exception as e: print("ogimet", b, e, file=sys.stderr)
    if not por_est: return None
    xs = sorted(por_est.values())
    return {"mm": xs[len(xs) // 2], "hasta": hasta, "est": por_est}


def lluvia_medida(dias):
    """{fecha: {"mm": mediana, "est": {estación: mm}}} para los días con datos completos."""
    d0 = dt.date.fromisoformat(min(dias)); d1 = dt.date.fromisoformat(max(dias)) + dt.timedelta(days=1)
    por_est = {}
    for i, (b, nombre) in enumerate(ESTACIONES.items()):
        if i: time.sleep(25)            # Ogimet limita la frecuencia de pedidos
        try: por_est[nombre] = por_dia(leer(b, d0, d1), dias)
        except Exception as e: print("ogimet", b, e, file=sys.stderr)
    out = {}
    for d in dias:
        vals = {n: v[d] for n, v in por_est.items() if d in v}
        if vals:
            xs = sorted(vals.values())
            out[d] = {"mm": xs[len(xs) // 2], "est": vals}
    return out


if __name__ == "__main__":
    if sys.argv[1:2] == ["hoy"]: print(lluvia_hoy(sys.argv[2]))
    else: print(lluvia_medida(sys.argv[1:]))
