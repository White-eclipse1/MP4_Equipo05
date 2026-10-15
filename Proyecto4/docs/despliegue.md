# Despliegue del portal en AWS (INT-01)

El portal de los Proyectos 1 a 3 con la sección **Capturas Edge** corre en una EC2 de la cuenta del equipo, detrás de Caddy con HTTPS. El receptor de capturas guarda en S3 con el **rol de la instancia**: no hay llaves de AWS en archivos, variables ni en el repositorio.

## Dónde está

| Dato | Valor |
|---|---|
| Portal | **https://54-80-197-58.sslip.io** (Capturas Edge en `#/capturas-edge`) |
| MLflow | https://mlflow.54-80-197-58.sslip.io |
| Receptor del dispositivo | `POST https://54-80-197-58.sslip.io/api/p4/capturas` (contrato en [`contrato-capturas.md`](contrato-capturas.md)) |
| Cuenta / región | `474665692638` / `us-east-1` |
| Instancia | `i-06a5651301e9b6c39`, `t3.medium`, Amazon Linux 2023, disco gp3 de 30 GB cifrado, IMDSv2 obligatorio (2 saltos para los contenedores), **sin llave SSH** |
| IP elástica | `54.80.197.58` (`eipalloc-011c7d71d4e101f41`) |
| Grupo de seguridad | `sg-0515e8eed7bc45e78` (`p4-portal-sg`): solo 80 y 443 |
| Rol / perfil de instancia | `p4-portal-ec2`: política [`deploy/politica-ec2.json`](../deploy/politica-ec2.json) + `AmazonSSMManagedInstanceCore` |
| Bucket | `p4-capturas-474665692638`: privado, cifrado, con versionado; capturas en `edge-capturas/` |
| Alerta de gasto | `p4-edge-mensual`, 20 USD al mes |

## Permisos del rol (mínimos)

- **Capturas:** leer y escribir en `edge-capturas/*` del bucket. **Sin `DeleteObject`**: el receptor nunca borra.
- **Modelos:** solo lectura de `modelos/*` y `models/*`.
- **Listado:** `ListBucket` limitado a esos prefijos.
- **Secretos:** `ssm:PutParameter` y `ssm:GetParameter` en `/p4/*`.
- **Administración:** Session Manager, sin SSH.

La política pasa la validación de IAM Access Analyzer sin hallazgos.

## Acceso de evaluación

- **Portal y MLflow:** usuario `evaluador` con `basic_auth` de Caddy. Solo `POST /api/p4/capturas` queda fuera, y lo protege el token del dispositivo.
- **Secretos:** la contraseña y el token se generan **dentro de la instancia** al instalar y se guardan cifrados en Parameter Store. Nunca pasan por el repositorio ni por el chat. Para leerlos, desde una terminal con acceso a la cuenta:

  ```bash
  aws ssm get-parameter --name /p4/portal-evaluador --with-decryption --query Parameter.Value --output text --profile p4-equipo --region us-east-1
  ```

  ```bash
  aws ssm get-parameter --name /p4/token-dispositivo --with-decryption --query Parameter.Value --output text --profile p4-equipo --region us-east-1
  ```

  La contraseña se entrega al evaluador por un canal privado; el token, al dispositivo (variable `P4_TOKEN_DISPOSITIVO`).

## Cómo se instaló

[`deploy/instalar_ec2.sh`](../deploy/instalar_ec2.sh) se pasó como user-data al lanzar la instancia, con las variables `P4_DOMINIO`, `P4_BUCKET`, `P4_RAMA` y `P4_MODELOS_ACEPTADOS` al inicio. El script:

1. **Docker:** instala Docker, Compose v5.5.1 y Buildx v0.37.1, y agrega 2 GiB de swap.
2. **Código:** clona el repositorio en `/opt/p4/repo`.
3. **Secretos:** genera `Proyecto2/.env` (contraseñas aleatorias) y `/opt/p4/secretos/caddy.env` (hash bcrypt), ambos con permisos `600`.
4. **Arranque:** levanta `docker compose -f docker-compose.yml -f docker-compose.aws.yml up -d --build` y espera a que la app quede sana.

En [`Proyecto2/docker-compose.aws.yml`](../../Proyecto2/docker-compose.aws.yml), solo Caddy publica puertos; la base de datos, MinIO, MLflow y la app quedan en la red interna de Docker. El registro de la instalación queda en `/var/log/p4-instalacion.log` de la instancia.

## Operación (Session Manager, sin SSH)

Ver el estado de los contenedores:

```bash
aws ssm send-command --instance-ids i-06a5651301e9b6c39 --document-name AWS-RunShellScript --parameters 'commands=["cd /opt/p4/repo/Proyecto2 && docker compose -f docker-compose.yml -f docker-compose.aws.yml ps"]' --profile p4-equipo --region us-east-1
```

Actualizar el código desplegado:

```bash
aws ssm send-command --instance-ids i-06a5651301e9b6c39 --document-name AWS-RunShellScript --parameters 'commands=["cd /opt/p4/repo && sudo -u ec2-user git pull && cd Proyecto2 && docker compose -f docker-compose.yml -f docker-compose.aws.yml up -d --build"]' --profile p4-equipo --region us-east-1
```

Cambiar los modelos aceptados por el receptor: editar `P4_MODELOS_ACEPTADOS` en `/opt/p4/repo/Proyecto2/.env` y volver a correr el `up -d` de arriba.

## Costo y apagado

Alrededor de 1.2 USD al día (EC2 `t3.medium`, IP pública y disco). Después de la evaluación, apagar o terminar la instancia y liberar la IP elástica: una IP elástica sin instancia también cobra.
