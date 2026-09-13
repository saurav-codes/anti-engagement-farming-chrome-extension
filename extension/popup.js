/**
 * Popup script for Anti-Engagement-Farm
 * Wires up the switch, renders the blocked tweets log, and handles clearing the log.
 */

document.addEventListener('DOMContentLoaded', () => {
  console.log('[AEF] popup: DOMContentLoaded');
  const toggleInput = document.getElementById('toggleInput');
  const clearButton = document.getElementById('clearButton');
  const logList = document.getElementById('logList');
  const blockCount = document.getElementById('blockCount');
  const hoverHl = document.getElementById('hoverHl');

  // Reflect enabled state on the switch and body class
  function updateToggleUI(isEnabled) {
    toggleInput.checked = isEnabled;
    document.body.classList.toggle('on', isEnabled);
    document.body.classList.toggle('off', !isEnabled);
    console.log('[AEF] popup: state flipped to ' + (isEnabled ? 'on' : 'off'));
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

  // Render the blocked tweets list and the count
  function updateLogUI(tweets) {
    logList.innerHTML = '';
    const list = tweets || [];
    blockCount.textContent = String(list.length);
    if (list.length === 0) {
      const li = document.createElement('li');
      li.className = 'empty';
      li.textContent = 'Nothing blocked yet';
      logList.appendChild(li);
      return;
    }
    list.forEach(tweet => {
      const li = document.createElement('li');
      li.className = 'card';
      const snippet = document.createElement('div');
      snippet.className = 'snippet';
      snippet.textContent = `"${tweet.snippet || ''}"`;
      const meta = document.createElement('div');
      meta.className = 'meta';
      const author = tweet.author ? `@${tweet.author}` : '';
      meta.textContent = tweet.timestamp
        ? `${author} · ${timeAgo(tweet.timestamp)}`
        : author;
      li.append(snippet, meta);
      logList.appendChild(li);
    });
  }

  // Initialize UI state from storage
  chrome.storage.local.get(['isEnabled'], ({ isEnabled }) => {
    updateToggleUI(Boolean(isEnabled));
  });
  chrome.storage.local.get(['blockedTweets'], ({ blockedTweets }) => {
    updateLogUI(blockedTweets || []);
  });

  // Handle switch flips
  toggleInput.addEventListener('change', () => {
    console.log('[AEF] popup: toggle flipped');
    const newState = toggleInput.checked;
    chrome.storage.local.set({ isEnabled: newState }, () => {
      updateToggleUI(newState);
    });
  });

  // Handle clear log button clicks
  clearButton.addEventListener('click', () => {
    console.log('[AEF] popup: clear log clicked');
    chrome.storage.local.set({ blockedTweets: [] }, () => {
      updateLogUI([]);
    });
  });

  // Fluid hover: one highlight glides between cards via transform
  logList.addEventListener('mousemove', (e) => {
    const card = e.target.closest('.card');
    if (!card) {
      hoverHl.style.opacity = '0';
      return;
    }
    hoverHl.style.height = card.offsetHeight + 'px';
    hoverHl.style.transform = `translateY(${card.offsetTop}px)`;
    hoverHl.style.opacity = '1';
  });
  logList.addEventListener('mouseleave', () => {
    hoverHl.style.opacity = '0';
  });
});
