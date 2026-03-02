'use client'
import { useState, useEffect, useRef } from 'react'
import {
  Factory, Gem, Ticket, Package, DollarSign, Calendar, Users, BarChart3,
  Send, Bell, Settings, Search, Clock, CheckCircle, AlertTriangle, 
  TrendingUp, MessageSquare, Zap, Brain, ExternalLink, RefreshCw,
  X, ChevronRight, Briefcase, Activity, Target, Cpu
} from 'lucide-react'

// AI Agents
const AGENTS = [
  { id: 'cleo', name: 'CLEO', role: 'Customer Service', color: 'from-pink-500 to-rose-600', status: 'online', 
    projects: [
      { id: 'p1', title: 'Quote for Azul Designs', status: 'in_progress', priority: 'high', progress: 65 },
      { id: 'p2', title: 'Support Ticket #47', status: 'waiting', priority: 'medium', progress: 30 },
      { id: 'p3', title: 'Follow-up: Johnson Design', status: 'pending', priority: 'low', progress: 0 },
    ],
    stats: { completed: 45, failed: 2, avgTime: '4.2 min' }
  },
  { id: 'nova', name: 'NOVA', role: 'Analytics & Reports', color: 'from-violet-500 to-purple-600', status: 'online',
    projects: [
      { id: 'p4', title: 'Daily Revenue Report', status: 'completed', priority: 'high', progress: 100 },
      { id: 'p5', title: 'Weekly Trends Analysis', status: 'in_progress', priority: 'medium', progress: 80 },
    ],
    stats: { completed: 120, failed: 0, avgTime: '12.5 min' }
  },
  { id: 'iris', name: 'IRIS', role: 'Inventory Management', color: 'from-emerald-500 to-green-600', status: 'online',
    projects: [
      { id: 'p6', title: 'Low Stock Alert: Blackout Lining', status: 'alert', priority: 'high', progress: 100 },
      { id: 'p7', title: 'Rowley Order #2847', status: 'in_progress', priority: 'medium', progress: 45 },
      { id: 'p8', title: 'Monthly Inventory Audit', status: 'scheduled', priority: 'low', progress: 0 },
    ],
    stats: { completed: 67, failed: 1, avgTime: '8.3 min' }
  },
  { id: 'atlas', name: 'ATLAS', role: 'Shipping & Logistics', color: 'from-blue-500 to-cyan-600', status: 'online',
    projects: [
      { id: 'p9', title: 'Ship Order #1042 - Express', status: 'in_progress', priority: 'high', progress: 70 },
      { id: 'p10', title: 'Track Return #876', status: 'waiting', priority: 'medium', progress: 50 },
    ],
    stats: { completed: 89, failed: 3, avgTime: '2.1 min' }
  },
  { id: 'sage', name: 'SAGE', role: 'Finance & Accounting', color: 'from-amber-500 to-yellow-600', status: 'online',
    projects: [
      { id: 'p11', title: 'Invoice #INV-2847', status: 'completed', priority: 'high', progress: 100 },
      { id: 'p12', title: 'Q1 Tax Preparation', status: 'in_progress', priority: 'high', progress: 35 },
      { id: 'p13', title: 'Expense Report Review', status: 'pending', priority: 'medium', progress: 0 },
    ],
    stats: { completed: 34, failed: 0, avgTime: '15.7 min' }
  },
  { id: 'pixel', name: 'PIXEL', role: 'Design & Visuals', color: 'from-fuchsia-500 to-pink-600', status: 'idle',
    projects: [
      { id: 'p14', title: 'Product Photo Enhancement', status: 'queued', priority: 'medium', progress: 0 },
    ],
    stats: { completed: 23, failed: 0, avgTime: '25.4 min' }
  },
  { id: 'scout', name: 'SCOUT', role: 'Research & Discovery', color: 'from-orange-500 to-red-600', status: 'online',
    projects: [
      { id: 'p15', title: 'Competitor Price Analysis', status: 'in_progress', priority: 'medium', progress: 60 },
      { id: 'p16', title: 'Market Trends Q1 2026', status: 'in_progress', priority: 'low', progress: 40 },
    ],
    stats: { completed: 56, failed: 1, avgTime: '45.2 min' }
  },
  { id: 'forge', name: 'FORGE', role: 'Production & Manufacturing', color: 'from-slate-500 to-gray-600', status: 'online',
    projects: [
      { id: 'p17', title: 'Job #142 - Ripplefold Drapes', status: 'in_progress', priority: 'high', progress: 85 },
      { id: 'p18', title: 'Job #143 - Roman Shades x3', status: 'queued', priority: 'medium', progress: 0 },
      { id: 'p19', title: 'Quality Check: Order #1038', status: 'in_progress', priority: 'high', progress: 50 },
    ],
    stats: { completed: 78, failed: 2, avgTime: '3.2 hrs' }
  },
]

