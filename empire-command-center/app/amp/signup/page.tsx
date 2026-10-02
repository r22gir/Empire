import { redirect } from 'next/navigation';

export default function AmpSignupRedirect() {
  redirect('/login');
}
