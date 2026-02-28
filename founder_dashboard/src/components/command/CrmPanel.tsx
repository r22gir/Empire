'use client';
import { useState } from 'react';
import { useContacts } from '@/hooks/useContacts';
import { Search, UserPlus, X } from 'lucide-react';

export default function CrmPanel() {
  const { contacts, total, isOnline, isLoading, search, setSearch, createContact } = useContacts();
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
    <div className="cc-panel">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <p className="cc-panel-header mb-0">CRM Personal</p>
          <span
            className="text-[10px] px-1.5 py-0.5 rounded font-mono"
            style={{ background: 'var(--elevated)', color: 'var(--text-muted)' }}
          >
            {total}
          </span>
        </div>
        <div className="flex gap-1">
          <span className={isOnline ? 'dot-online' : 'dot-offline'} />
          <button
            onClick={() => setShowAdd(!showAdd)}
            className="p-1 rounded-lg transition"
            style={{ color: 'var(--text-muted)' }}
            onMouseEnter={e => (e.currentTarget.style.color = 'var(--gold)')}
            onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-muted)')}
          >
            {showAdd ? <X className="w-3.5 h-3.5" /> : <UserPlus className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>

      {/* Quick add form */}
      {showAdd && (
        <div className="mb-3 p-2.5 rounded-lg space-y-2" style={{ background: 'var(--raised)', border: '1px solid var(--border)' }}>
          <input
            type="text"
            placeholder="Name"
            value={newContact.name}
            onChange={e => setNewContact({ ...newContact, name: e.target.value })}
            className="w-full rounded-lg px-2.5 py-1.5 text-xs outline-none"
            style={{ background: 'var(--elevated)', border: '1px solid var(--border)', color: 'var(--text-primary)' }}
          />
          <div className="flex gap-2">
            <select
              value={newContact.type}
              onChange={e => setNewContact({ ...newContact, type: e.target.value })}
              className="flex-1 rounded-lg px-2 py-1.5 text-xs outline-none cursor-pointer"
              style={{ background: 'var(--elevated)', border: '1px solid var(--border)', color: 'var(--text-primary)' }}
            >
              <option value="client">Client</option>
              <option value="contractor">Contractor</option>
              <option value="vendor">Vendor</option>
              <option value="other">Other</option>
            </select>
            <input
              type="text"
              placeholder="Phone"
              value={newContact.phone}
              onChange={e => setNewContact({ ...newContact, phone: e.target.value })}
              className="flex-1 rounded-lg px-2.5 py-1.5 text-xs outline-none"
              style={{ background: 'var(--elevated)', border: '1px solid var(--border)', color: 'var(--text-primary)' }}
            />
          </div>
          <button
            onClick={handleCreate}
            disabled={!newContact.name.trim()}
            className="w-full py-1.5 rounded-lg text-xs font-semibold transition"
            style={{
              background: newContact.name.trim() ? 'var(--gold)' : 'var(--elevated)',
              color: newContact.name.trim() ? '#0a0a0a' : 'var(--text-muted)',
            }}
          >
            Add Contact
          </button>
        </div>
      )}

      {/* Search */}
      <div className="relative mb-3">
        <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3 h-3" style={{ color: 'var(--text-muted)' }} />
        <input
          type="text"
          placeholder="Search contacts..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="w-full rounded-lg pl-7 pr-3 py-1.5 text-xs outline-none"
          style={{ background: 'var(--raised)', border: '1px solid var(--border)', color: 'var(--text-primary)' }}
          onFocus={e => (e.currentTarget.style.borderColor = 'var(--gold-border)')}
          onBlur={e => (e.currentTarget.style.borderColor = 'var(--border)')}
        />
      </div>

      {/* Contact list */}
      <div className="space-y-1.5 max-h-48 overflow-y-auto">
        {isLoading && contacts.length === 0 && (
          <p className="text-xs text-center py-3" style={{ color: 'var(--text-muted)' }}>Loading...</p>
        )}
        {!isLoading && contacts.length === 0 && (
          <p className="text-xs text-center py-3" style={{ color: 'var(--text-muted)' }}>No contacts</p>
        )}
        {contacts.slice(0, 6).map(c => (
          <div
            key={c.id}
            className="flex items-center gap-2 p-2 rounded-lg transition"
            style={{ background: 'var(--raised)' }}
            onMouseEnter={e => (e.currentTarget.style.background = 'var(--elevated)')}
            onMouseLeave={e => (e.currentTarget.style.background = 'var(--raised)')}
          >
            <div
              className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold shrink-0"
              style={{ background: 'var(--gold-pale)', color: 'var(--gold)' }}
            >
              {c.name.charAt(0).toUpperCase()}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium truncate" style={{ color: 'var(--text-primary)' }}>{c.name}</p>
              <p className="text-[10px] truncate" style={{ color: 'var(--text-muted)' }}>
                {c.phone || c.email || '--'}
              </p>
            </div>
            <span
              className="text-[10px] px-1.5 py-0.5 rounded shrink-0"
              style={{ background: 'var(--elevated)', color: 'var(--text-muted)' }}
            >
              {c.type}
            </span>
          </div>
        ))}
        {contacts.length > 6 && (
          <p className="text-[10px] text-center pt-1" style={{ color: 'var(--text-muted)' }}>
            +{contacts.length - 6} more
          </p>
        )}
      </div>
    </div>
  );
}
