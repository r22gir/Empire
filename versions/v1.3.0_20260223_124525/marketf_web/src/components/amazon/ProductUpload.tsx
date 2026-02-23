'use client';

import { useState } from 'react';

interface ProductFormData {
  gtin: string;
  title: string;
  bulletPoints: string[];
  description: string;
  price: string;
  inventory: string;
  weight: string;
  length: string;
  width: string;
  height: string;
  categoryId: string;
  brandName: string;
  brandAuthorized: boolean;
  manufacturer: string;
  imageUrls: string[];
}

interface FieldError {
  [field: string]: string[];
}

interface ProductUploadProps {
  storeId: string;
  onSuccess?: (sku: string) => void;
}

const EMPTY_FORM: ProductFormData = {
  gtin: '',
  title: '',
  bulletPoints: ['', '', '', '', ''],
  description: '',
  price: '',
  inventory: '',
  weight: '',
  length: '',
  width: '',
  height: '',
  categoryId: '',
  brandName: '',
  brandAuthorized: false,
  manufacturer: '',
  imageUrls: ['', '', '', '', '', '', ''],
};

export default function ProductUpload({ storeId, onSuccess }: ProductUploadProps) {
  const [form, setForm] = useState<ProductFormData>(EMPTY_FORM);
  const [errors, setErrors] = useState<FieldError>({});
  const [warnings, setWarnings] = useState<FieldError>({});
  const [submitting, setSubmitting] = useState(false);
  const [successSku, setSuccessSku] = useState<string | null>(null);

  function setField<K extends keyof ProductFormData>(key: K, value: ProductFormData[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
    // Clear field error on change
    if (errors[key]) {
      setErrors((prev) => {
        const next = { ...prev };
        delete next[key as string];
        return next;
      });
    }
  }

  function setBulletPoint(index: number, value: string) {
    const updated = [...form.bulletPoints];
    updated[index] = value;
    setField('bulletPoints', updated);
  }

  function setImageUrl(index: number, value: string) {
    const updated = [...form.imageUrls];
    updated[index] = value;
    setField('imageUrls', updated);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setErrors({});
    setWarnings({});

    try {
      const res = await fetch('/api/amazon/listings/validate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ storeId, product: form }),
      });

      const data = await res.json();

      if (!res.ok || !data.isValid) {
        setErrors(data.errors ?? {});
        setWarnings(data.warnings ?? {});
        return;
      }

      setWarnings(data.warnings ?? {});

      // Submit validated product
      const submitRes = await fetch('/api/amazon/listings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ storeId, product: form }),
      });

      if (!submitRes.ok) {
        const submitData = await submitRes.json();
        setErrors({ submit: [submitData.message ?? 'Submission failed'] });
        return;
      }

      const submitData = await submitRes.json();
      setSuccessSku(submitData.sku);
      setForm(EMPTY_FORM);
      onSuccess?.(submitData.sku);
    } catch {
      setErrors({ submit: ['An unexpected error occurred. Please try again.'] });
    } finally {
      setSubmitting(false);
    }
  }

  if (successSku) {
    return (
      <div className="rounded-lg bg-green-50 border border-green-200 p-6 text-center space-y-2">
        <p className="text-green-700 font-semibold">Product submitted successfully!</p>
        <p className="text-sm text-green-600">SKU: {successSku}</p>
        <button
          onClick={() => setSuccessSku(null)}
          className="mt-2 text-sm text-green-700 underline"
        >
          Upload another product
        </button>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {errors.submit && (
        <div className="rounded-lg bg-red-50 border border-red-200 p-4 text-sm text-red-700">
          {errors.submit.join(' ')}
        </div>
      )}

      {/* Identifiers */}
      <Section title="Product Identifiers">
        <Field label="GTIN / UPC / EAN *" error={errors.gtin}>
          <input
            type="text"
            value={form.gtin}
            onChange={(e) => setField('gtin', e.target.value)}
            placeholder="e.g. 012345678905"
            className={inputClass(!!errors.gtin)}
          />
        </Field>
      </Section>

      {/* Listing content */}
      <Section title="Listing Content">
        <Field label="Title * (≤200 chars)" error={errors.title} warning={warnings.title}>
          <input
            type="text"
            value={form.title}
            onChange={(e) => setField('title', e.target.value)}
            maxLength={200}
            placeholder="e.g. Wireless Bluetooth Headphones - Noise Cancelling, 20hr Battery"
            className={inputClass(!!errors.title)}
          />
          <CharCounter current={form.title.length} max={200} />
        </Field>

        <Field label="Bullet Points (up to 5, each ≤300 chars)" error={errors.bullet_points}>
          {form.bulletPoints.map((point, i) => (
            <div key={i} className="mb-2">
              <input
                type="text"
                value={point}
                onChange={(e) => setBulletPoint(i, e.target.value)}
                maxLength={300}
                placeholder={`Bullet point ${i + 1}`}
                className={inputClass(false)}
              />
            </div>
          ))}
        </Field>

        <Field label="Description (≤1,000 chars)" error={errors.description} warning={warnings.description}>
          <textarea
            value={form.description}
            onChange={(e) => setField('description', e.target.value)}
            maxLength={1000}
            rows={4}
            placeholder="Product description (HTML allowed)"
            className={inputClass(!!errors.description)}
          />
          <CharCounter current={form.description.length} max={1000} />
        </Field>
      </Section>

      {/* Images */}
      <Section title="Images (7+ required)">
        <p className="text-xs text-gray-500 mb-3">
          Main image must have a pure white background (RGB 255,255,255), ≥1,000px longest side,
          no watermarks or text. Enter publicly accessible image URLs.
        </p>
        {errors.images && <ErrorList messages={errors.images} />}
        {warnings.images && <WarningList messages={warnings.images} />}
        {form.imageUrls.map((url, i) => (
          <div key={i} className="mb-2">
            <input
              type="url"
              value={url}
              onChange={(e) => setImageUrl(i, e.target.value)}
              placeholder={i === 0 ? 'Main image URL (white background)' : `Additional image ${i + 1} URL`}
              className={inputClass(false)}
            />
          </div>
        ))}
      </Section>

      {/* Pricing & Inventory */}
      <Section title="Pricing & Inventory">
        <div className="grid grid-cols-2 gap-4">
          <Field label="Price (USD) *" error={errors.price}>
            <input
              type="number"
              step="0.01"
              min="0.01"
              value={form.price}
              onChange={(e) => setField('price', e.target.value)}
              placeholder="e.g. 29.99"
              className={inputClass(!!errors.price)}
            />
          </Field>
          <Field label="Inventory Qty *" error={errors.inventory}>
            <input
              type="number"
              min="0"
              value={form.inventory}
              onChange={(e) => setField('inventory', e.target.value)}
              placeholder="e.g. 50"
              className={inputClass(!!errors.inventory)}
            />
          </Field>
        </div>
      </Section>

      {/* Shipping dimensions */}
      <Section title="Shipping Weight & Dimensions">
        <p className="text-xs text-gray-500 mb-3">Required for FBA calculations.</p>
        {errors.dimensions && <ErrorList messages={errors.dimensions} />}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Field label="Weight (lbs) *">
            <input
              type="number"
              step="0.01"
              min="0"
              value={form.weight}
              onChange={(e) => setField('weight', e.target.value)}
              placeholder="0.00"
              className={inputClass(false)}
            />
          </Field>
          <Field label="Length (in) *">
            <input
              type="number"
              step="0.01"
              min="0"
              value={form.length}
              onChange={(e) => setField('length', e.target.value)}
              placeholder="0.00"
              className={inputClass(false)}
            />
          </Field>
          <Field label="Width (in) *">
            <input
              type="number"
              step="0.01"
              min="0"
              value={form.width}
              onChange={(e) => setField('width', e.target.value)}
              placeholder="0.00"
              className={inputClass(false)}
            />
          </Field>
          <Field label="Height (in) *">
            <input
              type="number"
              step="0.01"
              min="0"
              value={form.height}
              onChange={(e) => setField('height', e.target.value)}
              placeholder="0.00"
              className={inputClass(false)}
            />
          </Field>
        </div>
      </Section>

      {/* Categorization & Brand */}
      <Section title="Categorization & Brand">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Field label="Amazon Category ID *" error={errors.category}>
            <input
              type="text"
              value={form.categoryId}
              onChange={(e) => setField('categoryId', e.target.value)}
              placeholder="e.g. 172282"
              className={inputClass(!!errors.category)}
            />
          </Field>
          <Field label="Brand Name *" error={errors.brand}>
            <input
              type="text"
              value={form.brandName}
              onChange={(e) => setField('brandName', e.target.value)}
              placeholder="e.g. Acme Corp or Generic"
              className={inputClass(!!errors.brand)}
            />
          </Field>
          <Field label="Manufacturer *" error={errors.manufacturer}>
            <input
              type="text"
              value={form.manufacturer}
              onChange={(e) => setField('manufacturer', e.target.value)}
              placeholder="e.g. Acme Manufacturing Co."
              className={inputClass(!!errors.manufacturer)}
            />
          </Field>
          <Field label="Brand Authorization">
            <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
              <input
                type="checkbox"
                checked={form.brandAuthorized}
                onChange={(e) => setField('brandAuthorized', e.target.checked)}
                className="rounded border-gray-300"
              />
              I have authorization to sell under this brand name
            </label>
          </Field>
        </div>
      </Section>

      <button
        type="submit"
        disabled={submitting}
        className="w-full py-3 px-6 rounded-lg bg-orange-500 text-white font-semibold hover:bg-orange-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {submitting ? 'Validating & Submitting…' : 'Submit Product for Amazon Listing'}
      </button>
    </form>
  );
}

