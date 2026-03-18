from __future__ import annotations

from dataclasses import dataclass
from typing import List

from google import genai

from config.settings import settings


GEMINI_MODEL_NAME = "gemini-2.5-flash"


@dataclass(frozen=True)
class GeminiSummaryRequest:
    ticker: str
    reddit_snippets: List[str]
    news_snippets: List[str]
    display_name: str | None = None


@dataclass(frozen=True)
class FundamentalAuditRequest:
    ticker: str
    summary_text: str
    display_name: str | None = None


class GeminiClient:
    """
    I love AI Wrappers! Wrapper for Google GenAI SDK to generate a qualitative sentiment summary.
    """

    def __init__(self, model_name: str = GEMINI_MODEL_NAME) -> None:
        api_key = settings.api.gemini_api_key
        if not api_key:
            raise RuntimeError("Gemini API key is not configured.")

        self._client = genai.Client(api_key=api_key)
        self._model_name = model_name

    @staticmethod
    def _build_prompt(request: GeminiSummaryRequest) -> str:
        ticker = request.ticker.upper()
        display_name = request.display_name or f"{ticker} stock"

        system_prompt = (
            "You are a financial analyst specializing in equities. The ticker symbol "
            "{ticker} refers to the publicly traded company {display_name}. Treat all "
            "mentions of {ticker} strictly as this stock ticker and ignore any "
            "non-financial meanings (for example, military or political acronyms). "
            "Read the following recent news and Reddit discussions about {display_name}. "
            "Write a concise, one paragraph summary explaining the primary reasons "
            "behind the current retail and media sentiment."
        )

        header = system_prompt.format(ticker=ticker, display_name=display_name)

        parts: List[str] = [header, ""]

        if request.reddit_snippets:
            parts.append("Reddit posts:")
            for i, txt in enumerate(request.reddit_snippets, start=1):
                parts.append(f"{i}. {txt}")
            parts.append("")

        if request.news_snippets:
            parts.append("News articles:")
            for i, txt in enumerate(request.news_snippets, start=1):
                parts.append(f"{i}. {txt}")
            parts.append("")

        parts.append("Now provide your summary:")
        return "\n".join(parts)

    def summarize_sentiment(self, request: GeminiSummaryRequest) -> str:
        """
        Call Gemini to generate a single-paragraph sentiment summary.
        """
        prompt = self._build_prompt(request)
        response = self._client.models.generate_content(
            model=self._model_name,
            contents=prompt,
        )
        return getattr(response, "text", str(response))

    def generate_fundamental_audit(self, request: FundamentalAuditRequest) -> str:
        """
        Gemini to make response audit of company based on fundamental data
        """
        ticker = request.ticker.upper()
        display_name = request.display_name or f"{ticker} stock"

        system_prompt = (
            "Act as a strict financial auditor for publicly traded equities. Review "
            "the following financial information for {display_name}, whose ticker "
            "symbol is {ticker}. Treat all mentions of {ticker} strictly as this "
            "stock ticker and ignore any non-financial meanings (for example, "
            "military or political acronyms). If only a minority of key metrics are "
            "missing, still provide a normal audit and mention the gaps briefly. "
            "Reserve strong language such as 'audit impossible' or 'data is "
            "insufficient' only for cases where the majority of the core metrics "
            "(leverage, liquidity, profitability, and cash flow) are absent. "
            "Write a concise, one-paragraph summary of the company's balance sheet "
            "health, cash runway, and valuation risks."
        )

        header = system_prompt.format(ticker=ticker, display_name=display_name)

        prompt = f"{header}\n\nFinancial summary:\n{request.summary_text}\n\nAudit:"

        response = self._client.models.generate_content(
            model=self._model_name,
            contents=prompt,
        )
        return getattr(response, "text", str(response))
