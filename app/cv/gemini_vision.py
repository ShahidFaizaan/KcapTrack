"""
KCapTrack — Gemini Vision Food Identification Module.

Uses Google's Gemini Vision API (gemini-2.5-flash / gemini-2.0-flash, free tier)
to identify food items in an uploaded image. Supplements the YOLO pipeline to
provide accurate recognition for global and regional cuisines not in COCO's
80 classes (e.g., Masala Dosa, Biryani, Idli, Sambar, Chutneys, Curries, etc.).

Pipeline:
    1. Encode image or pass directly to google-genai SDK.
    2. Send structured prompt asking for food items, portion masses, and macros.
    3. Parse JSON response → return list of food items + estimated macros and grams.
    4. Caller fuzzy-matches food names against the DB nutrition lookup or uses direct dietitian estimates.

Environment:
    GEMINI_API_KEY  – obtained free from https://aistudio.google.com/app/apikey

Free tier limits:
    - 1,500 requests/day (gemini-2.5-flash / gemini-2.0-flash)
    - No credit card required
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
#  Data model
# ---------------------------------------------------------------------------

class GeminiDetection:
    """A single food item returned by Gemini Vision."""

    def __init__(
        self,
        food_name: str,
        estimated_grams: float,
        confidence: float = 0.9,
        calories: float = 0.0,
        protein_g: float = 0.0,
        fat_g: float = 0.0,
        carbs_g: float = 0.0,
    ):
        self.food_name = food_name
        self.estimated_grams = estimated_grams
        self.confidence = confidence
        self.calories = calories
        self.protein_g = protein_g
        self.fat_g = fat_g
        self.carbs_g = carbs_g

    def __repr__(self) -> str:
        return f"GeminiDetection({self.food_name!r}, {self.estimated_grams}g, {self.calories}kcal)"


# ---------------------------------------------------------------------------
#  Prompt
# ---------------------------------------------------------------------------

_PROMPT = (
    "You are a professional dietitian and computer vision expert specializing in global and Indian food recognition.\n\n"
    "Analyze the food photo and identify ALL visible food items (e.g. Masala Dosa, Dosa, Coconut Chutney, Sambar, Pizza, Biryani, Rice, etc.).\n\n"
    "Return a valid JSON array where each element has:\n"
    '  - "food_name": string (specific common culinary name, e.g. "Masala Dosa", "Coconut Chutney", "Sambar")\n'
    '  - "estimated_grams": number (realistic portion weight in grams for what is shown on the plate)\n'
    '  - "confidence": number between 0.50 and 1.0\n'
    '  - "calories": number (estimated total kcal for this portion)\n'
    '  - "protein_g": number (estimated total protein in grams for this portion)\n'
    '  - "fat_g": number (estimated total fat in grams for this portion)\n'
    '  - "carbs_g": number (estimated total carbs in grams for this portion)\n\n'
    "RULES:\n"
    "- Distinguish main dish from side dips/chutneys/gravies separately (e.g., separate items for Dosa, Chutney, and Sambar).\n"
    "- Provide accurate dietitian-grade nutritional estimates based on the portion size.\n"
    "- Do NOT include non-food items (plates, spoons, cups, tables, napkins).\n"
    "- Return ONLY the JSON array, no markdown fences, no conversational text.\n\n"
    "Example output:\n"
    '[{"food_name":"Masala Dosa","estimated_grams":180,"confidence":0.96,"calories":330,"protein_g":6.5,"fat_g":9.0,"carbs_g":52.0},'
    '{"food_name":"Coconut Chutney","estimated_grams":40,"confidence":0.93,"calories":95,"protein_g":1.1,"fat_g":9.2,"carbs_g":2.8},'
    '{"food_name":"Sambar","estimated_grams":120,"confidence":0.92,"calories":72,"protein_g":3.0,"fat_g":1.8,"carbs_g":11.5}]'
)


# ---------------------------------------------------------------------------
#  Main API function
# ---------------------------------------------------------------------------

def identify_foods_with_gemini(
    image_path: str | Path,
    api_key: str,
) -> List[GeminiDetection]:
    """Call Gemini Vision to identify food items in an image.

    Args:
        image_path: Path to the image file on disk.
        api_key: Gemini API key (from https://aistudio.google.com/app/apikey).

    Returns:
        List of GeminiDetection objects (may be empty on failure).

    Raises:
        RuntimeError: If the API call fails across all available model endpoints.
    """
    image_path = Path(image_path)
    raw_text = _call_gemini_api(image_path, api_key)
    return _parse_gemini_response(raw_text)


def _call_gemini_api(image_path: Path, api_key: str) -> str:
    """Execute Gemini generateContent with automatic model fallback."""
    from PIL import Image

    pil_img = Image.open(image_path)
    last_err = None

    # 1. Try modern google-genai SDK (v2+)
    try:
        from google import genai
        client = genai.Client(api_key=api_key)

        candidate_models = [
            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemini-1.5-flash",
            "gemini-1.5-flash-latest",
            "gemini-1.5-pro",
        ]

        # Query live available models for this specific API key
        try:
            avail = [m.name for m in client.models.list()]
            flash_avail = [m.replace("models/", "") for m in avail if "flash" in m.lower()]
            if flash_avail:
                candidate_models = flash_avail + candidate_models
        except Exception as list_exc:
            logger.debug("Could not query model list: %s", list_exc)

        for model_name in candidate_models:
            clean_name = model_name.replace("models/", "")
            try:
                logger.info("Attempting Gemini Vision with model: %s", clean_name)
                response = client.models.generate_content(
                    model=clean_name,
                    contents=[_PROMPT, pil_img],
                )
                if response and response.text:
                    logger.info("Gemini (%s) recognition succeeded", clean_name)
                    return response.text.strip()
            except Exception as e:
                logger.warning("google.genai (%s) failed: %s", clean_name, e)
                last_err = e
                continue
    except ImportError:
        pass

    # 2. Try legacy google.generativeai SDK
    try:
        import google.generativeai as legacy_genai
        legacy_genai.configure(api_key=api_key)

        candidate_models = [
            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemini-1.5-flash-latest",
            "gemini-1.5-flash",
            "gemini-1.5-pro",
        ]
        try:
            avail = [
                m.name.replace("models/", "")
                for m in legacy_genai.list_models()
                if "generateContent" in getattr(m, "supported_generation_methods", [])
            ]
            flash_avail = [m for m in avail if "flash" in m.lower()]
            if flash_avail:
                candidate_models = flash_avail + candidate_models
        except Exception:
            pass

        for model_name in candidate_models:
            clean_name = model_name.replace("models/", "")
            try:
                logger.info("Attempting legacy google.generativeai with model: %s", clean_name)
                model = legacy_genai.GenerativeModel(clean_name)
                response = model.generate_content([_PROMPT, pil_img])
                if response and response.text:
                    logger.info("legacy google.generativeai (%s) succeeded", clean_name)
                    return response.text.strip()
            except Exception as e:
                logger.warning("legacy google.generativeai (%s) failed: %s", clean_name, e)
                last_err = e
                continue
    except Exception as e:
        last_err = e

    # 3. Direct REST API fallback via httpx (guaranteed standard HTTP)
    import base64
    import httpx

    img_b64 = base64.b64encode(image_path.read_bytes()).decode("utf-8")
    suffix = image_path.suffix.lower()
    mime_type = "image/png" if suffix == ".png" else "image/webp" if suffix == ".webp" else "image/jpeg"

    rest_models = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-flash-latest"]
    for m in rest_models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={api_key}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": _PROMPT},
                        {"inline_data": {"mime_type": mime_type, "data": img_b64}},
                    ]
                }
            ]
        }
        try:
            r = httpx.post(url, json=payload, timeout=30.0)
            if r.status_code == 200:
                resp_json = r.json()
                text = resp_json["candidates"][0]["content"]["parts"][0]["text"]
                logger.info("Direct REST API (%s) succeeded", m)
                return text.strip()
            else:
                logger.warning("REST API (%s) returned %d: %s", m, r.status_code, r.text[:200])
        except Exception as rest_err:
            logger.warning("REST API (%s) error: %s", m, rest_err)
            last_err = rest_err

    raise RuntimeError(f"All Gemini models and API methods failed. Last error: {last_err}")


# ---------------------------------------------------------------------------
#  Response parser
# ---------------------------------------------------------------------------

def _parse_gemini_response(raw_text: str) -> List[GeminiDetection]:
    """Extract list of GeminiDetection from Gemini's response text."""
    # Strip markdown code fences if present
    raw_text = re.sub(r"```(?:json)?", "", raw_text).strip().strip("`").strip()

    data = None
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError:
        # Try to extract a JSON array from mixed text
        match = re.search(r"\[.*?\]", raw_text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
            except json.JSONDecodeError:
                pass

    if data is None:
        logger.warning("Gemini response could not be parsed: %s", raw_text[:300])
        return []

    if not isinstance(data, list):
        data = [data]

    results: List[GeminiDetection] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        food_name = str(
            item.get("food_name") or item.get("name") or ""
        ).strip()
        if not food_name:
            continue
        try:
            grams = float(item.get("estimated_grams") or item.get("grams") or 150)
        except (TypeError, ValueError):
            grams = 150.0
        try:
            conf = float(item.get("confidence") or 0.85)
        except (TypeError, ValueError):
            conf = 0.85

        try:
            calories = float(item.get("calories") or item.get("kcal") or 0.0)
        except (TypeError, ValueError):
            calories = 0.0
        try:
            protein_g = float(item.get("protein_g") or item.get("protein") or 0.0)
        except (TypeError, ValueError):
            protein_g = 0.0
        try:
            fat_g = float(item.get("fat_g") or item.get("fat") or 0.0)
        except (TypeError, ValueError):
            fat_g = 0.0
        try:
            carbs_g = float(item.get("carbs_g") or item.get("carbs") or 0.0)
        except (TypeError, ValueError):
            carbs_g = 0.0

        results.append(
            GeminiDetection(
                food_name=food_name,
                estimated_grams=grams,
                confidence=conf,
                calories=calories,
                protein_g=protein_g,
                fat_g=fat_g,
                carbs_g=carbs_g,
            )
        )

    logger.info(
        "Gemini identified %d food item(s): %s",
        len(results),
        [r.food_name for r in results],
    )
    return results
