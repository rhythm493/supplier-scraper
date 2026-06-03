from __future__ import annotations

import functools
import logging
import os
import threading
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from scraper.config import Config

log = logging.getLogger(__name__)

_MODEL_LOCK = threading.Lock()
_MODEL_INSTANCE = None
_LLM_DISABLED = False
_LLM_FAILURES = 0
_MAX_LLM_FAILURES = 3


def _abort_handler(signum: int, _frame: object) -> None:
    global _LLM_DISABLED
    _LLM_DISABLED = True
    raise RuntimeError("LLM model crashed — disabling further LLM extraction")


_ABORT_HANDLER_INSTALLED = False


def _install_abort_handler() -> None:
    global _ABORT_HANDLER_INSTALLED
    if _ABORT_HANDLER_INSTALLED:
        return
    _ABORT_HANDLER_INSTALLED = True
    try:
        import signal
        if hasattr(signal, "SIGABRT"):
            signal.signal(signal.SIGABRT, _abort_handler)
    except Exception:
        pass


def _models_dir(config: Config) -> str:
    return os.path.join(config.cache_dir, "models")


def _model_path(config: Config) -> str:
    info = LLM_MODELS.get(config.llm_model)
    if not info:
        return ""
    fn = info.get("file", "")
    return os.path.join(_models_dir(config), str(fn)) if fn else ""


LLM_MODELS: dict[str, dict[str, str | int]] = {
    "LFM2-350M-Extract": {
        "repo": "QuantFactory/LFM2-350M-Extract-GGUF",
        "file": "LFM2-350M-Extract.Q4_K_M.gguf",
        "size_mb": 267,
        "desc": "Fastest extraction model (350M params)",
    },
    "LFM2-1.2B-Extract": {
        "repo": "LiquidAI/LFM2-1.2B-Extract-GGUF",
        "file": "LFM2-1.2B-Extract.Q4_K_M.gguf",
        "size_mb": 731,
        "desc": "More accurate extraction model (1.2B params)",
    },
    "NuExtract-1.5-smol": {
        "repo": "QuantFactory/NuExtract-1.5-smol-GGUF",
        "file": "NuExtract-1.5-smol.Q4_K_M.gguf",
        "size_mb": 1100,
        "desc": "High-accuracy extraction (1.7B params)",
    },
}


def is_model_downloaded(config: Config) -> bool:
    path = _model_path(config)
    return bool(path) and os.path.isfile(path)


def ensure_model(
    config: Config,
    on_status: Callable[[str], None] | None = None,
) -> str | None:
    path = _model_path(config)
    if not path:
        return None

    if os.path.isfile(path):
        log.info("Model already cached: %s", path)
        return path

    info = LLM_MODELS.get(config.llm_model)
    if not info:
        log.warning("Unknown model: %s", config.llm_model)
        return None

    os.makedirs(os.path.dirname(path), exist_ok=True)

    try:
        from huggingface_hub import hf_hub_download

        size = info.get("size_mb", 0)
        msg = f"Downloading AI model ({size} MB) — one-time"
        if on_status:
            on_status(msg)
        log.info("%s from %s", msg, info["repo"])

        hf_hub_download(
            repo_id=str(info["repo"]),
            filename=str(info["file"]),
            local_dir=os.path.dirname(path),
        )

        final_path = os.path.join(os.path.dirname(path), str(info["file"]))
        if final_path != path:
            import shutil

            shutil.move(final_path, path)

        if on_status:
            on_status(f"AI model downloaded ({size} MB)")
        log.info("Model downloaded: %s", path)
        return path

    except Exception as e:
        log.warning("Model download failed — falling back to regex extraction: %s", e)
        if on_status:
            on_status("Model download failed — using regex only")
        return None


def _load_model(config: Config) -> Any:
    global _MODEL_INSTANCE

    with _MODEL_LOCK:
        if _MODEL_INSTANCE is not None:
            return _MODEL_INSTANCE

        path = ensure_model(config)
        if not path:
            return None

        try:
            from llama_cpp import Llama

            _MODEL_INSTANCE = Llama(
                model_path=path,
                n_ctx=4096,
                n_threads=max((os.cpu_count() or 4) // 2, 1),
                verbose=False,
            )
            log.info("LLM model loaded: %s", path)
            return _MODEL_INSTANCE
        except Exception as e:
            log.warning("Failed to load LLM model: %s", e)
            return None


_EXTRACTION_SYSTEM_PROMPT = """\
You are a precise company information extractor. Extract fields from the website text below.

Return ONLY a JSON object with these fields (use null if not found):
- country: the company's country (from address/contact/location)
- state: state/province/region
- city: city/locality
- phone: phone number
- email: email address
- company_name: exact company name
- products: comma-separated product names or categories

Only extract values explicitly present in the text. Do not guess or infer."""

_VERIFY_SYSTEM_PROMPT = """\
Verify if the phone number's country code matches the stated country.
Return JSON: {"match": true/false, "correct_country": "country name or null"}"""


@functools.lru_cache(maxsize=1000)
def _cached_extract(page_text_hash: str, text_snippet: str, model_name: str) -> dict[str, Any]:
    """Cached extraction — hash of page text, not the text itself, to keep cache small."""
    return {}


def extract_fields(
    text: str,
    url: str,
    config: Config,
    fields: list[str] | None = None,
) -> dict[str, Any] | None:
    global _LLM_DISABLED, _LLM_FAILURES
    if _LLM_DISABLED:
        return None

    _install_abort_handler()
    model = _load_model(config)
    if model is None:
        return None

    try:
        truncated = text[:3000]
        prompt = _EXTRACTION_SYSTEM_PROMPT

        resp = model.create_chat_completion(
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": truncated},
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
            max_tokens=256,
        )

        content = resp["choices"][0]["message"]["content"]
        import json

        result = json.loads(content)

        if not isinstance(result, dict):
            return None

        allowed = {"country", "state", "city", "phone", "email", "company_name", "products"}
        result = {k: v for k, v in result.items() if k in allowed and v not in (None, "")}
        for k, v in result.items():
            if isinstance(v, str):
                result[k] = v.strip()

        return result if result else None

    except Exception as e:
        log.debug("LLM extraction failed for %s: %s", url, e)
        _LLM_FAILURES += 1
        if _LLM_FAILURES >= _MAX_LLM_FAILURES:
            _LLM_DISABLED = True
        return None


def verify_phone_country(phone: str, country: str, config: Config) -> bool | str | None:
    global _LLM_DISABLED, _LLM_FAILURES
    if _LLM_DISABLED:
        return None
    if phone == "Not Found" or country == "Not Found":
        return None

    _install_abort_handler()
    model = _load_model(config)
    if model is None:
        return None

    try:
        resp = model.create_chat_completion(
            messages=[
                {"role": "system", "content": _VERIFY_SYSTEM_PROMPT},
                {"role": "user", "content": f"Phone: {phone}\nStated country: {country}"},
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
            max_tokens=64,
        )

        content = resp["choices"][0]["message"]["content"]
        import json

        result = json.loads(content)

        if result.get("match"):
            return True
        correct = result.get("correct_country")
        if correct and isinstance(correct, str):
            return correct
        return False

    except Exception as e:
        log.debug("Phone-country verification failed: %s", e)
        _LLM_FAILURES += 1
        if _LLM_FAILURES >= _MAX_LLM_FAILURES:
            _LLM_DISABLED = True
        return None
