// Side Panel - Protected AI Chat

const BACKEND_URL = 'http://localhost:3000';

// DOM Elements
const messagesContainer = document.getElementById('messagesContainer');
const messageInput = document.getElementById('messageInput');
const sendButton = document.getElementById('sendButton');
const statusIndicator = document.getElementById('statusIndicator');

// Chat state
let isProcessing = false;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
  checkBackendStatus();
  setupEventListeners();
  addWelcomeMessage();
});

// Setup event listeners
function setupEventListeners() {
  sendButton.addEventListener('click', handleSendMessage);
  
  messageInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  });
  
  messageInput.addEventListener('input', () => {
    sendButton.disabled = messageInput.value.trim() === '';
  });
}

// Check backend status
async function checkBackendStatus() {
  try {
    const response = await fetch(`${BACKEND_URL}/health`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json'
      }
    });
    
    if (response.ok) {
      statusIndicator.className = 'status-indicator status-online';
      statusIndicator.title = 'Backend connected';
    } else {
      statusIndicator.className = 'status-indicator status-offline';
      statusIndicator.title = 'Backend error';
    }
  } catch (error) {
    console.error('Backend check failed:', error);
    statusIndicator.className = 'status-indicator status-offline';
    statusIndicator.title = 'Backend offline';
  }
}

// Add welcome message
function addWelcomeMessage() {
  const welcomeMessage = {
    type: 'system',
    content: '👋 Welcome to Protected AI Chat! Ask me health-related questions and I\'ll provide safe, evidence-based information.'
  };
  addMessage(welcomeMessage);
}

// Handle send message
async function handleSendMessage() {
  const message = messageInput.value.trim();
  
  if (!message || isProcessing) return;
  
  // Add user message to chat
  addMessage({ type: 'user', content: message });
  
  // Clear input
  messageInput.value = '';
  sendButton.disabled = true;
  
  // Set processing state
  isProcessing = true;
  
  // Add loading message
  const loadingId = addMessage({ 
    type: 'loading', 
    content: '🤔 Thinking and checking safety...' 
  });
  
  try {
    console.log('Sending message to backend:', message);
    
    // Send to backend
    const response = await fetch(`${BACKEND_URL}/api/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        message: message
      })
    });
    
    console.log('Response status:', response.status);
    
    if (!response.ok) {
      const errorText = await response.text();
      console.error('Backend error:', errorText);
      throw new Error(`Backend returned ${response.status}: ${errorText}`);
    }
    
    const data = await response.json();
    console.log('Response data:', data);
    
    // Remove loading message
    removeMessage(loadingId);
    
    // Display result based on safety decision
    if (data.safe) {
      // Safe response - show AI answer
      addMessage({
        type: 'assistant',
        content: data.filtered_response || data.ai_response,
        decision: data.decision,
        severity: data.severity,
        sources: data.details?.evidence_summary || []
      });
    } else {
      // Unsafe response - show blocked message
      addMessage({
        type: 'blocked',
        content: data.explanation,
        decision: data.decision,
        severity: data.severity,
        reason: data.details?.decision_reason
      });
    }
    
  } catch (error) {
    console.error('Chat error:', error);
    
    // Remove loading message
    removeMessage(loadingId);
    
    // Show error message
    addMessage({
      type: 'error',
      content: `❌ Error: ${error.message}. Please check if backend is running on port 3000.`
    });
  } finally {
    isProcessing = false;
  }
}

// Add message to chat
function addMessage(message) {
  const messageId = Date.now();
  const messageDiv = document.createElement('div');
  messageDiv.className = `message message-${message.type}`;
  messageDiv.id = `message-${messageId}`;
  
  if (message.type === 'user') {
    messageDiv.innerHTML = `
      <div class="message-content">
        <strong>You:</strong>
        <p>${escapeHtml(message.content)}</p>
      </div>
    `;
  } else if (message.type === 'assistant') {
    const sourcesHtml = message.sources && message.sources.length > 0 
      ? generateSourcesHtml(message.sources)
      : '';
    
    messageDiv.innerHTML = `
      <div class="message-content">
        <strong>AI Assistant:</strong>
        <p>${escapeHtml(message.content)}</p>
        ${sourcesHtml}
        <div class="message-meta">
          <span class="severity-badge severity-${message.severity?.toLowerCase() || 'low'}">
            ${message.decision || 'SAFE'}
          </span>
        </div>
      </div>
    `;
  } else if (message.type === 'blocked') {
    messageDiv.innerHTML = `
      <div class="message-content">
        <strong>🚫 Response Blocked:</strong>
        <p>${escapeHtml(message.content)}</p>
        <div class="message-meta">
          <span class="severity-badge severity-${message.severity?.toLowerCase() || 'high'}">
            ${message.decision || 'BLOCKED'}
          </span>
          ${message.reason ? `<span class="reason">${escapeHtml(message.reason)}</span>` : ''}
        </div>
      </div>
    `;
  } else if (message.type === 'loading') {
    messageDiv.innerHTML = `
      <div class="message-content">
        <div class="loading-dots">
          <span></span><span></span><span></span>
        </div>
        <p>${escapeHtml(message.content)}</p>
      </div>
    `;
  } else if (message.type === 'error') {
    messageDiv.innerHTML = `
      <div class="message-content">
        <p style="color: #e53e3e;">${escapeHtml(message.content)}</p>
      </div>
    `;
  } else if (message.type === 'system') {
    messageDiv.innerHTML = `
      <div class="message-content">
        <p style="color: #718096; font-style: italic;">${escapeHtml(message.content)}</p>
      </div>
    `;
  }
  
  messagesContainer.appendChild(messageDiv);
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
  
  return messageId;
}

// Remove message
function removeMessage(messageId) {
  const messageDiv = document.getElementById(`message-${messageId}`);
  if (messageDiv) {
    messageDiv.remove();
  }
}

// Generate sources HTML
function generateSourcesHtml(sources) {
  if (!sources || sources.length === 0) return '';
  
  let html = '<div class="sources">';
  html += '<p><strong>📚 Evidence Sources:</strong></p>';
  
  sources.forEach(source => {
    const tier1 = source.tier1_sources || [];
    const tier2 = source.tier2_sources || [];
    
    if (tier1.length > 0) {
      html += '<div class="source-tier"><strong>Government/WHO Sources:</strong><ul>';
      tier1.forEach(s => {
        html += `<li><a href="${escapeHtml(s.url)}" target="_blank" title="${escapeHtml(s.title)}">${escapeHtml(s.title)}</a> <span class="confidence">(${s.confidence}% confidence)</span></li>`;
      });
      html += '</ul></div>';
    }
    
    if (tier2.length > 0) {
      html += '<div class="source-tier"><strong>Medical Research:</strong><ul>';
      tier2.forEach(s => {
        html += `<li><a href="${escapeHtml(s.url)}" target="_blank" title="${escapeHtml(s.title)}">${escapeHtml(s.title)}</a> <span class="confidence">(${s.confidence}% confidence)</span></li>`;
      });
      html += '</ul></div>';
    }
    
    html += `<p class="confidence-level">Confidence: <strong>${source.confidence_level || 'UNKNOWN'}</strong></p>`;
  });
  
  html += '</div>';
  return html;
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// Check backend status every 30 seconds
setInterval(checkBackendStatus, 30000);