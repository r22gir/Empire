import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const licenseApi = {
  validate: async (key: string) => {
    const response = await api.get(`/licenses/${key}/validate`);
    return response.data;
  },
  
  activate: async (key: string, userId: string) => {
    const response = await api.post(`/licenses/${key}/activate`, { user_id: userId });
    return response.data;
  },
};

export const preorderApi = {
  create: async (data: any) => {
    const response = await api.post('/preorders/', data);
    return response.data;
  },
  
  get: async (preorderId: string) => {
    const response = await api.get(`/preorders/${preorderId}`);
    return response.data;
  },
};

export default api;
