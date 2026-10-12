import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import App from '../src/App';

// Las 5 páginas nuevas de P3 (F8 T03) que se suman a la navegación existente.
const P3_PAGES = ['Training', 'Experiments', 'Evaluation', 'Models', 'Inference'] as const;

describe('navegación del portal con las páginas de P3', () => {
  it('muestra las 5 páginas de P3 en el menú existente', () => {
    render(<App />);
    for (const label of P3_PAGES) {
      expect(
        screen.getByRole('button', { name: new RegExp(label) }),
      ).toBeInTheDocument();
    }
  });

  it('navega a cada página de P3 y renderiza su encabezado', async () => {
    const user = userEvent.setup();
    render(<App />);
    for (const label of P3_PAGES) {
      await user.click(screen.getByRole('button', { name: new RegExp(label) }));
      expect(
        screen.getByRole('heading', { level: 1, name: new RegExp(label) }),
      ).toBeInTheDocument();
    }
  });
});

describe('navegación del portal con Capturas Edge (P4, decisión 6)', () => {
  it('abre Capturas Edge desde el menú, entre Inference y Settings', async () => {
    const user = userEvent.setup();
    const { container } = render(<App />);
    const labels = Array.from(container.querySelectorAll('.nav .label')).map(
      (label) => label.textContent,
    );
    expect(labels.slice(labels.indexOf('Inference'))).toEqual([
      'Inference',
      'Capturas Edge',
      'Settings',
    ]);

    await user.click(screen.getByRole('button', { name: /Capturas Edge/ }));
    expect(
      screen.getByRole('heading', { level: 1, name: 'Capturas Edge' }),
    ).toBeInTheDocument();
    expect(window.location.hash).toBe('#/edge-captures');
  });
});
