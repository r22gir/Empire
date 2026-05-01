'use client';

import { useState, useEffect, lazy, Suspense } from 'react';
import { useRouter } from 'next/navigation';
import {
  Camera, Users, Search, FileText, Download, History, BarChart3,
  Loader2, Plus, ChevronRight, CheckCircle, Clock, Eye, BookOpen, CreditCard,
} from 'lucide-react';
import ProductDocs from '../business/docs/ProductDocs';
import PaymentModule from '../business/payments/PaymentModule';
import { API } from '../../lib/api';

const PhotoAnalysisPanel = lazy(() => import('../business/vision/PhotoAnalysisPanel'));

/* ═══════════════════════════════════════════════════════════
   Types
   ═══════════════════════════════════════════════════════════ */

interface AnalysisJob {
  id: string;
  customerName: string;
  customerEmail: string;
  photoCount: number;
  status: 'pending' | 'in-progress' | 'complete';
  stepsCompleted: number;
  createdAt: string;
  notes: string;
}

/* ═══════════════════════════════════════════════════════════
   Constants
   ═══════════════════════════════════════════════════════════ */

const NAV = [
  { id: 'analyzer', label: 'Photo Analyzer', icon: <Camera size={16} /> },
  { id: 'jobs', label: 'Analysis Jobs', icon: <FileText size={16} /> },
  { id: 'history', label: 'History', icon: <History size={16} /> },
  { id: 'stats', label: 'Statistics', icon: <BarChart3 size={16} /> },
  { id: 'payments', label: 'Payments', icon: <CreditCard size={16} /> },
  { id: 'docs', label: 'Docs', icon: <BookOpen size={16} /> },
];

const Loading = () => (
  <div className="flex-1 flex items-center justify-center py-16">
    <Loader2 size={20} className="animate-spin text-[#7c3aed]" />
  </div>
);

/* ═══════════════════════════════════════════════════════════
   Main Component
   ═══════════════════════════════════════════════════════════ */

