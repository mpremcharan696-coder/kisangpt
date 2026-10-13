"""
hf_image_service.py
===================
Agricultural Pictorial Representation Service for KrishiMitra AI.

Tries Hugging Face Inference API with user's token first.
If credits are not active (HTTP 402/410), seamlessly falls back to free
high-resolution agricultural image generation so the chatbot never crashes.
"""

from __future__ import annotations

import base64
import os
import urllib.parse
from typing import Any, Dict
import httpx
from dotenv import load_dotenv

load_dotenv()

HF_API_KEY = os.getenv("HUGGINGFACE_API_KEY", "")
HF_MODEL = "stabilityai/stable-diffusion-xl-base-1.0"
HF_ROUTER_URL = f"https://router.huggingface.co/hf-inference/models/{HF_MODEL}"
PREFER_FREE_ENGINE = os.getenv("PREFER_FREE_ENGINE", "true").lower() in ("true", "1", "yes")


def generate_agricultural_visual(prompt: str, timeout_sec: float = 30.0) -> Dict[str, Any]:
    """
    Generate an agricultural visual guide.
    Uses free high-definition visual engine directly for zero cost and fast response.
    Can also use Hugging Face if PREFER_FREE_ENGINE=false and a funded HF token is set.

    Returns:
        dict: {
            "status": "success" | "error",
            "provider": "free_visual_engine" | "huggingface" | "direct_url",
            "image_url": str,
            "image_base64": str (optional data URI),
            "prompt": str
        }
    """
    clean_prompt = prompt.strip()
    if not clean_prompt:
        return {"status": "error", "error": "Empty visual prompt."}

    enhanced_prompt = (
        f"Clear educational agricultural photograph of {clean_prompt}, "
        f"bright daylight, sharp focus, real Indian farming context, 4k"
    )

    # 1. Primary: High-speed Free Image Generator (Pollinations zero-cost engine)
    if PREFER_FREE_ENGINE or not HF_API_KEY or HF_API_KEY.startswith("your_"):
        try:
            encoded_prompt = urllib.parse.quote(enhanced_prompt)
            direct_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}"
            
            with httpx.Client(timeout=timeout_sec, follow_redirects=True) as client:
                res = client.get(direct_url)
                if res.status_code == 200 and len(res.content) > 1000:
                    b64 = base64.b64encode(res.content).decode("utf-8")
                    return {
                        "status": "success",
                        "provider": "free_visual_engine",
                        "image_url": f"data:image/jpeg;base64,{b64}",
                        "image_base64": f"data:image/jpeg;base64,{b64}",
                        "prompt": clean_prompt
                    }
        except Exception as free_err:
            print(f"[Free Visual Engine Error] {free_err}: Attempting fallbacks...")

    # 2. Try Hugging Face Inference API if explicitly enabled or if free engine had a glitch
    if HF_API_KEY and not HF_API_KEY.startswith("your_"):
        try:
            headers = {
                "Authorization": f"Bearer {HF_API_KEY}",
                "Content-Type": "application/json"
            }
            with httpx.Client(timeout=timeout_sec) as client:
                res = client.post(
                    HF_ROUTER_URL,
                    headers=headers,
                    json={"inputs": enhanced_prompt}
                )
                if res.status_code == 200 and "image" in res.headers.get("content-type", ""):
                    b64 = base64.b64encode(res.content).decode("utf-8")
                    return {
                        "status": "success",
                        "provider": "huggingface",
                        "image_url": f"data:image/jpeg;base64,{b64}",
                        "image_base64": f"data:image/jpeg;base64,{b64}",
                        "prompt": clean_prompt
                    }
        except Exception as hf_err:
            print(f"[HF Inference Error] {hf_err}")

    # 3. Return direct URL as ultimate resilient zero-failure fallback
    encoded_prompt = urllib.parse.quote(clean_prompt)
    return {
        "status": "success",
        "provider": "direct_url",
        "image_url": f"https://image.pollinations.ai/prompt/{encoded_prompt}",
        "image_base64": None,
        "prompt": clean_prompt
    }


if __name__ == "__main__":
    test_res = generate_agricultural_visual("finger millet ragi leaf blast disease spots")
    print("Visual Test Result:")
    print(" - Status:", test_res["status"])
    print(" - Provider:", test_res["provider"])
    print(" - Image URL/Data length:", len(test_res.get("image_url", "")))
