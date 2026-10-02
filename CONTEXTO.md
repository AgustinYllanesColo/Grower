# Grower · Bitácora Suelo Vivo · temporada 26/27 (Lanús)

Contexto para cualquier sesión de Claude que trabaje sobre el cultivo de Tomy.

## Qué es
- **La bitácora**: https://claude.ai/artifact/RVpKesdPsPyMQEudSAySMa, una página privada con base de datos.
  Tomy la usa en su casa, **planificando con un mate**: consulta cuándo regó, qué comprar y qué le toca. **No la usa en el cultivo.**
  Las decisiones se toman en el chat con Claude, y Claude las pasa a la página el mismo día.
- **Código fuente**: `bitacora/index.html`, con las fotos fijas en `bitacora/fotos/`. Para publicar: Artifact publish con
  `url` del artifact, `file_path` bitacora/index.html y `files` fotos/fija1..7.jpg. `bitacora/original.html` es la versión anterior al 29/9, solo de referencia.
- **Base de datos** (se lee y escribe con ArtifactData sobre la URL de arriba):
  - `estado/checklist`: todo lo que carga Tomy (diario, obs, eventos, tandas, inv, fotos, cosecha, extr, borrados…).
    La página hace `set` del documento entero: nunca borrar campos, siempre leer antes y escribir con `if_version`.
  - `estado/clima`: días con {d, mm, tmax, tmin, hrmin, obs, txt}. La página lo usa si `cargado` es igual o posterior al que trae embebido.
  - `estado/avisos`: {fecha, titulo, resumen, items[{n: urg|avi|info, t, d}]}. Se muestra arriba de «Hoy» durante 4 días.
  - `estado/agenda`: la escribe la página cada vez que se abre. Tiene lo que toca en las próximas 3 semanas, el último riego, la última presencia y las tandas.
- **Ronda automática**: `scripts/ronda.py` (wttr.in + reglas deterministas). Corre cada 2 días como Routine. Ver `RONDA.md`.

## Cómo hablarle a Tomy
Crítico, sincero y exigente; nada de elogios. Corregir, enseñar y dar el porqué con números. Castellano rioplatense, de vos.
Regla de la bitácora: **certeza, no dudas**. Lo que no hace falta no va, y lo que va lleva su estado.

## Decisiones vigentes (29/9/26)
- Bancal de 2 m² de suelo vivo, lejos de la casa; visitas cada 3-4 días. Cover crop sembrado el 11/9. Última visita: 21/9.
- **Tanda 1** (autos, siembra directa en geotextiles de 40 L): domingo 4/10. 1 Permanent Jealousy, 1 Pineapple Slush y 2 Doble Tangie. Corte a fines de diciembre.
- **Toxi Watermelon** (fotoperiódica): 4 germinan el 4/10 en casa. Las 3 mejores van al bancal (~25/10, a 70 cm) y la 4ª a una geotextil de 40 L apoyada sobre tierra.
  Flor franca **estimada ~1/2** (fotoperíodo crítico 14-15,5 h, Lanús 34,7° S). Del banco son 60 días; afuera, 60-70.
  **Corte estimado: 1ª quincena de abril.** La bitácora recalcula todo desde el evento `flor_toxi` cuando Tomy lo marca.
- **Tanda 2**: 2 Doble Tangie en 2 geotextiles de 40 L, siembra a mediados de noviembre.
- **Breeder**: 12 Super Lemon Haze regulares en casa, lejos del bancal.
- **Secado: en el ALTILLO.** Medirlo con el termohigrómetro en octubre y en noviembre, y hacer el ensayo de secado. Cajas en el piso y ventilación de noche.
- **Plagas**: Bt kurstaki (Dipel) en flor cada 7-10 días; techito de nylon sobre el bancal desde la semana 3 de flor de las Toxi; cúpula enterrada contra babosas.
- **Registro de cosecha** por planta (húmedo, seco, descarte) y registro de extracciones.
- **Año pasado (línea de base):** 2 plantas en el bancal, ~600 g a 1 kg SECOS por planta (primera pesada >200 g y quedaba más del doble), con botrytis.
- **Extracciones:** Tomy es novato (solo kief del picador). Experimentos guiados: 1) rosin de kief con planchita, 2) rosin de flor. Falta comprar la balanza de 0,01 g.
- **Visitas:** cada 3-4 días con imprevistos. Diseñar para la ausencia (40 L, mulch, recordatorios de riego).
- **Lluvia de días pasados: MEDIDA** (SYNOP del SMN vía Ogimet: Observatorio, Aeroparque, Ezeiza; mediana) en scripts/synop.py. Pluviómetro propio manda si existe.
- **Clima = aliado:** VPD en kPa de día (9-18 h) y de noche en la tabla «Clima y VPD». Rangos de día: plántula 0,4-0,8 · vegetativo 0,8-1,2 · flor 1,0-1,5 · fin de flor 1,2-1,6. Noche <0,15 = rocío. Secado: 0,6-0,9 adentro de la caja; curado 58-62 % en el frasco.
- **Notificaciones propias:** app ntfy, suscripta al tema que está en la Routine «Ronda Suelo Vivo» (trig_01QU2vywp6rGJqJrsxJpUsNV). Lo que Tomy quiere a futuro: una app de verdad (PWA con push).
- Agua: de lluvia como principal; ácido ascórbico en polvo de respaldo.
- Nada de lombricario. Nada de freezer ni heladera para secar.
