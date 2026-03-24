'use client';
import { useCallback, useState } from 'react';
import PatternTemplateGenerator from '../../components/tools/PatternTemplateGenerator';
import { API } from '../../lib/api';

export default function PatternTemplatesPage() {
  const [status, setStatus] = useState<string | null>(null);

  const handleSave = useCallback(async (
    shape: string,
    params: Record<string, any>,
    _result: any,
    projectName: string
  ) => {
    try {
      setStatus('saving');
      const res = await fetch(`${API}/patterns/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: projectName || `${shape} - ${new Date().toLocaleDateString()}`,
          shape_type: shape,
          dimensions: params,
        }),
      });
      if (!res.ok) throw new Error(`Save failed (${res.status})`);
      setStatus('saved');
      setTimeout(() => setStatus(null), 2000);
    } catch (e: any) {
      setStatus(null);
      alert(e.message || 'Save failed');
    }
  }, []);

  return (
    <div className="relative">
      {status === 'saving' && (
        <div className="fixed top-4 right-4 z-50 px-4 py-2 bg-amber-100 text-amber-800 rounded-xl text-sm font-medium shadow-md">
          Saving template...
        </div>
      )}
      {status === 'saved' && (
        <div className="fixed top-4 right-4 z-50 px-4 py-2 bg-green-100 text-green-800 rounded-xl text-sm font-medium shadow-md">
          Template saved!
        </div>
      )}
      <PatternTemplateGenerator onSave={handleSave} />
    </div>
  );
}
