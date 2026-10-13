'use client';
import { useState } from 'react';
import { LifeBuoy, Send, CheckCircle2 } from 'lucide-react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '/api/v1';

export default function PedirAyudaMax() {
  const [subject, setSubject] = useState('');
  const [message, setMessage] = useState('');
  const [status, setStatus] = useState<'idle' | 'sending' | 'sent' | 'error'>('idle');
  const [error, setError] = useState('');
  const [proposal, setProposal] = useState<string | null>(null);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setStatus('sending');
    setError('');
    try {
      const res = await fetch(`${API_BASE.replace(/\/$/, '')}/family-help/pedir-ayuda`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          edition: 'amp',
          subject,
          message,
          requester_name: typeof window !== 'undefined' ? localStorage.getItem('amp-name') || undefined : undefined,
        }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `Error ${res.status}`);
      }
      const body = await res.json();
      setProposal(body.proposed_action_summary || null);
      setStatus('sent');
      setSubject('');
      setMessage('');
    } catch (err) {
      setStatus('error');
      setError(err instanceof Error ? err.message : 'No se pudo enviar');
    }
  };

  return (
    <section className="bg-white rounded-3xl p-6 border border-gold-light/30 shadow-sm">
      <h3 className="font-serif text-xl font-bold text-[#2D2A26] mb-1 flex items-center gap-2">
        <LifeBuoy size={20} className="text-gold" /> Pedir ayuda a Max
      </h3>
      <p className="text-sm text-[#9B9590] mb-4">
        Cuéntale a Max qué ajustar, arreglar o crear. El dueño recibe la petición y una propuesta.
        Nada se construye solo.
      </p>

      {status === 'sent' ? (
        <div className="rounded-2xl bg-sage-light/40 border border-sage/30 p-4 text-sm text-[#2D2A26]">
          <div className="flex items-center gap-2 font-bold mb-2">
            <CheckCircle2 size={18} className="text-sage" /> Pedido enviado
          </div>
          {proposal && <p className="text-[#5C5650]">{proposal}</p>}
          <button
            type="button"
            onClick={() => { setStatus('idle'); setProposal(null); }}
            className="mt-3 text-sm font-bold text-gold-dark"
          >
            Enviar otro
          </button>
        </div>
      ) : (
        <form onSubmit={submit} className="space-y-3">
          <input
            value={subject}
            onChange={e => setSubject(e.target.value)}
            required
            maxLength={500}
            placeholder="Asunto — qué necesitas"
            className="w-full px-4 py-3 rounded-2xl border border-gold/30 bg-warmwhite text-sm text-[#2D2A26] focus:outline-none focus:border-gold"
          />
          <textarea
            value={message}
            onChange={e => setMessage(e.target.value)}
            required
            rows={4}
            placeholder="Describe el ajuste, el arreglo o lo que quieres crear…"
            className="w-full px-4 py-3 rounded-2xl border border-gold/30 bg-warmwhite text-sm text-[#2D2A26] focus:outline-none focus:border-gold"
          />
          {status === 'error' && (
            <p className="text-sm text-red-500">{error}</p>
          )}
          <button
            type="submit"
            disabled={status === 'sending'}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-2xl bg-gradient-to-r from-gold to-sunrise text-white font-bold text-sm shadow-md hover:shadow-lg transition-all disabled:opacity-60"
          >
            <Send size={16} />
            {status === 'sending' ? 'Enviando…' : 'Enviar a Max'}
          </button>
        </form>
      )}
    </section>
  );
}
