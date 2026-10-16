# EDGE-01 — Configuración física y evidencias

Configuración verificada mediante archivos generados en la Raspberry y
confirmaciones de Omar. La [ficha de configuración](edge-guia.md#ficha-edge-01)
registra hardware, cámara, runtime, modo manual, imagen completa y device_id.

## Archivos recibidos

| Evidencia | Resultado |
|---|---|
| [Hardware y runtime](../evidencias/EDGE-01/hardware-runtime.txt) | Raspberry Pi 4 Model B Rev 1.5, Debian 13.7, aarch64, Python 3.13.5, ONNX Runtime 1.31.0; CPUExecutionProvider disponible |
| [Reloj](../evidencias/EDGE-01/reloj.txt) | NTP activo, reloj sincronizado, America/Mexico_City |
| [JPEG original](../evidencias/EDGE-01/camara-nueva.jpg) | JPEG legible, 1920 × 1080, 62 556 bytes; contenido confirmado por Omar |
| [Verificación de captura](../evidencias/EDGE-01/captura-verificacion.txt) | Resultado de Pillow ejecutado en la Raspberry |
| [Hash del modelo local](../evidencias/EDGE-01/modelo-sha256.txt) | Coincide con la variante 1.0.0-int8-e05.1 |
| [Fotografía de la imagen abierta](<../evidencias/EDGE-01/WhatsApp Image 2026-10-15 at 9.33.10 PM.jpeg>) | Muestra la escena del JPEG en pantalla |
| [Montaje físico](<../evidencias/EDGE-01/WhatsApp Image 2026-10-15 at 9.53.13 PM.jpeg>) | Raspberry y teléfono conectado mediante cable USB |

También se recibieron cuatro PNG de Terminal:
`Captura de pantalla 2026-10-15 205153.png`,
`Captura de pantalla 2026-10-15 205227.png`,
`Captura de pantalla 2026-10-15 205238.png` y
`Captura de pantalla 2026-10-15 210845.png`.

El JPEG transferido se volvió a verificar localmente con Pillow: formato JPEG,
1920 × 1080, sin error de integridad. SHA-256 de la copia recibida:
`605479b4a5e4f8d28efee22f8933c5576328b7162869c4222b1cb751a289b21a`.

El modelo permanece en `/home/pi/edge01/modelo/model_int8.onnx`. Su hash reportado
por `sha256sum` es
`ba89ee435ce33e0f0cdd4e8ed84dfb50d74e5a3bc23c32af975085306ca02a12`.
No se recibió ni se ejecutó el binario en esta revisión local; EDGE-01 comprueba
su identidad y disponibilidad en la Raspberry. La inferencia corresponde a EDGE-03.

## Cámara y comando de captura

Omar confirmó expresamente POCO C65, sistema 2.0.208.0, IP Webcam 1.19.0.913 y
conexión mediante USB tethering. La identificación del modelo se basa en su
confirmación. En la fotografía del montaje se lee OPPO; se conserva como evidencia
del montaje, pero no como comprobación independiente del modelo exacto.
Inicio: conectar USB, habilitar anclaje USB y pulsar Iniciar servidor
en IP Webcam. Con `CAMERA_URL` apuntando a la dirección accesible del teléfono
terminada en `/shot.jpg`, ejecutó:

```bash
curl --fail --show-error --connect-timeout 5 --max-time 30 -H "Cache-Control: no-cache" "$CAMERA_URL" -o "$HOME/edge01/evidencias/EDGE-01/camara-nueva.jpg"
```

La transferencia terminó correctamente y Pillow confirmó un JPEG legible.
El tipo de enlace se registra por confirmación de Omar; las salidas de curl
por sí solas no distinguen USB de Wi-Fi.

## Pendientes de entrega

- Revisar e integrar el PR de EDGE-01. Los archivos locales todavía no están
  confirmados ni publicados en Git.

Estado: listo para publicación y revisión de EDGE-01, con evidencias recibidas
y modelo de cámara confirmado por Omar. No marcar DONE antes de completar
revisión y merge.
