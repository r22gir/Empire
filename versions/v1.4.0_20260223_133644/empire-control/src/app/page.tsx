'use client'
import { useState, useEffect, useRef } from 'react'
import {
  Factory, Gem, Ticket, Package, DollarSign, Calendar, Users, BarChart3,
  Send, Bell, Settings, Search, Clock, CheckCircle, AlertTriangle, 
  TrendingUp, MessageSquare, Zap, Brain, ExternalLink, RefreshCw,
  X, ChevronRight, Target, Cpu, FlaskConical, Lightbulb, LineChart,
  Microscope, Sparkles, GitBranch, ThumbsUp, ThumbsDown, FileText,
  Play, Pause, RotateCcw
} from 'lucide-react'

const RD_AGENTS = [
  { id: 'oracle', name: 'ORACLE', role: 'Industry Analysis', color: 'from-blue-500 to-indigo-600', icon: LineChart, status: 'online', specialty: 'Market trends, competitor analysis, pricing intelligence', currentTask: 'Analyzing motorized shade market trends', progress: 80 },
  { id: 'edison', name: 'EDISON', role: 'Product Innovation', color: 'from-yellow-500 to-orange-600', icon: Lightbulb, status: 'online', specialty: 'New product ideas, feature development', currentTask: null, progress: 0 },
  { id: 'tensor', name: 'TENSOR', role: 'AI & Technology', color: 'from-purple-500 to-pink-600', icon: Cpu, status: 'online', specialty: 'AI/ML opportunities, automation, productivity', currentTask: 'Evaluating GPT-4 vision for measurements', progress: 45 },
  { id: 'spark', name: 'SPARK', role: 'Idea Evaluation', color: 'from-pink-500 to-rose-600', icon: Sparkles, status: 'online', specialty: 'Scoring ideas, ROI analysis, feasibility', currentTask: null, progress: 0 },
  { id: 'scout', name: 'SCOUT', role: 'Market Research', color: 'from-green-500 to-emerald-600', icon: Microscope, status: 'online', specialty: 'Competitor tracking, market opportunities', currentTask: 'Monitoring Shade Store pricing', progress: 60 },
]

const AGENTS = [
  { id: 'darwin', name: 'DARWIN', role: 'R&D Director', color: 'from-cyan-500 to-blue-600', status: 'online', isRDHead: true,
    projects: [
      { id: 'rd1', title: 'Motorized Shade Market Analysis', status: 'in_progress', priority: 'high', progress: 80, assignedTo: 'ORACLE' },
      { id: 'rd2', title: 'AI Vision Measurement Accuracy', status: 'in_progress', priority: 'high', progress: 45, assignedTo: 'TENSOR' },
      { id: 'rd3', title: 'Competitor Price Monitoring', status: 'in_progress', priority: 'medium', progress: 60, assignedTo: 'SCOUT' },
      { id: 'rd4', title: 'Commercial Spaces Vertical', status: 'pending_approval', priority: 'high', progress: 0, assignedTo: 'SPARK' },
    ],
    stats: { completed: 28, failed: 1, avgTime: '2.3 days' },
    recentReports: [
      { id: 'r1', title: 'Ripplefold Market Analysis', confidence: 98, date: '2026-02-22', summary: 'Growing 15% YoY, opportunity in luxury segment' },
      { id: 'r2', title: 'Somfy vs Lutron Comparison', confidence: 95, date: '2026-02-21', summary: 'Lutron premium justified, Somfy better value' },
    ]
  },
  { id: 'cleo', name: 'CLEO', role: 'Customer Service', color: 'from-pink-500 to-rose-600', status: 'online', projects: [{ id: 'p1', title: 'Quote for Azul Designs', status: 'in_progress', priority: 'high', progress: 65 }], stats: { completed: 45, failed: 2, avgTime: '4.2 min' } },
  { id: 'nova', name: 'NOVA', role: 'Analytics', color: 'from-violet-500 to-purple-600', status: 'online', projects: [{ id: 'p4', title: 'Daily Revenue Report', status: 'completed', priority: 'high', progress: 100 }], stats: { completed: 120, failed: 0, avgTime: '12.5 min' } },
  { id: 'iris', name: 'IRIS', role: 'Inventory', color: 'from-emerald-500 to-green-600', status: 'online', projects: [{ id: 'p6', title: 'Low Stock Alert', status: 'alert', priority: 'high', progress: 100 }], stats: { completed: 67, failed: 1, avgTime: '8.3 min' } },
  { id: 'atlas', name: 'ATLAS', role: 'Shipping', color: 'from-blue-500 to-cyan-600', status: 'online', projects: [{ id: 'p9', title: 'Ship Order #1042', status: 'in_progress', priority: 'high', progress: 70 }], stats: { completed: 89, failed: 3, avgTime: '2.1 min' } },
  { id: 'sage', name: 'SAGE', role: 'Finance', color: 'from-amber-500 to-yellow-600', status: 'online', projects: [{ id: 'p12', title: 'Q1 Tax Prep', status: 'in_progress', priority: 'high', progress: 35 }], stats: { completed: 34, failed: 0, avgTime: '15.7 min' } },
  { id: 'pixel', name: 'PIXEL', role: 'Design', color: 'from-fuchsia-500 to-pink-600', status: 'idle', projects: [], stats: { completed: 23, failed: 0, avgTime: '25.4 min' } },
  { id: 'forge', name: 'FORGE', role: 'Production', color: 'from-slate-500 to-gray-600', status: 'online', projects: [{ id: 'p17', title: 'Job #142 - Ripplefold', status: 'in_progress', priority: 'high', progress: 85 }], stats: { completed: 78, failed: 2, avgTime: '3.2 hrs' } },
]

