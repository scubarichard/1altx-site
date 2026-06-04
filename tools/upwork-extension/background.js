// Service worker — keeps extension registered in MV3.
// No alarm logic needed; content.js handles polling via setInterval.
chrome.runtime.onInstalled.addListener(() => {
  console.log('[1AltX] Upwork Feed extension installed.');
});
