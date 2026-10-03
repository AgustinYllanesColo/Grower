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
import json, sys, os, math, urllib.request, urllib.parse, datetime as dt

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


def vpd(t, hr):
    """VPD del aire en kPa (Tetens). Hoja al sol suele estar 1-3 °C distinta: esto es el aire."""
    return round(0.6108 * math.exp(17.27 * t / (t + 237.3)) * (1 - hr / 100), 2)


# rangos de VPD por etapa (kPa, aire, de día)
RANGOS = {"plántula": (0.4, 0.8), "vegetativo": (0.8, 1.2), "flor": (1.0, 1.5), "fin de flor": (1.2, 1.6)}


def mmf(x):
    return f"{x:g}".replace(".", ",")


def kpa(x):
    return f"{x:.1f}".replace(".", ",")


def wttr():
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
        # wttr da cada 3 h (0,3,…,21): día = 9-18 h, noche = 0-6 y 21 h
        dia = [h for h in hs if 900 <= int(h["time"]) <= 1800]
        noche = [h for h in hs if int(h["time"]) <= 600 or int(h["time"]) >= 2100]
        vd = [vpd(float(h["tempC"]), float(h["humidity"])) for h in dia] or [0]
        vn = [vpd(float(h["tempC"]), float(h["humidity"])) for h in noche] or [0]
        hrmax = max(int(h["humidity"]) for h in hs)
        txt = (f"lluvia {mmf(mm)} mm" if mm >= 1 else ("chaparrón posible" if prob >= 60 else "seco"))
        if racha >= 40:
            txt += f", ráfagas de {racha} km/h"
        out.append({"d": w["date"], "mm": mm, "tmax": int(w["maxtempC"]), "tmin": int(w["mintempC"]),
                    "hrmin": hrmin, "hrmax": hrmax, "vpd": round(sum(vd) / len(vd), 2), "vpdmax": max(vd),
                    "vpdn": min(vn), "prob": prob, "racha": racha, "obs": False, "txt": txt})
    return out


UA = {"User-Agent": "BitacoraSueloVivo/1.0 github.com/agustinyllanescolo/grower"}
LAT, LON = -34.70, -58.39


def get_json(url, timeout=40):
    return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout))


RESTO_HOY = {}


def metno():
    """MET Norway (modelo ECMWF): temperatura, humedad y lluvia hora a hora. La fuente principal."""
    j = get_json(f"https://api.met.no/weatherapi/locationforecast/2.0/complete?lat={LAT}&lon={LON}")
    dias = {}
    for t in j["properties"]["timeseries"]:
        loc = dt.datetime.fromisoformat(t["time"].replace("Z", "+00:00")).astimezone(TZ)
        d = loc.date().isoformat()
        det = t["data"]["instant"]["details"]
        x = dias.setdefault(d, {"t": [], "h": [], "vd": [], "vn": [], "mm": 0.0, "v": [], "horas": 0})
        T, H = det["air_temperature"], det["relative_humidity"]
        x["t"].append(T); x["h"].append(H); x["v"].append(det.get("wind_speed", 0) * 3.6)
        if 9 <= loc.hour <= 18: x["vd"].append(vpd(T, H))
        if loc.hour >= 21 or loc.hour <= 6: x["vn"].append(vpd(T, H))
        n1, n6 = t["data"].get("next_1_hours"), t["data"].get("next_6_hours")
        if n1:
            x["mm"] += n1["details"].get("precipitation_amount", 0); x["horas"] += 1
        elif n6:
            x["mm"] += n6["details"].get("precipitation_amount", 0); x["horas"] += 6
            for k in ("air_temperature_max", "air_temperature_min"):
                if k in n6["details"]: x["t"].append(n6["details"][k])
    out = {}
    hoy = HOY.isoformat()
    if hoy in dias: RESTO_HOY["mm"] = round(dias[hoy]["mm"], 1)   # lo que falta de hoy, desde la hora actual
    for d, x in dias.items():
        if x["horas"] < 18:          # día incompleto (hoy ya empezado o el último): se completa con otra fuente
            continue
        out[d] = {"tmax": round(max(x["t"]), 1), "tmin": round(min(x["t"]), 1), "hrmin": round(min(x["h"])), "hrmax": round(max(x["h"])),
                  "mm": round(x["mm"], 1), "vpd": round(sum(x["vd"]) / len(x["vd"]), 2) if x["vd"] else None,
                  "vpdmax": max(x["vd"]) if x["vd"] else None, "vpdn": min(x["vn"]) if x["vn"] else None, "viento": round(max(x["v"]))}
    return out


