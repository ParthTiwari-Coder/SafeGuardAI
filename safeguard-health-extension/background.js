// Background service worker

// Listen for extension installation
chrome.runtime.onInstalled.addListener((details) => {
  if (details.reason === 'install') {
    console.log('🛡️ SAFEGUARD-Health installed successfully');
    
    // Open welcome page
    chrome.tabs.create({
      url: chrome.runtime.getURL('welcome.html')
    });
  } else if (details.reason === 'update') {
    console.log('🛡️ SAFEGUARD-Health updated');
  }
});

// Keep service worker alive
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log('Background received message:', request);
  sendResponse({ status: 'received' });
  return true;
});

console.log('🛡️ SAFEGUARD-Health background service worker loaded');