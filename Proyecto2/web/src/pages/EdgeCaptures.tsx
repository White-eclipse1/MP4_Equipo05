/**
 * Capturas Edge (P4, F5): fotografías clasificadas en el dispositivo y guardadas en S3 (F4).
 *
 * Todo sale de `/api/p4/captures`, que lee los registros de S3: no hay datos fijos.
 * El orden es el del backend (de más reciente a más antigua por `captured_at` en UTC).
 * Un fallo al actualizar se muestra y NO borra lo que ya estaba cargado: quien mira
 * sabe que la lista puede estar desactualizada y por qué.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { Card, Pill } from '../components/ui';
import { ApiError, api, type EdgeCapture, type EdgeCapturesResponse } from '../lib/api';

const AUTO_REFRESH_MS = 30_000;

const WARNING_TEXT: Record<string, string> = {
  captured_at_en_el_futuro: 'reloj del dispositivo adelantado (fecha de captura en el futuro)',
};

/**
 * `2026-10-08T23:35:54-06:00` → `2026-10-08 23:35:54` y `UTC-06:00`.
 * Se muestra la hora tal como la escribió el dispositivo, con su zona explícita:
 * así coincide carácter por carácter con el registro de S3.
 */
export function splitIso(iso: string): { local: string; zone: string } {
  const match = /^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}:\d{2})(\.\d+)?(Z|[+-]\d{2}:\d{2})$/.exec(iso);
  if (!match) return { local: iso, zone: '' };
  const [, date, time, fraction, offset] = match;
  const zone = offset === 'Z' || offset === '+00:00' ? 'UTC' : `UTC${offset}`;
  return { local: `${date} ${time}${fraction ?? ''}`, zone };
}

function When({ iso, label }: { iso: string; label: string }) {
  const { local, zone } = splitIso(iso);
  return (
    <div>
      <span className="edge-key">{label}</span>{' '}
      <time dateTime={iso} className="mono">
        {local}
      </time>{' '}
      {zone && <span className="edge-zone">({zone})</span>}
    </div>
  );
}

function CapturePhoto({ capture, attempt }: { capture: EdgeCapture; attempt: number }) {
  const [failed, setFailed] = useState(false);
  // Cada «Actualizar» vuelve a intentar una imagen que falló.
  useEffect(() => setFailed(false), [attempt]);
  const { region, image_width: w, image_height: h } = capture;
  if (failed) {
    return (
      <div className="edge-photo edge-photo-missing" role="img" aria-label="imagen no disponible">
        No se pudo cargar la imagen desde S3 ({capture.image_key}). Pulsa Actualizar para
        reintentar.
      </div>
    );
  }
  return (
    <div className="edge-photo" style={{ aspectRatio: `${w} / ${h}` }}>
      <img
        src={api.p4.captureImageUrl(capture.capture_id)}
        alt={`Captura ${capture.capture_id}: ${capture.predicted_class}`}
        loading="lazy"
        onError={() => setFailed(true)}
      />
      {region && (
        <div
          className="edge-region"
          data-testid="edge-region"
          title={`Recorte clasificado: x=${region.x}, y=${region.y}, ${region.width}×${region.height} px`}
          style={{
            left: `${(region.x / w) * 100}%`,
            top: `${(region.y / h) * 100}%`,
            width: `${(region.width / w) * 100}%`,
            height: `${(region.height / h) * 100}%`,
          }}
        />
      )}
    </div>
  );
}

function CaptureCard({ capture, attempt }: { capture: EdgeCapture; attempt: number }) {
  return (
    <article className="edge-card" aria-label={`Captura ${capture.capture_id}`}>
      <CapturePhoto capture={capture} attempt={attempt} />
      <div className="edge-body">
        <div className="edge-title">
          <Pill kind="accent">{capture.predicted_class}</Pill>
          <span className="edge-conf" title={String(capture.confidence)}>
            {(capture.confidence * 100).toFixed(2)} %
          </span>
        </div>
        <div className="edge-meta">
          <div>
            <span className="edge-key">ID</span>{' '}
            <span className="mono">{capture.capture_id}</span>
          </div>
          <When iso={capture.captured_at} label="Capturada" />
          <When iso={capture.received_at} label="Recibida en AWS" />
          <div>
            <span className="edge-key">Dispositivo</span>{' '}
            <span className="mono">{capture.device_id}</span>
          </div>
          <div>
            <span className="edge-key">Modelo</span>{' '}
            <span className="mono" title={`SHA-256 ${capture.model_sha256}`}>
              {capture.model_version} · {capture.model_sha256.slice(0, 12)}…
            </span>
          </div>
          <div>
            <span className="edge-key">Confianza exacta</span>{' '}
            <span className="mono">{capture.confidence}</span>
          </div>
          <div>
            <span className="edge-key">Recorte</span>{' '}
            {capture.region ? (
              <span className="mono">
                x={capture.region.x}, y={capture.region.y}, {capture.region.width}×
                {capture.region.height} px
              </span>
            ) : (
              <span className="edge-zone">sin recorte (imagen completa)</span>
            )}
          </div>
        </div>
        {capture.warnings.length > 0 && (
          <div className="edge-warnings">
            {capture.warnings.map((warning) => (
              <Pill key={warning} kind="warn">
                {WARNING_TEXT[warning] ?? warning}
              </Pill>
            ))}
          </div>
        )}
      </div>
    </article>
  );
}

