'use client';

import { motion } from 'framer-motion';
import { PRICING_TIERS } from '@/lib/constants';
import Link from 'next/link';

export default function Pricing() {
  return (
    <section id="pricing" className="py-20">
      <div className="container mx-auto px-4">
        <h2 className="text-center mb-12">Simple, Transparent Pricing</h2>
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
          {PRICING_TIERS.map((tier, index) => (
            <motion.div
              key={tier.id}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6, delay: index * 0.1 }}
              className={`bg-white p-8 rounded-xl shadow-lg text-center transition-all hover:-translate-y-2 ${
                tier.featured
                  ? 'border-4 border-secondary scale-105 hover:scale-110'
                  : 'hover:scale-105'
              }`}
            >
              <h3 className="mb-4">{tier.name}</h3>
              <div className="text-4xl font-bold text-primary mb-2">
                {tier.price}
              </div>
              <p className="text-gray-600 mb-6">{tier.period}</p>
              <ul className="space-y-3 mb-8 text-left">
                {tier.features.map((feature) => (
                  <li key={feature} className="flex items-start">
                    <span className="text-primary font-bold mr-2">✓</span>
                    <span className="text-sm">{feature}</span>
                  </li>
                ))}
              </ul>
              <Link
                href="#contact"
                className={`block w-full py-3 rounded-full font-semibold transition-colors ${
                  tier.featured
                    ? 'bg-secondary hover:bg-secondary-dark text-white'
                    : 'bg-primary hover:bg-primary-dark text-white'
                }`}
              >
                {tier.featured ? 'Most Popular' : 'Get Started'}
              </Link>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
