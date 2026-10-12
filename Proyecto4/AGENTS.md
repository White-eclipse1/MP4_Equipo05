# AGENTS.md — Proyecto 4: Modelo en edge

## Contexto

Proyecto 4 = llevar el clasificador del Proyecto 3 a un dispositivo edge físico con cámara. El flujo obligatorio es: modelo publicado del P3 → variante optimizada (conversión reproducible) → clasificación local en el dispositivo, sin red → envío de fotografía y metadatos a AWS → sección **Capturas Edge** en el mismo portal de los Proyectos 1 a 3. Además se compara la calidad (original contra optimizado) y se miden los recursos en el dispositivo (tamaño, latencia, memoria).

Requisitos mínimos (si cualquiera falla, la nota se topa en 60):

- **M1:** la variante procede del modelo del Proyecto 3.
- **M2:** clasificación local en un dispositivo edge físico con cámara.
- **M3:** fotografías nuevas y resultados llegan a AWS y aparecen en Capturas Edge del portal.

Rúbrica base de 100 puntos más 15 extra por el video (máximo 115). El prompt de evaluación con el que se califica está en `docs/rubrica.md`; los contratos entre módulos, en `docs/contratos.md`. Si un M falla, el tope de 60 incluye el video extra.

Documentos de referencia (las rutas `docs/...` son relativas a `Proyecto4/`):

- `docs/PLAN.md`: equipo, roles, cronograma, controles y Git.
- `docs/rubrica.md`: prompt de evaluación completo (requisitos mínimos, criterios 1.1–6.3, video, evidencia que se pide y cómo se recalcula).
- `docs/decisiones.md`: decisiones técnicas de F1 (formato, runtime, técnica, hardware, AWS).
- `docs/contratos.md`: contrato del evento de captura entre el dispositivo y AWS.
- `docs/fases/`: un archivo por fase con bloques, criterios de cierre y registro de avance.
- Del Proyecto 3: `Proyecto3/docs/modelo.md`, `clases.md`, `publicacion_s3.md` y `contratos.md` (pesos, clases, preprocesamiento y versión publicada).

## Cómo trabajar una fase

1. Identifica la fase que te pidieron y abre su archivo en `docs/fases/`. Trabaja solo esa fase.
2. Crea o continúa su rama (indicada en el archivo). Si otra persona empezó la fase, sigue en la misma rama.
3. Ejecuta los bloques en orden.
4. Si dependes de una fase que aún no está en `main`, trabaja contra `docs/contratos.md` y una entrada conocida, y anótalo como pendiente en el registro.
5. Al cerrar un bloque: marca sus casillas con enlace a la evidencia, agrega una fila en "Registro de avance" y abre el PR para el revisor indicado.
6. Nunca marques una casilla sin evidencia real (salida de comando, archivo de mediciones, registro en AWS, comportamiento observado en el dispositivo o en el portal).

## Mapa de fases

| ID | Fase | Responsable | Fechas | Archivo |
|---|---|---|---|---|
| F1 | Kickoff, modelo del P3, hardware y contrato | Sebastián (coordina) | 7 oct | `docs/fases/F1-kickoff.md` |
| F2 | Variante optimizada y conversión reproducible | Edith | 7 oct → 8 oct | `docs/fases/F2-optimizacion.md` |
| F3 | Cámara e inferencia local en el dispositivo | Bryan | 7 oct → 9 oct | `docs/fases/F3-edge-camara.md` |
| F4 | Recepción y persistencia en AWS | Emilio | 7 oct → 8 oct | `docs/fases/F4-aws-recepcion.md` |
| F5 | Portal: sección Capturas Edge | Emilio | 8 oct → 9 oct | `docs/fases/F5-portal-capturas-edge.md` |
| F6 | Primer recorrido completo, de la cámara al portal | Emilio (opera Bryan) | 9 oct → 12 oct | `docs/fases/F6-recorrido-completo.md` |
| F7 | Comparación de calidad, original contra optimizado | Edith | 8 oct → 9 oct | `docs/fases/F7-comparacion-calidad.md` |
| F8 | Medición de recursos en el dispositivo | Bryan | 12 oct → 13 oct | `docs/fases/F8-medicion-recursos.md` |
| F9 | Operación, reintento sin duplicados y 20 capturas | Bryan | 13 oct | `docs/fases/F9-operacion-capturas.md` |
| F10 | README, pruebas y carpeta de evidencias | Emilio | 13 oct → 14 oct | `docs/fases/F10-readme-evidencias.md` |
| F11 | Ensayo, video opcional y entrega | Sebastián (coordina) | 14 oct | `docs/fases/F11-ensayo-entrega.md` |

## Reglas del equipo

1. **Ramas por fase, no por persona:** `feat/p4-fase-N-*`. Si alguien retoma una fase de otro, sigue en la misma rama.
2. **Nadie hace push directo a `main`; todo entra por PR.** Nadie mergea su propio PR: hace falta la review real de otro integrante (rotación en `docs/PLAN.md`).
3. **Commits pequeños**, un cambio lógico por commit; no mezclar fases.
4. **La variante sale del modelo del Proyecto 3.** Sustituirlo por un modelo ajeno rompe M1 y deja 1.2 en 0. El orden de clases y el preprocesamiento deben ser idénticos al original.
5. **El test del Proyecto 3 es intocable.** No se usa para calibración, cuantización ni para decidir la configuración. Si la técnica necesita calibración, solo muestras de entrenamiento, con manifiesto de IDs.
6. **Conversión reproducible:** script, configuración, dependencias y versiones en el repositorio. Toda conversión deja un registro con archivo de entrada, archivo de salida y SHA-256 de ambos.
7. **El dispositivo clasifica sin red.** Nada de depender de AWS, de otra computadora o de un simulador para la inferencia (2.3).
8. **El ID de captura es la clave de idempotencia.** Un reintento con el mismo ID nunca crea un duplicado en AWS. El registro local se conserva aunque el envío falle.
9. **Los números salen de registros recalculables:** predicciones por muestra, tiempos por repetición, exportación de eventos. No se reportan promedios sin registros ni cifras redondeadas antes de comparar.
10. **Nunca versionar** credenciales de AWS, claves de acceso, tokens ni contraseñas. Plantillas de configuración sin secretos; el evaluador recibe un acceso limitado, nunca un paquete con llaves: no se le entregan claves ni acceso administrativo, basta una consulta de solo lectura durante la demostración. Los pesos grandes se distribuyen con enlace de descarga y hash (la rúbrica no obliga a ponerlos en Git); qué cabe en Git se decide en `docs/decisiones.md`.
11. **Los fallos reales quedan visibles** (operación estable, 2.4): no se esconden con reintentos silenciosos ni se borran del historial.
12. **Contratos congelados** en `docs/contratos.md` cuando Bryan y Emilio los acuerdan; cualquier cambio de forma va explícito en el PR y se avisa al equipo.
13. **Código congelado el martes 13 por la noche.** El 14 es simulacro, el 15 corrección de pendientes y el 16 entrega.
14. **`git config user.name` / `user.email` reales.**
15. **Las pruebas destructivas** (cortar la red, apuntar a un destino inválido) deben ser reversibles y no dañar el entorno de AWS ni el portal desplegado.

## Coordinación (Sebastián)

Sebastián convoca el kickoff (F1) y el simulacro (F11), da seguimiento a accesos y fechas, confirma M1–M3 con evidencia observada y envía la entrega. No ejecuta trabajo técnico ni abre PR; cada bloque práctico tiene un dueño en el equipo.
