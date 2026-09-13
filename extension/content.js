// Content script for Anti-Engagement-Farm
// Observes new tweets on the page, delegates classification to the service
// worker (which proxies the local model), hides engagement bait, and logs it.

(() => {
  console.log('[AEF] content: script loaded');

  const MAX_SNIPPET_LENGTH = 100;

  // Helper: extract tweet body text
  function getTweetBody(articleEl) {
    const nodes = articleEl.querySelectorAll('[data-testid="tweetText"] span');
    return Array.from(nodes).map(el => el.innerText).join(' ').trim();
  }

  // Hide a tweet element and record its info
  async function hideAndLog(articleEl, tweetInfo) {
    articleEl.style.display = 'none';
    try {
      const { blockedTweets = [] } = await chrome.storage.local.get('blockedTweets');
      if (!blockedTweets.some(t => t.id === tweetInfo.id)) blockedTweets.unshift(tweetInfo);
      await chrome.storage.local.set({ blockedTweets });
    } catch (err) {
      console.error('[AEF] content: failed to log blocked tweet, ' + err.message);
    }
  }

  // Extract tweet metadata from an article element
  function extractTweetInfo(articleEl) {
    let tweetId = null;
    let author = null;

    // Find link with status in href
    const link = articleEl.querySelector('a[href*="/status/"]');
    if (link) {
      const parts = link.getAttribute('href').split('/');
      if (parts.length >= 4) {
        author = parts[1];
        tweetId = parts[3];
      }
    }

    const text = getTweetBody(articleEl);
    const snippet = text.length > MAX_SNIPPET_LENGTH
      ? text.slice(0, MAX_SNIPPET_LENGTH) + '…'
      : text;

    const timestamp = Date.now();
    return { id: tweetId, author, snippet, timestamp };
  }

  // Decide whether to hide a tweet: enabled check, then ask the service worker
  async function shouldHideTweet(text) {
    const { isEnabled } = await new Promise(res => chrome.storage.local.get({ isEnabled: false }, res));
    if (!isEnabled) {
      console.log('[AEF] content: filter disabled, skipping');
      return null;
    }

    try {
      return await chrome.runtime.sendMessage({
        action: 'classifyTweet',
        text
      });
    } catch (err) {
      console.error('[AEF] content: classification error, ' + err.message);
      return null;
    }
  }

  // Process a single tweet article element
  async function processTweet(articleEl) {
    if (articleEl.__aefProcessed) return;
    articleEl.__aefProcessed = true;

    const text = getTweetBody(articleEl);
    const tweetInfo = extractTweetInfo(articleEl);
    if (!tweetInfo.id) return;

    const resp = await shouldHideTweet(text);
    if (resp && resp.hide === true) {
      console.log('[AEF] content: tweet hidden, label=' + resp.label + ' prob=' + resp.prob);
      await hideAndLog(articleEl, tweetInfo);
    }
  }

  // Observe additions in timeline container
  function setupObserver() {
    let timeline = document.querySelector('[aria-label="Timeline: Your Home Timeline"]');
    if (!timeline) {
      timeline = document.querySelector('[role="feed"]');
    }
    if (!timeline) {
      timeline = document.body;
    }

    const observer = new MutationObserver((mutations) => {
      for (const { addedNodes } of mutations) {
        addedNodes.forEach(node => {
          if (node.nodeType === Node.ELEMENT_NODE) {
            const articles = node.nodeName === 'ARTICLE'
              ? [node]
              : node.querySelectorAll('article[data-testid="tweet"]');
            articles.forEach(el => processTweet(el));
          }
        });
      }
    });

    observer.observe(timeline, {
      childList: true,
      subtree: true
    });

    // Process existing tweets on load
    timeline.querySelectorAll('article[data-testid="tweet"]').forEach(el => processTweet(el));
  }

  // Wait until DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setupObserver);
  } else {
    setupObserver();
  }
})();
