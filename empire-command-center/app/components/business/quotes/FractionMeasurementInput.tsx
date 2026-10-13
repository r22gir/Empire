'use client';

import { formatFractionInches, parseFractionInches } from '../../../lib/measurements';

interface FractionMeasurementInputProps {
  label: string;
  value: string | number;
  onChange: (next: string) => void;
  placeholder?: string;
}

export default function FractionMeasurementInput({
  label,
  value,
  onChange,
  placeholder = '36 1/2',
}: FractionMeasurementInputProps) {
  const inches = parseFractionInches(value);
  const pretty = value ? formatFractionInches(value) : '';

  return (
    <label style={{ display: 'block' }}>
      <span style={{ fontSize: 11, fontWeight: 700, color: '#777' }}>{label}</span>
      <input
        value={value ?? ''}
        onChange={(e) => onChange(e.target.value)}
        onBlur={() => {
          if (value !== '' && value !== undefined) onChange(formatFractionInches(value));
        }}
        placeholder={placeholder}
        inputMode="text"
        style={{ width: '100%', padding: '10px 12px', borderRadius: 10, border: '1px solid #ece8e0', fontSize: 14, marginTop: 4, background: '#faf9f7', minHeight: 44 }}
      />
      {inches > 0 && (
        <span style={{ fontSize: 10, color: '#b8960c', fontWeight: 600 }}>{pretty}&quot;</span>
      )}
    </label>
  );
}
