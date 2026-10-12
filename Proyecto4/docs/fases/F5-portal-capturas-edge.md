# F5 — Portal: sección Capturas Edge

| Campo | Valor |
|---|---|
| Responsable | Emilio (Líder de AWS · portal · integración) |
| Revisor de PRs | Edith |
| Fechas | 8 oct → 9 oct de 2026 |
| Rama | `feat/p4-fase-5-portal-capturas-edge` |
| Puntos de rúbrica | 10 (5.1, 5.2 y 5.3) |
| Depende de | F4 |
| Bloquea a | F6 |
| Control | Control 2 |

**Nota de calendario:** empieza el jueves 8 con la consulta de F4 y queda desplegada el viernes 9, antes del primer recorrido completo.

> Antes de empezar lee `AGENTS.md`, `docs/decisiones.md` (ubicación de Capturas Edge) y `docs/contratos.md`. Trabaja los bloques en orden.

## Rúbrica (10 puntos)

- **5.1 Integración y acceso (3):** sección accesible desde la navegación del portal de los Proyectos 1 a 3, desplegada en AWS. Una galería aislada vale como máximo 1.5.
- **5.2 Imagen y metadatos reales (4):** fotografía, clase, confianza, fecha, ID, dispositivo y versión coinciden con los registros de AWS, de más reciente a más antigua.
- **5.3 Consulta funcional (3):** una captura nueva aparece al refrescar; carga, lista vacía y error tienen mensajes útiles.

## Bloques de trabajo

- [x] **Navegación:** sección accesible desde el menú del portal existente y desplegada en AWS. — Entrada `Capturas Edge` (`#/edge-captures`) en `PAGES` de `Proyecto2/web/src/App.tsx`, entre Inference y Settings (decisión 6). Desplegada en `https://174-129-84-80.sslip.io` (EC2 + Docker Compose + Caddy, ver [`despliegue.md`](../despliegue.md)); abierta desde el menú con el usuario del evaluador (evidencia `navegador_prueba.jpeg`, `navegador_https.jpeg`).
- [x] **Galería:** fotografía, clase, confianza, fecha, ID de captura, dispositivo y versión del modelo; recorte si aplica. — [`Proyecto2/web/src/pages/EdgeCaptures.tsx`](../../../Proyecto2/web/src/pages/EdgeCaptures.tsx): foto de `GET /api/p4/captures/{id}/image`, `captured_at` con su zona explícita, `received_at` en UTC, confianza en % y exacta, recorte dibujado sobre la foto y warnings.
- [x] **Orden y actualización:** de más reciente a más antigua, con botón de actualizar o actualización automática. — Orden del backend; botón «Actualizar» y auto-actualización cada 30 s (desactivable, solo con la pestaña visible).
- [x] **Estados:** mensajes para carga, error y lista vacía. — Carga, lista vacía, error con código y mensaje del receptor (si falla una actualización se conserva la última lista y se avisa), `errores` del listado e imagen que no carga. Pruebas en [`Proyecto2/web/tests/edge-captures.test.tsx`](../../../Proyecto2/web/tests/edge-captures.test.tsx).
- [x] **Acceso de evaluación:** si el portal pide inicio de sesión, preparar un acceso limitado para el evaluador. — Usuario `evaluador` y contraseña de Caddy (`basic_auth`) en todo el portal excepto `POST /api/p4/captures` (decisión 6, confirmado con el PM). Probado: sin credenciales, `/`, `/api/p4/captures`, imagen, exportación, `/health`, `/docs` y MLflow responden `401`; el `POST` sin token o con token falso responde `401 no_autorizado` de la app (evidencia `https_verificacion.txt`).

## Cómo se cierra

- [x] La sección abre desde la navegación del portal desplegado (`https://174-129-84-80.sslip.io/#/edge-captures` con `basic_auth`; `navegador_prueba.jpeg`)
- [x] Muestra los registros reales de F4, no datos fijos (`f4-prueba-20261008-0001` de F4 y las capturas nuevas leídas de S3 por `/api/p4/captures`; la página no tiene datos fijos)
- [x] Los metadatos coinciden con los de AWS en una captura de prueba (`f5-https-20261009-0001`, enviada por HTTPS al portal desplegado: los 11 campos del registro en S3 iguales al evento enviado, imagen con el mismo SHA-256; el portal la muestra arriba con person 99.94 % al pulsar Actualizar; `head_object_f5_https.txt`, `navegador_https.jpeg`)
- [ ] PR fusionado con review de Edith
- [ ] Estado de la tarjeta en **Hecho**

