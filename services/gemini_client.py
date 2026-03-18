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


@dataclass(frozen=True)
class FundamentalAuditRequest:
    ticker: str
    summary_text: str


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
        system_prompt = (
            "You are a financial analyst. Read the following recent news and Reddit "
            "discussions about {ticker}. Write a concise, one paragraph summary "
            "explaining the primary reasons behind the current retail and media sentiment."
        )
        parts: List[str] = [system_prompt.format(ticker=request.ticker), ""]

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
        system_prompt = (
            "Act as a strict financial auditor. Review the following financial "
            "information for {ticker}. Write a concise, one-paragraph summary "
            "of the company's balance sheet health, cash runway, and valuation risks."
        ).format(ticker=request.ticker)

        prompt = f"{system_prompt}\n\nFinancial summary:\n{request.summary_text}\n\nAudit:"

        response = self._client.models.generate_content(
            model=self._model_name,
            contents=prompt,
        )
        return getattr(response, "text", str(response))
