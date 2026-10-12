# F7 — Comparación de calidad, original contra optimizado

| Campo | Valor |
|---|---|
| Responsable | Edith (Líder de modelo y optimización) |
| Revisor de PRs | Bryan |
| Fechas | 8 oct → 9 oct de 2026 |
| Rama | `feat/p4-fase-7-comparacion-calidad` |
| Puntos de rúbrica | 10 (1.3) |
| Depende de | F2 |
| Bloquea a | F10 |
| Control | Control 2 |

**Nota de calendario:** empieza el jueves 8 en cuanto la variante de F2 está lista y el reporte se cierra el viernes 9. Si la caída de accuracy supera 2 puntos porcentuales, se regresa a F2 ese mismo viernes para probar otra configuración antes del lunes 12.

> Antes de empezar lee `AGENTS.md` y `docs/decisiones.md` (datos de comparación). El test del Proyecto 3 no se toca. Trabaja los bloques en orden.

## Rúbrica (10 puntos)

**1.3 Calidad comparada correctamente**, desglosada así:

- **3 puntos:** mismas muestras y clases, con predicciones individuales verificables.
- **3 puntos:** accuracy y F1 macro recalculables, resultados por clase y explicación de errores.
- **2 puntos:** calibración solo con entrenamiento, si aplica, y test fuera de cualquier ajuste.
- **2 puntos:** caída de accuracy de hasta 2 puntos porcentuales respecto al original. No se exige volver a obtener 85%.

## Bloques de trabajo

- **Evaluación común:** ambos modelos sobre la misma validación del Proyecto 3, con el mismo manifiesto y etiquetas.
- **Predicciones por muestra:** CSV o JSON con una fila por muestra: identificador, clase real, clase predicha por el original y clase predicha por el optimizado.
- **Revisión del manifiesto:** sin muestras faltantes, sin IDs duplicados, etiquetas coincidentes y todas las clases declaradas incluidas.
- **Métricas:** accuracy, F1 por clase y macro sobre el mapa de clases completo (F1 = 0 para una clase sin predicciones positivas), soporte por clase y caída en puntos porcentuales sin redondear.
- **Explicación de errores:** qué clases se ven afectadas por la optimización y por qué.
- **Separación de datos:** dejar constancia de la procedencia de los datos de calibración y de que el test no se usó. Si la técnica no necesitó calibración, los 2 puntos se verifican con el procedimiento de conversión y la procedencia de los datos comparados; no hace falta un manifiesto de calibración inexistente.

## Cómo se cierra

- [ ] Predicciones por muestra entregadas y recalculables
- [ ] Reporte antes y después con métricas por clase y errores explicados
- [ ] Caída de accuracy de hasta 2 puntos porcentuales, o decisión documentada si no se logra
- [ ] Procedencia de calibración y exclusión del test anotadas
- [ ] PR fusionado con review de Bryan
- [ ] Estado de la tarjeta en **Hecho**

## Registro de avance

| Fecha | Quién | Bloque | Qué se hizo / PR | Pendiente |
|---|---|---|---|---|
