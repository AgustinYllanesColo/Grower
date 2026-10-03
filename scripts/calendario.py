#!/usr/bin/env python3
"""Arma el .ics de la temporada para el calendario del iPhone a partir de las acciones de la bitácora.
Uso: python3 scripts/calendario.py acciones.json calendario/temporada-26-27.ics [desde AAAA-MM-DD]
Cada evento es de día completo, con aviso a las 9 h del día anterior. El UID es el id de la acción:
si se vuelve a importar, el calendario lo reconoce como el mismo evento."""
import json, sys, datetime as dt

def esc(t): return str(t).replace("\\", "\\\\").replace(";", "\;").replace(",", "\\,").replace("\n", "\\n")
def plegar(l):
    b = l.encode("utf-8"); out = []
    while len(b) > 74:
        corte = 74
        while (b[corte] & 0xC0) == 0x80: corte -= 1
        out.append(b[:corte].decode()); b = b" " + b[corte:]
    out.append(b.decode()); return "\r\n".join(out)

acc = json.load(open(sys.argv[1])); desde = sys.argv[3] if len(sys.argv) > 3 else dt.date.today().isoformat()
ahora = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
L = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Grower//Bitacora Suelo Vivo//ES", "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
     "X-WR-CALNAME:Suelo Vivo 26/27", "X-WR-TIMEZONE:America/Argentina/Buenos_Aires"]
for a in sorted(acc, key=lambda x: x["due"]):
    if a["due"] < desde: continue
    d = dt.date.fromisoformat(a["due"])
    titulo = a["n"] + (" (estimado)" if a.get("st") == "bloqueada" else "")
    pref = {"compra": "Comprar · ", "casa": "En casa · "}.get(a.get("tipo"), "")
    if pref and titulo.lower().startswith(("comprar", "conseguir", "juntar", "armar el kit", "bandeja", "kit")): pref = ""
    desc = (a.get("why") or "")[:700]
    if a.get("pasos"): desc += "\n\nPasos:\n" + "\n".join("• " + p for p in a["pasos"][:8])
    if a.get("dur"): desc += "\n\nTiempo: " + a["dur"]
    desc += "\n\nLa fecha se mueve según el clima y lo que pase: la bitácora manda."
    L += ["BEGIN:VEVENT", f"UID:{a['id']}@grower-suelo-vivo", f"DTSTAMP:{ahora}",
          f"DTSTART;VALUE=DATE:{d:%Y%m%d}", f"DTEND;VALUE=DATE:{d + dt.timedelta(days=1):%Y%m%d}",
          "SUMMARY:" + esc(pref + titulo), "DESCRIPTION:" + esc(desc), "TRANSP:TRANSPARENT",
          "BEGIN:VALARM", "ACTION:DISPLAY", "DESCRIPTION:" + esc(titulo), "TRIGGER:-PT15H", "END:VALARM", "END:VEVENT"]
L.append("END:VCALENDAR")
open(sys.argv[2], "w", newline="").write("\r\n".join(plegar(l) for l in L) + "\r\n")
print(sum(1 for l in L if l == "BEGIN:VEVENT"), "eventos")
