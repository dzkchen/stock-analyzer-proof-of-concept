<p align="center">
  <img src="images/chrome_extension_view.png" alt="Stock Analyzer Preview" width="700"/>
</p>

<h1 align="center">AI Stock Analyzer</h1>

<p align="center">
  <em>A proof-of-concept composite scoring engine for stocks, blending technicals, fundamentals, and sentiment.</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10+-blue?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/Streamlit-FF4B4B?logo=streamlit&logoColor=white" alt="Streamlit">
  <img src="https://img.shields.io/badge/Chrome_Extension-MV3-4285F4?logo=googlechrome&logoColor=white" alt="Chrome Extension">
  <img src="https://img.shields.io/badge/Gemini-LLM-8E75B2?logo=googlegemini&logoColor=white" alt="Gemini">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
</p>

> This is a prototype/proof of concep: not a complete product. 

---

## Features

| Feature | Description |
|---|---|
| **Composite AI Score** | Single 0–100 score blending Technical (40%), Fundamental (30%), News (20%), Reddit (10%) with gauge & breakdown |
| **Price & Sentiment Chart** | 30-day closing price + component score bar chart |
| **Market Sentiment Summary** | LLM-generated paragraph explaining Reddit & news sentiment |
| **Fundamental Audit** | Key ratios (P/E, D/E, current ratio, margins, FCF), snapshot stats, and LLM analysis |
| **Raw Feeds** | Links to top Reddit threads and news articles used in analysis |

## Demo

- **Chrome Extension** — [Watch demo (Google Drive)](https://drive.google.com/file/d/1ycOiLT8wyI3wJ9KmxLETN0Z1sHFXKF7c/view?usp=drive_link)
- **Streamlit App** — [Watch demo (Google Drive)](https://drive.google.com/file/d/1LL_yvjtx9mHEtB88KVigfsCgzYOP5B9I/view?usp=drive_link)

---

## Getting Started

### Prerequisites

- Python 3.10+
- [Gemini API key](https://ai.google.dev/)
- [NewsAPI key](https://newsapi.org/)

### Installation

```bash
git clone https://github.com/dzkchen/stock-analyzer-proof-of-concept
cd stock-analyzer-proof-of-concept
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Configuration

Create a `.env` file at the project root:

```env
GEMINI_API_KEY=""
NEWS_API_KEY=""
```

### Run

```bash
uvicorn api.server:app --reload --port 8000

streamlit run app.py
```

---

## Chrome Extension Setup

1. Navigate to `chrome://extensions` and enable Developer mode.
2. Click Load unpacked -> select the `extension/` folder.
3. Open a stock page (tested on Wealthsimple).
4. Open the side panel and click Refresh.

The extension will detect the ticker from the active tab (manual override available), call `localhost:8000/analyze`, and render the full analysis.

---

## About the Project

<details>
<summary><strong>Technical Indicators</strong></summary>

- Momentum & trend — RSI, MACD, SMA-20/50
- Volatility & price position — Bollinger Bands
- Short-term buying pressure — VWAP
</details>

<details>
<summary><strong>Fundamental Metrics</strong></summary>

- Liquidity — current ratio
- Leverage — debt-to-equity
- Profitability — profit & operating margins
- Valuation — forward P/E, free cash flow
</details>

<details>
<summary><strong>Sentiment Sources</strong></summary>

- News sentiment via NewsAPI + FinBERT
- Reddit sentiment via JSON requests + FinBERT
</details>

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python |
| Web UI | Streamlit |
| Extension UI | Chrome Extension (Manifest V3) |
| API | FastAPI + Uvicorn |
| Market Data | yfinance |
| Technical Indicators | pandas-ta |
| Social Data | Reddit JSON |
| News Data | NewsAPI |
| Sentiment Model | FinBERT |
| LLM | Gemini SDK |
| Charts | Plotly |

---

## Roadmap

- Switch Reddit scraping to official API (pending approval)
- Fine-tune composite scoring weights & add more factors
- Migrate UI from Streamlit to Flask / Django
- Fix edge cases for certain symbols (e.g., POW)
- Add options data & earnings surprises
- Portfolio mode via SnapTrade API
- Scenario learning prompts via Gemini
