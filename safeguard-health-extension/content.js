// Content script - Runs on all web pages
// Detects medical content and shows safety overlay

const BACKEND_URL = 'http://localhost:3000/api/evaluate';

// Medical keywords to trigger evaluation
const MEDICAL_KEYWORDS = [
  'treatment', 'medicine', 'medication', 'drug', 'cure', 'diagnose',
  'symptom', 'disease', 'condition', 'doctor', 'patient', 'health',
  'tablet', 'pill', 'capsule', 'mg', 'ml', 'dosage', 'prescription'
];

// Track evaluated content to avoid duplicates
const evaluatedContent = new Set();

// Listen for messages from popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'evaluateSelection') {
    evaluateSelectedText();
    sendResponse({ status: 'started' });
  } else if (request.action === 'evaluatePage') {
    evaluatePageContent();
    sendResponse({ status: 'started' });
  }
  return true;
});

// Auto-detect medical content on page load
window.addEventListener('load', () => {
  // Wait a bit for dynamic content
  setTimeout(() => {
    const pageText = document.body.innerText;
    if (containsMedicalContent(pageText)) {
      console.log('🛡️ SAFEGUARD: Medical content detected on page');
      // Could auto-evaluate here or show a prompt
    }
  }, 2000);
});

// Detect if text contains medical content
function containsMedicalContent(text) {
  const lowerText = text.toLowerCase();
  return MEDICAL_KEYWORDS.some(keyword => lowerText.includes(keyword));
}

// Evaluate selected text
async function evaluateSelectedText() {
  const selection = window.getSelection().toString().trim();
  
  if (!selection) {
    showNotification('Please select some text first', 'info');
    return;
  }
  
  if (selection.length < 10) {
    showNotification('Selected text is too short', 'info');
    return;
  }
  
  // Check if already evaluated
  const contentHash = hashContent(selection);
  if (evaluatedContent.has(contentHash)) {
    showNotification('This content has already been evaluated', 'info');
    return;
  }
  
  await evaluateContent(selection, 'selection');
  evaluatedContent.add(contentHash);
}

// Evaluate entire page content
async function evaluatePageContent() {
  // Extract main content (skip headers, footers, nav)
  const mainContent = extractMainContent();
  
  if (!mainContent || mainContent.length < 50) {
    showNotification('No substantial content found on page', 'info');
    return;
  }
  
  await evaluateContent(mainContent, 'page');
}

// Extract main content from page
function extractMainContent() {
  // Try to find main content area
  const selectors = [
    'main', 'article', '[role="main"]', '.content', 
    '.main-content', '#content', '.post-content'
  ];
  
  for (const selector of selectors) {
    const element = document.querySelector(selector);
    if (element) {
      return element.innerText.trim();
    }
  }
  
  // Fallback to body text (first 5000 chars)
  return document.body.innerText.trim().substring(0, 5000);
}

// Main evaluation function
async function evaluateContent(content, source) {
  console.log(`🔍 Evaluating ${source} content...`);
  
  // Show loading overlay
  showLoadingOverlay();
  
  try {
    const response = await fetch(BACKEND_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        content: content,
        userContext: {}, // Could be collected from user
        imageData: null
      })
    });
    
    if (!response.ok) {
      throw new Error(`Backend error: ${response.status}`);
    }
    
    const result = await response.json();
    console.log('✅ Evaluation result:', result);
    
    // Show result overlay
    showResultOverlay(result, content);
    
  } catch (error) {
    console.error('❌ Evaluation failed:', error);
    showErrorOverlay(error.message);
  }
}

// Show loading overlay
function showLoadingOverlay() {
  removeExistingOverlay();
  
  const overlay = document.createElement('div');
  overlay.id = 'safeguard-overlay';
  overlay.className = 'safeguard-loading';
  overlay.innerHTML = `
    <div class="safeguard-modal">
      <div class="safeguard-header">
        <div class="safeguard-logo">🛡️ SAFEGUARD-Health</div>
      </div>
      <div class="safeguard-body">
        <div class="safeguard-spinner"></div>
        <p>Evaluating content safety...</p>
        <small>Checking rules, searching evidence, and making decision</small>
      </div>
    </div>
  `;
  
  document.body.appendChild(overlay);
}

