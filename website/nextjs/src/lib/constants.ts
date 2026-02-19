export const COLORS = {
  primary: '#0066FF',
  primaryDark: '#0052CC',
  secondary: '#FF6600',
  secondaryDark: '#E55A00',
  dark: '#1A1A1A',
  light: '#F9F9F9',
};

export const PRICING_TIERS = [
  {
    id: 'free-trial',
    name: 'Free Trial',
    price: '$0',
    period: '7 Days',
    featured: false,
    features: [
      '10 listings',
      'All platforms',
      'Basic AI features',
      'Email support',
    ],
  },
  {
    id: 'pay-per-sale',
    name: 'Pay-Per-Sale',
    price: '3%',
    period: 'Per Sale',
    featured: false,
    features: [
      'Unlimited listings',
      'All platforms',
      'Full AI features',
      'Priority support',
      'No monthly fee',
    ],
  },
  {
    id: 'premium',
    name: 'Premium',
    price: '$9.99',
    period: 'Per Month',
    featured: true,
    features: [
      'Unlimited listings',
      'All platforms',
      'Full AI features',
      'Priority support',
      'No commission fees',
      'Advanced analytics',
    ],
  },
  {
    id: 'hybrid',
    name: 'Hybrid',
    price: '$5.99',
    period: '+ 1.5% Per Sale',
    featured: false,
    features: [
      'Unlimited listings',
      'All platforms',
      'Full AI features',
      'Priority support',
      'Best value for growing sellers',
    ],
  },
];

export const FAQ_DATA = [
  {
    question: 'Is there a setup fee?',
    answer:
      'No setup fee! Start with our 7-day free trial and only pay when you\'re ready. All plans include full platform access from day one.',
  },
  {
    question: 'How do I get paid?',
    answer:
      'Payment goes directly from the buyer to your connected payment processor (Stripe, PayPal, etc.). We never hold your money. Payouts are instant.',
  },
  {
    question: 'Can I cancel anytime?',
    answer:
      'Yes! Cancel anytime with one click. No contracts, no commitments. Your listings stay active until you remove them.',
  },
  {
    question: 'Which platforms are supported?',
    answer:
      'We support eBay, Poshmark, Facebook Marketplace, Mercari, Depop, and our own MarketF marketplace. More platforms coming soon!',
  },
  {
    question: 'Is my data safe?',
    answer:
      'Absolutely. We use bank-level encryption (AES-256) and never store your payment information. All data is backed up daily and GDPR compliant.',
  },
  {
    question: 'Is there a mobile app?',
    answer:
      'Yes! Our iOS and Android apps are available now. Take photos, list items, and manage your business from anywhere.',
  },
];

export const FEATURES = [
  {
    icon: '📸',
    title: 'MarketForge',
    subtitle: 'Photo → Price → Post in 30 seconds',
    features: [
      'AI-powered pricing',
      'Auto-description generation',
      'Multi-platform posting',
      'Instant crosslisting',
    ],
  },
  {
    icon: '🏪',
    title: 'MarketF Marketplace',
    subtitle: 'Your own marketplace with 8% fees',
    features: [
      'Built-in payment processing',
      'Custom branding',
      'No listing limits',
      'Analytics dashboard',
    ],
  },
  {
    icon: '🤖',
    title: 'AI Agents',
    subtitle: 'Work while you sleep, 24/7 automation',
    features: [
      'Auto-respond to messages',
      'Price optimization',
      'Inventory management',
      'Sales analytics',
    ],
  },
];

export const TESTIMONIALS = [
  {
    text: 'Went from 2 hours per listing to 30 seconds. Game changer for my business!',
    author: 'Sarah M.',
    role: 'Full-Time Reseller',
    rating: 5,
  },
  {
    text: 'The AI pricing is spot on. I\'m making 20% more per item now.',
    author: 'Mike T.',
    role: 'eBay Power Seller',
    rating: 5,
  },
  {
    text: 'Finally hit $10K/month thanks to the automation. Worth every penny!',
    author: 'Jessica L.',
    role: 'Poshmark Ambassador',
    rating: 5,
  },
  {
    text: 'Customer support is incredible. They helped me set up everything in minutes.',
    author: 'David R.',
    role: 'New Reseller',
    rating: 5,
  },
];

