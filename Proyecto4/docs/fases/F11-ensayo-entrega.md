# F11 — Ensayo, video opcional y entrega

| Campo | Valor |
|---|---|
| Responsable | Sebastián (PM, coordina) |
| Revisor de PRs | — (la fase no abre PR) |
| Fechas | 14 oct de 2026; colchón el 15; entrega el 16 |
| Rama | — |
| Puntos de rúbrica | 15 extra (video V1, V2 y V3); simulacro de M1, M2 y M3 |
| Depende de | F1–F10 |
| Bloquea a | — |
| Control | Control 3 |

**Nota de calendario:** todo ocurre el miércoles 14, con el código congelado desde el martes 13 por la noche; coordina Sebastián y participan los cuatro. El jueves 15 queda como colchón para corregir lo que salga del simulacro y la entrega es el viernes 16.

> Fase de coordinación. Sebastián dirige el simulacro, repasa las evidencias y envía la entrega; no ejecuta trabajo técnico ni toca el código. La demostración y el video los opera el equipo.

## Rúbrica (15 puntos extra)

El video se califica aparte de los 100 puntos base y solo cuenta si se entrega la grabación:

- **V1 (5):** dispositivo físico capturando y clasificando objetos de distintas clases, con resultados visibles.
- **V2 (5):** envío real a AWS y fotografías nuevas apareciendo en Capturas Edge.
- **V3 (5):** una misma captura seguida del dispositivo a AWS y al portal, con imagen, ID, fecha y clasificación coincidentes.

Narración o diapositivas sin ejecución valen 0. Duración orientativa de 3 a 5 minutos.

## Coordinación (Sebastián)

- **Simulacro de evaluación:** hacer de evaluador siguiendo `docs/rubrica.md` (demostración guiada de unos 10 a 15 minutos). Elegir los objetos y su orden, cinco eventos para contrastar entre exportación local, AWS y portal, y una muestra de la comparación de calidad o del benchmark para reproducir. Las 20 capturas y las mediciones pueden existir de antemano; durante la demo basta una captura nueva dirigida.
- **Requisitos mínimos:** confirmar M1, M2 y M3 con evidencia observada, no con afirmaciones.
- **Inventario de evidencias:** recorrer la carpeta de F10 contra la lista de entrega del prompt y abrir cada enlace con el acceso del evaluador.
- **Pendientes:** anotar cada falla con dueño y cerrarla el jueves 15.
- **Entrega:** enviar el viernes 16 el paquete de evidencias, la URL del portal y el video.

## Bloques de trabajo

- **Modelo y resultados (Edith):** mostrar modelo de origen, versión optimizada y hashes; reproducir la muestra de calidad que elija Sebastián.
- **Dispositivo (Bryan):** clasificar los objetos elegidos, desconectar la red y seguir clasificando, reconectar y enviar una captura nueva, provocar un envío fallido y reintentarlo, reiniciar el programa y volver a capturar.
- **AWS y portal (Emilio):** ejecutar la consulta de solo lectura, abrir Capturas Edge desde la navegación del portal, refrescar y mostrar la captura nueva y el evento reintentado sin duplicado.
- **Video de 3 a 5 minutos (Edith, con Bryan y Emilio en cámara):** grabar V1, V2 y V3 en una sola toma seguida si es posible, con el ID de la captura legible en dispositivo, AWS y portal.

## Cómo se cierra

- [ ] Simulacro completo sin intervención sobre el código
- [ ] M1, M2 y M3 confirmados con evidencia observada (Sebastián)
- [ ] Video accesible desde un enlace, mostrando V1, V2 y V3 (Edith)
- [ ] Pendientes del simulacro cerrados el jueves 15
- [ ] Entrega enviada el viernes 16 (Sebastián)
- [ ] Estado de la tarjeta en **Hecho** (Sebastián)

## Registro de avance

| Fecha | Quién | Bloque | Qué se hizo / PR | Pendiente |
|---|---|---|---|---|
