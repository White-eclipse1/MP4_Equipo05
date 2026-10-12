# Plan del equipo — Proyecto 4

Entrega: **viernes 16 de octubre de 2026**. Arranque: **miércoles 7 de octubre**. Compuerta: si M1 (la variante procede del modelo del P3), M2 (clasificación local en un dispositivo físico con cámara) o M3 (capturas nuevas en AWS y visibles en Capturas Edge) fallan, la nota se topa en 60.

El código se congela el **martes 13 por la noche**. El miércoles 14 es simulacro de evaluación, el jueves 15 queda como colchón para cerrar pendientes y el viernes 16 se entrega.

## Roles

| Persona | Rol | Fases | Puntos | Revisa sus PRs | Responsabilidad |
|---|---|---|---:|---|---|
| Sebastián | PM | F1, F11 | 0 (+15 del video) | — | Convoca kickoff y simulacro, da seguimiento a accesos y fechas, valida las casillas de cierre con evidencia y envía la entrega. No ejecuta trabajo técnico ni abre PR. |
| Edith | Líder de modelo y optimización | F2, F7 | 25 | Bryan | Recupera el modelo del P3, aplica la técnica de optimización, deja la conversión reproducible y compara la calidad contra el original. Graba el video con Bryan y Emilio en cámara. |
| Bryan | Líder de dispositivo edge y cámara | F3, F8, F9 | 40 | Emilio | Dueño del dispositivo: cámara, preprocesamiento, inferencia local, evento local, mediciones de recursos y operación estable con las 20 capturas. |
| Emilio | Líder de AWS · portal · integración | F4, F5, F6, F10 | 35 | Edith | Dueño de los accesos heredados, la recepción y persistencia en AWS, la sección Capturas Edge, el recorrido completo, el README y la carpeta de evidencias. |

Revisión en rotación: Edith → Bryan → Emilio → Edith. Nadie aprueba su propio PR. Los puntos no equivalen a esfuerzo.

## Cronograma

🟦 Bryan · 🟩 Edith · 🟧 Emilio · 🟪 Sebastián · `·` fin de semana (colchón)

| Fase | mié 7 | jue 8 | vie 9 | sáb 10 | dom 11 | lun 12 | mar 13 | mié 14 | jue 15 | vie 16 |
|---|---|---|---|---|---|---|---|---|---|---|
| F1 Kickoff, modelo del P3, hardware y contrato (Sebastián) | 🟪 |   |   | · | · |   |   |   |   |   |
| F2 Variante optimizada y conversión (Edith) | 🟩 | 🟩 |   | · | · |   |   |   |   |   |
| F3 Cámara e inferencia local (Bryan) | 🟦 | 🟦 | 🟦 | · | · |   |   |   |   |   |
| F4 Recepción y persistencia en AWS (Emilio) | 🟧 | 🟧 |   | · | · |   |   |   |   |   |
| F5 Portal: Capturas Edge (Emilio) |   | 🟧 | 🟧 | · | · |   |   |   |   |   |
| F6 Primer recorrido completo (Emilio, opera Bryan) |   |   | 🟧 | · | · | 🟧 |   |   |   |   |
| F7 Comparación de calidad (Edith) |   | 🟩 | 🟩 | · | · |   |   |   |   |   |
| F8 Medición de recursos (Bryan) |   |   |   | · | · | 🟦 | 🟦 |   |   |   |
| F9 Operación y 20 capturas (Bryan) |   |   |   | · | · |   | 🟦 |   |   |   |
| F10 README, pruebas y evidencias (Emilio) |   |   |   | · | · |   | 🟧 | 🟧 |   |   |
| F11 Ensayo, video y entrega (Sebastián) |   |   |   | · | · |   |   | 🟪 | colchón | 🟪 |

## Fases

| ID | Fase | Responsable | Revisor | Fechas | Puntos | Depende de | Bloquea a | Control | Archivo |
|---|---|---|---|---|---:|---|---|---|---|
| F1 | Kickoff, modelo del P3, hardware y contrato | Sebastián | — | 7 oct | 0 | — | F2–F10 | 1 | `docs/fases/F1-kickoff.md` |
| F2 | Variante optimizada y conversión reproducible | Edith | Bryan | 7 oct → 8 oct | 15 | F1 | F3, F7, F8 | 2 | `docs/fases/F2-optimizacion.md` |
| F3 | Cámara e inferencia local en el dispositivo | Bryan | Emilio | 7 oct → 9 oct | 20 | F1, F2 (variante final) | F6, F8, F9 | 2 | `docs/fases/F3-edge-camara.md` |
| F4 | Recepción y persistencia en AWS | Emilio | Edith | 7 oct → 8 oct | 10 | F1 (contrato) | F5, F6 | 2 | `docs/fases/F4-aws-recepcion.md` |
| F5 | Portal: sección Capturas Edge | Emilio | Edith | 8 oct → 9 oct | 10 | F4 | F6 | 2 | `docs/fases/F5-portal-capturas-edge.md` |
| F6 | Primer recorrido completo, de la cámara al portal | Emilio | Edith | 9 oct → 12 oct | 5 | F3, F4, F5 | F9, F11 | 2 | `docs/fases/F6-recorrido-completo.md` |
| F7 | Comparación de calidad, original contra optimizado | Edith | Bryan | 8 oct → 9 oct | 10 | F2 | F10 | 2 | `docs/fases/F7-comparacion-calidad.md` |
| F8 | Medición de recursos en el dispositivo | Bryan | Emilio | 12 oct → 13 oct | 15 | F2, F3 | F10 | 3 | `docs/fases/F8-medicion-recursos.md` |
| F9 | Operación, reintento sin duplicados y 20 capturas | Bryan | Emilio | 13 oct | 5 | F6 | F11 | 3 | `docs/fases/F9-operacion-capturas.md` |
| F10 | README, pruebas y carpeta de evidencias | Emilio | Edith | 13 oct → 14 oct | 10 | F7, F8 | F11 | 3 | `docs/fases/F10-readme-evidencias.md` |
| F11 | Ensayo, video opcional y entrega | Sebastián | — | 14 oct | 15 extra | F1–F10 | — | 3 | `docs/fases/F11-ensayo-entrega.md` |

Los 100 puntos base suman F2 a F10 (15 + 20 + 10 + 10 + 5 + 10 + 15 + 5 + 10). Los 15 de F11 son el video, aparte de la base.

## Controles

- **Control 1 → miércoles 7:** modelo original inferible con versión, run ID y hash anotados; cámara capturando en el dispositivo; AWS responde con las credenciales del equipo actual; contrato del evento acordado; decisiones técnicas escritas en `docs/decisiones.md`. Sin esto ninguna otra fase puede avanzar.
- **Control 2 → lunes 12:** variante cargable en el dispositivo (F2), clasificación local sin red (F3), captura nueva visible en Capturas Edge con fallo y reintento controlados (F4–F6) y comparación de calidad cerrada (F7). El centro es F6.
- **Control 3 → martes 13 por la noche:** congelación de código con mediciones (F8), operación y 20 capturas (F9) y README con carpeta de evidencias (F10) en curso de cierre. El miércoles 14 se hace el simulacro (F11) y el jueves 15 se cierran los pendientes.

## Git

**Nadie hace push directo a `main`; todo cambio entra por PR.** Nadie mergea su propio PR: hace falta la aprobación del revisor de la tabla, con una review real (no un "LGTM" vacío). Ramas por fase, no por persona: `feat/p4-fase-N-*`.

Las reglas completas del equipo están en `AGENTS.md`.
