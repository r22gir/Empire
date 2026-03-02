import { create } from 'zustand'

export const useStore = create((set) => ({
  customers: [],
  quotes: [],
  inventory: [],
  addCustomer: (c: any) => set((s: any) => ({ customers: [...s.customers, { ...c, id: Date.now().toString() }] })),
}))