function describeError(error: unknown): string {
  if (error instanceof ApiError) {
    const hint =
      error.status === 503
        ? ' El portal no puede leer el almacenamiento de capturas en S3.'
        : '';
    return `HTTP ${error.status}: ${error.message}.${hint}`;
  }
  return error instanceof Error ? error.message : 'Error desconocido';
}

export default function EdgeCaptures() {
  const [data, setData] = useState<EdgeCapturesResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null);
  const [auto, setAuto] = useState(true);
  const inFlight = useRef(false);

  const load = useCallback(async () => {
    if (inFlight.current) return;
    inFlight.current = true;
    setLoading(true);
    try {
      const response = await api.p4.captures();
      setData(response);
      setError(null);
      setUpdatedAt(new Date());
    } catch (e: unknown) {
      // Se conserva `data`: lo ya cargado sigue visible, con el error encima.
      setError(describeError(e));
    } finally {
      inFlight.current = false;
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!auto) return;
    const timer = window.setInterval(() => {
      if (document.visibilityState === 'visible') void load();
    }, AUTO_REFRESH_MS);
    return () => window.clearInterval(timer);
  }, [auto, load]);

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Capturas Edge</h1>
          <p className="page-sub">
            Fotografías tomadas y clasificadas en el dispositivo edge con la variante optimizada,
            recibidas y guardadas en AWS S3. De más reciente a más antigua por fecha de captura.
          </p>
        </div>
        <div className="edge-actions">
          <button type="button" className="ghost" onClick={() => void load()} disabled={loading}>
            {loading ? 'Actualizando…' : 'Actualizar'}
          </button>
          <label className="edge-auto">
            <input type="checkbox" checked={auto} onChange={(e) => setAuto(e.target.checked)} />{' '}
            cada 30 s
          </label>
        </div>
      </div>

      {error && (
        <div className="banner fail" role="alert">
          No se pudieron cargar las capturas. {error} Puedes reintentar con «Actualizar».
          {data && ' Lo que ves abajo es la última lista que sí se cargó.'}
        </div>
      )}

      {data && data.errores.length > 0 && (
        <div className="banner warn" role="status">
          {data.errores.length === 1
            ? 'Un registro de S3 no se pudo leer y no aparece en la galería:'
            : `${data.errores.length} registros de S3 no se pudieron leer y no aparecen en la galería:`}
          <ul className="edge-errors">
            {data.errores.map((item) => (
              <li key={item.record_key}>
                <span className="mono">{item.record_key}</span>: {item.problema}
              </li>
            ))}
          </ul>
        </div>
      )}

      <Card
        title="Capturas"
        aside={
          data && (
            <span className="edge-zone">
              {data.items.length < data.total
                ? `Mostrando ${data.items.length} de ${data.total}`
                : `${data.total} en total`}
              {updatedAt && ` · actualizado ${updatedAt.toLocaleTimeString()}`}
              {' · '}
              <a href={api.p4.exportUrl('csv')}>CSV</a> ·{' '}
              <a href={api.p4.exportUrl('json')}>JSON</a>
            </span>
          )
        }
      >
        {data === null ? (
          loading ? (
            <p className="state">Cargando capturas desde AWS…</p>
          ) : (
            <p className="state">Sin datos que mostrar todavía.</p>
          )
        ) : data.items.length === 0 ? (
          <p className="state">
            Todavía no hay capturas en AWS. Cuando el dispositivo envíe una, aparecerá aquí al
            pulsar «Actualizar».
          </p>
        ) : (
          <div className="edge-grid">
            {data.items.map((capture) => (
              <CaptureCard
                key={capture.capture_id}
                capture={capture}
                attempt={updatedAt?.getTime() ?? 0}
              />
            ))}
          </div>
        )}
      </Card>
    </>
  );
}
