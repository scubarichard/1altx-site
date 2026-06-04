// Runs on Best Matches page. Scans for new jobs every 60s and posts to n8n.

const WEBHOOK = 'https://n8n.dakona.net/webhook/upwork-extension';
const POLL_MS = 60000;

function extractJobs() {
  const jobs = [];
  // Upwork job card selectors (as of 2026)
  const cards = document.querySelectorAll('[data-test="job-tile"], article[data-ev-label="job_tile"], section[data-test="JobTile"]');

  cards.forEach(card => {
    try {
      const titleEl = card.querySelector('h2 a, [data-test="job-tile-title"] a, h3 a');
      if (!titleEl) return;

      const title = titleEl.textContent.trim();
      const href = titleEl.getAttribute('href') || '';
      const url = href.startsWith('http') ? href : 'https://www.upwork.com' + href;

      // Extract job ID from URL
      const idMatch = url.match(/~(\d+)/);
      if (!idMatch) return;
      const jobId = idMatch[1];

      // Description / snippet
      const descEl = card.querySelector('[data-test="job-description-text"], .job-description, p');
      const description = descEl ? descEl.textContent.trim().slice(0, 2000) : '';

      // Budget
      const budgetEl = card.querySelector('[data-test="budget"], [class*="budget"]');
      const budget = budgetEl ? budgetEl.textContent.trim() : '';

      jobs.push({ jobId, title, url, description, budget });
    } catch (e) {
      // skip malformed card
    }
  });

  return jobs;
}

async function loadSeen() {
  return new Promise(resolve => {
    chrome.storage.local.get(['seenJobIds'], r => resolve(new Set(r.seenJobIds || [])));
  });
}

async function saveSeen(seen) {
  // Keep last 500 to avoid unbounded growth
  const arr = [...seen].slice(-500);
  return new Promise(resolve => chrome.storage.local.set({ seenJobIds: arr }, resolve));
}

async function postJob(job) {
  try {
    const res = await fetch(WEBHOOK, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        jobId: job.jobId,
        jobTitle: job.title,
        upworkUrl: job.url,
        emailBody: job.description,
        budget: job.budget,
        source: 'extension',
        emailDate: new Date().toISOString(),
      }),
    });
    return res.ok;
  } catch (e) {
    return false;
  }
}

async function scan() {
  const jobs = extractJobs();
  chrome.storage.local.set({ lastScanTime: new Date().toISOString() });
  if (!jobs.length) return;

  const seen = await loadSeen();
  const newJobs = jobs.filter(j => !seen.has(j.jobId));
  if (!newJobs.length) return;

  console.log(`[1AltX] Found ${newJobs.length} new jobs`);

  let sent = 0;
  for (const job of newJobs) {
    const ok = await postJob(job);
    if (ok) {
      seen.add(job.jobId);
      sent++;
      console.log(`[1AltX] Sent: ${job.title}`);
    }
  }

  await saveSeen(seen);

  if (sent > 0) {
    const { sentCount = 0 } = await new Promise(r => chrome.storage.local.get(['sentCount'], r));
    chrome.storage.local.set({ sentCount: sentCount + sent });
  }
}

// Initial scan + polling
scan();
setInterval(scan, POLL_MS);

// Also scan on DOM mutations (new jobs loaded dynamically)
let debounce;
new MutationObserver(() => {
  clearTimeout(debounce);
  debounce = setTimeout(scan, 2000);
}).observe(document.body, { childList: true, subtree: true });