def ensemble():
    """GFS por conjuntos (31 corridas): la PROBABILIDAD de lluvia y el rango de milímetros."""
    j = get_json("https://ensemble-api.open-meteo.com/v1/ensemble?latitude=-34.70&longitude=-58.39&daily=precipitation_sum"
                 "&models=gfs025&timezone=America%2FArgentina%2FBuenos_Aires&forecast_days=10")
    dd = j["daily"]; ks = [k for k in dd if k.startswith("precipitation_sum")]
    out = {}
    for i, d in enumerate(dd["time"]):
        v = sorted(x for x in (dd[k][i] for k in ks) if x is not None)
        if not v: continue
        q = lambda p: round(v[min(len(v) - 1, int(p * len(v)))], 1)
        out[d] = {"prob": round(100 * sum(1 for x in v if x >= 1) / len(v)), "mm_p25": q(0.25), "mm_p50": q(0.5), "mm_p75": q(0.75)}
    return out


def smn_obs(fechas):
    """Observaciones horarias del SMN (Buenos Aires Observatorio): temperatura y humedad MEDIDAS de los días pasados.
    El archivo de cada fecha trae el día anterior, por eso se piden los dos."""
    filas = {}
    pedir = sorted({f for d in fechas for f in (d, (fecha(d) + dt.timedelta(days=1)).isoformat())})
    for d in pedir:
        url = "https://ssl.smn.gob.ar/dpd/descarga_opendata.php?file=observaciones/datohorario" + d.replace("-", "") + ".txt"
        try:
            txt = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=40).read().decode("latin-1")
        except Exception as e:
            print("SMN falló", d, e, file=sys.stderr); continue
        for l in txt.splitlines():
            if "BUENOS AIRES OBSERVATORIO" not in l: continue
            p = l.split()
            try:
                f = f"{p[0][4:8]}-{p[0][2:4]}-{p[0][0:2]}"; h, T, H = int(p[1]), float(p[2]), float(p[3])
            except Exception:
                continue
            filas.setdefault(f, {})[h] = (T, H)
    out = {}
    for f in fechas:
        hs = filas.get(f, {})
        if len(hs) < 20: continue
        T = [v[0] for v in hs.values()]; H = [v[1] for v in hs.values()]
        vd = [vpd(*hs[h]) for h in hs if 9 <= h <= 18]; vn = [vpd(*hs[h]) for h in hs if h >= 21 or h <= 6]
        out[f] = {"tmax": max(T), "tmin": min(T), "hrmin": round(min(H)), "hrmax": round(max(H)),
                  "vpd": round(sum(vd) / len(vd), 2) if vd else None, "vpdmax": max(vd) if vd else None, "vpdn": min(vn) if vn else None}
    return out


