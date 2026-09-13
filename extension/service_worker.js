/**
 * Background service worker for Anti-Engagement-Farm
 * Thin proxy: forwards tweet classification requests to the local
 * BERT ONNX backend and logs every model verdict.
 */

const BACKEND_URL = 'http://127.0.0.1:8000/api/classify/';

// On extension install, initialize storage defaults
chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.local.set({
    isEnabled: false,
    blockedTweets: []
  });
});

// Listen for messages from content scripts
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === 'classifyTweet' && typeof message.text === 'string') {
    chrome.storage.local.get('isEnabled', ({ isEnabled }) => {
      if (!isEnabled) {
        console.log('[AEF] service worker: filter disabled, returning hide=false');
        sendResponse({ hide: false });
        return;
      }
      classifyTweet(message.text)
        .then(resp => sendResponse(resp))
        .catch(error => {
          console.error('[AEF] service worker: classification failed, ' + error.message);
          sendResponse({ hide: false });
        });
    });
    // Returning true keeps sendResponse valid for async use
    return true;
  }
});

// Flip the toolbar icon when filtering toggles
chrome.storage.onChanged.addListener((changes, area) => {
  if (area === 'local' && changes.isEnabled) {
    const variant = changes.isEnabled.newValue ? 'logo-on' : 'logo-off';
    chrome.action.setIcon({
      path: {
        16: `icons/${variant}-16.png`,
        32: `icons/${variant}-32.png`,
        48: `icons/${variant}-48.png`,
        128: `icons/${variant}-128.png`
      }
    });
    console.log('[AEF] service worker: toolbar icon flipped to ' + variant);
  }
});

/**
 * Posts the tweet text to the backend, logs the model verdict,
 * and returns { hide, label, prob }. Returns { hide: false } on any failure.
 */
async function classifyTweet(text) {
  const snippet = text.slice(0, 50);
  try {
    const response = await fetch(BACKEND_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text })
    });

    if (!response.ok) {
      console.error('[AEF] service worker: backend returned status ' + response.status + ' for "' + snippet + '"');
      return { hide: false };
    }

    const result = await response.json();
    console.log('[AEF] service worker: model verdict label=' + result.label + ' prob=' + result.prob + ' ms=' + result.ms + ' for "' + snippet + '"');
    return { hide: result.hide, label: result.label, prob: result.prob };
  } catch (err) {
    console.error('[AEF] service worker: fetch error for "' + snippet + '": ' + err.message);
    return { hide: false };
  }
}
