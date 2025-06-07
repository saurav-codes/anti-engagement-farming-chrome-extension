/**
 * Background service worker for Anti-Engagement-Farm
 * Listens for classification requests from the content script and
 * proxies them to a backend service. Caches results in memory to
 * avoid duplicate API calls.
 */

console.log('[AEF] background worker loaded');
const BACKEND_URL = 'https://your-backend.example.com/api/classify'; // TODO: replace with your real endpoint

// Simple in-memory cache: text -> boolean (hide or not)
const classificationCache = new Map();

// On extension install, initialize storage defaults
chrome.runtime.onInstalled.addListener(() => {
  console.log('[AEF] onInstalled: initializing storage');
  chrome.storage.local.set({
    isEnabled: false,
    blockedTweets: []
  });
});

// Listen for messages from content scripts
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log('[AEF] onMessage received:', message);
  if (message.action === 'classifyTweet' && typeof message.text === 'string') {
    console.log('[AEF] classifyTweet request for snippet:', message.text.slice(0,50));
    // Check if filtering is currently enabled
    chrome.storage.local.get('isEnabled', ({ isEnabled }) => {
      if (!isEnabled) {
        // If user has turned off the filter, never hide
        console.log("service worker: user disabled our extension so returning hide as false")
        sendResponse({ hide: false });
      } else {
        // Otherwise, classify the tweet
        classifyTweet(message.text)
          .then(hide => sendResponse({ hide }))
          .catch(error => {
            console.error('Classification error:', error);
            sendResponse({ hide: false });
          });
      }
    });
    // Returning true indicates we'll call sendResponse asynchronously
    return true;
  }
});

/**
 * Sends the tweet text to the backend and returns whether to hide it.
 * Caches responses to avoid redundant network calls.
 *
 * @param {string} text - The full tweet text
 * @returns {Promise<boolean>} - True if the tweet should be hidden
 */
async function classifyTweet(text) {
  console.log('[AEF] classifyTweet invoked for snippet:', text.slice(0,50));
  // Return cached result if available
  if (classificationCache.has(text)) {
    console.log('[AEF] classifyTweet: cache hit');
    return classificationCache.get(text);
  }

  let shouldHide = false;
  console.log('[AEF] classifyTweet: cache miss, calling backend');
  try {
    const response = await fetch(BACKEND_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text })
    });

    if (!response.ok) {
          console.error('[AEF] Classification API returned status', response.status);
    } else {
          const result = await response.json();
          console.log('[AEF] Classification API result:', result);
          shouldHide = result.hide === true;
    }
  } catch (err) {
    console.error('Error calling classification API:', err);
  }

  classificationCache.set(text, shouldHide);
  return shouldHide;
}
