'use client';

import { motion } from 'framer-motion';
import { FEATURES } from '@/lib/constants';

export default function Features() {
  return (
    <section id="features" className="py-20">
      <div className="container mx-auto px-4">
        <h2 className="text-center mb-12">Why Resellers Choose EmpireBox</h2>
        <div className="grid md:grid-cols-3 gap-8">
          {FEATURES.map((feature, index) => (
            <motion.div
              key={feature.title}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6, delay: index * 0.1 }}
              className="bg-white p-8 rounded-xl shadow-lg hover:shadow-2xl transition-all hover:-translate-y-2"
            >
              <div className="text-5xl mb-4">{feature.icon}</div>
              <h3 className="text-primary mb-2">{feature.title}</h3>
              <p className="text-gray-600 mb-4">{feature.subtitle}</p>
              <ul className="space-y-2">
                {feature.features.map((item) => (
                  <li key={item} className="flex items-start">
                    <span className="text-primary font-bold mr-2">✓</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
