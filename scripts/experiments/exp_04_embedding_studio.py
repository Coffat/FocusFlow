"""Experiment 0.4: Google AI Studio Embedding verification (no cobhub, no LLM_API_KEY)."""

from __future__ import annotations

import asyncio
import math
import time
from typing import Any

from common import (
    get_embedding_studio_api_key,
    sanitize_error_message,
    utc_timestamp,
    write_experiment_json,
)


def _l2_norm(vec: list[float]) -> float:
    return round(math.sqrt(sum(float(x) * float(x) for x in vec)), 6)


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    return round(dot / (na * nb), 6)


async def _probe_litellm_embedding(
    *,
    label: str,
    model: str,
    api_key: str,
    texts: list[str],
    extra_kwargs: dict[str, Any],
) -> dict[str, Any]:
    import litellm

    t0 = time.perf_counter()
    try:
        resp = await asyncio.wait_for(
            litellm.aembedding(
                model=model,
                input=texts,
                api_key=api_key,
                **extra_kwargs,
            ),
            timeout=20.0,
        )
        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 3)
        data = getattr(resp, "data", None)
        if isinstance(resp, dict):
            data = resp.get("data")
        vectors: list[list[float]] = []
        for item in data or []:
            emb = item.get("embedding") if isinstance(item, dict) else getattr(item, "embedding", None)
            if isinstance(emb, list):
                vectors.append([float(v) for v in emb])
        dims = [len(v) for v in vectors]
        norms = [_l2_norm(v) for v in vectors]
        return {
            "label": label,
            "sdk": "litellm.aembedding",
            "model": model,
            "extra_kwargs": extra_kwargs,
            "ok": True,
            "latency_ms": elapsed_ms,
            "vector_count": len(vectors),
            "dimensions": dims,
            "l2_norms": norms,
            "vectors_preview": [v[:4] for v in vectors],
            "_vectors": vectors,
        }
    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 3)
        return {
            "label": label,
            "sdk": "litellm.aembedding",
            "model": model,
            "extra_kwargs": extra_kwargs,
            "ok": False,
            "latency_ms": elapsed_ms,
            "error_type": type(exc).__name__,
            "error_message": sanitize_error_message(exc),
        }


async def _probe_google_genai_embedding(
    *,
    label: str,
    model: str,
    api_key: str,
    texts: list[str],
    output_dimensionality: int | None = None,
    task_type: str | None = None,
) -> dict[str, Any]:
    from google import genai
    from google.genai import types

    t0 = time.perf_counter()
    try:
        client = genai.Client(api_key=api_key)
        cfg_kwargs: dict[str, Any] = {}
        if output_dimensionality is not None:
            cfg_kwargs["output_dimensionality"] = output_dimensionality
        if task_type is not None:
            cfg_kwargs["task_type"] = task_type
        cfg = types.EmbedContentConfig(**cfg_kwargs) if cfg_kwargs else None

        resp = await asyncio.wait_for(
            client.aio.models.embed_content(
                model=model,
                contents=texts,
                config=cfg,
            ),
            timeout=20.0,
        )
        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 3)
        embeddings = getattr(resp, "embeddings", None) or []
        vectors = [[float(v) for v in (getattr(e, "values", None) or [])] for e in embeddings]
        dims = [len(v) for v in vectors]
        norms = [_l2_norm(v) for v in vectors]
        return {
            "label": label,
            "sdk": "google.genai",
            "model": model,
            "output_dimensionality": output_dimensionality,
            "task_type": task_type,
            "ok": True,
            "latency_ms": elapsed_ms,
            "vector_count": len(vectors),
            "dimensions": dims,
            "l2_norms": norms,
            "_vectors": vectors,
        }
    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 3)
        return {
            "label": label,
            "sdk": "google.genai",
            "model": model,
            "output_dimensionality": output_dimensionality,
            "task_type": task_type,
            "ok": False,
            "latency_ms": elapsed_ms,
            "error_type": type(exc).__name__,
            "error_message": sanitize_error_message(exc),
        }


async def _list_available_embedding_models(api_key: str) -> list[str]:
    from google import genai

    try:
        client = genai.Client(api_key=api_key)
        models = await asyncio.wait_for(
            asyncio.to_thread(lambda: list(client.models.list())),
            timeout=20.0,
        )
        found: list[str] = []
        for m in models:
            name = str(getattr(m, "name", "") or "")
            methods = list(getattr(m, "supported_actions", None) or [])
            if "embed" in name.lower() or any("embed" in str(a).lower() for a in methods):
                found.append(name)
        return sorted(found)
    except Exception as exc:
        return [f"LIST_ERROR: {sanitize_error_message(exc)}"]


