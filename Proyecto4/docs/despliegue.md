# Despliegue del portal en AWS — F5

Portal de los Proyectos 1 a 3 (web y API de P2 con P3) más Capturas Edge (P4), en una EC2 con Docker Compose. P1 no se despliega (decisión del PM). Archivos:

| Archivo | Para qué |
|---|---|
| [`Proyecto2/docker-compose.prod.yml`](../../Proyecto2/docker-compose.prod.yml) | Stack de producción: sin volúmenes de código ni `--reload`, solo Caddy publica puertos, límites de memoria |
| [`Proyecto2/docker/Dockerfile`](../../Proyecto2/docker/Dockerfile) (etapa `prod`) | Imagen del portal con `Proyecto3/src`, `Proyecto4/src` y `reports/` dentro |
| [`Proyecto4/deploy/Caddyfile`](../deploy/Caddyfile) | HTTPS (Let's Encrypt sobre `sslip.io`) y `basic_auth` en todo menos `POST /api/p4/captures` |
| [`Proyecto4/deploy/instalar_instancia.sh`](../deploy/instalar_instancia.sh) | Docker, compose, buildx, swap y clon del repo público en la EC2 |
| [`Proyecto4/deploy/preparar_secretos.sh`](../deploy/preparar_secretos.sh) | Escribe los secretos en la EC2 sin mostrarlos |

## Arquitectura

```
Pi (F3) ──POST /api/p4/captures + Bearer token──┐
Evaluador ──HTTPS + basic_auth──────────────────┤
                                                 ▼
  EC2 t3.medium (us-east-1a) · SG p4-portal-sg: 80, 443 · IP elástica · <ip>.sslip.io
  ┌─ caddy :80/:443 ─► app :8000 (web + API P2/P3/P4) ─► mariadb, minio, mcp, mlflow, p3-inference
  │                                                     └─ p3-worker
  └─ rol de instancia p4-portal-ec2 (IMDSv2, hop limit 2) ─► S3 dataset-quality-releases-…
```

- Sin llaves personales: la app usa el rol de instancia (`P3_AWS_PROFILE` y `P4_AWS_PROFILE` vacíos). El *hop limit* 2 es indispensable: los contenedores están un salto más lejos del servicio de metadatos.
- Sin SSH: puerto 22 cerrado; acceso con `aws ssm start-session`.
- Acceso del evaluador: usuario y contraseña de `basic_auth` (decisión 6). El dispositivo solo necesita el token.

## b) Memoria: cabe en una t3.medium (4 GiB)

Medido en local (9 oct), en reposo:

| Servicio | Desarrollo | Producción | Cómo |
|---|---:|---:|---|
| mlflow | 2 294 MiB | **351 MiB** | `MLFLOW_SERVER_ENABLE_JOB_EXECUTION=false` (7 procesos `huey` de jobs de GenAI que P3 no usa) y `--workers 1`. Medido con un contenedor de prueba |
| p3-inference | 297 MiB | ≈ 300 MiB | Tope 1 GiB (picos al cargar el modelo) |
| app | 270 MiB | ≈ 270 MiB | Tope 768 MiB, sin `--reload` |
| p3-worker | 195 MiB | ≈ 200 MiB | Tope 1.5 GiB; entrenar en la nube no es objetivo del despliegue |
| minio | 175 MiB | ≈ 175 MiB | Tope 384 MiB |
| mariadb | 117 MiB | ≈ 120 MiB | Tope 384 MiB |
| mcp | 86 MiB | ≈ 90 MiB | Tope 256 MiB |
| caddy | — | ≈ 30 MiB | Tope 128 MiB |
| **Total contenedores** | **≈ 3.4 GiB** | **≈ 1.5 GiB** | |

Con el sistema (≈ 0.4 GiB) quedan unos 2 GiB libres más 2 GiB de swap (`vm.swappiness=10`, solo para picos). **Conclusión: t3.medium alcanza**; la t3.large solo haría falta para entrenar en la instancia.

**Construir `p3-inference` (torch CPU) en la instancia es viable:** la imagen pesa ≈ 2 GiB y el `pip install` del wheel de CPU necesita ≈ 1 GiB de RAM. Se construye **antes** de levantar el stack (toda la memoria libre) y tarda ≈ 10-15 min. Disco: imágenes ≈ 6 GiB + caché de build ≈ 3 GiB → volumen de 30 GiB.

## c) Cómo llega el código

El repositorio `sebastian0023/Proyecto-3-Clasificador-de-imagenes` es **público** (verificado el 9 oct con la API de GitHub). `instalar_instancia.sh` lo clona por HTTPS **sin credenciales** y fija el commit indicado: no queda ningún token personal en la instancia y el commit desplegado se puede citar. Actualizar = `git fetch` + `checkout` del commit nuevo + `build` + `up -d`.

## d) Plan paso a paso

Comandos de AWS para Git Bash, siempre con `--profile p4-emilio --region us-east-1` (se omiten abajo por espacio). En Git Bash, `run-instances` necesita `MSYS_NO_PATHCONV=1` delante: si no, convierte `/dev/xvda` en una ruta de Windows y AWS responde `InvalidBlockDeviceMapping`. Cada paso que crea o modifica algo se autoriza por separado. Valores ya verificados con lecturas:

| Dato | Valor |
|---|---|
| VPC por defecto | `vpc-0d050a1c3a92dcdb8` |
| Subnet (us-east-1a, IP pública) | `subnet-0b1edac74e6b7aada` |
| AMI Amazon Linux 2023 x86_64 | `ami-0d27e0fb3bac4d724` (`al2023-ami-2023.12.20260930.0`) |
| Perfil de instancia | `p4-portal-ec2` (existe, con el rol `p4-portal-ec2`) |

### Costo (us-east-1, on-demand, aproximado)

| Recurso | Precio | 9 → 16 oct (7 días, 24 h) |
|---|---|---:|
| t3.medium | $0.0416/h | $7.00 |
| EBS gp3 30 GiB | $0.08/GiB-mes | $0.56 |
| IPv4 pública (IP elástica) | $0.005/h | $0.84 |
| Transferencia de salida | primeros 100 GB/mes gratis | ≈ $0 |
| **Total** | | **≈ $8.40** (≈ $1.20/día) |

Detenida, la instancia no cobra cómputo, pero el disco y la IP elástica siguen (≈ $0.20/día).

### 0. Simulacros sin efecto (`--dry-run`)

Comprueban permisos sin crear nada (respuesta esperada: `DryRunOperation`; `UnauthorizedOperation` = falta permiso).

```bash
aws ec2 create-security-group --dry-run --group-name p4-portal-sg --description "Portal P4: solo HTTP y HTTPS" --vpc-id vpc-0d050a1c3a92dcdb8 --tag-specifications 'ResourceType=security-group,Tags=[{Key=Project,Value=p4-portal},{Key=Name,Value=p4-portal-sg}]'
aws ec2 run-instances --dry-run --image-id ami-0d27e0fb3bac4d724 --instance-type t3.medium --subnet-id subnet-0b1edac74e6b7aada --iam-instance-profile Name=p4-portal-ec2 --metadata-options HttpTokens=required,HttpPutResponseHopLimit=2,HttpEndpoint=enabled --block-device-mappings 'DeviceName=/dev/xvda,Ebs={VolumeSize=30,VolumeType=gp3,Encrypted=true,DeleteOnTermination=true}' --tag-specifications 'ResourceType=instance,Tags=[{Key=Project,Value=p4-portal},{Key=Name,Value=p4-portal}]' 'ResourceType=volume,Tags=[{Key=Project,Value=p4-portal}]' --count 1
aws ec2 allocate-address --dry-run --domain vpc --tag-specifications 'ResourceType=elastic-ip,Tags=[{Key=Project,Value=p4-portal}]'
```

(El `run-instances` del simulacro usa el SG `default` de la VPC solo porque `p4-portal-sg` aún no existe.)

### 1. Security group (sin costo)

```bash
aws ec2 create-security-group --group-name p4-portal-sg --description "Portal P4: solo HTTP y HTTPS" --vpc-id vpc-0d050a1c3a92dcdb8 --tag-specifications 'ResourceType=security-group,Tags=[{Key=Project,Value=p4-portal},{Key=Name,Value=p4-portal-sg}]' --query GroupId --output text
aws ec2 authorize-security-group-ingress --group-id <sg-id> --ip-permissions 'IpProtocol=tcp,FromPort=80,ToPort=80,IpRanges=[{CidrIp=0.0.0.0/0,Description=ACME y redireccion a HTTPS}]' 'IpProtocol=tcp,FromPort=443,ToPort=443,IpRanges=[{CidrIp=0.0.0.0/0,Description=Portal HTTPS}]'
```

Sin regla para el 22. La salida queda abierta (la necesitan `dnf`, GitHub, Let's Encrypt y S3).

### 2. Instancia ($0.0416/h desde que arranca)

```bash
aws ec2 run-instances --image-id ami-0d27e0fb3bac4d724 --instance-type t3.medium --subnet-id subnet-0b1edac74e6b7aada --security-group-ids <sg-id> --iam-instance-profile Name=p4-portal-ec2 --metadata-options HttpTokens=required,HttpPutResponseHopLimit=2,HttpEndpoint=enabled --block-device-mappings 'DeviceName=/dev/xvda,Ebs={VolumeSize=30,VolumeType=gp3,Encrypted=true,DeleteOnTermination=true}' --tag-specifications 'ResourceType=instance,Tags=[{Key=Project,Value=p4-portal},{Key=Name,Value=p4-portal}]' 'ResourceType=volume,Tags=[{Key=Project,Value=p4-portal}]' --count 1 --query 'Instances[0].InstanceId' --output text
aws ec2 wait instance-running --instance-ids <i-id>
aws ec2 describe-instances --instance-ids <i-id> --query 'Reservations[0].Instances[0].{Estado:State.Name,IMDS:MetadataOptions,Perfil:IamInstanceProfile.Arn}'
```

### 3. IP elástica ($0.005/h; reemplaza la IP pública automática)

```bash
aws ec2 allocate-address --domain vpc --tag-specifications 'ResourceType=elastic-ip,Tags=[{Key=Project,Value=p4-portal}]' --query '[AllocationId,PublicIp]' --output text
aws ec2 associate-address --instance-id <i-id> --allocation-id <eipalloc-id>
```

El portal queda en `https://<a-b-c-d>.sslip.io` (la IP con guiones; `sslip.io` resuelve ese nombre a la IP sin registrar dominio).

### 4. Entrar por SSM (sin costo extra)

```bash
aws ssm describe-instance-information --filters Key=InstanceIds,Values=<i-id> --query 'InstanceInformationList[0].PingStatus' --output text
aws ssm start-session --target <i-id>
```

Tarda 1-2 min en aparecer `Online`. Desde aquí, todo ocurre **dentro de la sesión** y lo escribe Emilio.

### 5. Verificar el rol en S3 — primer paso dentro de la instancia

```bash
aws s3 ls s3://dataset-quality-releases-750702272375/models/clasificador-edge/1.0.0-int8.1/
echo "verificacion del rol p4-portal-ec2 $(date -u +%FT%TZ)" > /tmp/verificacion.txt
aws s3api put-object --bucket dataset-quality-releases-750702272375 --key edge-captures/_verificacion/despliegue-20261009.txt --body /tmp/verificacion.txt --if-none-match '*'
```

La escritura va a `edge-captures/_verificacion/`, fuera de `events/` e `images/`: no aparece en la galería y `--if-none-match` impide pisar nada. **Si alguna de las dos falla, detenerse** (la política del rol no es la esperada) y avisar al PM.

### 6. Preparar la instancia y escribir los secretos

`<commit>` es el commit publicado que se despliega; el que se usó queda en el Registro de avance de F5.

```bash
curl -fsSL https://raw.githubusercontent.com/sebastian0023/Proyecto-3-Clasificador-de-imagenes/<commit>/Proyecto4/deploy/instalar_instancia.sh -o /tmp/instalar_instancia.sh
sudo bash /tmp/instalar_instancia.sh <commit>
sudo bash /opt/p4/repo/Proyecto4/deploy/preparar_secretos.sh
```

`instalar_instancia.sh` es idempotente: si una corrida se corta (por ejemplo, en el swap), se vuelve a correr igual. No reinstala paquetes ni plugins que ya estén, rehace un `/swapfile` incompleto (otro tamaño o sin firma de swap), no vuelve a clonar y no duplica `/etc/fstab`. Para ver el estado antes de reanudar:

```bash
swapon --show; ls -l /swapfile; sudo blkid -p -s TYPE -o value /swapfile; ls -d /opt/p4/repo/.git
```

`preparar_secretos.sh` pide, **sin mostrarlos**: el token nuevo del dispositivo (generado en tu máquina con `python -c "import secrets; print(secrets.token_urlsafe(32))"`), el usuario y la contraseña de `basic_auth`. Escribe `/opt/p4/repo/Proyecto2/.env` y `/opt/p4/secretos/caddy.env` (600, root). Contraseñas internas de MariaDB y MinIO: al azar.

### 7. Construir y levantar

```bash
cd /opt/p4/repo/Proyecto2
sudo docker compose -f docker-compose.prod.yml build
sudo docker compose -f docker-compose.prod.yml up -d
sudo docker compose -f docker-compose.prod.yml ps
sudo docker compose -f docker-compose.prod.yml logs caddy --tail 30
free -h && sudo docker stats --no-stream
```

Opcional (corridas del barrido en Experiments y manifiestos en Training; requiere que el rol lea `dataset-quality-dvc-cache-750702272375`):

```bash
sudo docker compose -f docker-compose.prod.yml run --rm --no-deps --user 0 -v /opt/p4/repo/Proyecto3:/p3 -w /p3 app dvc pull data/manifests/m-0.1.3-s42-1.dvc data/manifests/m-0.1.3-s7-1.dvc mlflow_snapshot.dvc
sudo docker compose -f docker-compose.prod.yml restart mlflow-restore mlflow
```

### 8. Verificar HTTPS y el acceso (desde la máquina de Emilio, PowerShell)

```bash
curl.exe -sI http://<a-b-c-d>.sslip.io/
curl.exe -sI https://<a-b-c-d>.sslip.io/
curl.exe -sv -o NUL https://<a-b-c-d>.sslip.io/ 2>&1 | findstr /i "issuer subject expire"
curl.exe -s -o NUL -w "%{http_code}\n" https://<a-b-c-d>.sslip.io/api/p4/captures
curl.exe -s -o NUL -w "%{http_code}\n" -u <usuario> https://<a-b-c-d>.sslip.io/api/p4/captures
curl.exe -s -o NUL -w "%{http_code}\n" -X POST https://<a-b-c-d>.sslip.io/api/p4/captures
```

| Comprobación | Esperado |
|---|---|
| `http://` | `308` hacia `https://` |
| `https://` sin credenciales | `401` con `WWW-Authenticate: Basic` |
| Certificado | emitido por Let's Encrypt para `<a-b-c-d>.sslip.io` |
| `GET /api/p4/captures` sin / con `basic_auth` | `401` / `200` (curl pide la contraseña: no queda en el historial) |
| `POST /api/p4/captures` sin token | `401 no_autorizado` de la app (Caddy lo deja pasar; la app exige el token) |

La captura de prueba por HTTPS (con ID aprobado) se envía con `Proyecto4/scripts/enviar_captura.py --url https://<a-b-c-d>.sslip.io/api/p4/captures`, con el token de producción en la variable de entorno `P4_DEVICE_TOKEN` de esa consola (no en un archivo).

**Plan B de HTTPS** si Let's Encrypt rechaza el nombre de `sslip.io`: CloudFront delante de la EC2 (dominio `*.cloudfront.net`). Necesita permisos de CloudFront que hoy no hay: se pide al PM.

### 9. Apagar y limpiar

| Cuándo | Comando | Efecto |
|---|---|---|
| Pausa (noches, fin de semana) | `aws ec2 stop-instances --instance-ids <i-id>` | Sin costo de cómputo; disco e IP siguen (≈ $0.20/día). Los datos se conservan |
| Reanudar | `aws ec2 start-instances --instance-ids <i-id>` | La IP elástica se conserva: misma URL y mismo certificado |
| Tras la entrega (16 oct) | `aws ec2 terminate-instances --instance-ids <i-id>` y luego `aws ec2 release-address --allocation-id <eipalloc-id>` | Borra la instancia y su disco; libera la IP |
| Tras terminar | — | Borrar `p4-portal-sg` lo hace el PM (no hay permiso `DeleteSecurityGroup`) |

Lo que queda en S3 (`edge-captures/`) no se borra: es la evidencia de la entrega.

## Despliegue actual (9 oct de 2026)

| Recurso | Valor |
|---|---|
| URL | `https://174-129-84-80.sslip.io` (MLflow: `https://mlflow.174-129-84-80.sslip.io`) |
| Commit desplegado | `978681ab0c0f0884e94d52b321ea387d9e1711b9` |
| Instancia | `i-0348c123c4c126267` (t3.medium, us-east-1a), volumen `vol-0e820472328aa1584` |
| Security group | `sg-03ef1c4d438238594` (`p4-portal-sg`) |
| IP elástica | `174.129.84.80` (`eipalloc-028fd049cafd50d82`) |

## Limitaciones conocidas

- P1 no se despliega: «Enviar a cola» de Inference responde 502.
- Sin `dvc pull` (paso 7, opcional) Experiments no muestra las corridas del barrido y Training no lista manifiestos; Exploración y las miniaturas de Evaluation necesitan además el dataset y los recortes, que no se llevan a la instancia.
- `quality.yaml` y `reports/` se pueden modificar desde Settings dentro del contenedor, pero esos cambios se pierden al recrearlo (los versionados están en Git).
- Mejora opcional: el `401` que responde `basic_auth` no incluye `Strict-Transport-Security` (las respuestas de la app sí). No es un riesgo práctico porque el puerto 80 solo redirige a HTTPS.
