'use client';
import React, { useState, useEffect } from 'react';
import { API } from '../../lib/api';
import { useTranslation } from '../../lib/i18n';
import {
  Store, ShoppingCart, Package, BarChart3, Users, Truck, CreditCard,
  Gift, UserCheck, Loader2, Plus, Search, Barcode, DollarSign,
  TrendingUp, AlertTriangle, Tag, Clock, Minus, ChevronRight,
  Hash, Layers, Archive, Star
} from 'lucide-react';
import ProductDocs from '../business/docs/ProductDocs';

const SF_API = `${API}/storefront`;

const NAV_SECTIONS = [
  { id: 'dashboard', label: 'Dashboard', icon: BarChart3 },
  { id: 'pos', label: 'POS Terminal', icon: ShoppingCart },
  { id: 'products', label: 'Products', icon: Package },
  { id: 'inventory', label: 'Inventory', icon: Layers },
  { id: 'customers', label: 'Customers', icon: Users },
  { id: 'orders', label: 'Purchase Orders', icon: Truck },
  { id: 'employees', label: 'Employees', icon: UserCheck },
  { id: 'giftcards', label: 'Gift Cards', icon: Gift },
  { id: 'suppliers', label: 'Suppliers', icon: Archive },
  { id: 'reports', label: 'Reports', icon: BarChart3 },
  { id: 'docs', label: 'Docs', icon: BarChart3 },
] as const;

type Section = typeof NAV_SECTIONS[number]['id'];

interface StoreFrontForgePageProps { initialSection?: string; }

export default function StoreFrontForgePage({ initialSection }: StoreFrontForgePageProps) {
  const [section, setSection] = useState<Section>((initialSection as Section) || 'dashboard');
  const { t, locale } = useTranslation('storefront');

  useEffect(() => {
    if (initialSection) setSection(initialSection as Section);
  }, [initialSection]);

  const renderContent = () => {
    switch (section) {
      case 'dashboard': return <DashboardSection />;
      case 'pos': return <POSSection />;
      case 'products': return <ProductsSection />;
      case 'inventory': return <InventorySection />;
      case 'customers': return <CustomersSection />;
      case 'orders': return <PurchaseOrdersSection />;
      case 'employees': return <EmployeesSection />;
      case 'giftcards': return <GiftCardsSection />;
      case 'suppliers': return <SuppliersSection />;
      case 'reports': return <ReportsSection />;
      case 'docs': return <ProductDocs product="storefront" />;
      default: return <DashboardSection />;
    }
  };

  return (
    <div style={{ display: 'flex', height: '100%', background: '#faf9f7' }}>
      <div style={{ width: 200, borderRight: '1px solid #e5e2dc', padding: '16px 0', flexShrink: 0, overflowY: 'auto' }}>
        <div style={{ padding: '0 16px 12px', borderBottom: '1px solid #e5e2dc', marginBottom: 8 }}>
          <div style={{ fontSize: 14, fontWeight: 700, color: '#16a34a', display: 'flex', alignItems: 'center', gap: 6 }}>
            <Store size={16} /> StoreFront Forge
          </div>
          <div style={{ fontSize: 10, color: '#999', marginTop: 2 }}>Retail Store Management</div>
        </div>
        {NAV_SECTIONS.map(nav => (
          <button key={nav.id} onClick={() => setSection(nav.id)}
            style={{
              display: 'flex', alignItems: 'center', gap: 8, width: '100%',
              padding: '8px 16px', border: 'none', cursor: 'pointer',
              background: section === nav.id ? '#f0fdf4' : 'transparent',
              color: section === nav.id ? '#16a34a' : '#666',
              fontWeight: section === nav.id ? 600 : 400, fontSize: 12, textAlign: 'left',
            }}>
            <nav.icon size={14} />
            {nav.label}
          </button>
        ))}
      </div>
      <div style={{ flex: 1, overflowY: 'auto', padding: '20px 24px' }}>
        {renderContent()}
      </div>
    </div>
  );
}

