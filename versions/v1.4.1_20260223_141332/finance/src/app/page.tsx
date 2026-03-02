'use client'
import { useState } from 'react'
import {
  DollarSign, TrendingUp, TrendingDown, CreditCard, Receipt, FileText,
  PieChart, BarChart3, Calendar, Clock, CheckCircle, AlertTriangle,
  Plus, Search, Filter, Download, Send, Eye, Edit, Trash2, X,
  ArrowUpRight, ArrowDownRight, Building2, User, ChevronRight
} from 'lucide-react'

// Sample financial data
const INVOICES = [
  { id: 'INV-2851', customer: 'Azul Designs', amount: 4500, status: 'paid', date: '2026-02-22', dueDate: '2026-03-22', items: 'Ripplefold Drapes x4' },
  { id: 'INV-2850', customer: 'Johnson Design Co.', amount: 8500, status: 'pending', date: '2026-02-20', dueDate: '2026-03-20', items: 'Office Blinds x20' },
  { id: 'INV-2849', customer: 'Smith Residence', amount: 3200, status: 'paid', date: '2026-02-18', dueDate: '2026-03-18', items: 'Living Room Drapes' },
  { id: 'INV-2848', customer: 'Luxury Interiors', amount: 12400, status: 'overdue', date: '2026-01-15', dueDate: '2026-02-15', items: 'Full Home Package' },
  { id: 'INV-2847', customer: 'Metro Hotels', amount: 28500, status: 'pending', date: '2026-02-10', dueDate: '2026-03-10', items: 'Hotel Room Blinds x50' },
  { id: 'INV-2846', customer: 'Chen Residence', amount: 2100, status: 'paid', date: '2026-02-05', dueDate: '2026-03-05', items: 'Bedroom Shades x2' },
]

const EXPENSES = [
  { id: 'EXP-501', vendor: 'Rowley Company', amount: 3200, category: 'Materials', date: '2026-02-21', description: 'Fabric order - blackout lining' },
  { id: 'EXP-500', vendor: 'Somfy', amount: 1850, category: 'Hardware', date: '2026-02-19', description: 'Motorization units x5' },
  { id: 'EXP-499', vendor: 'Office Depot', amount: 245, category: 'Office', date: '2026-02-18', description: 'Printer supplies' },
  { id: 'EXP-498', vendor: 'UPS', amount: 380, category: 'Shipping', date: '2026-02-17', description: 'Monthly shipping' },
  { id: 'EXP-497', vendor: 'AWS', amount: 89, category: 'Software', date: '2026-02-15', description: 'Cloud hosting' },
]

const TRANSACTIONS = [
  { id: 'TXN-1001', type: 'income', description: 'Payment from Azul Designs', amount: 4500, date: '2026-02-22', category: 'Sales' },
  { id: 'TXN-1002', type: 'expense', description: 'Rowley fabric order', amount: 3200, date: '2026-02-21', category: 'Materials' },
  { id: 'TXN-1003', type: 'income', description: 'Payment from Smith', amount: 3200, date: '2026-02-20', category: 'Sales' },
  { id: 'TXN-1004', type: 'expense', description: 'Somfy motors', amount: 1850, date: '2026-02-19', category: 'Hardware' },
  { id: 'TXN-1005', type: 'income', description: 'Payment from Chen', amount: 2100, date: '2026-02-18', category: 'Sales' },
]

const MONTHLY_DATA = [
  { month: 'Sep', revenue: 32000, expenses: 18000 },
  { month: 'Oct', revenue: 38000, expenses: 21000 },
  { month: 'Nov', revenue: 35000, expenses: 19000 },
  { month: 'Dec', revenue: 42000, expenses: 24000 },
  { month: 'Jan', revenue: 48000, expenses: 26000 },
  { month: 'Feb', revenue: 52000, expenses: 28000 },
]

