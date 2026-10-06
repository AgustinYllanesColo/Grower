# Grower · Bitácora Suelo Vivo · temporada 26/27 (Lanús)

Contexto para cualquier sesión de Claude que trabaje sobre el cultivo de Tomy.

## Qué es
- **La bitácora**: https://claude.ai/artifact/RVpKesdPsPyMQEudSAySMa, una página privada con base de datos.
  Tomy la usa en su casa, **planificando con un mate**: consulta cuándo regó, qué comprar y qué le toca. **No la usa en el cultivo.**
  Las decisiones se toman en el chat con Claude, y Claude las pasa a la página el mismo día.
- **Código fuente**: `bitacora/index.html`, con las fotos fijas en `bitacora/fotos/`. Para publicar: Artifact publish con
  `url` del artifact, `file_path` bitacora/index.html y `files` riego.js y fotos/fija1..17.jpg. `bitacora/original.html` es la versión anterior al 29/9, solo de referencia.
- **Base de datos** (se lee y escribe con ArtifactData sobre la URL de arriba):
  - `estado/checklist`: todo lo que carga Tomy (diario, obs, eventos, tandas, inv, fotos, cosecha, extr, borrados…).
    La página hace `set` del documento entero: nunca borrar campos, siempre leer antes y escribir con `if_version`.
  - `estado/clima`: días con {d, mm, tmax, tmin, hrmin, obs, txt}. La página lo usa si `cargado` es igual o posterior al que trae embebido.
  - `estado/avisos`: {fecha, titulo, resumen, items[{n: urg|avi|info, t, d}]}. Se muestra arriba de «Hoy» durante 4 días.
  - `estado/agenda`: la escribe la página cada vez que se abre. Tiene lo que toca en las próximas 3 semanas, el último riego, la última presencia y las tandas.
- **Ronda automática**: `scripts/ronda.py` (wttr.in + reglas deterministas). Corre cada 2 días como Routine. Ver `RONDA.md`.

## Registro
**Tomy NO anota en la bitácora: anota Claude desde el chat** (riegos con litros en `n`, p. ej. «20 L» o «3,5 L c/u»; dedo con `p` = lo que predecía el cálculo; notas). Su balde es de **10 L**. **Toda foto que pase va a la galería sin preguntar** (fotos/fijaN.jpg, 900 px, en FOTOS_FIJAS con fecha, sujeto y pie de foto).

**Ficha por planta** (pestaña Plantas): Claude anota en `checklist.plantas[ID]` (IDs: PJ-1, PS-1, DT-1..4, TW-1..4, SLH):
`alt: [{d, cm}]` altura, `ev: [{d, t}]` lo que se le hizo (LST, topping, plaga…), `germ` si germinó otro día que su tanda,
`estado: "descartada"` + `motivo`, `nota`; para SLH `machos`/`hembras`. Siempre con `t: Date.now()` (gana el más nuevo). Fotos de una planta: campo `p: ID` en FOTOS_FIJAS.
**Calendario del iPhone**: `scripts/calendario.py` arma `calendario/temporada-26-27.ics` (UID = id de la acción). Si las fechas cambian mucho, regenerarlo y mandárselo.
**Alertas oficiales SMN**: `scripts/alertas_smn.py` (CAP público, polígono que contiene Lanús) entra en la ronda diaria.

## Cómo hablarle a Tomy
Crítico, sincero y exigente; nada de elogios. Corregir, enseñar y dar el porqué con números. Castellano rioplatense, de vos.
Regla de la bitácora: **certeza, no dudas**. **Claude mantiene la bitácora (fechas, tabla de riego, avisos) al día con lo que se dice en el chat SIN que Tomy lo pida.** Lo que no hace falta no va, y lo que va lleva su estado.

## Objetivo de calidad (6/10)
Tomy mandó fotos de referencia (I+D, línea Athena, interior): cogollos densos, escarcha total, pistilos naranjas, violeta en las hojitas.
Eso es lo que busca. Palancas en orden: genética + selección (PJ la más cercana; clonar la mejor Toxi; breeder SLH) · luz en cada cola (LST/topping, limpiar el tercio de abajo)
· sin N de más en flor · corte por tricomas · secado lento 10-14 días y manicurado. Color solo con genética + noches <15 °C. Afuera en BA, denso = botrytis: estructura abierta, Bt, techito, corte a tiempo.

