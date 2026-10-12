import { act, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { EdgeCapture, EdgeCapturesResponse } from '../src/lib/api';
import EdgeCaptures, { splitIso } from '../src/pages/EdgeCaptures';

// Capturas Edge (P4, F5): la página solo usa `/api/p4/captures`; aquí `fetch` es falso.

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

function capture(overrides: Partial<EdgeCapture> = {}): EdgeCapture {
  return {
    schema_version: 1,
    capture_id: 'f4-prueba-20261008-0001',
    captured_at: '2026-10-08T23:35:54-06:00',
    predicted_class: 'dog',
    confidence: 0.8859987854957581,
    device_id: 'f4-prueba',
    model_version: '1.0.0-int8.1',
    model_sha256: 'ca689c4e1478ccca7821dffaba8f07886bd9609a8aa3cec7450d9f875fbd69c0',
    image_ref: 'capturas/f4-prueba-20261008-0001.jpg',
    image_sha256: 'c898dd126fb30a4e9de61b6a167c8ec3136b373fd919c21e92f5a93186d62f7a',
    region: null,
    received_at: '2026-10-09T05:53:22.210+00:00',
    image_key: 'edge-captures/images/f4-prueba-20261008-0001.jpg',
    image_bytes: 238034,
    image_width: 1204,
    image_height: 1600,
    delivery_delay_s: 1048.211,
    warnings: [],
    ...overrides,
  };
}

function listing(items: EdgeCapture[], errores: EdgeCapturesResponse['errores'] = []) {
  return { items, total: items.length, errores };
}

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('splitIso', () => {
  it('conserva la hora del dispositivo y hace explícita su zona', () => {
    expect(splitIso('2026-10-08T23:35:54-06:00')).toEqual({
      local: '2026-10-08 23:35:54',
      zone: 'UTC-06:00',
    });
    expect(splitIso('2026-10-09T05:53:22.210+00:00')).toEqual({
      local: '2026-10-09 05:53:22.210',
      zone: 'UTC',
    });
    expect(splitIso('2026-10-09T05:53:22Z').zone).toBe('UTC');
  });
});

describe('Capturas Edge', () => {
  it('pide el listado a /api/p4/captures y muestra los campos del registro', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(listing([capture()])));
    vi.stubGlobal('fetch', fetchMock);
    render(<EdgeCaptures />);

    const card = await screen.findByRole('article', { name: /f4-prueba-20261008-0001/ });
    expect(fetchMock).toHaveBeenCalledWith('/api/p4/captures?limit=100', undefined);
    const inCard = within(card);
    expect(inCard.getByText('dog')).toBeInTheDocument();
    expect(inCard.getByText('88.60 %')).toBeInTheDocument();
    expect(inCard.getByText('0.8859987854957581')).toBeInTheDocument();
    expect(inCard.getByText('f4-prueba')).toBeInTheDocument();
    expect(inCard.getByText(/1\.0\.0-int8\.1 · ca689c4e1478/)).toBeInTheDocument();
    expect(inCard.getByText('2026-10-08 23:35:54')).toBeInTheDocument();
    expect(inCard.getByText('(UTC-06:00)')).toBeInTheDocument();
    expect(inCard.getByText('2026-10-09 05:53:22.210')).toBeInTheDocument();
    expect(inCard.getByText(/sin recorte/)).toBeInTheDocument();
    expect(inCard.getByRole('img')).toHaveAttribute(
      'src',
      '/api/p4/captures/f4-prueba-20261008-0001/image',
    );
    expect(screen.getByText(/1 en total/)).toBeInTheDocument();
  });

  it('respeta el orden del backend (más reciente primero)', async () => {
    const items = [
      capture({ capture_id: 'nueva', captured_at: '2026-10-09T10:00:00-06:00' }),
      capture({ capture_id: 'vieja', captured_at: '2026-10-08T10:00:00-06:00' }),
    ];
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(listing(items))));
    render(<EdgeCaptures />);
    const cards = await screen.findAllByRole('article');
    expect(cards.map((card) => card.getAttribute('aria-label'))).toEqual([
      'Captura nueva',
      'Captura vieja',
    ]);
  });

  it('dibuja el recorte cuando region no es null', async () => {
    const withRegion = capture({
      // 1204×1600 px: 301/1204 = 400/1600 = 25 %, 602/1204 = 800/1600 = 50 %.
      region: { x: 301, y: 400, width: 602, height: 800 },
    });
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(listing([withRegion]))));
    render(<EdgeCaptures />);
    const region = await screen.findByTestId('edge-region');
    expect(region.style.left).toBe('25%');
    expect(region.style.top).toBe('25%');
    expect(region.style.width).toBe('50%');
    expect(region.style.height).toBe('50%');
    expect(screen.getByText(/x=301, y=400/)).toBeInTheDocument();
  });

  it('muestra los warnings del registro', async () => {
    const warned = capture({ warnings: ['captured_at_en_el_futuro'] });
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(listing([warned]))));
    render(<EdgeCaptures />);
    expect(await screen.findByText(/reloj del dispositivo adelantado/)).toBeInTheDocument();
  });

  it('muestra un mensaje de carga mientras llega el listado', () => {
    vi.stubGlobal('fetch', vi.fn().mockReturnValue(new Promise(() => {})));
    render(<EdgeCaptures />);
    expect(screen.getByText(/Cargando capturas desde AWS/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Actualizando…' })).toBeDisabled();
  });

  it('explica la lista vacía', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(listing([]))));
    render(<EdgeCaptures />);
    expect(await screen.findByText(/Todavía no hay capturas en AWS/)).toBeInTheDocument();
  });

  it('muestra el error del receptor y permite reintentar', async () => {
    const user = userEvent.setup();
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        jsonResponse(
          {
            error: 'almacenamiento_no_disponible',
            mensaje: 'S3 no aceptó la operación (AccessDenied). Vuelve a consultar en unos segundos',
            detalles: [],
          },
          503,
        ),
      )
      .mockResolvedValueOnce(jsonResponse(listing([capture()])));
    vi.stubGlobal('fetch', fetchMock);
    render(<EdgeCaptures />);

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('HTTP 503');
    expect(alert).toHaveTextContent('AccessDenied');
    expect(alert).toHaveTextContent(/reintentar/);

    await user.click(screen.getByRole('button', { name: 'Actualizar' }));
    expect(await screen.findByRole('article')).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('si una actualización falla, conserva la última lista y lo dice', async () => {
    const user = userEvent.setup();
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(listing([capture()])))
      .mockRejectedValueOnce(new TypeError('Failed to fetch'));
    vi.stubGlobal('fetch', fetchMock);
    render(<EdgeCaptures />);
    await screen.findByRole('article');

    await user.click(screen.getByRole('button', { name: 'Actualizar' }));
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('Failed to fetch');
    expect(alert).toHaveTextContent(/última lista que sí se cargó/);
    expect(screen.getByRole('article')).toBeInTheDocument();
  });

  it('muestra los registros que S3 no pudo leer', async () => {
    const errores = [{ record_key: 'edge-captures/events/roto.json', problema: 'JSON invalido' }];
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(listing([capture()], errores))));
    render(<EdgeCaptures />);
    const status = await screen.findByRole('status');
    expect(status).toHaveTextContent('edge-captures/events/roto.json');
    expect(status).toHaveTextContent('JSON invalido');
  });

  it('una captura nueva aparece al pulsar Actualizar', async () => {
    const user = userEvent.setup();
    const nueva = capture({ capture_id: 'f5-nueva', captured_at: '2026-10-09T12:00:00-06:00' });
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(listing([capture()])))
      .mockResolvedValueOnce(jsonResponse(listing([nueva, capture()])));
    vi.stubGlobal('fetch', fetchMock);
    render(<EdgeCaptures />);
    await screen.findByRole('article');

    await user.click(screen.getByRole('button', { name: 'Actualizar' }));
    expect(await screen.findByRole('article', { name: 'Captura f5-nueva' })).toBeInTheDocument();
    expect(screen.getAllByRole('article')[0]).toHaveAttribute('aria-label', 'Captura f5-nueva');
  });

  it('se actualiza sola cada 30 s y se puede apagar', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(listing([capture()])));
    vi.stubGlobal('fetch', fetchMock);
    render(<EdgeCaptures />);
    await screen.findByRole('article');
    expect(fetchMock).toHaveBeenCalledTimes(1);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(30_000);
    });
    expect(fetchMock).toHaveBeenCalledTimes(2);

    await act(async () => {
      screen.getByRole('checkbox').click();
      await vi.advanceTimersByTimeAsync(60_000);
    });
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it('enlaza la exportación CSV y JSON del backend', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(listing([capture()]))));
    render(<EdgeCaptures />);
    await screen.findByRole('article');
    expect(screen.getByRole('link', { name: 'CSV' })).toHaveAttribute(
      'href',
      '/api/p4/captures/export?format=csv',
    );
    expect(screen.getByRole('link', { name: 'JSON' })).toHaveAttribute(
      'href',
      '/api/p4/captures/export?format=json',
    );
  });
});
