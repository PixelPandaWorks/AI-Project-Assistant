/**
 * Main UI Logic for AI Project Assistant
 */

// State
let currentProjectId = null;
let currentProject = null;

// DOM Elements
const els = {
  projectList: document.getElementById('project-list'),
  btnNewProject: document.getElementById('btn-new-project'),
  modalProject: document.getElementById('modal-project'),
  btnCancelModal: document.getElementById('btn-cancel-modal'),
  btnSubmitProject: document.getElementById('btn-submit-project'),
  btnCloseModal: document.getElementById('btn-close-modal'),
  
  // Chat
  currentProjectName: document.getElementById('current-project-name'),
  chatMessages: document.getElementById('chat-messages'),
  chatInputContainer: document.getElementById('chat-input-container'),
  chatInput: document.getElementById('chat-input'),
  btnSendMessage: document.getElementById('btn-send-message'),
  btnTriggerAgent: document.getElementById('btn-trigger-agent'),
  
  // Panels
  rightPanel: document.getElementById('right-panel'),
  tabs: document.querySelectorAll('.tab'),
  tabPanes: document.querySelectorAll('.tab-pane'),
  
  // Tab content
  briefTitle: document.getElementById('brief-title'),
  briefDesc: document.getElementById('brief-desc'),
  briefDetails: document.getElementById('brief-details'),
  memoryList: document.getElementById('memory-list'),
  imagesGrid: document.getElementById('images-grid'),
  btnRefreshMemory: document.getElementById('btn-refresh-memory'),
  btnRefreshImages: document.getElementById('btn-refresh-images')
};

// --- Initialization ---
document.addEventListener('DOMContentLoaded', () => {
  // Initialize Lucide icons
  lucide.createIcons();
  
  // Setup tabs
  els.tabs.forEach(tab => {
    tab.addEventListener('click', () => switchTab(tab.dataset.tab));
  });
  
  // Setup modal
  els.btnNewProject.addEventListener('click', () => els.modalProject.classList.add('active'));
  els.btnCancelModal.addEventListener('click', () => els.modalProject.classList.remove('active'));
  els.btnCloseModal.addEventListener('click', () => els.modalProject.classList.remove('active'));
  
  // Create Project
  els.btnSubmitProject.addEventListener('click', handleCreateProject);
  
  // Chat events
  els.btnSendMessage.addEventListener('click', handleSendMessage);
  els.chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  });
  
  // Agent events
  els.btnTriggerAgent.addEventListener('click', handleTriggerAgent);
  
  // Refresh events
  els.btnRefreshMemory.addEventListener('click', () => {
    if (currentProjectId) loadProjectMemory(currentProjectId);
  });
  els.btnRefreshImages.addEventListener('click', () => {
    if (currentProjectId) loadProjectImages(currentProjectId);
  });
  
  // Initial data load
  loadProjects();
});

// --- UI Helpers ---

function switchTab(tabId) {
  els.tabs.forEach(t => t.classList.remove('active'));
  els.tabPanes.forEach(p => p.classList.remove('active'));
  
  document.querySelector(`.tab[data-tab="${tabId}"]`).classList.add('active');
  document.getElementById(`tab-${tabId}`).classList.add('active');
}

function showLoading(container) {
  container.innerHTML = `<div style="display:flex; justify-content:center; padding: 24px;">
    <div class="loading-dots"><span></span><span></span><span></span></div>
  </div>`;
}

function scrollChatToBottom() {
  els.chatMessages.scrollTop = els.chatMessages.scrollHeight;
}

// --- Logic ---

