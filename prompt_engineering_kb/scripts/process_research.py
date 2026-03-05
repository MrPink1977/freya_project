"""
process_research.py
-------------------
Processes raw research JSON from the parallel research phase into structured,
chunked documents ready for ChromaDB ingestion.

Each research document is split into semantic sections (by markdown heading),
and each chunk is enriched with metadata for precise RAG filtering.

Output: data/prompt_engineering_chunks.json
"""

import json
import re
import hashlib
import os
from datetime import datetime

# ── Paths ──────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
RAW_JSON    = os.path.join(os.path.dirname(PROJECT_DIR), "prompt_engineering_research.json")
# Fallback: look for the file relative to project root
if not os.path.exists(RAW_JSON):
    RAW_JSON = os.path.join(PROJECT_DIR, "data", "raw_research.json")
OUTPUT_JSON = os.path.join(PROJECT_DIR, "data", "prompt_engineering_chunks.json")

# ── Category mapping ────────────────────────────────────────────────────────
CATEGORY_MAP = {
    "Chain-of-Thought": "reasoning_techniques",
    "Tree of Thought":  "reasoning_techniques",
    "CoT":              "reasoning_techniques",
    "ToT":              "reasoning_techniques",
    "Few-shot":         "in_context_learning",
    "Zero-shot":        "in_context_learning",
    "Few-Shot":         "in_context_learning",
    "Zero-Shot":        "in_context_learning",
    "In-Context":       "in_context_learning",
    "ReAct":            "agentic_prompting",
    "Reflexion":        "agentic_prompting",
    "Agent":            "agentic_prompting",
    "AutoGPT":          "agentic_prompting",
    "Tool-Use":         "agentic_prompting",
    "OPRO":             "prompt_optimization",
    "APE":              "prompt_optimization",
    "DSPy":             "prompt_optimization",
    "Automatic Prompt": "prompt_optimization",
    "Optimization":     "prompt_optimization",
    "RAG":              "rag_and_retrieval",
    "Retrieval":        "rag_and_retrieval",
    "Retrieval-Augmented": "rag_and_retrieval",
    "System Prompt":    "system_prompt_engineering",
    "Persona":          "system_prompt_engineering",
    "Role Prompting":   "system_prompt_engineering",
    "Text-to-Image":    "image_generation",
    "Stable Diffusion": "image_generation",
    "Midjourney":       "image_generation",
    "DALL-E":           "image_generation",
    "Hyperrealism":     "image_generation",
    "Security":         "adversarial_and_security",
    "Adversarial":      "adversarial_and_security",
    "Jailbreak":        "adversarial_and_security",
    "Red-Team":         "adversarial_and_security",
    "Injection":        "adversarial_and_security",
}

def infer_category(topic: str) -> str:
    """Map a topic string to a category slug."""
    for keyword, category in CATEGORY_MAP.items():
        if keyword.lower() in topic.lower():
            return category
    return "general_prompting"

def make_chunk_id(topic: str, section: str, index: int) -> str:
    """Generate a deterministic unique ID for a chunk."""
    raw = f"{topic}::{section}::{index}"
    return "pe_" + hashlib.md5(raw.encode()).hexdigest()[:12]

def split_into_sections(markdown_text: str) -> list[dict]:
    """
    Split a markdown document into sections by H2/H3 headings.
    Returns a list of dicts with 'heading' and 'content' keys.
    """
    # Split on lines that start with ## or ###
    pattern = re.compile(r'^(#{2,3})\s+(.+)$', re.MULTILINE)
    matches = list(pattern.finditer(markdown_text))

    sections = []
    if not matches:
        # No headings found — treat the whole document as one section
        sections.append({
            "heading": "Overview",
            "level": 2,
            "content": markdown_text.strip()
        })
        return sections

    # Text before first heading
    if matches[0].start() > 0:
        preamble = markdown_text[:matches[0].start()].strip()
        if preamble:
            sections.append({
                "heading": "Introduction",
                "level": 2,
                "content": preamble
            })

    for i, match in enumerate(matches):
        heading_level = len(match.group(1))
        heading_text  = match.group(2).strip()
        content_start = match.end()
        content_end   = matches[i + 1].start() if i + 1 < len(matches) else len(markdown_text)
        content       = markdown_text[content_start:content_end].strip()

        if content:  # Skip empty sections
            sections.append({
                "heading": heading_text,
                "level":   heading_level,
                "content": content
            })

    return sections

