// CoPilotForge Popup Script

document.addEventListener('DOMContentLoaded', async () => {
  // Load stats
  const data = await browser.storage.local.get(['lastSave', 'chatHistory']);
  
  if (data.lastSave) {
    const lastSave = new Date(data.lastSave);
    document.getElementById('last-save').textContent = formatTime(lastSave);
  }
  
  if (data.chatHistory) {
    document.getElementById('save-count').textContent = data.chatHistory.length;
  }
  
  // Save Now button
  document.getElementById('save-now').addEventListener('click', async () => {
    const tabs = await browser.tabs.query({ active: true, currentWindow: true });
    if (tabs[0]?.url?.includes('github.com/copilot')) {
      browser.tabs.sendMessage(tabs[0].id, { type: 'MANUAL_SAVE' });
      document.getElementById('save-now').textContent = '✅ Saved!';
      setTimeout(() => {
        document.getElementById('save-now').textContent = '💾 Save Now';
      }, 2000);
    } else {
      alert('Please open a GitHub Copilot chat first');
    }
  });
  
  // View History button
  document.getElementById('view-history').addEventListener('click', async () => {
    const data = await browser.storage.local.get('chatHistory');
    const history = data.chatHistory || [];
    
    if (history.length === 0) {
      alert('No saved chats yet');
      return;
    }
    
    // Open history in new tab
    const historyHtml = generateHistoryPage(history);
    const blob = new Blob([historyHtml], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    browser.tabs.create({ url });
  });
  
  // Export All button
  document.getElementById('export-all').addEventListener('click', async () => {
    const data = await browser.storage.local.get('chatHistory');
    const history = data.chatHistory || [];
    
    if (history.length === 0) {
      alert('No saved chats to export');
      return;
    }
    
    // Create markdown file
    let markdown = '# CoPilotForge - Chat Export\n\n';
    markdown += `Exported: ${new Date().toISOString()}\n\n`;
    markdown += '---\n\n';
    
    history.forEach((chat, i) => {
      markdown += `## Session ${i + 1}\n`;
      markdown += `**Time:** ${chat.timestamp}\n`;
      markdown += `**URL:** ${chat.url}\n\n`;
      markdown += chat.content + '\n\n';
      markdown += '---\n\n';
    });
    
    // Download
    const blob = new Blob([markdown], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `copilotforge-export-${Date.now()}.md`;
    a.click();
  });
});

function formatTime(date) {
  const now = new Date();
  const diff = now - date;
  
  if (diff < 60000) return 'Just now';
  if (diff < 3600000) return `${Math.floor(diff / 60000)} min ago`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)} hours ago`;
  return date.toLocaleDateString();
}

function generateHistoryPage(history) {
  return `
<!DOCTYPE html>
<html>
<head>
  <title>CoPilotForge History</title>
  <style>
    body {
      font-family: system-ui, sans-serif;
      max-width: 900px;
      margin: 0 auto;
      padding: 40px 20px;
      background: #0d1117;
      color: #e6edf3;
    }
    h1 { color: #8b5cf6; }
    .session {
      background: #161b22;
      border: 1px solid #30363d;
      border-radius: 8px;
      padding: 20px;
      margin-bottom: 20px;
    }
    .meta {
      font-size: 12px;
      color: #8b949e;
      margin-bottom: 12px;
    }
    pre {
      background: #0d1117;
      padding: 16px;
      border-radius: 6px;
      overflow-x: auto;
      white-space: pre-wrap;
    }
  </style>
</head>
<body>
  <h1>🔷 CoPilotForge History</h1>
  ${history.map((chat, i) => `
    <div class="session">
      <div class="meta">
        <strong>Session ${history.length - i}</strong> • 
        ${new Date(chat.timestamp).toLocaleString()} •
        ${chat.reason}
      </div>
      <pre>${escapeHtml(chat.content)}</pre>
    </div>
  `).reverse().join('')}
</body>
</html>
  `;
}

function escapeHtml(text) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}