async function loadProjects() {
  try {
    const projects = await window.api.getProjects();
    els.projectList.innerHTML = '';
    
    if (projects.length === 0) {
      els.projectList.innerHTML = `<div style="padding:12px; color:var(--text-secondary); font-size:0.85rem">No projects yet.</div>`;
      return;
    }
    
    projects.forEach(p => {
      const div = document.createElement('div');
      div.className = 'project-item';
      if (p.id === currentProjectId) div.classList.add('active');
      div.onclick = () => selectProject(p.id);
      div.innerHTML = `
        <i data-lucide="folder" style="width: 16px; height: 16px;"></i>
        <div style="flex:1; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;" title="${p.name}">${p.name}</div>
      `;
      els.projectList.appendChild(div);
    });
    lucide.createIcons();
    
    // Automatically select the first project if none selected
    // if (!currentProjectId && projects.length > 0) {
    //   selectProject(projects[0].id);
    // }
  } catch (e) {
    console.error("Failed to load projects", e);
  }
}

async function handleCreateProject() {
  const name = document.getElementById('form-name').value;
  const title = document.getElementById('form-title').value;
  const desc = document.getElementById('form-desc').value;
  
  if (!name || !title || !desc) {
    alert("Please fill all required fields.");
    return;
  }
  
  const payload = {
    name,
    brief: { title, description: desc, goals: [], reference_links: [] }
  };
  
  const btn = els.btnSubmitProject;
  btn.disabled = true;
  btn.innerText = 'Creating...';
  
  try {
    const newProject = await window.api.createProject(payload);
    els.modalProject.classList.remove('active');
    
    // Clear form
    document.getElementById('form-name').value = '';
    document.getElementById('form-title').value = '';
    document.getElementById('form-desc').value = '';
    
    await loadProjects();
    selectProject(newProject.id);
    
  } catch(e) {
    alert(e.message);
  } finally {
    btn.disabled = false;
    btn.innerText = 'Create Project';
  }
}

async function selectProject(id) {
  currentProjectId = id;
  loadProjects(); // Re-render to highlight active
  
  try {
    const projectInfo = await window.api.getProject(id);
    currentProject = projectInfo;
    
    // Update headers
    els.currentProjectName.innerText = projectInfo.name;
    
    // Show hidden panels
    els.rightPanel.classList.remove('hidden');
    els.chatInputContainer.classList.remove('hidden');
    els.btnTriggerAgent.classList.remove('hidden');
    
    // Render Brief
    renderBrief(projectInfo.brief);
    
    // Load concurrent blocks
    loadChatHistory(id);
    loadProjectMemory(id);
    loadProjectImages(id);
    
  } catch(e) {
    console.error("Error selecting project", e);
    alert("Could not load project details.");
  }
}

function renderBrief(brief) {
  if (!brief) return;
  els.briefTitle.innerText = brief.title || 'Untitled Brief';
  els.briefDesc.innerText = brief.description || 'No description provided.';
  
  let html = '';
  
  const addKV = (key, value) => {
    if (!value) return;
    html += `
      <div class="key-value">
        <div class="key">${key}</div>
        <div class="value">${value}</div>
      </div>
    `;
  };
  
  if (brief.goals && brief.goals.length) {
    addKV('Goals', `<ul>${brief.goals.map(g => `<li>${g}</li>`).join('')}</ul>`);
  }
  
  if (brief.target_audience) addKV('Target Audience', brief.target_audience);
  if (brief.tech_stack) addKV('Tech Stack', brief.tech_stack);
  
  if (brief.reference_links && brief.reference_links.length) {
    const links = brief.reference_links.map(l => `<a href="${l}" target="_blank" style="color:var(--accent)">${l}</a>`).join('<br/>');
    addKV('References', links);
  }
  
  els.briefDetails.innerHTML = html;
}

// --- Chat Logic ---

