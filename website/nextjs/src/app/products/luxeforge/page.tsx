import { Metadata } from 'next';
import ProductPageLayout from '@/components/ProductPageLayout';

export const metadata: Metadata = {
  title: 'LuxeForge - EmpireBox',
  description: 'Luxury goods reselling platform with authentication and premium marketplace listings.',
};

export default function LuxeForgePage() {
  return (
    <ProductPageLayout
      icon="💎"
      name="LuxeForge"
      tagline="Luxury Reselling, Simplified"
      description="Specialized platform for luxury goods resellers. Authenticate, price, and list premium items on exclusive marketplaces with confidence."
      features={[
        'Luxury item authentication tools',
        'Premium pricing engine with comps',
        'Exclusive luxury marketplace listings',
        'High-resolution photo tools',
        'Certificate of authenticity tracking',
        'White-glove customer support',
        'Consignment management',
        'Insurance integration options',
      ]}
      pricingTiers={[
        {
          name: 'LuxeForge',
          price: '$29.99',
          period: 'month',
          featured: true,
          features: ['Unlimited luxury listings', 'Authentication tools', 'Premium marketplace access', 'White-glove support', 'Analytics dashboard', '7-day free trial'],
        },
      ]}
    />
  );
}