async def main() -> None:
    api_key, key_source = get_embedding_studio_api_key()
    sample_docs = [
        "Python asyncio event loop and coroutines for concurrent I/O.",
        "SQLAlchemy 2.0 async session management and unit of work pattern.",
    ]
    sample_query = ["How does Python asyncio handle concurrent I/O?"]

    checks: list[dict[str, Any]] = []

    # 1. Model ID check in litellm.aembedding: gemini/gemini-embedding-2 vs gemini-embedding-2
    c1 = await _probe_litellm_embedding(
        label="litellm_prefix_default_dim",
        model="gemini/gemini-embedding-2",
        api_key=api_key,
        texts=sample_docs,
        extra_kwargs={},
    )
    checks.append(c1)

    c2 = await _probe_litellm_embedding(
        label="litellm_noprefix_default_dim",
        model="gemini-embedding-2",
        api_key=api_key,
        texts=sample_docs[:1],
        extra_kwargs={},
    )
    checks.append(c2)

    # 2. 768 dimensions via litellm (dimensions=768 vs output_dimensionality=768)
    c3 = await _probe_litellm_embedding(
        label="litellm_dimensions_768",
        model="gemini/gemini-embedding-2",
        api_key=api_key,
        texts=sample_docs,
        extra_kwargs={"dimensions": 768},
    )
    checks.append(c3)

    c4 = await _probe_litellm_embedding(
        label="litellm_output_dimensionality_768",
        model="gemini/gemini-embedding-2",
        api_key=api_key,
        texts=sample_docs,
        extra_kwargs={"output_dimensionality": 768},
    )
    checks.append(c4)

    # 3. task_type support in litellm
    c5 = await _probe_litellm_embedding(
        label="litellm_task_type_retrieval_document_768",
        model="gemini/gemini-embedding-2",
        api_key=api_key,
        texts=sample_docs,
        extra_kwargs={"dimensions": 768, "task_type": "RETRIEVAL_DOCUMENT"},
    )
    checks.append(c5)

    c6 = await _probe_litellm_embedding(
        label="litellm_task_type_retrieval_query_768",
        model="gemini/gemini-embedding-2",
        api_key=api_key,
        texts=sample_query,
        extra_kwargs={"dimensions": 768, "task_type": "RETRIEVAL_QUERY"},
    )
    checks.append(c6)

    # 4. Also probe google.genai SDK directly (in case model name differs or for task_type/output_dimensionality comparison)
    for model_cand in ("gemini-embedding-2-preview", "gemini-embedding-2", "gemini-embedding-001"):
        g_def = await _probe_google_genai_embedding(
            label=f"genai_{model_cand}_default",
            model=model_cand,
            api_key=api_key,
            texts=sample_docs[:1],
        )
        checks.append(g_def)
        if g_def["ok"]:
            g_doc = await _probe_google_genai_embedding(
                label=f"genai_{model_cand}_768_doc",
                model=model_cand,
                api_key=api_key,
                texts=sample_docs,
                output_dimensionality=768,
                task_type="RETRIEVAL_DOCUMENT",
            )
            g_qry = await _probe_google_genai_embedding(
                label=f"genai_{model_cand}_768_query",
                model=model_cand,
                api_key=api_key,
                texts=sample_query,
                output_dimensionality=768,
                task_type="RETRIEVAL_QUERY",
            )
            checks.extend([g_doc, g_qry])

    # Compute cosine similarity check if doc/query vectors succeeded
    retrieval_sanity: dict[str, Any] = {}
    for doc_chk, qry_chk, tag in (
        (c5, c6, "litellm_gemini_embedding_2"),
        *[
            (
                next((x for x in checks if x["label"] == f"genai_{m}_768_doc"), None),
                next((x for x in checks if x["label"] == f"genai_{m}_768_query"), None),
                f"genai_{m}",
            )
            for m in ("gemini-embedding-2-preview", "gemini-embedding-2", "gemini-embedding-001")
        ],
    ):
        if doc_chk and qry_chk and doc_chk.get("ok") and qry_chk.get("ok"):
            dvecs = doc_chk.get("_vectors", [])
            qvecs = qry_chk.get("_vectors", [])
            if len(dvecs) == 2 and len(qvecs) == 1:
                sim_relevant = _cosine_similarity(qvecs[0], dvecs[0])
                sim_other = _cosine_similarity(qvecs[0], dvecs[1])
                retrieval_sanity[tag] = {
                    "sim_relevant_doc": sim_relevant,
                    "sim_other_doc": sim_other,
                    "top1_correct": sim_relevant > sim_other,
                }

    available_embedding_models = await _list_available_embedding_models(api_key)

    # Strip raw _vectors before writing artifact
    clean_checks = [{k: v for k, v in chk.items() if k != "_vectors"} for chk in checks]
    for chk in clean_checks:
        print(
            f"[0.4] {chk['label']}: ok={chk['ok']} model={chk['model']} "
            f"dims={chk.get('dimensions')} norms={chk.get('l2_norms')} "
            f"err={chk.get('error_type')}",
            flush=True,
        )

    report = {
        "experiment": "0.4_embedding_studio",
        "timestamp": utc_timestamp(),
        "endpoint": "google_ai_studio_default",
        "api_key_source_env": key_source,
        "available_embedding_models": available_embedding_models,
        "retrieval_sanity": retrieval_sanity,
        "checks": clean_checks,
    }
    out = write_experiment_json("exp_04_embedding_studio.json", report)
    print(f"Saved: {out}")


if __name__ == "__main__":
    asyncio.run(main())
