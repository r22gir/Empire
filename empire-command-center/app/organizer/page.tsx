import { redirect } from 'next/navigation';

export default function OrganizerRedirect() {
  redirect('/?screen=calendar');
}
