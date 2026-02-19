import { Metadata } from 'next';
import ProductPageLayout from '@/components/ProductPageLayout';

export const metadata: Metadata = {
  title: 'LeadForge - EmpireBox',
  description: 'AI lead generation and nurturing for resellers. Turn leads into customers automatically.',
};

export default function LeadForgePage() {
  return (
    <ProductPageLayout
      icon="🎯"
      name="LeadForge"
      tagline="Turn Leads into Customers Automatically"
      description="AI-powered lead generation and nurturing system built for resellers. Capture, score, and convert leads 24/7 without lifting a finger."
      features={[
        'AI lead capture from social media',
        'Automated lead scoring and prioritization',
        'Personalized follow-up sequences',
        'CRM integration',
        'Conversion rate analytics',
        'Multi-channel outreach (email, SMS, social)',
        'Lead database management',
        'A/B testing for campaigns',
      ]}
      pricingTiers={[
        {
          name: 'Starter',
          price: '$19.99',
          period: 'month',
          features: ['Up to 500 leads/month', 'Basic AI scoring', 'Email follow-ups', 'Email support'],
        },
        {
          name: 'Professional',
          price: '$49.99',
          period: 'month',
          featured: true,
          features: ['Unlimited leads', 'Advanced AI scoring', 'Email + SMS follow-ups', 'CRM integration', 'Priority support', 'A/B testing'],
        },
      ]}
    />
  );
}
