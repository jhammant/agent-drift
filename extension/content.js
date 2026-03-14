/**
 * Agent Drift — Content Script
 * Detects AI chatbot widgets on pages and enables probing.
 */

const WIDGET_SELECTORS = {
  intercom: {
    frame: '#intercom-container iframe, .intercom-messenger-frame',
    launcher: '.intercom-launcher, #intercom-container',
    input: '.intercom-composer-send-button, [name="message"]',
    name: 'Intercom'
  },
  drift: {
    frame: '#drift-widget iframe, .drift-frame-controller',
    launcher: '#drift-widget, .drift-open-chat',
    input: '.drift-widget-message-input',
    name: 'Drift'
  },
  zendesk: {
    frame: '#webWidget iframe, iframe[title*="zendesk"], iframe[title*="Zendesk"]',
    launcher: '[data-testid="launcher"], #launcher',
    input: '[data-testid="message-field"]',
    name: 'Zendesk'
  },
  tidio: {
    frame: '#tidio-chat iframe, iframe[title*="Tidio"]',
    launcher: '#tidio-chat',
    input: null,
    name: 'Tidio'
  },
  crisp: {
    frame: '.crisp-client iframe',
    launcher: '.crisp-client',
    input: null,
    name: 'Crisp'
  },
  hubspot: {
    frame: '#hubspot-messages-iframe-container iframe',
    launcher: '#hubspot-messages-iframe-container',
    input: null,
    name: 'HubSpot'
  },
  freshdesk: {
    frame: 'iframe#freshworks-frame',
    launcher: '#freshworks-container',
    input: null,
    name: 'Freshdesk'
  },
  livechat: {
    frame: '#chat-widget iframe, iframe[title*="LiveChat"]',
    launcher: '#chat-widget',
    input: null,
    name: 'LiveChat'
  },
  generic: {
    frame: 'iframe[title*="chat" i], iframe[title*="support" i], iframe[title*="help" i], iframe[title*="assistant" i], iframe[title*="bot" i]',
    launcher: '[class*="chat-widget" i], [class*="chatbot" i], [id*="chat-widget" i], [id*="chatbot" i]',
    input: null,
    name: 'Chat Widget'
  }
};

function detectWidget() {
  for (const [key, config] of Object.entries(WIDGET_SELECTORS)) {
    const frame = document.querySelector(config.frame);
    const launcher = document.querySelector(config.launcher);
    if (frame || launcher) {
      return {
        type: key,
        name: config.name,
        hasFrame: !!frame,
        hasLauncher: !!launcher,
        element: frame || launcher
      };
    }
  }
  
  // Check for custom chat elements
  const chatElements = document.querySelectorAll(
    '[role="dialog"][aria-label*="chat" i], ' +
    '[role="complementary"][aria-label*="chat" i], ' +
    'div[class*="chat-container" i], ' +
    'div[class*="chatwindow" i], ' +
    'div[class*="chat-window" i]'
  );
  
  if (chatElements.length > 0) {
    return {
      type: 'custom',
      name: 'Custom Chat Widget',
      hasFrame: false,
      hasLauncher: true,
      element: chatElements[0]
    };
  }
  
  return null;
}

// Listen for detection requests from popup
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.action === 'detect') {
    const widget = detectWidget();
    sendResponse({ widget });
  }
  
  if (msg.action === 'getPageInfo') {
    sendResponse({
      url: window.location.href,
      title: document.title,
      domain: window.location.hostname
    });
  }
});

// Auto-detect and notify background
const widget = detectWidget();
if (widget) {
  chrome.runtime.sendMessage({ action: 'widgetFound', widget, url: window.location.href });
}