function appendMessageToUI(msg) {
  const isUser = msg.role === 'user';
  const div = document.createElement('div');
  div.className = `message ${isUser ? 'user' : 'assistant'}`;
  
  // Icon parsing
  const icon = isUser ? 'user' : 'bot';
  
  let contentHtml = isUser 
    ? msg.content 
    : marked.parse(msg.content); // Use marked.js for assistant markdown
    
  // Format tool calls if present
  let toolCallsHtml = '';
  if (msg.tool_calls && Array.isArray(msg.tool_calls) && msg.tool_calls.length > 0) {
    toolCallsHtml = msg.tool_calls.map(tc => `
      <div class="tool-call">
        <i data-lucide="wrench" style="width: 14px; margin-top: 2px;"></i>
        <div>
          <div style="font-weight: 500; color: #94a3b8; margin-bottom: 4px;">Used tool: ${tc.tool || tc.name}</div>
          <pre>${JSON.stringify(tc.input || tc.arguments, null, 2)}</pre>
        </div>
      </div>
    `).join('');
  }
  
  div.innerHTML = `
    <div class="message-avatar">
      <i data-lucide="${icon}" style="width: 18px; height: 18px;"></i>
    </div>
    <div style="display:flex; flex-direction:column; max-width:100%;">
      <div class="message-bubble">${contentHtml}</div>
      ${toolCallsHtml}
    </div>
  `;
  
  els.chatMessages.appendChild(div);
  lucide.createIcons({root: div});
  scrollChatToBottom();
}

async function loadChatHistory(id) {
  showLoading(els.chatMessages);
  els.chatMessages.innerHTML = '';
  
  try {
    const history = await window.api.getChatHistory(id);
    
    if (history.length === 0) {
      els.chatMessages.innerHTML = `
        <div class="message assistant" style="align-self: center; margin: auto; opacity: 0.7; text-align: center;">
          <p>No messages yet. Send a message to start.</p>
        </div>
      `;
      return;
    }
    
    els.chatMessages.innerHTML = ''; // clear loading
    history.forEach(msg => appendMessageToUI(msg));
    
  } catch(e) {
    els.chatMessages.innerHTML = `<div style="color:red; padding: 24px;">Failed to load chat: ${e.message}</div>`;
  }
}

async function handleSendMessage() {
  const text = els.chatInput.value.trim();
  if (!text || !currentProjectId) return;
  
  els.chatInput.value = '';
  els.chatInput.style.height = 'auto'; // Reset size
  
  // Optimistic UI update
  appendMessageToUI({ role: 'user', content: text });
  
  // Helper for typing indicator
  const typingId = 'typing-' + Date.now();
  const typingDiv = document.createElement('div');
  typingDiv.className = 'message assistant';
  typingDiv.id = typingId;
  typingDiv.innerHTML = `
    <div class="message-avatar"><i data-lucide="bot" style="width: 18px;"></i></div>
    <div class="message-bubble">
      <div class="loading-dots"><span></span><span></span><span></span></div>
      <div style="font-size: 0.8rem; margin-top: 8px; color: var(--text-secondary);">Claude is thinking...</div>
    </div>
  `;
  els.chatMessages.appendChild(typingDiv);
  lucide.createIcons({root: typingDiv});
  scrollChatToBottom();
  
  els.chatInput.disabled = true;
  els.btnSendMessage.disabled = true;
  
  try {
    const res = await window.api.sendChatMessage(currentProjectId, text);
    document.getElementById(typingId).remove();
    
    appendMessageToUI({ role: 'assistant', content: res.response, tool_calls: res.tool_calls });
    
    // If tool calls were made, it's a good idea to refresh memory or images
    if (res.tool_calls && res.tool_calls.length) {
      const toolNames = res.tool_calls.map(t => t.tool || t.name);
      if (toolNames.includes('save_project_memory')) loadProjectMemory(currentProjectId);
      if (toolNames.includes('generate_image')) loadProjectImages(currentProjectId);
    }
    
  } catch (e) {
    document.getElementById(typingId).remove();
    alert(`Error: ${e.message}`);
  } finally {
    els.chatInput.disabled = false;
    els.btnSendMessage.disabled = false;
    els.chatInput.focus();
  }
}

// --- Memory & Assets ---

