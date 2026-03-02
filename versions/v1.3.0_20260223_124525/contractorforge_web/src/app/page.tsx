import Link from 'next/link'

export default function HomePage() {
  return (
    <main className="min-h-screen">
      {/* Hero Section */}
      <section className="relative bg-gradient-to-br from-blue-50 to-indigo-100 py-20 px-4">
        <div className="max-w-6xl mx-auto text-center">
          <h1 className="text-5xl md:text-6xl font-bold text-gray-900 mb-6">
            ContractorForge
          </h1>
          <p className="text-xl md:text-2xl text-gray-700 mb-4">
            Universal AI-Powered Platform for Service Businesses
          </p>
          <p className="text-lg text-gray-600 mb-8 max-w-3xl mx-auto">
            From custom workrooms to electricians to landscaping - one platform, infinite possibilities.
            AI conversational intake, photo measurements, and smart quoting for any service business.
          </p>
          <div className="flex gap-4 justify-center">
            <Link
              href="/signup"
              className="bg-blue-600 hover:bg-blue-700 text-white px-8 py-3 rounded-lg text-lg font-semibold transition"
            >
              Start Free Trial
            </Link>
            <Link
              href="/pricing"
              className="bg-white hover:bg-gray-50 text-blue-600 px-8 py-3 rounded-lg text-lg font-semibold border-2 border-blue-600 transition"
            >
              View Pricing
            </Link>
          </div>
        </div>
      </section>

      {/* Industry Selection */}
      <section className="py-20 px-4">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-4xl font-bold text-center mb-4">Choose Your Industry</h2>
          <p className="text-xl text-gray-600 text-center mb-12">
            Select the template that matches your business
          </p>
          
          <div className="grid md:grid-cols-3 gap-8">
            {/* LuxeForge - Workrooms */}
            <Link href="/industries/workrooms" className="group">
              <div className="bg-white rounded-xl shadow-lg p-8 hover:shadow-xl transition border-2 border-transparent hover:border-purple-500">
                <div className="w-16 h-16 bg-purple-100 rounded-lg flex items-center justify-center mb-4">
                  <span className="text-3xl">🪟</span>
                </div>
                <h3 className="text-2xl font-bold mb-2 text-purple-700">LuxeForge</h3>
                <p className="text-lg font-semibold mb-2">Custom Workrooms</p>
                <p className="text-gray-600 mb-4">
                  Drapery, window treatments, soft furnishings. Production queue, fabric catalogs, COM workflow.
                </p>
                <ul className="text-sm text-gray-600 space-y-1">
                  <li>• Per-width & per-sqft pricing</li>
                  <li>• Fabric & hardware catalogs</li>
                  <li>• Production management</li>
                </ul>
              </div>
            </Link>

            {/* ElectricForge - Electricians */}
            <Link href="/industries/electricians" className="group">
              <div className="bg-white rounded-xl shadow-lg p-8 hover:shadow-xl transition border-2 border-transparent hover:border-yellow-500">
                <div className="w-16 h-16 bg-yellow-100 rounded-lg flex items-center justify-center mb-4">
                  <span className="text-3xl">⚡</span>
                </div>
                <h3 className="text-2xl font-bold mb-2 text-yellow-600">ElectricForge</h3>
                <p className="text-lg font-semibold mb-2">Electricians</p>
                <p className="text-gray-600 mb-4">
                  Electrical contracting and service calls. Hourly & per-fixture pricing, permit tracking, crew dispatch.
                </p>
                <ul className="text-sm text-gray-600 space-y-1">
                  <li>• Hourly & fixture pricing</li>
                  <li>• Permit tracking</li>
                  <li>• Emergency multiplier</li>
                </ul>
              </div>
            </Link>

            {/* LandscapeForge - Landscaping */}
            <Link href="/industries/landscaping" className="group">
              <div className="bg-white rounded-xl shadow-lg p-8 hover:shadow-xl transition border-2 border-transparent hover:border-green-600">
                <div className="w-16 h-16 bg-green-100 rounded-lg flex items-center justify-center mb-4">
                  <span className="text-3xl">🌳</span>
                </div>
                <h3 className="text-2xl font-bold mb-2 text-green-600">LandscapeForge</h3>
                <p className="text-lg font-semibold mb-2">Landscaping</p>
                <p className="text-gray-600 mb-4">
                  Landscape design and installation. Per-sqft areas, plant libraries, seasonal scheduling.
                </p>
                <ul className="text-sm text-gray-600 space-y-1">
                  <li>• Per-sqft & per-plant pricing</li>
                  <li>• Plant libraries</li>
                  <li>• Design mockups</li>
                </ul>
              </div>
            </Link>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="bg-gray-50 py-20 px-4">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-4xl font-bold text-center mb-12">Universal Features</h2>
          
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            <div className="bg-white rounded-lg p-6">
              <div className="text-3xl mb-3">🤖</div>
              <h3 className="text-xl font-bold mb-2">AI Conversational Intake</h3>
              <p className="text-gray-600">Natural language project scoping that adapts to your industry</p>
            </div>
            
            <div className="bg-white rounded-lg p-6">
              <div className="text-3xl mb-3">📸</div>
              <h3 className="text-xl font-bold mb-2">Photo Measurements</h3>
              <p className="text-gray-600">Automatic measurements from photos using OpenCV & AI</p>
            </div>
            
            <div className="bg-white rounded-lg p-6">
              <div className="text-3xl mb-3">💰</div>
              <h3 className="text-xl font-bold mb-2">Smart Quoting</h3>
              <p className="text-gray-600">Industry-specific pricing rules and auto-calculations</p>
            </div>
            
            <div className="bg-white rounded-lg p-6">
              <div className="text-3xl mb-3">👥</div>
              <h3 className="text-xl font-bold mb-2">Universal CRM</h3>
              <p className="text-gray-600">Customer management that works for any service business</p>
            </div>
            
            <div className="bg-white rounded-lg p-6">
              <div className="text-3xl mb-3">📅</div>
              <h3 className="text-xl font-bold mb-2">Calendar & Scheduling</h3>
              <p className="text-gray-600">Appointments, installations, and consultations</p>
            </div>
            
            <div className="bg-white rounded-lg p-6">
              <div className="text-3xl mb-3">💳</div>
              <h3 className="text-xl font-bold mb-2">Payments & Invoicing</h3>
              <p className="text-gray-600">Stripe integration for deposits and final payments</p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="bg-blue-600 text-white py-16 px-4">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-4xl font-bold mb-4">Ready to Transform Your Business?</h2>
          <p className="text-xl mb-8">Join thousands of service businesses using ContractorForge</p>
          <Link
            href="/signup"
            className="bg-white text-blue-600 px-8 py-3 rounded-lg text-lg font-semibold hover:bg-gray-100 transition inline-block"
          >
            Start Your Free Trial
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 text-gray-300 py-12 px-4">
        <div className="max-w-6xl mx-auto grid md:grid-cols-4 gap-8">
          <div>
            <h3 className="text-white font-bold text-lg mb-4">ContractorForge</h3>
            <p className="text-sm">Universal platform for service businesses</p>
          </div>
          <div>
            <h4 className="text-white font-semibold mb-3">Industries</h4>
            <ul className="space-y-2 text-sm">
              <li><Link href="/industries/workrooms">Custom Workrooms</Link></li>
              <li><Link href="/industries/electricians">Electricians</Link></li>
              <li><Link href="/industries/landscaping">Landscaping</Link></li>
            </ul>
          </div>
          <div>
            <h4 className="text-white font-semibold mb-3">Product</h4>
            <ul className="space-y-2 text-sm">
              <li><Link href="/pricing">Pricing</Link></li>
              <li><Link href="/features">Features</Link></li>
              <li><Link href="/docs">Documentation</Link></li>
            </ul>
          </div>
          <div>
            <h4 className="text-white font-semibold mb-3">Company</h4>
            <ul className="space-y-2 text-sm">
              <li><Link href="/about">About</Link></li>
              <li><Link href="/contact">Contact</Link></li>
              <li><Link href="/support">Support</Link></li>
            </ul>
          </div>
        </div>
        <div className="max-w-6xl mx-auto mt-8 pt-8 border-t border-gray-800 text-center text-sm">
          <p>&copy; 2026 ContractorForge. All rights reserved.</p>
        </div>
      </footer>
    </main>
  )
}
