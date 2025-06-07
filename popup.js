/**
 * Popup script for Anti-Engagement-Farm
 * Wires up the toggle button, displays the blocked tweets log, and handles clearing the log.
 */

document.addEventListener('DOMContentLoaded', () => {
  console.log('[AEF] popup: DOMContentLoaded');
  const toggleButton = document.getElementById('toggleButton');
  const clearButton = document.getElementById('clearButton');
  const logList = document.getElementById('logList');

  // Update the toggle button UI based on whether filtering is enabled
  function updateToggleUI(isEnabled) {
    toggleButton.textContent = isEnabled ? 'Turn OFF' : 'Turn ON';
    toggleButton.classList.toggle('toggle-on', isEnabled);
    toggleButton.classList.toggle('toggle-off', !isEnabled);
  }

  // Format a timestamp into a relative "time ago" string
  function timeAgo(timestamp) {
    const diff = Date.now() - timestamp;
    const minute = 60 * 1000;
    const hour = 60 * minute;
    const day = 24 * hour;

    if (diff < minute) {
      return '<1m ago';
    } else if (diff < hour) {
      return Math.floor(diff / minute) + 'm ago';
    } else if (diff < day) {
      return Math.floor(diff / hour) + 'h ago';
    } else {
      return Math.floor(diff / day) + 'd ago';
    }
  }

  // Render the list of blocked tweets in the popup
  function updateLogUI(tweets) {
    logList.innerHTML = '';
    if (!tweets || tweets.length === 0) {
      const li = document.createElement('li');
      li.className = 'empty';
      li.textContent = '— No tweets hidden yet —';
      logList.appendChild(li);
      return;
    }
    tweets.forEach(tweet => {
      const li = document.createElement('li');
      const author = tweet.author ? `@${tweet.author}` : '';
      const snippet = tweet.snippet || '';
      const time = tweet.timestamp ? ` (${timeAgo(tweet.timestamp)})` : '';
      li.textContent = `${author}: "${snippet}"${time}`;
      logList.appendChild(li);
    });
  }

  // Initialize UI state from storage
  chrome.storage.local.get(['isEnabled'], ({ isEnabled }) => {
    console.log('[AEF] popup: isEnabled=', isEnabled);
    updateToggleUI(Boolean(isEnabled));
  });
  chrome.storage.local.get(['blockedTweets'], ({ blockedTweets }) => {
    console.log('[AEF] popup: blockedTweets=', blockedTweets);
    updateLogUI(blockedTweets || []);
  });

  // Handle toggle button clicks
  toggleButton.addEventListener('click', () => {
    console.log('[AEF] popup: toggle clicked');
    chrome.storage.local.get(['isEnabled'], ({ isEnabled }) => {
      const newState = !isEnabled;
      chrome.storage.local.set({ isEnabled: newState }, () => {
        updateToggleUI(newState);
      });
    });
  });

  // Handle clear log button clicks
  clearButton.addEventListener('click', () => {
    console.log('[AEF] popup: clear log clicked');
    chrome.storage.local.set({ blockedTweets: [] }, () => {
      updateLogUI([]);
    });
  });
});