## Registro de avance

| Fecha | Quién | Bloque | Qué se hizo / PR | Pendiente |
|---|---|---|---|---|
| 2026-10-09 | Emilio | Galería, orden y estados (local) | Página Capturas Edge en el portal (React, solo endpoints de F4, sin datos fijos). `api.ts` lee también `mensaje` de los errores del receptor de P4. Pruebas web: Vitest 71 (13 nuevas de la página y 1 de navegación), `npm test` 5, `npm run build` OK; P4 96; Proyecto2 278 en el contenedor. Verificado en local (Vite contra el portal en Docker, que lee S3 con `p4-emilio`): aparece `f4-prueba-20261008-0001` con dog, 0.8859987854957581, `f4-prueba`, `1.0.0-int8.1`, 2026-10-08 23:35:54 (UTC-06:00), igual que en S3. | Captura nueva al pulsar Actualizar (falta foto e ID aprobados); despliegue en AWS (Parte 2). |
| 2026-10-09 | Emilio | Despliegue (preparación, sin recursos creados) | Lecturas con `p4-emilio`: perfil de instancia `p4-portal-ec2` existe; VPC por defecto `vpc-0d050a1c3a92dcdb8`, subnet `subnet-0b1edac74e6b7aada`; AMI AL2023 `ami-0d27e0fb3bac4d724`; repo público. Archivos: `docker-compose.prod.yml` (sin volúmenes de código, solo Caddy publica 80/443, topes de memoria), etapa `prod` del Dockerfile (P3 y P4 dentro de la imagen; base compose fija `target: app`), `Caddyfile` (validado con `caddy validate`), `instalar_instancia.sh` y `preparar_secretos.sh` (ShellCheck sin advertencias) y [`docs/despliegue.md`](../despliegue.md). MLflow sin jobs y con 1 worker: 2 294 → 351 MiB (medido): el stack cabe en t3.medium (≈ 1.5 GiB en reposo). | Crear SG, instancia e IP elástica (cada paso con visto bueno); verificar el rol en S3; captura por HTTPS. |
| 2026-10-09 | Emilio | Despliegue (recursos creados) | Con visto bueno paso a paso: SG `sg-03ef1c4d438238594` (`p4-portal-sg`, solo 80/443), instancia `i-0348c123c4c126267` (t3.medium, AL2023, perfil `p4-portal-ec2`, IMDSv2 hop limit 2, gp3 30 GiB cifrado, sin llave SSH), IP elástica `174.129.84.80` (`eipalloc-028fd049cafd50d82`) → `https://174-129-84-80.sslip.io`; SSM `Online`. Rol verificado dentro de la instancia: `assumed-role/p4-portal-ec2/…`, lectura de `models/` y escritura de `edge-captures/_verificacion/despliegue-20261009.txt` (VersionId `U2hiSKuVVXcbwy7W0zij9rmJodnlYiVs`). | `instalar_instancia.sh` falló en el swap (`mkswap -q` no existe en AL2023). |
| 2026-10-09 | Emilio | Despliegue (arreglo del script) | `instalar_instancia.sh`: `mkswap` sin `-q`; idempotente sobre una instancia a medias (no reinstala paquetes ni plugins, rehace un `/swapfile` sin firma o de otro tamaño, no vuelve a clonar y clona aparte para no dejar `/opt/p4/repo` a medias, no duplica `/etc/fstab`, `vm.swappiness` en `/etc/sysctl.d`). Probado en un contenedor con util-linux 2.37.4 y coreutils 8.32 (las versiones de AL2023; Rocky Linux 9 porque `dnf` de amazonlinux:2023 no descargaba desde Docker Desktop): 4 escenarios OK (swapfile a medias como en la EC2, segunda corrida, tamaño incorrecto, `/opt/p4/repo` sin `.git` → falla con mensaje). bash -n y ShellCheck (nivel style) limpios. | Volver a correrlo en la EC2 con el commit nuevo; secretos; build y up. |
| 2026-10-09 | Emilio | Despliegue (portal arriba) | En la EC2, con el commit `978681ab0c0f0884e94d52b321ea387d9e1711b9`: `instalar_instancia.sh` (swap rehecho, repo clonado), `preparar_secretos.sh` (token nuevo de producción y `basic_auth` del evaluador, escritos por Emilio sin mostrarse), `docker compose -f docker-compose.prod.yml build` y `up -d --wait`: todos los servicios sanos; Caddy obtuvo de Let's Encrypt los certificados de `174-129-84-80.sslip.io` y `mlflow.174-129-84-80.sslip.io` (TLS 1.3, vencen el 7 ene 2027). Memoria en reposo 1.7 GiB de 3.7 GiB, swap sin uso. Verificado desde fuera: `http` → `308` a `https`; sin credenciales todo responde `401`; `POST /api/p4/captures` sin token o con token falso → `401 no_autorizado`. | **Mejora opcional:** el `401` de `basic_auth` no incluye `Strict-Transport-Security` (las respuestas de la app sí); no afecta porque el 80 redirige a HTTPS. |
| 2026-10-09 | Emilio | Captura por HTTPS y metadatos | `f5-https-20261009-0001` (foto de Emilio; person 0.9993854761123657 con `scripts/inferir_captura.py` en x86, no en la Pi; `captured_at` = hora de guardado del archivo, sin EXIF), enviada con `enviar_captura.py --url https://174-129-84-80.sslip.io/api/p4/captures` y el token de producción en la consola → `201 created`. En S3: imagen VersionId `ERpIgwQdRzt1T6CNdnV_URwsWME.d4kN` (837 884 B, `sha256` `157869ff…eedd` igual a la foto) y registro VersionId `AIM1r9Ri1vM1RPS3NaGrTHslis4xAIia`, 11/11 campos iguales al evento. En el portal desplegado, al pulsar Actualizar: «3 en total» y `f5-https` arriba con person 99.94 %. | PR de F5 con review de Edith; tarjeta en Hecho. |

