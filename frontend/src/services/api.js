import axios from 'axios';

// Connect to the FastAPI backend (local or deployed)
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const getDashboardSummary = async () => {
  const response = await api.get('/dashboard/summary');
  return response.data;
};

export const getTopPlates = async (limit = 5) => {
  const response = await api.get('/dashboard/top-plates', { params: { limit } });
  return response.data;
};

export const getHotspots = async () => {
  const response = await api.get('/analytics/hotspots');
  return response.data;
};

export const getTrends = async () => {
  const response = await api.get('/analytics/trends');
  return response.data;
};

export const searchEvidence = async (params) => {
  const response = await api.get('/search', { params });
  return response.data;
};

export const getEvidenceDetails = async (id) => {
  const response = await api.get(`/evidence/${id}`);
  return response.data;
};

export const getEvidenceDownloadUrl = (id) => {
  return `${API_URL}/evidence/${id}/download`;
};

export const getAssetUrl = (path) => {
  if (!path) return null;
  if (/^https?:\/\//i.test(path)) return path;
  return `${API_URL}${path.startsWith('/') ? path : `/${path}`}`;
};

export const processVideo = async (file, cameraId) => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post(`/video/predict?camera_id=${cameraId}`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
  return response.data;
};

export const processImage = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post('/predict', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
  return response.data;
};

export const getVideoStatus = async (taskId) => {
  const response = await api.get(`/video/status/${taskId}`);
  return response.data;
};

export const getVideoResult = async (taskId) => {
  const response = await api.get(`/video/result/${taskId}`);
  return response.data;
};

// ── Phase 6: Enforcement & Challan APIs ──────────────────────────────────

export const getEnforcementStats = async () => {
  const response = await api.get('/demo/enforcement');
  return response.data;
};

export const getChallans = async (params) => {
  const response = await api.get('/challan/list', { params });
  return response.data;
};

export const getChallanDetails = async (id) => {
  const response = await api.get(`/challan/${id}`);
  return response.data;
};

export const updateChallanStatus = async (id, status) => {
  const response = await api.put(`/challan/status/${id}?status=${status}`);
  return response.data;
};

export const getChallanPdfUrl = (id) => {
  return `${API_URL}/challan/pdf/${id}`;
};

export const manualGenerateChallan = async (evidenceId) => {
  const response = await api.post(`/challan/generate?evidence_id=${evidenceId}`);
  return response.data;
};
