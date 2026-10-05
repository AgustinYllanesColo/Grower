/* Motor de riego de la Bitácora Suelo Vivo.
   Balance de agua día por día para cada «grupo» (bancal, macetas de cada tanda, maceta de la 4ª Toxi):
   agua que se va = ET0 (Hargreaves, FAO-56, ajustada por VPD) × coeficiente de la etapa;
   agua que entra = lluvia (contada con prudencia si es pronóstico) + riegos anotados.
   El dedo corrige: una observación de «Lo vivo» resetea el balance de ese día.
   Lo usan la página (window.Riego) y la ronda automática (node riego.js checklist.json clima.json). */
(function (root) {
  const LAT = -34.70;
  const ET0_MES = [5.6, 4.7, 3.6, 2.4, 1.5, 1.0, 1.1, 1.7, 2.5, 3.4, 4.5, 5.3]; // mm/día típicos de Buenos Aires (ene..dic)
  const RANGO = { "plántula": [0.4, 0.8], "vegetativo": [0.8, 1.2], "flor": [1.0, 1.5], "fin de flor": [1.2, 1.6] };
  const LLUVIA_ANOTADA = { lluvia_poca: 3, lluvia: 10, lluvia_fuerte: 25 };

  const d2 = s => new Date(s + "T12:00:00");
  const iso = d => d.toISOString().slice(0, 10);
  const suma = (s, n) => { const d = d2(s); d.setDate(d.getDate() + n); return iso(d); };
  const entre = (a, b) => Math.round((d2(b) - d2(a)) / 86400000);
  const r1 = x => Math.round(x * 10) / 10;

  function vpd(t, hr) { return 0.6108 * Math.exp(17.27 * t / (t + 237.3)) * (1 - hr / 100); }

  /* radiación extraterrestre en mm/día (FAO-56 ec. 21, ×0,408) */
  function ra(fecha) {
    const d = d2(fecha), inicio = new Date(d.getFullYear(), 0, 0);
    const J = Math.floor((d - inicio) / 86400000), phi = LAT * Math.PI / 180;
    const dr = 1 + 0.033 * Math.cos(2 * Math.PI * J / 365), del = 0.409 * Math.sin(2 * Math.PI * J / 365 - 1.39);
    const ws = Math.acos(-Math.tan(phi) * Math.tan(del));
    return 0.408 * (24 * 60 / Math.PI) * 0.082 * dr * (ws * Math.sin(phi) * Math.sin(del) + Math.cos(phi) * Math.cos(del) * Math.sin(ws));
  }
  /* ET0 del día: Hargreaves con la temperatura; corregida por el VPD real (aire seco evapora más) y por lluvia (nublado) */
  function et0(c, fecha) {
    if (c && c.et0 != null) return c.et0;
    if (!c || c.tmax == null || c.tmin == null) return ET0_MES[d2(fecha).getMonth()];
    const tm = (c.tmax + c.tmin) / 2;
    let e = 0.0023 * ra(fecha) * (tm + 17.8) * Math.sqrt(Math.max(0.5, c.tmax - c.tmin));
    const v = c.vpd != null ? c.vpd : (c.hrmin != null ? vpd(c.tmax, c.hrmin) * 0.8 : null);
    if (v != null) e *= Math.min(1.25, Math.max(0.75, 1 + 0.25 * (v - 1.0)));
    if ((c.mm || 0) >= 5) e *= 0.75;
    return r1(Math.max(0.3, e));
  }
  /* lluvia que cuenta: la medida entera; la pronosticada, con prudencia según su probabilidad */
  function lluviaSegura(c, fecha, hoy) {
    if (!c) return 0;
    const mm = c.mm || 0;
    if (fecha < hoy || c.obs) return mm;
    if (c.mm_med != null) {                  /* hoy: lo medido es seguro; lo que falta, según la probabilidad */
      const r = c.mm_resto || 0, p = c.prob == null ? 60 : c.prob;
      return c.mm_med + (p >= 75 ? r * 0.8 : p >= 50 ? r * 0.4 : 0);
    }
    if (c.prob == null) return mm * 0.6;
    if (c.prob >= 75) return c.mm_p25 != null ? Math.max(c.mm_p25, mm * 0.6) : mm * 0.8;
    if (c.prob >= 50) return mm * 0.4;
    return 0;
  }

  /* ---- qué grupos existen hoy y en qué etapa está cada uno ---- */
  function etapaAuto(d) { return d <= 21 ? "plántula" : d <= 35 ? "vegetativo" : d <= 70 ? "flor" : "fin de flor"; }
  function etapaFoto(dPlant, hoy, flor) {
    if (flor && hoy >= flor) return entre(flor, hoy) >= 50 ? "fin de flor" : "flor";
    return dPlant <= 21 ? "plántula" : "vegetativo";
  }
  function hecho(ev, id) { const e = ev[id]; return e && e.estado === "hecho" && e.d ? e.d : null; }

  function grupos(S) {
    const ev = S.eventos || {}, ta = S.tandas || {}, hoy = S.hoy, G = [];
    const tre = ultimaObs(S.obs, "trebol");
    const pt = hecho(ev, "plantar_toxi");
    let et, kc, awc, txt;
    if (pt) {
      et = etapaFoto(entre(pt, hoy) + 1, hoy, S.flor);
      kc = { "plántula": 0.75, "vegetativo": 0.9, "flor": 1.0, "fin de flor": 0.9 }[et];
      awc = { "plántula": 30, "vegetativo": 40, "flor": 45, "fin de flor": 45 }[et];
      txt = "3 Toxi · " + et;
    } else {
      const v = tre ? tre.v : "asomo";
      if (v === "cubre") { et = "cobertura"; kc = 0.7; awc = 30; txt = "trébol cerrado"; }
      else if (v === "hojas") { et = "cobertura"; kc = 0.55; awc = 14; txt = "trébol con hojas"; }
      /* naciendo: lo que importa son los 2-3 cm de arriba, donde está la semilla: poca reserva y se seca rápido */
      else { et = "cobertura"; kc = 0.6; awc = 6; txt = "trébol naciendo"; }
    }
    G.push({ id: "bancal", nombre: "Bancal", tipo: "suelo", etapa: et, txt: txt, kc: kc, cap: awc, unidad: "mm", n: 1,
             rango: RANGO[et] || null, desde: "2026-09-11", riegos: ["riego", "riego_b"], dedo: "dedo" });
    const maceta = (id, nombre, armada, germ, tipoPlanta, n) => {
      if (!armada) return;
      let et, coef, txt;
      if (!germ || germ > hoy) { et = "cocinando"; coef = 0.12; txt = "tapadas, cocinando"; }
      else {
        const d = entre(germ, hoy) + 1;
        et = tipoPlanta === "auto" ? etapaAuto(d) : etapaFoto(d, hoy, S.flor);
        coef = tipoPlanta === "auto" ? { "plántula": 0.22, "vegetativo": 0.35, "flor": 0.6, "fin de flor": 0.5 }[et]
                                     : { "plántula": 0.25, "vegetativo": 0.55, "flor": 0.8, "fin de flor": 0.7 }[et];
        txt = et + " · día " + d;
      }
      G.push({ id: id, nombre: nombre, tipo: "maceta", etapa: et, txt: txt, coef: coef, cap: 11, unidad: "L", n: n,
               lluviaTapa: S.macetasAlAire ? et === "cocinando" : true,   /* las macetas están bajo techo: la lluvia no les llega */ rango: RANGO[et] || null, desde: armada, riegos: ["riego", "riego_m"], dedo: "mhum",
               siembra: et === "cocinando" && S.siembras && S.siembras[id] ? S.siembras[id] : null });
    };
    maceta("t1", "Macetas tanda 1", hecho(ev, "macetas"), (ta.t1 || {}).f, "auto", 4);
    maceta("toxi4", "Maceta 4ª Toxi", hecho(ev, "armar_toxi4"), pt, "foto", 1);
    maceta("t2", "Macetas tanda 2", hecho(ev, "armar_t2"), (ta.t2 || {}).f, "auto", 2);
    return G;
  }
  function ultimaObs(obs, k) { let m = null; (obs || []).forEach(o => { if (o.k === k && (!m || o.d > m.d)) m = o; }); return m; }

  /* ---- balance de un grupo ---- */
  function balance(g, S) {
    const hoy = S.hoy, dias = {}; (S.clima || []).forEach(c => { dias[c.d] = c; });
    const ultimoClima = (S.clima || []).reduce((m, c) => c.d > m ? c.d : m, hoy);
    const riegos = new Set((S.diario || []).filter(e => g.riegos.includes(e.a)).map(e => e.d));
    /* riego con litros anotados ("20 L", "3,5 L c/u"): resta esa agua; sin litros, se asume que quedó lleno */
    const parcial = {}, lleno = new Set();
    (S.diario || []).filter(e => g.riegos.includes(e.a)).forEach(e => {
      const m = String(e.n || "").match(/^\s*(\d+(?:[.,]\d+)?)\s*L/i);
      if (m && e.a !== "riego") { const L = parseFloat(m[1].replace(",", ".")); parcial[e.d] = (parcial[e.d] || 0) + (g.tipo === "suelo" ? L / 2 : L); }
      else lleno.add(e.d);
    });
    /* el riego a fondo previo a la siembra (guía «Antes de sembrar») también cuenta */
    const pre = g.id === "t1" ? hecho(S.eventos || {}, "papel_t1") : null;
    if (pre && pre <= hoy) { riegos.add(pre); lleno.add(pre); }
    const regar = (def, f) => { if (lleno.has(f)) def = 0; if (parcial[f] != null) def = Math.max(0, def - parcial[f]); return def; };
    const lluAnot = {}; (S.diario || []).forEach(e => { if (LLUVIA_ANOTADA[e.a] != null) lluAnot[e.d] = Math.max(lluAnot[e.d] || 0, LLUVIA_ANOTADA[e.a]); });
    const dedos = {}; (S.obs || []).forEach(o => { if (o.k === g.dedo) dedos[o.d] = o.v; });
    /* pluviómetro propio: manda sobre cualquier otra fuente */
    const pluvio = {}; (S.diario || []).forEach(e => { if (e.a === "lluvia_mm") { const v = parseFloat(String(e.n).replace(",", ".")); if (isFinite(v)) pluvio[e.d] = v; } });
    /* calibración: cada vez que el dedo contradijo al cálculo, el consumo del grupo se corrige */
    const Q = { hum: 0.2, apenas: 0.5, seca: 0.85, secas: 0.6 };
    let kcal = 1, ncal = 0;
    (S.obs || []).filter(o => o.k === g.dedo && o.p != null && Q[o.v] != null).sort((a, b) => a.d < b.d ? -1 : 1)
      .forEach(o => { kcal = Math.min(1.6, Math.max(0.6, kcal * (1 + 0.6 * (Q[o.v] - o.p)))); ncal++; });
    /* ancla: el último dato firme (riego, dedo o armado) */
    const firmes = [...lleno, ...Object.keys(dedos), g.desde].filter(Boolean).filter(d => d <= hoy).sort();
    let ancla = firmes.length ? firmes[firmes.length - 1] : suma(hoy, -7);
    let def = 0, sinDato = !firmes.length;
    if (dedos[ancla]) def = g.cap * ({ hum: 0.2, apenas: 0.5, seca: 0.85, secas: 0.6 }[dedos[ancla]] || 0.3);
    if (ancla < hoy) def = regar(def, ancla);   /* el dedo se mira antes de regar */
    if (sinDato) def = g.cap * 0.5;
    const perdida = (c, f) => { const e = et0(c, f); return (g.tipo === "suelo" ? e * g.kc : e * g.coef) * kcal; };
    const entra = (c, f, segura) => {
      let mm = c ? (segura ? lluviaSegura(c, f, hoy) : (c.mm || 0)) : (lluAnot[f] || 0);
      if (!c && lluAnot[f]) mm = lluAnot[f];
      if (pluvio[f] != null) mm = pluvio[f];
      if (g.tipo === "suelo") return Math.max(0, mm - 1);
      return g.lluviaTapa ? 0 : mm * 0.1;            // una geotextil de 40 L junta ~0,1 L por mm
    };
    /* qué tan confiable es el número: días desde el último dato firme, calibración y origen de la lluvia */
    const conConfianza = r => {
      const firme = [...riegos, ...Object.keys(dedos)].filter(d => d <= hoy).sort().pop();
      const df = firme ? entre(firme, hoy) : 99;
      const hayPluvio = Object.keys(pluvio).some(d => d >= suma(hoy, -7));
      const nivel = df <= 3 && ncal >= 2 ? "alta" : df <= 6 ? "media" : "baja";
      const txt = (df >= 99 ? "sin riegos ni dedo anotados" : "último dato firme hace " + df + (df === 1 ? " día" : " días"))
        + " · " + (ncal ? "calibrado con " + ncal + (ncal === 1 ? " medición" : " mediciones") + " del dedo" : "sin calibrar con tu dedo")
        + " · lluvia medida por el SMN";
      r.confianza = { nivel: nivel, txt: txt, firme: firme || null, dias: df, kcal: Math.round(kcal * 100) / 100, ncal: ncal, pluvio: hayPluvio };
      const p = r.dias.find(x => x.est === "regar" || x.est === "urgente"); r.proximo = p ? p.d : null;
      return r;
    };
    /* pasado: desde el día siguiente al ancla hasta ayer (queda como historia) */
    const hist = [];
    for (let f = suma(ancla, 1); f < hoy; f = suma(f, 1)) {
      const c = dias[f]; const llu = entra(c, f, false);
      def = Math.max(0, def + perdida(c, f) - llu);
      if (dedos[f]) def = g.cap * ({ hum: 0.2, apenas: 0.5, seca: 0.85, secas: 0.6 }[dedos[f]] || 0.3);
      def = regar(def, f);
      def = Math.min(def, g.cap);
      hist.push({ d: f, pct: Math.round(def / g.cap * 100), llu: r1(llu), regado: riegos.has(f) });
    }
    const ultR = [...riegos].filter(d => d <= hoy).sort().pop() || null;
    /* lluvia desde el último riego: días completos medidos + lo que ya cayó hoy; aparte, lo que falta de hoy */
    const cHoy = dias[hoy];
    const medHoy = ultR && ultR < hoy && cHoy ? (cHoy.mm_med != null ? cHoy.mm_med : (pluvio[hoy] != null ? pluvio[hoy] : null)) : null;
    const lluviaDesde = ultR ? r1(hist.filter(h => h.d > ultR).reduce((a, h) => a + (dias[h.d] ? (dias[h.d].mm || 0) : (lluAnot[h.d] || 0)), 0) + (medHoy || 0)) : null;
    const lluviaFalta = cHoy && ultR ? (cHoy.mm_med != null ? (cHoy.mm_resto || 0) : (cHoy.mm || 0)) : null;
    const pico = hist.reduce((m, h) => h.pct > (m ? m.pct : -1) ? h : m, null);
    const resumen = { ultRiego: ultR, diasSin: ultR ? entre(ultR, hoy) : null, lluvia: lluviaDesde, lluviaFalta: lluviaFalta != null ? r1(lluviaFalta) : null, medHasta: cHoy && cHoy.mm_med != null ? cHoy.med_hasta : null, pico: pico ? pico.pct : null, picoD: pico ? pico.d : null };
    /* hoy y lo que viene: decidir */
    const out = [], hoyRegado = riegos.has(hoy);
    if (hoyRegado) def = regar(def, hoy);
    let saturado = false;
    for (let k = 0, f = hoy; f <= ultimoClima && k < 10; k++, f = suma(f, 1)) {
      const c = dias[f], e = perdida(c, f), llu = entra(c, f, true), lluBruta = entra(c, f, false);
      const llu2 = llu + entra(dias[suma(f, 1)], suma(f, 1), true);
      const frac = def / g.cap, fin = Math.min(g.cap, Math.max(0, def + e - llu)), fracFin = fin / g.cap;
      let est = "ok", txt;
      if (f === hoy && hoyRegado) { est = "regado"; txt = "regado hoy"; }
      else if (g.tipo === "suelo" && lluBruta - def > 8) { est = "saturado"; txt = "no regar: sobra agua"; saturado = true; }
      else if (frac >= 0.5 || fracFin >= 0.75) {
        /* semilla o plántula: no se apuesta a la lluvia de mañana, solo a la de hoy */
        const sensible = g.cap <= 8 || g.etapa === "plántula";
        if (g.tipo === "suelo" && ((!sensible && llu2 >= 0.8 * def && frac < 0.75) || llu >= 0.8 * def)) { est = "lluvia"; txt = "no regar: llueve " + r1(llu2) + " mm"; }
        else { est = frac >= 0.75 ? "urgente" : "regar"; txt = frac >= 0.75 ? "regar ya" : "regar"; }
      } else if (frac >= 0.35 || fracFin >= 0.5) { est = "pronto"; txt = "aguanta"; }
      else { txt = "bien"; }
      out.push({ d: f, def: r1(def), pct: Math.round(frac * 100), est: est, txt: txt, et: r1(e), llu: r1(llu), dosis: dosis(g, def) });
      def = (est === "regar" || est === "urgente") ? e * 0.5 : fin;
    }
    /* macetas a punto de sembrarse: se riegan a fondo 1-2 días antes, haga lo que haga el balance */
    /* tapadas y bajo techo, un riego a fondo dura ~5 días: si es más viejo, se riega antes de sembrar */
    const ventana = g.lluviaTapa ? -5 : -2;
    if (g.siembra && entre(hoy, g.siembra) >= 0 && entre(hoy, g.siembra) <= 2 && ![...riegos].some(d => d >= suma(hoy, ventana))) {
      const dd = out.find(x => x.d === suma(g.siembra, -1)) || out[0];
      out.forEach(x => { if (x.d === dd.d) { x.est = "regar"; x.txt = "regar a fondo"; } });
      return conConfianza({ dias: out, hist: hist, resumen: resumen, ancla: ancla, sinDato: sinDato,
               orden: { nivel: "avi", t: dd.d === hoy ? "Regá a fondo hoy" : (entre(hoy, g.siembra) === 2 ? "Regá a fondo hoy o mañana" : "Regá a fondo " + cuando(dd.d, hoy)),
                        d: "Se siembra " + (entre(hoy, g.siembra) <= 1 ? "" : "el ") + cuando(g.siembra, hoy) + ": los 40 L tienen que estar mojados de antes, la semilla va en sustrato húmedo. ≈ 6-8 L por maceta, despacio, hasta que escurra. La lluvia no entra con el cartón." } });
    }
    if (g.siembra && entre(hoy, g.siembra) >= 0 && entre(hoy, g.siembra) <= 1) {
      out.forEach(x => { if (x.d <= g.siembra && (x.est === "regar" || x.est === "urgente")) { x.est = "ok"; x.txt = "bien"; } });
      const ur = [...riegos].filter(d => d <= hoy).sort().pop();
      return conConfianza({ dias: out, hist: hist, resumen: resumen, ancla: ancla, sinDato: sinDato,
               orden: { nivel: "ok", t: g.siembra === hoy ? "Se siembra hoy: sin balde" : "Se siembra mañana: sin balde",
                        d: "Regadas a fondo el " + (ur ? d2(ur).getDate() + "/" + (d2(ur).getMonth() + 1) : "—") + " y tapadas bajo techo: tienen agua. Dedo a 5 cm antes de sembrar: húmedo, se siembra y solo se rocía el centro; seco, 5-7 L por maceta despacio y media hora de espera antes de la semilla." } });
    }
    return conConfianza({ dias: out, hist: hist, resumen: resumen, ancla: ancla, sinDato: sinDato, orden: orden(g, out) });
  }
  function dosis(g, def) {
    if (g.tipo === "suelo" && g.cap <= 8) return "riego suave: 8-10 mm = 16-20 L (2 baldes de 10 L) con regadera o a mano, sin lavar la semilla";
    if (g.tipo === "suelo") { const mm = Math.max(15, Math.min(30, Math.round(def + 5))); return mm + " mm = " + Math.round(mm * 2) + " L (" + Math.ceil(mm * 2 / 10) + " baldes de 10 L) en 2-3 pasadas"; }
    const l = Math.max(3, Math.round(def + 1)); return "≈ " + l + " L por maceta (" + (l >= 10 ? String(Math.round(l / 10 * 10) / 10).replace(".", ",") + " baldes" : l >= 6 ? "casi un balde" : l >= 4 ? "medio balde" : "un cuarto de balde") + "), despacio, hasta que escurra";
  }
  const DIAS_N = ["dom", "lun", "mar", "mié", "jue", "vie", "sáb"];
  function cuando(f, hoy) { const n = entre(hoy, f); return n === 0 ? "hoy" : n === 1 ? "mañana" : DIAS_N[d2(f).getDay()] + " " + d2(f).getDate() + "/" + (d2(f).getMonth() + 1); }
  /* la orden corta: qué hacer y cuándo */
  function orden(g, D) {
    if (!D.length) return null;
    const hoy = D[0].d, r = D.find(x => x.est === "regar" || x.est === "urgente"), l = D.find(x => x.est === "lluvia");
    if (D[0].est === "regado") { const p = D.find(x => x.est === "regar" || x.est === "urgente"); return { nivel: "ok", t: "Regado hoy", d: p ? "Próximo riego: " + cuando(p.d, hoy) + "." : "No vuelve a hacer falta en los próximos días." }; }
    if (D[0].est === "urgente") return { nivel: "urg", t: "Regá hoy", d: "Usó el " + D[0].pct + " % del agua útil. " + D[0].dosis + "." };
    if (D[0].est === "regar") {
      const m = D[1] && D[1].llu >= D[0].def ? D[1] : null;
      return { nivel: "avi", t: "Regá hoy", d: "Usó el " + D[0].pct + " % del agua útil. " + D[0].dosis + "." + (m ? " Si hoy no podés ir, la lluvia de mañana (" + String(m.llu).replace(".", ",") + " mm seguros) lo cubre: con semilla recién nacida conviene no esperar, pero no es grave." : " No viene lluvia que alcance.") };
    }
    if (D[0].est === "lluvia") return { nivel: "info", t: "No riegues: llueve", d: "Viene lluvia que repone lo que falta (" + D[0].pct + " % usado). Si el dedo a 3 cm sale seco igual, regá." };
    if (D[0].est === "saturado") return { nivel: "info", t: "No riegues", d: "Llovió o llueve de más: dejá que escurra." };
    if (r) { const n = entre(hoy, r.d); return { nivel: n <= 1 ? "avi" : "ok", t: n === 1 ? "Regá mañana" : "Próximo riego " + cuando(r.d, hoy), d: (n <= 2 ? "Si vas antes, regá: " : "") + r.dosis + "." }; }
    if (l) return { nivel: "ok", t: "Sin riego a la vista", d: "La lluvia del " + cuando(l.d, hoy) + " cubre lo que se va." };
    return { nivel: "ok", t: "Sin riego a la vista", d: "Aguanta con el agua que tiene hasta donde llega el pronóstico." };
  }

  function plan(S) {
    return grupos(S).map(g => Object.assign({}, g, balance(g, S)));
  }

  const API = { plan: plan, et0: et0, vpd: vpd, RANGO: RANGO, cuando: cuando };
  if (typeof module !== "undefined" && module.exports) module.exports = API;
  else root.Riego = API;

  /* CLI: node riego.js checklist.json clima.json [hoy] [flor] */
  if (typeof require !== "undefined" && typeof module !== "undefined" && require.main === module) {
    const fs = require("fs");
    const ld = p => { const j = JSON.parse(fs.readFileSync(p, "utf8")); return j.data || j; };
    const ck = ld(process.argv[2]), cl = ld(process.argv[3]);
    const hoy = process.argv[4] || new Date(Date.now() - 3 * 3600000).toISOString().slice(0, 10);
    const fl = (ck.eventos && ck.eventos.flor_toxi && ck.eventos.flor_toxi.estado === "hecho" && ck.eventos.flor_toxi.d) || process.argv[5] || "2027-02-01";
    const ag = process.argv[6] && fs.existsSync(process.argv[6]) ? ld(process.argv[6]) : {};
    const sb = {}; (ag.items || []).forEach(a => { if (a.id === "germ_t1") sb.t1 = a.due; if (a.id === "germ_t2") sb.t2 = a.due; });
    const P = plan({ hoy: hoy, flor: fl, tandas: ck.tandas, eventos: ck.eventos, obs: ck.obs, diario: ck.diario, clima: cl.dias, siembras: sb });
    process.stdout.write(JSON.stringify(P.map(g => ({ id: g.id, nombre: g.nombre, etapa: g.etapa, orden: g.orden, proximo: g.proximo, confianza: g.confianza, dias: g.dias.slice(0, 4) }))));
  }
})(typeof window !== "undefined" ? window : this);
