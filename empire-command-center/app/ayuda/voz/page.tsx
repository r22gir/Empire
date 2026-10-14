import Link from 'next/link';
import { AYUDA_OPENER } from '../../lib/ayudaCopy';

const STEPS = [
  'Mantén presionado el micrófono en el chat. Al soltarlo, la nota se envía a transcribir.',
  'Habla con naturalidad, en español. Si cambias de idioma, la transcripción lo detecta. Los documentos quedan en es-CO.',
  'Revisa la transcripción. Si algo quedó mal, escríbelo o graba otra nota. Varias notas arman un solo borrador.',
  'Cuando haya que elegir, verás dos o tres opciones: plan de pagos A, B o C, casa T1, T2 o T3, con acabados o sin acabados.',
  'Di o escribe listo. Aparece el borrador y la vista previa. Sigue marcado DRAFT.',
  'Aprueba el borrador. Descárgalo desde la vista previa, o marca la confirmación antes de pulsar Enviar. Sin esa confirmación no se envía nada.',
];

export default function ComoUsarLaVoz() {
  return (
    <main style={{ maxWidth: 720, margin: '0 auto', padding: '32px 20px', fontFamily: 'Inter, sans-serif', color: '#1a1a1a' }}>
      <nav aria-label="Navegación de ayuda" style={{ display: 'flex', flexWrap: 'wrap', gap: 16, marginBottom: 24, fontSize: 14 }}>
        <Link href="/ayuda" style={{ color: '#b8960c', fontWeight: 700 }}>← Volver a Ayuda</Link>
        <Link href="/" style={{ color: '#444', fontWeight: 600 }}>Centro de mando</Link>
      </nav>
      <p style={{ fontSize: 12, letterSpacing: 0.4, color: '#b8960c', fontWeight: 700, margin: 0 }}>CENTRO DE MANDO</p>
      <h1 style={{ fontSize: 32, margin: '8px 0' }}>Cómo usar la voz</h1>
      <p data-ayuda-opener="1" style={{ fontFamily: "'Playfair Display', Georgia, serif", fontSize: 26, margin: '8px 0 12px' }}>{AYUDA_OPENER}</p>
      <p style={{ fontSize: 16, lineHeight: 1.5 }}>
        Maxine arma reservas, planes de pago y notas de obra a partir de lo que dictas. El resultado es un borrador hasta que tú lo apruebas. No escribe a compradores.
      </p>
      <ol style={{ paddingLeft: 20, lineHeight: 1.55 }}>
        {STEPS.map((step) => (
          <li key={step} style={{ marginBottom: 10 }}>{step}</li>
        ))}
      </ol>
      <p style={{ fontSize: 14, color: '#444' }}>
        Puedes separar un lote: “separar el lote 12, cuota inicial 30%, saldo en 24 meses”. El precio tiene que decirlo tú. El estado del lote pasa a reservado, separado o vendido solo cuando lo confirmas.
      </p>
      <p style={{ fontSize: 14, color: '#444' }}>
        Las fotos de la obra se etiquetan con lote y etapa (cimentación, estructura, acabados). Google Photos solo trae lo que tú eliges. El borrador queda en la copia de trabajo de esta máquina y, si conectaste tu Drive, en tu carpeta Maxine/.
      </p>
      <p style={{ fontSize: 14, color: '#444' }}>
        WhatsApp usa el número de esta instancia. No reutilices llaves ni números de otra instancia. Si las variables no están, el canal queda apagado. Las notas de voz arman el mismo borrador. El PDF sale solo cuando escribes que lo envíe. La guía está en <Link href="/ayuda/whatsapp" style={{ color: '#b8960c', fontWeight: 700 }}>/ayuda/whatsapp</Link>.
      </p>
      <Link href="/" style={{ color: '#b8960c', fontWeight: 700 }}>Volver al centro de mando</Link>
    </main>
  );
}
