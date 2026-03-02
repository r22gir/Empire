'use client'
import { useState } from 'react'
import { DollarSign, Plus, TrendingUp, TrendingDown, Calendar, ArrowUpRight, ArrowDownRight, X } from 'lucide-react'

interface Transaction { id: string; type: 'income' | 'expense'; category: string; description: string; amount: number; date: string }

export default function Finance() {
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [showModal, setShowModal] = useState(false)
  const [form, setForm] = useState({ type: 'income' as const, category: '', description: '', amount: 0, date: new Date().toISOString().split('T')[0] })

  const save = () => {
    if (!form.amount) return
    setTransactions([{ ...form, id: Date.now().toString() }, ...transactions])
    setShowModal(false)
    setForm({ type: 'income', category: '', description: '', amount: 0, date: new Date().toISOString().split('T')[0] })
  }

  const income = transactions.filter(t => t.type === 'income').reduce((s, t) => s + t.amount, 0)
  const expenses = transactions.filter(t => t.type === 'expense').reduce((s, t) => s + t.amount, 0)
  const profit = income - expenses

  return (
    <div className="min-h-screen bg-[#030308] p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-yellow-500 to-amber-600 flex items-center justify-center">
            <DollarSign className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-2xl font-bold">Finance</h1>
            <p className="text-gray-500">{transactions.length} transactions</p>
          </div>
        </div>
        <button onClick={() => setShowModal(true)} className="flex items-center gap-2 bg-gradient-to-r from-yellow-500 to-amber-600 px-4 py-2 rounded-xl font-semibold text-black">
          <Plus className="w-5 h-5" />Add Transaction
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <div className="bg-[#0a0a12] rounded-xl p-5 border border-white/10">
          <div className="flex items-center gap-2 mb-2"><TrendingUp className="w-5 h-5 text-green-400" /><span className="text-gray-500">Income</span></div>
          <p className="text-2xl font-bold text-green-400">${income.toLocaleString()}</p>
        </div>
        <div className="bg-[#0a0a12] rounded-xl p-5 border border-white/10">
          <div className="flex items-center gap-2 mb-2"><TrendingDown className="w-5 h-5 text-red-400" /><span className="text-gray-500">Expenses</span></div>
          <p className="text-2xl font-bold text-red-400">${expenses.toLocaleString()}</p>
        </div>
        <div className="bg-[#0a0a12] rounded-xl p-5 border border-white/10">
          <div className="flex items-center gap-2 mb-2"><DollarSign className="w-5 h-5 text-amber-400" /><span className="text-gray-500">Profit</span></div>
          <p className={`text-2xl font-bold ${profit >= 0 ? 'text-green-400' : 'text-red-400'}`}>${profit.toLocaleString()}</p>
        </div>
      </div>

      {/* Empty State */}
      {transactions.length === 0 && (
        <div className="text-center py-16">
          <div className="w-20 h-20 rounded-full bg-yellow-500/20 flex items-center justify-center mx-auto mb-4">
            <DollarSign className="w-10 h-10 text-yellow-400" />
          </div>
          <h2 className="text-xl font-bold mb-2">No transactions yet</h2>
          <p className="text-gray-500 mb-6">Add your first income or expense</p>
          <button onClick={() => setShowModal(true)} className="bg-gradient-to-r from-yellow-500 to-amber-600 px-6 py-3 rounded-xl font-semibold text-black">Add Transaction</button>
        </div>
      )}

      {/* Transactions */}
      {transactions.length > 0 && (
        <div className="bg-[#0a0a12] rounded-xl border border-white/10 overflow-hidden">
          <div className="px-5 py-3 border-b border-white/10 text-sm text-gray-500">Recent Transactions</div>
          <div className="divide-y divide-white/5">
            {transactions.map(t => (
              <div key={t.id} className="px-5 py-4 flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${t.type === 'income' ? 'bg-green-500/20' : 'bg-red-500/20'}`}>
                    {t.type === 'income' ? <ArrowDownRight className="w-5 h-5 text-green-400" /> : <ArrowUpRight className="w-5 h-5 text-red-400" />}
                  </div>
                  <div>
                    <p className="font-medium">{t.description || t.category || (t.type === 'income' ? 'Income' : 'Expense')}</p>
                    <p className="text-sm text-gray-500">{t.date}</p>
                  </div>
                </div>
                <p className={`font-bold ${t.type === 'income' ? 'text-green-400' : 'text-red-400'}`}>
                  {t.type === 'income' ? '+' : '-'}${t.amount.toLocaleString()}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/60" onClick={() => setShowModal(false)} />
          <div className="relative bg-[#0a0a12] border border-white/10 rounded-2xl w-full max-w-md p-6">
            <div className="flex justify-between mb-4"><h2 className="text-xl font-bold">Add Transaction</h2><button onClick={() => setShowModal(false)}><X className="w-5 h-5" /></button></div>
            <div className="space-y-4">
              <div className="flex gap-2">
                <button onClick={() => setForm({ ...form, type: 'income' })} className={`flex-1 py-3 rounded-xl font-medium ${form.type === 'income' ? 'bg-green-500 text-black' : 'bg-white/10'}`}>Income</button>
                <button onClick={() => setForm({ ...form, type: 'expense' })} className={`flex-1 py-3 rounded-xl font-medium ${form.type === 'expense' ? 'bg-red-500 text-white' : 'bg-white/10'}`}>Expense</button>
              </div>
              <input type="number" placeholder="Amount *" value={form.amount || ''} onChange={(e) => setForm({ ...form, amount: +e.target.value })} className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 outline-none text-2xl font-bold text-center" />
              <input type="text" placeholder="Description" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 outline-none" />
              <input type="text" placeholder="Category" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 outline-none" />
              <input type="date" value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 outline-none" />
            </div>
            <div className="flex gap-3 mt-6">
              <button onClick={() => setShowModal(false)} className="flex-1 bg-white/10 py-3 rounded-xl">Cancel</button>
              <button onClick={save} className={`flex-1 py-3 rounded-xl font-semibold ${form.type === 'income' ? 'bg-green-500 text-black' : 'bg-red-500'}`}>Save</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
