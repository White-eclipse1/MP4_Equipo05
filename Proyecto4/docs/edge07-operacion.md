# EDGE-07 — Operación continua y reinicio

`edge/operacion.py` reutiliza cámara, inferencia y eventos de EDGE-02/03/05.
Carga el modelo una vez por proceso y guarda JPEG, registro de cámara, evento
del contrato y resultados de inferencia de cada captura. No envía al portal.
La integración real se verifica con `enviar.py` y las evidencias de EDGE-06.

## Dependencias y alcance

El cierre de EDGE-07 requiere EDGE-04, EDGE-06 y VAL-07. Se puede preparar el
código y ejecutar la serie física mientras VAL-07 está pendiente, pero la serie
no sustituye esa validación de preprocesamiento. La evidencia física de este
ticket se incorpora después de ejecutar el protocolo en la Raspberry.

## Serie de más de cinco minutos

Distribuir `operacion.py` a `/home/pi/edge01/app/`. Conservar camara.py,
inferencia.py, eventos.py y el preprocesador/modelo de los tickets anteriores.

```bash
cd "$HOME/edge01"
source .venv/bin/activate
python -u app/operacion.py --modelo modelo/model_int8.onnx --url "$CAMERA_URL" --cantidad 21 --intervalo 16 --fase continua --salida evidencias/EDGE-07
```

Definir CAMERA_URL con la dirección HTTP local real terminada en /shot.jpg.
Antes de comenzar, preparar sujetos o representaciones de gato, perro y persona.
Si se usan imágenes en pantalla, documentar esa condición. La cámara debe tomar
fotografías físicas nuevas; el programa no lee una carpeta de fotos como entrada.

El programa espera un Enter inicial y luego toma 21 fotos automáticamente:
1–7 de gato, 8–14 de perro y 15–21 de persona. Anuncia la clase a presentar antes
de cada espera. Cambiar encuadre o escena para cada foto. La primera es inmediata;
entre las siguientes espera 16 s más el tiempo de captura/inferencia/escritura.
Veinte esperas suman 320 s: no cerrar la Terminal durante la serie.

Las clases solicitadas son instrucciones al operador, no etiquetas que fuerzan
la predicción. El resumen cuenta las clases realmente predichas. Para acreditar
reparto entre las tres clases debe existir al menos un resultado de cada clase,
además de revisión visual de las escenas capturadas.

## Reinicio del programa

Cuando la serie termine y aparezca el prompt de la Terminal, ejecutar un proceso
nuevo con el mismo modelo, URL, device_id e intervalo:

```bash
python -u app/operacion.py --modelo modelo/model_int8.onnx --url "$CAMERA_URL" --cantidad 1 --intervalo 16 --fase reinicio --salida evidencias/EDGE-07
```

Presentar una escena nueva de gato y pulsar Enter. No es necesario reiniciar el
sistema operativo. La nueva sesión debe volver a cargar el modelo con hash
correcto, conservar config_sha256 y agregar una captura al historial existente.

## Archivos y verificación

- `operacion.jsonl`: cargas de modelo, session_id, PID, configuración identificada
  por SHA-256, fallos, eventos completos, predicciones y resumen de cada sesión.
- `historial.jsonl`: export de eventos del contrato de todas las sesiones.
- `sesiones/<session_id>/configuracion.json`: configuración sin tokens.
- `sesiones/<session_id>/capturas/`: JPEG y registros de cámara.
- `sesiones/<session_id>/eventos/`: JSON completos del contrato.

La duración se mide con reloj monotónico; `serie_s` excluye la espera inicial
del operador y la carga del modelo. `entre_primera_ultima_captura_s` permite
contrastar que el periodo contenga capturas reales. Un fallo queda en el log
y el programa intenta la captura siguiente; no se inventa una predicción.
Si no hay fallos se esperan 21 eventos en la serie y uno tras reiniciar.

Conservar los originales y capturas de Terminal de carga, progreso, resumen y
nuevo arranque. Verificar al menos 20 eventos únicos, fechas con zona, JPEG/hash
correspondientes, clases/confianzas y modelo, serie >=300 s y una captura posterior
al reinicio con la misma configuración. Si hay fallos, conservarlos y comprobar
los conteos reales antes de afirmar cumplimiento.

## Evidencia física del 16 de octubre de 2026

Archivos originales en [`evidencias/EDGE-07/`](../evidencias/EDGE-07/), con
export `historial.jsonl`, log `operacion.jsonl`, carpetas por sesión y capturas
de Terminal en `capturas_pantalla/`.

| Comprobación | Resultado |
|---|---|
| Sesión continua | 25c10a75e5d94c95b3c5ec3c1dd412cc, PID 2379 |
| Carga del modelo | 18:52:14, versión 1.0.0-int8-e05.1, CPUExecutionProvider |
| Serie física | 21 capturas completas; 326.52 s; cero fallos |
| Predicciones reales de la serie | cat 10, dog 4, person 7 |
| Sesión de reinicio | 3496bcee8b764806bb1e922b8d92a877, PID 2416 |
| Recarga correcta | 18:59:41, mismo hash del modelo |
| Captura posterior al reinicio | Un evento nuevo; sesión finalizada a las 19:00:14 |
| Configuración de ambas sesiones | 919f0ac833954b3eb50c99fe709360a363d5d79b75f3c66d93783095c9162862 |
| Historial acumulado | 22 eventos, 22 capture_id únicos y 22 JPEG |

La revisión verificó JPEG legibles y SHA-256 coincidentes entre fotos, registros
de cámara y eventos; fechas con zona, clase/confianza concordantes con los logs
de inferencia y export completo. Las configuraciones guardadas producen el mismo
hash en ambas sesiones. Las fechas de captura de la serie abarcan 326.03 s,
coherentes con la duración monotónica registrada. El reinicio utiliza otro proceso
y vuelve a cargar el modelo, conservando la configuración y el historial.

Las cantidades por clase son predicciones observadas, no los siete objetivos por
clase que solicita el protocolo. No implican que todas las clasificaciones hayan
sido correctas. La sesión corta muestra false en el criterio combinado de 20
capturas/cinco minutos/tres clases; ese requisito lo acredita la sesión continua.
La corrida no tuvo fallos físicos; la continuidad ante fallo se prueba localmente
con un doble de cámara y no se presenta como un fallo ocurrido en esta serie.

Prueba local desde Proyecto4, sin cámara ni esperas reales:

```bash
python -m unittest discover -s edge -p test_operacion.py -v
```

Comprueba continuidad tras fallo, export y coincidencia de configuración entre
sesiones. No acredita duración ni capturas físicas; estas requieren la corrida real.