def lluvia_pasada():
    """Lluvia de los últimos días según el análisis del modelo (mediana de 31 corridas). No es un pluviómetro."""
    j = get_json("https://ensemble-api.open-meteo.com/v1/ensemble?latitude=-34.70&longitude=-58.39&daily=precipitation_sum"
                 "&models=gfs025&timezone=America%2FArgentina%2FBuenos_Aires&past_days=3&forecast_days=1")
    dd = j["daily"]; ks = [k for k in dd if k.startswith("precipitation_sum")]
    out = {}
    for i, d in enumerate(dd["time"]):
        v = sorted(x for x in (dd[k][i] for k in ks) if x is not None)
        if v and d < HOY.isoformat(): out[d] = round(v[len(v) // 2], 1)
    return out


def pronostico():
    """Une las tres fuentes. MET Norway manda en temperatura, humedad y lluvia; el conjunto da la probabilidad;
    wttr.in aporta las ráfagas y un segundo voto. La confianza sale de cuánto coinciden."""
    fuentes = []
    try: M = metno(); fuentes.append("MET Norway")
    except Exception as e: M = {}; print("met.no falló:", e, file=sys.stderr)
    try: E = ensemble(); fuentes.append("GFS conjunto")
    except Exception as e: E = {}; print("ensemble falló:", e, file=sys.stderr)
    try: W = {w["d"]: w for w in wttr()}; fuentes.append("wttr.in")
    except Exception as e: W = {}; print("wttr falló:", e, file=sys.stderr)
    if not M and not W:
        raise SystemExit("sin fuentes de clima")
    out = []
    for d in sorted(set(M) | set(W)):
        if d < HOY.isoformat(): continue
        m, w, e = M.get(d), W.get(d), E.get(d, {})
        base = dict(m) if m else {k: w[k] for k in ("tmax", "tmin", "hrmin", "hrmax", "mm", "vpd", "vpdmax", "vpdn")}
        if not m and w: base["fuente"] = "wttr.in"
        base.update({k: e[k] for k in ("prob", "mm_p25", "mm_p75") if k in e})
        if w: base["racha"] = w["racha"]; base["mm2"] = w["mm"]
        # confianza: lluvia y temperatura según coincidan las fuentes
        votos = [x for x in (base.get("mm"), e.get("mm_p50"), w["mm"] if w else None) if x is not None]
        llueve = [x >= 2 for x in votos]
        conf = "alta" if len(votos) >= 2 and (all(llueve) or not any(llueve)) else ("media" if len(votos) >= 2 else "baja")
        if w and m and abs(w["tmax"] - m["tmax"]) > 3: conf = "media" if conf == "alta" else "baja"
        if e.get("prob") is not None and 30 <= e["prob"] <= 70 and conf == "alta": conf = "media"
        base["conf"] = conf
        mm = base.get("mm") or 0
        txt = (f"lluvia {mmf(mm)} mm" if mm >= 1 else ("chaparrón posible" if e.get("prob", 0) >= 50 else "seco"))
        if base.get("racha", 0) >= 40: txt += f", ráfagas de {base['racha']} km/h"
        base.update({"d": d, "obs": False, "txt": txt})
        out.append(base)
    return out, " + ".join(fuentes)


def main():
    ck = cargar(sys.argv[1]) if len(sys.argv) > 1 else {}
    clima_prev = cargar(sys.argv[2]) if len(sys.argv) > 2 else {}
    agenda = cargar(sys.argv[3]) if len(sys.argv) > 3 else {}
    fc, fuentes = pronostico()
    # si la probabilidad no llegó hoy, se conserva la de la ronda anterior (máximo 2 días de antigüedad)
    if clima_prev.get("cargado") and (HOY - fecha(clima_prev["cargado"])).days <= 2:
        prev = {d["d"]: d for d in clima_prev.get("dias", [])}
        for d in fc:
            if d.get("prob") is None and prev.get(d["d"], {}).get("prob") is not None:
                for k in ("prob", "mm_p25", "mm_p75"):
                    if k in prev[d["d"]]: d[k] = prev[d["d"]][k]
                d["prob_de"] = clima_prev["cargado"]
    hoy = HOY.isoformat()

    # ---- clima: pasado conservado, pronóstico nuevo ----
    pasados = [d for d in clima_prev.get("dias", []) if d.get("d", "") < hoy][-12:]
    # los días pasados no se quedan con el pronóstico viejo: temperatura y humedad medidas (SMN) y lluvia del análisis
    ultimos = [(HOY - dt.timedelta(days=k)).isoformat() for k in (5, 4, 3, 2, 1)]
    try: obs_t = smn_obs(ultimos)
    except Exception as e: obs_t = {}; print("SMN falló:", e, file=sys.stderr)
    try: llu_p = lluvia_pasada()
    except Exception as e: llu_p = {}; print("lluvia pasada falló:", e, file=sys.stderr)
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import synop
        llu_m = synop.lluvia_medida(ultimos)
    except Exception as e: llu_m = {}; print("SYNOP falló:", e, file=sys.stderr)
    anotada = {e["d"]: e for e in (ck.get("diario") or []) if e.get("a") == "lluvia_mm"}
    por_d = {d["d"]: d for d in pasados}
    for f in ultimos:
        d = dict(por_d.get(f) or {"d": f, "txt": ""})
        if d.get("obs") and d.get("src") == "pluviómetro": continue
        if f in obs_t: d.update(obs_t[f]); d["src_t"] = "SMN medido"
        if f in anotada:
            d["mm"] = float(anotada[f].get("n") or 0); d["obs"] = True; d["src"] = "pluviómetro"
        elif f in llu_m:
            d["mm"] = llu_m[f]["mm"]; d["obs"] = True; d["src"] = "SMN medido"; d["mm_est"] = llu_m[f]["est"]
        elif d.get("src") == "SMN medido":
            pass
        elif f in llu_p:
            d["mm"] = llu_p[f]; d["obs"] = False; d["src"] = "modelo"
        for k in ("prob", "mm_p25", "mm_p75", "mm2", "conf", "racha"): d.pop(k, None)
        d["txt"] = (f"lluvia {mmf(d['mm'])} mm" if (d.get("mm") or 0) >= 1 else "seco")
        por_d[f] = d
    pasados = [por_d[k] for k in sorted(por_d)]
    # hoy: lo que ya cayó (medido) + lo que falta (pronóstico de las próximas horas)
    try: med = synop.lluvia_hoy(hoy)
    except Exception as e: med = None; print("SYNOP hoy falló:", e, file=sys.stderr)
    for d in fc:
        if d["d"] != hoy: continue
        resto = RESTO_HOY.get("mm")
        if med:
            d["mm_med"] = med["mm"]; d["med_hasta"] = med["hasta"]; d["mm_med_est"] = med["est"]
            d["mm_resto"] = resto if resto is not None else 0
            d["mm"] = round(med["mm"] + d["mm_resto"], 1)
            d["txt"] = (f"lluvia {mmf(d['mm'])} mm" if d["mm"] >= 1 else "seco") + (f", ráfagas de {d['racha']} km/h" if d.get("racha", 0) >= 40 else "")
    clima = {"cargado": hoy, "fuente": "Pronóstico: " + fuentes + ". Días pasados: MEDIDOS por el SMN (lluvia: mediana de Observatorio, Aeroparque y Ezeiza; temperatura y humedad: Observatorio). Si anotás tu pluviómetro, manda ese dato.",
             "dias": pasados + fc,
             # lluvia de toda la temporada (no se recorta): {fecha: mm medido}
             "hist": dict(sorted({**(clima_prev.get("hist") or {}), **{d["d"]: d.get("mm", 0) for d in pasados if d.get("obs") or d.get("src") == "SMN medido"}}.items()))}

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
    fechas_pres += [e.get("d") for e in (eventos or {}).values() if isinstance(e, dict) and e.get("estado") == "hecho" and e.get("d")]
    ult_pres = max([x for x in fechas_pres + [agenda.get("presencia")] if x] or [None]) if (fechas_pres or agenda.get("presencia")) else None
    sin_ir = (HOY - fecha(ult_pres)).days if ult_pres else None
    plantulas = [n for n, e in (("tanda 1", t1), ("tanda 2", t2)) if e and e <= 21]
    autos_flor = [n for n, e in (("tanda 1", t1), ("tanda 2", t2)) if e and 35 <= e <= 95]
    autos_final = [n for n, e in (("tanda 1", t1), ("tanda 2", t2)) if e and 70 <= e <= 95]
    toxi_flor = dia_flor_toxi is not None and dia_flor_toxi >= 1
    toxi_final = dia_flor_toxi is not None and dia_flor_toxi >= 50
    etapa = ("fin de flor" if (autos_final or toxi_final) else "flor" if (autos_flor or toxi_flor)
             else "vegetativo" if (toxi_plantada or (t1 and t1 > 21) or (t2 and t2 > 21))
             else "plántula" if plantulas else None)
    # último riego efectivo: riego anotado, lluvia anotada, o ≥8 mm en el clima
    riegos = [e["d"] for e in diario if e.get("a") in ("riego", "riego_b", "riego_m", "lluvia", "lluvia_fuerte", "lluvia_mm")]
    riegos += [d["d"] for d in clima["dias"] if d.get("d", "") <= hoy and d.get("mm", 0) >= 8]
    ult_riego = max(riegos) if riegos else None
    sin_riego = (HOY - fecha(ult_riego)).days if ult_riego else None
    prox = [a for a in agenda.get("items", []) if a.get("due", "9") <= (HOY + dt.timedelta(days=3)).isoformat()]
    prox_ids = " ".join(a["id"] for a in prox)

    # ---- números del pronóstico ----
    llu48 = sum(d["mm"] for d in fc[:2])
    llu72 = sum(d["mm"] for d in fc)
    dia_lluvia = next((d for d in fc if d["mm"] >= 5), None)
    racha = max(fc[:3], key=lambda d: d.get("racha") or 0); racha = dict(racha, racha=racha.get("racha") or 0)
    calor = max(fc, key=lambda d: d["tmax"])
    frio = min(fc, key=lambda d: d["tmin"])
    hr_alta = min(d["hrmin"] for d in fc[:3]) >= 75

    items = []
    def aviso(n, t, d):
        items.append({"n": n, "t": t, "d": d})

    # ---- alertas OFICIALES del SMN que caen sobre Lanús (van primero) ----
    try:
        import alertas_smn
        for al in alertas_smn.alertas():
            ev = al["evento"].lower()
            if "granizo" in ev or "tormenta" in ev: que = "Tutores firmes, cartón de las macetas con peso, ramas sobre el mulch." + (" Techito armado: hay cogollos." if etapa in ("flor", "fin de flor") else "")
            elif "viento" in ev or "zonda" in ev: que = "Tutores firmes y macetas que no se vuelquen; cartón y mulch con peso encima."
            elif "calor" in ev or "temperaturas extremas" in ev: que = "Regá antes de que empiece y sombra a las geotextiles (arpillera): el sustrato negro pasa los 40 °C."
            elif "lluvia" in ev: que = "No riegues; en la próxima visita mirá charcos y que el mulch no se haya lavado."
            elif "frío" in ev or "helada" in ev or "nevada" in ev: que = "Plántulas tapadas de noche (vasito o botella cortada)."
            else: que = "Revisá el cultivo en la próxima visita."
            ini = al["desde"][11:16] + " h " + nombre_dia(al["desde"][:10]) if al["desde"] else ""
            aviso("urg" if al["nivel"] in ("naranja", "roja") else "avi",
                  f"Alerta {al['nivel']} del SMN: {al['evento'].lower()}" + (f" desde las {ini}" if ini else ""), que)
    except Exception as e: print("alertas SMN fallaron:", e, file=sys.stderr)

    if llu48 >= 8:
        aviso("info", f"Lluvia {nombre_dia(dia_lluvia['d'])}: {mmf(dia_lluvia['mm'])} mm",
              "Si hay que regar o no lo decide la tabla de Clima y riego de cada grupo: con semillas o plántulas no se apuesta a la lluvia de mañana, y a una maceta la lluvia casi no le llega.")
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
                aviso("info", f"Día de siembra: {d_siembra['txt']}, {round(d_siembra['tmin'])}-{round(d_siembra['tmax'])} °C",
                      "Con sol y más de 15 °C, cúpula enterrada y sustrato húmedo de antes. Con lluvia fuerte ese día, sembrá igual: la cúpula protege.")

    # ---- VPD: el clima leído como lo lee la planta ----
    if etapa:
        lo, hi = RANGOS[etapa]
        alto = [d for d in fc[:4] if (d.get("vpd") or 0) > hi + 0.6]
        bajo_noche = [d for d in fc[:4] if d.get("vpdn") is not None and d["vpdn"] < 0.15]
        if alto:
            d = max(alto, key=lambda x: x["vpd"])
            aviso("avi", f"VPD alto {nombre_dia(d['d'])}: {kpa(d['vpd'])} kPa de día (ideal en {etapa}: {lo}-{hi})",
                  "El aire tira agua de la hoja más rápido de lo que la raíz la repone: la planta cierra estomas al mediodía y deja de crecer. Suelo húmedo y mulch grueso es lo único que compensa afuera. No es día de topping, LST fuerte ni trasplante.")
        if bajo_noche and etapa in ("flor", "fin de flor") and len(bajo_noche) >= 2:
            aviso("urg", f"Noches saturadas ({len(bajo_noche)} de 4): rocío en los cogollos",
                  "VPD de noche casi 0 = humedad 95-100 %: se condensa agua adentro de la flor. Es el clima de la botrytis. Cogollos por dentro en la próxima visita, defoliar el interior para que circule aire, techito puesto.")
    else:
        lo = hi = None
    # ---- recordatorios de la bitácora ----
    ordenes = riego_motor(sys.argv[1], clima, hoy, sys.argv[3] if len(sys.argv) > 3 else "")
    for g in ordenes:
        o = g.get("orden") or {}
        if o.get("nivel") in ("urg", "avi"):
            aviso(o["nivel"], f"{g['nombre']}: {o['t'].lower()}", o.get("d", ""))
    prox_r = sorted(g["proximo"] for g in ordenes if g.get("proximo"))
    tarea_c = sorted(a["due"] for a in agenda.get("items", []) if a.get("tipo") == "cama" and a.get("due") and a["due"] >= hoy and (eventos.get(a.get("id")) or {}).get("estado") != "hecho")
    cand = [max(hoy, x) for x in (prox_r[:1] + tarea_c[:1])]
    if ult_pres: cand.append(max(hoy, (fecha(ult_pres) + dt.timedelta(days=4)).isoformat()))
    if cand:
        v = min(cand)
        aviso("info", "Próxima visita: " + nombre_dia(v), "El orden, los litros y el tiempo están en «Visita» arriba de todo en la bitácora.")
    if sin_riego is not None and sin_riego >= 4 and not any((g.get("orden") or {}).get("nivel") in ("urg", "avi") for g in ordenes):
        aviso("info", f"Hace {sin_riego} días que no anotás un riego",
              "Si regaste, anotalo: el cálculo del próximo riego parte de ese dato.")
    tocan = [a["n"] for a in prox if a.get("st") in ("toca", "pendiente", "vencida") and a.get("due", "9") <= hoy and (eventos.get(a.get("id")) or {}).get("estado") != "hecho"]
    if tocan:
        aviso("info", f"Tareas para hoy: {len(tocan)}", " · ".join(tocan))

    orden = {"urg": 0, "avi": 1, "info": 2}
    riego_t = tuple(g["nombre"] + ":" for g in ordenes)
    items.sort(key=lambda i: (orden[i["n"]], 0 if i["t"].startswith(riego_t) else 1))
    linea = " · ".join(f"{nombre_dia(d['d'])} {round(d['tmin'])}-{round(d['tmax'])} °C {d['txt']}" + (f", VPD {kpa(d['vpd'])}" if d.get("vpd") is not None else "") for d in fc[:3])
    titulo = items[0]["t"] if items else "Nada que cambie el plan"
    avisos = {"fecha": hoy, "titulo": titulo, "resumen": linea, "items": items, "riego": [{"id": g["id"], "orden": g.get("orden")} for g in ordenes], "etapa": etapa, "rango": [lo, hi] if lo else None}
    os.makedirs("out", exist_ok=True)
    json.dump(clima, open("out/clima.json", "w"), ensure_ascii=False)
    json.dump(avisos, open("out/avisos.json", "w"), ensure_ascii=False)
    urg = [i for i in items if i["n"] == "urg"]
    notificar(items, linea)
    print(("⚠ " if urg else "") + titulo + (f" (+{len(items)-1} avisos)" if len(items) > 1 else "") + ". " + linea)


def riego_motor(ck_path, clima, hoy, agenda_path=""):
    """Corre el mismo motor de riego que usa la página (bitacora/riego.js) con el clima recién armado."""
    import subprocess, tempfile
    js = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "bitacora", "riego.js")
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as t:
        json.dump(clima, t, ensure_ascii=False)
    try:
        r = subprocess.run(["node", js, ck_path, t.name, hoy, "", agenda_path], capture_output=True, text=True, timeout=60)
        return json.loads(r.stdout) if r.returncode == 0 and r.stdout else []
    except Exception as e:
        print("motor de riego falló:", e, file=sys.stderr)
        return []


def notificar(items, linea):
    """Notificación propia de la bitácora vía ntfy (app «ntfy» en el celular, suscripta al tema)."""
    tema = os.environ.get("NTFY_TOPIC")
    if not tema or not items:
        return
    urg = any(i["n"] == "urg" for i in items)
    cuerpo = "\n".join(("⚠ " if i["n"] == "urg" else "• ") + i["t"] for i in items[:5]) + "\n\n" + linea
    req = urllib.request.Request("https://ntfy.sh/" + tema, data=cuerpo.encode(), headers={
        "Title": "Bitácora Suelo Vivo".encode("utf-8").decode("latin-1"),
        "Priority": "high" if urg else "default",
        "Tags": "seedling",
        "Click": "https://claude.ai/artifact/RVpKesdPsPyMQEudSAySMa"})
    try:
        urllib.request.urlopen(req, timeout=20)
    except Exception as e:
        print("ntfy falló:", e, file=sys.stderr)


if __name__ == "__main__":
    main()