// -----------------------------------------------------------------------
// Small helper components
// -----------------------------------------------------------------------

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide border-b pb-2">
        {title}
      </h3>
      {children}
    </div>
  );
}

function Field({
  label,
  children,
  error,
  warning,
}: {
  label: string;
  children: React.ReactNode;
  error?: string[];
  warning?: string[];
}) {
  return (
    <div className="space-y-1">
      <label className="block text-sm font-medium text-gray-700">{label}</label>
      {children}
      {error && <ErrorList messages={error} />}
      {warning && <WarningList messages={warning} />}
    </div>
  );
}

function ErrorList({ messages }: { messages: string[] }) {
  return (
    <ul className="space-y-0.5">
      {messages.map((msg, i) => (
        <li key={i} className="text-xs text-red-600">
          {msg}
        </li>
      ))}
    </ul>
  );
}

function WarningList({ messages }: { messages: string[] }) {
  return (
    <ul className="space-y-0.5">
      {messages.map((msg, i) => (
        <li key={i} className="text-xs text-yellow-600">
          ⚠ {msg}
        </li>
      ))}
    </ul>
  );
}

function CharCounter({ current, max }: { current: number; max: number }) {
  const over = current > max;
  return (
    <p className={`text-xs text-right mt-0.5 ${over ? 'text-red-600' : 'text-gray-400'}`}>
      {current}/{max}
    </p>
  );
}

function inputClass(hasError: boolean): string {
  return `w-full rounded-lg border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-orange-400 ${
    hasError ? 'border-red-400 bg-red-50' : 'border-gray-300 bg-white'
  }`;
}
