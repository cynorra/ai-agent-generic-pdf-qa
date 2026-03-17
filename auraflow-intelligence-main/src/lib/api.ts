import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface ChatRequest {
  message: string;
  session_id?: string;
  business_name: string;
}

export interface ChatResponse {
  response: string;
  session_id: string;
  business_name: string;
  iterations: number;
  duration_ms: number;
}

export interface Business {
  id: string;
  name: string;
  type: string;
  pdf_path: string;
  description: string;
}

export const chatApi = {
  sendMessage: async (data: ChatRequest): Promise<ChatResponse> => {
    const response = await api.post<ChatResponse>('/agent/chat', data);
    return response.data;
  },
  
  loadPdf: async (file: File, businessName: string, businessType: string, description: string = '') => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('business_name', businessName);
    formData.append('business_type', businessType);
    formData.append('description', description);
    
    const response = await api.post('/business/load_pdf', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  listBusinesses: async () => {
    const response = await api.get<{ businesses: Business[] }>('/business/list');
    return response.data;
  },

  getSessionDetails: async (sessionId: string) => {
    const response = await api.get(`/admin/session/${sessionId}`);
    return response.data;
  },

  getAuditLog: async (sessionId: string) => {
    const response = await api.get(`/admin/audit/${sessionId}`);
    return response.data;
  },
  
  deleteBusiness: async (businessId: string) => {
    const response = await api.delete(`/business/${businessId}`);
    return response.data;
  }
};

export default api;
