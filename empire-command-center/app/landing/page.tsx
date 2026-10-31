// empirebox.store public landing (served at apex "/" via middleware rewrite → /landing).
// v2 visual: full-bleed hero, image-led business cards, process strip, gallery.
// Luxe palette (ivory / charcoal / gold), serif display. ApostApp kept separate (no Workroom link).
// All imagery is already public under /public/workroom-showroom or is non-identifying
// shop material (/public/empirebox-landing). No client names or addresses.

import RevealOnScroll from './RevealOnScroll';
import { GROUPS, PROCESS_STEPS, GALLERY, SWATCHES, type ModuleEntry } from './_data';

export const metadata = {
  title: 'EmpireBox — custom workroom, fine fabrics, woodworks, and small-business tools',
  description:
    'Empire Workroom, Empire Fine Fabrics, and Empire Woodworks: custom drapery, upholstery, and millwork from 3D design to CNC cutting to installation. Washington DC · Maryland · Virginia.',
  robots: { index: true, follow: true },
};

const CSS = `
.lx{--iv:#f7f2ea;--iv2:#efe7da;--ch:#1f1d1a;--ch2:#3a3631;--gd:#b08d57;--gd2:#8a6b3b;--mut:#5c554c;
  background:var(--iv);color:var(--ch);font-family:Inter,system-ui,-apple-system,sans-serif;line-height:1.6}
.lx *{box-sizing:border-box}
.lx a{color:inherit}
.lx .serif{font-family:'Cormorant Garamond','Playfair Display',Georgia,'Times New Roman',serif;font-weight:500;letter-spacing:-.01em}
.lx .wrap{max-width:1200px;margin:0 auto;padding:0 32px}
.lx .eyebrow{font-size:12px;letter-spacing:.22em;text-transform:uppercase;color:var(--gd2);font-weight:600}
.lx .rule{width:56px;height:2px;background:var(--gd);margin:18px 0 0}
.lx-nav{position:absolute;top:0;left:0;right:0;z-index:5;color:#fff}
.lx-nav .wrap{display:flex;justify-content:space-between;align-items:center;height:76px}
.lx-nav .brand{font-size:22px;letter-spacing:.24em;text-decoration:none}
.lx-nav nav{display:flex;gap:28px;font-size:13px;letter-spacing:.08em;text-transform:uppercase}
.lx-nav nav a{text-decoration:none;opacity:.9}
.lx-hero{position:relative;min-height:88vh;display:flex;align-items:flex-end;color:#fff;
  background:#2a2620 url('/workroom-showroom/photos/drapery-music-room.jpg') center/cover no-repeat}
.lx-hero:before{content:'';position:absolute;inset:0;background:linear-gradient(180deg,rgba(20,18,15,.55) 0%,rgba(20,18,15,.15) 35%,rgba(20,18,15,.78) 100%)}
.lx-hero .wrap{position:relative;padding-bottom:88px;width:100%}
.lx-hero h1{font-size:clamp(44px,7vw,92px);line-height:1.02;margin:16px 0 20px;max-width:900px}
.lx-hero p{font-size:clamp(16px,1.6vw,20px);max-width:620px;opacity:.95;margin:0 0 32px}
.lx-hero .eyebrow{color:#e6cf9f}
.btn{display:inline-block;padding:15px 28px;border-radius:2px;font-size:14px;letter-spacing:.08em;text-transform:uppercase;text-decoration:none;font-weight:600;transition:all .2s}
.btn-gold{background:var(--gd);color:#fff!important}.btn-gold:hover{background:var(--gd2)}
.btn-ghost{border:1px solid rgba(255,255,255,.7);color:#fff!important;margin-left:12px}.btn-ghost:hover{background:rgba(255,255,255,.12)}
.btn-dark{border:1px solid var(--ch);color:var(--ch)!important}
.lx-sec{padding:120px 0}
.lx-sec.alt{background:var(--iv2)}
.lx-sec.dark{background:var(--ch);color:var(--iv)}
.lx-sec.dark .eyebrow{color:#d9bd86}
.lx h2{font-size:clamp(34px,4.4vw,56px);line-height:1.08;margin:14px 0 0}
.lx .lede{font-size:18px;color:var(--mut);max-width:640px;margin:22px 0 0}
.lx-sec.dark .lede{color:#cfc6b8}
.biz{display:grid;grid-template-columns:repeat(2,1fr);gap:32px;margin-top:64px}
.biz .card{background:#fff;text-decoration:none;display:flex;flex-direction:column;box-shadow:0 1px 2px rgba(31,29,26,.06),0 12px 32px rgba(31,29,26,.08);transition:transform .25s,box-shadow .25s;overflow:hidden}
.biz .card:hover{transform:translateY(-4px);box-shadow:0 2px 4px rgba(31,29,26,.08),0 22px 48px rgba(31,29,26,.14)}
.biz .ph{aspect-ratio:16/10;background:#ddd center/cover no-repeat;position:relative}
.biz .tag{position:absolute;top:16px;left:16px;background:rgba(247,242,234,.94);color:var(--ch);font-size:11px;letter-spacing:.16em;text-transform:uppercase;padding:6px 12px;font-weight:600}
.biz .tag.soon{background:var(--ch);color:#e6cf9f}
.biz .body{padding:28px 30px 32px}
.biz h3{font-size:30px;margin:0 0 10px}
.biz p{margin:0;color:var(--mut);font-size:15.5px}
.biz .cta{margin-top:18px;font-size:13px;letter-spacing:.1em;text-transform:uppercase;color:var(--gd2);font-weight:600}
.swatchstrip{display:grid;grid-template-columns:repeat(6,1fr);height:100%}
.swatchstrip div{background-size:cover;background-position:center}
.swatches{display:grid;grid-template-columns:repeat(6,1fr);gap:20px;margin-top:48px}
.swatches figure{margin:0}
.swatches .sw{aspect-ratio:1;background:center/cover;box-shadow:0 8px 24px rgba(31,29,26,.12)}
.swatches figcaption{font-size:13px;margin-top:10px}
.swatches figcaption span{display:block;color:var(--mut);font-size:11px;letter-spacing:.14em;text-transform:uppercase}
.proc{display:grid;grid-template-columns:repeat(4,1fr);gap:24px;margin-top:64px;counter-reset:s}
.proc li{list-style:none}
.proc .im{aspect-ratio:4/3;background:#fff center/cover no-repeat;border:1px solid rgba(217,189,134,.25)}
.proc .im.contain{background-size:contain;background-color:#fff}
.proc .n{font-size:44px;color:#d9bd86;margin:20px 0 4px;line-height:1}
.proc h3{font-size:24px;margin:0 0 8px}
.proc p{margin:0;font-size:14.5px;color:#cfc6b8}
.gal{display:grid;grid-template-columns:repeat(3,1fr);grid-auto-rows:280px;gap:16px;margin-top:64px}
.gal figure{margin:0;position:relative;overflow:hidden;background:#ccc center/cover no-repeat}
.gal figure.big{grid-row:span 2;grid-column:span 2}
.gal figcaption{position:absolute;left:0;right:0;bottom:0;padding:40px 20px 18px;color:#fff;background:linear-gradient(180deg,transparent,rgba(20,18,15,.75))}
.gal figcaption b{display:block;font-family:'Cormorant Garamond',Georgia,serif;font-size:22px;font-weight:500}
.gal figcaption span{font-size:11px;letter-spacing:.16em;text-transform:uppercase;color:#e6cf9f}
.tools{display:grid;grid-template-columns:repeat(4,1fr);gap:24px;margin-top:56px}
.tools .t{background:#fff;padding:28px;box-shadow:0 8px 24px rgba(31,29,26,.06);border-top:2px solid var(--gd)}
.tools h3{font-size:24px;margin:0 0 8px}
.tools .st{font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--gd2);font-weight:600}
.tools p{font-size:14.5px;color:var(--mut);margin:10px 0 0}
.docs{display:flex;gap:48px;align-items:center;justify-content:space-between;border:1px solid #d8ccb8;padding:48px;background:#fff}
.docs h3{font-size:34px;margin:6px 0 10px}
.docs p{color:var(--mut);margin:0;max-width:620px}
.lx-foot{background:var(--ch);color:#cfc6b8;padding:64px 0;font-size:14px}
.lx-foot .brand{font-size:24px;letter-spacing:.24em;color:var(--iv)}
.lx-foot .row{display:flex;justify-content:space-between;gap:24px;flex-wrap:wrap;align-items:flex-end}
.lx-foot a{color:#e6cf9f}
@media (max-width:900px){
  .lx .wrap{padding:0 22px}
  .lx-nav nav{display:none}
  .lx-hero{min-height:92vh}
  .lx-hero .wrap{padding-bottom:56px}
  .btn{display:block;text-align:center;margin:0 0 12px!important}
  .lx-sec{padding:80px 0}
  .biz{grid-template-columns:1fr;gap:24px;margin-top:40px}
  .biz h3{font-size:26px}
  .swatches{grid-template-columns:repeat(3,1fr);gap:14px}
  .proc{grid-template-columns:1fr 1fr;gap:20px}
  .proc h3{font-size:20px}
  .gal{grid-template-columns:1fr 1fr;grid-auto-rows:200px;gap:10px}
  .gal figure.big{grid-row:span 1;grid-column:span 2}
  .gal figure:last-child{grid-column:span 2}
  .gal figcaption{padding:28px 12px 10px}
  .gal figcaption b{font-size:16px;line-height:1.2}
  .gal figcaption span{font-size:9px}
  .tools{grid-template-columns:1fr;gap:16px}
  .docs{flex-direction:column;align-items:flex-start;padding:32px 24px;gap:24px}
}
@media (max-width:480px){ .proc{grid-template-columns:1fr} }
`;

