'use client';

import { useState, FormEvent } from 'react';

export default function EmailForm() {
  const [email, setEmail] = useState('');
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (email) {
      // In a real app, send to your backend/email service
      console.log('Email submitted:', email);
      setSubmitted(true);
      setEmail('');
      setTimeout(() => setSubmitted(false), 3000);
    }
  };

  return (
    <div className="max-w-md mx-auto">
      {submitted ? (
        <div className="bg-white text-primary py-4 px-6 rounded-full font-semibold">
          Thanks! Check your email for next steps.
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-4">
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Enter your email"
            required
            className="flex-1 px-6 py-4 rounded-full text-dark focus:outline-none focus:ring-2 focus:ring-secondary"
          />
          <button
            type="submit"
            className="bg-secondary hover:bg-secondary-dark px-8 py-4 rounded-full font-semibold transition-colors whitespace-nowrap"
          >
            Get Started
          </button>
        </form>
      )}
    </div>
  );
}
