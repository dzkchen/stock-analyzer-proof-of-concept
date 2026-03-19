function cleanTicker(value) {
  if (!value || typeof value !== "string") {
    return "";
  }
  const upper = value.toUpperCase().trim();
  if (!/^[A-Z]{1,6}$/.test(upper)) {
    return "";
  }
  return upper;
}

function isLikelyNoiseToken(token) {
  const noise = new Set([
    "USD",
    "CAD",
    "BUY",
    "SELL",
    "CALL",
    "PUT",
    "TFSA",
    "RRSP",
    "FHSA",
    "NEXT",
    "YTD",
  ]);
  return noise.has(token);
}

function extractTickerFromText(text) {
  if (!text) {
    return "";
  }

  const normalized = String(text).replace(/\s+/g, " ").trim();
  if (!normalized) {
    return "";
  }

  const companyPattern = normalized.match(
    /(?:^|\s)([A-Z]{1,6})(?=\s+[A-Z][a-z])/,
  );
  if (companyPattern?.[1]) {
    const ticker = cleanTicker(companyPattern[1]);
    if (ticker && !isLikelyNoiseToken(ticker)) {
      return ticker;
    }
  }

  const shortLabelPattern = normalized.match(/^(?:\$)?([A-Z]{1,6})(?:\b|$)/);
  if (shortLabelPattern?.[1]) {
    const ticker = cleanTicker(shortLabelPattern[1]);
    if (ticker && !isLikelyNoiseToken(ticker)) {
      return ticker;
    }
  }

  return "";
}

function fromWealthsimpleDom() {
  if (!window.location.hostname.includes("wealthsimple.com")) {
    return "";
  }

  const logoCandidates = document.querySelectorAll(
    "main#main img[data-testid='security-logo-image'][src*='_'], main img[data-testid='security-logo-image'][src*='_']",
  );
  for (const img of logoCandidates) {
    const src = img.getAttribute("src") || "";
    const match = src.match(/_[A-Z]{2,5}_([A-Z]{1,6})_(?:\d+x\d+)\.png/i);
    const ticker = cleanTicker(match?.[1] || "");
    if (ticker && !isLikelyNoiseToken(ticker)) {
      return ticker;
    }
  }

  const selectorCandidates = [
    "[data-qa='page-content-layout'] p",
    "main#main p",
    "header [class*='symbol']",
    "header [class*='ticker']",
    "header [class*='security']",
    "main [class*='symbol']",
    "main [class*='ticker']",
    "main [class*='security']",
    "header h1, header h2, header span, header div",
    "main h1, main h2, main span, main div",
  ];

  for (const selector of selectorCandidates) {
    const nodes = document.querySelectorAll(selector);
    for (const node of nodes) {
      const text = node.textContent || "";
      const ticker = extractTickerFromText(text);
      if (ticker) {
        return ticker;
      }
    }
  }

  const topRegion = document.querySelector("header, main") || document.body;
  const allNodes = topRegion.querySelectorAll("h1, h2, h3, span, div, p");
  for (const node of Array.from(allNodes).slice(0, 250)) {
    const text = (node.textContent || "").replace(/\s+/g, " ").trim();
    if (!text || text.length > 40) {
      continue;
    }
    const ticker = extractTickerFromText(text);
    if (ticker) {
      return ticker;
    }
  }

  return "";
}

function fromWealthsimpleTitle() {
  if (!window.location.hostname.includes("wealthsimple.com")) {
    return "";
  }
  const title = document.title || "";
  const match = title.match(/^([A-Z]{1,6})\s+\$/);
  const ticker = cleanTicker(match?.[1] || "");
  return ticker && !isLikelyNoiseToken(ticker) ? ticker : "";
}

function fromDom() {
  const selectorCandidates = [
    "[data-symbol]",
    "[data-testid='ticker']",
    "[data-test='ticker']",
    "[data-qa='symbol']",
    ".ticker",
    ".symbol",
    ".security-symbol",
    "h1",
  ];

  for (const selector of selectorCandidates) {
    const nodes = document.querySelectorAll(selector);
    for (const node of nodes) {
      const candidates = [
        node.getAttribute?.("data-symbol") || "",
        node.getAttribute?.("data-ticker") || "",
        node.textContent || "",
      ];

      for (const raw of candidates) {
        const ticker = extractTickerFromText(raw);
        if (ticker) {
          return ticker;
        }
      }
    }
  }

  return "";
}

function fromUrl() {
  const url = window.location.href;

  const patterns = [
    /[?&]symbol=([A-Za-z]{1,6})(?:[&#]|$)/,
    /\/quote\/([A-Za-z]{1,6})(?:[/?#]|$)/,
    /\/stocks?\/([A-Za-z]{1,6})(?:[/?#]|$)/,
    /\/symbol\/([A-Za-z]{1,6})(?:[/?#]|$)/,
  ];

  for (const pattern of patterns) {
    const match = url.match(pattern);
    const ticker = cleanTicker(match?.[1] || "");
    if (ticker) {
      return ticker;
    }
  }
  return "";
}

function fromTitle() {
  const title = document.title || "";
  return extractTickerFromText(title);
}

function detectTicker() {
  const urlTicker = fromUrl();
  if (urlTicker) {
    return { ticker: urlTicker, source: "url", confidence: "high" };
  }

  const wealthsimpleTicker = fromWealthsimpleDom();
  if (wealthsimpleTicker) {
    return { ticker: wealthsimpleTicker, source: "wealthsimple-dom", confidence: "high" };
  }

  const wealthsimpleTitleTicker = fromWealthsimpleTitle();
  if (wealthsimpleTitleTicker) {
    return { ticker: wealthsimpleTitleTicker, source: "wealthsimple-title", confidence: "high" };
  }

  const domTicker = fromDom();
  if (domTicker) {
    return { ticker: domTicker, source: "dom", confidence: "medium" };
  }

  const titleTicker = fromTitle();
  if (titleTicker) {
    return { ticker: titleTicker, source: "title", confidence: "low" };
  }

  return { ticker: "", source: "none", confidence: "low" };
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (!message || typeof message !== "object") {
    return;
  }
  if (message.type === "EXTRACT_TICKER_NOW") {
    sendResponse(detectTicker());
  }
});

function publishTicker() {
  const detected = detectTicker();
  chrome.runtime.sendMessage({
    type: "TICKER_DETECTED",
    ticker: detected.ticker,
    source: detected.source,
    confidence: detected.confidence,
  });
}

let lastPublishedKey = "";
function publishTickerIfChanged() {
  const detected = detectTicker();
  const nextKey = `${detected.ticker}|${detected.source}|${detected.confidence}`;
  if (nextKey === lastPublishedKey) {
    return;
  }
  lastPublishedKey = nextKey;
  chrome.runtime.sendMessage({
    type: "TICKER_DETECTED",
    ticker: detected.ticker,
    source: detected.source,
    confidence: detected.confidence,
  });
}

publishTicker();
window.addEventListener("popstate", publishTicker);
window.addEventListener("hashchange", publishTicker);
window.addEventListener("focus", publishTickerIfChanged);
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible") {
    publishTickerIfChanged();
  }
});

setInterval(publishTickerIfChanged, 1500);
