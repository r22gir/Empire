'use client';

import { useState } from 'react';
import { API } from '../../lib/api';

export default function ReservationForm() {
  const [form, setForm] = useState({
    lot_number: '',
    buyer_name: '',
    price: '',
    separacion: '',
    cuota_inicial_pct: '30',
    installments: '24',
    balloon: '',
  });
  const [view, setView] = useState<any>(null);
  const [lotStatus, setLotStatus] = useState('reservado');
  const [confirmDeal, setConfirmDeal] = useState(false);
  const [message, setMessage] = useState('');

  function set(key: string, value: string) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function preview() {
    const res = await fetch(`${API}/construction/reservations/preview`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        lot_number: form.lot_number,
        buyer_name: form.buyer_name,
        price: form.price ? Number(form.price) : null,
        separacion: form.separacion ? Number(form.separacion) : null,
        cuota_inicial_pct: form.cuota_inicial_pct ? Number(form.cuota_inicial_pct) : null,
        installments: form.installments ? Number(form.installments) : null,
        balloon: form.balloon ? Number(form.balloon) : null,
        session_id: view?.session_id,
      }),
    });
    const data = await res.json();
    if (!data.draft && data.session_id) {
      const closed = await fetch(`${API}/voice/documents/sessions/${data.session_id}/close`, { method: 'POST' });
      setView(await closed.json());
      return;
    }
    setView(data);
  }

  async function confirm() {
    if (!view?.draft?.id) {
      setMessage('Primero arma el borrador.');
      return;
    }
    const res = await fetch(`${API}/construction/reservations/confirm`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        draft_id: view.draft.id,
        confirm: confirmDeal,
        lot_status: confirmDeal ? lotStatus : null,
      }),
    });
    const data = await res.json();
    setMessage(data.reason || (data.ok ? `Venta registrada. Lote ${data.lot_status}. No se envió nada.` : 'No se registró.'));
  }

  return (
    <div style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 12, padding: 16, marginBottom: 16 }}>
      <div style={{ fontSize: 14, fontWeight: 700 }}>Separar lote</div>
      <p style={{ fontSize: 12, color: '#666' }}>
        El paquete queda en borrador. El lote avanza un paso cuando confirmas: disponible, reservado, separado, vendido.
      </p>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 8 }}>
        <input placeholder="Lote" value={form.lot_number} onChange={(event) => set('lot_number', event.target.value)} />
        <input placeholder="Comprador" value={form.buyer_name} onChange={(event) => set('buyer_name', event.target.value)} />
        <input placeholder="Precio COP" value={form.price} onChange={(event) => set('price', event.target.value)} />
        <input placeholder="Separación" value={form.separacion} onChange={(event) => set('separacion', event.target.value)} />
        <input placeholder="% cuota inicial" value={form.cuota_inicial_pct} onChange={(event) => set('cuota_inicial_pct', event.target.value)} />
        <input placeholder="Meses" value={form.installments} onChange={(event) => set('installments', event.target.value)} />
      </div>
      <button type="button" onClick={preview} style={{ marginTop: 10, background: '#1a1a1a', color: '#fff', border: 'none', borderRadius: 8, padding: '8px 12px', cursor: 'pointer' }}>
        Armar borrador
      </button>
      {view?.options?.choices ? (
        <ul style={{ fontSize: 12, color: '#333' }}>
          {view.options.choices.slice(0, 3).map((choice: any) => (
            <li key={choice.id}>{choice.summary || choice.label}</li>
          ))}
        </ul>
      ) : null}
      {view?.draft ? (
        <div style={{ marginTop: 8, fontSize: 12 }}>
          <a href={`${API}/voice/documents/drafts/${view.draft.id}/preview`} target="_blank" rel="noreferrer">Vista previa DRAFT</a>
          <div style={{ marginTop: 8 }}>
            <label>
              <input type="checkbox" checked={confirmDeal} onChange={(event) => setConfirmDeal(event.target.checked)} /> Confirmo registrar la venta
            </label>
            <select value={lotStatus} onChange={(event) => setLotStatus(event.target.value)} style={{ marginLeft: 8 }}>
              <option value="reservado">Reservado</option>
              <option value="separado">Separado</option>
              <option value="vendido">Vendido</option>
            </select>
            <button type="button" onClick={confirm} style={{ marginLeft: 8 }}>Registrar</button>
          </div>
        </div>
      ) : null}
      {message ? <p style={{ fontSize: 12 }}>{message}</p> : null}
    </div>
  );
}
