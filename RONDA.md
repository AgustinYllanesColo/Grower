# Ronda automática (Routine cada 2 días)

Objetivo: gastar pocos tokens. Todas las reglas están en `scripts/ronda.py`; el modelo solo mueve archivos.
Artifact: https://claude.ai/artifact/RVpKesdPsPyMQEudSAySMa

Pasos:
1. Parado en la raíz del repo `agustinyllanescolo/grower`. Si no está clonado: `git clone https://github.com/agustinyllanescolo/grower`.
2. Cargar ArtifactData con ToolSearch (`select:ArtifactData`). Hacer un `list` de la colección `estado` con out_dir `/tmp/ronda/db`.
   Anotar la `version` de `clima` y la de `avisos`.
3. `cd /tmp/ronda && NTFY_TOPIC=<tema de la rutina> python3 <repo>/scripts/ronda.py db/estado/checklist.json db/estado/clima.json db/estado/agenda.json`
   Manda la notificación por ntfy, imprime una línea de resumen y deja `out/clima.json` y `out/avisos.json`.
4. ArtifactData `batch` con dos `set`: `estado/clima` desde `/tmp/ronda/out/clima.json` y `estado/avisos` desde `/tmp/ronda/out/avisos.json`,
   cada uno con el `if_version` que leíste (si `avisos` no existía, sin `if_version`).
5. Respuesta final: SOLO la línea que imprimió el script. Esa línea es la notificación.

Si wttr.in falla, reintentar una vez. Si vuelve a fallar, responder «Ronda sin clima: wttr.in no respondió» y no escribir nada.
No leer la bitácora (el HTML), no investigar y no hacer nada más.
