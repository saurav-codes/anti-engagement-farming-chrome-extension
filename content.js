// Content script for Anti-Engagement-Farm
// Observes new tweets on the page, applies a quick regex filter, optionally delegates to background for classification,
// hides the tweet if it is engagement bait, and logs hidden tweets to storage.

(() => {
  console.log('[AEF] content script loaded');
  const QUICK_PATTERNS = [
    /like\s*(and|&|or)?\s*retweet/i,
    /retweet\s*if/i,
    /tag\s*a\s*friend/i,
    /comment\s*(below|if)/i,
    /share\s*(this|if)/i,
    /follow\s*(for|and)/i
  ];

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
      blockedTweets.unshift(tweetInfo);
      await chrome.storage.local.set({ blockedTweets });
    } catch (err) {
      console.error('Failed to log blocked tweet', err);
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

  // Decide whether to hide a tweet
  async function shouldHideTweet(text) {
    // Check if filtering is enabled
    const { isEnabled } = await new Promise(res => chrome.storage.local.get({ isEnabled: false }, res));
    if (!isEnabled) {
      console.log('[AEF] shouldHideTweet: filter disabled; skipping');
      return false;
    }

    // dont process long tweets
    if (text.length > MAX_SNIPPET_LENGTH) {
      console.log('[AEF] shouldHideTweet: text too long (' + text.length + '), skipping classification');
      return false;
    }

    for (const re of QUICK_PATTERNS) {
      if (re.test(text)) {
        console.log('[AEF] shouldHideTweet: matched pattern', re);
        return true;
      }
    }
    // Fallback to background classification
    try {
      const resp = await chrome.runtime.sendMessage({
        action: 'classifyTweet',
        text
      });
      return resp && resp.hide === true;
    } catch (err) {
      console.error('Error classifying tweet', err);
      return false;
    }
  }

  // Process a single tweet article element
  async function processTweet(articleEl) {
    if (articleEl.__aefProcessed) return;
    articleEl.__aefProcessed = true;

    const text = getTweetBody(articleEl);
    const tweetInfo = extractTweetInfo(articleEl);
    if (!tweetInfo.id) return;

    const hide = await shouldHideTweet(text);
    if (hide) {
      console.log('[AEF] processTweet: tweet should be hidden -', text);
      await hideAndLog(articleEl, tweetInfo);
    } else {
      console.log('[AEF] processTweet: tweet is safe, not hiding');
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
