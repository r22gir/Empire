import { Metadata } from 'next';
import ProductPageLayout from '@/components/ProductPageLayout';

export const metadata: Metadata = {
  title: 'EmpireAssist AI - EmpireBox',
  description: '24/7 AI Virtual Assistant for resellers. Auto-respond to messages and manage orders.',
};

export default function EmpireAssistPage() {
  return (
    <ProductPageLayout
      icon="🤖"
      name="EmpireAssist AI"
      tagline="24/7 AI Virtual Assistant for Resellers"
      description="Your personal AI business assistant handles customer messages, pricing questions, and order management around the clock — so you can focus on sourcing and scaling."
      features={[
        '24/7 automated message responses',
        'AI-powered price negotiation',
        'Order management and tracking',
        'Multi-platform unified inbox',
        'Custom response templates',
        'Escalation to human support',
        'Sales analytics and insights',
        'Integration with all major marketplaces',
      ]}
      pricingTiers={[
        {
          name: 'Basic',
          price: '$19.99',
          period: 'month',
          features: ['500 AI responses/month', '2 marketplace integrations', 'Basic templates', 'Email support'],
        },
        {
          name: 'Professional',
          price: '$39.99',
          period: 'month',
          featured: true,
          features: ['Unlimited AI responses', 'All marketplace integrations', 'Custom templates', 'Price negotiation AI', 'Priority support', 'Analytics dashboard'],
        },
      ]}
      ctaText="Start Free Trial"
    />
  );
}