const PENDING_APPROVALS = [
  { id: 'approval-1', type: 'delegation', from: 'MAX', title: 'Delegate commercial market research', description: 'Assign DARWIN team to research commercial window treatment market. ORACLE analyzes industry, SCOUT tracks competitors, SPARK evaluates ROI.', suggestedAgents: ['ORACLE', 'SCOUT', 'SPARK'], estimatedTime: '3-5 days', priority: 'high', createdAt: new Date(Date.now() - 3600000) },
  { id: 'approval-2', type: 'research', from: 'DARWIN', title: 'Smart Home Integration Opportunity', description: 'TENSOR identified growing market for smart home integrated treatments. Recommend developing Alexa/Google Home compatibility.', confidence: 87, potentialRevenue: '$50k-100k/year', investmentRequired: '$5k-10k', createdAt: new Date(Date.now() - 7200000) },
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
  const [stats, setStats] = useState({ revenue: 42500, openQuotes: 1, activeJobs: 3 })
  const [tasks, setTasks] = useState([
    { id: 1, text: 'Quote for Azul Designs', urgent: true, done: false },
    { id: 2, text: 'Follow up: Smith order', urgent: false, done: false },
    { id: 3, text: 'Order fabric from Rowley', urgent: false, done: false },
  ])
  const [activities] = useState([
    { id: 1, text: 'Payment $1,500 received', type: 'payment', time: '10 min ago' },
    { id: 2, text: 'New quote request - Azul Designs', type: 'quote', time: '25 min ago' },
    { id: 3, text: 'DARWIN: Research report ready', type: 'research', time: '1 hour ago' },
  ])
  const [currentTime, setCurrentTime] = useState(new Date())
  const [showAgentsPanel, setShowAgentsPanel] = useState(false)
  const [selectedAgent, setSelectedAgent] = useState<any>(null)
  const [showRDPanel, setShowRDPanel] = useState(false)
  const [selectedRDAgent, setSelectedRDAgent] = useState<any>(null)
  const [showApprovals, setShowApprovals] = useState(false)
  const [pendingApprovals, setPendingApprovals] = useState(PENDING_APPROVALS)
  const chatEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => { const t = setInterval(() => setCurrentTime(new Date()), 1000); return () => clearInterval(t) }, [])

  useEffect(() => {
    const hour = new Date().getHours()
    const greeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening'
    setTimeout(() => {
      setChatHistory([{ role: 'max', content: `${greeting}! I'm MAX, your Empire AI.\n\n📬 2 new quote requests\n💰 $1,500 payment received\n🔬 2 R&D items need approval\n\nWhat would you like to focus on?`, time: new Date() }])
    }, 300)
  }, [])

  const sendToMax = async () => {
    if (!inputValue.trim()) return
    const userMsg = inputValue.trim()
    setInputValue('')
    setChatHistory(h => [...h, { role: 'user', content: userMsg, time: new Date() }])
    setIsTyping(true)
    setTimeout(() => chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 100)
    
    setTimeout(() => {
      const response = getSmartResponse(userMsg)
      setChatHistory(h => [...h, { role: 'max', content: response, time: new Date() }])
      setIsTyping(false)
      setTimeout(() => chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 100)
    }, 1000)
  }

  const getSmartResponse = (msg: string): string => {
    const l = msg.toLowerCase()
    if (l.includes('research') || l.includes('r&d') || l.includes('darwin')) return "🔬 **R&D Update:**\n\n3 active projects:\n• Motorized Shade Market (80%)\n• AI Vision Accuracy (45%)\n• Competitor Monitoring (60%)\n\n📋 **Pending Approval:**\n• Commercial market research\n• Smart home opportunity\n\nClick **R&D Lab** for details."
    if (l.includes('approve')) return "📋 **2 items need your approval:**\n\n1. Delegate commercial research to DARWIN's team\n2. Smart Home Integration ($50-100k potential)\n\nClick **Approvals** button to review."
    if (l.includes('opportunity') || l.includes('money')) return "💡 **Opportunities from R&D:**\n\n1. **Commercial Spaces** - High potential\n2. **Smart Home Integration** - $50-100k\n3. **Luxury Segment** - 15% YoY growth\n\nWant me to prioritize any?"
    return "I'll analyze this. Click **R&D Lab** for research or **Agents** for operations."
  }

  const handleApproval = (id: string, approved: boolean) => {
    const approval = pendingApprovals.find(a => a.id === id)
    setPendingApprovals(prev => prev.filter(a => a.id !== id))
    if (approved && approval) {
      setChatHistory(h => [...h, { role: 'max', content: `✅ **Approved:** ${approval.title}\n\nDelegating to appropriate team. I'll report back with findings.`, time: new Date() }])
    }
  }

  const openApp = (port: number) => window.open(`http://localhost:${port}`, '_blank')
  const openMaxInterface = () => window.open('http://localhost:3009', '_blank')
  const toggleTask = (id: number) => setTasks(tasks.map(t => t.id === id ? { ...t, done: !t.done } : t))
  const getStatusColor = (s: string) => s === 'online' ? 'bg-green-500' : s === 'idle' ? 'bg-yellow-500' : 'bg-red-500'
  const getProjectStatusColor = (s: string) => ({ completed: 'bg-green-500/20 text-green-400', in_progress: 'bg-blue-500/20 text-blue-400', pending_approval: 'bg-purple-500/20 text-purple-400', alert: 'bg-red-500/20 text-red-400' }[s] || 'bg-gray-500/20 text-gray-400')
  const darwin = AGENTS.find(a => a.id === 'darwin')

  return (
    <div className="min-h-screen bg-[#0D0D0D] text-white">
      <header className="bg-[#1A1A1A] border-b border-gray-800 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="text-4xl">🏰</div>
            <div>
              <h1 className="text-2xl font-bold bg-gradient-to-r from-[#C9A84C] to-yellow-300 bg-clip-text text-transparent">EMPIRE CONTROL CENTER</h1>
              <p className="text-sm text-gray-500">Command your business empire</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-right mr-4 hidden md:block">
              <div className="text-xl font-mono text-[#C9A84C]">{currentTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>
              <div className="text-xs text-gray-500">{currentTime.toLocaleDateString([], { weekday: 'long', month: 'short', day: 'numeric' })}</div>
            </div>
            {pendingApprovals.length > 0 && (
              <button onClick={() => setShowApprovals(true)} className="flex items-center gap-2 bg-purple-500/20 hover:bg-purple-500/30 border border-purple-500/50 text-purple-400 rounded-lg px-3 py-2">
                <GitBranch className="w-4 h-4" /><span className="text-sm">Approvals</span>
                <span className="w-5 h-5 bg-purple-500 text-white rounded-full text-xs flex items-center justify-center">{pendingApprovals.length}</span>
              </button>
            )}
            <button className="relative p-2 text-gray-400 hover:text-white"><Bell className="w-5 h-5" /><span className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 rounded-full text-xs flex items-center justify-center">3</span></button>
            <button className="p-2 text-gray-400 hover:text-white"><Settings className="w-5 h-5" /></button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto p-6">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div className="lg:col-span-5">
            <div className="bg-[#1A1A1A] rounded-2xl border border-gray-800 overflow-hidden h-[650px] flex flex-col">
              <div className="bg-gradient-to-r from-[#C9A84C]/20 to-amber-500/10 px-5 py-4 border-b border-gray-800">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <button onClick={openMaxInterface} className="w-14 h-14 rounded-full bg-gradient-to-br from-[#C9A84C] to-amber-600 flex items-center justify-center hover:scale-110 transition-transform cursor-pointer group relative" title="Open MAX Interface">
                      <Brain className="w-7 h-7 text-[#0D0D0D]" />
                      <div className="absolute -bottom-1 -right-1 w-5 h-5 bg-blue-500 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition"><ExternalLink className="w-3 h-3 text-white" /></div>
                    </button>
                    <div>
                      <h2 className="font-bold text-xl flex items-center gap-2">MAX<span className="text-xs bg-green-500/20 text-green-400 px-2 py-0.5 rounded-full">Online</span></h2>
                      <p className="text-sm text-gray-400">Your AI Business Assistant</p>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button onClick={() => setShowRDPanel(true)} className="flex items-center gap-2 bg-cyan-500/20 hover:bg-cyan-500/30 border border-cyan-500/50 text-cyan-400 rounded-xl px-3 py-2"><FlaskConical className="w-4 h-4" /><span className="text-sm">R&D Lab</span></button>
                    <button onClick={() => setShowAgentsPanel(true)} className="flex items-center gap-2 bg-[#2C2C2C] hover:bg-[#3C3C3C] border border-gray-700 rounded-xl px-3 py-2"><Cpu className="w-4 h-4 text-[#C9A84C]" /><span className="text-sm">Agents</span><span className="w-5 h-5 bg-green-500/20 text-green-400 rounded-full text-xs flex items-center justify-center">8</span></button>
                  </div>
                </div>
              </div>
              <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {chatHistory.map((msg, i) => (
                  <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-[90%] rounded-2xl px-4 py-3 ${msg.role === 'user' ? 'bg-[#C9A84C] text-[#0D0D0D]' : 'bg-[#2C2C2C]'}`}>
                      <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                      <p className={`text-xs mt-2 ${msg.role === 'user' ? 'text-[#0D0D0D]/50' : 'text-gray-500'}`}>{msg.time.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</p>
                    </div>
                  </div>
                ))}
                {isTyping && <div className="flex justify-start"><div className="bg-[#2C2C2C] rounded-2xl px-4 py-3"><div className="flex gap-1"><span className="w-2 h-2 bg-[#C9A84C] rounded-full animate-bounce" /><span className="w-2 h-2 bg-[#C9A84C] rounded-full animate-bounce" style={{animationDelay:'150ms'}} /><span className="w-2 h-2 bg-[#C9A84C] rounded-full animate-bounce" style={{animationDelay:'300ms'}} /></div></div></div>}
                <div ref={chatEndRef} />
              </div>
              <div className="p-4 border-t border-gray-800">
                <div className="flex gap-2">
                  <input type="text" value={inputValue} onChange={(e) => setInputValue(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && sendToMax()} placeholder="Ask MAX anything..." className="flex-1 bg-[#2C2C2C] border border-gray-700 rounded-xl px-4 py-3 focus:border-[#C9A84C] outline-none" />
                  <button onClick={sendToMax} disabled={!inputValue.trim()} className="bg-[#C9A84C] hover:bg-[#B8973F] disabled:opacity-50 text-[#0D0D0D] px-5 rounded-xl font-semibold"><Send className="w-5 h-5" /></button>
                </div>
                <div className="flex gap-2 mt-3">{['🔬 R&D', '💡 Opportunities', '📊 Stats'].map(btn => (<button key={btn} onClick={() => setInputValue(btn.split(' ')[1])} className="text-xs bg-[#2C2C2C] hover:bg-[#3C3C3C] px-3 py-1.5 rounded-lg text-gray-400 hover:text-white">{btn}</button>))}</div>
              </div>
            </div>
          </div>

          <div className="lg:col-span-7 space-y-6">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[{ label: 'Revenue MTD', value: `$${(stats.revenue/1000).toFixed(1)}k`, icon: TrendingUp, color: 'text-green-400', change: '+12%' },
                { label: 'Open Quotes', value: stats.openQuotes, icon: MessageSquare, color: 'text-yellow-400' },
                { label: 'Active Jobs', value: stats.activeJobs, icon: Factory, color: 'text-blue-400' },
                { label: 'R&D Projects', value: darwin?.projects.length || 0, icon: FlaskConical, color: 'text-cyan-400' }
              ].map((stat, i) => (
                <div key={i} className="bg-[#1A1A1A] rounded-xl p-4 border border-gray-800 hover:border-gray-700 cursor-pointer" onClick={() => i === 3 && setShowRDPanel(true)}>
                  <div className="flex items-center justify-between mb-2"><stat.icon className={`w-5 h-5 ${stat.color}`} />{stat.change && <span className="text-xs text-green-400">{stat.change}</span>}</div>
                  <p className="text-2xl font-bold">{stat.value}</p><p className="text-xs text-gray-500">{stat.label}</p>
                </div>
              ))}
            </div>

            <div className="bg-[#1A1A1A] rounded-2xl p-5 border border-gray-800">
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2"><Zap className="w-5 h-5 text-[#C9A84C]" />Quick Launch</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {APPS.map(app => (
                  <button key={app.id} onClick={() => openApp(app.port)} className="group relative bg-[#2C2C2C] hover:bg-[#3C3C3C] rounded-xl p-4 text-left border border-gray-700 hover:border-gray-600">
                    <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${app.color} flex items-center justify-center mb-3 group-hover:scale-110 transition`}><app.icon className="w-6 h-6 text-white" /></div>
                    <p className="font-semibold text-sm">{app.name}</p><p className="text-xs text-gray-500">{app.desc}</p>
                    {app.badge > 0 && <span className="absolute top-3 right-3 w-5 h-5 bg-red-500 rounded-full text-xs flex items-center justify-center">{app.badge}</span>}
                  </button>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="bg-[#1A1A1A] rounded-2xl p-5 border border-gray-800">
                <div className="flex items-center justify-between mb-4"><h3 className="font-semibold flex items-center gap-2"><CheckCircle className="w-5 h-5 text-[#C9A84C]" />Today's Tasks</h3><span className="text-xs text-gray-500">{tasks.filter(t => !t.done).length} left</span></div>
                <div className="space-y-2">{tasks.map(task => (
                  <div key={task.id} onClick={() => toggleTask(task.id)} className={`flex items-center gap-3 p-3 rounded-lg cursor-pointer ${task.done ? 'bg-[#2C2C2C]/50 opacity-60' : 'bg-[#2C2C2C] hover:bg-[#3C3C3C]'}`}>
                    <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center ${task.done ? 'bg-green-500 border-green-500' : task.urgent ? 'border-red-400' : 'border-gray-600'}`}>{task.done && <CheckCircle className="w-3 h-3 text-white" />}</div>
                    <span className={`flex-1 text-sm ${task.done ? 'line-through text-gray-500' : ''}`}>{task.text}</span>
                    {task.urgent && !task.done && <span className="text-xs bg-red-500/20 text-red-400 px-2 py-0.5 rounded">!</span>}
                  </div>
                ))}</div>
              </div>
              <div className="bg-[#1A1A1A] rounded-2xl p-5 border border-gray-800">
                <div className="flex items-center justify-between mb-4"><h3 className="font-semibold flex items-center gap-2"><Bell className="w-5 h-5 text-[#C9A84C]" />Recent Activity</h3></div>
                <div className="space-y-3">{activities.map(a => (
                  <div key={a.id} className="flex items-start gap-3 p-3 rounded-lg bg-[#2C2C2C]/50">
                    {a.type === 'payment' ? <DollarSign className="w-4 h-4 text-green-400" /> : a.type === 'research' ? <FlaskConical className="w-4 h-4 text-cyan-400" /> : <MessageSquare className="w-4 h-4 text-blue-400" />}
                    <div><p className="text-sm">{a.text}</p><p className="text-xs text-gray-500 mt-1"><Clock className="w-3 h-3 inline mr-1" />{a.time}</p></div>
                  </div>
                ))}</div>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* R&D Panel */}
      {showRDPanel && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <div className="absolute inset-0 bg-black/60" onClick={() => { setShowRDPanel(false); setSelectedRDAgent(null) }} />
          <div className="relative w-full max-w-lg bg-[#1A1A1A] border-l border-gray-800 overflow-y-auto">
            <div className="px-6 py-4 border-b border-gray-800 flex items-center justify-between bg-gradient-to-r from-cyan-500/10 to-blue-500/10 sticky top-0">
              <div className="flex items-center gap-3"><FlaskConical className="w-6 h-6 text-cyan-400" /><div><h2 className="font-bold text-lg">R&D Lab</h2><p className="text-xs text-gray-500">DARWIN's Research Division</p></div></div>
              <button onClick={() => { setShowRDPanel(false); setSelectedRDAgent(null) }} className="p-2 hover:bg-[#2C2C2C] rounded-lg"><X className="w-5 h-5" /></button>
            </div>
            <div className="p-4">
              {!selectedRDAgent ? (
                <>
                  <div className="bg-gradient-to-br from-cyan-500/20 to-blue-500/20 rounded-xl p-4 mb-4">
                    <div className="flex items-center gap-3 mb-3">
                      <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center"><span className="text-xl font-bold">D</span></div>
                      <div><h3 className="font-bold flex items-center gap-2">DARWIN<span className="w-2 h-2 rounded-full bg-green-500" /></h3><p className="text-sm text-gray-400">R&D Director → Reports to MAX → Reports to YOU</p></div>
                    </div>
                    <div className="grid grid-cols-3 gap-2 text-center">
                      <div className="bg-black/20 rounded-lg p-2"><p className="text-lg font-bold text-green-400">{darwin?.stats.completed}</p><p className="text-xs text-gray-500">Done</p></div>
                      <div className="bg-black/20 rounded-lg p-2"><p className="text-lg font-bold text-blue-400">5</p><p className="text-xs text-gray-500">Agents</p></div>
                      <div className="bg-black/20 rounded-lg p-2"><p className="text-lg font-bold text-cyan-400">{darwin?.projects.length}</p><p className="text-xs text-gray-500">Active</p></div>
                    </div>
                  </div>
                  <h4 className="font-semibold text-sm text-gray-400 uppercase mb-3">Research Specialists</h4>
                  <div className="space-y-2 mb-6">
                    {RD_AGENTS.map(agent => (
                      <button key={agent.id} onClick={() => setSelectedRDAgent(agent)} className="w-full bg-[#2C2C2C] hover:bg-[#3C3C3C] rounded-xl p-4 text-left flex items-center gap-3">
                        <div className={`w-10 h-10 rounded-lg bg-gradient-to-br ${agent.color} flex items-center justify-center`}><agent.icon className="w-5 h-5 text-white" /></div>
                        <div className="flex-1"><div className="flex items-center gap-2"><span className="font-bold text-sm">{agent.name}</span><div className={`w-2 h-2 rounded-full ${getStatusColor(agent.status)}`} /></div><p className="text-xs text-gray-400">{agent.role}</p></div>
                        {agent.currentTask && <div className="text-right"><p className="text-xs text-cyan-400">{agent.progress}%</p><div className="w-16 h-1 bg-[#1A1A1A] rounded-full mt-1"><div className="h-full bg-cyan-500 rounded-full" style={{width:`${agent.progress}%`}} /></div></div>}
                        <ChevronRight className="w-4 h-4 text-gray-600" />
                      </button>
                    ))}
                  </div>
                  <h4 className="font-semibold text-sm text-gray-400 uppercase mb-3">Active Research</h4>
                  <div className="space-y-2 mb-6">
                    {darwin?.projects.map(p => (
                      <div key={p.id} className="bg-[#2C2C2C] rounded-xl p-4">
                        <div className="flex items-start justify-between mb-2"><h5 className="font-semibold text-sm">{p.title}</h5><span className={`text-xs px-2 py-0.5 rounded ${getProjectStatusColor(p.status)}`}>{p.status.replace('_',' ')}</span></div>
                        <p className="text-xs text-gray-500 mb-2">Assigned: <span className="text-cyan-400">{p.assignedTo}</span></p>
                        <div className="h-1.5 bg-[#1A1A1A] rounded-full"><div className="h-full bg-cyan-500 rounded-full" style={{width:`${p.progress}%`}} /></div>
                      </div>
                    ))}
                  </div>
                  <h4 className="font-semibold text-sm text-gray-400 uppercase mb-3">Recent Reports</h4>
                  <div className="space-y-2">
                    {darwin?.recentReports?.map(r => (
                      <div key={r.id} className="bg-[#2C2C2C] rounded-xl p-4">
                        <div className="flex items-start gap-3"><FileText className="w-5 h-5 text-cyan-400 flex-shrink-0" /><div><h5 className="font-semibold text-sm">{r.title}</h5><p className="text-xs text-gray-500 mt-1">{r.summary}</p><p className="text-xs text-green-400 mt-1">{r.confidence}% confidence • {r.date}</p></div></div>
                      </div>
                    ))}
                  </div>
                </>
              ) : (
                <div>
                  <button onClick={() => setSelectedRDAgent(null)} className="text-sm text-gray-400 hover:text-white mb-4">← Back</button>
                  <div className={`bg-gradient-to-br ${selectedRDAgent.color} bg-opacity-20 rounded-xl p-4 mb-4`}>
                    <div className="flex items-center gap-4">
                      <div className={`w-16 h-16 rounded-2xl bg-gradient-to-br ${selectedRDAgent.color} flex items-center justify-center`}><selectedRDAgent.icon className="w-8 h-8 text-white" /></div>
                      <div><h3 className="text-xl font-bold flex items-center gap-2">{selectedRDAgent.name}<div className={`w-2 h-2 rounded-full ${getStatusColor(selectedRDAgent.status)}`} /></h3><p className="text-gray-400">{selectedRDAgent.role}</p><p className="text-xs text-gray-500">Reports to: DARWIN</p></div>
                    </div>
                  </div>
                  <div className="bg-[#2C2C2C] rounded-xl p-4 mb-4"><h4 className="font-semibold text-sm mb-2">Specialty</h4><p className="text-sm text-gray-400">{selectedRDAgent.specialty}</p></div>
                  {selectedRDAgent.currentTask ? (
                    <div className="bg-[#2C2C2C] rounded-xl p-4">
                      <h4 className="font-semibold text-sm mb-2 flex items-center gap-2"><Play className="w-4 h-4 text-green-400" />Current Task</h4>
                      <p className="text-sm">{selectedRDAgent.currentTask}</p>
                      <div className="mt-3"><div className="flex justify-between text-xs mb-1"><span className="text-gray-500">Progress</span><span className="text-cyan-400">{selectedRDAgent.progress}%</span></div><div className="h-2 bg-[#1A1A1A] rounded-full"><div className="h-full bg-cyan-500 rounded-full" style={{width:`${selectedRDAgent.progress}%`}} /></div></div>
                      <div className="flex gap-2 mt-4"><button className="flex-1 bg-yellow-500/20 text-yellow-400 py-2 rounded-lg text-sm flex items-center justify-center gap-2"><Pause className="w-4 h-4" />Pause</button><button className="flex-1 bg-red-500/20 text-red-400 py-2 rounded-lg text-sm flex items-center justify-center gap-2"><RotateCcw className="w-4 h-4" />Reset</button></div>
                    </div>
                  ) : (
                    <div className="bg-[#2C2C2C] rounded-xl p-4 text-center"><p className="text-gray-500 text-sm">No active task</p><button className="mt-3 bg-cyan-500 hover:bg-cyan-600 text-white px-4 py-2 rounded-lg text-sm">Assign Task</button></div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Approvals Modal */}
      {showApprovals && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/70" onClick={() => setShowApprovals(false)} />
          <div className="relative bg-[#1A1A1A] rounded-2xl border border-gray-800 w-full max-w-xl overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-800 flex items-center justify-between bg-gradient-to-r from-purple-500/10 to-pink-500/10">
              <div className="flex items-center gap-3"><GitBranch className="w-6 h-6 text-purple-400" /><div><h2 className="font-bold text-lg">Pending Approvals</h2><p className="text-xs text-gray-500">MAX needs your decision</p></div></div>
              <button onClick={() => setShowApprovals(false)} className="p-2 hover:bg-[#2C2C2C] rounded-lg"><X className="w-5 h-5" /></button>
            </div>
            <div className="max-h-[60vh] overflow-y-auto p-4 space-y-4">
              {pendingApprovals.length === 0 ? (
                <div className="text-center py-8 text-gray-500"><CheckCircle className="w-12 h-12 mx-auto mb-3 opacity-30" /><p>All caught up!</p></div>
              ) : pendingApprovals.map(a => (
                <div key={a.id} className="bg-[#2C2C2C] rounded-xl p-5 border border-gray-700">
                  <span className={`text-xs px-2 py-0.5 rounded ${a.type === 'delegation' ? 'bg-blue-500/20 text-blue-400' : 'bg-green-500/20 text-green-400'}`}>{a.type === 'delegation' ? 'Delegation' : 'Research'}</span>
                  <h3 className="font-bold mt-2">{a.title}</h3>
                  <p className="text-xs text-gray-500">From: {a.from}</p>
                  <p className="text-sm text-gray-300 my-3">{a.description}</p>
                  {a.suggestedAgents && <div className="flex flex-wrap gap-2 mb-3">{a.suggestedAgents.map(ag => <span key={ag} className="text-xs bg-[#1A1A1A] px-2 py-1 rounded">🤖 {ag}</span>)}<span className="text-xs text-gray-500">• {a.estimatedTime}</span></div>}
                  {a.potentialRevenue && <div className="grid grid-cols-2 gap-3 mb-4"><div className="bg-[#1A1A1A] rounded-lg p-3"><p className="text-xs text-gray-500">Confidence</p><p className="font-bold text-green-400">{a.confidence}%</p></div><div className="bg-[#1A1A1A] rounded-lg p-3"><p className="text-xs text-gray-500">Potential</p><p className="font-bold text-[#C9A84C]">{a.potentialRevenue}</p></div></div>}
                  <div className="flex gap-3">
                    <button onClick={() => handleApproval(a.id, true)} className="flex-1 bg-green-500 hover:bg-green-600 text-white font-semibold py-3 rounded-xl flex items-center justify-center gap-2"><ThumbsUp className="w-4 h-4" />Approve</button>
                    <button onClick={() => handleApproval(a.id, false)} className="flex-1 bg-[#3C3C3C] hover:bg-[#4C4C4C] py-3 rounded-xl flex items-center justify-center gap-2"><ThumbsDown className="w-4 h-4" />Decline</button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Agents Panel */}
      {showAgentsPanel && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <div className="absolute inset-0 bg-black/60" onClick={() => { setShowAgentsPanel(false); setSelectedAgent(null) }} />
          <div className="relative w-full max-w-md bg-[#1A1A1A] border-l border-gray-800 overflow-y-auto">
            <div className="px-6 py-4 border-b border-gray-800 flex items-center justify-between bg-gradient-to-r from-[#C9A84C]/10 to-transparent sticky top-0">
              <div className="flex items-center gap-3"><Cpu className="w-6 h-6 text-[#C9A84C]" /><div><h2 className="font-bold text-lg">AI Agents</h2><p className="text-xs text-gray-500">8 agents online</p></div></div>
              <button onClick={() => { setShowAgentsPanel(false); setSelectedAgent(null) }} className="p-2 hover:bg-[#2C2C2C] rounded-lg"><X className="w-5 h-5" /></button>
            </div>
            <div className="p-4 space-y-2">
              {AGENTS.map(agent => (
                <button key={agent.id} onClick={() => agent.isRDHead ? (setShowAgentsPanel(false), setShowRDPanel(true)) : setSelectedAgent(agent)} className={`w-full bg-[#2C2C2C] hover:bg-[#3C3C3C] rounded-xl p-4 text-left flex items-center gap-4 ${agent.isRDHead ? 'border border-cyan-500/30' : ''}`}>
                  <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${agent.color} flex items-center justify-center`}><span className="text-lg font-bold">{agent.name[0]}</span></div>
                  <div className="flex-1"><div className="flex items-center gap-2"><span className="font-bold">{agent.name}</span><div className={`w-2 h-2 rounded-full ${getStatusColor(agent.status)}`} />{agent.isRDHead && <span className="text-xs bg-cyan-500/20 text-cyan-400 px-2 py-0.5 rounded">R&D</span>}</div><p className="text-sm text-gray-400">{agent.role}</p></div>
                  <ChevronRight className="w-5 h-5 text-gray-600" />
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      <style jsx>{`@keyframes slide-in{from{transform:translateX(100%)}to{transform:translateX(0)}}.animate-slide-in{animation:slide-in .3s ease-out}`}</style>
    </div>
  )
}
