// CoPilotForge v2 Content Script
// Runs on github.com/copilot pages
// Features: auto-save, SHA-256 dedup, message counter, session limit, RAM warnings

(function() {
  'use strict';

  const SAVE_INTERVAL = 5 * 60 * 1000; // 5 minutes
  const MESSAGE_CHECK_INTERVAL = 30 * 1000; // 30 seconds
  const MESSAGE_LIMIT = 50;

  let saveTimer = null;
  let lastSavedHash = '';
  let messageCount = 0;
  let warningBannerShown = false;

  console.log('CoPilotForge v2: Extension loaded');

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

    const fullContent = `# CoPilotForge Auto-Save
URL: ${window.location.href}
Saved: ${timestamp}
Messages: ${messageCount}

---

${content}`;

    return fullContent;
  }

  // ============================================
  // COUNT MESSAGES IN DOM
  // ============================================
  function countMessages() {
    const messageSelectors = [
      '[data-testid="conversation"] [data-testid="message"]',
      '.copilot-chat-container .message',
      '[class*="conversation"] [class*="message"]',
      '[role="log"] [role="article"]',
      'main [data-turn]',
      '[class*="turn"]',
      '[class*="message-content"]'
    ];

    for (const selector of messageSelectors) {
      const messages = document.querySelectorAll(selector);
      if (messages.length > 0) {
        return messages.length;
      }
    }

    // Fallback: count substantial text blocks in main
    const main = document.querySelector('main');
    if (main) {
      const blocks = main.querySelectorAll('[class*="response"], [class*="request"], [class*="answer"], [class*="prompt"]');
      if (blocks.length > 0) return blocks.length;
    }

    return 0;
  }

  // ============================================
  // CHECK MESSAGE COUNT
  // ============================================
  function checkMessageCount() {
    const count = countMessages();
    messageCount = count;

    // Report count to background for popup display
    browser.runtime.sendMessage({
      type: 'UPDATE_MESSAGE_COUNT',
      count: messageCount
    }).catch(() => {});

    // At limit: emergency save + warning banner
    if (messageCount >= MESSAGE_LIMIT && !warningBannerShown) {
      saveChat('message-limit-reached');
      showWarningBanner();
      warningBannerShown = true;
    }
  }

  // ============================================
  // SHA-256 CONTENT HASH
  // ============================================
  async function hashContent(str) {
    const encoder = new TextEncoder();
    const data = encoder.encode(str);
    const hashBuffer = await crypto.subtle.digest('SHA-256', data);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
  }

  // ============================================
  // SAVE TO LOCAL STORAGE + SEND TO BACKGROUND
  // ============================================
  async function saveChat(reason = 'auto') {
    const content = extractChatContent();

    // Skip if no changes (SHA-256 dedup)
    const contentHash = await hashContent(content);
    if (contentHash === lastSavedHash) {
      console.log('CoPilotForge: No changes (hash match), skipping save');
      return;
    }
    lastSavedHash = contentHash;

    const saveData = {
      type: 'SAVE_CHAT',
      content: content,
      url: window.location.href,
      timestamp: new Date().toISOString(),
      reason: reason,
      messageCount: messageCount
    };

    // Send to background script
    browser.runtime.sendMessage(saveData)
      .then(response => {
        console.log('CoPilotForge: Saved!', response);
        showNotification('Chat saved');
      })
      .catch(err => {
        console.error('CoPilotForge: Save error', err);
      });

    // Also save to extension storage as backup
    browser.storage.local.set({
      lastChat: content,
      lastSave: new Date().toISOString(),
      lastUrl: window.location.href
    });
  }

  // ============================================
  // SHOW NOTIFICATION (transient toast)
  // ============================================
  function showNotification(message) {
    const existing = document.getElementById('copilotforge-notification');
    if (existing) existing.remove();

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
        animation: cpf-slideIn 0.3s ease;
      ">
        <span style="font-size: 16px; font-weight: 600;">CPF</span>
        <span>${message}</span>
      </div>
      <style>
        @keyframes cpf-slideIn {
          from { transform: translateX(100px); opacity: 0; }
          to { transform: translateX(0); opacity: 1; }
        }
      </style>
    `;
    document.body.appendChild(notif);
    setTimeout(() => notif.remove(), 3000);
  }

  // ============================================
  // SHOW WARNING BANNER (persistent, for limits)
  // ============================================
  function showWarningBanner() {
    const existing = document.getElementById('copilotforge-warning');
    if (existing) return;

    const banner = document.createElement('div');
    banner.id = 'copilotforge-warning';
    banner.innerHTML = `
      <div style="
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%);
        color: white;
        padding: 12px 20px;
        font-family: system-ui, sans-serif;
        font-size: 14px;
        z-index: 9999999;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 4px 20px rgba(0,0,0,0.4);
      ">
        <span>
          <strong>CoPilotForge:</strong> ${messageCount} messages reached.
          Long chats increase memory and crash risk.
          Chat auto-saved. Start a new chat.
        </span>
        <div style="display: flex; gap: 8px;">
          <a href="https://github.com/copilot" target="_blank"
             style="background: white; color: #dc2626; padding: 6px 16px;
                    border-radius: 4px; text-decoration: none; font-weight: 600;
                    font-size: 13px;">
            New Chat
          </a>
          <button onclick="this.closest('#copilotforge-warning').remove()"
                  style="background: rgba(255,255,255,0.2); color: white;
                         border: none; padding: 6px 12px; border-radius: 4px;
                         cursor: pointer; font-size: 13px;">
            Dismiss
          </button>
        </div>
      </div>`;
    document.body.prepend(banner);
  }

  // ============================================
  // START AUTO-SAVE TIMER
  // ============================================
  function startAutoSave() {
    if (saveTimer) clearInterval(saveTimer);

    saveTimer = setInterval(() => {
      console.log('CoPilotForge: Auto-saving...');
      saveChat('auto-5min');
    }, SAVE_INTERVAL);

    console.log('CoPilotForge: Auto-save started (every 5 min)');
    showNotification('Auto-save enabled');
  }

  // ============================================
  // SAVE ON PAGE UNLOAD
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
    if (message.type === 'EMERGENCY_SAVE') {
      saveChat('emergency-ram');
      showWarningBanner();
      sendResponse({ success: true });
    }
    return true;
  });

  // ============================================
  // INITIALIZE
  // ============================================
  startAutoSave();

  // Initial save after 10 seconds (let DOM settle)
  setTimeout(() => saveChat('initial'), 10000);

  // Start message counter
  setInterval(checkMessageCount, MESSAGE_CHECK_INTERVAL);
  setTimeout(checkMessageCount, 5000);

})();