function SH({ title, subtitle, action }: { title: string; subtitle?: string; action?: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 }}>
      <div>
        <h2 style={{ fontSize: 20, fontWeight: 700, color: '#1a1a1a', margin: 0 }}>{title}</h2>
        {subtitle && <p style={{ fontSize: 12, color: '#888', marginTop: 2 }}>{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}

function Kpi({ label, value, color }: { label: string; value: string | number; color?: string }) {
  return (
    <div style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 10, padding: '16px 18px', flex: 1, minWidth: 130 }}>
      <div style={{ fontSize: 10, fontWeight: 600, color: '#888', textTransform: 'uppercase', letterSpacing: 0.5 }}>{label}</div>
      <div style={{ fontSize: 22, fontWeight: 700, color: color || '#1a1a1a', marginTop: 4 }}>{value}</div>
    </div>
  );
}

function DashboardSection() {
  const [stats, setStats] = useState<any>({});
  useEffect(() => {
    Promise.all([
      fetch(`${SF_API}/products`).then(r => r.json()).catch(() => ({})),
      fetch(`${SF_API}/transactions`).then(r => r.json()).catch(() => ({})),
      fetch(`${SF_API}/customers`).then(r => r.json()).catch(() => ({})),
    ]).then(([prods, txns, custs]) => {
      const products = prods.products || prods || [];
      const transactions = txns.transactions || txns || [];
      const customers = custs.customers || custs || [];
      const todayRev = transactions.reduce((s: number, t: any) => s + (t.total || 0), 0);
      setStats({ products: products.length, transactions: transactions.length, customers: customers.length, revenue: todayRev });
    });
  }, []);
  return (
    <div>
      <SH title="Store Dashboard" subtitle="Overview of your retail operations" />
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 20 }}>
        <Kpi label="Products" value={stats.products ?? '—'} color="#2563eb" />
        <Kpi label="Transactions" value={stats.transactions ?? '—'} color="#16a34a" />
        <Kpi label="Revenue" value={`$${(stats.revenue || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}`} color="#b8960c" />
        <Kpi label="Customers" value={stats.customers ?? '—'} color="#8b5cf6" />
      </div>
      <div style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 10, padding: 16 }}>
        <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>Quick Actions</div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {[
            { label: 'New Sale', icon: ShoppingCart, color: '#16a34a' },
            { label: 'Add Product', icon: Plus, color: '#2563eb' },
            { label: 'Scan Barcode', icon: Barcode, color: '#b8960c' },
            { label: 'View Reports', icon: BarChart3, color: '#8b5cf6' },
          ].map((a, i) => (
            <button key={i} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 14px', border: '1px solid #e5e2dc', borderRadius: 8, background: '#fff', cursor: 'pointer', fontSize: 12, fontWeight: 500 }}>
              <a.icon size={14} style={{ color: a.color }} /> {a.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function POSSection() {
  const [cart, setCart] = useState<{ product: any; qty: number }[]>([]);
  const [products, setProducts] = useState<any[]>([]);
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('all');

  useEffect(() => {
    fetch(`${SF_API}/products`).then(r => r.json()).then(d => setProducts(d.products || d || [])).catch(() => {});
  }, []);

  const categories = ['all', ...new Set(products.map((p: any) => p.category).filter(Boolean))];
  const filtered = products.filter((p: any) => {
    if (category !== 'all' && p.category !== category) return false;
    if (search && !p.name.toLowerCase().includes(search.toLowerCase()) && p.sku !== search && p.barcode !== search) return false;
    return true;
  });

  const addToCart = (product: any) => {
    setCart(prev => {
      const existing = prev.find(c => c.product.id === product.id);
      if (existing) return prev.map(c => c.product.id === product.id ? { ...c, qty: c.qty + 1 } : c);
      return [...prev, { product, qty: 1 }];
    });
  };

  const subtotal = cart.reduce((s, c) => s + c.product.retail_price * c.qty, 0);
  const tax = subtotal * 0.06; // Default 6% tax
  const total = subtotal + tax;

  return (
    <div style={{ display: 'flex', gap: 16, height: 'calc(100vh - 120px)' }}>
      {/* Product grid */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
          <div style={{ position: 'relative', flex: 1 }}>
            <Search size={14} style={{ position: 'absolute', left: 10, top: 10, color: '#999' }} />
            <input value={search} onChange={e => setSearch(e.target.value)}
              placeholder="Search product or scan barcode..."
              style={{ width: '100%', padding: '8px 8px 8px 30px', border: '1px solid #e5e2dc', borderRadius: 8, fontSize: 12 }} />
          </div>
        </div>
        <div style={{ display: 'flex', gap: 4, marginBottom: 10, flexWrap: 'wrap' }}>
          {categories.map(c => (
            <button key={c} onClick={() => setCategory(c)} style={{
              fontSize: 10, padding: '4px 10px', borderRadius: 12,
              border: category === c ? '2px solid #16a34a' : '1px solid #e5e2dc',
              background: category === c ? '#f0fdf4' : '#fff', cursor: 'pointer',
              fontWeight: category === c ? 600 : 400, color: category === c ? '#16a34a' : '#666',
            }}>
              {c === 'all' ? 'All' : c}
            </button>
          ))}
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(120px, 1fr))', gap: 8, overflowY: 'auto', flex: 1 }}>
          {filtered.map((p: any) => (
            <button key={p.id} onClick={() => addToCart(p)} style={{
              background: '#fff', border: '1px solid #e5e2dc', borderRadius: 8, padding: 10,
              cursor: 'pointer', textAlign: 'center', display: 'flex', flexDirection: 'column',
              alignItems: 'center', gap: 4, fontSize: 11, minHeight: 80,
            }}>
              <Package size={20} style={{ color: '#16a34a' }} />
              <div style={{ fontWeight: 500, lineHeight: 1.2 }}>{p.name}</div>
              <div style={{ fontWeight: 700, color: '#16a34a' }}>${p.retail_price?.toFixed(2)}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Cart */}
      <div style={{ width: 300, background: '#fff', border: '1px solid #e5e2dc', borderRadius: 10, padding: 16, display: 'flex', flexDirection: 'column' }}>
        <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 10 }}>
          <ShoppingCart size={16} style={{ verticalAlign: 'text-bottom' }} /> Current Sale
        </h3>
        <div style={{ flex: 1, overflowY: 'auto' }}>
          {cart.length === 0 ? (
            <div style={{ textAlign: 'center', color: '#ccc', padding: 20, fontSize: 12 }}>Cart is empty</div>
          ) : cart.map((c, i) => (
            <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: '1px solid #f0ede6', fontSize: 12 }}>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 500 }}>{c.product.name}</div>
                <div style={{ color: '#888', fontSize: 10 }}>${c.product.retail_price?.toFixed(2)} × {c.qty}</div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <button onClick={() => setCart(prev => prev.map((x, j) => j === i ? { ...x, qty: Math.max(1, x.qty - 1) } : x))}
                  style={{ width: 22, height: 22, border: '1px solid #e5e2dc', borderRadius: 4, background: '#fff', cursor: 'pointer', fontSize: 12 }}>−</button>
                <span style={{ fontWeight: 600, minWidth: 16, textAlign: 'center' }}>{c.qty}</span>
                <button onClick={() => setCart(prev => prev.map((x, j) => j === i ? { ...x, qty: x.qty + 1 } : x))}
                  style={{ width: 22, height: 22, border: '1px solid #e5e2dc', borderRadius: 4, background: '#fff', cursor: 'pointer', fontSize: 12 }}>+</button>
                <span style={{ fontWeight: 700, minWidth: 50, textAlign: 'right' }}>${(c.product.retail_price * c.qty).toFixed(2)}</span>
              </div>
            </div>
          ))}
        </div>
        <div style={{ borderTop: '2px solid #e5e2dc', paddingTop: 10, marginTop: 10 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 4 }}>
            <span>Subtotal</span><span>${subtotal.toFixed(2)}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 4, color: '#888' }}>
            <span>Tax (6%)</span><span>${tax.toFixed(2)}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 18, fontWeight: 700, color: '#16a34a', marginTop: 4 }}>
            <span>Total</span><span>${total.toFixed(2)}</span>
          </div>
          <div style={{ display: 'flex', gap: 6, marginTop: 12 }}>
            <button style={{ flex: 1, padding: '10px', background: '#16a34a', color: '#fff', border: 'none', borderRadius: 8, fontWeight: 700, fontSize: 13, cursor: 'pointer' }}>
              <CreditCard size={14} style={{ verticalAlign: 'text-bottom' }} /> Pay
            </button>
            <button onClick={() => setCart([])} style={{ padding: '10px 14px', background: '#f5f3ef', color: '#666', border: 'none', borderRadius: 8, fontWeight: 600, fontSize: 12, cursor: 'pointer' }}>
              Clear
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function ProductsSection() {
  const [products, setProducts] = useState<any[]>([]);
  useEffect(() => { fetch(`${SF_API}/products`).then(r => r.json()).then(d => setProducts(d.products || d || [])).catch(() => {}); }, []);
  return (
    <div>
      <SH title="Products" subtitle={`${products.length} products in catalog`}
        action={<button style={{ fontSize: 12, padding: '6px 14px', background: '#16a34a', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontWeight: 600 }}><Plus size={12} /> Add Product</button>} />
      {products.length === 0 ? <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>No products yet. Add your first product.</div> : (
        <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
          <thead><tr style={{ borderBottom: '2px solid #e5e2dc', textAlign: 'left' }}>
            <th style={{ padding: 8 }}>SKU</th><th style={{ padding: 8 }}>Name</th><th style={{ padding: 8 }}>Category</th>
            <th style={{ padding: 8 }}>Cost</th><th style={{ padding: 8 }}>Price</th><th style={{ padding: 8 }}>Margin</th>
          </tr></thead>
          <tbody>{products.map((p: any) => {
            const margin = p.retail_price > 0 ? ((p.retail_price - p.cost_price) / p.retail_price * 100) : 0;
            return (
              <tr key={p.id} style={{ borderBottom: '1px solid #f0ede6' }}>
                <td style={{ padding: 8, fontFamily: 'monospace', fontSize: 11 }}>{p.sku}</td>
                <td style={{ padding: 8, fontWeight: 500 }}>{p.name}</td>
                <td style={{ padding: 8, color: '#666' }}>{p.category || '—'}</td>
                <td style={{ padding: 8, color: '#888' }}>${(p.cost_price || 0).toFixed(2)}</td>
                <td style={{ padding: 8, fontWeight: 600 }}>${(p.retail_price || 0).toFixed(2)}</td>
                <td style={{ padding: 8, color: margin > 30 ? '#16a34a' : margin > 15 ? '#b8960c' : '#dc2626', fontWeight: 600 }}>{margin.toFixed(0)}%</td>
              </tr>
            );
          })}</tbody>
        </table>
      )}
    </div>
  );
}