const APPS = [
  { id: 'workroom', name: 'WorkroomForge', icon: Factory, color: 'from-amber-500 to-orange-600', port: 3001, desc: 'Quotes & Production', badge: 2 },
  { id: 'luxe', name: 'LuxeForge', icon: Gem, color: 'from-purple-500 to-pink-600', port: 3002, desc: 'Marketplace', badge: 0 },
  { id: 'support', name: 'SupportForge', icon: Ticket, color: 'from-blue-500 to-cyan-600', port: 3003, desc: 'Support Tickets', badge: 0 },
  { id: 'inventory', name: 'Inventory', icon: Package, color: 'from-green-500 to-emerald-600', port: 3004, desc: 'Stock & Orders', badge: 1 },
  { id: 'finance', name: 'Finance', icon: DollarSign, color: 'from-yellow-500 to-amber-600', port: 3005, desc: 'Accounting', badge: 0 },
  { id: 'calendar', name: 'Schedule', icon: Calendar, color: 'from-red-500 to-rose-600', port: 3006, desc: 'Calendar', badge: 0 },
  { id: 'crm', name: 'Customers', icon: Users, color: 'from-indigo-500 to-violet-600', port: 3007, desc: 'CRM', badge: 0 },
  { id: 'analytics', name: 'Analytics', icon: BarChart3, color: 'from-teal-500 to-cyan-600', port: 3008, desc: 'Reports', badge: 0 },
]

