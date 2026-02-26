// CoPilotForge Content Script
// Runs on github.com/copilot pages

(function() {
  'use strict';
  
  const SAVE_INTERVAL = 5 * 60 * 1000; // 5 minutes
  let saveTimer = null;
  let lastSavedContent = '';
  
  console.log('🔷 CoPilotForge: Extension loaded');
  
  // ============================================
  // EXTRACT CHAT CONTENT
  // ============================================
  function extractChatContent() {
    let content = '';
    const timestamp = new Date().toISOString();
    
    // Try multiple selectors (GitHub may change their DOM)
    const selectors = [
      '[data-testid="conversation"]',
      '.copilot-chat-container',
      'main[role="main"]',
      '.markdown-body',
      '[class*="conversation"]',
      '[class*="chat"]'
    ];
    
    for (const selector of selectors) {
      const elements = document.querySelectorAll(selector);
      if (elements.length > 0) {
        elements.forEach(el => {
          content += el.innerText + '\n\n';
        });
        break;
      }
    }
    
    // Fallback: get all visible text from main content
    if (!content.trim()) {
      const main = document.querySelector('main') || document.body;
      content = main.innerText;
    }
    
    // Add metadata
    const fullContent = `# CoPilotForge Auto-Save
URL: ${window.location.href}
Saved: ${timestamp}

---

${content}`;
    
    return fullContent;
  }
  
  // ============================================
  // SAVE TO LOCAL STORAGE + SEND TO BACKGROUND
  // ============================================
  function saveChat(reason = 'auto') {
    const content = extractChatContent();
    
    // Skip if no changes
    if (content === lastSavedContent) {
      console.log('🔷 CoPilotForge: No changes, skipping save');
      return;
    }
    
    lastSavedContent = content;
    
    const saveData = {
      type: 'SAVE_CHAT',
      content: content,
      url: window.location.href,
      timestamp: new Date().toISOString(),
      reason: reason
    };
    
    // Send to background script
    browser.runtime.sendMessage(saveData)
      .then(response => {
        console.log('🔷 CoPilotForge: Saved!', response);
        showNotification('💾 Chat saved');
      })
      .catch(err => {
        console.error('🔷 CoPilotForge: Save error', err);
      });
    
    // Also save to extension storage as backup
    browser.storage.local.set({
      lastChat: content,
      lastSave: new Date().toISOString(),
      lastUrl: window.location.href
    });
  }
  
  // ============================================
  // SHOW NOTIFICATION ON PAGE
  // ============================================
  function showNotification(message) {
    // Remove existing notification
    const existing = document.getElementById('copilotforge-notification');
    if (existing) existing.remove();
    
    // Create notification
    const notif = document.createElement('div');
    notif.id = 'copilotforge-notification';
    notif.innerHTML = `
      <div style="
        position: fixed;
        bottom: 20px;
        right: 20px;
        background: linear-gradient(135deg, #1e1b4b 0%, #312e81 100%);
        color: white;
        padding: 12px 20px;
        border-radius: 8px;
        font-family: system-ui, sans-serif;
        font-size: 14px;
        z-index: 999999;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        display: flex;
        align-items: center;
        gap: 8px;
        animation: slideIn 0.3s ease;
      ">
        <span style="font-size: 18px;">🔷</span>
        <span>${message}</span>
      </div>
      <style>
        @keyframes slideIn {
          from { transform: translateX(100px); opacity: 0; }
          to { transform: translateX(0); opacity: 1; }
        }
      </style>
    `;
    document.body.appendChild(notif);
    
    // Remove after 3 seconds
    setTimeout(() => notif.remove(), 3000);
  }
  
  // ============================================
  // START AUTO-SAVE TIMER
  // ============================================
  function startAutoSave() {
    if (saveTimer) clearInterval(saveTimer);
    
    saveTimer = setInterval(() => {
      console.log('🔷 CoPilotForge: Auto-saving...');
      saveChat('auto-5min');
    }, SAVE_INTERVAL);
    
    console.log('🔷 CoPilotForge: Auto-save started (every 5 min)');
    showNotification('Auto-save enabled ✓');
  }
  
  // ============================================
  // SAVE ON PAGE UNLOAD (Close/Navigate away)
  // ============================================
  window.addEventListener('beforeunload', () => {
    saveChat('page-close');
  });
  
  // ============================================
  // LISTEN FOR MESSAGES FROM POPUP/BACKGROUND
  // ============================================
  browser.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === 'MANUAL_SAVE') {
      saveChat('manual');
      sendResponse({ success: true });
    }
    if (message.type === 'GET_CONTENT') {
      sendResponse({ content: extractChatContent() });
    }
    return true;
  });
  
  // ============================================
  // INITIALIZE
  // ============================================
  startAutoSave();
  
  // Initial save after 10 seconds
  setTimeout(() => saveChat('initial'), 10000);
  
})();
