import { redirect } from 'next/navigation';

export default function AmpLoginRedirect() {
  redirect('/login');
}
