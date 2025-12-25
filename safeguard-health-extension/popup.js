// Popup script - Handles extension popup UI

const BACKEND_URL = 'http://localhost:3000/health';

// Check backend status on load
document.addEventListener('DOMContentLoaded', async () => {
  await checkBackendStatus();
  
  // Set up button listeners
  document.getElementById('evaluateSelection').addEventListener('click', evaluateSelection);
  document.getElementById('evaluatePage').addEventListener('click', evaluatePage);
  document.getElementById('openChat').addEventListener('click', openChat);
});

// Check if backend is running
async function checkBackendStatus() {
  const statusElement = document.getElementById('backendStatus');
  
  try {
    // Create timeout manually (compatible with all Chrome versions)
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 3000);
    
    const response = await fetch(BACKEND_URL, { 
      method: 'GET',
      signal: controller.signal
    });
    
    clearTimeout(timeoutId);
    
    if (response.ok) {
      const data = await response.json();
      statusElement.innerHTML = '<span class="online">● Online</span>';
      statusElement.className = 'status-value online';
    } else {
      throw new Error('Backend returned error');
    }
  } catch (error) {
    statusElement.innerHTML = '<span class="offline">● Offline</span>';
    statusElement.className = 'status-value offline';
    
    console.log('Backend check failed:', error.message);
  }
}

// Evaluate selected text
async function evaluateSelection() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  
  if (!tab) {
    alert('No active tab found');
    return;
  }
  
  // Send message to content script
  chrome.tabs.sendMessage(tab.id, { action: 'evaluateSelection' }, (response) => {
    if (chrome.runtime.lastError) {
      console.error('Error:', chrome.runtime.lastError);
      alert('Please refresh the page and try again');
    } else {
      window.close(); // Close popup after triggering evaluation
    }
  });
}

// Evaluate page content
async function evaluatePage() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  
  if (!tab) {
    alert('No active tab found');
    return;
  }
  
  // Send message to content script
  chrome.tabs.sendMessage(tab.id, { action: 'evaluatePage' }, (response) => {
    if (chrome.runtime.lastError) {
      console.error('Error:', chrome.runtime.lastError);
      alert('Please refresh the page and try again');
    } else {
      window.close(); // Close popup after triggering evaluation
    }
  });
}

// Open Protected AI Chat
async function openChat() {
  try {
    // Get current window
    const currentWindow = await chrome.windows.getCurrent();
    
    // Open side panel
    await chrome.sidePanel.open({ windowId: currentWindow.id });
    
    // Close popup
    window.close();
  } catch (error) {
    console.error('Error opening chat:', error);
    alert('Failed to open chat. Please try again.');
  }
}