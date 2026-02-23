/**
 * API Client for ContractorForge Backend
 */
import axios from 'axios'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor to add auth token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('authToken')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized
      localStorage.removeItem('authToken')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default apiClient

// API methods
export const api = {
  // Industries
  getIndustries: () => apiClient.get('/industries'),
  
  // Auth
  signup: (data: any) => apiClient.post('/auth/signup', data),
  login: (data: any) => apiClient.post('/auth/login', data),
  
  // Projects
  getProjects: () => apiClient.get('/projects'),
  getProject: (id: number) => apiClient.get(`/projects/${id}`),
  createProject: (data: any) => apiClient.post('/projects', data),
  
  // AI Chat
  startConversation: (industryCode: string) => 
    apiClient.post('/ai/conversation/start', { industry_code: industryCode }),
  sendMessage: (conversationId: number, message: string) =>
    apiClient.post(`/ai/conversation/${conversationId}/message`, { message }),
  
  // Photo Measurement
  measurePhoto: (file: File, referenceType?: string) => {
    const formData = new FormData()
    formData.append('file', file)
    if (referenceType) {
      formData.append('reference_type', referenceType)
    }
    return apiClient.post('/measurement/photo', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  
  // Estimates
  generateEstimate: (projectId: number) =>
    apiClient.post(`/projects/${projectId}/estimate`),
  getEstimate: (id: number) => apiClient.get(`/estimates/${id}`),
  
  // Customers
  getCustomers: () => apiClient.get('/customers'),
  createCustomer: (data: any) => apiClient.post('/customers', data),
}
