'use client';

import { motion } from 'framer-motion';
import { TESTIMONIALS } from '@/lib/constants';

export default function Testimonials() {
  return (
    <section className="py-20 bg-light">
      <div className="container mx-auto px-4">
        <h2 className="text-center mb-12">What Resellers Are Saying</h2>
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
          {TESTIMONIALS.map((testimonial, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6, delay: index * 0.1 }}
              className="bg-white p-6 rounded-xl border-l-4 border-primary"
            >
              <div className="text-secondary text-xl mb-3">
                {'★'.repeat(testimonial.rating)}
              </div>
              <p className="italic text-gray-700 mb-4">
                &ldquo;{testimonial.text}&rdquo;
              </p>
              <p className="font-semibold text-primary">
                — {testimonial.author}
              </p>
              <p className="text-sm text-gray-600">{testimonial.role}</p>
            </motion.div>
          ))}
        </div>
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="gradient-primary text-white text-center p-8 rounded-xl font-semibold text-lg md:text-xl"
        >
          95% Retention Rate | 72 NPS Score | $3.5K Average Monthly Revenue
        </motion.div>
      </div>
    </section>
  );
}
