#!/usr/bin/env python3
"""Alertas y avisos OFICIALES del SMN que tocan el cultivo (Lanús).

Lee el índice CAP público del SMN (ssl.smn.gob.ar/CAP/AR.php), baja cada alerta en formato CAP 1.2
y se queda con las que tienen un polígono que contiene el punto del cultivo y siguen vigentes.
Nivel: Moderate = amarilla, Severe = naranja, Extreme = roja.
"""
import re, sys, html, datetime as dt, urllib.request
from concurrent.futures import ThreadPoolExecutor
import xml.etree.ElementTree as ET

LAT, LON = -34.70, -58.39
INDICE = "https://ssl.smn.gob.ar/CAP/AR.php"
NS = {"c": "urn:oasis:names:tc:emergency:cap:1.2"}
NIVEL = {"Minor": "amarilla", "Moderate": "amarilla", "Severe": "naranja", "Extreme": "roja"}


def bajar(url, t=25):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=t).read().decode("utf-8", "replace")


def adentro(lat, lon, pts):
    """Punto en polígono (ray casting). pts = [(lat, lon), ...]."""
    ok, j = False, len(pts) - 1
    for i in range(len(pts)):
        yi, xi = pts[i]; yj, xj = pts[j]
        if (xi > lon) != (xj > lon) and lat < (yj - yi) * (lon - xi) / (xj - xi + 1e-12) + yi:
            ok = not ok
        j = i
    return ok


def leer_cap(url):
    try: raiz = ET.fromstring(bajar(url).encode("utf-8"))
    except Exception: return []
    out = []
    for info in raiz.findall("c:info", NS):
        g = lambda k: (info.findtext("c:" + k, default="", namespaces=NS) or "").strip()
        pols = []
        for area in info.findall("c:area", NS):
            for p in area.findall("c:polygon", NS):
                pts = []
                for par in (p.text or "").split():
                    a, b = par.split(",")[:2]
                    pts.append((float(a), float(b)))
                if len(pts) >= 3: pols.append(pts)
            desc = area.findtext("c:areaDesc", default="", namespaces=NS) or ""
            if "lanus" in desc.lower().replace("ú", "u"): pols.append(None)
        if not any(p is None or adentro(LAT, LON, p) for p in pols): continue
        out.append({"evento": g("event") or g("headline"), "nivel": NIVEL.get(g("severity"), "amarilla"),
                    "desde": g("onset") or g("effective") or g("sent"), "hasta": g("expires"),
                    "txt": html.unescape(g("description")), "url": url})
    return out


def alertas(ahora=None):
    ahora = ahora or dt.datetime.now(dt.timezone(dt.timedelta(hours=-3)))
    idx = bajar(INDICE)
    urls = sorted(set(re.findall(r'https://ssl\.smn\.gob\.ar/feeds/CAP/[^"\s]+\.xml', idx)))
    with ThreadPoolExecutor(8) as ex:
        todas = [a for r in ex.map(leer_cap, urls) for a in r]
    vig, vistas = [], set()
    for a in todas:
        try:
            hasta = dt.datetime.fromisoformat(a["hasta"]) if a["hasta"] else None
            desde = dt.datetime.fromisoformat(a["desde"]) if a["desde"] else None
        except ValueError: hasta = desde = None
        if hasta and hasta < ahora: continue
        if desde and desde > ahora + dt.timedelta(hours=48): continue
        k = (a["evento"], a["nivel"], a["desde"][:13])
        if k in vistas: continue
        vistas.add(k); vig.append(a)
    orden = {"roja": 0, "naranja": 1, "amarilla": 2}
    return sorted(vig, key=lambda a: (orden[a["nivel"]], a["desde"]))


if __name__ == "__main__":
    for a in alertas():
        print(a["nivel"], a["evento"], a["desde"], "→", a["hasta"]); print("  ", a["txt"][:200])
