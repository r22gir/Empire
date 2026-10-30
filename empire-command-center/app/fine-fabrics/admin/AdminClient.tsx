'use client';

import { useEffect, useState } from 'react';
import { fabricsApi } from '../api';
import { money } from '../cartStore';

const CATS = ['Upholstery', 'Drapery', 'Outdoor', 'Other'];

export default function AdminClient() {
  const [message, setMessage] = useState('');
  const [files, setFiles] = useState<Array<{ name: string; bytes: number }>>([]);
  const [unsorted, setUnsorted] = useState<Array<Record<string, unknown>>>([]);
  const [rules, setRules] = useState<Array<Record<string, unknown>>>([]);
  const [orders, setOrders] = useState<Array<Record<string, unknown>>>([]);
  const [samples, setSamples] = useState<Array<Record<string, unknown>>>([]);
  const [shortfalls, setShortfalls] = useState<Array<Record<string, unknown>>>([]);

  const reload = async () => {
    const [fileData, queue, ship, ledger, bills] = await Promise.all([
      fabricsApi.admin.importFiles(),
      fabricsApi.admin.unsorted(),
      fabricsApi.admin.shippingRules(),
      fabricsApi.admin.orders(),
      fabricsApi.admin.shortfalls(),
    ]);
    setFiles(fileData.files);
    setUnsorted(queue.products);
    setRules(ship.rules);
    setOrders(ledger.orders);
    setSamples(ledger.samples);
    setShortfalls(bills.shortfalls);
  };

  useEffect(() => {
    reload().catch((err) => setMessage(err instanceof Error ? err.message : 'Admin load failed'));
  }, []);

  return (
    <main className="ff-main" id="cloth" style={{ paddingTop: 36 }}>
      <p className="ff-eyebrow">Owner</p>
      <h1>Fine Fabrics admin</h1>
      <p className="ff-note">
        Import mill CSVs, empty the Unsorted queue, and record the actual vendor
        freight so any shortfall can be billed. Shipping is pass-through — never free.
      </p>
      {message ? <p className="ff-banner">{message}</p> : null}

      <section className="ff-admin-block">
        <h2>Import</h2>
        <label className="ff-btn-ghost">
          Upload CSV
          <input
            type="file"
            accept=".csv,text/csv"
            hidden
            onChange={async (event) => {
              const file = event.target.files?.[0];
              if (!file) return;
              try {
                const result = await fabricsApi.admin.importCsv(file);
                setMessage(JSON.stringify(result));
                await reload();
              } catch (err) {
                setMessage(err instanceof Error ? err.message : 'Import failed');
              }
            }}
          />
        </label>
        <button
          className="ff-btn"
          type="button"
          onClick={async () => {
            try {
              const result = await fabricsApi.admin.importDir();
              setMessage(JSON.stringify(result));
              await reload();
            } catch (err) {
              setMessage(err instanceof Error ? err.message : 'Directory import failed');
            }
          }}
        >
          Import data directory
        </button>
        <ul className="ff-admin-list">
          {files.map((file) => (
            <li key={file.name}>
              {file.name} · {file.bytes} bytes
              <button
                className="ff-btn-ghost"
                type="button"
                onClick={async () => {
                  const result = await fabricsApi.admin.importDir(file.name);
                  setMessage(JSON.stringify(result));
                  await reload();
                }}
              >
                Import
              </button>
            </li>
          ))}
          {files.length === 0 ? <li className="ff-note">No CSVs in FINE_FABRICS_DATA_DIR.</li> : null}
        </ul>
      </section>

      <section className="ff-admin-block">
        <h2>Unsorted queue</h2>
        <p className="ff-note">Blank or unknown categories stay here — they are never public.</p>
        {unsorted.length === 0 ? <p className="ff-note">Queue is empty.</p> : null}
        {unsorted.map((row) => (
          <div className="ff-line" key={String(row.id)}>
            <div>
              <strong>{String(row.pattern)}</strong>
              <div className="ff-note">{String(row.vendor_name || '')} · {String(row.sku || row.sku_range || '')}</div>
            </div>
            <select
              defaultValue=""
              onChange={async (event) => {
                if (!event.target.value) return;
                await fabricsApi.admin.assignCategory(Number(row.id), event.target.value);
                await reload();
              }}
            >
              <option value="">Assign category</option>
              {CATS.map((cat) => <option key={cat} value={cat}>{cat}</option>)}
            </select>
          </div>
        ))}
      </section>

      <section className="ff-admin-block">
        <h2>Vendor shipping estimates</h2>
        <p className="ff-note">
          Checkout charges an estimate of vendor freight (per yard / per sample / minimum)
          plus optional handling. After the mill invoice, record the actual charge below.
        </p>
        {rules.map((rule) => (
          <form
            key={String(rule.vendor_id)}
            className="ff-form"
            onSubmit={async (event) => {
              event.preventDefault();
              const data = new FormData(event.currentTarget);
              await fabricsApi.admin.updateShippingRules(Number(rule.vendor_id), {
                ship_per_yard: Number(data.get('ship_per_yard')),
                ship_per_sample: Number(data.get('ship_per_sample')),
                ship_minimum: Number(data.get('ship_minimum')),
                handling_fee: Number(data.get('handling_fee')),
              });
              setMessage(`Updated ${rule.slug} shipping rules`);
              await reload();
            }}
          >
            <strong>{String(rule.name)}</strong>
            <label>Per yard<input name="ship_per_yard" type="number" step="0.01" defaultValue={Number(rule.ship_per_yard)} /></label>
            <label>Per sample<input name="ship_per_sample" type="number" step="0.01" defaultValue={Number(rule.ship_per_sample)} /></label>
            <label>Minimum<input name="ship_minimum" type="number" step="0.01" defaultValue={Number(rule.ship_minimum)} /></label>
            <label>Handling<input name="handling_fee" type="number" step="0.01" defaultValue={Number(rule.handling_fee)} /></label>
            <button className="ff-btn" type="submit">Save estimates</button>
          </form>
        ))}
      </section>

      <section className="ff-admin-block">
        <h2>Actual vendor shipping</h2>
        <p className="ff-note">If the mill charged more than we collected, the row is flagged to bill the shortfall.</p>
        {shortfalls.length ? (
          <p className="ff-banner">{shortfalls.length} shortfall{shortfalls.length === 1 ? '' : 's'} to bill.</p>
        ) : null}
        {[...orders.map((row) => ({ ...row, kind: 'order' })), ...samples.map((row) => ({ ...row, kind: 'sample' }))].map((row) => (
          <form
            key={`${row.kind}-${row.id}`}
            className="ff-line"
            onSubmit={async (event) => {
              event.preventDefault();
              const actual = Number(new FormData(event.currentTarget).get('actual'));
              if (row.kind === 'order') await fabricsApi.admin.recordOrderShipping(Number(row.id), actual);
              else await fabricsApi.admin.recordSampleShipping(Number(row.id), actual);
              await reload();
            }}
          >
            <div>
              <strong>{String(row.kind)} #{String(row.id)}</strong>
              <div className="ff-note">
                {String(row.customer_name || '')} · collected {money(Number(row.shipping_total || 0))}
                {row.actual_vendor_shipping != null ? ` · actual ${money(Number(row.actual_vendor_shipping))}` : ''}
                {row.shipping_flag === 'shortfall' ? ` · BILL ${money(Number(row.shipping_shortfall || 0))}` : ''}
              </div>
            </div>
            <div>
              <input className="ff-qty" name="actual" type="number" step="0.01" min="0" placeholder="Actual" required />
              <button className="ff-btn-ghost" type="submit">Record</button>
            </div>
          </form>
        ))}
      </section>
    </main>
  );
}
