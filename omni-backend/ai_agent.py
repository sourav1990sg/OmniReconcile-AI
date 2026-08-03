import json
import os

import google.generativeai as genai


def generate_dispute_email(discrepancy_data: dict) -> str:
    """Draft a professional dispute email for a flagged reconciliation row via Gemini."""
    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Missing Gemini API key. Set GOOGLE_API_KEY or GEMINI_API_KEY in the environment."
        )

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    payload = json.dumps(discrepancy_data, ensure_ascii=True, default=str)
    prompt = f"""You are drafting a formal merchant dispute email for a food-delivery aggregator settlement shortfall.

Discrepancy data (JSON):
{payload}

Instructions:
- Write a highly professional, corporate, and concise dispute email addressed to the aggregator's merchant support team.
- Itemize the key order details from the JSON (Order ID, Date, Outlet, Expected Amount, Settled Amount, Discrepancy / missing amount, Status).
- Clearly demand an adjustment/credit for the exact missing amount shown by the discrepancy (use the absolute shortfall when Discrepancy is negative).
- Do not invent facts that are not present in the JSON.
- Do not use markdown, bullet symbols that look casual, or meta commentary.
- Sign off exactly as: Sourav, Outlet Admin
- Return ONLY the raw email text (include a Subject line as the first line). No preamble or closing notes outside the email."""

    response = model.generate_content(prompt)
    text = getattr(response, "text", None)
    if not text:
        raise RuntimeError("Gemini returned an empty response for the dispute email.")
    return text.strip()
