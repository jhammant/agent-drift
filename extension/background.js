/**
 * Agent Drift — Background Service Worker
 * Handles widget detection state and badge updates.
 */

const detectedWidgets = new Map();

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.action === 'widgetFound' && sender.tab) {
    detectedWidgets.set(sender.tab.id, msg.widget);
    chrome.action.setBadgeText({ text: '!', tabId: sender.tab.id });
    chrome.action.setBadgeBackgroundColor({ color: '#f59e0b', tabId: sender.tab.id });
  }
  
  if (msg.action === 'getDetected') {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs[0]) {
        const widget = detectedWidgets.get(tabs[0].id);
        sendResponse({ widget: widget || null });
      }
    });
    return true; // async response
  }
});

// Clean up when tab closes
chrome.tabs.onRemoved.addListener((tabId) => {
  detectedWidgets.delete(tabId);
});