function BizCard({ m }: { m: ModuleEntry }) {
  const soon = m.status === 'roadmap';
  const isFabrics = m.id === 'fabrics';
  const content = (
    <>
      <div className="ph" style={isFabrics ? undefined : { backgroundImage: `url(${m.image})` }} role="img" aria-label={m.imageAlt}>
        {isFabrics && (
          <div className="swatchstrip">
            {SWATCHES.map((s) => <div key={s.src} style={{ backgroundImage: `url(${s.src})` }} />)}
          </div>
        )}
        <span className={`tag${soon ? ' soon' : ''}`}>{m.statusText}</span>
      </div>
      <div className="body">
        <h3 className="serif">{m.name}</h3>
        <p>{m.description}</p>
        {m.ctaHref ? <div className="cta">{m.ctaLabel}</div> : soon ? <div className="cta" style={{ color: 'var(--mut)' }}>Launching soon</div> : null}
      </div>
    </>
  );
  return m.ctaHref ? (
    <a className="card" href={m.ctaHref} data-testid={`module-${m.id}`} aria-label={m.ariaLabel || m.name}>{content}</a>
  ) : (
    <div className="card" data-testid={`module-${m.id}`} aria-label={m.ariaLabel || m.name}>{content}</div>
  );
}

export default function LandingPage() {
  const [home, business, documents] = GROUPS;
  const apost = documents.modules[0];
  return (
    <main className="lx" data-empirebox-page>
      <style dangerouslySetInnerHTML={{ __html: CSS }} />
      <header className="lx-nav">
        <div className="wrap">
          <a href="/" className="brand serif" aria-label="EmpireBox home">EMPIREBOX</a>
          <nav aria-label="Primary">
            <a href="#home-design">Home &amp; design</a>
            <a href="#process">Process</a>
            <a href="#recent-work">Our work</a>
            <a href="#business-tools">Business tools</a>
            <a href="#documents">Documents</a>
          </nav>
        </div>
      </header>

      <section className="lx-hero" data-testid="hero">
        <div className="wrap">
          <div className="eyebrow">Washington DC · Maryland · Virginia</div>
          <h1 className="serif">Drapery, upholstery &amp; fine woodwork — made in our own shop.</h1>
          <p>Designed in 3D, cut on our CNC, and finished by hand. Empire Workroom, Empire Fine Fabrics, and Empire Woodworks under one roof.</p>
          <a href="https://workroom.empirebox.store" className="btn btn-gold" data-testid="cta-workroom">Visit the Workroom</a>
          <a href="#recent-work" className="btn btn-ghost" data-testid="cta-recent-work">See recent work</a>
        </div>
      </section>

      <section id="home-design" className="lx-sec">
        <div className="wrap">
          <div className="eyebrow">Home &amp; design</div>
          <h2 className="serif">Four houses of craft</h2>
          <div className="rule" />
          <p className="lede">{home.intro}</p>
          <div className="biz">
            {home.modules.filter((m) => m.id !== 'luxeforge').map((m) => <BizCard key={m.id} m={m} />)}
          </div>
          <p className="lede" style={{ fontSize: 15, marginTop: 36 }}>
            <strong style={{ color: 'var(--ch)' }}>LuxeForge</strong> (founder preview) — see fabrics and finishes on your own room before anything is cut.
          </p>
        </div>
      </section>

      <section className="lx-sec alt" data-testid="swatches">
        <div className="wrap">
          <div className="eyebrow">Empire Fine Fabrics</div>
          <h2 className="serif">Linens, silks, cottons &amp; vinyls</h2>
          <div className="rule" />
          <div className="swatches">
            {SWATCHES.map((s) => (
              <figure key={s.src}>
                <div className="sw" style={{ backgroundImage: `url(${s.src})` }} role="img" aria-label={s.name} />
                <figcaption><span>{s.material}</span>{s.name}</figcaption>
              </figure>
            ))}
          </div>
          <div style={{ marginTop: 40 }}><a className="btn btn-dark" href="https://fabrics.empirebox.store">Browse the collection</a></div>
        </div>
      </section>

      <section id="process" className="lx-sec dark" data-testid="process-steps">
        <div className="wrap">
          <div className="eyebrow">Our process</div>
          <h2 className="serif">From 3D design to CNC to your room</h2>
          <div className="rule" />
          <p className="lede">Every piece is modeled before it is cut, so you approve proportions, fabric, and finish first — then the CNC cuts it exactly to the drawing.</p>
          <ol className="proc" style={{ padding: 0 }}>
            {PROCESS_STEPS.map((s, i) => (
              <li key={s.title}>
                <div className={`im${i < 2 ? ' contain' : ''}`} style={{ backgroundImage: `url(${s.image})` }} role="img" aria-label={s.alt} />
                <div className="n serif">0{i + 1}</div>
                <h3 className="serif">{s.title}</h3>
                <p>{s.body}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section id="recent-work" className="lx-sec" data-testid="recent-work">
        <div className="wrap">
          <div className="eyebrow">Recent work</div>
          <h2 className="serif">From the workroom floor</h2>
          <div className="rule" />
          <div className="gal">
            {GALLERY.map((g, i) => (
              <figure key={g.src} className={i === 0 ? 'big' : undefined} style={{ backgroundImage: `url(${g.src})` }}>
                <figcaption><span>{g.tag}</span><b>{g.title}</b></figcaption>
              </figure>
            ))}
          </div>
        </div>
      </section>

      <section id="business-tools" className="lx-sec alt">
        <div className="wrap">
          <div className="eyebrow">Business tools</div>
          <h2 className="serif">The software behind our shop</h2>
          <div className="rule" />
          <p className="lede">{business.intro}</p>
          <div className="tools">
            {business.modules.map((m) => (
              <div className="t" key={m.id} data-testid={`module-${m.id}`}>
                <div className="st">{m.statusText}</div>
                <h3 className="serif">{m.name}</h3>
                <p>{m.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="documents" className="lx-sec">
        <div className="wrap">
          <div className="docs" data-testid="module-apostapp">
            <div>
              <div className="eyebrow">Documents · separate service</div>
              <h3 className="serif">{apost.name}</h3>
              <p>{apost.description} Not affiliated with the design workroom. EmpireBox is not a law firm and does not give legal advice.</p>
            </div>
            <a className="btn btn-dark" href={apost.ctaHref}>Go to ApostApp</a>
          </div>
        </div>
      </section>

      <footer className="lx-foot" role="contentinfo">
        <div className="wrap row">
          <div>
            <div className="brand serif">EMPIREBOX</div>
            <div style={{ marginTop: 10 }}>Washington DC · Maryland · Virginia</div>
          </div>
          <div>
            Every quote is reviewed by a person · Customer pays shipping on product orders<br />
            © {new Date().getFullYear()} EmpireBox · <a href="mailto:hello@empirebox.store">hello@empirebox.store</a>
          </div>
        </div>
      </footer>
      <RevealOnScroll />
    </main>
  );
}