## Evidencia para F10

Fuera del repo, en `C:\MLOps_Project_Four\evidencia_f5\` (se copia a la carpeta de evidencias en F10, sin tokens, contraseñas, hashes de `basic_auth` ni rutas sensibles):

| Archivo | Qué demuestra |
|---|---|
| `local_capturas_edge.jpg`, `local_pagina_texto.txt`, `local_api_listado.json` | La sección en local mostrando `f4-prueba-20261008-0001` con los mismos datos que S3 |
| `local_antes_actualizar.jpg`, `local_despues_actualizar.jpg` | Captura nueva (`f5-prueba-20261009-0001`) que aparece arriba al pulsar Actualizar |
| `inferencia_f5_x86.json`, `evento_f5-prueba-20261009-0001.json`, `envio_f5.txt`, `head_object_f5.txt` | Predicción, evento, respuesta `201` y llaves en S3 de `f5-prueba` |
| `aws_sg_creado.json`, `aws_sg_reglas.json` | Security group `p4-portal-sg` etiquetado, solo 80 y 443 |
| `aws_instance_id.txt`, `aws_instancia.json`, `aws_volumen.json` | EC2 con rol, IMDSv2 hop limit 2, sin llave SSH, disco cifrado y etiquetas |
| `aws_eip.txt`, `aws_eip.json` | IP elástica `174.129.84.80` asociada |
| `aws_verificacion_rol.json` | Escritura del rol de instancia en `edge-captures/_verificacion/` |
| `prueba_instalar.sh`, `prueba_instalar_salida.txt` | Prueba del script de instalación (4 escenarios) |
| `https_verificacion.txt` | Redirección a HTTPS, certificados de Let's Encrypt, `401` sin credenciales y `POST` sin token rechazado |
| `navegador_prueba.jpeg` | La sección abierta desde la navegación del portal desplegado, con `basic_auth` |
| `inferencia_f5_https_x86.json`, `evento_f5-https-20261009-0001.json`, `envio_f5_https.txt`, `head_object_f5_https.txt` | Captura por HTTPS: predicción, evento, `201` y llaves en S3 con los mismos metadatos |
| `navegador_https.jpeg` | La captura por HTTPS arriba en el portal desplegado («3 en total», person 99.94 %) |