function InventorySection() {
  const [items, setItems] = useState<any[]>([]);
  useEffect(() => { fetch(`${SF_API}/inventory/1`).then(r => r.json()).then(d => setItems(d.inventory || d || [])).catch(() => {}); }, []);
  return (
    <div>
      <SH title="Inventory" subtitle="Stock levels across all locations" />
      {items.length === 0 ? <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>No inventory data. Add products and stock levels first.</div> : (
        <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
          <thead><tr style={{ borderBottom: '2px solid #e5e2dc', textAlign: 'left' }}>
            <th style={{ padding: 8 }}>Product</th><th style={{ padding: 8 }}>Location</th><th style={{ padding: 8 }}>Qty</th><th style={{ padding: 8 }}>Reorder At</th><th style={{ padding: 8 }}>Status</th>
          </tr></thead>
          <tbody>{items.map((it: any) => (
            <tr key={it.id} style={{ borderBottom: '1px solid #f0ede6' }}>
              <td style={{ padding: 8, fontWeight: 500 }}>{it.product_name || `Product #${it.product_id}`}</td>
              <td style={{ padding: 8, color: '#666' }}>{it.bin_location || '—'}</td>
              <td style={{ padding: 8, fontWeight: 600, color: it.quantity <= it.reorder_point ? '#dc2626' : '#16a34a' }}>{it.quantity}</td>
              <td style={{ padding: 8, color: '#888' }}>{it.reorder_point}</td>
              <td style={{ padding: 8 }}><span style={{ fontSize: 10, fontWeight: 600, padding: '2px 8px', borderRadius: 8, background: it.quantity <= it.reorder_point ? '#fef2f2' : '#f0fdf4', color: it.quantity <= it.reorder_point ? '#dc2626' : '#16a34a' }}>{it.quantity <= it.reorder_point ? 'Low Stock' : 'OK'}</span></td>
            </tr>
          ))}</tbody>
        </table>
      )}
    </div>
  );
}

