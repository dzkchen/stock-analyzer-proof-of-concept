const API_BASE = "http://localhost:8000";

function setText(id, text) {
  const el = document.getElementById(id);
  if (el) {
    el.textContent = text;
  }
}

function clampScore(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) {
    return 0;
  }
  return Math.max(0, Math.min(100, n));
}

function escapeHtml(text) {
  return String(text || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function normalizedTicker(value) {
  return String(value || "")
    .trim()
    .toUpperCase();
}

function renderTicker(payload) {
  const ticker = payload?.ticker || "";
  const source = payload?.source || "none";
  const confidence = payload?.confidence || "low";
  const url = payload?.url || "";
  const hasManualOverride = Boolean(payload?.hasManualOverride);

  setText("tickerValue", ticker || "--");
  setText(
    "tickerMeta",
    ticker
      ? `Source: ${source} | Confidence: ${confidence}${hasManualOverride ? " | Manual override active" : ""}`
      : "No ticker found. Use manual override."
  );
  setText("statusText", url ? `Page: ${url}` : "No active page.");
}

function drawScoreRows(scores = {}) {
  const container = document.getElementById("scoreBars");
  if (!container) {
    return;
  }

  const rows = [
    ["Overall", clampScore(scores.overall)],
    ["Technical", clampScore(scores.technical)],
    ["Fundamental", clampScore(scores.fundamental)],
    ["News", clampScore(scores.news)],
    ["Reddit", clampScore(scores.reddit)],
  ];

  container.innerHTML = rows
    .map(
      ([label, score]) => `
        <div class="score-row">
          <span class="score-label">${label}</span>
          <div class="track"><div class="fill" style="width:${score}%"></div></div>
          <span class="score-num">${score.toFixed(0)}</span>
        </div>
      `,
    )
    .join("");
}

function fillSourceList(listId, items, mapItem) {
  const list = document.getElementById(listId);
  if (!list) {
    return;
  }
  if (!Array.isArray(items) || items.length === 0) {
    list.innerHTML = "<li>None</li>";
    return;
  }

  list.innerHTML = items
    .slice(0, 10)
    .map(mapItem)
    .join("");
}

function renderAnalysis(data) {
  const scores = data?.scores || {};
  const overall = clampScore(scores.overall);
  setText("overallScore", `${overall.toFixed(1)} / 100`);
  drawScoreRows(scores);

  setText(
    "sentimentSummary",
    data?.market_sentiment_summary || "No sentiment summary available for this ticker.",
  );
  setText(
    "fundamentalAudit",
    data?.fundamental_audit_text || "No fundamental audit available for this ticker.",
  );

  fillSourceList("redditSources", data?.sources?.reddit, (item) => {
    const title = escapeHtml(item?.title || "Reddit thread");
    const subreddit = escapeHtml(item?.subreddit || "reddit");
    const url = escapeHtml(item?.url || "#");
    const ups = Number(item?.ups || 0);
    return `<li>[r/${subreddit}] <a href="${url}" target="_blank" rel="noreferrer noopener">${title}</a> (${ups} upvotes)</li>`;
  });

  fillSourceList("newsSources", data?.sources?.news, (item) => {
    const title = escapeHtml(item?.title || "News article");
    const source = escapeHtml(item?.source || "source");
    const url = escapeHtml(item?.url || "#");
    return `<li>[${source}] <a href="${url}" target="_blank" rel="noreferrer noopener">${title}</a></li>`;
  });
}

function sendMessage(payload) {
  return new Promise((resolve, reject) => {
    chrome.runtime.sendMessage(payload, (response) => {
      if (chrome.runtime.lastError) {
        reject(new Error(chrome.runtime.lastError.message));
        return;
      }
      resolve(response || {});
    });
  });
}

async function getTickerContext() {
  const response = await sendMessage({ type: "GET_ACTIVE_TAB_TICKER" });
  renderTicker(response || {});
  return response || {};
}

async function fetchAnalysis(ticker, exchange = "NASDAQ") {
  const url = `${API_BASE}/analyze?ticker=${encodeURIComponent(ticker)}&exchange=${encodeURIComponent(exchange)}`;
  const resp = await fetch(url, { method: "GET" });
  if (!resp.ok) {
    let detail = `HTTP ${resp.status}`;
    try {
      const err = await resp.json();
      if (err?.detail) {
        detail = err.detail;
      }
    } catch (_ignore) {}
    throw new Error(detail);
  }
  return resp.json();
}

async function runAnalysis() {
  setText("statusText", "Refreshing tab...");
  const ctx = await getTickerContext();
  const ticker = normalizedTicker(ctx?.ticker);

  if (!ticker) {
    setText("statusText", "No ticker. Set one, then refresh.");
    return;
  }

  setText("statusText", `Analyzing ${ticker}...`);
  try {
    const data = await fetchAnalysis(ticker, "NASDAQ");
    renderAnalysis(data);
    setText("statusText", `${ticker} loaded.`);
  } catch (error) {
    setText(
      "statusText",
      `API error: ${error.message}. Check ${API_BASE}.`,
    );
  }
}

async function onSetManualTicker() {
  const input = document.getElementById("manualTickerInput");
  const ticker = normalizedTicker(input?.value);

  if (!/^[A-Z]{1,6}$/.test(ticker)) {
    setText("statusText", "Invalid ticker. Use 1-6 letters (A-Z).");
    return;
  }

  try {
    const response = await sendMessage({ type: "SET_MANUAL_TICKER", ticker });
    if (!response.ok) {
      setText("statusText", response.error || "Unable to set manual ticker.");
      return;
    }
    setText("statusText", `Manual ticker set to ${ticker}.`);
    await runAnalysis();
  } catch (error) {
    setText("statusText", `Extension error: ${error.message}`);
  }
}

async function onClearManualTicker() {
  try {
    const response = await sendMessage({ type: "CLEAR_MANUAL_TICKER" });
    if (!response.ok) {
      setText("statusText", response.error || "Unable to clear manual ticker.");
      return;
    }
    setText("statusText", "Manual override cleared.");
    await runAnalysis();
  } catch (error) {
    setText("statusText", `Extension error: ${error.message}`);
  }
}

function bindEvents() {
  const setBtn = document.getElementById("setTickerBtn");
  const clearBtn = document.getElementById("clearTickerBtn");
  const refreshBtn = document.getElementById("refreshBtn");
  const input = document.getElementById("manualTickerInput");

  setBtn?.addEventListener("click", onSetManualTicker);
  clearBtn?.addEventListener("click", onClearManualTicker);
  refreshBtn?.addEventListener("click", async () => {
    try {
      await runAnalysis();
    } catch (error) {
      setText("statusText", `Extension error: ${error.message}`);
    }
  });
  input?.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      onSetManualTicker();
    }
  });
}

bindEvents();
runAnalysis();
