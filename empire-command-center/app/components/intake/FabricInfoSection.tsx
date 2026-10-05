'use client';
import { useRef, useState } from 'react';
import { Camera, ChevronDown, ChevronUp, Link2, Upload, X } from 'lucide-react';
import { intakeUpload } from '../../lib/intake-auth';
import { FABRIC_MAX_BYTES, fabricTooLarge, fabricUploadKind } from '../../lib/fabricUpload';
import { isImageFile } from '../../lib/fileKind';
import { API_BASE } from '../../lib/api';

export interface FabricFile {
  path: string;
  original_name?: string;
  size?: number;
  content_type?: string;
}

export interface FabricInfo {
  id?: number;
  scope: 'room' | 'item';
  room_name?: string;
  item_name?: string;
  fabric_preference: 'picked_out' | 'com' | 'recommend' | 'not_sure';
  fabric_name?: string;
  color_pattern?: string;
  fabric_code?: string;
  supplier_url?: string;
  swatch_photo_path?: string;
  swatch_files?: FabricFile[];
  vertical_repeat?: number;
  horizontal_repeat?: number;
  fabric_width?: number;
  material_type?: string;
  yards_available?: number;
  client_notes?: string;
}

const PREFERENCES = [
  { value: 'picked_out', label: 'Yes, I have one picked out' },
  { value: 'com', label: 'Yes, I\'m supplying my own fabric (COM)' },
  { value: 'recommend', label: 'No, I need the workroom to recommend one' },
  { value: 'not_sure', label: 'Not sure yet' },
] as const;

const MATERIAL_TYPES = [
  'Upholstery', 'Marine Vinyl', 'Velvet', 'Linen', 'Outdoor', 'Leather', 'Other',
];

interface Props {
  fabric: FabricInfo;
  onChange: (fabric: FabricInfo) => void;
  onUploadPhoto?: (file: File) => Promise<string | null>;
  onRemove?: () => void;
  label?: string;
  projectId?: string;
  ensureProject?: () => Promise<string>;
}

function fileUrl(path: string): string {
  if (path.startsWith('http') || path.startsWith('blob:')) return path;
  return `${API_BASE}${path}`;
}

