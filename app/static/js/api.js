/**
 * API Service for AI Project Assistant
 * Wraps all the endpoints provided by FastAPI.
 */
const API_BASE = window.location.origin;

class ApiService {
  /** Helper for handling responses */
  static async _fetch(url, options = {}) {
    const defaultHeaders = { 'Content-Type': 'application/json' };
    const res = await fetch(`${API_BASE}${url}`, {
      ...options,
      headers: { ...defaultHeaders, ...options.headers }
    });
    
    if (!res.ok) {
      let errorData;
      try {
        errorData = await res.json();
      } catch (e) {
        errorData = { detail: res.statusText };
      }
      throw new Error(errorData.detail || `HTTP Error ${res.status}`);
    }
    
    return res.json();
  }

  // Projects
  static getProjects() {
    return this._fetch('/projects/');
  }

  static getProject(id) {
    return this._fetch(`/projects/${id}`);
  }

  static createProject(payload) {
    return this._fetch('/projects/', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  }

  // Chat
  static getChatHistory(projectId) {
    return this._fetch(`/projects/${projectId}/chat/`);
  }

  static sendChatMessage(projectId, message) {
    return this._fetch(`/projects/${projectId}/chat/`, {
      method: 'POST',
      body: JSON.stringify({ message })
    });
  }

  // Memory & Assets
  static getProjectMemory(projectId) {
    return this._fetch(`/projects/${projectId}/memory`);
  }

  static getProjectImages(projectId) {
    return this._fetch(`/projects/${projectId}/images`);
  }

  // Agents
  static triggerAgent(projectId) {
    return this._fetch(`/projects/${projectId}/agent/trigger`, {
      method: 'POST'
    });
  }

  static getAgentStatus(executionId) {
    return this._fetch(`/agent/status/${executionId}`);
  }
}

// Attach to window for global access
window.api = ApiService;
