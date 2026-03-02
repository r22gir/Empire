'use client'
import { Settings, User, Building, Bell, Shield, Plug, CreditCard } from 'lucide-react'

export default function SettingsPage() {
  return (
    <div className="min-h-screen bg-[#030308] p-6">
      <div className="flex items-center gap-4 mb-8">
        <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-gray-500 to-gray-600 flex items-center justify-center">
          <Settings className="w-6 h-6" />
        </div>
        <h1 className="text-2xl font-bold">Settings</h1>
      </div>
      <div className="max-w-2xl space-y-4">
        {[
          { icon: User, label: 'Profile', desc: 'Your personal information' },
          { icon: Building, label: 'Business', desc: 'Company details and branding' },
          { icon: Bell, label: 'Notifications', desc: 'Email and alert preferences' },
          { icon: Shield, label: 'Security', desc: 'Password and two-factor auth' },
          { icon: Plug, label: 'Integrations', desc: 'Connect third-party apps' },
          { icon: CreditCard, label: 'Billing', desc: 'Subscription and payments' },
        ].map((item, i) => (
          <div key={i} className="bg-[#0a0a12] rounded-xl border border-white/10 p-5 flex items-center gap-4 cursor-pointer hover:border-white/20 transition">
            <div className="w-10 h-10 rounded-lg bg-white/10 flex items-center justify-center"><item.icon className="w-5 h-5 text-gray-400" /></div>
            <div><p className="font-medium">{item.label}</p><p className="text-sm text-gray-500">{item.desc}</p></div>
          </div>
        ))}
      </div>
    </div>
  )
}
