// Environment configuration
const getApiBaseUrl = (): string => {
  // Check if we're in a browser environment
  if (typeof window !== 'undefined') {
    // Try to get from environment variables first
    const envApiUrl = import.meta.env?.VITE_API_BASE_URL;
    if (envApiUrl) {
      return envApiUrl;
    }

    // Fallback to current host with common backend ports
    const { protocol, hostname } = window.location;

    // In development, try common backend ports
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
      return `${protocol}//${hostname}:8000/api`;
    }

    // In production, assume API is on same host with /api path
    return `${protocol}//${hostname}/api`;
  }

  // Server-side fallback
  return process.env.API_BASE_URL || 'http://localhost:8000/api';
};

export const API_CONFIG = {
  BASE_URL: getApiBaseUrl(),
  TIMEOUT: 30000, // 30 seconds
  RETRY_ATTEMPTS: 3,
  RETRY_DELAY: 1000, // 1 second
};

// Health check configuration
export const HEALTH_CHECK_CONFIG = {
  INTERVAL: 30000, // 30 seconds
  TIMEOUT: 5000,   // 5 seconds
  ENDPOINT: '/health/',
};

// Frontend configuration
export const APP_CONFIG = {
  NAME: 'Agent Builder',
  VERSION: '1.0.0',
  ENABLE_DEBUG: import.meta.env?.DEV || false,
  ENABLE_MOCK_DATA: import.meta.env?.VITE_ENABLE_MOCK_DATA === 'true',
};

// Feature flags
export const FEATURES = {
  WORKFLOWS: true,
  AGENTS: true,
  CREDENTIALS: true,
  PROJECTS: true,
  TOOLS: true,
};

export default {
  API_CONFIG,
  HEALTH_CHECK_CONFIG,
  APP_CONFIG,
  FEATURES,
};