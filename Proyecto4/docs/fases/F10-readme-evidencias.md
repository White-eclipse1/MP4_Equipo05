# F10 — README, pruebas y carpeta de evidencias

| Campo | Valor |
|---|---|
| Responsable | Emilio (Líder de AWS · portal · integración) |
| Revisor de PRs | Edith |
| Fechas | 13 oct → 14 oct de 2026 |
| Rama | `feat/p4-fase-10-readme-evidencias` |
| Puntos de rúbrica | 10 (6.1, 6.2 y 6.3) |
| Depende de | F7, F8 |
| Bloquea a | F11 |
| Control | Control 3 |

**Nota de calendario:** empieza el martes 13 con los reportes de F7 y F8, y se cierra el miércoles 14 por la mañana, antes del simulacro de F11. El código se congela el martes 13 por la noche.

> Antes de empezar lee `AGENTS.md`, `docs/rubrica.md` y `docs/decisiones.md`. Trabaja los bloques en orden.

## Rúbrica (10 puntos)

- **6.1 Instrucciones suficientes (4):** ficha y README permiten instalar, arrancar, recuperar artefactos y ejecutar el recorrido, con hardware y versiones documentados.
- **6.2 Comprobaciones repetibles (4):** pasos para comprobar carga y conversión, respuesta a entradas conocidas y evento enviado y recuperado. Valen pruebas automatizadas o una lista manual con resultados; no se exige TDD, CI nuevo ni cobertura.
- **6.3 Configuración operable y acceso controlado (2):** destino de AWS, identidad del dispositivo y artefacto configurables y documentados; plantilla sin secretos y acceso de evaluación limitado.

## Bloques de trabajo

- **Ficha de entrega:** equipo, dispositivo y cámara, sistema operativo, runtime, técnica, comandos de instalación y arranque, URL del portal y referencias a cada evidencia.
- **README:** instalación, configuración, recuperación del modelo, arranque de dispositivo y portal, y pasos de verificación.
- **Comprobaciones repetibles:** lista con comando o paso, resultado esperado y registro, para carga y conversión, inferencia sobre entradas conocidas y evento enviado y recuperado.
- **Configuración:** plantilla sin secretos donde se cambian destino de AWS, identidad del dispositivo y artefacto.
- **Carpeta de evidencias:** directorio o ZIP (la rúbrica acepta nombres y formatos equivalentes) con la lista de abajo.
  - Ficha de entrega y README breve.
  - Identificación del modelo existente: versión y referencia del P3, run ID si existe, pesos originales, clases y preprocesamiento.
  - Variante optimizada: archivo recuperable, formato y precisión, versión, SHA-256 y registro de conversión con entrada y salida.
  - Comparación de calidad: manifiesto de validación del P3, etiquetas, predicciones de original y optimizado por muestra, métricas y exclusiones si hubo.
  - Comparación de recursos: tamaño de ambos artefactos, al menos 100 tiempos de la variante tras 10 calentamientos, hardware y condiciones; tiempos del original si corre en ese dispositivo.
  - Exportación de las 20 capturas con sus fotografías.
  - Evidencia de AWS: registros persistidos, referencia del servicio o recurso y consulta de solo lectura.
  - Acceso al portal: URL de Capturas Edge, acceso de evaluación si pide inicio de sesión y cómo llegar desde la navegación del portal previo.
  - Enlace al video, si se entrega.
- **Acceso de evaluación:** acceso limitado al portal y consulta de solo lectura de AWS; ninguna credencial dentro del paquete. La rúbrica prohíbe pedir claves de AWS, contraseñas personales o acceso administrativo.

## Cómo se cierra

- [ ] Edith o Bryan siguen el README de principio a fin sin ayuda
- [ ] Lista de comprobaciones ejecutada con resultados registrados
- [ ] Carpeta de evidencias completa, con todos los enlaces abriendo
- [ ] Sin credenciales reales en el repositorio ni en el paquete
- [ ] PR fusionado con review de Edith
- [ ] Estado de la tarjeta en **Hecho**

## Registro de avance

| Fecha | Quién | Bloque | Qué se hizo / PR | Pendiente |
|---|---|---|---|---|
