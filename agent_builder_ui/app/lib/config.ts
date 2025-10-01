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

// Agent Builder AI Service configuration
const getAgentBuilderUrl = (): string => {
  // Check if we're in a browser environment
  if (typeof window !== 'undefined') {
    // Try environment variable first
    const envUrl = import.meta.env?.REACT_APP_AGENT_BUILDER_URL || import.meta.env?.VITE_AGENT_BUILDER_URL;
    if (envUrl) {
      return envUrl;
    }
  }

  // Server-side or fallback
  try {
    if (typeof process !== 'undefined' && process.env?.REACT_APP_AGENT_BUILDER_URL) {
      return process.env.REACT_APP_AGENT_BUILDER_URL;
    }
  } catch (e) {
    // process not available in browser
  }

  // Default fallback
  return 'http://127.0.0.1:8001';
};

const getAgentBuilderTimeout = (): number => {
  // Check if we're in a browser environment
  if (typeof window !== 'undefined') {
    const envTimeout = import.meta.env?.REACT_APP_AGENT_BUILDER_TIMEOUT || import.meta.env?.VITE_AGENT_BUILDER_TIMEOUT;
    if (envTimeout) {
      return parseInt(envTimeout);
    }
  }

  // Server-side or fallback
  try {
    if (typeof process !== 'undefined' && process.env?.REACT_APP_AGENT_BUILDER_TIMEOUT) {
      return parseInt(process.env.REACT_APP_AGENT_BUILDER_TIMEOUT);
    }
  } catch (e) {
    // process not available in browser
  }

  // Default fallback
  return 30000;
};

export const AGENT_BUILDER_CONFIG = {
  BASE_URL: getAgentBuilderUrl(),
  TIMEOUT: getAgentBuilderTimeout(),
  HEALTH_ENDPOINT: '/healthz',
  SESSION_ENDPOINT: '/session/',
  CHAT_ENDPOINT: '/chat/',
  GENERATE_ENDPOINT: '/generate/',
  GENERATE_FINALIZE_ENDPOINT: '/generate/finalize/',
  FINALIZE_ENDPOINT: '/finalize/',
  RESET_ENDPOINT: '/reset/',
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
  AGENT_BUILDER_CONFIG,
  APP_CONFIG,
  FEATURES,
};