#!/usr/bin/env bash
# Escribe los secretos de produccion en la EC2, sin imprimirlos (Proyecto4/docs/despliegue.md).
# Lo corre Emilio, con sudo, dentro de `aws ssm start-session`:
#
#   sudo bash /opt/p4/repo/Proyecto4/deploy/preparar_secretos.sh
#
# Pide (sin eco) lo que decide una persona:
#   - P4_DEVICE_TOKEN: token NUEVO del dispositivo (distinto del de desarrollo).
#   - Usuario y contrasena de basic_auth: el acceso limitado del evaluador.
# Genera al azar lo interno (MariaDB, MinIO), que nadie necesita conocer.
#
# Escribe, con permisos 600 y dueno root:
#   /opt/p4/repo/Proyecto2/.env       app, MariaDB, MinIO, token (ignorado por Git)
#   /opt/p4/secretos/caddy.env        dominio, usuario y hash bcrypt de basic_auth
# Si ya existen, pregunta antes de reemplazarlos.
set -euo pipefail

REPO=/opt/p4/repo
ENV_APP="$REPO/Proyecto2/.env"
ENV_CADDY=/opt/p4/secretos/caddy.env
CADDY_IMAGE=caddy:2.10.2

[ "$(id -u)" -eq 0 ] || { echo "Correr con sudo." >&2; exit 1; }
umask 077

for archivo in "$ENV_APP" "$ENV_CADDY"; do
	if [ -e "$archivo" ]; then
		read -r -p "$archivo ya existe. ¿Reemplazarlo? [s/N] " r
		[ "$r" = "s" ] || { echo "Sin cambios."; exit 0; }
	fi
done

# Dominio: la IP publica (la elastica, si ya esta asociada) con guiones + sslip.io.
imds_token="$(curl -fsS -X PUT http://169.254.169.254/latest/api/token -H 'X-aws-ec2-metadata-token-ttl-seconds: 60')"
ip="$(curl -fsS -H "X-aws-ec2-metadata-token: $imds_token" http://169.254.169.254/latest/meta-data/public-ipv4)"
site="${ip//./-}.sslip.io"
echo "Dominio del portal: https://$site  (MLflow: https://mlflow.$site)"

echo
echo "Token del dispositivo (P4_DEVICE_TOKEN). Generalo en TU maquina, por ejemplo:"
echo "  python -c \"import secrets; print(secrets.token_urlsafe(32))\""
read -r -s -p "Pega el token (no se muestra): " device_token
echo
[[ "$device_token" =~ ^[A-Za-z0-9_-]{32,}$ ]] || { echo "Token invalido: usa token_urlsafe(32) (solo A-Z a-z 0-9 _ -)." >&2; exit 1; }

echo
read -r -p "Usuario de basic_auth para el evaluador: " auth_user
[[ "$auth_user" =~ ^[A-Za-z0-9._-]{3,32}$ ]] || { echo "Usuario invalido (3-32: letras, digitos, . _ -)." >&2; exit 1; }
read -r -s -p "Contrasena (no se muestra, minimo 12): " pw1
echo
read -r -s -p "Repite la contrasena: " pw2
echo
[ "$pw1" = "$pw2" ] || { echo "No coinciden." >&2; exit 1; }
[ "${#pw1}" -ge 12 ] || { echo "Minimo 12 caracteres." >&2; exit 1; }

# El hash se calcula en un contenedor de Caddy; la contrasena viaja por variable de
# entorno (no por la linea de comandos) y nunca se escribe en disco.
auth_hash="$(PW="$pw1" docker run --rm -e PW "$CADDY_IMAGE" sh -c 'caddy hash-password --plaintext "$PW"')"
unset pw1 pw2
[[ "$auth_hash" == \$2* ]] || { echo "No se pudo calcular el hash." >&2; exit 1; }

aleatorio() { openssl rand -hex 24; }
commit="$(git -C "$REPO" rev-parse HEAD)"

# `.env` de la app: la plantilla del repo con los valores de produccion encima.
{
	grep -v -E '^(APP_ENV|DB_PASSWORD|DB_ROOT_PASSWORD|MINIO_ROOT_PASSWORD|P3_AWS_PROFILE|P4_AWS_PROFILE|P4_DEVICE_TOKEN)=' "$REPO/Proyecto2/.env.example"
	echo
	echo "# --- Produccion (preparar_secretos.sh, $(date -u +%FT%TZ)) ---"
	echo "APP_ENV=production"
	echo "DB_PASSWORD=$(aleatorio)"
	echo "DB_ROOT_PASSWORD=$(aleatorio)"
	echo "MINIO_ROOT_PASSWORD=$(aleatorio)"
	echo "P3_AWS_PROFILE="
	echo "P4_AWS_PROFILE="
	echo "P4_DEVICE_TOKEN=$device_token"
	echo "SITE_ADDRESS=$site"
	echo "P3_CODE_COMMIT=$commit"
} >"$ENV_APP"
unset device_token

# Comillas simples: compose no interpreta los `$` del hash bcrypt.
{
	echo "SITE_ADDRESS=$site"
	echo "BASIC_AUTH_USER=$auth_user"
	echo "BASIC_AUTH_HASH='$auth_hash'"
} >"$ENV_CADDY"
unset auth_hash

chown root:root "$ENV_APP" "$ENV_CADDY"
chmod 600 "$ENV_APP" "$ENV_CADDY"
echo
echo "Escritos (600, root): $ENV_APP y $ENV_CADDY. Ningun secreto se mostro."
echo "Para volver a ver el token cuando se lo pases a Bryan (en esta sesion, no en el chat):"
echo "  sudo grep '^P4_DEVICE_TOKEN=' $ENV_APP"
