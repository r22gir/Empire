const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface FetchOptions extends RequestInit {
  params?: Record<string, any>;
}

class APIClient {
  private baseURL: string;

  constructor(baseURL: string) {
    this.baseURL = baseURL;
  }

  private async request<T>(endpoint: string, options: FetchOptions = {}): Promise<T> {
    const { params, ...fetchOptions } = options;
    
    let url = `${this.baseURL}${endpoint}`;
    
    if (params) {
      const queryString = new URLSearchParams(
        Object.entries(params).reduce((acc, [key, value]) => {
          if (value !== undefined && value !== null) {
            acc[key] = String(value);
          }
          return acc;
        }, {} as Record<string, string>)
      ).toString();
      
      if (queryString) {
        url += `?${queryString}`;
      }
    }

    const response = await fetch(url, {
      ...fetchOptions,
      headers: {
        'Content-Type': 'application/json',
        ...fetchOptions.headers,
      },
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }

    return response.json();
  }

  async get<T>(endpoint: string, params?: Record<string, any>): Promise<T> {
    return this.request<T>(endpoint, { method: 'GET', params });
  }

  async post<T>(endpoint: string, data?: any): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async put<T>(endpoint: string, data?: any): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async delete<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'DELETE' });
  }
}

export const api = new APIClient(API_URL);

// Product API
export const productAPI = {
  list: (params?: any) => api.get('/marketplace/products', params),
  get: (id: string) => api.get(`/marketplace/products/${id}`),
  create: (data: any) => api.post('/marketplace/products', data),
  update: (id: string, data: any) => api.put(`/marketplace/products/${id}`, data),
  delete: (id: string) => api.delete(`/marketplace/products/${id}`),
};

// Order API
export const orderAPI = {
  list: (params?: any) => api.get('/marketplace/orders', params),
  get: (id: string) => api.get(`/marketplace/orders/${id}`),
  create: (data: any) => api.post('/marketplace/orders', data),
  ship: (id: string, data: any) => api.post(`/marketplace/orders/${id}/ship`, data),
};

// Review API
export const reviewAPI = {
  create: (orderId: string, data: any) => api.post(`/marketplace/orders/${orderId}/review`, data),
  getUser: (userId: string, params?: any) => api.get(`/marketplace/users/${userId}/reviews`, params),
};

// Seller API
export const sellerAPI = {
  orders: (params?: any) => api.get('/marketplace/seller/orders', params),
};