export default function FinancePage() {
  const [activeTab, setActiveTab] = useState<'overview' | 'invoices' | 'expenses' | 'reports'>('overview')
  const [showNewInvoice, setShowNewInvoice] = useState(false)
  const [showNewExpense, setShowNewExpense] = useState(false)
  const [selectedInvoice, setSelectedInvoice] = useState<typeof INVOICES[0] | null>(null)
  const [invoiceFilter, setInvoiceFilter] = useState('all')

  const totalRevenue = 52000
  const totalExpenses = 28000
  const netProfit = totalRevenue - totalExpenses
  const pendingInvoices = INVOICES.filter(i => i.status === 'pending').reduce((sum, i) => sum + i.amount, 0)
  const overdueInvoices = INVOICES.filter(i => i.status === 'overdue').reduce((sum, i) => sum + i.amount, 0)

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      paid: 'bg-green-500/20 text-green-400',
      pending: 'bg-yellow-500/20 text-yellow-400',
      overdue: 'bg-red-500/20 text-red-400',
      draft: 'bg-gray-500/20 text-gray-400',
    }
    return colors[status] || 'bg-gray-500/20 text-gray-400'
  }

  const filteredInvoices = INVOICES.filter(i => invoiceFilter === 'all' || i.status === invoiceFilter)

  return (
    <div className="min-h-screen bg-[#0D0D0D] text-white">
      {/* Header */}
      <header className="bg-[#1A1A1A] border-b border-gray-800 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-yellow-500 to-amber-600 flex items-center justify-center">
              <DollarSign className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold">Empire Finance</h1>
              <p className="text-sm text-gray-500">Financial Management & Reporting</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button onClick={() => setShowNewExpense(true)} className="flex items-center gap-2 bg-[#2C2C2C] hover:bg-[#3C3C3C] px-4 py-2 rounded-xl transition">
              <Receipt className="w-4 h-4" /> Add Expense
            </button>
            <button onClick={() => setShowNewInvoice(true)} className="flex items-center gap-2 bg-[#C9A84C] hover:bg-[#B8973F] text-[#0D0D0D] px-4 py-2 rounded-xl font-semibold transition">
              <FileText className="w-4 h-4" /> New Invoice
            </button>
          </div>
        </div>
      </header>

      {/* Tabs */}
      <div className="bg-[#1A1A1A] border-b border-gray-800">
        <div className="max-w-7xl mx-auto flex">
          {(['overview', 'invoices', 'expenses', 'reports'] as const).map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-6 py-3 text-sm font-medium transition ${
                activeTab === tab ? 'text-[#C9A84C] border-b-2 border-[#C9A84C]' : 'text-gray-400 hover:text-white'
              }`}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>
      </div>

      <main className="max-w-7xl mx-auto p-6">
        {activeTab === 'overview' && (
          <div className="space-y-6">
            {/* Stats Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-[#1A1A1A] rounded-xl p-5 border border-gray-800">
                <div className="flex items-center justify-between mb-3">
                  <TrendingUp className="w-5 h-5 text-green-400" />
                  <span className="text-xs text-green-400 flex items-center gap-1"><ArrowUpRight className="w-3 h-3" /> +18%</span>
                </div>
                <p className="text-2xl font-bold">${totalRevenue.toLocaleString()}</p>
                <p className="text-sm text-gray-500">Revenue MTD</p>
              </div>
              <div className="bg-[#1A1A1A] rounded-xl p-5 border border-gray-800">
                <div className="flex items-center justify-between mb-3">
                  <TrendingDown className="w-5 h-5 text-red-400" />
                  <span className="text-xs text-red-400 flex items-center gap-1"><ArrowDownRight className="w-3 h-3" /> +12%</span>
                </div>
                <p className="text-2xl font-bold">${totalExpenses.toLocaleString()}</p>
                <p className="text-sm text-gray-500">Expenses MTD</p>
              </div>
              <div className="bg-[#1A1A1A] rounded-xl p-5 border border-gray-800">
                <div className="flex items-center justify-between mb-3">
                  <DollarSign className="w-5 h-5 text-[#C9A84C]" />
                </div>
                <p className="text-2xl font-bold text-green-400">${netProfit.toLocaleString()}</p>
                <p className="text-sm text-gray-500">Net Profit</p>
              </div>
              <div className="bg-[#1A1A1A] rounded-xl p-5 border border-gray-800">
                <div className="flex items-center justify-between mb-3">
                  <Clock className="w-5 h-5 text-yellow-400" />
                  {overdueInvoices > 0 && <span className="text-xs text-red-400">${overdueInvoices.toLocaleString()} overdue</span>}
                </div>
                <p className="text-2xl font-bold">${pendingInvoices.toLocaleString()}</p>
                <p className="text-sm text-gray-500">Pending Invoices</p>
              </div>
            </div>

            {/* Charts Row */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Revenue Chart */}
              <div className="bg-[#1A1A1A] rounded-xl p-5 border border-gray-800">
                <h3 className="font-semibold mb-4 flex items-center gap-2">
                  <BarChart3 className="w-5 h-5 text-[#C9A84C]" /> Revenue vs Expenses
                </h3>
                <div className="h-48 flex items-end justify-between gap-2">
                  {MONTHLY_DATA.map((data, i) => (
                    <div key={i} className="flex-1 flex flex-col items-center gap-1">
                      <div className="w-full flex gap-1 items-end h-36">
                        <div className="flex-1 bg-green-500/60 rounded-t" style={{ height: `${(data.revenue / 60000) * 100}%` }} />
                        <div className="flex-1 bg-red-500/60 rounded-t" style={{ height: `${(data.expenses / 60000) * 100}%` }} />
                      </div>
                      <span className="text-xs text-gray-500">{data.month}</span>
                    </div>
                  ))}
                </div>
                <div className="flex items-center justify-center gap-6 mt-4 text-xs">
                  <span className="flex items-center gap-2"><span className="w-3 h-3 bg-green-500/60 rounded" /> Revenue</span>
                  <span className="flex items-center gap-2"><span className="w-3 h-3 bg-red-500/60 rounded" /> Expenses</span>
                </div>
              </div>

              {/* Expense Breakdown */}
              <div className="bg-[#1A1A1A] rounded-xl p-5 border border-gray-800">
                <h3 className="font-semibold mb-4 flex items-center gap-2">
                  <PieChart className="w-5 h-5 text-[#C9A84C]" /> Expense Breakdown
                </h3>
                <div className="space-y-3">
                  {[
                    { category: 'Materials', amount: 12500, percent: 45, color: 'bg-blue-500' },
                    { category: 'Hardware', amount: 6200, percent: 22, color: 'bg-purple-500' },
                    { category: 'Shipping', amount: 4100, percent: 15, color: 'bg-yellow-500' },
                    { category: 'Labor', amount: 3500, percent: 12, color: 'bg-green-500' },
                    { category: 'Other', amount: 1700, percent: 6, color: 'bg-gray-500' },
                  ].map((item, i) => (
                    <div key={i}>
                      <div className="flex items-center justify-between text-sm mb-1">
                        <span>{item.category}</span>
                        <span className="text-gray-400">${item.amount.toLocaleString()} ({item.percent}%)</span>
                      </div>
                      <div className="h-2 bg-[#2C2C2C] rounded-full overflow-hidden">
                        <div className={`h-full ${item.color} rounded-full`} style={{ width: `${item.percent}%` }} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Recent Transactions */}
            <div className="bg-[#1A1A1A] rounded-xl border border-gray-800 overflow-hidden">
              <div className="px-5 py-4 border-b border-gray-800 flex items-center justify-between">
                <h3 className="font-semibold flex items-center gap-2">
                  <CreditCard className="w-5 h-5 text-[#C9A84C]" /> Recent Transactions
                </h3>
                <button className="text-sm text-[#C9A84C] hover:underline">View All</button>
              </div>
              <div className="divide-y divide-gray-800">
                {TRANSACTIONS.map(txn => (
                  <div key={txn.id} className="px-5 py-3 flex items-center justify-between hover:bg-[#2C2C2C]/50">
                    <div className="flex items-center gap-3">
                      <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                        txn.type === 'income' ? 'bg-green-500/20' : 'bg-red-500/20'
                      }`}>
                        {txn.type === 'income' ? (
                          <ArrowDownRight className="w-5 h-5 text-green-400" />
                        ) : (
                          <ArrowUpRight className="w-5 h-5 text-red-400" />
                        )}
                      </div>
                      <div>
                        <p className="font-medium text-sm">{txn.description}</p>
                        <p className="text-xs text-gray-500">{txn.date} • {txn.category}</p>
                      </div>
                    </div>
                    <span className={`font-semibold ${txn.type === 'income' ? 'text-green-400' : 'text-red-400'}`}>
                      {txn.type === 'income' ? '+' : '-'}${txn.amount.toLocaleString()}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'invoices' && (
          <div className="space-y-4">
            {/* Filters */}
            <div className="flex items-center justify-between">
              <div className="flex gap-2">
                {['all', 'pending', 'paid', 'overdue'].map(filter => (
                  <button
                    key={filter}
                    onClick={() => setInvoiceFilter(filter)}
                    className={`px-4 py-2 rounded-lg text-sm transition ${
                      invoiceFilter === filter ? 'bg-[#C9A84C] text-[#0D0D0D]' : 'bg-[#2C2C2C] hover:bg-[#3C3C3C]'
                    }`}
                  >
                    {filter.charAt(0).toUpperCase() + filter.slice(1)}
                  </button>
                ))}
              </div>
              <button className="flex items-center gap-2 text-sm text-gray-400 hover:text-white">
                <Download className="w-4 h-4" /> Export
              </button>
            </div>

            {/* Invoice List */}
            <div className="bg-[#1A1A1A] rounded-xl border border-gray-800 overflow-hidden">
              <table className="w-full">
                <thead className="bg-[#2C2C2C]">
                  <tr>
                    <th className="px-5 py-3 text-left text-xs text-gray-400 font-medium">Invoice</th>
                    <th className="px-5 py-3 text-left text-xs text-gray-400 font-medium">Customer</th>
                    <th className="px-5 py-3 text-left text-xs text-gray-400 font-medium">Amount</th>
                    <th className="px-5 py-3 text-left text-xs text-gray-400 font-medium">Status</th>
                    <th className="px-5 py-3 text-left text-xs text-gray-400 font-medium">Due Date</th>
                    <th className="px-5 py-3 text-right text-xs text-gray-400 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800">
                  {filteredInvoices.map(invoice => (
                    <tr key={invoice.id} className="hover:bg-[#2C2C2C]/50">
                      <td className="px-5 py-4">
                        <span className="font-mono text-sm">{invoice.id}</span>
                      </td>
                      <td className="px-5 py-4">
                        <p className="font-medium">{invoice.customer}</p>
                        <p className="text-xs text-gray-500">{invoice.items}</p>
                      </td>
                      <td className="px-5 py-4 font-semibold">${invoice.amount.toLocaleString()}</td>
                      <td className="px-5 py-4">
                        <span className={`text-xs px-2 py-1 rounded ${getStatusColor(invoice.status)}`}>
                          {invoice.status}
                        </span>
                      </td>
                      <td className="px-5 py-4 text-sm text-gray-400">{invoice.dueDate}</td>
                      <td className="px-5 py-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button className="p-1.5 hover:bg-[#3C3C3C] rounded" title="View"><Eye className="w-4 h-4" /></button>
                          <button className="p-1.5 hover:bg-[#3C3C3C] rounded" title="Send"><Send className="w-4 h-4" /></button>
                          <button className="p-1.5 hover:bg-[#3C3C3C] rounded" title="Edit"><Edit className="w-4 h-4" /></button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeTab === 'expenses' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold">Expense Tracking</h2>
              <button onClick={() => setShowNewExpense(true)} className="flex items-center gap-2 bg-[#C9A84C] hover:bg-[#B8973F] text-[#0D0D0D] px-4 py-2 rounded-xl font-semibold">
                <Plus className="w-4 h-4" /> Add Expense
              </button>
            </div>

            <div className="bg-[#1A1A1A] rounded-xl border border-gray-800 overflow-hidden">
              <table className="w-full">
                <thead className="bg-[#2C2C2C]">
                  <tr>
                    <th className="px-5 py-3 text-left text-xs text-gray-400 font-medium">ID</th>
                    <th className="px-5 py-3 text-left text-xs text-gray-400 font-medium">Vendor</th>
                    <th className="px-5 py-3 text-left text-xs text-gray-400 font-medium">Category</th>
                    <th className="px-5 py-3 text-left text-xs text-gray-400 font-medium">Description</th>
                    <th className="px-5 py-3 text-left text-xs text-gray-400 font-medium">Date</th>
                    <th className="px-5 py-3 text-right text-xs text-gray-400 font-medium">Amount</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800">
                  {EXPENSES.map(expense => (
                    <tr key={expense.id} className="hover:bg-[#2C2C2C]/50">
                      <td className="px-5 py-4 font-mono text-sm">{expense.id}</td>
                      <td className="px-5 py-4 font-medium">{expense.vendor}</td>
                      <td className="px-5 py-4">
                        <span className="text-xs bg-[#2C2C2C] px-2 py-1 rounded">{expense.category}</span>
                      </td>
                      <td className="px-5 py-4 text-sm text-gray-400">{expense.description}</td>
                      <td className="px-5 py-4 text-sm text-gray-400">{expense.date}</td>
                      <td className="px-5 py-4 text-right font-semibold text-red-400">-${expense.amount.toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeTab === 'reports' && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {[
                { title: 'Profit & Loss', desc: 'Income statement for the period', icon: TrendingUp },
                { title: 'Balance Sheet', desc: 'Assets, liabilities, equity', icon: PieChart },
                { title: 'Cash Flow', desc: 'Cash in and out analysis', icon: CreditCard },
                { title: 'Accounts Receivable', desc: 'Outstanding customer payments', icon: Clock },
                { title: 'Accounts Payable', desc: 'Outstanding vendor bills', icon: Receipt },
                { title: 'Tax Summary', desc: 'Quarterly tax estimates', icon: FileText },
              ].map((report, i) => (
                <button key={i} className="bg-[#1A1A1A] rounded-xl p-5 border border-gray-800 hover:border-gray-700 text-left transition group">
                  <report.icon className="w-8 h-8 text-[#C9A84C] mb-3" />
                  <h3 className="font-semibold">{report.title}</h3>
                  <p className="text-sm text-gray-500 mt-1">{report.desc}</p>
                  <div className="flex items-center gap-1 text-[#C9A84C] text-sm mt-3 opacity-0 group-hover:opacity-100 transition">
                    Generate <ChevronRight className="w-4 h-4" />
                  </div>
                </button>
              ))}
            </div>

            {/* Quick Stats */}
            <div className="bg-[#1A1A1A] rounded-xl p-5 border border-gray-800">
              <h3 className="font-semibold mb-4">Year-to-Date Summary</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div>
                  <p className="text-sm text-gray-500">Total Revenue</p>
                  <p className="text-xl font-bold text-green-400">$284,500</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Total Expenses</p>
                  <p className="text-xl font-bold text-red-400">$156,200</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Net Profit</p>
                  <p className="text-xl font-bold text-[#C9A84C]">$128,300</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Profit Margin</p>
                  <p className="text-xl font-bold">45.1%</p>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* New Invoice Modal */}
      {showNewInvoice && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/70" onClick={() => setShowNewInvoice(false)} />
          <div className="relative bg-[#1A1A1A] rounded-2xl border border-gray-800 w-full max-w-lg overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-800 flex items-center justify-between">
              <h2 className="font-bold text-lg">Create New Invoice</h2>
              <button onClick={() => setShowNewInvoice(false)} className="p-1 hover:bg-[#2C2C2C] rounded-lg"><X className="w-5 h-5" /></button>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">Customer *</label>
                <select className="w-full bg-[#2C2C2C] border border-gray-700 rounded-lg px-4 py-2 focus:border-[#C9A84C] outline-none">
                  <option>Select customer...</option>
                  <option>Azul Designs</option>
                  <option>Johnson Design Co.</option>
                  <option>Smith Residence</option>
                </select>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Invoice Date</label>
                  <input type="date" className="w-full bg-[#2C2C2C] border border-gray-700 rounded-lg px-4 py-2 focus:border-[#C9A84C] outline-none" />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Due Date</label>
                  <input type="date" className="w-full bg-[#2C2C2C] border border-gray-700 rounded-lg px-4 py-2 focus:border-[#C9A84C] outline-none" />
                </div>
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">Items/Description *</label>
                <textarea className="w-full bg-[#2C2C2C] border border-gray-700 rounded-lg px-4 py-2 focus:border-[#C9A84C] outline-none h-20 resize-none" placeholder="Describe the products/services..." />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">Amount *</label>
                <div className="relative">
                  <DollarSign className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
                  <input type="number" className="w-full bg-[#2C2C2C] border border-gray-700 rounded-lg pl-10 pr-4 py-2 focus:border-[#C9A84C] outline-none" placeholder="0.00" />
                </div>
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">Notes</label>
                <textarea className="w-full bg-[#2C2C2C] border border-gray-700 rounded-lg px-4 py-2 focus:border-[#C9A84C] outline-none h-16 resize-none" placeholder="Additional notes..." />
              </div>
            </div>
            <div className="px-6 py-4 border-t border-gray-800 flex gap-3">
              <button onClick={() => setShowNewInvoice(false)} className="flex-1 bg-[#2C2C2C] hover:bg-[#3C3C3C] py-3 rounded-xl">Cancel</button>
              <button className="flex-1 bg-[#C9A84C] hover:bg-[#B8973F] text-[#0D0D0D] font-semibold py-3 rounded-xl flex items-center justify-center gap-2">
                <CheckCircle className="w-4 h-4" /> Create Invoice
              </button>
            </div>
          </div>
        </div>
      )}

      {/* New Expense Modal */}
      {showNewExpense && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/70" onClick={() => setShowNewExpense(false)} />
          <div className="relative bg-[#1A1A1A] rounded-2xl border border-gray-800 w-full max-w-lg overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-800 flex items-center justify-between">
              <h2 className="font-bold text-lg">Add Expense</h2>
              <button onClick={() => setShowNewExpense(false)} className="p-1 hover:bg-[#2C2C2C] rounded-lg"><X className="w-5 h-5" /></button>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">Vendor *</label>
                <input type="text" className="w-full bg-[#2C2C2C] border border-gray-700 rounded-lg px-4 py-2 focus:border-[#C9A84C] outline-none" placeholder="Vendor name" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Category</label>
                  <select className="w-full bg-[#2C2C2C] border border-gray-700 rounded-lg px-4 py-2 focus:border-[#C9A84C] outline-none">
                    <option>Materials</option>
                    <option>Hardware</option>
                    <option>Shipping</option>
                    <option>Labor</option>
                    <option>Software</option>
                    <option>Office</option>
                    <option>Other</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Date</label>
                  <input type="date" className="w-full bg-[#2C2C2C] border border-gray-700 rounded-lg px-4 py-2 focus:border-[#C9A84C] outline-none" />
                </div>
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">Amount *</label>
                <div className="relative">
                  <DollarSign className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
                  <input type="number" className="w-full bg-[#2C2C2C] border border-gray-700 rounded-lg pl-10 pr-4 py-2 focus:border-[#C9A84C] outline-none" placeholder="0.00" />
                </div>
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">Description</label>
                <textarea className="w-full bg-[#2C2C2C] border border-gray-700 rounded-lg px-4 py-2 focus:border-[#C9A84C] outline-none h-16 resize-none" placeholder="What was this expense for?" />
              </div>
            </div>
            <div className="px-6 py-4 border-t border-gray-800 flex gap-3">
              <button onClick={() => setShowNewExpense(false)} className="flex-1 bg-[#2C2C2C] hover:bg-[#3C3C3C] py-3 rounded-xl">Cancel</button>
              <button className="flex-1 bg-[#C9A84C] hover:bg-[#B8973F] text-[#0D0D0D] font-semibold py-3 rounded-xl flex items-center justify-center gap-2">
                <CheckCircle className="w-4 h-4" /> Add Expense
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