export default function FabricInfoSection({ fabric, onChange, onUploadPhoto, onRemove, label, projectId, ensureProject }: Props) {
  const [showDetails, setShowDetails] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const libraryRef = useRef<HTMLInputElement>(null);
  const cameraRef = useRef<HTMLInputElement>(null);
  const fabricRef = useRef(fabric);
  fabricRef.current = fabric;

  const hasDetails = fabric.fabric_preference === 'picked_out' || fabric.fabric_preference === 'com';
  const isCom = fabric.fabric_preference === 'com';

  const update = (field: keyof FabricInfo, value: any) => {
    onChange({ ...fabric, [field]: value });
  };

  const rememberFiles = (next: FabricFile[]) => {
    const current = fabricRef.current;
    const firstImage = next.find(file => isImageFile(file.original_name || file.path));
    onChange({
      ...current,
      swatch_files: next,
      swatch_photo_path: firstImage?.path || next[0]?.path || '',
    });
  };

  const uploadOne = async (file: File, pid: string): Promise<FabricFile> => {
    if (onUploadPhoto) {
      const path = await onUploadPhoto(file);
      if (!path) throw new Error('Upload did not return a file');
      return { path, original_name: file.name, size: file.size, content_type: file.type };
    }
    const kind = fabricUploadKind(file);
    const saved = await intakeUpload(`/projects/${pid}/${kind}`, file);
    const path = saved.path || (saved.filename ? `/intake_uploads/${pid}/${saved.filename}` : '');
    if (!path) throw new Error('Upload did not return a file');
    return {
      path,
      original_name: saved.original_name || file.name,
      size: saved.size || file.size,
      content_type: saved.content_type || file.type,
    };
  };

  const handleFiles = async (list: FileList | null) => {
    const files = Array.from(list || []);
    if (!files.length) return;
    setUploadError(null);
    const oversized = files.find(fabricTooLarge);
    if (oversized) {
      setUploadError(`${oversized.name} is over ${Math.round(FABRIC_MAX_BYTES / (1024 * 1024))} MB.`);
      return;
    }
    setUploading(true);
    try {
      let pid = projectId || '';
      if (!onUploadPhoto) {
        if (!pid && ensureProject) pid = await ensureProject();
        if (!pid) throw new Error('Enter a project name, then add the fabric photo.');
      }
      const stored = [...(fabricRef.current.swatch_files || [])];
      for (const file of files) {
        stored.push(await uploadOne(file, pid));
        rememberFiles(stored);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Upload failed';
      setUploadError(message);
    }
    setUploading(false);
    if (libraryRef.current) libraryRef.current.value = '';
    if (cameraRef.current) cameraRef.current.value = '';
  };

  return (
    <div className="rounded-[10px] border border-[#ece8e0] bg-[#faf9f7] p-3.5" style={{ marginTop: 8 }}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-[10px] font-bold text-[#b8960c] uppercase tracking-[0.5px]">
          {label || 'Fabric Information'} <span className="text-[#ccc] font-normal">(optional)</span>
        </span>
        {onRemove && (
          <button onClick={onRemove} type="button" className="text-[#d5d0c8] hover:text-[#dc2626] transition-colors cursor-pointer" style={{ background: 'none', border: 'none', padding: 0 }}>
            <X size={13} />
          </button>
        )}
      </div>

      {/* Preference radio buttons */}
      <div className="space-y-1.5 mb-3">
        <label className="block text-[11px] font-semibold text-[#666] mb-1">Do you have a specific fabric?</label>
        {PREFERENCES.map(p => (
          <label key={p.value} className="flex items-center gap-2 cursor-pointer" style={{ minHeight: 44 }}>
            <input
              type="radio"
              name={`fabric-pref-${fabric.scope}-${fabric.room_name}-${fabric.item_name}`}
              value={p.value}
              checked={fabric.fabric_preference === p.value}
              onChange={() => update('fabric_preference', p.value)}
              className="accent-[#b8960c]"
              style={{ width: 18, height: 18 }}
            />
            <span className="text-[12px] text-[#444]">{p.label}</span>
          </label>
        ))}
      </div>

      {/* Detail fields — only if picked_out or COM */}
      {hasDetails && (
        <div className="space-y-2.5 pt-2 border-t border-[#ece8e0]">
          <div>
            <label className="block text-[10px] font-semibold text-[#999] uppercase tracking-[0.3px] mb-1">Fabric Name / Brand</label>
            <input
              type="text"
              value={fabric.fabric_name || ''}
              onChange={e => update('fabric_name', e.target.value)}
              className="form-input"
              placeholder="e.g., Charlotte Fabrics Cuaderno"
            />
          </div>

          <div className="grid grid-cols-2 gap-2.5">
            <div>
              <label className="block text-[10px] font-semibold text-[#999] uppercase tracking-[0.3px] mb-1">Color / Pattern</label>
              <input
                type="text"
                value={fabric.color_pattern || ''}
                onChange={e => update('color_pattern', e.target.value)}
                className="form-input"
                placeholder="e.g., Spruce"
              />
            </div>
            <div>
              <label className="block text-[10px] font-semibold text-[#999] uppercase tracking-[0.3px] mb-1">Fabric Code</label>
              <input
                type="text"
                value={fabric.fabric_code || ''}
                onChange={e => update('fabric_code', e.target.value)}
                className="form-input"
                placeholder="e.g., V639"
              />
            </div>
          </div>

          {/* Supplier URL — the gold field */}
          <div>
            <label className="block text-[10px] font-semibold text-[#999] uppercase tracking-[0.3px] mb-1">
              <Link2 size={10} style={{ display: 'inline', marginRight: 3 }} />
              Paste fabric link here
            </label>
            <input
              type="url"
              value={fabric.supplier_url || ''}
              onChange={e => update('supplier_url', e.target.value)}
              className="form-input"
              placeholder="https://www.charlottefabrics.com/product/..."
              style={{ fontSize: 12 }}
            />
            <p className="text-[9px] text-[#bbb] mt-0.5">Paste the URL from the fabric supplier&apos;s website</p>
          </div>

          {/* Photo upload. Real file inputs stay in the form so iOS Safari
              opens the camera and the photo library. A script-built input
              does not. */}
          <div>
            <label className="block text-[10px] font-semibold text-[#999] uppercase tracking-[0.3px] mb-1">
              Upload a photo of your fabric
            </label>
            <div className="flex flex-col sm:flex-row items-stretch gap-2">
              <button
                type="button"
                onClick={() => cameraRef.current?.click()}
                disabled={uploading}
                className="flex items-center justify-center gap-2 cursor-pointer transition-colors"
                style={{
                  padding: '10px 16px', borderRadius: 8, border: '1px solid #ece8e0',
                  background: uploading ? '#f5f2ed' : '#fff', fontSize: 12, fontWeight: 600,
                  color: '#666', minHeight: 44,
                }}
              >
                <Camera size={16} />
                {uploading ? 'Uploading...' : 'Take Photo'}
              </button>
              <button
                type="button"
                onClick={() => libraryRef.current?.click()}
                disabled={uploading}
                className="flex items-center justify-center gap-2 cursor-pointer transition-colors"
                style={{
                  padding: '10px 16px', borderRadius: 8, border: '1px solid #ece8e0',
                  background: '#fff', fontSize: 12, fontWeight: 600,
                  color: '#666', minHeight: 44,
                }}
              >
                <Upload size={16} />
                Upload
              </button>
            </div>
            <input
              ref={cameraRef}
              type="file"
              accept="image/*,.heic,.heif,.jpg,.jpeg,.png"
              multiple
              onChange={e => handleFiles(e.target.files)}
              className="hidden"
            />
            <input
              ref={libraryRef}
              type="file"
              multiple
              onChange={e => handleFiles(e.target.files)}
              className="hidden"
            />
            {uploadError && (
              <p className="text-[11px] text-[#dc2626] mt-1.5">{uploadError}</p>
            )}
            {(fabric.swatch_files && fabric.swatch_files.length > 0) && (
              <div className="flex flex-wrap gap-2 mt-2">
                {fabric.swatch_files.map((file, index) => {
                  const name = file.original_name || file.path;
                  const image = isImageFile(name);
                  return (
                    <div key={`${file.path}-${index}`} className="flex items-center gap-1.5">
                      {image ? (
                        <img
                          src={fileUrl(file.path)}
                          alt={name}
                          style={{ width: 44, height: 44, objectFit: 'cover', borderRadius: 6, border: '1px solid #ece8e0' }}
                        />
                      ) : (
                        <a href={fileUrl(file.path)} target="_blank" rel="noopener noreferrer" className="text-[10px] font-semibold text-[#b8960c] max-w-[120px] truncate">
                          {name}
                        </a>
                      )}
                      <button
                        type="button"
                        onClick={() => rememberFiles((fabric.swatch_files || []).filter((_, i) => i !== index))}
                        className="text-[#ccc] hover:text-[#dc2626] cursor-pointer"
                        style={{ background: 'none', border: 'none', padding: 0 }}
                        aria-label="Remove file"
                      >
                        <X size={12} />
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* COM yards */}
          {isCom && (
            <div>
              <label className="block text-[10px] font-semibold text-[#999] uppercase tracking-[0.3px] mb-1">How many yards do you have?</label>
              <input
                type="number"
                value={fabric.yards_available || ''}
                onChange={e => update('yards_available', e.target.value ? parseFloat(e.target.value) : undefined)}
                className="form-input"
                placeholder="e.g., 12"
                step="0.5"
                min="0"
                style={{ maxWidth: 150 }}
              />
            </div>
          )}

          {/* Expandable additional details */}
          <button
            type="button"
            onClick={() => setShowDetails(!showDetails)}
            className="flex items-center gap-1 text-[11px] font-semibold text-[#b8960c] cursor-pointer mt-1"
            style={{ background: 'none', border: 'none', padding: 0 }}
          >
            {showDetails ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            {showDetails ? 'Hide' : 'Show'} additional details
          </button>

          {showDetails && (
            <div className="space-y-2.5 pt-2 border-t border-[#ece8e0]">
              <div className="grid grid-cols-3 gap-2.5">
                <div>
                  <label className="block text-[10px] font-semibold text-[#999] uppercase tracking-[0.3px] mb-1">Vertical Repeat</label>
                  <div className="flex items-center gap-1">
                    <input
                      type="number"
                      value={fabric.vertical_repeat || ''}
                      onChange={e => update('vertical_repeat', e.target.value ? parseFloat(e.target.value) : undefined)}
                      className="form-input"
                      placeholder="0"
                      step="0.25"
                      min="0"
                    />
                    <span className="text-[10px] text-[#aaa]">in</span>
                  </div>
                </div>
                <div>
                  <label className="block text-[10px] font-semibold text-[#999] uppercase tracking-[0.3px] mb-1">Horiz. Repeat</label>
                  <div className="flex items-center gap-1">
                    <input
                      type="number"
                      value={fabric.horizontal_repeat || ''}
                      onChange={e => update('horizontal_repeat', e.target.value ? parseFloat(e.target.value) : undefined)}
                      className="form-input"
                      placeholder="0"
                      step="0.25"
                      min="0"
                    />
                    <span className="text-[10px] text-[#aaa]">in</span>
                  </div>
                </div>
                <div>
                  <label className="block text-[10px] font-semibold text-[#999] uppercase tracking-[0.3px] mb-1">Fabric Width</label>
                  <div className="flex items-center gap-1">
                    <input
                      type="number"
                      value={fabric.fabric_width || ''}
                      onChange={e => update('fabric_width', e.target.value ? parseFloat(e.target.value) : undefined)}
                      className="form-input"
                      placeholder="54"
                      step="1"
                      min="0"
                    />
                    <span className="text-[10px] text-[#aaa]">in</span>
                  </div>
                </div>
              </div>
              <div>
                <label className="block text-[10px] font-semibold text-[#999] uppercase tracking-[0.3px] mb-1">Material Type</label>
                <select
                  value={fabric.material_type || ''}
                  onChange={e => update('material_type', e.target.value)}
                  className="form-input"
                >
                  <option value="">Select...</option>
                  {MATERIAL_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
            </div>
          )}

          {/* Notes */}
          <div>
            <label className="block text-[10px] font-semibold text-[#999] uppercase tracking-[0.3px] mb-1">Notes for the workroom</label>
            <textarea
              value={fabric.client_notes || ''}
              onChange={e => update('client_notes', e.target.value)}
              className="form-input resize-none"
              rows={2}
              placeholder="Anything else about this fabric — where you bought it, care instructions, matching requirements..."
              style={{ fontSize: 12 }}
            />
          </div>
        </div>
      )}
    </div>
  );
}
