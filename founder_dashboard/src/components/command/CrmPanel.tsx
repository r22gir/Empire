'use client';
import { useState } from 'react';
import { useContacts } from '@/hooks/useContacts';
import { Search, UserPlus, X, ChevronDown, ChevronRight } from 'lucide-react';

export default function CrmPanel() {
  const { contacts, total, isOnline, isLoading, search, setSearch, createContact } = useContacts();
  const [open, setOpen] = useState(false);
  const [showAdd, setShowAdd] = useState(false);
  const [newContact, setNewContact] = useState({ name: '', type: 'client', phone: '' });

  const handleCreate = async () => {
    if (!newContact.name.trim()) return;
    await createContact({
      name: newContact.name.trim(),
      type: newContact.type,
      phone: newContact.phone || undefined,
    });
    setNewContact({ name: '', type: 'client', phone: '' });
    setShowAdd(false);
  };

  return (
    <div className="cc-panel" style={{ padding: '8px 10px' }}>
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-2"
      >
        <span className="text-[10px]">👤</span>
        <span className="flex-1 text-[11px] font-mono text-left" style={{ color: 'var(--text-secondary)' }}>
          CRM | {total} contacts
        </span>
        <span className={isOnline ? 'dot-online' : 'dot-offline'} />
        {open
          ? <ChevronDown className="w-3 h-3 shrink-0" style={{ color: 'var(--text-muted)' }} />
          : <ChevronRight className="w-3 h-3 shrink-0" style={{ color: 'var(--text-muted)' }} />
        }
      </button>

      {open && (
        <div className="mt-2 pt-2" style={{ borderTop: '1px solid var(--border)' }}>
          {/* Search + Add */}
          <div className="flex gap-1.5 mb-2">
            <div className="relative flex-1">
              <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-2.5 h-2.5" style={{ color: 'var(--text-muted)' }} />
              <input
                type="text"
                placeholder="Search..."
                value={search}
                onChange={e => setSearch(e.target.value)}
                className="w-full rounded-lg pl-6 pr-2 py-1 text-[10px] outline-none"
                style={{ background: 'var(--raised)', border: '1px solid var(--border)', color: 'var(--text-primary)' }}
              />
            </div>
            <button
              onClick={() => setShowAdd(!showAdd)}
              className="p-1 rounded-lg"
              style={{ color: 'var(--text-muted)' }}
            >
              {showAdd ? <X className="w-3 h-3" /> : <UserPlus className="w-3 h-3" />}
            </button>
          </div>

          {/* Quick add */}
          {showAdd && (
            <div className="mb-2 p-2 rounded-lg space-y-1.5" style={{ background: 'var(--raised)', border: '1px solid var(--border)' }}>
              <input
                type="text" placeholder="Name" value={newContact.name}
                onChange={e => setNewContact({ ...newContact, name: e.target.value })}
                className="w-full rounded px-2 py-1 text-[10px] outline-none"
                style={{ background: 'var(--elevated)', border: '1px solid var(--border)', color: 'var(--text-primary)' }}
              />
              <div className="flex gap-1.5">
                <select
                  value={newContact.type} onChange={e => setNewContact({ ...newContact, type: e.target.value })}
                  className="flex-1 rounded px-1.5 py-1 text-[10px] outline-none cursor-pointer"
                  style={{ background: 'var(--elevated)', border: '1px solid var(--border)', color: 'var(--text-primary)' }}
                >
                  <option value="client">Client</option>
                  <option value="contractor">Contractor</option>
                  <option value="vendor">Vendor</option>
                </select>
                <button
                  onClick={handleCreate} disabled={!newContact.name.trim()}
                  className="px-2 py-1 rounded text-[10px] font-semibold"
                  style={{ background: newContact.name.trim() ? 'var(--gold)' : 'var(--elevated)', color: newContact.name.trim() ? '#0a0a0a' : 'var(--text-muted)' }}
                >
                  Add
                </button>
              </div>
            </div>
          )}

          {/* Contact list */}
          <div className="space-y-1 max-h-32 overflow-y-auto">
            {isLoading && contacts.length === 0 && (
              <p className="text-[10px] text-center py-2" style={{ color: 'var(--text-muted)' }}>Loading...</p>
            )}
            {!isLoading && contacts.length === 0 && (
              <p className="text-[10px] text-center py-2" style={{ color: 'var(--text-muted)' }}>No contacts</p>
            )}
            {contacts.slice(0, 5).map(c => (
              <div key={c.id} className="flex items-center gap-1.5 px-1 py-1 rounded text-[10px]">
                <span
                  className="w-5 h-5 rounded-full flex items-center justify-center text-[9px] font-bold shrink-0"
                  style={{ background: 'var(--gold-pale)', color: 'var(--gold)' }}
                >
                  {c.name.charAt(0).toUpperCase()}
                </span>
                <span className="flex-1 truncate" style={{ color: 'var(--text-primary)' }}>{c.name}</span>
                <span style={{ color: 'var(--text-muted)' }}>{c.type}</span>
              </div>
            ))}
            {contacts.length > 5 && (
              <p className="text-[9px] text-center" style={{ color: 'var(--text-muted)' }}>+{contacts.length - 5} more</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
