# F8 — Medición de recursos en el dispositivo

| Campo | Valor |
|---|---|
| Responsable | Bryan (Líder de dispositivo edge y cámara) |
| Revisor de PRs | Emilio |
| Fechas | 12 oct → 13 oct de 2026 |
| Rama | `feat/p4-fase-8-medicion-recursos` |
| Puntos de rúbrica | 15 (3.1, 3.2 y 3.3) |
| Depende de | F2, F3 |
| Bloquea a | F10 |
| Control | Control 3 |

**Nota de calendario:** empieza el lunes 12, con F3 clasificando de forma estable, y se cierra el martes 13.

> Antes de empezar lee `AGENTS.md` y `docs/decisiones.md` (hardware, runtime y objetivo de optimización). Trabaja los bloques en orden.

## Rúbrica (15 puntos)

- **3.1 Comparación bajo condiciones equivalentes (5):** hardware, runtime, precisión, tamaño de entrada y condiciones identificados; original y variante comparados donde sea posible.
- **3.2 Mediciones auditables (5):** tamaños verificables, al menos 100 tiempos locales después de 10 calentamientos y p50/p95 recalculables. Un promedio sin registros vale como máximo 2.5.
- **3.3 Mejora demostrada y decisión justificada (5):** 3 puntos por una mejora medible en tamaño, latencia o memoria, y 2 por explicar el intercambio entre recursos y calidad para el hardware elegido.

## Bloques de trabajo

- **Tamaño:** bytes de ambos artefactos y porcentaje de reducción.
- **Tiempos:** CSV o JSON con una fila por inferencia: variante, número de repetición y milisegundos de preprocesamiento más inferencia local. El calentamiento se identifica y se excluye; el envío a AWS se registra aparte.
- **Percentiles:** p50 y p95 con el método indicado, por ejemplo interpolación lineal.
- **Original en el mismo dispositivo:** medirlo si puede ejecutarse; si no cabe o es incompatible, guardar el error observado y la configuración. No se compara laptop contra dispositivo.
- **Mejora:** comprobar que la diferencia supera la variabilidad de las mediciones; si no, repetir mediciones o apoyarse en la reducción de tamaño.
- **Decisión (con Edith):** explicar qué se ganó en recursos, qué se cedió en calidad según F7 y por qué conviene para este hardware.
- **Ficha de condiciones:** hardware, sistema operativo, runtime, precisión y tamaño de entrada.

## Cómo se cierra

- [ ] Archivo de tiempos por repetición con p50 y p95 recalculables
- [ ] Tamaños de ambos artefactos y reducción calculada
- [ ] Mejora medible documentada, con el intercambio recursos y calidad explicado
- [ ] Ficha de hardware, runtime, precisión y condiciones
- [ ] PR fusionado con review de Emilio
- [ ] Estado de la tarjeta en **Hecho**

## Registro de avance

| Fecha | Quién | Bloque | Qué se hizo / PR | Pendiente |
|---|---|---|---|---|
