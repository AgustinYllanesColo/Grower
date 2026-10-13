# Protocolos · parámetros GO / NO GO por acción

Fuente de verdad: `scripts/semaforo.py` (el código manda; este archivo lo explica). La ronda lo corre cada 2 días sobre la agenda
y manda «NO» por ntfy antes de la fecha de cada acción. En el chat, antes de confirmar cualquier acción, Claude corre:

    python3 scripts/semaforo.py <clima.json> --accion <germ|plantar|topping|cupula|cover|cosecha> [--desde AAAA-MM-DD]

y pega el resultado en la respuesta. Rojo = no se hace, y se dice qué hacer en cambio. Sin pronóstico = tampoco se hace.

| Acción | Mira | Pisos / topes | Por qué |
|---|---|---|---|
| Germinar / sembrar afuera | 5 días | noches ≥ 13 °C · máximas ≥ 20 °C · ≤ 25 mm | Semilla: 22-26 °C de suelo. Afuera con menos, el sustrato queda a 12-15 °C: tarda o se pudre. Alternativa: papel a 22-25 °C adentro y plantar brotada. |
| Trasplantar | 3 días | noches ≥ 10 °C · ≤ 20 mm · ráfagas < 50 km/h · VPD ≤ 1,8 | Sin raíz nueva no aguanta frío, temporal ni aire seco. |
| Topping / poda / LST fuerte | 2 días | noches ≥ 8 °C · ≤ 15 mm · VPD ≤ 1,8 | Herida abierta + lluvia = hongo; VPD alto = planta ya estresada. |
| Sacar la cúpula | 3 días | noches ≥ 10 °C · ráfagas < 45 km/h · VPD ≤ 1,5 | La cúpula es el único reparo de la plántula. |
| Cover crop / resiembra | 5 días | noches ≥ 6 °C · máximas ≥ 14 °C · ≤ 40 mm | Legumbres germinan desde 8 °C pero necesitan 5 días de suelo húmedo. |
| Cortar | 2 días | ≤ 5 mm | Cogollo mojado al secado = botrytis. Si viene lluvia, se corta ANTES. |

Lo que el semáforo NO mide y Claude tiene que preguntar igual: cuántas semillas quedan, qué se pierde si sale mal,
cuándo es la próxima visita (si la acción necesita control diario, no se hace afuera), y si se puede hacer en dos tiempos.

## Germinación, el procedimiento que vale (desde el 13/10/26)
1. Papel de cocina húmedo (no chorreando) entre dos platos, en un lugar a 22-25 °C (arriba de la heladera, del router). Oscuridad.
2. Revisar a las 24, 48 y 72 h. Raíz de 0,5-1 cm = lista. Más de 5 días sin raíz = semilla muerta; no insistir.
3. Plantar brotada: hoyo de 1 cm en el centro de la maceta, raíz para abajo, tapar sin apretar, mojar solo un vasito en el centro.
   La maceta NO se riega a fondo ese día. Cúpula de botella sin tapa.
4. Afuera solo si el semáforo da verde para los 5 días siguientes; si no, en vasito de 1 L en casa hasta que dé.

## Lo que pasó el 6/10/26 (para no repetirlo)
Tanda 1 sembrada directo en 40 L, regada a fondo, y después 7 días de 16-19 °C de máxima, 10-13 °C de noche y 29 mm.
Ninguna germinó. Con este semáforo, el 6/10 daba rojo en los 5 días.
