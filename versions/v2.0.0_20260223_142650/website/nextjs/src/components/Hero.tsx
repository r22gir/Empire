'use client';

import { motion } from 'framer-motion';
import Link from 'next/link';

export default function Hero() {
  return (
    <section className="gradient-primary text-white py-20 md:py-32">
      <div className="container mx-auto px-4 text-center">
        <motion.h1
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          className="mb-6"
        >
          The Operating System for Resellers
        </motion.h1>
        <motion.p
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.2 }}
          className="text-xl md:text-2xl mb-8 opacity-95"
        >
          From side hustle to $10K/month business in 6 months. Post to eBay,
          Poshmark, and Facebook in 30 seconds.
        </motion.p>
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.4 }}
        >
          <Link
            href="#contact"
            className="inline-block bg-secondary hover:bg-secondary-dark text-white font-semibold px-10 py-4 rounded-full text-lg transition-all hover:-translate-y-1 hover:shadow-xl"
          >
            Try Free for 7 Days
          </Link>
        </motion.div>
      </div>
    </section>
  );
}
