import Link from 'next/link';

interface ServiceCardProps {
  icon: string;
  name: string;
  tagline: string;
  price: string;
  href: string;
}

export default function ServiceCard({ icon, name, tagline, price, href }: ServiceCardProps) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 flex flex-col hover:shadow-md transition-shadow">
      <div className="text-4xl mb-3">{icon}</div>
      <h3 className="text-lg font-heading font-bold text-gray-900 mb-1">{name}</h3>
      <p className="text-sm text-gray-600 flex-1 mb-3">{tagline}</p>
      <p className="text-primary-700 font-semibold text-sm mb-4">{price}</p>
      <Link
        href={href}
        className="mt-auto inline-block text-center bg-accent-500 text-white py-2 px-4 rounded-lg text-sm font-semibold hover:bg-orange-600 transition-colors"
      >
        Get Started
      </Link>
    </div>
  );
}
