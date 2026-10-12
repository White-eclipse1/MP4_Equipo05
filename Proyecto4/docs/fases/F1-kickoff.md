# F1 — Kickoff, modelo del P3, hardware y contrato

| Campo | Valor |
|---|---|
| Responsable | Sebastián (PM, coordina) |
| Revisor de PRs | Edith revisa el PR del andamiaje; el de decisiones lo abre Edith y lo revisa Bryan |
| Fechas | 7 oct de 2026 |
| Rama | `feat/p4-fase-1-kickoff` (andamiaje de `Proyecto4/`) |
| Puntos de rúbrica | 0 (habilita M1 y prepara 1.1) |
| Depende de | — |
| Bloquea a | F2–F10 |
| Control | Control 1 |

**Nota de calendario:** todo ocurre el miércoles 7; coordina Sebastián y participan los cuatro. Es el Control 1: sin modelo inferible, cámara funcionando, acceso a AWS y contrato escrito, ninguna otra fase puede avanzar.

> Fase de coordinación. Sebastián convoca, da seguimiento y valida el cierre; no ejecuta trabajo técnico. Cada bloque práctico tiene su dueño. La única excepción es el PR inicial que sube el andamiaje documental de `Proyecto4/` (AGENTS, plan, rúbrica, guías de fase, plantillas de decisiones y contrato), que no contiene trabajo técnico.

## Coordinación (Sebastián)

- Convocar el kickoff y repartir los bloques de abajo.
- Compartir con el equipo la rúbrica (`docs/rubrica.md`) y la lista de evidencias que pide el prompt de evaluación.
- Confirmar con cada líder responsable, revisor y fechas de las tarjetas F2–F11.
- Dar seguimiento a los accesos pedidos a Diego y Andrés hasta que estén resueltos.
- Validar al final del día las casillas de cierre con la evidencia que muestre cada dueño.

## Bloques de trabajo

- **Referencia del Proyecto 3 (Edith):** recuperar pesos originales, clases y preprocesamiento; anotar versión, run ID si existe y hash SHA-256. Comprobar que el modelo infiere una entrada conocida. Se registra en la tabla final de `docs/decisiones.md`.
- **Traspaso del repositorio (Edith):** recorrer con Bryan y Emilio el repositorio, la estructura del portal y los servicios desplegados.
- **Accesos heredados (Emilio):** obtener la cuenta de AWS, el bucket de S3 y el despliegue del portal; probar con credenciales del equipo actual.
- **Hardware (Bryan):** probar dispositivo, cámara y runtime; anotar sistema operativo y versiones.
- **Decisiones técnicas (Edith, Bryan y Emilio):** cada líder escribe las suyas en `docs/decisiones.md`: formato y runtime, técnica y objetivo de optimización, datos de comparación, modo de captura, servicios de AWS y ubicación de Capturas Edge. El PR lo abre Edith y lo revisa Bryan.
- **Contrato del evento (Emilio y Bryan):** ID de captura, fecha con zona horaria, clase, confianza entre 0 y 1, dispositivo, versión del artefacto optimizado, referencia a la fotografía y región clasificada si aplica. Se escribe en `docs/contratos.md`.

## Cómo se cierra

- [ ] Modelo original inferible, con versión, run ID y hash anotados (Edith)
- [ ] Cámara capturando en el dispositivo (Bryan)
- [ ] AWS responde con las credenciales del equipo actual (Emilio)
- [ ] Contrato del evento acordado por Bryan y Emilio
- [ ] Tarjetas F2–F11 con responsable y fecha confirmados (Sebastián)
- [ ] Estado de la tarjeta de F1 en **Hecho** (Sebastián)

## Registro de avance

| Fecha | Quién | Bloque | Qué se hizo / PR | Pendiente |
|---|---|---|---|---|
