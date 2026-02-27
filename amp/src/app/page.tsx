"use client";

import { useScrollReveal } from "@/hooks/useScrollReveal";
import Navbar from "@/components/Navbar";
import Hero from "@/components/Hero";
import SocialProof from "@/components/SocialProof";
import Pillars from "@/components/Pillars";
import Features from "@/components/Features";
import HowItWorks from "@/components/HowItWorks";
import Pricing from "@/components/Pricing";
import Testimonials from "@/components/Testimonials";
import Maxwell from "@/components/Maxwell";
import EmailCapture from "@/components/EmailCapture";
import Footer from "@/components/Footer";

export default function Home() {
  useScrollReveal();

  return (
    <main>
      <Navbar />
      <Hero />
      <SocialProof />
      <Pillars />
      <Features />
      <HowItWorks />
      <Pricing />
      <Testimonials />
      <Maxwell />
      <EmailCapture />
      <Footer />
    </main>
  );
}
