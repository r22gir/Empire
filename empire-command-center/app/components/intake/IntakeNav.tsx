'use client';
import { IntakeAuthedHeader } from './IntakeChrome';

export default function IntakeNav({ user }: { user?: { name: string; company?: string } | null }) {
  return <IntakeAuthedHeader user={user} />;
}