## Decisiones vigentes (29/9/26, germinación corrida el 5/10)
- Bancal de 2 m² de suelo vivo, lejos de la casa; visitas cada 3-4 días. Cover crop sembrado el 11/9. Última visita: 21/9.
- **Tanda 1** (autos, siembra directa en geotextiles de 40 L): iba el domingo 4/10 y NO se hizo. Siembra DIRECTA sin papel en las macetas el martes 6/10 (se corrió dos veces: 4/10 y 5/10). Color en la manija: rojo PJ-1, amarillo PS-1, azul DT-1, verde DT-2. 1 Permanent Jealousy, 1 Pineapple Slush y 2 Doble Tangie. Corte a fines de diciembre.
- **Toxi Watermelon** (fotoperiódica): 3 sembradas el 6/10 directo en vasitos (la 4ª semilla de reserva). Las 3 mejores van al bancal (~25/10, a 70 cm) y la 4ª a una geotextil de 40 L apoyada sobre tierra.
  Flor franca **estimada ~1/2** (fotoperíodo crítico 14-15,5 h, Lanús 34,7° S). Del banco son 60 días; afuera, 60-70.
  **Corte estimado: 1ª quincena de abril.** La bitácora recalcula todo desde el evento `flor_toxi` cuando Tomy lo marca.
- **Tanda 2**: 2 Doble Tangie en 2 geotextiles de 40 L, siembra a mediados de noviembre.
- **Breeder**: 12 Super Lemon Haze regulares en casa, lejos del bancal. TODO en vasitos de 500 ml, sin comprar nada (observación, aprendizaje, selección). Siembra 20/11-1/12; sexado en enero; polen y una rama de la mejor SLH hembra en febrero, en casa.
- **Secado: en el ALTILLO.** Medirlo con el termohigrómetro en octubre y en noviembre, y hacer el ensayo de secado. Cajas en el piso y ventilación de noche.
- **Plagas**: Bt kurstaki (Dipel) en flor cada 7-10 días; techito de nylon sobre el bancal desde la semana 3 de flor de las Toxi; cúpula enterrada contra babosas.
- **Registro de cosecha** por planta (húmedo, seco, descarte) y registro de extracciones.
- **Año pasado (línea de base):** 2 plantas en el bancal, ~600 g a 1 kg SECOS por planta (primera pesada >200 g y quedaba más del doble), con botrytis.
- **Extracciones:** Tomy es novato (solo kief del picador). Experimentos guiados: 1) rosin de kief con planchita, 2) rosin de flor. Falta comprar la balanza de 0,01 g.
- **Visitas:** cada 3-4 días con imprevistos. Diseñar para la ausencia (40 L, mulch, recordatorios de riego).
- **Lluvia de días pasados: MEDIDA** (SYNOP del SMN vía Ogimet: Observatorio, Aeroparque, Ezeiza; mediana) en scripts/synop.py. Tomy no va a tener pluviómetro. Macetas BAJO TECHO: la lluvia no les llega.
- **Clima = aliado:** VPD en kPa de día (9-18 h) y de noche en la tabla «Clima y VPD». Rangos de día: plántula 0,4-0,8 · vegetativo 0,8-1,2 · flor 1,0-1,5 · fin de flor 1,2-1,6. Noche <0,15 = rocío. Secado: 0,6-0,9 adentro de la caja; curado 58-62 % en el frasco.
- **Notificaciones propias:** app ntfy, suscripta al tema que está en la Routine «Ronda Suelo Vivo» (trig_01QU2vywp6rGJqJrsxJpUsNV). Lo que Tomy quiere a futuro: una app de verdad (PWA con push).
- Agua: por ahora canilla batida y reposada (no puede dejar baldes de lluvia); Vitamina C NO se consigue: el agua se trata con jugo de 1 limón por balde de 10 L. Ascórbico en polvo solo si aparece.
- Borra de café: va al bancal, finita bajo el mulch y mezclada con cartón (hasta 5 L por mes). En las macetas no, hasta que las plantas tengan 4 semanas. Se guarda abierta. Lista «Para juntar» en Compras.
- Nada de lombricario. Nada de freezer ni heladera para secar.
- **5/10: sin compras por ahora.** La compra grande se decide a fin de octubre y solo si hay tanda 2. La 4ª Toxi queda de reserva en bolsa de rafia en casa.
- **Trébol falló (se secó).** No se compra más trébol: resiembra de claros con lentejas o arvejas del almacén a 2-3 cm (aguantan visitas cada 3-4 días). Las Toxi no esperan al cover: van con 2-3 pares de hojas.
- Azúcar rubia: hay. IMO y LAB arrancan el 5-6/10 con el mismo arroz.
