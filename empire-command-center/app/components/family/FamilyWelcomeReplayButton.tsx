'use client';

import type { CSSProperties, ReactNode } from 'react';
import { WELCOME_HELP_LABEL, requestFamilyWelcomeReplay } from '../../lib/familyWelcome';

type Props = {
  className?: string;
  style?: CSSProperties;
  children?: ReactNode;
};

export default function FamilyWelcomeReplayButton({ className, style, children }: Props) {
  return (
    <button
      type="button"
      className={className}
      data-testid="family-welcome-replay"
      onClick={requestFamilyWelcomeReplay}
      style={{
        background: 'none',
        border: 'none',
        padding: 0,
        font: 'inherit',
        color: 'inherit',
        cursor: 'pointer',
        textAlign: 'left',
        ...style,
      }}
    >
      {children || WELCOME_HELP_LABEL}
    </button>
  );
}
