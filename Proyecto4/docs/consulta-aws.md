# Consulta de solo lectura en AWS — Capturas Edge (F4)

Para la demostración (rúbrica 4.2 y M3): muestra que una captura está persistida en AWS, en qué recurso vive y que su imagen y su registro coinciden. **Solo lectura:** `sts get-caller-identity`, `s3api head-object`, `s3api get-object` y `s3 ls`. No se entregan llaves al evaluador; el equipo ejecuta la consulta en vivo (decisión 5 en [`decisiones.md`](decisiones.md)).

| Recurso | Valor |
|---|---|
| Cuenta / región | `750702272375` / `us-east-1` |
| Bucket | `dataset-quality-releases-750702272375` (versionado, cifrado SSE, sin acceso público) |
| Imagen | `edge-captures/images/{capture_id}.jpg` (metadatos S3 `sha256` y `capture-id`) |
| Registro | `edge-captures/events/{capture_id}.json` |

## Comandos (PowerShell, listos para copiar)

Cambia `$P` por el perfil de quien consulta y `$ID` por la captura que elija el evaluador.

```powershell
$P  = "p4-emilio"
$B  = "dataset-quality-releases-750702272375"
$ID = "f4-prueba-20261008-0001"
$D  = Join-Path $env:TEMP "consulta-f4"; New-Item -ItemType Directory -Force $D | Out-Null

# 1. Quién consulta (usuario IAM de la cuenta del equipo)
aws sts get-caller-identity --profile $P --query Arn --output text

# 2. El registro existe en S3: versión y fecha
aws s3api head-object --profile $P --bucket $B --key "edge-captures/events/$ID.json" --query "{VersionId:VersionId,LastModified:LastModified,Bytes:ContentLength,Tipo:ContentType}" --output table

# 3. Contenido del registro
aws s3api get-object --profile $P --bucket $B --key "edge-captures/events/$ID.json" "$D\$ID.json" --query VersionId --output text
Get-Content "$D\$ID.json" -Raw | ConvertFrom-Json | Format-List capture_id,captured_at,predicted_class,confidence,device_id,model_version,model_sha256,image_sha256,received_at,image_key

# 4. La imagen existe: versión, fecha y SHA-256 guardado en sus metadatos
$meta = aws s3api head-object --profile $P --bucket $B --key "edge-captures/images/$ID.jpg" --query "Metadata.sha256" --output text; $meta
aws s3api head-object --profile $P --bucket $B --key "edge-captures/images/$ID.jpg" --query "{VersionId:VersionId,LastModified:LastModified,Bytes:ContentLength}" --output table

# 5. Descargar la imagen y recalcular su SHA-256: debe coincidir con metadatos y registro
aws s3api get-object --profile $P --bucket $B --key "edge-captures/images/$ID.jpg" "$D\$ID.jpg" --query VersionId --output text
$calc = (Get-FileHash "$D\$ID.jpg" -Algorithm SHA256).Hash.ToLower(); $calc
$reg  = (Get-Content "$D\$ID.json" -Raw | ConvertFrom-Json).image_sha256
"metadatos = descargada: $($meta -eq $calc) | registro = descargada: $($reg -eq $calc)"

# 6. Un solo registro y una sola imagen con ese ID
aws s3 ls "s3://$B/edge-captures/" --recursive --profile $P | Select-String $ID
```

En Linux o macOS: los mismos `aws ...`, con `sha256sum` en lugar de `Get-FileHash`.

## Resultado probado (9 oct de 2026, perfil `p4-emilio`)

| Paso | Resultado |
|---|---|
| 1 | `arn:aws:iam::750702272375:user/dataset-quality-emilio` |
| 2 | Registro: 727 bytes, `application/json`, `VersionId` `Ti1VGCMyvBfeilNL8XS0Siut6LiSBsgS`, `LastModified` `2026-10-09T05:53:23+00:00` |
| 3 | `capture_id` `f4-prueba-20261008-0001`, `dog`, `0.8859987854957581`, `f4-prueba`, `1.0.0-int8.1`, `received_at` `2026-10-09T05:53:22.210+00:00` |
| 4 | Imagen: 238 034 bytes, `VersionId` `icZio54eDr2va6q3uSInCXuBD1UWlThQ`, metadato `sha256` `c898dd126fb30a4e9de61b6a167c8ec3136b373fd919c21e92f5a93186d62f7a` |
| 5 | SHA-256 de la imagen descargada igual al de metadatos y al del registro: `True` / `True` |
| 6 | Una línea de `events/` y una de `images/` para el ID |

## Por qué esto demuestra AWS y no solo una URL

- La identidad (paso 1) es un usuario IAM de la cuenta del equipo, y los objetos se leen con la API de S3 de esa cuenta: no hay URL pública (el bucket bloquea el acceso público).
- `VersionId` y `LastModified` los asigna S3; el evaluador puede pedir otro ID de captura y repetir la consulta.
- La imagen descargada tiene el mismo SHA-256 que el registro y que el evento local del dispositivo (`image_sha256`), lo que vincula la foto con sus metadatos (4.1).
- El portal (F5) muestra el mismo registro: `GET /api/p4/captures/{id}` lo lee del mismo objeto de S3.

## Acceso de solo lectura para el evaluador (opcional)

La rúbrica acepta que el equipo ejecute la consulta en vivo; un acceso temporal y limitado de lectura también vale, nunca llaves administrativas.

- El usuario `dataset-quality-evaluator` está definido en Terraform (`Proyecto2/terraform/modules/team_access/main.tf`, `create_evaluator = true` por defecto) con `s3:ListBucket`, `ListBucketVersions`, `GetBucketLocation`, `GetObject` y `GetObjectVersion` sobre el bucket. Esos permisos alcanzan para los pasos 2 a 6; el paso 1 (`sts get-caller-identity`) no requiere permisos.
- **No probado con ese usuario:** en la máquina de Emilio no hay un perfil configurado para él. Para probarlo hace falta que el PM confirme que el usuario existe en la cuenta y genere una llave de acceso temporal fuera de Terraform (`aws iam create-access-key`), que se configure en la máquina de la demo como un perfil aparte (por ejemplo `aws configure --profile p4-evaluador`) y que la llave se desactive o borre después de la evaluación. La llave nunca va a Git ni al evaluador por escrito.
- Con el perfil del evaluador, la consulta es la misma cambiando `$P`.
