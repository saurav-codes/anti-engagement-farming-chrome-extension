Product Requirements Document (PRD)
Project: “Anti-Engagement-Farm” Chrome Extension (MVP v1.0)

1. Overview
• Problem: Twitter timelines are full of “like & retweet,” “tag a friend,” “comment below” tweets that add noise.
• Solution: A Chrome extension that, with one click, hides engagement-bait tweets using an OpenAI‐powered classifier behind your own API key, and shows a simple log of what was removed.

2. Objectives & Success Metrics
• Primary objective: Let users turn filtering on/off in one click and see what’s blocked.
• Success metrics (90 days after launch):
  – ≥ 500 active users
  – ≥ 80% of engagement-bait tweets removed (measured in dev tests)
  – ≥ 4.0 average rating (or positive feedback in GitHub issues/discussions)

3. Target Users
• Power users of Twitter (web) sick of low-value engagement-bait.
• Social-media pros who want to focus on real content.

4. Core Features (MVP)
1. Toggle Button
   – Single large ON/OFF button in the extension popup.
   – Persists state across browser restarts via chrome.storage.
2. Engagement-Bait Detection
   – Cheap local regex pass + OpenAI classification (using your embedded API key or your backend proxy).
   – MutationObserver in content script hides matching `<article[data-testid="tweet"]>`.
3. Blocked Tweets Log
   – In the popup UI, list recent tweets (text snippet + author handle) that were hidden this session.
   – “Clear Log” button.
4. Zero User Setup
   – No API key input by end users. You supply/manage the key.

5. User Flows
A. First Install
  1. User adds extension (unpacked or published).
  2. Default state = OFF.
  3. Opens popup → sees big “Turn ON” button and empty log.
B. Filtering
  1. Click “Turn ON.” State flips to ON and stored.
  2. Background/content script activates: starts observing tweets.
  3. Each new tweet: quick regex → if uncertain, call your backend or in-extension OpenAI API → if “bait,” hide it and append to log.
  4. User opens popup → sees list of hidden tweets (text + author).
C. Disable
  1. Click “Turn OFF.”
  2. Stop hiding tweets. Log stays until “Clear Log.”
D. Clear Log
  1. Click “Clear Log” → logs UI resets.

6. Technical Architecture
• Manifest V3
  – Permissions: “storage”, “scripting”
  – Host permissions: twitter.com/*, (optionally) your backend endpoint
  – Background: service_worker.js
  – Content script: content.js (run_at: document_idle)
  – Popup: popup.html + popup.js + popup.css
• Storage
  – chrome.storage.local:
    • isEnabled: bool
    • blockedTweets: array of { id, author, snippet, timestamp }
• Content Script (content.js)
  – MutationObserver on timeline container
  – Extract tweet text, id, author handle
  – quick regex → if match hide & log
  – else send text to background for classification
• Background Service Worker (background.js)
  – Listener for “classifyTweet” messages
  – Option A (quick): embed your OpenAI key, call ChatCompletion directly
  – Option B (better): proxy via your Django backend—POST /api/classify → returns yes/no
  – Caches recent texts in memory to avoid duplicate API calls
  – Replies to content script to hide or not
• Popup UI (popup.html/js)
  – Big toggle button reflects state from storage
  – List of blockedTweets, scrollable
  – “Clear Log” button

7. UI Mockup (textual)
Popup when OFF:
  [ Turn ON (green) ]
  — No tweets hidden yet —
Popup when ON & some blocked:
  [ Turn OFF (red) ]
  Blocked Tweets:
   • @alice: “Like & retweet if you agree!” (2m ago)
   • @bob: “Tag a friend who…” (5m ago)
  [ Clear Log ]

8. Development Roadmap
Week 1
  • Scaffold MV3 manifest, popup + toggle, storage logic
  • Stub content script + MutationObserver (no hiding yet)
Week 2
  • Implement quick-regex filter & in-memory log
  • Wire popup to show log & clear it
Week 3
  • Integrate OpenAI classification (direct key or Django proxy)
  • Add caching in background
Week 4
  • QA & edge‐case testing (infinite scroll, search pages, threads)
  • Prepare marketing assets: icon, screenshots, README, privacy note
  • Decide on distribution: paid Chrome Store vs. unpacked/GitHub

9. Distribution Strategy
• Short-term: Publish source + ZIP on GitHub Releases. In README instruct “Load unpacked” steps.
• Long-term: Pay $5 Chrome Developer fee → publish to Web Store for auto-updates and higher trust.

10. Risks & Mitigations
• Key leakage if bundled in extension → prefer a backend proxy that hides your key.
• Rate limits & cost → cache aggressively; reinforce quick regex.
• DOM selector changes → isolate selectors in one module for easy updates.
• False positives → keep regex conservative; allow easy disable.

11. Next Steps
1. Validate PRD with any collaborators.
2. Kick off Week 1 tasks in a private Git repo.
3. By end of Week 4, open pilot to small beta group.
4. Iterate on feedback; prepare for public release.

—
With this MVP PRD you can move quickly from concept to usable extension. Good luck!
