#!/usr/bin/env python3
"""
Match a job offer against the CV using One API (LLM).

Reads the CV from cv/curriculum.md, reads a job offer (JSON) from stdin,
calls the One API LLM to compute a semantic match score, and outputs
the match result as JSON.

Usage:
    echo '{"title": "...", "description": "..."}' | python3 match.py
    python3 match.py --offer '{"title": "...", "description": "..."}'
"""

import argparse
import json
import logging
import os
import sys
import urllib.error
import urllib.request

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stderr,
)
log = logging.getLogger("matcher")

ONE_API_URL = "http://localhost:3001/v1/chat/completions"
DEFAULT_MODEL = "llama-3.1-8b-instant"

try:
    import yaml
except ImportError:
    log.error("PyYAML is required: pip install pyyaml")
    sys.exit(1)


def _project_root() -> str:
    dir_ = os.path.dirname(os.path.abspath(__file__))
    for _ in range(6):
        if os.path.isdir(os.path.join(dir_, "cv")) and os.path.isfile(os.path.join(dir_, "cv", "curriculum.md")):
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


def load_config(root: str) -> dict:
    path = os.path.join(root, "config", "search_params.yaml")
    with open(path, "r") as f:
        return yaml.safe_load(f)


def build_prompt(cv: str, offer: dict) -> str:
    return f"""Eres un evaluador de hojas de vida para el mercado laboral colombiano. Compara la siguiente hoja de vida (CV) con una oferta de trabajo y genera un puntaje de compatibilidad estructurado.

REGLAS ESTRICTAS:
1. NO inventes experiencia, habilidades o informacion que no este explicitamente en el CV (Regla 9: Never fabricate experience).
2. El CV es la UNICA fuente de verdad sobre la experiencia del candidato (Regla 10).
3. Responde UNICAMENTE con JSON valido. Sin markdown, sin texto adicional, sin bloques de codigo.

PONDERACION DEL PUNTAJE:
- Coincidencia de habilidades tecnicas: 50%
- Nivel de experiencia: 20%
- Modalidad/ubicacion: 15%
- Sector industrial: 10%
- Idioma: 5%

=== CV DEL CANDIDATO ===
{cv}
=== FIN DEL CV ===

=== OFERTA DE TRABAJO ===
{json.dumps(offer, ensure_ascii=False, indent=2)}
=== FIN DE LA OFERTA ===

Responde UNICAMENTE con un objeto JSON con esta estructura exacta, sin texto adicional:
{{
  "score": <numero entero 0-100>,
  "skills_matched": ["<habilidad 1>", "<habilidad 2>"],
  "skills_missing": ["<habilidad faltante 1>"],
  "experience_match": true/false,
  "modality_match": true/false,
  "salary_in_range": true/false,
  "adaptation_possible": true/false,
  "adaptation_focus": ["<sugerencia 1>", "<sugerencia 2>"]
}}"""


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
        with urllib.request.urlopen(req, timeout=60) as resp:
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

    try:
        result = json.loads(content)
    except json.JSONDecodeError:
        log.error("Failed to parse LLM response as JSON")
        log.error("Raw response: %s", content[:500])
        sys.exit(1)

    return result


def compute_match(offer: dict, root: str) -> dict:
    cv = load_cv(root)
    config = load_config(root)
    thresholds = config.get("match_thresholds", {})
    auto_notify = thresholds.get("auto_notify", 70)
    possible_adapt = thresholds.get("possible_adapt", 50)

    api_key = os.environ.get("PICOCLAW_API_KEY", "")
    if not api_key:
        log.error("PICOCLAW_API_KEY environment variable not set")
        sys.exit(1)

    prompt = build_prompt(cv, offer)
    llm_result = call_llm(prompt, api_key)

    score = llm_result.get("score", 0)
    if "adaptation_possible" not in llm_result:
        llm_result["adaptation_possible"] = possible_adapt <= score < auto_notify

    llm_result["_offer_id"] = offer.get("url", "") + "|" + offer.get("title", "")
    return llm_result


def main() -> None:
    parser = argparse.ArgumentParser(description="Match job offer against CV")
    parser.add_argument("--offer", help="Job offer as JSON string")
    args = parser.parse_args()

    if args.offer:
        offer = json.loads(args.offer)
    else:
        line = sys.stdin.readline()
        if not line:
            log.error("No input received on stdin")
            sys.exit(1)
        offer = json.loads(line)

    root = _project_root()
    result = compute_match(offer, root)
    print(json.dumps(result, ensure_ascii=False))
    log.info(
        "Match score: %d for %s",
        result.get("score", 0),
        offer.get("title", "unknown"),
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
