const latestTickerByTab = new Map();
const manualTickerByTab = new Map();

function blankTickerState(url = "") {
  return {
    ticker: "",
    source: "none",
    confidence: "low",
    url,
  };
}

function applyManualTicker(tabId, basePayload, tabUrl) {
  const manualTicker = manualTickerByTab.get(tabId);
  if (manualTicker) {
    return {
      ticker: manualTicker,
      source: "manual",
      confidence: "high",
      url: tabUrl || basePayload?.url || "",
      hasManualOverride: true,
    };
  }

  return {
    ...(basePayload || blankTickerState(tabUrl || "")),
    url: tabUrl || basePayload?.url || "",
    hasManualOverride: false,
  };
}

function resolveTickerPayload(tabId, tabUrl) {
  const cached = latestTickerByTab.get(tabId) || blankTickerState(tabUrl || "");
  return applyManualTicker(tabId, cached, tabUrl);
}

function fetchLiveTickerFromTab(tabId, tabUrl, callback) {
  chrome.tabs.sendMessage(tabId, { type: "EXTRACT_TICKER_NOW" }, (response) => {
    if (chrome.runtime.lastError) {
      callback(resolveTickerPayload(tabId, tabUrl));
      return;
    }

    const ticker = typeof response?.ticker === "string" ? response.ticker.trim() : "";
    const payload = {
      ticker,
      source: response?.source || "unknown",
      confidence: response?.confidence || "low",
      url: tabUrl || "",
    };

    if (ticker) {
      latestTickerByTab.set(tabId, payload);
      callback(resolveTickerPayload(tabId, tabUrl));
      return;
    }

    callback(resolveTickerPayload(tabId, tabUrl));
  });
}

chrome.runtime.onInstalled.addListener(() => {
  chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true });
});

chrome.tabs.onRemoved.addListener((tabId) => {
  latestTickerByTab.delete(tabId);
  manualTickerByTab.delete(tabId);
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (!message || typeof message !== "object") {
    return;
  }

  if (message.type === "TICKER_DETECTED") {
    const tabId = sender.tab?.id;
    if (typeof tabId === "number" && typeof message.ticker === "string") {
      const ticker = message.ticker.trim();
      if (ticker) {
        latestTickerByTab.set(tabId, {
          ticker,
          source: message.source || "unknown",
          confidence: message.confidence || "low",
          url: sender.tab?.url || "",
        });
      }
    }
    return;
  }

  if (message.type === "GET_ACTIVE_TAB_TICKER") {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      const activeTab = tabs[0];
      const tabId = activeTab?.id;
      if (typeof tabId !== "number") {
        sendResponse({ ticker: "", source: "none", url: "" });
        return;
      }

      fetchLiveTickerFromTab(tabId, activeTab?.url || "", sendResponse);
    });
    return true;
  }

  if (message.type === "SET_MANUAL_TICKER") {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      const activeTab = tabs[0];
      const tabId = activeTab?.id;
      const ticker = typeof message.ticker === "string" ? message.ticker.trim().toUpperCase() : "";
      if (typeof tabId !== "number") {
        sendResponse({ ok: false, error: "No active tab." });
        return;
      }
      if (!/^[A-Z]{1,6}$/.test(ticker)) {
        sendResponse({ ok: false, error: "Ticker must be 1-6 letters." });
        return;
      }

      manualTickerByTab.set(tabId, ticker);
      sendResponse({ ok: true });
    });
    return true;
  }

  if (message.type === "CLEAR_MANUAL_TICKER") {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      const activeTab = tabs[0];
      const tabId = activeTab?.id;
      if (typeof tabId !== "number") {
        sendResponse({ ok: false, error: "No active tab." });
        return;
      }
      manualTickerByTab.delete(tabId);
      sendResponse({ ok: true });
    });
    return true;
  }
});
