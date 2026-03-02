// CoPilotForge v2 Background Script
// Handles saving via native messaging, RAM monitoring, badge updates

const NATIVE_APP = 'copilotforge';
const RAM_CHECK_INTERVAL_MINUTES = 2;
const RAM_WARNING_MB = 3500;  // Warn at 3.5GB
const RAM_CRITICAL_MB = 4000; // Emergency save at 4GB

let lastRamWarningTime = 0;

// ============================================
// RECEIVE MESSAGES FROM CONTENT SCRIPT
// ============================================
browser.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'SAVE_CHAT') {
    saveToFile(message)
      .then(() => sendResponse({ success: true }))
      .catch(err => sendResponse({ success: false, error: err.message }));
    return true;
  }

  if (message.type === 'UPDATE_MESSAGE_COUNT') {
    browser.storage.local.set({ messageCount: message.count });
    // Show count on badge when approaching limit
    if (message.count >= 40) {
      updateBadge(String(message.count), '#f59e0b');
    }
  }
});

// ============================================
// SAVE TO FILE VIA NATIVE MESSAGING
// ============================================
async function saveToFile(data) {
  try {
    const response = await browser.runtime.sendNativeMessage(NATIVE_APP, data);
    console.log('CoPilotForge: Native save response:', response);
    return response;
  } catch (err) {
    console.log('CoPilotForge: Native messaging not available, using storage fallback');
    await saveToStorage(data);
  }
}

// ============================================
// FALLBACK: SAVE TO EXTENSION STORAGE
// ============================================
async function saveToStorage(data) {
  const stored = await browser.storage.local.get('chatHistory') || { chatHistory: [] };
  const history = stored.chatHistory || [];

  history.push({
    content: data.content,
    url: data.url,
    timestamp: data.timestamp,
    reason: data.reason
  });

  // Keep last 50 saves
  if (history.length > 50) {
    history.shift();
  }

  await browser.storage.local.set({ chatHistory: history });
  console.log('CoPilotForge: Saved to extension storage');
}

// ============================================
// RAM MONITORING VIA ALARMS + NATIVE HOST
// ============================================
browser.alarms.create('ram-check', {
  periodInMinutes: RAM_CHECK_INTERVAL_MINUTES
});

browser.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === 'ram-check') {
    checkFirefoxRam();
  }
});

async function checkFirefoxRam() {
  try {
    const response = await browser.runtime.sendNativeMessage(NATIVE_APP, {
      type: 'CHECK_RAM'
    });

    if (response && response.firefox_mb) {
      const mbUsed = response.firefox_mb;

      if (mbUsed >= RAM_CRITICAL_MB) {
        // Emergency: save on all copilot tabs immediately
        triggerEmergencySave('critical-ram');
        updateBadge('!!', '#dc2626');
      } else if (mbUsed >= RAM_WARNING_MB) {
        const now = Date.now();
        // Only warn once per 10 minutes
        if (now - lastRamWarningTime > 10 * 60 * 1000) {
          lastRamWarningTime = now;
          updateBadge('RAM', '#f59e0b');
          triggerEmergencySave('warning-ram');
        }
      } else {
        // Clear badge (unless message count is high)
        const data = await browser.storage.local.get('messageCount');
        if (!data.messageCount || data.messageCount < 40) {
          updateBadge('', '');
        }
      }

      // Store for popup display
      browser.storage.local.set({ firefoxRamMb: mbUsed });
    }
  } catch (err) {
    // Native host not available — RAM check not possible
    console.log('CoPilotForge: RAM check unavailable (native host not connected)');
  }
}

// ============================================
// TRIGGER EMERGENCY SAVE ON ALL COPILOT TABS
// ============================================
async function triggerEmergencySave(reason) {
  const tabs = await browser.tabs.query({ url: 'https://github.com/copilot*' });
  for (const tab of tabs) {
    try {
      await browser.tabs.sendMessage(tab.id, {
        type: 'EMERGENCY_SAVE',
        reason: reason
      });
    } catch (e) {
      // Tab may not have content script loaded
    }
  }
}

// ============================================
// BADGE HELPER
// ============================================
function updateBadge(text, color) {
  browser.browserAction.setBadgeText({ text: text });
  if (color) {
    browser.browserAction.setBadgeBackgroundColor({ color: color });
  }
}

// ============================================
// HANDLE TAB CLOSE
// ============================================
browser.tabs.onRemoved.addListener(async (tabId, removeInfo) => {
  console.log('CoPilotForge: Tab closed, checking for pending saves');
});

// ============================================
// CONTEXT MENU FOR MANUAL SAVE
// ============================================
browser.contextMenus?.create({
  id: 'copilotforge-save',
  title: 'Save Chat (CoPilotForge)',
  contexts: ['page'],
  documentUrlPatterns: ['https://github.com/copilot*']
});

browser.contextMenus?.onClicked.addListener((info, tab) => {
  if (info.menuItemId === 'copilotforge-save') {
    browser.tabs.sendMessage(tab.id, { type: 'MANUAL_SAVE' });
  }
});

console.log('CoPilotForge v2 Background Script loaded');
