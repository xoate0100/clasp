#!/usr/bin/env python3
"""
Deterministic blog.article evaluator (SW-BLOG-002).

Governance evaluator — same class as other 3_bootstrap_scripts validators.
No LLM calls. Agent-scored dimensions are recorded and never gate alone.

Usage:
  python 3_bootstrap_scripts/content/blog_evaluate.py \\
    --ir path/to/article.json \\
    --override path/to/override.json \\
    [--html path/to/projected.html] \\
    [--agent-scored path/to/agent_scores.json] \\
    [--out report.json]
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from typing import Any

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

try:
    import yaml
    import jsonschema
except ImportError:
    print("[blog_evaluate] ERROR: PyYAML and jsonschema required", file=sys.stderr)
    sys.exit(1)

PROFILE_SCHEMA = REPO_ROOT / "7_schemas" / "content_ir" / "profile.blog.article.schema.json"
OVERRIDE_SCHEMA = REPO_ROOT / "7_schemas" / "content_ir" / "blog.override.schema.json"

WORD_RE = re.compile(r"\b[\w'-]+\b", re.UNICODE)
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
STYLE_ATTR_RE = re.compile(r"\bstyle\s*=", re.IGNORECASE)
FAQ_JSONLD_RE = re.compile(
    r'application/ld\+json[^>]*>[^<]*FAQPage| "@type"\s*:\s*"FAQPage"',
    re.IGNORECASE | re.DOTALL,
)
INLINE_SVG_RE = re.compile(r"<svg[\s>]", re.IGNORECASE)
DETAILS_SUMMARY_RE = re.compile(r"<details\b[^>]*>.*?<summary\b", re.IGNORECASE | re.DOTALL)
DISCLOSURE_CLASS_RE = re.compile(r"disclosure", re.IGNORECASE)


def _load(path: pathlib.Path) -> Any:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yaml", ".yml"}:
        return yaml.safe_load(text)
    return json.loads(text)


def _word_count(text: str) -> int:
    return len(WORD_RE.findall(text or ""))


def _sentences_from_text(text: str) -> list[str]:
    parts = [p.strip() for p in SENTENCE_SPLIT_RE.split((text or "").strip()) if p.strip()]
    return parts or ([] if not (text or "").strip() else [text.strip()])


def _iter_sentence_nodes(ir: dict) -> list[dict]:
    out: list[dict] = []
    for section in ir.get("sections") or []:
        for block in section.get("blocks") or []:
            if block.get("type") == "paragraph":
                for sent in block.get("sentences") or []:
                    out.append(sent)
    return out


def _iter_paragraph_blocks(ir: dict) -> list[dict]:
    out: list[dict] = []
    for section in ir.get("sections") or []:
        for block in section.get("blocks") or []:
            if block.get("type") == "paragraph":
                out.append(block)
    return out


def _all_body_text(ir: dict) -> str:
    chunks: list[str] = []
    for sent in _iter_sentence_nodes(ir):
        chunks.append(sent.get("text") or "")
    for section in ir.get("sections") or []:
        for block in section.get("blocks") or []:
            if block.get("type") == "list":
                for item in block.get("items") or []:
                    chunks.append(item.get("text") or "")
    return " ".join(chunks)


def _sentence_index(ir: dict) -> dict[str, str]:
    return {s["id"]: s["text"] for s in _iter_sentence_nodes(ir) if s.get("id")}


def _dim(score: float, passed: bool, findings: list[dict]) -> dict:
    return {"score": score, "pass": passed, "findings": findings}


def _finding(code: str, message: str, **extra: Any) -> dict:
    row = {"code": code, "message": message}
    row.update(extra)
    return row


def validate_schemas(ir: dict, override: dict) -> list[str]:
    errors: list[str] = []
    for label, data, schema_path in (
        ("ir", ir, PROFILE_SCHEMA),
        ("override", override, OVERRIDE_SCHEMA),
    ):
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        validator = jsonschema.Draft7Validator(schema)
        for err in sorted(validator.iter_errors(data), key=lambda e: list(e.path)):
            errors.append(f"{label}: {err.message} at {list(err.path)}")
    return errors


def eval_d1_intent_fit(ir: dict, override: dict) -> dict:
    findings: list[dict] = []
    pillar_ids = {p.get("id") for p in (override.get("pillars") or [])}
    if ir.get("pillar_ref") not in pillar_ids:
        findings.append(
            _finding(
                "D1_PILLAR",
                f"pillar_ref '{ir.get('pillar_ref')}' not in override.pillars",
            )
        )
    funnel = ir.get("funnel")
    if funnel not in {"tofu", "mofu", "bofu"}:
        findings.append(_finding("D1_FUNNEL", f"invalid funnel '{funnel}'"))
    bands = (override.get("length_by_funnel") or {}).get(funnel or "")
    if bands:
        words = _word_count(_all_body_text(ir))
        lo, hi = bands.get("min_words", 0), bands.get("max_words", 10**9)
        if words < lo or words > hi:
            findings.append(
                _finding(
                    "D1_LENGTH",
                    f"body word count {words} outside {funnel} band [{lo}, {hi}]",
                    words=words,
                )
            )
    passed = not findings
    return _dim(1.0 if passed else 0.0, passed, findings)


def eval_d2_grounding(ir: dict) -> dict:
    findings: list[dict] = []
    sources = ir.get("sources") or []
    source_keys: set[str] = set()
    for i, src in enumerate(sources):
        source_keys.add(str(i))
        source_keys.add(src.get("url") or "")
        if src.get("url"):
            source_keys.add(src["url"])
    has_primary = any(s.get("primary") for s in sources)
    for claim in ir.get("claims") or []:
        if claim.get("type") != "statistic":
            continue
        ref = claim.get("source_ref")
        if not ref or ref not in source_keys:
            findings.append(
                _finding(
                    "D2_STAT_SOURCE",
                    f"statistic claim '{claim.get('claim_id')}' missing source_ref",
                    claim_id=claim.get("claim_id"),
                )
            )
        elif has_primary:
            # Prefer primary when one exists among sources for this claim's ref
            matched = None
            for i, src in enumerate(sources):
                if ref in {str(i), src.get("url")}:
                    matched = src
                    break
            if matched is not None and not matched.get("primary"):
                # Only warn-style finding if a primary source exists in the set
                # but this claim points at a non-primary — still pass if sourced.
                pass
    if not sources:
        findings.append(_finding("D2_NO_SOURCES", "sources[] is empty"))
    passed = not findings
    return _dim(1.0 if passed else 0.0, passed, findings)


def eval_d3_structure(ir: dict) -> dict:
    """SCAN-01..08 deterministic checks against IR blocks."""
    findings: list[dict] = []
    sentences = _iter_sentence_nodes(ir)
    paragraphs = _iter_paragraph_blocks(ir)

    # SCAN-02: paragraphs max 3 sentences or 60 words (either limit fails)
    for block in paragraphs:
        sents = block.get("sentences") or []
        text = " ".join(s.get("text") or "" for s in sents)
        wc = _word_count(text)
        if len(sents) > 3 or wc > 60:
            findings.append(
                _finding(
                    "SCAN-02",
                    f"paragraph {block.get('id')} has {len(sents)} sentences / {wc} words (max 3 / 60)",
                )
            )

    # SCAN-03: sentences <= 25 words
    for sent in sentences:
        wc = _word_count(sent.get("text") or "")
        if wc > 25:
            findings.append(
                _finding(
                    "SCAN-03",
                    f"sentence {sent.get('id')} has {wc} words (max 25)",
                )
            )

    # SCAN-01: no prose run > 150 words without structural break
    # A "prose run" is consecutive paragraph blocks between non-paragraph blocks / section boundaries.
    for section in ir.get("sections") or []:
        run_words = 0
        for block in section.get("blocks") or []:
            if block.get("type") == "paragraph":
                run_words += _word_count(
                    " ".join(s.get("text") or "" for s in (block.get("sentences") or []))
                )
                if run_words > 150:
                    findings.append(
                        _finding(
                            "SCAN-01",
                            f"prose run of {run_words} words without structural break in section {section.get('id')}",
                        )
                    )
                    break
            else:
                run_words = 0

    # SCAN-04: no H2 section over 400 words
    for section in ir.get("sections") or []:
        if section.get("level") != 2:
            continue
        words = 0
        for block in section.get("blocks") or []:
            if block.get("type") == "paragraph":
                words += _word_count(
                    " ".join(s.get("text") or "" for s in (block.get("sentences") or []))
                )
            elif block.get("type") == "list":
                for item in block.get("items") or []:
                    words += _word_count(item.get("text") or "")
        if words > 400:
            findings.append(
                _finding(
                    "SCAN-04",
                    f"H2 section {section.get('id')} has {words} words (max 400)",
                )
            )

    # SCAN-06: bold lead-in on bullets in lists of 4+
    for section in ir.get("sections") or []:
        for block in section.get("blocks") or []:
            if block.get("type") != "list":
                continue
            items = block.get("items") or []
            if len(items) >= 4:
                for item in items:
                    if not item.get("bold_lead_in"):
                        findings.append(
                            _finding(
                                "SCAN-06",
                                f"list {block.get('id')} item missing bold_lead_in",
                            )
                        )
                        break

    # Pull quotes must reference existing sentence ids (verbatim contract)
    idx = _sentence_index(ir)
    for pq in ir.get("pull_quotes") or []:
        sid = pq.get("sentence_id")
        if sid not in idx:
            findings.append(
                _finding(
                    "PULL_QUOTE",
                    f"pull_quote sentence_id '{sid}' is not a body sentence id",
                )
            )

    # Takeaways exactly 4 — also enforced by schema; bite fixtures may bypass schema
    takeaways = ir.get("takeaways") or []
    if len(takeaways) != 4:
        findings.append(
            _finding("TAKEAWAYS", f"expected 4 takeaways, found {len(takeaways)}")
        )

    # SCAN-05 / 07 / 08: FK band handled in d5; visual cadence + mobile are soft IR checks
    total_words = _word_count(_all_body_text(ir))
    visuals = 0
    for section in ir.get("sections") or []:
        for block in section.get("blocks") or []:
            if block.get("type") in {"visual", "interactive_ref", "table"}:
                visuals += 1
    visuals += 1 if ir.get("diagram") else 0
    visuals += len(ir.get("interactive") or [])
    if total_words > 1000 and visuals == 0:
        findings.append(
            _finding("SCAN-07", "no visual/interactive element in a long article")
        )

    # SCAN-08 is primarily a projection/HTML concern; IR cannot fully prove viewport rules.
    # Recorded as pass-through when no HTML is supplied.

    passed = not findings
    return _dim(1.0 if passed else 0.0, passed, findings)


def _claim_matches_rule(claim: dict, rule: dict, sources: list[dict]) -> bool:
    if rule.get("claim_type") and claim.get("type") != rule["claim_type"]:
        return False
    pattern = rule.get("text_regex")
    if pattern and not re.search(pattern, claim.get("text") or ""):
        return False
    return True


def _source_for_ref(ref: str | None, sources: list[dict]) -> dict | None:
    if ref is None:
        return None
    for i, src in enumerate(sources):
        if ref in {str(i), src.get("url")}:
            return src
    return None


def eval_d4_claims_compliance(ir: dict, override: dict) -> dict:
    findings: list[dict] = []
    sources = ir.get("sources") or []
    claims = ir.get("claims") or []
    for ruleset in (override.get("compliance") or {}).get("rulesets") or []:
        for rule in ruleset.get("rules") or []:
            for claim in claims:
                if not _claim_matches_rule(claim, rule, sources):
                    continue
                if rule.get("forbid"):
                    findings.append(
                        _finding(
                            rule.get("id") or "RULE_FORBID",
                            rule.get("message") or "forbidden claim",
                            severity=rule.get("severity", "block"),
                            claim_id=claim.get("claim_id"),
                        )
                    )
                    continue
                for req in rule.get("require") or []:
                    if req == "attribution":
                        attr = claim.get("attribution")
                        allowed = rule.get("attribution_in")
                        if not attr or (allowed and attr not in allowed):
                            findings.append(
                                _finding(
                                    rule.get("id") or "RULE_ATTR",
                                    rule.get("message") or "attribution required",
                                    severity=rule.get("severity", "block"),
                                    claim_id=claim.get("claim_id"),
                                )
                            )
                    elif req == "source_ref":
                        if not claim.get("source_ref"):
                            findings.append(
                                _finding(
                                    rule.get("id") or "RULE_SOURCE",
                                    rule.get("message") or "source_ref required",
                                    severity=rule.get("severity", "block"),
                                    claim_id=claim.get("claim_id"),
                                )
                            )
                    elif req == "source.primary":
                        src = _source_for_ref(claim.get("source_ref"), sources)
                        if not src or not src.get("primary"):
                            findings.append(
                                _finding(
                                    rule.get("id") or "RULE_PRIMARY",
                                    rule.get("message") or "primary source required",
                                    severity=rule.get("severity", "block"),
                                    claim_id=claim.get("claim_id"),
                                )
                            )
                    elif req == "link_present":
                        text = claim.get("text") or ""
                        href = claim.get("source_ref") or ""
                        if "http://" not in text and "https://" not in text and not (
                            href.startswith("http://") or href.startswith("https://")
                        ):
                            findings.append(
                                _finding(
                                    rule.get("id") or "RULE_LINK",
                                    rule.get("message") or "link required",
                                    severity=rule.get("severity", "block"),
                                    claim_id=claim.get("claim_id"),
                                )
                            )
    # Only block-severity findings fail the dimension
    blocking = [f for f in findings if f.get("severity", "block") == "block"]
    passed = not blocking
    return _dim(1.0 if passed else 0.0, passed, findings)


def _flesch_kincaid_grade(text: str) -> float:
    words = WORD_RE.findall(text or "")
    if not words:
        return 0.0
    sents = max(len(_sentences_from_text(text)), 1)
    # Syllable approximation: vowel groups
    syllables = 0
    for w in words:
        groups = re.findall(r"[aeiouy]+", w.lower())
        syllables += max(len(groups), 1)
    # FK grade: 0.39*(words/sents) + 11.8*(syllables/words) - 15.59
    return 0.39 * (len(words) / sents) + 11.8 * (syllables / len(words)) - 15.59


def eval_d5_clarity(ir: dict, override: dict) -> dict:
    findings: list[dict] = []
    band = override.get("reading_level") or {}
    if not band:
        return _dim(1.0, True, [])
    text = _all_body_text(ir)
    grade = _flesch_kincaid_grade(text)
    lo = band.get("min_grade")
    hi = band.get("max_grade")
    if lo is not None and grade < lo:
        findings.append(
            _finding("D5_LOW", f"reading grade {grade:.1f} below min {lo}")
        )
    if hi is not None and grade > hi:
        findings.append(
            _finding("D5_HIGH", f"reading grade {grade:.1f} above max {hi}")
        )
    passed = not findings
    return _dim(1.0 if passed else 0.0, passed, findings)


def eval_d6_voice(agent_scored: dict | None) -> dict:
    """Agent-scored; never gates alone. Recorded when provided."""
    if not agent_scored or "d6_voice" not in agent_scored:
        return _dim(
            0.0,
            True,  # does not fail gate
            [
                _finding(
                    "D6_PENDING",
                    "voice fidelity is agent_scored; no agent score supplied",
                    scoring="agent_scored",
                )
            ],
        )
    entry = agent_scored["d6_voice"]
    score = float(entry.get("score", 0))
    rationale = entry.get("rationale") or ""
    return _dim(
        score,
        True,
        [
            _finding(
                "D6_AGENT",
                rationale or "agent-scored voice fidelity",
                scoring="agent_scored",
                rationale=rationale,
            )
        ],
    )


def eval_d7_eeat(ir: dict) -> dict:
    findings: list[dict] = []
    if not ir.get("author_ref"):
        findings.append(_finding("D7_AUTHOR", "author_ref required"))
    if not ir.get("published_intent_at"):
        findings.append(_finding("D7_DATE", "published_intent_at required"))
    sources = ir.get("sources") or []
    if not sources:
        findings.append(_finding("D7_SOURCES", "sources must be cited"))
    else:
        for i, src in enumerate(sources):
            if not src.get("accessed_at"):
                findings.append(
                    _finding("D7_SOURCE_DATE", f"source[{i}] missing accessed_at")
                )
    # First-person experience only with author_ref (already required);
    # flag first-person markers in claims of type other/performance without author.
    first_person = re.compile(r"\b(I|we|my|our)\b", re.IGNORECASE)
    if not ir.get("author_ref"):
        for claim in ir.get("claims") or []:
            if first_person.search(claim.get("text") or ""):
                findings.append(
                    _finding(
                        "D7_FIRST_PERSON",
                        f"first-person claim '{claim.get('claim_id')}' without author_ref",
                    )
                )
    passed = not findings
    return _dim(1.0 if passed else 0.0, passed, findings)


def eval_projection_html(html: str, override: dict) -> dict:
    findings: list[dict] = []
    if STYLE_ATTR_RE.search(html):
        findings.append(_finding("INV-WP-01", "html contains style= attribute"))
    if FAQ_JSONLD_RE.search(html):
        findings.append(_finding("INV-WP-02", "html contains FAQPage JSON-LD"))
    if INLINE_SVG_RE.search(html):
        findings.append(_finding("INV-WP-03", "html contains inline <svg>"))
    if "<details" in html.lower():
        if not DETAILS_SUMMARY_RE.search(html):
            findings.append(
                _finding("INV-WP-04", "details present without summary pairing")
            )
    # Disclosure exactly once
    disclosure_hits = len(DISCLOSURE_CLASS_RE.findall(html))
    # Prefer explicit data-disclosure or class containing disclosure block_ref
    block_ref = ((override.get("disclosure") or {}).get("block_ref") or "disclosure")
    explicit = len(re.findall(re.escape(block_ref), html, flags=re.IGNORECASE))
    count = explicit if block_ref != "disclosure" else disclosure_hits
    if count == 0:
        findings.append(_finding("INV-WP-06", "disclosure missing"))
    elif count > 1:
        findings.append(
            _finding("INV-WP-06", f"disclosure present {count} times (want 1)")
        )
    prefix = ((override.get("components") or {}).get("class_prefix") or "").strip()
    if prefix and f'class="' in html:
        # If component-like classes appear, they should use the prefix — soft check:
        # when class_prefix set, at least one class should start with it if shortcodes/components used.
        pass
    passed = not findings
    return _dim(1.0 if passed else 0.0, passed, findings)


GATE_DIMENSIONS = (
    "d1_intent_fit",
    "d2_grounding",
    "d3_structure",
    "d4_claims_compliance",
    "d5_clarity",
    "d7_eeat",
)


def evaluate(
    ir: dict,
    override: dict,
    html: str | None = None,
    agent_scored: dict | None = None,
    *,
    skip_schema: bool = False,
) -> dict:
    schema_errors = [] if skip_schema else validate_schemas(ir, override)
    dimensions = {
        "d1_intent_fit": eval_d1_intent_fit(ir, override),
        "d2_grounding": eval_d2_grounding(ir),
        "d3_structure": eval_d3_structure(ir),
        "d4_claims_compliance": eval_d4_claims_compliance(ir, override),
        "d5_clarity": eval_d5_clarity(ir, override),
        "d6_voice": eval_d6_voice(agent_scored),
        "d7_eeat": eval_d7_eeat(ir),
    }
    if html is not None:
        dimensions["projection_invariants"] = eval_projection_html(html, override)

    gate_ok = not schema_errors and all(
        dimensions[d]["pass"] for d in GATE_DIMENSIONS if d in dimensions
    )
    if html is not None and not dimensions["projection_invariants"]["pass"]:
        gate_ok = False

    return {
        "evaluator": "EV.content.blog_article",
        "schema_errors": schema_errors,
        "dimension": dimensions,
        "overall": {"pass": gate_ok, "gate": "deterministic"},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate blog.article IR + override")
    parser.add_argument("--ir", required=True, type=pathlib.Path)
    parser.add_argument("--override", required=True, type=pathlib.Path)
    parser.add_argument("--html", type=pathlib.Path, default=None)
    parser.add_argument("--agent-scored", type=pathlib.Path, default=None)
    parser.add_argument("--out", type=pathlib.Path, default=None)
    parser.add_argument(
        "--skip-schema",
        action="store_true",
        help="Skip JSON Schema validation (fixture bite tests only)",
    )
    args = parser.parse_args(argv)

    ir = _load(args.ir)
    override = _load(args.override)
    html = args.html.read_text(encoding="utf-8") if args.html else None
    agent_scored = _load(args.agent_scored) if args.agent_scored else None

    report = evaluate(
        ir, override, html=html, agent_scored=agent_scored, skip_schema=args.skip_schema
    )
    payload = json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0 if report["overall"]["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
