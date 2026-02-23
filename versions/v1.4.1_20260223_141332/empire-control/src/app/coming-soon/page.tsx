'use client'
import { useSearchParams } from 'next/navigation'
import { Suspense } from 'react'
import {
  Construction, ArrowLeft, Bell, Calendar, Clock, Sparkles,
  Home, Brain, Rocket, CheckCircle
} from 'lucide-react'

function ComingSoonContent() {
  const searchParams = useSearchParams()
  const moduleName = searchParams.get('name') || 'This Module'
  const moduleId = searchParams.get('module') || 'unknown'

  const features = {
    'scheduler': ['Drag & drop scheduling', 'Team calendar view', 'Automated reminders', 'Integration with CRM'],
    'installations': ['Track install crews', 'GPS routing', 'Customer notifications', 'Photo documentation'],
    'invoicing': ['Professional templates', 'Auto-generate from quotes', 'Payment tracking', 'Recurring invoices'],
    'expenses': ['Receipt scanning', 'Category tracking', 'Vendor management', 'Tax reports'],
    'reports': ['Custom dashboards', 'Export to PDF/Excel', 'Scheduled reports', 'KPI tracking'],
    'quotes': ['Quote history', 'Version comparison', 'Win/loss analysis', 'Follow-up automation'],
    'portal': ['Customer login', 'Order tracking', 'Document sharing', 'Payment portal'],
    'research': ['Market analysis', 'Competitor tracking', 'Trend reports', 'AI insights'],
    'market': ['Industry data', 'Price benchmarking', 'Opportunity scoring', 'Territory mapping'],
    'store': ['Product catalog', 'Online ordering', 'Customer accounts', 'Inventory sync'],
    'suppliers': ['Vendor database', 'Price comparison', 'Order automation', 'Quality tracking'],
    'partners': ['Partner directory', 'Referral tracking', 'Commission management', 'Collaboration tools'],
    'tickets': ['Ticket management', 'SLA tracking', 'Knowledge base', 'Customer satisfaction'],
    'knowledge': ['Searchable articles', 'Video tutorials', 'FAQs', 'Community forums'],
    'training': ['Video courses', 'Certifications', 'Progress tracking', 'Team training'],
    'notifications': ['Real-time alerts', 'Email digests', 'Mobile push', 'Custom rules'],
  }

  const plannedFeatures = features[moduleId as keyof typeof features] || ['Advanced features', 'Seamless integration', 'AI assistance', 'Mobile support']

  return (
    <div className="min-h-screen bg-[#030308] text-white flex flex-col">
      {/* Header */}
      <header className="h-16 bg-[#0a0a12] border-b border-white/10 flex items-center px-6">
        <button 
          onClick={() => window.location.href = 'http://localhost:3000'}
          className="flex items-center gap-2 text-gray-400 hover:text-white transition"
        >
          <ArrowLeft className="w-5 h-5" />
          <span>Back to Control Center</span>
        </button>
      </header>

      {/* Content */}
      <main className="flex-1 flex items-center justify-center p-6">
        <div className="max-w-lg text-center">
          {/* Icon */}
          <div className="w-24 h-24 mx-auto mb-8 rounded-3xl bg-gradient-to-br from-amber-500/20 to-orange-500/20 border border-amber-500/30 flex items-center justify-center">
            <Construction className="w-12 h-12 text-amber-400" />
          </div>

          {/* Title */}
          <h1 className="text-4xl font-bold mb-4 bg-gradient-to-r from-amber-400 to-orange-500 bg-clip-text text-transparent">
            {moduleName}
          </h1>
          <p className="text-xl text-gray-400 mb-8">Coming Soon</p>

          {/* Description */}
          <p className="text-gray-500 mb-8">
            Our team is working hard to bring you this feature. 
            It will be part of the Empire Founder's Edition.
          </p>

          {/* Planned Features */}
          <div className="bg-[#0a0a12] rounded-2xl border border-white/10 p-6 mb-8 text-left">
            <h3 className="font-semibold mb-4 flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-amber-400" />
              Planned Features
            </h3>
            <div className="space-y-3">
              {plannedFeatures.map((feature, i) => (
                <div key={i} className="flex items-center gap-3 text-gray-400">
                  <CheckCircle className="w-4 h-4 text-green-500" />
                  <span>{feature}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Actions */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <button 
              onClick={() => window.location.href = 'http://localhost:3000'}
              className="flex items-center justify-center gap-2 bg-white/10 hover:bg-white/20 px-6 py-3 rounded-xl transition"
            >
              <Home className="w-5 h-5" />
              Control Center
            </button>
            <button 
              onClick={() => window.location.href = 'http://localhost:3009'}
              className="flex items-center justify-center gap-2 bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-black font-semibold px-6 py-3 rounded-xl transition"
            >
              <Brain className="w-5 h-5" />
              Ask MAX
            </button>
          </div>

          {/* Notify */}
          <div className="mt-12 p-4 bg-white/5 rounded-xl border border-white/10">
            <p className="text-sm text-gray-500 flex items-center justify-center gap-2">
              <Bell className="w-4 h-4" />
              MAX will notify you when this module is ready
            </p>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="h-16 border-t border-white/10 flex items-center justify-center text-sm text-gray-600">
        Empire Founder's Edition • Building the Future of Window Treatment Business
      </footer>
    </div>
  )
}

export default function ComingSoon() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-[#030308] flex items-center justify-center"><div className="text-white">Loading...</div></div>}>
      <ComingSoonContent />
    </Suspense>
  )
}