// Show result overlay
function showResultOverlay(result, content) {
  removeExistingOverlay();
  
  const decision = result.decision;
  const severity = result.severity;
  const explanation = result.explanation;
  const details = result.details;
  
  // Determine color and icon based on decision
  const config = getDecisionConfig(decision);
  
  const overlay = document.createElement('div');
  overlay.id = 'safeguard-overlay';
  overlay.className = `safeguard-result safeguard-${decision.toLowerCase().replace('_', '-')}`;
  
  overlay.innerHTML = `
    <div class="safeguard-modal">
      <div class="safeguard-header" style="background: ${config.color}">
        <div class="safeguard-logo">🛡️ SAFEGUARD-Health</div>
        <button class="safeguard-close">✕</button>
      </div>
      
      <div class="safeguard-body">
        <div class="safeguard-decision-badge" style="background: ${config.color}">
          ${config.icon} ${config.label}
        </div>
        
        <div class="safeguard-severity">
          Severity: <span class="severity-${severity.toLowerCase()}">${severity}</span>
        </div>
        
        <div class="safeguard-explanation">
          ${explanation}
        </div>
        
        ${renderEvidenceSummary(details.evidence_summary)}
        
        ${renderRuleFlags(details.rule_flags)}
        
        <div class="safeguard-actions">
          ${config.actionButton}
          <button class="safeguard-btn-secondary safeguard-dismiss-btn">
            Dismiss
          </button>
        </div>
        
        <div class="safeguard-footer">
          <small>⚠️ This is a safety evaluation, not medical advice. Always consult healthcare professionals.</small>
        </div>
      </div>
    </div>
  `;
  
  document.body.appendChild(overlay);
  
  console.log('🛡️ Overlay added to page');
  
  // Add event listeners for buttons
  const dismissBtn = overlay.querySelector('.safeguard-dismiss-btn');
  if (dismissBtn) {
    console.log('✅ Dismiss button found, adding listener');
    dismissBtn.addEventListener('click', () => {
      console.log('🔘 Dismiss button clicked');
      overlay.remove();
    });
  } else {
    console.log('❌ Dismiss button NOT found');
  }
  
  const closeBtn = overlay.querySelector('.safeguard-close');
  if (closeBtn) {
    console.log('✅ Close button found, adding listener');
    closeBtn.addEventListener('click', () => {
      console.log('🔘 Close button clicked');
      overlay.remove();
    });
  } else {
    console.log('❌ Close button NOT found');
  }
  
  // Add event listeners for action buttons
  const actionBtns = overlay.querySelectorAll('.safeguard-action-btn');
  console.log(`✅ Found ${actionBtns.length} action buttons`);
  actionBtns.forEach((btn, index) => {
    btn.addEventListener('click', () => {
      const action = btn.getAttribute('data-action');
      console.log(`🔘 Action button ${index} clicked: ${action}`);
      handleActionButton(action);
    });
  });
  
  // Add click outside to close
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) {
      console.log('🔘 Clicked outside modal, closing');
      overlay.remove();
    }
  });
}

// Get decision configuration
function getDecisionConfig(decision) {
  const configs = {
    'REFUSE': {
      color: '#dc2626',
      icon: '🚫',
      label: 'CONTENT BLOCKED',
      actionButton: '<button class="safeguard-btn-danger safeguard-action-btn" data-action="visit-who">Visit WHO.int for Trusted Info</button>'
    },
    'ESCALATE': {
      color: '#f59e0b',
      icon: '⚠️',
      label: 'NEEDS REVIEW',
      actionButton: '<button class="safeguard-btn-warning safeguard-action-btn" data-action="contact-provider">Contact Healthcare Provider</button>'
    },
    'ASK_MORE_INFO': {
      color: '#3b82f6',
      icon: 'ℹ️',
      label: 'MORE INFO NEEDED',
      actionButton: '<button class="safeguard-btn-info safeguard-action-btn" data-action="show-info">What Info is Needed?</button>'
    },
    'ALLOW_WITH_WARNING': {
      color: '#eab308',
      icon: '⚡',
      label: 'PROCEED WITH CAUTION',
      actionButton: '<button class="safeguard-btn-warning safeguard-action-btn" data-action="learn-more">Learn More</button>'
    },
    'ALLOW': {
      color: '#16a34a',
      icon: '✅',
      label: 'CONTENT APPEARS SAFE',
      actionButton: ''
    }
  };
  
  return configs[decision] || configs['REFUSE'];
}

// Handle action button clicks
function handleActionButton(action) {
  switch(action) {
    case 'visit-who':
      window.open('https://www.who.int', '_blank');
      break;
    case 'contact-provider':
      showInfoModal('Contact Healthcare Provider', 
        'This content requires professional medical review. Please consult with your healthcare provider for personalized medical advice.');
      break;
    case 'show-info':
      showInfoModal('Information Needed', 
        'To properly evaluate medical content, we need:\n\n• Your age\n• Current symptoms\n• Medical history\n• When symptoms started (timeframe)\n\nThis helps ensure accurate safety assessment.');
      break;
    case 'learn-more':
      showInfoModal('Verify Information', 
        'This content has limited evidence support. Always:\n\n• Verify with healthcare professionals\n• Check multiple trusted sources\n• Consider your personal medical situation\n• Don\'t make health decisions based solely on online content');
      break;
  }
}

// Show info modal
function showInfoModal(title, message) {
  const modal = document.createElement('div');
  modal.className = 'safeguard-info-modal';
  modal.innerHTML = `
    <div class="safeguard-info-content">
      <h3>${title}</h3>
      <p style="white-space: pre-line;">${message}</p>
      <button class="safeguard-btn-secondary safeguard-info-close">Got It</button>
    </div>
  `;
  
  document.body.appendChild(modal);
  
  const closeBtn = modal.querySelector('.safeguard-info-close');
  closeBtn.addEventListener('click', () => modal.remove());
  
  modal.addEventListener('click', (e) => {
    if (e.target === modal) {
      modal.remove();
    }
  });
}

