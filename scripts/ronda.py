#!/usr/bin/env python3
"""Ronda automática de la Bitácora Suelo Vivo.

Trae el pronóstico de Lanús (wttr.in), lo cruza con el estado del cultivo que la
bitácora guarda en su base (estado/checklist y estado/agenda) y escribe:
  out/clima.json   -> documento estado/clima (lo que la página usa para el riego)
  out/avisos.json  -> documento estado/avisos (las consecuencias, arriba de «Hoy»)
e imprime un resumen corto para la notificación.

Uso:
  python3 scripts/ronda.py <checklist.json> <clima.json> [agenda.json]
Los .json son los que deja ArtifactData con out_dir (con o sin envoltorio "data").
Todas las reglas son deterministas: el modelo solo mueve archivos.
"""
import json, sys, os, urllib.request, datetime as dt

LAT_LON = "Lanus,Argentina"
TZ = dt.timezone(dt.timedelta(hours=-3))
HOY = dt.datetime.now(TZ).date()
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


def cargar(path):
    if not path or not os.path.exists(path):
        return {}
    d = json.load(open(path))
    return d.get("data", d) if isinstance(d, dict) else {}


def fecha(s):
    return dt.date.fromisoformat(s)


def nombre_dia(s):
    f = fecha(s)
    if f == HOY:
        return "hoy"
    if f == HOY + dt.timedelta(days=1):
        return "mañana"
    return f"el {DIAS[f.weekday()]} {f.day}/{f.month}"


def pronostico():
    url = f"https://wttr.in/{LAT_LON}?format=j1&lang=es"
    req = urllib.request.Request(url, headers={"User-Agent": "curl/8"})
    j = json.load(urllib.request.urlopen(req, timeout=40))
    out = []
    for w in j["weather"]:
        hs = w["hourly"]
        mm = round(sum(float(h["precipMM"]) for h in hs), 1)
        racha = max(int(h["WindGustKmph"]) for h in hs)
        prob = max(int(h["chanceofrain"]) for h in hs)
        hrmin = min(int(h["humidity"]) for h in hs)
        txt = (f"lluvia {mm:g} mm" if mm >= 1 else ("chaparrón posible" if prob >= 60 else "seco"))
        if racha >= 40:
            txt += f", ráfagas de {racha} km/h"
        out.append({"d": w["date"], "mm": mm, "tmax": int(w["maxtempC"]), "tmin": int(w["mintempC"]),
                    "hrmin": hrmin, "prob": prob, "racha": racha, "obs": False, "txt": txt})
    return out