def chunk_section(section_content: str, max_chars: int = 1800) -> list[str]:
    """
    If a section is longer than max_chars, split it into paragraph-level chunks.
    This keeps chunks semantically coherent while staying within embedding limits.
    """
    if len(section_content) <= max_chars:
        return [section_content]

    # Split by double newline (paragraphs / code blocks)
    paragraphs = re.split(r'\n{2,}', section_content)
    chunks = []
    current = ""

    for para in paragraphs:
        if len(current) + len(para) + 2 <= max_chars:
            current = (current + "\n\n" + para).strip()
        else:
            if current:
                chunks.append(current)
            # If a single paragraph exceeds max, split by sentence
            if len(para) > max_chars:
                sentences = re.split(r'(?<=[.!?])\s+', para)
                sub = ""
                for sent in sentences:
                    if len(sub) + len(sent) + 1 <= max_chars:
                        sub = (sub + " " + sent).strip()
                    else:
                        if sub:
                            chunks.append(sub)
                        sub = sent
                if sub:
                    chunks.append(sub)
            else:
                current = para

    if current:
        chunks.append(current)

    return chunks if chunks else [section_content]

def process_research(raw_json_path: str) -> list[dict]:
    """
    Load raw research JSON and convert to a flat list of enriched chunk dicts.
    """
    with open(raw_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    all_chunks = []
    results = data.get("results", [])

    for result in results:
        if result.get("error"):
            print(f"  [SKIP] Error in result: {result['error'][:80]}")
            continue

        output   = result.get("output", {})
        topic    = output.get("topic", "Unknown Topic")
        content  = output.get("content", "")
        key_tech = output.get("key_techniques", "")
        sources  = output.get("sources", "")
        category = infer_category(topic)

        print(f"  Processing: {topic[:60]}...")

        sections = split_into_sections(content)
        chunk_index = 0

        for section in sections:
            sub_chunks = chunk_section(section["content"])

            for sub in sub_chunks:
                if len(sub.strip()) < 80:
                    continue  # Skip trivially short chunks

                chunk_id = make_chunk_id(topic, section["heading"], chunk_index)

                chunk = {
                    "id": chunk_id,
                    "document": sub.strip(),
                    "metadata": {
                        "topic":          topic,
                        "section":        section["heading"],
                        "heading_level":  section["level"],
                        "category":       category,
                        "key_techniques": key_tech,
                        "sources":        sources,
                        "collection":     "prompt_engineering_kb",
                        "created_at":     datetime.utcnow().isoformat() + "Z",
                        "char_count":     len(sub.strip()),
                    }
                }
                all_chunks.append(chunk)
                chunk_index += 1

        print(f"    → {chunk_index} chunks generated")

    return all_chunks

def main():
    print("=" * 60)
    print("Prompt Engineering KB — Research Processor")
    print("=" * 60)

    if not os.path.exists(RAW_JSON):
        print(f"[ERROR] Raw research file not found: {RAW_JSON}")
        print("  Make sure prompt_engineering_research.json is in the right place.")
        return

    print(f"\nLoading raw research from:\n  {RAW_JSON}\n")
    chunks = process_research(RAW_JSON)

    print(f"\nTotal chunks generated: {len(chunks)}")

    # Write output
    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump({"chunks": chunks, "total": len(chunks)}, f, indent=2, ensure_ascii=False)

    print(f"\nOutput written to:\n  {OUTPUT_JSON}")

    # Print category summary
    from collections import Counter
    cats = Counter(c["metadata"]["category"] for c in chunks)
    print("\nChunks by category:")
    for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"  {cat:<35} {count:>4} chunks")

    print("\n[DONE] Processing complete.")

if __name__ == "__main__":
    main()
