'use client'
import Link from 'next/link'
import { TrendingUp, Users, Package, DollarSign, Factory, Brain, Plus, ArrowUpRight, Bell } from 'lucide-react'
import { useState, useEffect } from 'react'

export default function Dashboard() {
  const [time, setTime] = useState(new Date())
  useEffect(() => { const t = setInterval(() => setTime(new Date()), 1000); return () => clearInterval(t) }, [])
  const greeting = time.getHours() < 12 ? 'Good morning' : time.getHours() < 17 ? 'Good afternoon' : 'Good evening'

  return (
    <div className="min-h-screen bg-[#030308] p-6">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold">{greeting}!</h1>
          <p className="text-gray-500">Here's your business overview</p>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-right">
            <p className="text-lg font-mono text-amber-400">{time.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</p>
            <p className="text-xs text-gray-500">{time.toLocaleDateString([], { weekday: 'long', month: 'short', day: 'numeric' })}</p>
          </div>
          <button className="relative p-2 hover:bg-white/5 rounded-lg"><Bell className="w-5 h-5 text-gray-400" /></button>
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {[
          { label: 'Revenue MTD', value: '$0', sub: 'Add first invoice', icon: DollarSign, color: 'text-green-400', href: '/finance' },
          { label: 'Open Quotes', value: '0', sub: 'Create a quote', icon: Factory, color: 'text-blue-400', href: '/workroom' },
          { label: 'Customers', value: '0', sub: 'Add first customer', icon: Users, color: 'text-purple-400', href: '/customers' },
          { label: 'Inventory', value: '0', sub: 'Add stock items', icon: Package, color: 'text-amber-400', href: '/inventory' },
        ].map((s, i) => (
          <Link key={i} href={s.href} className="bg-[#0a0a12] rounded-xl p-5 border border-white/10 hover:border-white/20 group">
            <div className="flex items-center justify-between mb-3"><s.icon className={`w-5 h-5 ${s.color}`} /><ArrowUpRight className="w-4 h-4 text-gray-600 group-hover:text-white" /></div>
            <p className="text-2xl font-bold">{s.value}</p>
            <p className="text-sm text-gray-500">{s.label}</p>
            <p className="text-xs text-amber-400 mt-2">{s.sub} →</p>
          </Link>
        ))}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Link href="/max" className="bg-gradient-to-br from-amber-500/20 to-orange-500/20 rounded-2xl border border-amber-500/30 p-6 hover:border-amber-500/50">
          <div className="flex items-center gap-4 mb-4">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center"><Brain className="w-6 h-6" /></div>
            <div><h2 className="font-bold text-lg">Ask MAX</h2><p className="text-sm text-gray-400">Your AI assistant</p></div>
          </div>
          <p className="text-gray-400">MAX can help with quotes, inventory, and business insights.</p>
        </Link>
        <div className="bg-[#0a0a12] rounded-2xl border border-white/10 p-6">
          <h2 className="font-bold mb-4">Quick Actions</h2>
          <div className="grid grid-cols-2 gap-3">
            {[
              { label: 'New Quote', href: '/workroom', color: 'from-blue-500 to-cyan-600' },
              { label: 'Add Customer', href: '/customers', color: 'from-purple-500 to-pink-600' },
              { label: 'Check Stock', href: '/inventory', color: 'from-green-500 to-emerald-600' },
              { label: 'View Finance', href: '/finance', color: 'from-yellow-500 to-amber-600' },
            ].map((a, i) => (
              <Link key={i} href={a.href} className={`bg-gradient-to-r ${a.color} p-3 rounded-xl text-center font-medium text-sm hover:opacity-90`}>{a.label}</Link>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