def main():
    ck = cargar(sys.argv[1]) if len(sys.argv) > 1 else {}
    clima_prev = cargar(sys.argv[2]) if len(sys.argv) > 2 else {}
    agenda = cargar(sys.argv[3]) if len(sys.argv) > 3 else {}
    fc = pronostico()
    hoy = HOY.isoformat()

    # ---- clima: pasado conservado, pronóstico nuevo ----
    pasados = [d for d in clima_prev.get("dias", []) if d.get("d", "") < hoy][-10:]
    clima = {"cargado": hoy, "fuente": "Registrado: estación MeteoLanus / lo anotado. Pronóstico: wttr.in Lanús (ronda automática).",
             "dias": pasados + [{k: v for k, v in d.items() if k not in ("prob", "racha")} for d in fc]}
    # el pronóstico largo anterior (Meteored u otro) se conserva más allá de los 3 días de wttr, si es reciente
    if clima_prev.get("cargado") and (HOY - fecha(clima_prev["cargado"])).days <= 3:
        clima["dias"] += [d for d in clima_prev.get("dias", []) if d.get("d", "") > fc[-1]["d"]]

    # ---- estado del cultivo ----
    tandas = ck.get("tandas", {}) or {}
    eventos = ck.get("eventos", {}) or {}
    diario = ck.get("diario", []) or []

    def edad(tid):
        f = (tandas.get(tid) or {}).get("f")
        return (HOY - fecha(f)).days + 1 if f else None

    t1, t2 = edad("t1"), edad("t2")
    pt = (eventos.get("plantar_toxi") or {})
    toxi_plantada = pt.get("estado") == "hecho"
    ft = (eventos.get("flor_toxi") or {})
    flor_toxi = fecha(ft["d"]) if ft.get("estado") == "hecho" and ft.get("d") else None
    dia_flor_toxi = (HOY - flor_toxi).days + 1 if flor_toxi else None
    fechas_pres = [e["d"] for e in diario if e.get("a") not in ("lluvia", "lluvia_poca", "lluvia_fuerte")]
    fechas_pres += [o.get("d") for o in ck.get("obs", []) if o.get("d")]
    ult_pres = agenda.get("presencia") or (max(fechas_pres) if fechas_pres else None)
    sin_ir = (HOY - fecha(ult_pres)).days if ult_pres else None
    plantulas = [n for n, e in (("tanda 1", t1), ("tanda 2", t2)) if e and e <= 21]
    autos_flor = [n for n, e in (("tanda 1", t1), ("tanda 2", t2)) if e and 35 <= e <= 95]
    autos_final = [n for n, e in (("tanda 1", t1), ("tanda 2", t2)) if e and 70 <= e <= 95]
    toxi_flor = dia_flor_toxi is not None and dia_flor_toxi >= 1
    toxi_final = dia_flor_toxi is not None and dia_flor_toxi >= 50
    prox = [a for a in agenda.get("items", []) if a.get("due", "9") <= (HOY + dt.timedelta(days=3)).isoformat()]
    prox_ids = " ".join(a["id"] for a in prox)

    # ---- números del pronóstico ----
    llu48 = sum(d["mm"] for d in fc[:2])
    llu72 = sum(d["mm"] for d in fc)
    dia_lluvia = next((d for d in fc if d["mm"] >= 5), None)
    racha = max(fc, key=lambda d: d["racha"])
    calor = max(fc, key=lambda d: d["tmax"])
    frio = min(fc, key=lambda d: d["tmin"])
    hr_alta = min(d["hrmin"] for d in fc) >= 75

    items = []
    def aviso(n, t, d):
        items.append({"n": n, "t": t, "d": d})

    if llu48 >= 8:
        aviso("avi", f"No riegues: vienen {llu48:g} mm en 48 h",
              f"Lluvia fuerte {nombre_dia(dia_lluvia['d'])}. Aunque la bitácora marque riego, esa lluvia es el riego del bancal. Las macetas tapadas con cartón no reciben casi nada: esas sí se revisan con el dedo.")
        if any(k in prox_ids for k in ("borra", "humus_td", "bok_", "pescado", "plantar_toxi", "preflor")):
            aviso("info", "Aprovechá la lluvia para los aportes",
                  "Borra, humus, bokashi, pescado o trasplante van ANTES de una lluvia normal: la lluvia los incorpora sin que riegues. Después de una tormenta, esperá a que escurra.")
    elif 3 <= llu72 < 8:
        aviso("info", f"Lluvia chica en 3 días ({llu72:g} mm)",
              "No alcanza como riego profundo: si el dedo a 3 cm sale seco, regá igual.")
    if racha["racha"] >= 50:
        aviso("urg", f"Ráfagas de {racha['racha']} km/h {nombre_dia(racha['d'])}",
              "Antes: tutores firmes y atados, ramas cruzadas sobre la cama, cartón de las macetas con piedra encima"
              + (", amarres del techito" if toxi_flor else "")
              + (". Una planta quebrada no se recupera." if (t1 or t2 or toxi_plantada) else "."))
    elif racha["racha"] >= 40:
        aviso("avi", f"Viento fuerte {nombre_dia(racha['d'])} ({racha['racha']} km/h)",
              "Revisá tutores y ataduras en la próxima visita; lo que esté flojo, atalo antes.")
    if calor["tmax"] >= 30 and llu72 < 5:
        dias_txt = f" Hace {sin_ir} días que no pasa nadie: andá antes del calor." if sin_ir and sin_ir >= 3 else ""
        aviso("urg" if (plantulas or (sin_ir and sin_ir >= 4)) else "avi",
              f"Calor seco: {calor['tmax']} °C {nombre_dia(calor['d'])}",
              "Con calor y sin lluvia, una geotextil de 40 L se seca en 2-3 días y el bancal pierde la superficie." + dias_txt
              + (" Plántulas: la cúpula con agujeros y a la sombra al mediodía, o se cocinan." if plantulas else ""))
    if frio["tmin"] <= 5 and plantulas:
        aviso("avi", f"Noche fría ({frio['tmin']} °C) con plántulas",
              "Cúpula puesta esa noche. Una auto frenada por frío pierde días que no recupera.")
    if plantulas and llu48 >= 5:
        aviso("avi", "Después de la lluvia salen las babosas",
              "Cúpulas enterradas 1-2 cm; revisá la trampa o la tablita en la visita.")
    if (autos_flor or toxi_flor) and (llu72 >= 5 or hr_alta):
        quien = ", ".join(autos_flor + (["Toxi"] if toxi_flor else []))
        aviso("avi", f"Humedad en flor ({quien})",
              "Próxima visita: abrir cogollos por dentro y Bt DESPUÉS de la lluvia (la lluvia lo lava)."
              + (" Techito puesto antes de que llueva." if toxi_flor else "")
              + (" Macetas bajo techo si se puede." if autos_flor else ""))
    if (autos_final or toxi_final) and llu72 >= 10:
        aviso("urg", "Lluvia con cosecha cerca",
              "Si los tricomas ya están en 70 % lechosos, se corta ANTES de la lluvia: una semana más mojada vale menos que el engorde. Las autos, bajo techo.")
    if sin_ir is not None and sin_ir >= 6:
        aviso("avi", f"Hace {sin_ir} días que nadie va a la cama",
              "El plan es cada 3-4 días. Con este clima, la próxima visita no es opcional.")
    for a in prox:
        if a.get("id", "").startswith("foliar") and llu48 >= 3:
            aviso("info", f"«{a['n']}»: posponelo",
                  "Un foliar antes de la lluvia se lava. Va al atardecer de un día seco.")
        if a.get("id", "").startswith("germ_t1") or a.get("id", "") == "germ_t2":
            d_siembra = next((d for d in fc if d["d"] == a.get("due")), None)
            if d_siembra:
                aviso("info", f"Día de siembra: {d_siembra['txt']}, {d_siembra['tmin']}-{d_siembra['tmax']} °C",
                      "Con sol y más de 15 °C, cúpula enterrada y sustrato húmedo de antes. Con lluvia fuerte ese día, sembrá igual: la cúpula protege.")

    orden = {"urg": 0, "avi": 1, "info": 2}
    items.sort(key=lambda i: orden[i["n"]])
    linea = " · ".join(f"{nombre_dia(d['d'])} {d['tmin']}-{d['tmax']} °C {d['txt']}" for d in fc)
    titulo = items[0]["t"] if items else "Nada que cambie el plan"
    avisos = {"fecha": hoy, "titulo": titulo, "resumen": linea, "items": items}
    os.makedirs("out", exist_ok=True)
    json.dump(clima, open("out/clima.json", "w"), ensure_ascii=False)
    json.dump(avisos, open("out/avisos.json", "w"), ensure_ascii=False)
    urg = [i for i in items if i["n"] == "urg"]
    print(("⚠ " if urg else "") + titulo + (f" (+{len(items)-1} avisos)" if len(items) > 1 else "") + ". " + linea)


if __name__ == "__main__":
    main()
