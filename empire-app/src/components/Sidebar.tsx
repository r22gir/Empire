'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Home, Factory, Package, DollarSign, Users, Lightbulb, Brain, Settings, Search, HelpCircle } from 'lucide-react'

const NAV = [
  { section: 'Command', items: [
    { label: 'Dashboard', href: '/', icon: Home },
    { label: 'MAX AI', href: '/max', icon: Brain },
  ]},
  { section: 'Operations', items: [
    { label: 'Workroom', href: '/workroom', icon: Factory },
    { label: 'Inventory', href: '/inventory', icon: Package },
  ]},
  { section: 'Finance', items: [
    { label: 'Finance', href: '/finance', icon: DollarSign },
  ]},
  { section: 'Customers', items: [
    { label: 'CRM', href: '/customers', icon: Users },
  ]},
  { section: 'Innovation', items: [
    { label: 'Creations', href: '/creations', icon: Lightbulb },
  ]},
]

export default function Sidebar() {
  const pathname = usePathname()
  return (
    <aside className="fixed top-0 left-0 w-64 h-full bg-[#0a0a12] border-r border-white/10 flex flex-col z-50">
      <div className="h-16 px-4 flex items-center gap-3 border-b border-white/10">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center">
          <span className="text-lg font-bold">E</span>
        </div>
        <div>
          <h1 className="font-bold text-sm text-amber-400">EMPIRE</h1>
          <p className="text-[10px] text-gray-500">Founder's Edition</p>
        </div>
      </div>
      <nav className="flex-1 overflow-y-auto px-3 py-4">
        {NAV.map((group) => (
          <div key={group.section} className="mb-4">
            <p className="text-xs text-gray-500 uppercase px-2 mb-2">{group.section}</p>
            {group.items.map((item) => (
              <Link key={item.href} href={item.href}
                className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm mb-1 ${pathname === item.href ? 'bg-amber-500/20 text-amber-400' : 'text-gray-400 hover:bg-white/5'}`}>
                <item.icon className="w-4 h-4" />{item.label}
              </Link>
            ))}
          </div>
        ))}
      </nav>
      <div className="p-3 border-t border-white/10">
        <Link href="/settings" className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-gray-400 hover:bg-white/5">
          <Settings className="w-4 h-4" />Settings
        </Link>
      </div>
    </aside>
  )
}
