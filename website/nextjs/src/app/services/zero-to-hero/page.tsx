import { Metadata } from 'next';
import ProductPageLayout from '@/components/ProductPageLayout';

export const metadata: Metadata = {
  title: 'Zero to Hero Program - EmpireBox',
  description: 'Complete mentorship program to launch your reselling business from scratch to full-time income.',
};

export default function ZeroToHeroPage() {
  return (
    <ProductPageLayout
      icon="🚀"
      name="Zero to Hero Program"
      tagline="Launch Your Reselling Business from Scratch"
      description="Complete mentorship and training program to take you from zero experience to a full-time reselling income. Includes live coaching, community access, and proven step-by-step curriculum."
      features={[
        'Step-by-step reselling curriculum (12 modules)',
        'Weekly live coaching calls',
        'Private community of 1,000+ resellers',
        'Sourcing guide and supplier access',
        'Pricing and profit strategies',
        'Marketplace-specific tactics (eBay, Poshmark, etc.)',
        'Tax and business setup guidance',
        '90-day money-back guarantee',
      ]}
      pricingTiers={[
        {
          name: 'Self-Paced',
          price: '$299',
          period: 'one-time',
          features: ['Full curriculum access', 'Community access', 'Sourcing guide', 'Email support', '90-day money-back guarantee'],
        },
        {
          name: 'Mentorship',
          price: '$599',
          period: 'one-time',
          featured: true,
          features: ['Everything in Self-Paced', 'Weekly live coaching calls', '1-on-1 strategy session', 'Direct mentor access', 'Lifetime updates', '90-day money-back guarantee'],
        },
      ]}
      ctaText="Enroll Now"
    />
  );
}
