# Guion de la demostración (INT-04, INT-06, INT-08)

Sigue el orden en que la rúbrica observa el recorrido ([`rubrica.md`](rubrica.md), "B. Observar el recorrido"). Duración objetivo: 10 a 15 minutos. Cada paso dice **quién** lo hace, **qué se muestra** y **con qué comando**, para que nadie improvise.

> ⏳ = depende del programa del dispositivo (Omar, EDGE-02 a EDGE-08); se completa cuando exista. Los comandos de AWS y del portal ya están probados.

## Roles en la demostración

| Persona | Hace |
|---|---|
| Omar | Opera el dispositivo y la cámara; lee en voz alta el `capture_id` de cada captura |
| Diego | Portal (Capturas Edge), consulta de solo lectura en AWS y fallo y reintento del envío |
| Josué | Modelo: linaje del P3, comparación de calidad y benchmark (paso 9) |
| Mauricio | Conduce, controla el tiempo y anota los `capture_id` que pide el evaluador |

## Antes de la demostración

**Un día antes** (y otra vez 30 minutos antes):

- [ ] Portal arriba: https://54-80-197-58.sslip.io abre y pide usuario. Con `evaluador` entra y se ve Capturas Edge.
- [ ] Contraseña del evaluador lista para entregarla por privado:
  ```powershell
  aws ssm get-parameter --name /p4/portal-evaluador --with-decryption --query Parameter.Value --output text --profile p4-equipo --region us-east-1
  ```
- [ ] Sesiones de AWS vigentes: `p4-lectura` (consultas de S3 en la demo, solo lectura) y `p4-equipo` (solo para leer secretos y operar la EC2). Comprobar con `aws sts get-caller-identity --profile <perfil>`; si caducó, `aws login --profile <perfil>`. **Duran máximo 12 horas: renovarlas la mañana de la demo.**
- [ ] Consulta de solo lectura probada con una captura existente:
  ```powershell
  .\Proyecto2\.venv\Scripts\python.exe Proyecto4\scripts\consultar_captura.py <capture_id> --profile p4-lectura
  ```
- [ ] Contenedores sanos (Session Manager, ver [`despliegue.md`](despliegue.md), "Operación").
- [ ] ⏳ Dispositivo cargado, cámara conectada, programa probado con una captura nueva.
- [ ] ⏳ Tres objetos a mano: un gato (foto o peluche), un perro y una persona.
- [ ] Pestañas abiertas: portal en Capturas Edge, la [ficha del P4](../README.md), las evidencias de calidad y de benchmark.

## Recorrido

### 1. Dispositivo, modelo y runtime (Omar y Josué, 2 min)

- ⏳ Omar arranca el programa: en pantalla aparecen la versión `1.0.0-int8-e05.1` y el SHA-256 `ba89ee43…2a12` del modelo cargado, el runtime y el `device_id`.
- Josué muestra el origen en la [ficha del modelo](modelo-optimizado.md) y el [linaje](linaje-modelo.md): `model.pt` del P3 1.0.0 (`e4acca42…`) → conversión INT8 con registro de SHA-256.

### 2. Capturas nuevas con objetos que elige el evaluador (Omar, 2 min)

- ⏳ El evaluador elige y acomoda los objetos; Omar captura cada uno. El dispositivo muestra la clase, la confianza y el tiempo de inferencia, y guarda la foto y el evento en su registro local.

### 3. Sin red (Omar, 1 min)

- ⏳ Con el modelo ya cargado, Omar **desconecta la red** del dispositivo (wifi apagado o cable fuera) y captura otra vez: sigue clasificando. El envío de esa captura falla y el error se ve en pantalla. **Esa captura no se sube después**: la rúbrica no lo exige.

### 4. Reconexión y captura nueva (Omar, 1 min)

- ⏳ Omar reconecta la red y hace una captura nueva, que se envía. Lee su `capture_id` en voz alta y Mauricio lo anota.

### 5. La captura llega a AWS (Diego, 2 min)

Con el `capture_id` del paso 4:

```powershell
.\Proyecto2\.venv\Scripts\python.exe Proyecto4\scripts\consultar_captura.py <capture_id> --profile p4-lectura
```

Se muestra:

- **Dónde está:** el registro y la foto en `s3://p4-capturas-474665692638/edge-capturas/`, con el `VersionId` y la fecha que asignó S3.
- **Que la foto es la misma:** su SHA-256 recalculado, igual al de los metadatos de S3 y al del evento del dispositivo.
- **Que no hubo duplicados:** una sola versión de cada objeto.

Termina en `Resultado: OK`.

### 6. La misma captura en el portal (Diego, 1 min)

- Desde el menú del portal: **Capturas Edge**. Pulsar **Actualizar**: la captura del paso 4 aparece arriba, con la misma foto, clase, confianza, fechas, `capture_id`, dispositivo y versión del modelo.
- Recargar la página (F5): sigue ahí. También se actualiza sola cada 30 segundos.

### 7. Fallo de envío controlado y reintento sin duplicado (Omar y Diego, 2 min, INT-04)

Fallo **reversible y solo del lado del dispositivo**; no se toca AWS ni el portal:

1. ⏳ Omar desconecta la red del dispositivo, o cambia `P4_RECEPTOR_URL` a una dirección inválida, y hace una captura. En pantalla se ve el error del envío ("sin respuesta del receptor") y que la foto y el evento quedaron en el registro local.
2. ⏳ Omar restablece la red (o la URL) y **reintenta ese mismo evento**: mismo `capture_id` y mismo `captured_at`, releídos del registro local. La respuesta es `201 creado` si el primer intento no llegó, o `200 duplicado` si sí había llegado.
3. Diego corre la consulta del paso 5 con ese `capture_id`: **una sola versión** del registro y de la foto. En Capturas Edge aparece una sola vez.

Respaldo, si el dispositivo falla: la misma secuencia de respuestas (201, 200 duplicado, 409, 422, 401) ya está probada contra el receptor desplegado en [`evidencias/int-02/`](../evidencias/int-02/).

### 8. Reinicio del programa (Omar, 1 min)

- ⏳ Omar cierra el programa y lo vuelve a abrir: muestra otra vez la versión y el hash del modelo, el historial local sigue ahí y una captura nueva se clasifica y se envía.

### 9. Contraste de calidad o de latencia (Josué, 2 min)

- ⏳ El evaluador elige un ID de la comparación de calidad o una fila del benchmark. Josué lo reproduce: la misma imagen da la misma clase con el original y con el INT8, o el mismo rango de tiempo en el dispositivo.

## Si algo falla durante la demostración

| Falla | Qué hacer |
|---|---|
| El portal no abre | Revisar los contenedores por Session Manager (`docker compose ... ps`); si hace falta, `docker compose ... up -d` (ver [`despliegue.md`](despliegue.md)). No reiniciar la instancia: la IP elástica se conserva, pero tarda varios minutos |
| La consulta de AWS dice que la sesión caducó | `aws login --profile p4-equipo` y repetir |
| El envío responde 401 | El token del dispositivo no coincide: leerlo otra vez de Parameter Store (`/p4/token-dispositivo`) |
| El envío responde 422 | Leer los `detalles`: indican qué campo no cumple el [contrato](contrato-capturas.md). No se reintenta: se corrige |
| La captura no aparece en el portal | Pulsar **Actualizar**; revisar que el envío respondió 201 o 200 y correr la consulta del paso 5 |

## Después de la evaluación

Apagar o terminar la EC2 y liberar la IP elástica para no generar costo (ver [`despliegue.md`](despliegue.md), "Costo y apagado").