export default function EmpireControlCenter() {
  const [chatHistory, setChatHistory] = useState<{role: string, content: string, time: Date}[]>([])
  const [isTyping, setIsTyping] = useState(false)
  const [inputValue, setInputValue] = useState('')
  const [stats, setStats] = useState({ revenue: 42500, openQuotes: 1, activeJobs: 3, alerts: 1 })
  const [tasks, setTasks] = useState([
    { id: 1, text: 'Quote for Azul Designs', urgent: true, done: false },
    { id: 2, text: 'Follow up: Smith order', urgent: false, done: false },
    { id: 3, text: 'Order fabric from Rowley', urgent: false, done: false },
  ])
  const [activities] = useState([
    { id: 1, text: 'Payment $1,500 received', type: 'payment', time: '10 min ago' },
    { id: 2, text: 'New quote request - Azul Designs', type: 'quote', time: '25 min ago' },
    { id: 3, text: 'Job #142 completed', type: 'job', time: '1 hour ago' },
  ])
  const [currentTime, setCurrentTime] = useState(new Date())
  const [showAgentsPanel, setShowAgentsPanel] = useState(false)
  const [selectedAgent, setSelectedAgent] = useState<typeof AGENTS[0] | null>(null)
  const [selectedProject, setSelectedProject] = useState<any>(null)
  const chatEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000)
    return () => clearInterval(timer)
  }, [])

  useEffect(() => {
    const hour = new Date().getHours()
    const greeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening'
    setTimeout(() => {
      setChatHistory([{
        role: 'max',
        content: `${greeting}! I'm MAX, your Empire AI assistant.\n\n📬 You have 2 new quote requests\n💰 $1,500 payment received today\n⚠️ 1 inventory alert\n\nWhat would you like to focus on?`,
        time: new Date()
      }])
    }, 300)
    fetchStats()
  }, [])

  const fetchStats = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/v1/quote-requests')
      if (res.ok) {
        const data = await res.json()
        const pending = data.requests?.filter((r: any) => r.status === 'pending').length || 0
        setStats(s => ({ ...s, openQuotes: pending }))
      }
    } catch (e) { console.error(e) }
  }

  const sendToMax = async () => {
    if (!inputValue.trim()) return
    const userMsg = inputValue.trim()
    setInputValue('')
    setChatHistory(h => [...h, { role: 'user', content: userMsg, time: new Date() }])
    setIsTyping(true)
    setTimeout(() => chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 100)

    try {
      const res = await fetch('http://localhost:8000/api/v1/max/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMsg })
      })
      if (res.ok) {
        const data = await res.json()
        setChatHistory(h => [...h, { role: 'max', content: data.response, time: new Date() }])
      } else throw new Error()
    } catch {
      const response = getSmartResponse(userMsg)
      setChatHistory(h => [...h, { role: 'max', content: response, time: new Date() }])
    }
    setIsTyping(false)
    setTimeout(() => chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 100)
  }

  const getSmartResponse = (msg: string): string => {
    const l = msg.toLowerCase()
    if (l.includes('quote') || l.includes('workroom')) return "Opening WorkroomForge... You have 2 pending quotes:\n\n1. **Azul Designs** - Ripplefold drapes\n2. **Test Designer** - 3 windows\n\nClick the WorkroomForge tile or I can summarize details!"
    if (l.includes('inventory') || l.includes('stock')) return "📦 Inventory Status:\n\n⚠️ **Low Stock:**\n• Blackout lining: 15 yards left\n• Ripplefold tape: 20 meters\n\n✅ **Good Stock:**\n• Standard lining: 85 yards\n• Drapery hooks: 500+\n\nWant me to create a Rowley order?"
    if (l.includes('revenue') || l.includes('money') || l.includes('finance')) return `💰 Financial Summary:\n\n**This Month:** $${stats.revenue.toLocaleString()}\n**Today:** +$1,500 payment received\n**Pending:** $4,200 in unpaid invoices\n\nClick Finance for full details.`
    if (l.includes('agent')) return "🤖 All 8 AI agents are operational!\n\nClick the **AI Agents** button to see their offices and current projects."
    if (l.includes('help')) return "I can help with:\n\n🏭 **Quotes** - Create, manage, send\n📦 **Inventory** - Check stock, order\n💰 **Finance** - Revenue, invoices\n📅 **Schedule** - Jobs, deadlines\n👥 **Customers** - CRM, history\n🤖 **Agents** - View AI team status\n\nJust ask or click an app!"
    return "I understand! Click any app tile below to get started, or ask me about:\n• Quotes & production\n• Inventory levels\n• Financial reports\n• AI agent status"
  }

  const openApp = (port: number) => window.open(`http://localhost:${port}`, '_blank')
  const openMaxInterface = () => window.open('http://localhost:3009', '_blank')
  const toggleTask = (id: number) => setTasks(tasks.map(t => t.id === id ? { ...t, done: !t.done } : t))

  const getActivityIcon = (type: string) => {
    const icons: Record<string, JSX.Element> = {
      payment: <DollarSign className="w-4 h-4 text-green-400" />,
      quote: <MessageSquare className="w-4 h-4 text-blue-400" />,
      job: <CheckCircle className="w-4 h-4 text-purple-400" />,
      alert: <AlertTriangle className="w-4 h-4 text-yellow-400" />,
    }
    return icons[type] || <Zap className="w-4 h-4 text-gray-400" />
  }

  const getStatusColor = (status: string) => {
    if (status === 'online') return 'bg-green-500'
    if (status === 'idle') return 'bg-yellow-500'
    return 'bg-red-500'
  }

  const getProjectStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      'completed': 'bg-green-500/20 text-green-400',
      'in_progress': 'bg-blue-500/20 text-blue-400',
      'waiting': 'bg-yellow-500/20 text-yellow-400',
      'pending': 'bg-gray-500/20 text-gray-400',
      'queued': 'bg-purple-500/20 text-purple-400',
      'alert': 'bg-red-500/20 text-red-400',
      'scheduled': 'bg-cyan-500/20 text-cyan-400',
    }
    return colors[status] || 'bg-gray-500/20 text-gray-400'
  }

  const getPriorityColor = (priority: string) => {
    const colors: Record<string, string> = {
      'high': 'text-red-400',
      'medium': 'text-yellow-400',
      'low': 'text-gray-400',
    }
    return colors[priority] || 'text-gray-400'
  }

  return (
    <div className="min-h-screen bg-[#0D0D0D] text-white">
      {/* Header */}
      <header className="bg-[#1A1A1A] border-b border-gray-800 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="text-4xl">🏰</div>
            <div>
              <h1 className="text-2xl font-bold bg-gradient-to-r from-[#C9A84C] to-yellow-300 bg-clip-text text-transparent">
                EMPIRE CONTROL CENTER
              </h1>
              <p className="text-sm text-gray-500">Command your business empire</p>
            </div>
          </div>
          
          <div className="flex items-center gap-4">
            <div className="text-right mr-4 hidden md:block">
              <div className="text-xl font-mono text-[#C9A84C]">
                {currentTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </div>
              <div className="text-xs text-gray-500">
                {currentTime.toLocaleDateString([], { weekday: 'long', month: 'short', day: 'numeric' })}
              </div>
            </div>
            <div className="relative hidden md:block">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
              <input type="text" placeholder="Search..." className="bg-[#2C2C2C] border border-gray-700 rounded-lg pl-10 pr-4 py-2 text-sm w-48 focus:border-[#C9A84C] outline-none" />
            </div>
            <button className="relative p-2 text-gray-400 hover:text-white">
              <Bell className="w-5 h-5" />
              <span className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 rounded-full text-xs flex items-center justify-center">3</span>
            </button>
            <button className="p-2 text-gray-400 hover:text-white">
              <Settings className="w-5 h-5" />
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto p-6">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          
          {/* LEFT: MAX AI Chat */}
          <div className="lg:col-span-5">
            <div className="bg-[#1A1A1A] rounded-2xl border border-gray-800 overflow-hidden h-[650px] flex flex-col">
              {/* MAX Header - Clickable Brain */}
              <div className="bg-gradient-to-r from-[#C9A84C]/20 to-amber-500/10 px-5 py-4 border-b border-gray-800">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    {/* Clickable Brain - Opens MAX Interface */}
                    <button 
                      onClick={openMaxInterface}
                      className="w-14 h-14 rounded-full bg-gradient-to-br from-[#C9A84C] to-amber-600 flex items-center justify-center hover:scale-110 transition-transform cursor-pointer group relative"
                      title="Open MAX Interface"
                    >
                      <Brain className="w-7 h-7 text-[#0D0D0D]" />
                      <div className="absolute -bottom-1 -right-1 w-5 h-5 bg-blue-500 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition">
                        <ExternalLink className="w-3 h-3 text-white" />
                      </div>
                    </button>
                    <div>
                      <h2 className="font-bold text-xl flex items-center gap-2">
                        MAX
                        <span className="text-xs bg-green-500/20 text-green-400 px-2 py-0.5 rounded-full">Online</span>
                      </h2>
                      <p className="text-sm text-gray-400">Your AI Business Assistant</p>
                    </div>
                  </div>
                  
                  {/* AI Agents Button */}
                  <button
                    onClick={() => setShowAgentsPanel(true)}
                    className="flex items-center gap-2 bg-[#2C2C2C] hover:bg-[#3C3C3C] border border-gray-700 rounded-xl px-4 py-2 transition"
                  >
                    <Cpu className="w-4 h-4 text-[#C9A84C]" />
                    <span className="text-sm font-medium">AI Agents</span>
                    <span className="w-5 h-5 bg-green-500/20 text-green-400 rounded-full text-xs flex items-center justify-center">8</span>
                  </button>
                </div>
              </div>

              {/* Chat Messages */}
              <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {chatHistory.map((msg, i) => (
                  <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-[90%] rounded-2xl px-4 py-3 ${
                      msg.role === 'user' ? 'bg-[#C9A84C] text-[#0D0D0D]' : 'bg-[#2C2C2C] text-white'
                    }`}>
                      <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                      <p className={`text-xs mt-2 ${msg.role === 'user' ? 'text-[#0D0D0D]/50' : 'text-gray-500'}`}>
                        {msg.time.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </p>
                    </div>
                  </div>
                ))}
                {isTyping && (
                  <div className="flex justify-start">
                    <div className="bg-[#2C2C2C] rounded-2xl px-4 py-3">
                      <div className="flex gap-1">
                        <span className="w-2 h-2 bg-[#C9A84C] rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                        <span className="w-2 h-2 bg-[#C9A84C] rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                        <span className="w-2 h-2 bg-[#C9A84C] rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                      </div>
                    </div>
                  </div>
                )}
                <div ref={chatEndRef} />
              </div>

              {/* Input */}
              <div className="p-4 border-t border-gray-800 bg-[#1A1A1A]">
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && sendToMax()}
                    placeholder="Ask MAX anything..."
                    className="flex-1 bg-[#2C2C2C] border border-gray-700 rounded-xl px-4 py-3 focus:border-[#C9A84C] outline-none"
                  />
                  <button onClick={sendToMax} disabled={!inputValue.trim()} className="bg-[#C9A84C] hover:bg-[#B8973F] disabled:opacity-50 text-[#0D0D0D] px-5 rounded-xl transition font-semibold">
                    <Send className="w-5 h-5" />
                  </button>
                </div>
                <div className="flex gap-2 mt-3 flex-wrap">
                  {['📊 Stats', '📋 Tasks', '💰 Revenue', '🤖 Agents'].map(btn => (
                    <button key={btn} onClick={() => setInputValue(btn.split(' ')[1])} className="text-xs bg-[#2C2C2C] hover:bg-[#3C3C3C] px-3 py-1.5 rounded-lg text-gray-400 hover:text-white transition">
                      {btn}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* RIGHT: Dashboard */}
          <div className="lg:col-span-7 space-y-6">
            
            {/* Quick Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[
                { label: 'Revenue MTD', value: `$${(stats.revenue/1000).toFixed(1)}k`, icon: TrendingUp, color: 'text-green-400', change: '+12%' },
                { label: 'Open Quotes', value: stats.openQuotes, icon: MessageSquare, color: 'text-yellow-400' },
                { label: 'Active Jobs', value: stats.activeJobs, icon: Factory, color: 'text-blue-400' },
                { label: 'Alerts', value: stats.alerts, icon: AlertTriangle, color: stats.alerts > 0 ? 'text-red-400' : 'text-gray-600' },
              ].map((stat, i) => (
                <div key={i} className="bg-[#1A1A1A] rounded-xl p-4 border border-gray-800 hover:border-gray-700 transition">
                  <div className="flex items-center justify-between mb-2">
                    <stat.icon className={`w-5 h-5 ${stat.color}`} />
                    {stat.change && <span className="text-xs text-green-400">{stat.change}</span>}
                  </div>
                  <p className="text-2xl font-bold">{stat.value}</p>
                  <p className="text-xs text-gray-500">{stat.label}</p>
                </div>
              ))}
            </div>

            {/* App Launcher */}
            <div className="bg-[#1A1A1A] rounded-2xl p-5 border border-gray-800">
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <Zap className="w-5 h-5 text-[#C9A84C]" />
                Quick Launch
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {APPS.map(app => (
                  <button
                    key={app.id}
                    onClick={() => openApp(app.port)}
                    className="group relative bg-[#2C2C2C] hover:bg-[#3C3C3C] rounded-xl p-4 transition-all hover:scale-[1.02] border border-gray-700 hover:border-gray-600 text-left"
                  >
                    <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${app.color} flex items-center justify-center mb-3 group-hover:scale-110 transition`}>
                      <app.icon className="w-6 h-6 text-white" />
                    </div>
                    <p className="font-semibold text-sm">{app.name}</p>
                    <p className="text-xs text-gray-500">{app.desc}</p>
                    {app.badge > 0 && (
                      <span className="absolute top-3 right-3 w-5 h-5 bg-red-500 rounded-full text-xs flex items-center justify-center">
                        {app.badge}
                      </span>
                    )}
                  </button>
                ))}
              </div>
            </div>

            {/* Tasks & Activity */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Tasks */}
              <div className="bg-[#1A1A1A] rounded-2xl p-5 border border-gray-800">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-semibold flex items-center gap-2">
                    <CheckCircle className="w-5 h-5 text-[#C9A84C]" />
                    Today's Tasks
                  </h3>
                  <span className="text-xs text-gray-500">{tasks.filter(t => !t.done).length} remaining</span>
                </div>
                <div className="space-y-2">
                  {tasks.map(task => (
                    <div
                      key={task.id}
                      onClick={() => toggleTask(task.id)}
                      className={`flex items-center gap-3 p-3 rounded-lg cursor-pointer transition ${
                        task.done ? 'bg-[#2C2C2C]/50 opacity-60' : 'bg-[#2C2C2C] hover:bg-[#3C3C3C]'
                      }`}
                    >
                      <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center flex-shrink-0 ${
                        task.done ? 'bg-green-500 border-green-500' : task.urgent ? 'border-red-400' : 'border-gray-600'
                      }`}>
                        {task.done && <CheckCircle className="w-3 h-3 text-white" />}
                      </div>
                      <span className={`flex-1 text-sm ${task.done ? 'line-through text-gray-500' : ''}`}>
                        {task.text}
                      </span>
                      {task.urgent && !task.done && (
                        <span className="text-xs bg-red-500/20 text-red-400 px-2 py-0.5 rounded flex-shrink-0">!</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {/* Activity */}
              <div className="bg-[#1A1A1A] rounded-2xl p-5 border border-gray-800">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-semibold flex items-center gap-2">
                    <Bell className="w-5 h-5 text-[#C9A84C]" />
                    Recent Activity
                  </h3>
                  <button onClick={fetchStats} className="text-gray-500 hover:text-white">
                    <RefreshCw className="w-4 h-4" />
                  </button>
                </div>
                <div className="space-y-3">
                  {activities.map(a => (
                    <div key={a.id} className="flex items-start gap-3 p-3 rounded-lg bg-[#2C2C2C]/50 hover:bg-[#2C2C2C] transition cursor-pointer">
                      {getActivityIcon(a.type)}
                      <div className="flex-1 min-w-0">
                        <p className="text-sm truncate">{a.text}</p>
                        <p className="text-xs text-gray-500 flex items-center gap-1 mt-1">
                          <Clock className="w-3 h-3" /> {a.time}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* AI Agents Panel - Slide Over */}
      {showAgentsPanel && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <div className="absolute inset-0 bg-black/60" onClick={() => { setShowAgentsPanel(false); setSelectedAgent(null); }} />
          <div className="relative w-full max-w-md bg-[#1A1A1A] border-l border-gray-800 overflow-hidden flex flex-col animate-slide-in">
            {/* Panel Header */}
            <div className="px-6 py-4 border-b border-gray-800 flex items-center justify-between bg-gradient-to-r from-[#C9A84C]/10 to-transparent">
              <div className="flex items-center gap-3">
                <Cpu className="w-6 h-6 text-[#C9A84C]" />
                <div>
                  <h2 className="font-bold text-lg">AI Agents</h2>
                  <p className="text-xs text-gray-500">8 agents • All systems operational</p>
                </div>
              </div>
              <button onClick={() => { setShowAgentsPanel(false); setSelectedAgent(null); }} className="p-2 hover:bg-[#2C2C2C] rounded-lg">
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Agents List or Agent Detail */}
            <div className="flex-1 overflow-y-auto">
              {!selectedAgent ? (
                // Agents List
                <div className="p-4 space-y-2">
                  {AGENTS.map(agent => (
                    <button
                      key={agent.id}
                      onClick={() => setSelectedAgent(agent)}
                      className="w-full bg-[#2C2C2C] hover:bg-[#3C3C3C] rounded-xl p-4 text-left transition group"
                    >
                      <div className="flex items-center gap-4">
                        <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${agent.color} flex items-center justify-center`}>
                          <span className="text-lg font-bold text-white">{agent.name[0]}</span>
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <span className="font-bold">{agent.name}</span>
                            <div className={`w-2 h-2 rounded-full ${getStatusColor(agent.status)}`} />
                          </div>
                          <p className="text-sm text-gray-400">{agent.role}</p>
                          <p className="text-xs text-gray-600 mt-1">{agent.projects.length} active projects</p>
                        </div>
                        <ChevronRight className="w-5 h-5 text-gray-600 group-hover:text-white transition" />
                      </div>
                    </button>
                  ))}
                </div>
              ) : (
                // Agent Office Detail
                <div>
                  {/* Agent Header */}
                  <div className={`p-6 bg-gradient-to-br ${selectedAgent.color} bg-opacity-20`}>
                    <button onClick={() => setSelectedAgent(null)} className="text-sm text-gray-400 hover:text-white mb-3 flex items-center gap-1">
                      ← Back to Agents
                    </button>
                    <div className="flex items-center gap-4">
                      <div className={`w-16 h-16 rounded-2xl bg-gradient-to-br ${selectedAgent.color} flex items-center justify-center`}>
                        <span className="text-2xl font-bold text-white">{selectedAgent.name[0]}</span>
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <h3 className="text-xl font-bold">{selectedAgent.name}'s Office</h3>
                          <div className={`w-2 h-2 rounded-full ${getStatusColor(selectedAgent.status)}`} />
                        </div>
                        <p className="text-gray-400">{selectedAgent.role}</p>
                      </div>
                    </div>
                    
                    {/* Agent Stats */}
                    <div className="grid grid-cols-3 gap-3 mt-4">
                      <div className="bg-black/20 rounded-lg p-3 text-center">
                        <p className="text-xl font-bold text-green-400">{selectedAgent.stats.completed}</p>
                        <p className="text-xs text-gray-400">Completed</p>
                      </div>
                      <div className="bg-black/20 rounded-lg p-3 text-center">
                        <p className="text-xl font-bold text-red-400">{selectedAgent.stats.failed}</p>
                        <p className="text-xs text-gray-400">Failed</p>
                      </div>
                      <div className="bg-black/20 rounded-lg p-3 text-center">
                        <p className="text-xl font-bold text-blue-400">{selectedAgent.stats.avgTime}</p>
                        <p className="text-xs text-gray-400">Avg Time</p>
                      </div>
                    </div>
                  </div>

                  {/* Projects */}
                  <div className="p-4">
                    <h4 className="font-semibold text-sm text-gray-400 uppercase tracking-wider mb-3">Current Projects</h4>
                    <div className="space-y-2">
                      {selectedAgent.projects.map(project => (
                        <button
                          key={project.id}
                          onClick={() => setSelectedProject(project)}
                          className="w-full bg-[#2C2C2C] hover:bg-[#3C3C3C] rounded-xl p-4 text-left transition"
                        >
                          <div className="flex items-start justify-between mb-2">
                            <h5 className="font-semibold text-sm">{project.title}</h5>
                            <span className={`text-xs px-2 py-0.5 rounded ${getProjectStatusColor(project.status)}`}>
                              {project.status.replace('_', ' ')}
                            </span>
                          </div>
                          <div className="flex items-center justify-between">
                            <span className={`text-xs ${getPriorityColor(project.priority)}`}>
                              {project.priority.toUpperCase()} Priority
                            </span>
                            <span className="text-xs text-gray-500">{project.progress}%</span>
                          </div>
                          {/* Progress Bar */}
                          <div className="mt-2 h-1.5 bg-[#1A1A1A] rounded-full overflow-hidden">
                            <div 
                              className={`h-full rounded-full transition-all ${
                                project.status === 'completed' ? 'bg-green-500' :
                                project.status === 'alert' ? 'bg-red-500' : 'bg-[#C9A84C]'
                              }`}
                              style={{ width: `${project.progress}%` }}
                            />
                          </div>
                        </button>
                      ))}
                    </div>
                    
                    {/* Quick Actions */}
                    <div className="mt-4 pt-4 border-t border-gray-800">
                      <h4 className="font-semibold text-sm text-gray-400 uppercase tracking-wider mb-3">Quick Actions</h4>
                      <div className="grid grid-cols-2 gap-2">
                        <button className="bg-[#2C2C2C] hover:bg-[#3C3C3C] rounded-lg p-3 text-sm transition flex items-center gap-2">
                          <MessageSquare className="w-4 h-4 text-[#C9A84C]" />
                          Chat with {selectedAgent.name}
                        </button>
                        <button className="bg-[#2C2C2C] hover:bg-[#3C3C3C] rounded-lg p-3 text-sm transition flex items-center gap-2">
                          <Target className="w-4 h-4 text-[#C9A84C]" />
                          Assign Task
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Project Detail Modal */}
      {selectedProject && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/70" onClick={() => setSelectedProject(null)} />
          <div className="relative bg-[#1A1A1A] rounded-2xl border border-gray-800 w-full max-w-lg overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-800 flex items-center justify-between">
              <h3 className="font-bold text-lg">Project Details</h3>
              <button onClick={() => setSelectedProject(null)} className="p-1 hover:bg-[#2C2C2C] rounded-lg">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6">
              <div className="flex items-start justify-between mb-4">
                <h4 className="text-xl font-bold">{selectedProject.title}</h4>
                <span className={`text-xs px-3 py-1 rounded-full ${getProjectStatusColor(selectedProject.status)}`}>
                  {selectedProject.status.replace('_', ' ')}
                </span>
              </div>
              
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-gray-400">Priority</span>
                  <span className={`font-semibold ${getPriorityColor(selectedProject.priority)}`}>
                    {selectedProject.priority.toUpperCase()}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-400">Progress</span>
                  <span className="font-semibold">{selectedProject.progress}%</span>
                </div>
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-gray-400 text-sm">Completion</span>
                  </div>
                  <div className="h-3 bg-[#2C2C2C] rounded-full overflow-hidden">
                    <div 
                      className={`h-full rounded-full transition-all ${
                        selectedProject.status === 'completed' ? 'bg-green-500' :
                        selectedProject.status === 'alert' ? 'bg-red-500' : 'bg-[#C9A84C]'
                      }`}
                      style={{ width: `${selectedProject.progress}%` }}
                    />
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-400">Assigned Agent</span>
                  <span className="font-semibold">{selectedAgent?.name}</span>
                </div>
              </div>

              <div className="mt-6 pt-4 border-t border-gray-800 flex gap-3">
                <button className="flex-1 bg-[#C9A84C] hover:bg-[#B8973F] text-[#0D0D0D] font-semibold py-3 rounded-xl transition">
                  View in App
                </button>
                <button className="flex-1 bg-[#2C2C2C] hover:bg-[#3C3C3C] py-3 rounded-xl transition">
                  Edit Project
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* CSS for animations */}
      <style jsx>{`
        @keyframes slide-in {
          from { transform: translateX(100%); }
          to { transform: translateX(0); }
        }
        .animate-slide-in {
          animation: slide-in 0.3s ease-out;
        }
      `}</style>
    </div>
  )
}
