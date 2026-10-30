import { headers } from 'next/headers';
import { notFound } from 'next/navigation';
import { isFabricsHost } from '../../lib/fabricsHost';
import AdminClient from './AdminClient';

export const metadata = {
  title: 'Fine Fabrics admin',
  robots: { index: false, follow: false },
};

export default async function FineFabricsAdminPage() {
  const host = (await headers()).get('host');
  if (isFabricsHost(host)) notFound();
  return <AdminClient />;
}
