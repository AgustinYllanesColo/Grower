"""Semáforo de acciones: GO / NO GO antes de cada acción irreversible, con reglas fijas.

La lección del 6/10 (tanda 1 sembrada directo con 16-19 °C de máxima y 29 mm: nada germinó) se paga una sola vez.
Las reglas viven acá, no en el criterio de la sesión. Lo corre la ronda cada 2 días (avisos urg) y Claude
lo corre en el chat ANTES de confirmar cualquier acción (ver PROTOCOLOS.md).

  python3 scripts/semaforo.py <clima.json> [agenda.json]      -> evalúa las acciones de los próximos 7 días
  python3 scripts/semaforo.py <clima.json> --accion germ      -> evalúa una acción puntual (germ, plantar, topping, cupula, cover, cosecha)
"""
import json, sys, datetime as dt

HOY = dt.date.today()

# Reglas por familia de acción. Cada regla mira el pronóstico desde el día de la acción (o hoy) hacia adelante.
#   dias: cuántos días de pronóstico mira · tmin/tmax: pisos y techos · mm: lluvia máxima aceptada en esos días
#   porque: el motivo que se le dice a Tomy · si_no: qué hacer en cambio
REGLAS = {
    "germ": dict(nombre="Germinar / sembrar afuera", dias=5, tmin_min=13, tmax_min=20, mm_max=25, racha_max=None, vpd_max=None,
                 porque="La semilla germina a 22-26 °C de suelo. Con máximas <20 °C o noches <13 °C el sustrato queda a 12-15 °C: tarda 2 semanas o se pudre, y con lluvia encima se pudre seguro.",
                 si_no="Germinar ADENTRO: papel de cocina húmedo entre dos platos a 22-25 °C (arriba de la heladera). Con la raíz de 0,5-1 cm, plantar brotada a 1 cm en la maceta, con cúpula, mojando solo el centro."),
    "plantar": dict(nombre="Trasplantar al bancal / a la maceta", dias=3, tmin_min=10, tmax_min=None, mm_max=20, racha_max=50, vpd_max=1.8,
                    porque="Una plántula recién movida no tiene raíz para aguantar frío, un temporal ni aire seco. Se queda chiquita 10 días o se pierde.",
                    si_no="Esperar en el vasito en casa. Si ya está muy grande para el vasito, pasarla a uno de 1 L y seguir esperando la ventana."),
    "topping": dict(nombre="Topping / poda / LST fuerte", dias=2, tmin_min=8, tmax_min=None, mm_max=15, racha_max=None, vpd_max=1.8,
                    porque="El corte es una herida abierta: con lluvia encima entra hongo; con VPD alto la planta ya está estresada y se frena 1 semana más.",
                    si_no="Posponer 2-3 días; no cambia nada en el calendario."),
    "cupula": dict(nombre="Sacar la cúpula a las plántulas", dias=3, tmin_min=10, tmax_min=None, mm_max=None, racha_max=45, vpd_max=1.5,
                   porque="La cúpula es el único reparo de la plántula contra noches frías, ráfagas y aire seco.",
                   si_no="Dejarla, pero ventilada (sin tapa) y sacarla solo de día si hace más de 28 °C."),
    "cover": dict(nombre="Sembrar cover crop / resiembra del bancal", dias=5, tmin_min=6, tmax_min=14, mm_max=40, racha_max=None, vpd_max=None,
                  porque="Las legumbres germinan desde 8 °C, pero necesitan el suelo húmedo 5 días seguidos y Tomy va cada 3-4.",
                  si_no="Sembrar el día antes de una lluvia moderada o regar y tapar con cartón 4 días."),
    "cosecha": dict(nombre="Cortar", dias=2, tmin_min=None, tmax_min=None, mm_max=5, racha_max=None, vpd_max=None,
                    porque="Cortar con cogollos mojados o con lluvia encima es llevar botrytis al secado.",
                    si_no="Esperar 2 días de seco; si hay lluvia anunciada, cortar ANTES, no después."),
}
# qué id de la agenda cae en qué familia
# (el orden importa: lo específico antes que lo genérico)
FAMILIA = [("resiembra", "cover"), ("cover", "cover"), ("germ_", "germ"), ("siembra", "germ"), ("plantar_", "plantar"), ("trasplante", "plantar"),
           ("topping", "topping"), ("poda", "topping"), ("lst_", "topping"), ("cup_", "cupula"), ("cosecha", "cosecha"), ("corte", "cosecha")]


