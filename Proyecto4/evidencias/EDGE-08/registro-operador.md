# EDGE-08 — Registro de reproducción por otro integrante

Copia de `docs/edge08-registro.template.md`. **Todavía no se ejecuta ningún paso en
la Raspberry.** Lo que dice "Esperado" sale de la documentación de Omar (EDGE-01 a
EDGE-07) y se confirma o corrige con lo que se observe en la corrida. No incluir
tokens, contraseñas ni enlaces temporales.

| Dato | Valor |
|---|---|
| Operador (Lemus o Josué) | Josué (GitHub `JGO-07`) |
| Fecha y zona horaria | Pendiente: anotar al ejecutar (`date --iso-8601=seconds` en la Raspberry) |
| Commit del repositorio utilizado | Pendiente: `git rev-parse HEAD` de la copia desde la que se transfieran los scripts. Runbook revisado en `origin/EDGE-08` @ `8eab76602b3ae5d598af4c34918f9321c853935d` |
| Dispositivo | Pendiente de confirmar. Esperado (EDGE-01): Raspberry Pi 4 Model B Rev 1.5, Debian 13 ARM64 |
| Cámara y versión de app | Pendiente de confirmar. Esperado (EDGE-01): POCO C65, IP Webcam 1.19.0.913, anclaje USB |
| Python / ONNX Runtime | Pendiente de confirmar. Esperado: Python 3.13.5, ONNX Runtime 1.31.0 |
| Modelo, versión y SHA-256 | `1.0.0-int8-e05.1`, `ba89ee435ce33e0f0cdd4e8ed84dfb50d74e5a3bc23c32af975085306ca02a12`. Copia de la laptop de Josué verificada el 2026-10-16: `Proyecto4/modelo/artefactos/1.0.0-int8-e05.1/model_int8.onnx` da ese hash. **Falta verificarlo en la Raspberry** |
| Ruta/versión del runbook utilizado | `Proyecto4/docs/edge08-runbook.md`, rama `EDGE-08` @ `8eab766` |
| Ejecución sin instrucciones adicionales de Omar | Pendiente. Ver los huecos detectados antes de ejecutar (abajo) |

Dependencias del runbook: EDGE-07 (PR #48) e INT-06 (PR #46) ya están fusionados en `main`.

## Resultados

Ningún paso se ha ejecutado todavía.

| Paso | Resultado observado | Evidencia |
|---|---|---|
| Entorno, NTP y hash comprobados | Pendiente | `evidencias/EDGE-08/entorno.txt` |
| Captura física nueva y predicción local | Pendiente | `evidencias/EDGE-08/normal/` |
| Envío aceptado y duplicado | Pendiente | `evidencias/EDGE-08/envios.jsonl` |
| Foto/clase/modelo visibles en portal | Pendiente | |
| Historial de estabilidad y recuperación de EDGE-07 revisado | Pendiente | `docs/edge07-operacion.md` y `evidencias/EDGE-07/` (de Omar; no se atribuyen al operador) |
| Modelo cargado antes de desconectar | Pendiente | `evidencias/EDGE-08/offline/` |
| Red offline registrada antes y después de dos capturas | Pendiente | `offline/red-offline-antes.txt`, `offline/red-offline-despues.txt` |
| Dos capturas offline con clases diferentes | Pendiente | `offline/` |
| HTTP exitoso antes de tercera inferencia | Pendiente | `offline/red-reconectada.txt` |
| Misma sesión/PID antes y después de reconectar | Pendiente | `offline/` |
| Nuevo proceso y modelo recargado al reiniciar | Pendiente | `evidencias/EDGE-08/reinicio/` |
| Foto nueva tras reinicio; misma configuración e historial conservado | Pendiente | `evidencias/EDGE-08/reinicio/` |

## Incidencias e instrucciones que faltaron

### Revisión previa (2026-10-16, antes de ejecutar)

Se leyó el runbook y se comparó con la laptop del operador. Estos huecos aparecen
antes de llegar a la Raspberry. Cada uno se marca al final como **resuelto con la
guía**, **resuelto con ayuda** (quién) o **bloqueó el paso**.

1. **Transferencia desde Windows sin WSL Ubuntu ni rsync (paso 1).** El runbook solo
   da `wsl -d Ubuntu` + `rsync`. La laptop del operador solo tiene la distro WSL
   `docker-desktop` y no tiene `rsync`. Sí tiene `scp` (OpenSSH de Windows). Falta
   una alternativa con `scp` desde PowerShell, o pedir instalar Ubuntu en WSL.
   Estado: pendiente.
2. **Ruta del modelo en la laptop (paso 2).** El runbook copia
   `$PROYECTO/modelo/model_int8.onnx`, pero `convertir.py` lo deja en
   `modelo/artefactos/1.0.0-int8-e05.1/model_int8.onnx` (así está en la laptop del
   operador). Hay que corregir la ruta en la guía. Estado: pendiente.
3. **IP y acceso SSH a la Raspberry (paso 1).** Pide "IP actual de la Raspberry",
   pero no dice cómo obtenerla (por ejemplo, `hostname -I` en la consola local) ni
   cómo recibe el operador la contraseña o llave del usuario `pi`. Estado: pendiente.
4. **Token del dispositivo (paso 3).** Solo dice "por canal privado". `docs/despliegue.md`
   lo lee con `--profile p4-equipo`, pero el perfil de AWS del operador se llama
   `p4-josue`. La guía debería dar el comando con un perfil genérico (`<tu-perfil>`).
   Estado: pendiente.
5. **Qué copia del repositorio usar.** Pide "una copia que incluya todos los scripts
   citados" sin decir la rama ni el commit. El checkout del operador está en otra
   rama (`feat/p4-val-08-paquete`). La guía debería decir `main` (después de fusionar
   EDGE-08) o el commit exacto. Estado: pendiente.
6. **Verificación en el portal (paso 4).** Dice "El responsable del portal debe
   verificar". Si lo hace Diego, ese paso no es del operador. Falta indicar cómo lo
   comprueba el propio operador (usuario `evaluador`, contraseña en Parameter Store
   `/p4/portal-evaluador`). Estado: pendiente.

### Durante la ejecución

Pendiente. Anotar aquí cada error, la solución aplicada y si hizo falta ayuda (de
quién). Si hubo ayuda, incorporarla al runbook y repetir el paso antes de declarar
reproducción independiente.

## Confirmación del operador

Pendiente. La escribe Josué con sus propias palabras al terminar: qué pasos pudo
reproducir, cuáles quedaron pendientes, nombre y fecha.
