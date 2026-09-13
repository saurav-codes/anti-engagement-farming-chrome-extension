// X (Twitter) timeline collector. Paste into the browser console on x.com.
//   __farmCollector.start(2000)   // auto-scroll and collect up to 2000 tweets
//   __farmCollector.stop()       // stop scrolling
//   __farmCollector.data()       // array of {id, author, text}
//   __farmCollector.download()   // saves tweets.json
//   __farmCollector.clear()      // wipe collected data
// Survives page refreshes (localStorage). Run start() again to continue where you left off.
(() => {
  const KEY = "farm_collector_tweets";

  const load = () => {
    try {
      return new Map(JSON.parse(localStorage.getItem(KEY) || "[]").map((t) => [t.id, t]));
    } catch {
      return new Map();
    }
  };

  const save = (tweets) => {
    try {
      localStorage.setItem(KEY, JSON.stringify(tweets));
    } catch (e) {
      console.warn("[farm-collector] storage full, run download() now", e);
    }
  };

  function extract() {
    const tweets = load();
    for (const article of document.querySelectorAll('article[data-testid="tweet"]')) {
      const link = article.querySelector('a[href*="/status/"]');
      const text = article.querySelector('[data-testid="tweetText"]')?.innerText?.trim();
      const match = link?.href.match(/([^/?#]+)\/status\/(\d+)/);
      if (!match || !text) continue;
      const [, author, id] = match;
      if (!tweets.has(id)) tweets.set(id, { id, author, text });
    }
    save([...tweets.values()]);
    return tweets.size;
  }

  let timer = null;

  function start(max = 2000) {
    stop();
    let stall = 0;
    let last = extract();
    console.log(`[farm-collector] ${last} collected, scrolling...`);
    timer = setInterval(() => {
      window.scrollBy(0, window.innerHeight * (0.7 + Math.random() * 0.6));
      const count = extract();
      stall = count > last ? 0 : stall + 1;
      last = count;
      console.log(`[farm-collector] ${count}/${max}`);
      if (count >= max || stall >= 12) stop(); // no new tweets for ~18s means timeline exhausted
    }, 1500);
  }

  function stop() {
    if (timer) clearInterval(timer);
    timer = null;
  }

  function download() {
    const blob = new Blob([JSON.stringify(data(), null, 1)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "tweets.json";
    a.click();
    URL.revokeObjectURL(a.href);
  }

  function data() {
    return [...load().values()];
  }

  window.__farmCollector = { start, stop, data, download, clear: () => localStorage.removeItem(KEY) };
})();
