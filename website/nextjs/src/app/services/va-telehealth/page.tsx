import { Metadata } from 'next';
import ProductPageLayout from '@/components/ProductPageLayout';

export const metadata: Metadata = {
  title: 'VA App Telehealth - EmpireBox',
  description: 'Telehealth and benefits navigation for veteran resellers and entrepreneurs.',
};

export default function VATelehealthPage() {
  return (
    <ProductPageLayout
      icon="🏥"
      name="VA App Telehealth"
      tagline="Healthcare Navigation for Veterans & Entrepreneurs"
      description="Telehealth and VA benefits navigation service designed specifically for veteran resellers and entrepreneurs. Access quality healthcare while building your business."
      features={[
        'Virtual telehealth consultations',
        'VA benefits navigation assistance',
        'Mental wellness and stress management',
        'Business health and wellness coaching',
        'Prescription management support',
        'Specialist referral network',
        'HIPAA-compliant platform',
        'Priority scheduling for veterans',
      ]}
      pricingTiers={[
        {
          name: 'Basic',
          price: '$9.99',
          period: 'month',
          features: ['2 telehealth visits/month', 'Benefits navigation', 'Wellness resources', 'Email support'],
        },
        {
          name: 'Premium',
          price: '$24.99',
          period: 'month',
          featured: true,
          features: ['Unlimited telehealth visits', 'VA benefits navigation', 'Business health coaching', 'Mental wellness support', 'Priority scheduling', '24/7 nurse line'],
        },
      ]}
      ctaText="Get Started"
    />
  );
}