export default function VisionAnalysisPage() {
  const [section, setSection] = useState('analyzer');
  const [customers, setCustomers] = useState<any[]>([]);
  const [selectedCustomer, setSelectedCustomer] = useState<any>(null);
  const [customerSearch, setCustomerSearch] = useState('');
  const [jobs, setJobs] = useState<AnalysisJob[]>([]);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const router = useRouter();

  // Fetch CRM customers for assignment
  useEffect(() => {
    fetch(`${API}/crm/customers`).then(r => r.json())
      .then(data => setCustomers(data.customers || data || []))
      .catch(() => {});
  }, []);

  const filteredCustomers = customerSearch.length >= 2
    ? customers.filter((c: any) =>
        (c.name || '').toLowerCase().includes(customerSearch.toLowerCase()) ||
        (c.email || '').toLowerCase().includes(customerSearch.toLowerCase())
      )
    : [];

  const handleSaveQuote = (quoteData: any) => {
    const newJob: AnalysisJob = {
      id: `AJ-${String(jobs.length + 1).padStart(3, '0')}`,
      customerName: quoteData.customer || selectedCustomer?.name || 'Walk-in',
      customerEmail: quoteData.email || selectedCustomer?.email || '',
      photoCount: quoteData.photos?.length || 0,
      status: 'complete',
      stepsCompleted: 4,
      createdAt: new Date().toISOString(),
      notes: `${quoteData.styles?.length || 0} styles, ${quoteData.photos?.length || 0} photos`,
    };
    setJobs(prev => [newJob, ...prev]);
    setSection('jobs');
  };

  const renderSection = () => {
    switch (section) {
      case 'analyzer':
        return (
          <div style={{ maxWidth: 1000, margin: '0 auto' }}>
            {/* Customer Assignment Bar */}
            <div className="empire-card flat" style={{ padding: '14px 18px', marginBottom: 16 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <Users size={16} style={{ color: '#7c3aed', flexShrink: 0 }} />
                <span style={{ fontSize: 11, fontWeight: 700, color: '#777', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  Assign to Customer
                </span>
                {selectedCustomer ? (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, flex: 1 }}>
                    <div style={{
                      width: 28, height: 28, borderRadius: '50%', background: '#7c3aed',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontSize: 11, fontWeight: 700, color: '#fff',
                    }}>
                      {selectedCustomer.name?.charAt(0)?.toUpperCase()}
                    </div>
                    <div>
                      <div style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a' }}>{selectedCustomer.name}</div>
                      <div style={{ fontSize: 10, color: '#999' }}>{selectedCustomer.email}</div>
                    </div>
                    <span className="status-pill" style={{ background: '#f0fdf4', color: '#16a34a', marginLeft: 8 }}>
                      <CheckCircle size={10} /> Assigned
                    </span>
                    <button
                      onClick={() => { setSelectedCustomer(null); setCustomerSearch(''); }}
                      className="cursor-pointer hover:bg-[#f0ede8] transition-colors"
                      style={{ marginLeft: 'auto', padding: '4px 10px', borderRadius: 8, border: '1px solid #ece8e0', background: '#faf9f7', fontSize: 10, fontWeight: 600, color: '#999' }}
                    >
                      Change
                    </button>
                  </div>
                ) : (
                  <div style={{ flex: 1, position: 'relative' }}>
                    <div style={{ position: 'relative' }}>
                      <Search size={14} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: '#bbb' }} />
                      <input
                        value={customerSearch}
                        onChange={e => setCustomerSearch(e.target.value)}
                        placeholder="Search customer name or email..."
                        className="outline-none focus:border-[#7c3aed] transition-colors"
                        style={{ width: '100%', padding: '8px 12px 8px 32px', fontSize: 12, border: '1px solid #ece8e0', borderRadius: 10, background: '#faf9f7' }}
                      />
                    </div>
                    {filteredCustomers.length > 0 && (
                      <div style={{
                        position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 10, marginTop: 4,
                        background: '#fff', borderRadius: 10, border: '1px solid #ece8e0',
                        boxShadow: '0 4px 20px rgba(0,0,0,0.1)', maxHeight: 200, overflowY: 'auto',
                      }}>
                        {filteredCustomers.slice(0, 8).map((c: any) => (
                          <button
                            key={c.id || c.name}
                            onClick={() => { setSelectedCustomer(c); setCustomerSearch(''); }}
                            className="w-full flex items-center gap-3 cursor-pointer hover:bg-[#faf9f7] transition-colors"
                            style={{ padding: '10px 14px', border: 'none', background: 'transparent', textAlign: 'left' }}
                          >
                            <div style={{
                              width: 28, height: 28, borderRadius: '50%', background: '#7c3aed',
                              display: 'flex', alignItems: 'center', justifyContent: 'center',
                              fontSize: 11, fontWeight: 700, color: '#fff', flexShrink: 0,
                            }}>
                              {c.name?.charAt(0)?.toUpperCase()}
                            </div>
                            <div>
                              <div style={{ fontSize: 12, fontWeight: 600, color: '#1a1a1a' }}>{c.name}</div>
                              <div style={{ fontSize: 10, color: '#999' }}>{c.email || c.phone || ''}</div>
                            </div>
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Photo Analysis Panel */}
            <Suspense fallback={<Loading />}>
              <PhotoAnalysisPanel
                customerName={selectedCustomer?.name}
                customerEmail={selectedCustomer?.email}
                onSaveQuote={handleSaveQuote}
              />
            </Suspense>
          </div>
        );

      case 'jobs':
        return (
          <div style={{ maxWidth: 900, margin: '0 auto' }}>
            <div className="flex items-center justify-between mb-4">
              <h2 style={{ fontSize: 18, fontWeight: 700, color: '#1a1a1a', margin: 0 }}>Analysis Jobs</h2>
              <button
                onClick={() => setSection('analyzer')}
                className="flex items-center gap-2 cursor-pointer transition-all hover:brightness-110"
                style={{ padding: '8px 16px', borderRadius: 10, background: '#7c3aed', color: '#fff', fontSize: 12, fontWeight: 700, border: 'none' }}
              >
                <Plus size={14} /> New Analysis
              </button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {jobs.map(job => (
                <div
                  key={job.id}
                  className="empire-card flat cursor-pointer hover:shadow-md transition-all"
                  style={{ padding: '14px 18px' }}
                  onClick={() => { setActiveJobId(job.id); setSection('analyzer'); }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                    <div style={{
                      width: 40, height: 40, borderRadius: 12,
                      background: job.status === 'complete' ? '#dcfce7' : job.status === 'in-progress' ? '#fdf8e8' : '#f5f3ef',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                    }}>
                      {job.status === 'complete' ? <CheckCircle size={20} style={{ color: '#16a34a' }} /> :
                       job.status === 'in-progress' ? <Eye size={20} style={{ color: '#b8960c' }} /> :
                       <Clock size={20} style={{ color: '#999' }} />}
                    </div>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <span style={{ fontSize: 14, fontWeight: 700, color: '#1a1a1a' }}>{job.customerName}</span>
                        <span style={{ fontSize: 10, color: '#999' }}>{job.id}</span>
                        <span className="status-pill" style={{
                          background: job.status === 'complete' ? '#dcfce7' : job.status === 'in-progress' ? '#fdf8e8' : '#f5f3ef',
                          color: job.status === 'complete' ? '#16a34a' : job.status === 'in-progress' ? '#b8960c' : '#999',
                        }}>
                          {job.status === 'complete' ? 'Complete' : job.status === 'in-progress' ? 'In Progress' : 'Pending'}
                        </span>
                      </div>
                      <div style={{ fontSize: 11, color: '#777', marginTop: 2 }}>
                        {job.photoCount} photos · {job.stepsCompleted}/4 steps · {job.notes}
                      </div>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4 }}>
                      <div style={{ fontSize: 11, color: '#999' }}>{new Date(job.createdAt).toLocaleDateString()}</div>
                      <div style={{ display: 'flex', gap: 4 }}>
                        <button
                          onClick={(e) => { e.stopPropagation(); setActiveJobId(job.id); setSection('analyzer'); }}
                          className="flex items-center gap-1 cursor-pointer hover:bg-[#faf5ff] transition-colors"
                          style={{ padding: '3px 8px', borderRadius: 6, border: '1px solid #e9d5ff', background: '#faf9f7', fontSize: 9, fontWeight: 700, color: '#7c3aed' }}
                        >
                          <Plus size={10} /> Photos
                        </button>
                        {job.status === 'complete' && (
                          <button
                            onClick={(e) => { e.stopPropagation(); router.push(`/quote/${job.customerEmail || job.id}`); }}
                            className="flex items-center gap-1 cursor-pointer hover:bg-[#f0fdf4] transition-colors"
                            style={{ padding: '3px 8px', borderRadius: 6, border: '1px solid #bbf7d0', background: '#faf9f7', fontSize: 9, fontWeight: 700, color: '#16a34a' }}
                          >
                            <FileText size={10} /> Quote
                          </button>
                        )}
                      </div>
                    </div>
                    <ChevronRight size={16} style={{ color: '#ccc' }} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        );

      case 'history':
        return (
          <div style={{ maxWidth: 900, margin: '0 auto' }}>
            <h2 style={{ fontSize: 18, fontWeight: 700, color: '#1a1a1a', marginBottom: 16 }}>Analysis History</h2>
            <div className="empire-card flat" style={{ padding: '40px 20px', textAlign: 'center' }}>
              <History size={40} style={{ color: '#ddd', margin: '0 auto 12px' }} />
              <div style={{ fontSize: 14, fontWeight: 600, color: '#999' }}>Analysis history will populate as you complete jobs</div>
              <div style={{ fontSize: 12, color: '#bbb', marginTop: 4 }}>Completed analyses are saved with customer data, photos, and results</div>
            </div>
          </div>
        );

      case 'stats':
        return (
          <div style={{ maxWidth: 900, margin: '0 auto' }}>
            <h2 style={{ fontSize: 18, fontWeight: 700, color: '#1a1a1a', marginBottom: 16 }}>Analysis Statistics</h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 20 }}>
              {[
                { label: 'Total Analyses', value: String(jobs.length), color: '#7c3aed' },
                { label: 'Photos Processed', value: String(jobs.reduce((s, j) => s + j.photoCount, 0)), color: '#2563eb' },
                { label: 'Completed', value: String(jobs.filter(j => j.status === 'complete').length), color: '#16a34a' },
                { label: 'Pending', value: String(jobs.filter(j => j.status === 'pending').length), color: '#b8960c' },
              ].map(stat => (
                <div key={stat.label} className="empire-card flat" style={{ padding: '16px 14px', textAlign: 'center' }}>
                  <div style={{ fontSize: 28, fontWeight: 700, color: stat.color }}>{stat.value}</div>
                  <div style={{ fontSize: 10, fontWeight: 700, color: '#777', textTransform: 'uppercase', letterSpacing: '0.05em', marginTop: 4 }}>{stat.label}</div>
                </div>
              ))}
            </div>

            <div className="empire-card flat" style={{ padding: '20px' }}>
              <div className="section-label" style={{ marginBottom: 12 }}>Analysis Modes Used</div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10 }}>
                {[
                  { label: 'Measure', count: jobs.filter(j => j.stepsCompleted >= 1).length, color: '#2563eb' },
                  { label: 'Upholstery', count: jobs.filter(j => j.stepsCompleted >= 2).length, color: '#7c3aed' },
                  { label: 'Design Mockup', count: jobs.filter(j => j.stepsCompleted >= 3).length, color: '#b8960c' },
                  { label: 'Install Plan', count: jobs.filter(j => j.stepsCompleted >= 4).length, color: '#16a34a' },
                ].map(m => (
                  <div key={m.label} style={{ padding: '12px', borderRadius: 10, background: '#faf9f7', border: '1px solid #ece8e0', textAlign: 'center' }}>
                    <div style={{ fontSize: 20, fontWeight: 700, color: m.color }}>{m.count}</div>
                    <div style={{ fontSize: 11, fontWeight: 600, color: '#777' }}>{m.label}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        );

      case 'payments':
        return <PaymentModule product="vision" />;

      case 'docs':
        return <div style={{ padding: 24 }}><ProductDocs product="vision" /></div>;

      default:
        return null;
    }
  };

  return (
    <div className="flex-1 flex overflow-hidden">
      {/* Sidebar */}
      <div
        className="border-r border-[var(--border)] bg-[var(--panel)] shrink-0 overflow-y-auto"
        style={{ width: 210, padding: '16px 10px' }}
      >
        <div className="flex items-center gap-2 px-2 mb-4">
          <Camera size={20} className="text-[#7c3aed]" />
          <div>
            <div style={{ fontSize: 15, fontWeight: 700, color: '#1a1a1a' }}>AI Vision</div>
            <div style={{ fontSize: 10, color: '#999' }}>Photo Analysis Tool</div>
          </div>
        </div>

        {NAV.map(item => {
          const active = section === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setSection(item.id)}
              className="w-full flex items-center gap-2.5 cursor-pointer transition-all"
              style={{
                padding: '10px 12px', borderRadius: 10, marginBottom: 2, border: 'none', textAlign: 'left',
                background: active ? '#7c3aed10' : 'transparent',
                color: active ? '#7c3aed' : '#777',
                fontWeight: active ? 700 : 500,
                fontSize: 13,
              }}
            >
              <span style={{ color: active ? '#7c3aed' : '#bbb' }}>{item.icon}</span>
              {item.label}
            </button>
          );
        })}

        {/* Quick Stats */}
        <div style={{ marginTop: 20, padding: '12px', borderRadius: 10, background: '#faf5ff', border: '1px solid #e9d5ff' }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: '#7c3aed', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 8 }}>
            Quick Stats
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
              <span style={{ color: '#777' }}>Total Jobs</span>
              <span style={{ fontWeight: 700, color: '#1a1a1a' }}>{jobs.length}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
              <span style={{ color: '#777' }}>Complete</span>
              <span style={{ fontWeight: 700, color: '#16a34a' }}>{jobs.filter(j => j.status === 'complete').length}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
              <span style={{ color: '#777' }}>In Progress</span>
              <span style={{ fontWeight: 700, color: '#b8960c' }}>{jobs.filter(j => j.status === 'in-progress').length}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
              <span style={{ color: '#777' }}>Photos</span>
              <span style={{ fontWeight: 700, color: '#7c3aed' }}>{jobs.reduce((s, j) => s + j.photoCount, 0)}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-y-auto" style={{ padding: '24px 36px' }}>
        {renderSection()}
      </div>
    </div>
  );
}
