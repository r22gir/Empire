// CoPilotForge Background Script
// Handles saving to files via native messaging

const NATIVE_APP = 'copilotforge';

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
});

// ============================================
// SAVE TO FILE VIA NATIVE MESSAGING
// ============================================
async function saveToFile(data) {
  try {
    // Try native messaging first
    const response = await browser.runtime.sendNativeMessage(NATIVE_APP, data);
    console.log('🔷 Native save response:', response);
    return response;
  } catch (err) {
    console.log('🔷 Native messaging not available, using storage fallback');
    // Fallback: save to extension storage
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
  console.log('🔷 Saved to extension storage');
}

// ============================================
// HANDLE TAB CLOSE - TRIGGER FINAL SAVE
// ============================================
browser.tabs.onRemoved.addListener(async (tabId, removeInfo) => {
  // Try to save any pending content
  console.log('🔷 Tab closed, checking for pending saves');
});

// ============================================
// CONTEXT MENU FOR MANUAL SAVE
// ============================================
browser.contextMenus?.create({
  id: 'copilotforge-save',
  title: '🔷 Save Chat (CoPilotForge)',
  contexts: ['page'],
  documentUrlPatterns: ['https://github.com/copilot*']
});

browser.contextMenus?.onClicked.addListener((info, tab) => {
  if (info.menuItemId === 'copilotforge-save') {
    browser.tabs.sendMessage(tab.id, { type: 'MANUAL_SAVE' });
  }
});

console.log('🔷 CoPilotForge Background Script loaded');
