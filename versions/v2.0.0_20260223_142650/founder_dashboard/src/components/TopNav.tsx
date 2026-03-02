'use client'
import { useState } from 'react'
import {
  Home, Brain, Package, DollarSign, Users, Lightbulb, Factory,
  Menu, X, Search, Bell
} from 'lucide-react'

const APPS = [
  { label: 'Control Center', icon: Home, port: 3000 },
  { label: 'WorkroomForge', icon: Factory, port: 3001 },
  { label: 'Inventory', icon: Package, port: 3004 },
  { label: 'Finance', icon: DollarSign, port: 3005 },
  { label: 'Creations', icon: Lightbulb, port: 3006 },
  { label: 'CRM', icon: Users, port: 3007 },
  { label: 'MAX AI', icon: Brain, port: 3009 },
]

export default function TopNav({ currentApp, currentPort }: { currentApp: string, currentPort: number }) {
  const [showMenu, setShowMenu] = useState(false)

  return (
    <>
      <div className="h-12 bg-[#0a0a12] border-b border-white/10 flex items-center justify-between px-4 sticky top-0 z-50">
        <div className="flex items-center gap-3">
          <button onClick={() => window.location.href = 'http://localhost:3000'} className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center">
              <span className="text-xs font-bold">E</span>
            </div>
            <span className="text-sm font-bold text-amber-400 hidden sm:inline">EMPIRE</span>
          </button>
          <span className="text-gray-600">/</span>
          <span className="text-sm font-medium">{currentApp}</span>
        </div>
        <div className="hidden md:flex items-center gap-1">
          {APPS.map(app => (
            <button key={app.port} onClick={() => window.location.href = 'http://localhost:' + app.port}
              className={'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs transition ' + (app.port === currentPort ? 'bg-amber-500/20 text-amber-400' : 'text-gray-400 hover:text-white hover:bg-white/5')}>
              <app.icon className="w-3.5 h-3.5" />
              <span className="hidden lg:inline">{app.label}</span>
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <button className="relative p-2 text-gray-400 hover:text-white hover:bg-white/5 rounded-lg">
            <Bell className="w-4 h-4" />
            <span className="absolute top-1 right-1 w-1.5 h-1.5 bg-red-500 rounded-full" />
          </button>
          <button onClick={() => window.location.href = 'http://localhost:3009'}
            className="flex items-center gap-1.5 bg-amber-500/20 text-amber-400 px-3 py-1.5 rounded-lg text-xs hover:bg-amber-500/30">
            <Brain className="w-3.5 h-3.5" /><span className="hidden sm:inline">MAX</span>
          </button>
          <button onClick={() => setShowMenu(!showMenu)} className="md:hidden p-2 text-gray-400">
            <Menu className="w-5 h-5" />
          </button>
        </div>
      </div>
      {showMenu && (
        <div className="fixed inset-0 z-50 md:hidden">
          <div className="absolute inset-0 bg-black/60" onClick={() => setShowMenu(false)} />
          <div className="absolute right-0 top-0 h-full w-64 bg-[#0a0a12] border-l border-white/10 p-4">
            <div className="flex justify-between items-center mb-4">
              <span className="font-bold">Menu</span>
              <button onClick={() => setShowMenu(false)}><X className="w-5 h-5" /></button>
            </div>
            <div className="space-y-1">
              {APPS.map(app => (
                <button key={app.port} onClick={() => window.location.href = 'http://localhost:' + app.port}
                  className={'w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm ' + (app.port === currentPort ? 'bg-amber-500/20 text-amber-400' : 'text-gray-400 hover:bg-white/5')}>
                  <app.icon className="w-4 h-4" />{app.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </>
  )
}