async function loadProjectMemory(id) {
  showLoading(els.memoryList);
  try {
    const memory = await window.api.getProjectMemory(id);
    els.memoryList.innerHTML = '';
    
    if (memory.length === 0) {
      els.memoryList.innerHTML = `<p style="font-size: 0.85rem; color: var(--text-secondary);">No memory blocks stored yet.</p>`;
      return;
    }
    
    memory.forEach(m => {
      const isAgent = m.source === 'agent';
      const div = document.createElement('div');
      div.className = 'key-value';

      // Extract string from memory_value (it's a JSON object like {"content": "..."})
      let displayValue = m.memory_value;
      if (typeof displayValue === 'object' && displayValue !== null) {
        displayValue = displayValue.content || JSON.stringify(displayValue, null, 2);
      }

      div.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <div class="key">${m.memory_key}</div>
          ${isAgent ? '<span style="font-size:0.65rem; background:#4f46e5; color:white; padding:2px 6px; border-radius:4px;">Auto</span>' : ''}
        </div>
        <div class="value">${marked.parse(String(displayValue))}</div>
      `;
      els.memoryList.appendChild(div);
    });
    
  } catch(e) {
    els.memoryList.innerHTML = `<p style="color:red; font-size: 0.85rem;">Failed to load memory.</p>`;
  }
}

async function loadProjectImages(id) {
  showLoading(els.imagesGrid);
  try {
    const images = await window.api.getProjectImages(id);
    els.imagesGrid.innerHTML = '';
    
    if (images.length === 0) {
      els.imagesGrid.innerHTML = `<p style="font-size: 0.85rem; color: var(--text-secondary); grid-column: 1 / -1;">No images generated yet.</p>`;
      return;
    }
    
    images.forEach(img => {
      const div = document.createElement('div');
      div.className = 'img-card';
      
      const url = img.url;
      const promptText = img.prompt ? img.prompt.substring(0, 60) + (img.prompt.length > 60 ? '...' : '') : '';
      
      div.innerHTML = `
        <a href="${url}" target="_blank">
          <img src="${url}" alt="Generated Image" loading="lazy"
               onerror="this.onerror=null; this.parentElement.innerHTML='<div style=\\"display:flex;align-items:center;justify-content:center;height:100%;color:var(--text-secondary);font-size:0.8rem;padding:12px;text-align:center;\\">Image unavailable<br/>(expired or invalid URL)</div>';" />
        </a>
        ${promptText ? `<div style="padding:6px 8px; font-size:0.75rem; color:var(--text-secondary); border-top:1px solid var(--border); overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${img.prompt}">${promptText}</div>` : ''}
      `;
      els.imagesGrid.appendChild(div);
    });
    
  } catch(e) {
    els.imagesGrid.innerHTML = `<p style="color:red; font-size: 0.85rem; grid-column: 1 / -1;">Failed to load images.</p>`;
  }
}

// --- Agent Logic ---

async function handleTriggerAgent() {
  if (!currentProjectId) return;
  els.btnTriggerAgent.disabled = true;
  els.btnTriggerAgent.innerHTML = `<i data-lucide="loader" class="spin"></i> Running...`;
  lucide.createIcons({root: els.btnTriggerAgent});
  
  try {
    // 1. Trigger
    const res = await window.api.triggerAgent(currentProjectId);
    const execId = res.execution_id;
    
    // 2. Poll
    let status = 'running';
    while (status === 'running' || status === 'pending') {
      await new Promise(r => setTimeout(r, 2000)); // poll every 2s
      const pollRes = await window.api.getAgentStatus(execId);
      status = pollRes.status;
    }
    
    if (status === 'completed') {
      alert("Agent completed memory organization!");
      loadProjectMemory(currentProjectId); // Refresh memory
    } else {
      alert("Agent execution failed.");
    }
    
  } catch(e) {
    alert(`Failed to run agent: ${e.message}`);
  } finally {
    els.btnTriggerAgent.disabled = false;
    els.btnTriggerAgent.innerHTML = `<i data-lucide="zap"></i> Run Agent`;
    lucide.createIcons({root: els.btnTriggerAgent});
  }
}
