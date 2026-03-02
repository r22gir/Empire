'use client';

import { motion } from 'framer-motion';
import EmailForm from './EmailForm';

export default function CTA() {
  return (
    <section id="contact" className="gradient-primary text-white py-20">
      <div className="container mx-auto px-4 text-center">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
        >
          <h2 className="mb-4">Ready to Stop Wasting Time?</h2>
          <p className="text-xl mb-8 opacity-95">
            Join 50+ resellers already making more money with less work.
          </p>
          <EmailForm />
          <p className="mt-4 text-sm opacity-90">
            No credit card required • 7-day free trial
          </p>
        </motion.div>
      </div>
    </section>
  );
}