function CustomersSection() {
  const [customers, setCustomers] = useState<any[]>([]);
  useEffect(() => { fetch(`${SF_API}/customers`).then(r => r.json()).then(d => setCustomers(d.customers || d || [])).catch(() => {}); }, []);
  return (
    <div>
      <SH title="Customers" subtitle="Customer profiles and loyalty program"
        action={<button style={{ fontSize: 12, padding: '6px 14px', background: '#16a34a', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontWeight: 600 }}><Plus size={12} /> Add Customer</button>} />
      {customers.length === 0 ? <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>No customers yet.</div> : (
        <div style={{ display: 'grid', gap: 10, gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))' }}>
          {customers.map((c: any) => (
            <div key={c.id} style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 10, padding: 14 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ fontWeight: 600, fontSize: 13 }}>{c.first_name} {c.last_name}</div>
                <span style={{ fontSize: 9, fontWeight: 700, padding: '2px 8px', borderRadius: 10, background: c.loyalty_tier === 'vip' ? '#fdf8eb' : '#f5f3ef', color: c.loyalty_tier === 'vip' ? '#b8960c' : '#888' }}>{(c.loyalty_tier || 'standard').toUpperCase()}</span>
              </div>
              <div style={{ fontSize: 11, color: '#888', marginTop: 4 }}>{c.email || c.phone || '—'}</div>
              <div style={{ display: 'flex', gap: 12, marginTop: 6, fontSize: 10, color: '#666' }}>
                <span><Star size={10} /> {c.loyalty_points || 0} pts</span>
                <span>${(c.total_spent || 0).toLocaleString()} spent</span>
                <span>{c.visit_count || 0} visits</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function PurchaseOrdersSection() {
  return <div><SH title="Purchase Orders" subtitle="Manage vendor orders and receiving" /><div style={{ textAlign: 'center', padding: 40, color: '#999' }}>No purchase orders yet.</div></div>;
}
function EmployeesSection() {
  const [employees, setEmployees] = useState<any[]>([]);
  useEffect(() => { fetch(`${SF_API}/employees`).then(r => r.json()).then(d => setEmployees(d.employees || d || [])).catch(() => {}); }, []);
  return (
    <div>
      <SH title="Employees" subtitle="Staff management and shift tracking"
        action={<button style={{ fontSize: 12, padding: '6px 14px', background: '#16a34a', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontWeight: 600 }}><Plus size={12} /> Add Employee</button>} />
      {employees.length === 0 ? <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>No employees yet.</div> : (
        <div style={{ display: 'grid', gap: 10, gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))' }}>
          {employees.map((e: any) => (
            <div key={e.id} style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 10, padding: 14 }}>
              <div style={{ fontWeight: 600, fontSize: 13 }}>{e.name}</div>
              <div style={{ fontSize: 11, color: '#888', textTransform: 'capitalize' }}>{e.role}</div>
              <div style={{ fontSize: 11, color: '#666', marginTop: 4 }}>{e.email || e.phone || '—'}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
function GiftCardsSection() {
  return <div><SH title="Gift Cards" subtitle="Create and manage gift cards" /><div style={{ textAlign: 'center', padding: 40, color: '#999' }}>No gift cards yet.</div></div>;
}
function SuppliersSection() {
  return <div><SH title="Suppliers" subtitle="Vendor management" /><div style={{ textAlign: 'center', padding: 40, color: '#999' }}>No suppliers yet.</div></div>;
}
function ReportsSection() {
  return (
    <div>
      <SH title="Reports" subtitle="Sales analytics and performance metrics" />
      <div style={{ display: 'grid', gap: 12, gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))' }}>
        {[
          { label: 'Daily Sales', icon: DollarSign, desc: 'Sales summary by day' },
          { label: 'Top Products', icon: TrendingUp, desc: 'Best selling items' },
          { label: 'Revenue', icon: BarChart3, desc: 'Revenue over time' },
          { label: 'Inventory Value', icon: Package, desc: 'Total stock value' },
          { label: 'Employee Sales', icon: UserCheck, desc: 'Performance by employee' },
          { label: 'Tax Summary', icon: DollarSign, desc: 'Tax collected by period' },
        ].map((r, i) => (
          <div key={i} style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 10, padding: 16, cursor: 'pointer' }}>
            <r.icon size={20} style={{ color: '#16a34a', marginBottom: 8 }} />
            <div style={{ fontSize: 13, fontWeight: 600 }}>{r.label}</div>
            <div style={{ fontSize: 10, color: '#888', marginTop: 2 }}>{r.desc}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