// Render evidence summary
function renderEvidenceSummary(evidenceSummary) {
  if (!evidenceSummary || evidenceSummary.length === 0) {
    return '';
  }
  
  let html = '<div class="safeguard-evidence"><h4>📊 Evidence Analysis</h4>';
  
  evidenceSummary.forEach(evidence => {
    html += `
      <div class="evidence-item">
        <div class="evidence-claim"><strong>Claim:</strong> ${truncateText(evidence.claim, 100)}</div>
        <div class="evidence-status">
          Status: <span class="status-${evidence.status.toLowerCase().replace('_', '-')}">${evidence.status}</span>
          <span class="confidence-badge">${evidence.confidence_level || 'UNKNOWN'} confidence</span>
        </div>
    `;
    
    // Show Tier 1 sources (highest priority)
    if (evidence.tier1_sources && evidence.tier1_sources.length > 0) {
      html += '<div class="evidence-sources"><strong>🏛️ Government/WHO Sources:</strong><ul>';
      evidence.tier1_sources.forEach(source => {
        html += `<li><a href="${source.url}" target="_blank">${source.title}</a> <span class="source-confidence">(${source.confidence}%)</span></li>`;
      });
      html += '</ul></div>';
    }
    
    // Show Tier 2 sources
    if (evidence.tier2_sources && evidence.tier2_sources.length > 0) {
      html += '<div class="evidence-sources"><strong>🏥 Research/Medical:</strong><ul>';
      evidence.tier2_sources.forEach(source => {
        html += `<li><a href="${source.url}" target="_blank">${source.title}</a> <span class="source-confidence">(${source.confidence}%)</span></li>`;
      });
      html += '</ul></div>';
    }
    
    html += '</div>';
  });
  
  html += '</div>';
  return html;
}

// Render rule flags
function renderRuleFlags(flags) {
  const activeFlags = Object.entries(flags).filter(([key, value]) => value === true);
  
  if (activeFlags.length === 0) {
    return '';
  }
  
  let html = '<div class="safeguard-flags"><h4>🚨 Safety Flags</h4><ul>';
  
  activeFlags.forEach(([flag, _]) => {
    const readableFlag = flag.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    html += `<li>⚠️ ${readableFlag}</li>`;
  });
  
  html += '</ul></div>';
  return html;
}

// Show error overlay
function showErrorOverlay(errorMessage) {
  removeExistingOverlay();
  
  const overlay = document.createElement('div');
  overlay.id = 'safeguard-overlay';
  overlay.className = 'safeguard-error';
  overlay.innerHTML = `
    <div class="safeguard-modal">
      <div class="safeguard-header" style="background: #dc2626">
        <div class="safeguard-logo">🛡️ SAFEGUARD-Health</div>
        <button class="safeguard-close">✕</button>
      </div>
      <div class="safeguard-body">
        <div class="safeguard-error-icon">❌</div>
        <h3>Evaluation Failed</h3>
        <p>${errorMessage}</p>
        <p><strong>Possible reasons:</strong></p>
        <ul>
          <li>Backend server not running (run: <code>python app.py</code>)</li>
          <li>Network connection issue</li>
          <li>API quota exceeded</li>
        </ul>
        <button class="safeguard-btn-secondary safeguard-dismiss-btn">
          Close
        </button>
      </div>
    </div>
  `;
  
  document.body.appendChild(overlay);
  
  // Add event listeners
  const dismissBtn = overlay.querySelector('.safeguard-dismiss-btn');
  if (dismissBtn) {
    dismissBtn.addEventListener('click', () => overlay.remove());
  }
  
  const closeBtn = overlay.querySelector('.safeguard-close');
  if (closeBtn) {
    closeBtn.addEventListener('click', () => overlay.remove());
  }
}

// Show notification
function showNotification(message, type = 'info') {
  const notification = document.createElement('div');
  notification.className = `safeguard-notification safeguard-notification-${type}`;
  notification.textContent = message;
  
  document.body.appendChild(notification);
  
  setTimeout(() => {
    notification.classList.add('show');
  }, 10);
  
  setTimeout(() => {
    notification.classList.remove('show');
    setTimeout(() => notification.remove(), 300);
  }, 3000);
}

// Helper functions
function removeExistingOverlay() {
  const existing = document.getElementById('safeguard-overlay');
  if (existing) {
    existing.remove();
  }
}

function truncateText(text, maxLength) {
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength) + '...';
}

function hashContent(content) {
  // Simple hash function for content deduplication
  let hash = 0;
  for (let i = 0; i < content.length; i++) {
    const char = content.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash;
  }
  return hash;
}

console.log('🛡️ SAFEGUARD-Health extension loaded');