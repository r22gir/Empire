import { Mail, Clock, CheckCircle } from 'lucide-react'

export default function ContactPage() {
  const teamSizes = ['Just me', '2–5 people', '6–15 people', '16+ people']

  return (
    <>
      {/* Hero */}
      <section className="bg-[#2C2C2C] text-white py-20 px-4 text-center">
        <div className="max-w-3xl mx-auto">
          <h1 className="text-5xl font-bold mb-4">
            Schedule Your <span className="text-[#C9A84C]">Demo</span>
          </h1>
          <p className="text-gray-300 text-lg">
            See LuxeForge live with your own workroom use cases. No sales pressure, just a real look at the software.
          </p>
        </div>
      </section>

      {/* Form + Sidebar */}
      <section className="py-20 px-4 bg-white">
        <div className="max-w-6xl mx-auto grid md:grid-cols-3 gap-12">
          {/* Form */}
          <div className="md:col-span-2">
            <h2 className="text-2xl font-bold text-[#2C2C2C] mb-6">Request a Demo</h2>
            <form className="space-y-5">
              <div className="grid sm:grid-cols-2 gap-5">
                <div>
                  <label className="block text-sm font-medium text-[#2C2C2C] mb-1">First Name</label>
                  <input
                    type="text"
                    className="w-full border border-gray-300 rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-[#C9A84C] focus:border-transparent"
                    placeholder="Jane"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#2C2C2C] mb-1">Last Name</label>
                  <input
                    type="text"
                    className="w-full border border-gray-300 rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-[#C9A84C] focus:border-transparent"
                    placeholder="Smith"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-[#2C2C2C] mb-1">Business Email</label>
                <input
                  type="email"
                  className="w-full border border-gray-300 rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-[#C9A84C] focus:border-transparent"
                  placeholder="jane@myworkroom.com"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-[#2C2C2C] mb-1">Business Name</label>
                <input
                  type="text"
                  className="w-full border border-gray-300 rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-[#C9A84C] focus:border-transparent"
                  placeholder="Smith Custom Workroom"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-[#2C2C2C] mb-1">Team Size</label>
                <select
                  className="w-full border border-gray-300 rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-[#C9A84C] focus:border-transparent bg-white"
                >
                  <option value="">Select team size...</option>
                  {teamSizes.map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-[#2C2C2C] mb-1">
                  Phone <span className="text-gray-400 font-normal">(optional)</span>
                </label>
                <input
                  type="tel"
                  className="w-full border border-gray-300 rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-[#C9A84C] focus:border-transparent"
                  placeholder="(555) 000-0000"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-[#2C2C2C] mb-1">What would you like to see?</label>
                <textarea
                  rows={4}
                  className="w-full border border-gray-300 rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-[#C9A84C] focus:border-transparent resize-none"
                  placeholder="Tell us about your workroom and what challenges you're looking to solve..."
                />
              </div>
              <button
                type="submit"
                className="w-full bg-[#C9A84C] hover:bg-[#A07A2E] text-[#2C2C2C] font-bold py-4 rounded-lg text-lg transition"
              >
                Request My Demo
              </button>
              <p className="text-xs text-gray-400 text-center">
                We respect your privacy. No spam — just one reply to schedule your demo.
              </p>
            </form>
          </div>

          {/* Sidebar */}
          <div className="space-y-8">
            <div className="bg-gray-50 rounded-xl p-6">
              <h3 className="font-bold text-[#2C2C2C] mb-4 text-lg">What happens next?</h3>
              <ul className="space-y-3 text-sm text-gray-600">
                {[
                  "We'll reply within 1 business day to confirm your demo time",
                  'A 20-minute Zoom call with a workroom specialist',
                  'Live walkthrough tailored to your business',
                  'Q&A — ask anything, no pressure',
                ].map((step, i) => (
                  <li key={i} className="flex items-start gap-3">
                    <CheckCircle size={16} className="text-[#C9A84C] flex-shrink-0 mt-0.5" />
                    {step}
                  </li>
                ))}
              </ul>
            </div>

            <div className="bg-gray-50 rounded-xl p-6">
              <h3 className="font-bold text-[#2C2C2C] mb-4 text-lg">Contact Info</h3>
              <ul className="space-y-3 text-sm text-gray-600">
                <li className="flex items-center gap-3">
                  <Mail size={16} className="text-[#C9A84C]" />
                  <a href="mailto:hello@luxeforge.app" className="hover:text-[#C9A84C] transition">hello@luxeforge.app</a>
                </li>
                <li className="flex items-center gap-3">
                  <Clock size={16} className="text-[#C9A84C]" />
                  <span>Mon–Fri, 9am–6pm EST</span>
                </li>
              </ul>
            </div>

            <div className="border-l-4 border-[#C9A84C] pl-4">
              <p className="text-sm text-gray-600 italic">
                &ldquo;LuxeForge cut our quoting time from 2 hours to 15 minutes. Our clients are impressed, and we book more projects because we respond faster.&rdquo;
              </p>
              <p className="text-xs text-gray-500 mt-2">— Workroom owner, Nashville TN</p>
            </div>
          </div>
        </div>
      </section>
    </>
  )
}