def familia(aid):
    aid = (aid or "").lower()
    return next((f for p, f in FAMILIA if p in aid), None)


def evaluar(fam, dias, desde=None):
    """Devuelve (ok, motivos[]) para la familia con los días de pronóstico (lista de dicts d,tmin,tmax,mm,racha,vpd)."""
    r = REGLAS[fam]
    desde = desde or HOY.isoformat()
    ventana = [d for d in dias if d.get("d", "") >= desde and not d.get("obs")][:r["dias"]]
    if len(ventana) < min(2, r["dias"]):
        return None, [f"sin pronóstico suficiente desde {desde}"]
    malos = []
    if r["tmin_min"] is not None:
        f = [d for d in ventana if d.get("tmin") is not None and d["tmin"] < r["tmin_min"]]
        if f: malos.append(f"noches de {min(d['tmin'] for d in f):.1f} °C ({len(f)} de {len(ventana)} días; piso {r['tmin_min']} °C)")
    if r["tmax_min"] is not None:
        f = [d for d in ventana if d.get("tmax") is not None and d["tmax"] < r["tmax_min"]]
        if f: malos.append(f"máximas de {round(min(d['tmax'] for d in f))}-{round(max(d['tmax'] for d in f))} °C ({len(f)} de {len(ventana)} días; piso {r['tmax_min']} °C)")
    if r["mm_max"] is not None:
        mm = sum(d.get("mm") or 0 for d in ventana)
        if mm > r["mm_max"]: malos.append(f"{round(mm)} mm de lluvia en {len(ventana)} días (tope {r['mm_max']})")
    if r["racha_max"] is not None:
        f = [d for d in ventana if (d.get("racha") or 0) >= r["racha_max"]]
        if f: malos.append(f"ráfagas de {max(d['racha'] for d in f)} km/h")
    if r["vpd_max"] is not None:
        f = [d for d in ventana if (d.get("vpd") or 0) > r["vpd_max"]]
        if f: malos.append(f"VPD de {max(d['vpd'] for d in f):.1f} kPa (tope {r['vpd_max']})")
    return (not malos), malos


def texto(fam, ok, motivos, que=""):
    r = REGLAS[fam]
    n = que or r["nombre"]
    if ok is None: return "avi", f"{n}: sin semáforo ({motivos[0]})", "No hay pronóstico para evaluarlo. No se hace hasta tenerlo."
    if ok: return "info", f"{n}: luz VERDE", f"Pronóstico dentro de los parámetros ({r['dias']} días)."
    return "urg", f"NO: {n}. " + "; ".join(motivos), r["porque"] + " QUÉ HACER: " + r["si_no"]


def avisos_agenda(agenda, dias, eventos=None, horizonte=7):
    """Para la ronda: una lista de avisos {n,t,d} por cada acción irreversible de la agenda en los próximos días."""
    eventos = eventos or {}
    out = []
    lim = (HOY + dt.timedelta(days=horizonte)).isoformat()
    for a in agenda.get("items", []):
        fam = familia(a.get("id"))
        # compras no se evalúan; lo que se hace en casa (vasitos adentro) tampoco: ahí el clima lo pone Tomy
        if a.get("tipo") in ("compra", "casa"): continue
        if not fam or (eventos.get(a.get("id")) or {}).get("estado") == "hecho": continue
        due = a.get("due") or "9"
        if due > lim: continue
        ok, motivos = evaluar(fam, dias, max(due, HOY.isoformat()))
        if ok: continue  # verde no hace ruido en la ronda; rojo y "sin pronóstico" sí
        n, t, d = texto(fam, ok, motivos, a.get("n"))
        out.append({"n": n, "t": t, "d": d})
    return out


if __name__ == "__main__":
    clima = json.load(open(sys.argv[1]))
    dias = clima.get("dias") or clima
    if "--accion" in sys.argv:
        fam = sys.argv[sys.argv.index("--accion") + 1]
        desde = sys.argv[sys.argv.index("--desde") + 1] if "--desde" in sys.argv else None
        ok, motivos = evaluar(fam, dias, desde)
        n, t, d = texto(fam, ok, motivos)
        print(f"[{n}] {t}\n{d}")
        sys.exit(0 if ok else 1)
    agenda = json.load(open(sys.argv[2])) if len(sys.argv) > 2 else {"items": []}
    for av in avisos_agenda(agenda, dias):
        print(f"[{av['n']}] {av['t']}\n   {av['d']}")
