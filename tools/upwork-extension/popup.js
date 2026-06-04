chrome.storage.local.get(['seenJobIds', 'sentCount', 'lastScanTime'], r => {
  document.getElementById('tracked').textContent = (r.seenJobIds || []).length;
  document.getElementById('sent').textContent = r.sentCount || 0;

  if (r.lastScanTime) {
    const d = new Date(r.lastScanTime);
    document.getElementById('lastScan').textContent =
      d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    document.getElementById('status').textContent = 'Feed active — monitoring Best Matches.';
    document.getElementById('status').style.background = '#f0fff4';
    document.getElementById('status').style.color = '#1a7a3a';
  }
});
