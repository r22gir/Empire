const methods = [
  ['Empire Workroom', 'Upholstery, cushions, pillows, drapery, fabric/materials, labor, install, rush surcharge'],
  ['Woodcraft / CraftForge', 'Sheet goods, board-foot material, CNC time, drawing time, assembly, finishing, hardware, install'],
];

const fields = [
  'pricing method',
  'pricing inputs',
  'rate table version',
  'formula version',
  'calculation explanation',
  'manual override',
  'override reason',
  'final approved price',
  'invoice snapshot status',
];

export default function PricingStudioPage() {
  return (
    <main style={{ minHeight: '100vh', background: '#f7f7f4', color: '#1f2933', fontFamily: 'Inter, system-ui, sans-serif' }}>
      <header style={{ borderBottom: '1px solid #dedbd2', background: '#ffffff', padding: '18px 24px' }}>
        <div style={{ maxWidth: 1100, margin: '0 auto', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16 }}>
          <div>
            <h1 style={{ fontSize: 22, margin: 0, fontWeight: 800 }}>Pricing Studio</h1>
            <p style={{ margin: '4px 0 0', color: '#62717f', fontSize: 13 }}>Deterministic pricing snapshots for Workroom and CraftForge.</p>
          </div>
          <a href="/" style={{ color: '#0f766e', fontSize: 13, fontWeight: 700, textDecoration: 'none' }}>Command Center</a>
        </div>
      </header>

      <section style={{ maxWidth: 1100, margin: '0 auto', padding: 24 }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 14 }}>
          {methods.map(([title, body]) => (
            <article key={title} style={{ background: '#ffffff', border: '1px solid #dedbd2', borderRadius: 8, padding: 18 }}>
              <h2 style={{ fontSize: 16, margin: '0 0 8px', fontWeight: 800 }}>{title}</h2>
              <p style={{ margin: 0, color: '#52616f', fontSize: 13, lineHeight: 1.5 }}>{body}</p>
            </article>
          ))}
        </div>

        <section style={{ marginTop: 18, background: '#ffffff', border: '1px solid #dedbd2', borderRadius: 8, padding: 18 }}>
          <h2 style={{ fontSize: 16, margin: '0 0 12px', fontWeight: 800 }}>Snapshot Fields</h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 8 }}>
            {fields.map((field) => (
              <div key={field} style={{ border: '1px solid #ebe8df', borderRadius: 6, padding: '10px 12px', fontSize: 13, fontWeight: 700, color: '#2f3b45' }}>
                {field}
              </div>
            ))}
          </div>
        </section>
      </section>
    </main>
  );
}
