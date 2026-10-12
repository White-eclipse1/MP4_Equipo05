# F9 — Operación, reintento sin duplicados y 20 capturas

| Campo | Valor |
|---|---|
| Responsable | Bryan (Líder de dispositivo edge y cámara) |
| Revisor de PRs | Emilio |
| Fechas | 13 oct de 2026 |
| Rama | `feat/p4-fase-9-operacion-capturas` |
| Puntos de rúbrica | 5 (2.4) |
| Depende de | F6 |
| Bloquea a | F11 |
| Control | Control 3 |

**Nota de calendario:** se hace el martes 13, con el recorrido de F6 ya estable y antes de la congelación de código de esa noche.

> Antes de empezar lee `AGENTS.md` y `docs/contratos.md`. Trabaja los bloques en orden.

## Rúbrica (5 puntos)

**2.4 Operación estable (5):** demostración de cinco minutos, historial de veinte capturas repartidas entre las clases y reinicio del programa seguido de una captura nueva. Los fallos reales quedan visibles. No se exige arranque automático con el sistema operativo.

## Bloques de trabajo

- **Estabilidad:** cinco minutos de operación continua, dejando visibles los fallos que ocurran.
- **Reinicio:** reiniciar el programa y hacer una captura nueva; los datos anteriores persisten.
- **20 capturas:** al menos 20 eventos repartidos entre las clases, con sus fotografías, enviados a AWS. Verifican operación y no tienen un umbral propio de accuracy.
- **Exportación de eventos:** CSV o JSON con ID, fecha con zona horaria, clase, confianza, dispositivo, versión y referencia a la fotografía.
- **Ensayo del reintento:** repetir el fallo y reintento de F6 para confirmar que sigue dejando un solo registro.

## Cómo se cierra

- [ ] Las 20 capturas visibles en el portal con sus metadatos
- [ ] Exportación de eventos entregada a Emilio para la carpeta de evidencias
- [ ] Captura nueva correcta después del reinicio
- [ ] El evento reintentado aparece una sola vez
- [ ] PR fusionado con review de Emilio
- [ ] Estado de la tarjeta en **Hecho**

## Registro de avance

| Fecha | Quién | Bloque | Qué se hizo / PR | Pendiente |
|---|---|---|---|---|