export const HOW_IT_WORKS_STEPS = [
  {
    number: 1,
    title: 'Upload Photo',
    description: 'Take a photo or upload from your device. Our AI analyzes the item instantly.',
  },
  {
    number: 2,
    title: 'Set Price',
    description: 'AI suggests optimal pricing based on market data. Edit as needed.',
  },
  {
    number: 3,
    title: 'Get Paid',
    description: 'Post to all platforms with one click. Track sales in real-time dashboard.',
  },
];

export const PRODUCTS = [
  {
    id: 'marketforge',
    name: 'MarketForge',
    tagline: 'Photo → Price → Post in 30 seconds',
    description: 'AI-powered listing tool that posts to eBay, Poshmark, Facebook Marketplace, and more in seconds.',
    price: 'From $9.99/mo',
    features: ['AI-powered pricing', 'Auto-description generation', 'Multi-platform posting', 'Instant crosslisting'],
    href: '/products/marketforge',
    icon: '📸',
  },
  {
    id: 'leadforge',
    name: 'LeadForge',
    tagline: 'Turn Leads into Customers Automatically',
    description: 'AI lead generation and nurturing system for resellers. Capture, score, and convert leads 24/7.',
    price: 'From $19.99/mo',
    features: ['AI lead scoring', 'Automated follow-ups', 'CRM integration', 'Conversion analytics'],
    href: '/products/leadforge',
    icon: '🎯',
  },
  {
    id: 'luxeforge',
    name: 'LuxeForge',
    tagline: 'Luxury Reselling, Simplified',
    description: 'Specialized platform for luxury goods resellers. Authentication, pricing, and marketplace listings for premium items.',
    price: 'From $29.99/mo',
    features: ['Luxury item authentication', 'Premium pricing engine', 'Exclusive marketplace listings', 'White-glove support'],
    href: '/products/luxeforge',
    icon: '💎',
  },
  {
    id: 'empire-token',
    name: 'EMPIRE Token',
    tagline: 'Earn, Stake, and Govern the EmpireBox Ecosystem',
    description: 'The native utility token powering the EMPIREBOX ecosystem. Earn rewards, pay fees, and participate in governance.',
    price: 'Free to earn',
    features: ['Earn through activity', 'Reduced platform fees', 'Governance voting', 'Exclusive member perks'],
    href: '/products/empire-token',
    icon: '🪙',
  },
  {
    id: 'empire-nft',
    name: 'EMPIRE License NFT',
    tagline: 'Your Digital Business License on the Blockchain',
    description: 'NFT-based software license that grants access to premium EmpireBox features and can be transferred or resold.',
    price: 'One-time purchase',
    features: ['Transferable license', 'Premium feature access', 'Revenue sharing', 'On-chain verification'],
    href: '/products/empire-nft',
    icon: '🏆',
  },
];

export const SERVICES = [
  {
    id: 'empire-assist',
    name: 'EmpireAssist AI',
    tagline: '24/7 AI Virtual Assistant for Resellers',
    description: 'Your personal AI business assistant handles customer messages, pricing questions, and order management around the clock.',
    price: 'From $19.99/mo',
    features: ['24/7 message responses', 'Order management', 'Price negotiation AI', 'Multi-platform inbox'],
    href: '/services/empire-assist',
    icon: '🤖',
  },
  {
    id: 'va-telehealth',
    name: 'VA App Telehealth',
    tagline: 'Healthcare Navigation for Veterans & Entrepreneurs',
    description: 'Telehealth and benefits navigation service designed for veteran resellers and entrepreneurs.',
    price: 'From $9.99/mo',
    features: ['Telehealth consultations', 'VA benefits navigation', 'Mental wellness support', 'Business health coaching'],
    href: '/services/va-telehealth',
    icon: '🏥',
  },
  {
    id: 'zero-to-hero',
    name: 'Zero to Hero Program',
    tagline: 'Launch Your Reselling Business from Scratch',
    description: 'Complete mentorship and training program to take you from zero experience to a full-time reselling income.',
    price: 'From $299 one-time',
    features: ['Step-by-step curriculum', 'Live coaching calls', 'Private community access', '90-day money-back guarantee'],
    href: '/services/zero-to-hero',
    icon: '🚀',
  },
];
