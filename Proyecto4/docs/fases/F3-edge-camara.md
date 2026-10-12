# F3 — Cámara e inferencia local en el dispositivo

| Campo | Valor |
|---|---|
| Responsable | Bryan (Líder de dispositivo edge y cámara) |
| Revisor de PRs | Emilio |
| Fechas | 7 oct → 9 oct de 2026 |
| Rama | `feat/p4-fase-3-edge-camara` |
| Puntos de rúbrica | 20 (2.1, 2.2 y 2.3; requisito M2) |
| Depende de | F1, F2 (variante final) |
| Bloquea a | F6, F8, F9 |
| Control | Control 2 |

**Nota de calendario:** el miércoles 7 se arma la captura y el preprocesamiento con el modelo original o una entrada conocida, sin esperar a F2. El jueves 8 al mediodía llega la variante y el viernes 9 debe clasificar sin red.

> Antes de empezar lee `AGENTS.md`, `docs/decisiones.md` (modo de captura, hardware y runtime) y `docs/contratos.md` (evento). Trabaja los bloques en orden.

## Rúbrica (20 puntos)

- **2.1 Cámara en el dispositivo (5):** capturas nuevas de objetos que elige el evaluador. Una carpeta de imágenes precargadas no sustituye la cámara.
- **2.2 Entrada y clases coherentes (5):** resolución, canales, normalización, cuantización de entrada y recorte coinciden con el paquete del modelo.
- **2.3 Inferencia local con la variante (10):** la predicción cambia con objetos de distintas clases y sigue funcionando sin red. Si depende de AWS, de otra computadora o de un simulador, vale 0.
- **Requisito mínimo M2:** clasificación local en un dispositivo edge físico con cámara.

## Bloques de trabajo

- **Captura:** programa por botón o intervalo, un objeto por captura, con recorte fijo si aplica.
- **Preprocesamiento:** igual al de evaluación: tamaño, normalización, orden RGB/BGR y cuantización de entrada si aplica.
- **Inferencia local:** mostrar clase, confianza y tiempo.
- **Artefacto en uso:** al arrancar, el programa muestra versión y SHA-256 de la variante cargada. La prueba sin red no basta sola para demostrar qué modelo está cargado.
- **Entradas conocidas:** reproducir algunas muestras de validación en el dispositivo y contrastar clase y salida con los registros de F7.
- **Evento local:** registro con ID de captura, fecha con zona horaria, clase, confianza entre 0 y 1, dispositivo, versión del artefacto y referencia a la fotografía.

## Cómo se cierra

- [ ] Clasifica objetos nuevos de varias clases con la variante de F2
- [ ] Sigue capturando y clasificando con la red desconectada después de cargar el modelo
- [ ] Muestra versión y hash del artefacto cargado
- [ ] Entradas conocidas dan la misma clase que en los registros
- [ ] Cada captura deja imagen y registro con ID único
- [ ] PR fusionado con review de Emilio
- [ ] Estado de la tarjeta en **Hecho**

## Registro de avance

| Fecha | Quién | Bloque | Qué se hizo / PR | Pendiente |
|---|---|---|---|---|
