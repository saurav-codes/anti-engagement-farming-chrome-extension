// Smoke test for the service worker proxy. Run: node test/smoke.mjs
import { readFileSync } from 'node:fs';
import assert from 'node:assert';

const __dirname = new URL('.', import.meta.url).pathname;

// Minimal in-memory chrome.storage.local
const storageData = {};
const storage = {
  get(key, cb) {
    let result;
    if (typeof key === 'string') result = { [key]: storageData[key] };
    else if (Array.isArray(key)) { result = {}; for (const k of key) result[k] = storageData[k]; }
    else { result = {}; for (const [k, d] of Object.entries(key)) result[k] = storageData[k] !== undefined ? storageData[k] : d; }
    if (cb) { cb(result); return undefined; }
    return Promise.resolve(result);
  },
  set(obj, cb) {
    Object.assign(storageData, obj);
    if (cb) cb();
    return Promise.resolve();
  }
};

let messageHandler;
let onChangedHandler;
let iconPath = [];
globalThis.chrome = {
  storage: {
    local: storage,
    onChanged: { addListener: (cb) => { onChangedHandler = cb; } }
  },
  action: {
    setIcon: (opts, cb) => { iconPath = Object.values(opts.path); if (cb) cb(); }
  },
  runtime: {
    onInstalled: { addListener: (cb) => { messageHandler = null; cb(); } },
    onMessage: { addListener: (cb) => { messageHandler = cb; } },
    sendMessage: (msg) => new Promise(res => {
      messageHandler(msg, {}, (r) => { res(r); })
    })
  }
};

// Canned backend: bait hides, anything else is genuine
let fetchCalls = 0;
globalThis.fetch = async (_url, opts) => {
  fetchCalls++;
  const { text } = JSON.parse(opts.body);
  const isBait = text.includes('bait');
  return {
    ok: true,
    json: async () => isBait
      ? { hide: true, label: 'engagement_farming', prob: 0.97, ms: 1.8 }
      : { hide: false, label: 'genuine', prob: 0.02, ms: 1.7 }
  };
};

// Load the service worker with the stubs in place
new Function(readFileSync(__dirname + '../extension/service_worker.js', 'utf8'))();

async function run() {
  const send = (text) => chrome.runtime.sendMessage({ action: 'classifyTweet', text });

  // Enabled: bait text resolves hide:true with model details
  chrome.storage.local.set({ isEnabled: true });
  const bait = await send('please like and retweet this bait post');
  assert.strictEqual(bait.hide, true);
  assert.strictEqual(bait.label, 'engagement_farming');
  assert.strictEqual(bait.prob, 0.97);

  // Enabled: genuine text resolves hide:false
  const genuine = await send('a normal genuine thought');
  assert.strictEqual(genuine.hide, false);

  // Disabled: hide:false without calling fetch
  chrome.storage.local.set({ isEnabled: false });
  const before = fetchCalls;
  const disabled = await send('please like and retweet this bait post');
  assert.strictEqual(disabled.hide, false);
  assert.strictEqual(fetchCalls, before);

  // Icon flips to logo-on when filtering is enabled
  onChangedHandler({ isEnabled: { newValue: true } }, 'local');
  assert.ok(iconPath.every(p => p.includes('logo-on')));

  // Icon flips to logo-off when filtering is disabled
  onChangedHandler({ isEnabled: { newValue: false } }, 'local');
  assert.ok(iconPath.every(p => p.includes('logo-off')));

  // Other storage keys never flip the icon
  iconPath = [];
  onChangedHandler({ blockedTweets: { newValue: [] } }, 'local');
  assert.deepStrictEqual(iconPath, []);

  console.log('smoke: all assertions passed');
}

run().catch(err => { console.error('smoke: FAILED -', err); process.exit(1); });
