#!/usr/bin/env python3
"""
Adapt the CV to better match a specific job offer.

Reads CV from cv/curriculum.md, accepts a job offer and matcher result,
calls One API LLM to generate an adapted CV and cover letter, and saves
them to cv/adapted/.

Usage:
    python3 adapt.py --offer '{"title": "...", ...}' --match '{"score": 65, ...}'
    echo '{"offer": {...}, "match": {...}}' | python3 adapt.py
"""

import argparse
import hashlib
import json
import logging
import os
import re
import sys
import urllib.error
import urllib.request

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stderr,
)
log = logging.getLogger("cv_adapter")

ONE_API_URL = "http://localhost:3001/v1/chat/completions"
DEFAULT_MODEL = "llama-3.1-8b-instant"


def _project_root() -> str:
    dir_ = os.path.dirname(os.path.abspath(__file__))
    for _ in range(6):
        if os.path.isdir(os.path.join(dir_, "cv")) and os.path.isfile(
            os.path.join(dir_, "cv", "curriculum.md")
        ):
            return dir_
        parent = os.path.dirname(dir_)
        if parent == dir_:
            break
        dir_ = parent
    return "/app"


def load_cv(root: str) -> str:
    path = os.path.join(root, "cv", "curriculum.md")
    with open(path, "r") as f:
        return f.read()


def compute_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sanitize_offer_id(offer: dict) -> str:
    raw = offer.get("url", "") + "|" + offer.get("title", "")
    sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", raw)
    return re.sub(r"_+", "_", sanitized).strip("_")[:120] or "offer"


def build_prompt(cv: str, offer: dict, match: dict) -> str:
    return f"""Eres un asistente de adaptacion de hojas de vida para el mercado laboral colombiano. Genera una version adaptada del CV y una carta de presentacion para una oferta de trabajo especifica.

REGLAS ESTRICTAS (NO VIOLAR):
1. NO inventes, modifiques ni extrapoles experiencia, fechas, cargos, empresas o certificaciones (Regla 9).
2. El CV es la UNICA fuente de verdad. Todo lo que escribas debe ser trazable al CV original (Regla 10).
3. Solo puedes: (a) REORDENAR habilidades existentes para priorizar las mas relevantes a la oferta, (b) REFORMULAR la seccion de resumen/perfil manteniendo los hechos intactos, (c) DESTACAR experiencia existente que se relacione con habilidades solicitadas en la oferta.
4. La carta de presentacion puede enfatizar habilidades blandas y motivacion, pero debe ser veraz.
5. NO cambies datos personales, fechas, cargos, empresas ni logros cuantitativos.

=== CV ORIGINAL ===
{cv}
=== FIN DEL CV ===

=== OFERTA DE TRABAJO ===
{json.dumps(offer, ensure_ascii=False, indent=2)}
=== FIN DE LA OFERTA ===

=== RESULTADO DEL MATCH ===
{json.dumps(match, ensure_ascii=False, indent=2)}
=== FIN DEL MATCH ===

Responde UNICAMENTE con un objeto JSON valido, sin markdown, sin bloques de codigo, sin texto adicional. Usa esta estructura exacta:
{{
  "adapted_cv": "# Andrés Felipe Botache Rojas\\n\\n**Agente de Contact Center ...**\\n\\n... (CV completo adaptado segun las reglas)",
  "cover_letter": "Cali, ...\\n\\nEstimado equipo de selección, ...",
  "changes_made": [
    "Reordered skills: moved BPO Operations to top",
    "Reworded summary to emphasize outbound sales experience"
  ]
}}

IMPORTANTE: adapted_cv debe contener el CV COMPLETO (todas las secciones), no solo los cambios. cover_letter debe ser una carta de presentacion profesional y personalizada para esta oferta especifica."""


def call_llm(prompt: str, api_key: str) -> dict:
    payload = {
        "model": DEFAULT_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
    }
    req = urllib.request.Request(
        ONE_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError) as e:
        log.error("One API request failed: %s", e)
        sys.exit(1)
    except json.JSONDecodeError as e:
        log.error("Invalid JSON response from One API: %s", e)
        sys.exit(1)

    content = (
        body.get("choices", [{}])[0].get("message", {}).get("content", "")
    )
    if not content:
        log.error("Empty response from One API")
        sys.exit(1)

    content = content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)

    try:
        result = json.loads(content)
    except json.JSONDecodeError:
        log.error("Failed to parse LLM response as JSON")
        log.error("Raw response: %s", content[:1000])
        sys.exit(1)

    return result


def adapt(offer: dict, match: dict, root: str) -> dict:
    cv = load_cv(root)
    original_hash = compute_sha256(cv)

    api_key = os.environ.get("PICOCLAW_API_KEY", "")
    if not api_key:
        log.error("PICOCLAW_API_KEY environment variable not set")
        sys.exit(1)

    prompt = build_prompt(cv, offer, match)
    llm_result = call_llm(prompt, api_key)

    adapted_dir = os.path.join(root, "cv", "adapted")
    os.makedirs(adapted_dir, exist_ok=True)

    offer_id = sanitize_offer_id(offer)
    adapted_cv_path = os.path.join(adapted_dir, f"{offer_id}_curriculum.md")
    cover_path = os.path.join(adapted_dir, f"{offer_id}_cover.md")

    adapted_cv = llm_result.get("adapted_cv", "").strip()
    cover_letter = llm_result.get("cover_letter", "").strip()

    if not adapted_cv:
        log.error("LLM response missing 'adapted_cv' field")
        sys.exit(1)

    with open(adapted_cv_path, "w") as f:
        f.write(adapted_cv)

    with open(cover_path, "w") as f:
        f.write(cover_letter)

    changes_made = llm_result.get("changes_made", [])

    log.info(
        "Adapted CV saved to %s (score=%d, hash=%s)",
        adapted_cv_path,
        match.get("score", 0),
        original_hash,
    )

    return {
        "adapted_cv": adapted_cv_path,
        "cover_letter_path": cover_path,
        "changes_made": changes_made,
        "original_cv_hash": f"sha256:{original_hash}",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Adapt CV for a job offer")
    parser.add_argument("--offer", help="Job offer as JSON string")
    parser.add_argument("--match", help="Matcher result as JSON string")
    args = parser.parse_args()

    if args.offer and args.match:
        offer = json.loads(args.offer)
        match_data = json.loads(args.match)
    else:
        line = sys.stdin.readline()
        if not line:
            log.error("No input received on stdin")
            sys.exit(1)
        try:
            data = json.loads(line)
            offer = data.get("offer", data)
            match_data = data.get("match", {})
        except json.JSONDecodeError:
            log.error("Invalid JSON on stdin")
            sys.exit(1)

    root = _project_root()
    result = adapt(offer, match_data, root)
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    main()
