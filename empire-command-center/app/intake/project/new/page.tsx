'use client';
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft, ArrowRight, Check, Send } from 'lucide-react';
import IntakeNav from '../../../components/intake/IntakeNav';
import PhotoUploader from '../../../components/intake/PhotoUploader';
import MeasurementInput, { Measurement } from '../../../components/intake/MeasurementInput';
import { intakeFetch, getToken } from '../../../lib/intake-auth';

const steps = ['Project Info', 'Photos & Scans', 'Measurements', 'Notes & Submit'];

export default function NewProject() {
  const router = useRouter();
  const [user, setUser] = useState<any>(null);
  const [step, setStep] = useState(0);
  const [projectId, setProjectId] = useState<string | null>(null);
  const [photos, setPhotos] = useState<any[]>([]);
  const [submitting, setSubmitting] = useState(false);

  // Step 1 fields
  const [name, setName] = useState('');
  const [address, setAddress] = useState('');
  const [treatment, setTreatment] = useState('');
  const [style, setStyle] = useState('');
  const [scope, setScope] = useState('');

  // Step 3 fields
  const [measurements, setMeasurements] = useState<Measurement[]>([
    { room: '', width: '', height: '', reference: 'none' },
  ]);

  // Step 4 fields
  const [notes, setNotes] = useState('');

  useEffect(() => {
    if (!getToken()) { router.push('/intake/login'); return; }
    intakeFetch('/me').then(setUser).catch(() => router.push('/intake/login'));
  }, [router]);

  const createProject = async () => {
    const proj = await intakeFetch('/projects', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, address, treatment, style, scope }),
    });
    setProjectId(proj.id);
    return proj.id;
  };

  const saveDetails = async () => {
    if (!projectId) return;
    await intakeFetch(`/projects/${projectId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        measurements: measurements.filter(m => m.room || m.width || m.height),
        notes,
      }),
    });
  };

  const handleNext = async () => {
    if (step === 0) {
      if (!name.trim()) return;
      if (!projectId) await createProject();
      else {
        await intakeFetch(`/projects/${projectId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name, address, treatment, style, scope }),
        });
      }
    }
    setStep(s => s + 1);
  };

  const handleSubmit = async () => {
    if (!projectId) return;
    setSubmitting(true);
    try {
      await saveDetails();
      await intakeFetch(`/projects/${projectId}/submit`, { method: 'POST' });
      router.push(`/intake/project/${projectId}`);
    } catch (_err) {
      setSubmitting(false);
    }
  };

  const refreshPhotos = async () => {
    if (!projectId) return;
    const proj = await intakeFetch(`/projects/${projectId}`);
    setPhotos(proj.photos || []);
  };

  return (
    <div className="min-h-screen bg-[#faf9f7]">
      <IntakeNav user={user} />

      <div className="max-w-2xl mx-auto px-4 sm:px-6 py-8">
        {/* Step indicator */}
        <div className="flex items-center gap-1 mb-8">
          {steps.map((label, i) => (
            <div key={i} className="flex-1 flex flex-col items-center">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold mb-1 transition-colors ${
                i < step ? 'bg-[#16a34a] text-white' :
                i === step ? 'bg-[#c9a84c] text-white' :
                'bg-[#e5e0d8] text-[#aaa]'
              }`}>
                {i < step ? <Check size={14} /> : i + 1}
              </div>
              <span className={`text-[10px] font-medium ${i <= step ? 'text-[#1a1a1a]' : 'text-[#aaa]'}`}>
                {label}
              </span>
            </div>
          ))}
        </div>

        <div className="bg-white border border-[#e5e0d8] rounded-xl p-6">
          {/* Step 1: Project Info */}
          {step === 0 && (
            <div className="space-y-4">
              <h2 className="text-lg font-bold text-[#1a1a1a] mb-4">Tell Us About Your Project</h2>
              <div>
                <label className="block text-xs font-medium text-[#555] mb-1.5">Project Name *</label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={e => setName(e.target.value)}
                  className="w-full px-3 py-2.5 text-sm border border-[#e5e0d8] rounded-lg focus:border-[#c9a84c] outline-none"
                  placeholder="e.g., Living Room Drapes"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-[#555] mb-1.5">Address</label>
                <input
                  type="text"
                  value={address}
                  onChange={e => setAddress(e.target.value)}
                  className="w-full px-3 py-2.5 text-sm border border-[#e5e0d8] rounded-lg focus:border-[#c9a84c] outline-none"
                  placeholder="123 Main St, City, ST"
                />
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-[#555] mb-1.5">Treatment Type</label>
                  <select
                    value={treatment}
                    onChange={e => setTreatment(e.target.value)}
                    className="w-full px-3 py-2.5 text-sm border border-[#e5e0d8] rounded-lg focus:border-[#c9a84c] outline-none"
                  >
                    <option value="">Select...</option>
                    <option value="drapery">Drapery</option>
                    <option value="blinds">Blinds</option>
                    <option value="shades">Shades</option>
                    <option value="shutters">Shutters</option>
                    <option value="upholstery">Upholstery</option>
                    <option value="bedding">Bedding</option>
                    <option value="other">Other / Not Sure</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-[#555] mb-1.5">Style Preference</label>
                  <select
                    value={style}
                    onChange={e => setStyle(e.target.value)}
                    className="w-full px-3 py-2.5 text-sm border border-[#e5e0d8] rounded-lg focus:border-[#c9a84c] outline-none"
                  >
                    <option value="">Select...</option>
                    <option value="modern">Modern / Minimalist</option>
                    <option value="traditional">Traditional / Classic</option>
                    <option value="transitional">Transitional</option>
                    <option value="bohemian">Bohemian</option>
                    <option value="coastal">Coastal</option>
                    <option value="farmhouse">Farmhouse</option>
                    <option value="not-sure">Not Sure — Surprise Me</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-[#555] mb-1.5">Scope</label>
                <select
                  value={scope}
                  onChange={e => setScope(e.target.value)}
                  className="w-full px-3 py-2.5 text-sm border border-[#e5e0d8] rounded-lg focus:border-[#c9a84c] outline-none"
                >
                  <option value="">Select...</option>
                  <option value="single-window">Single Window</option>
                  <option value="single-room">Single Room</option>
                  <option value="multiple-rooms">Multiple Rooms</option>
                  <option value="whole-home">Whole Home</option>
                </select>
              </div>
            </div>
          )}

          {/* Step 2: Photos & Scans */}
          {step === 1 && projectId && (
            <div>
              <h2 className="text-lg font-bold text-[#1a1a1a] mb-2">Upload Photos</h2>
              <p className="text-xs text-[#777] mb-4">
                Take photos of your windows, rooms, or any inspiration images. We&apos;ll use AI to help analyze them.
              </p>
              <PhotoUploader projectId={projectId} photos={photos} onUpload={refreshPhotos} />
            </div>
          )}

          {/* Step 3: Measurements */}
          {step === 2 && (
            <div>
              <h2 className="text-lg font-bold text-[#1a1a1a] mb-2">Window Measurements</h2>
              <p className="text-xs text-[#777] mb-4">
                Enter approximate measurements. Don&apos;t worry about being exact — we&apos;ll verify everything before production.
              </p>
              <MeasurementInput measurements={measurements} onChange={setMeasurements} />
            </div>
          )}

          {/* Step 4: Notes & Submit */}
          {step === 3 && (
            <div>
              <h2 className="text-lg font-bold text-[#1a1a1a] mb-2">Additional Notes</h2>
              <p className="text-xs text-[#777] mb-4">
                Anything else we should know? Special requests, fabric preferences, budget range, timeline?
              </p>
              <textarea
                value={notes}
                onChange={e => setNotes(e.target.value)}
                rows={5}
                className="w-full px-3 py-2.5 text-sm border border-[#e5e0d8] rounded-lg focus:border-[#c9a84c] outline-none resize-none"
                placeholder="Tell us anything that helps us create the perfect proposal for you..."
              />
              <div className="mt-6 p-4 rounded-lg bg-[#fdf8eb] border border-[#c9a84c]/20">
                <h3 className="text-sm font-semibold text-[#1a1a1a] mb-1">Ready to submit?</h3>
                <p className="text-xs text-[#777]">
                  We&apos;ll review your project and send you a 3-tier proposal within 24 hours. You can always add more photos or details later.
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Navigation buttons */}
        <div className="flex items-center justify-between mt-6">
          {step > 0 ? (
            <button
              onClick={() => setStep(s => s - 1)}
              className="px-4 py-2.5 text-xs font-semibold text-[#777] border border-[#e5e0d8] rounded-lg hover:border-[#c9a84c] hover:text-[#c9a84c] transition-colors flex items-center gap-1.5"
            >
              <ArrowLeft size={14} /> Back
            </button>
          ) : (
            <button
              onClick={() => router.push('/intake/dashboard')}
              className="px-4 py-2.5 text-xs font-semibold text-[#777] border border-[#e5e0d8] rounded-lg hover:border-[#c9a84c] hover:text-[#c9a84c] transition-colors flex items-center gap-1.5"
            >
              <ArrowLeft size={14} /> Dashboard
            </button>
          )}

          {step < 3 ? (
            <button
              onClick={handleNext}
              disabled={step === 0 && !name.trim()}
              className="px-6 py-2.5 text-xs font-semibold bg-[#c9a84c] text-white rounded-lg hover:bg-[#b8960c] transition-colors disabled:opacity-50 flex items-center gap-1.5"
            >
              Next <ArrowRight size={14} />
            </button>
          ) : (
            <button
              onClick={handleSubmit}
              disabled={submitting}
              className="px-6 py-2.5 text-xs font-semibold bg-[#16a34a] text-white rounded-lg hover:bg-[#15803d] transition-colors disabled:opacity-50 flex items-center gap-1.5"
            >
              {submitting ? 'Submitting...' : (<><Send size={14} /> Submit Project</>)}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
