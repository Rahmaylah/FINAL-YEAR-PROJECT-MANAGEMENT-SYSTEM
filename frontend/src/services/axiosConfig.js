import axios from 'axios';

// Dynamically determine the backend URL based on the current host
// This allows the app to work from any IP/domain (localhost, 192.168.x.x, etc.)
const getBackendURL = () => {
  const hostname = window.location.hostname;
  const backendPort = 8000; // Django backend port
  return `http://${hostname}:${backendPort}`;
};

// Create axios instance with dynamic config
const axiosInstance = axios.create({
  baseURL: getBackendURL(),
  headers: {
    'Content-Type': 'application/json',
  },
});

export const getStoredToken = () => localStorage.getItem('authToken');
export const setStoredToken = (token) => {
  if (token) {
    localStorage.setItem('authToken', token);
  } else {
    localStorage.removeItem('authToken');
  }
};

// Request interceptor for debugging
axiosInstance.interceptors.request.use(
  (config) => {
    const token = getStoredToken();
    if (token) {
      config.headers.Authorization = `Token ${token}`;
    } else if (config.headers?.Authorization) {
      delete config.headers.Authorization;
    }
    console.log(`[REQUEST] ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for debugging and error handling
axiosInstance.interceptors.response.use(
  (response) => {
    console.log(`[RESPONSE] ${response.status} ${response.config.url}`);
    return response;
  },
  (error) => {
    if (error.response) {
      console.error(`[ERROR] ${error.response.status} ${error.config?.url}`);
      console.error('Error details:', error.response.data);
    } else if (error.request) {
      console.error('[ERROR] No response received from server');
    } else {
      console.error('[ERROR]', error.message);
    }
    return Promise.reject(error);
  }
);

export default axiosInstance;
