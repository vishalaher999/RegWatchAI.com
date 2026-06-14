"""
Document chunker for F2 — 5 strategies benchmarked on Day 9.

Day 8: Fixed-size chunking (baseline).
Day 9: Extended with 4 more strategies + benchmark scoring.
Day 10: Hierarchical chunking (winner from benchmark + structure awareness).

Strategy summary:
  1. fixed_size      — split every N chars with overlap (Day 8 baseline)
  2. sentence        — split on sentence boundaries
  3. paragraph       — split on blank lines (double newlines)
  4. recursive       — try paragraph → sentence → fixed, adapt to structure
  5. regulatory      — split on regulatory section markers (§, PART, SEC.)

Why chunking strategy matters more than model choice:
  Better chunking → better retrieval → relevant context reaches Claude.
  A compliance deadline in chunk 47 that never gets retrieved is useless
  no matter how good Claude is. Chunking is the highest-leverage RAG decision.
"""

import re
from dataclasses import dataclass, field

# ── Constants ──────────────────────────────────────────────────────────────────
CHUNK_SIZE = 1_000      # target characters per chunk
OVERLAP = 150           # overlap between adjacent fixed-size chunks
MIN_CHUNK_SIZE = 100    # discard chunks smaller than this (usually boilerplate)
MAX_CHUNK_SIZE = 2_000  # hard cap — chunks above this get split further

# Regulatory section markers — signal the start of a new logical unit
_REGULATORY_MARKERS = re.compile(
    r'(?m)^(?:'
    r'\s*§+\s*\d+'           # § 1002.5 or §§ 1002.5
    r'|\s*PART\s+\d+'        # PART 1002
    r'|\s*SEC(?:TION)?\.?\s+\d+'  # SECTION 4 or SEC. 4
    r'|\s*\d+\.\s+[A-Z]'    # 1. Purpose
    r'|\s*[A-Z][A-Z\s]{4,}:' # ALL CAPS HEADER:
    r')'
)

# Sentence boundary — end of sentence followed by space and capital letter
_SENTENCE_END = re.compile(r'(?<=[.!?])\s+(?=[A-Z])')


@dataclass
class Chunk:
    """One piece of a document, ready to be scored for relevance."""
    index: int
    text: str
    start_char: int
    end_char: int
    strategy: str = "unknown"   # which chunking strategy produced this chunk


# ── Strategy 1: Fixed-size (Day 8 baseline) ───────────────────────────────────

def chunk_fixed_size(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = OVERLAP,
) -> list[Chunk]:
    """
    Split every N characters with overlap.

    Simplest strategy. Does not respect sentence or paragraph boundaries.
    Overlap ensures sentences at boundaries appear in at least one complete chunk.
    """
    if not text or not text.strip():
        return []

    chunks: list[Chunk] = []
    step = chunk_size - overlap
    start = 0
    index = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk_text = text[start:end].strip()
        if len(chunk_text) >= MIN_CHUNK_SIZE:
            chunks.append(Chunk(index=index, text=chunk_text,
                                start_char=start, end_char=end, strategy="fixed_size"))
            index += 1
        if end >= len(text):
            break
        start += step

    return chunks


# Alias for backward compatibility with Day 8 code
def chunk_document(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = OVERLAP) -> list[Chunk]:
    """Backward-compatible alias for chunk_fixed_size."""
    return chunk_fixed_size(text, chunk_size, overlap)


# ── Strategy 2: Sentence-based ────────────────────────────────────────────────

def chunk_sentences(text: str, target_size: int = CHUNK_SIZE) -> list[Chunk]:
    """
    Split on sentence boundaries, accumulate until target size reached.

    Never cuts mid-sentence. Better coherence than fixed-size for
    extracting dates (which often sit at the end of long sentences).

    Example: "The final rule amends 12 CFR Part 1002. It takes effect
    on January 1, 2027. Compliance is required by March 31, 2027."
    → Each sentence stays intact.
    """
    if not text or not text.strip():
        return []

    sentences = _SENTENCE_END.split(text)
    chunks: list[Chunk] = []
    current_text = ""
    current_start = 0
    char_pos = 0
    index = 0

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            char_pos += len(sentence) + 1
            continue

        if len(current_text) + len(sentence) > target_size and current_text:
            if len(current_text) >= MIN_CHUNK_SIZE:
                chunks.append(Chunk(
                    index=index, text=current_text.strip(),
                    start_char=current_start, end_char=char_pos,
                    strategy="sentence",
                ))
                index += 1
            current_text = sentence
            current_start = char_pos
        else:
            current_text = (current_text + " " + sentence).strip() if current_text else sentence

        char_pos += len(sentence) + 1

    if current_text and len(current_text) >= MIN_CHUNK_SIZE:
        chunks.append(Chunk(
            index=index, text=current_text.strip(),
            start_char=current_start, end_char=char_pos,
            strategy="sentence",
        ))

    return chunks


# ── Strategy 3: Paragraph-based ───────────────────────────────────────────────

def chunk_paragraphs(text: str, target_size: int = CHUNK_SIZE) -> list[Chunk]:
    """
    Split on double newlines (paragraph boundaries), accumulate until target size.

    Regulatory documents are structured in paragraphs. Each paragraph is
    a coherent unit of thought. Paragraph chunking keeps related sentences
    together — important for multi-sentence compliance requirements.

    Example:
      "Paragraph about scope." \n\n "Paragraph about effective dates." \n\n "..."
      → Each paragraph or group of small paragraphs becomes one chunk.
    """
    if not text or not text.strip():
        return []

    paragraphs = re.split(r'\n\s*\n', text)
    chunks: list[Chunk] = []
    current_text = ""
    current_start = 0
    char_pos = 0
    index = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            char_pos += len(para) + 2
            continue

        # If this single paragraph exceeds max size, split it with sentences
        if len(para) > MAX_CHUNK_SIZE:
            if current_text and len(current_text) >= MIN_CHUNK_SIZE:
                chunks.append(Chunk(index=index, text=current_text.strip(),
                                    start_char=current_start, end_char=char_pos,
                                    strategy="paragraph"))
                index += 1
                current_text = ""
                current_start = char_pos
            # Add oversized paragraph as its own chunk (trimmed)
            chunks.append(Chunk(index=index, text=para[:MAX_CHUNK_SIZE].strip(),
                                start_char=char_pos, end_char=char_pos + len(para),
                                strategy="paragraph"))
            index += 1
            char_pos += len(para) + 2
            continue

        if len(current_text) + len(para) > target_size and current_text:
            if len(current_text) >= MIN_CHUNK_SIZE:
                chunks.append(Chunk(index=index, text=current_text.strip(),
                                    start_char=current_start, end_char=char_pos,
                                    strategy="paragraph"))
                index += 1
            current_text = para
            current_start = char_pos
        else:
            current_text = (current_text + "\n\n" + para).strip() if current_text else para

        char_pos += len(para) + 2

    if current_text and len(current_text) >= MIN_CHUNK_SIZE:
        chunks.append(Chunk(index=index, text=current_text.strip(),
                            start_char=current_start, end_char=len(text),
                            strategy="paragraph"))

    return chunks


# ── Strategy 4: Recursive (paragraph → sentence → fixed fallback) ─────────────

def chunk_recursive(text: str, target_size: int = CHUNK_SIZE) -> list[Chunk]:
    """
    Try paragraph boundaries first. If paragraphs are too large, fall back
    to sentence boundaries. If sentences are too large, fall back to fixed-size.

    This is the most adaptive strategy — it respects document structure
    when possible and falls back to simpler methods when necessary.
    Think of it as: "use the largest unit that fits."
    """
    if not text or not text.strip():
        return []

    paragraphs = re.split(r'\n\s*\n', text)
    chunks: list[Chunk] = []
    index = 0
    char_pos = 0

    for para in paragraphs:
        para_stripped = para.strip()
        if not para_stripped:
            char_pos += len(para) + 2
            continue

        if len(para_stripped) <= target_size:
            # Paragraph fits — use it as-is
            if len(para_stripped) >= MIN_CHUNK_SIZE:
                chunks.append(Chunk(index=index, text=para_stripped,
                                    start_char=char_pos,
                                    end_char=char_pos + len(para),
                                    strategy="recursive"))
                index += 1
        else:
            # Paragraph too big — try sentence splitting
            sentences = _SENTENCE_END.split(para_stripped)
            current = ""
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                if len(current) + len(sentence) > target_size and current:
                    if len(current) >= MIN_CHUNK_SIZE:
                        chunks.append(Chunk(index=index, text=current.strip(),
                                            start_char=char_pos,
                                            end_char=char_pos + len(current),
                                            strategy="recursive"))
                        index += 1
                    current = sentence
                else:
                    current = (current + " " + sentence).strip() if current else sentence

                # Sentence itself exceeds target — fixed-size fallback
                if len(sentence) > target_size:
                    sub_chunks = chunk_fixed_size(sentence, target_size, OVERLAP)
                    for sc in sub_chunks:
                        sc.index = index
                        sc.strategy = "recursive"
                        chunks.append(sc)
                        index += 1
                    current = ""

            if current and len(current) >= MIN_CHUNK_SIZE:
                chunks.append(Chunk(index=index, text=current.strip(),
                                    start_char=char_pos,
                                    end_char=char_pos + len(current),
                                    strategy="recursive"))
                index += 1

        char_pos += len(para) + 2

    return chunks


# ── Strategy 5: Regulatory section-aware ──────────────────────────────────────

def chunk_regulatory(text: str, target_size: int = CHUNK_SIZE) -> list[Chunk]:
    """
    Split on regulatory section markers (§, PART, SECTION, numbered headings).

    Regulatory documents are organised by sections. Each section is a
    self-contained compliance unit. Splitting on section boundaries means
    each chunk answers a specific compliance question:
      - Section: Purpose
      - Section: Definitions
      - Section: Effective dates and compliance dates
      - Section: Affected institutions

    This is the most domain-specific strategy and often produces the
    highest-quality chunks for regulatory text.
    """
    if not text or not text.strip():
        return []

    # Find all section marker positions
    marker_positions = [m.start() for m in _REGULATORY_MARKERS.finditer(text)]

    if len(marker_positions) < 2:
        # No structure found — fall back to recursive
        result = chunk_recursive(text, target_size)
        for c in result:
            c.strategy = "regulatory"
        return result

    chunks: list[Chunk] = []
    index = 0

    # Add a synthetic start position and end position
    positions = [0] + marker_positions + [len(text)]

    for i in range(len(positions) - 1):
        section_text = text[positions[i]:positions[i+1]].strip()

        if not section_text or len(section_text) < MIN_CHUNK_SIZE:
            continue

        if len(section_text) <= target_size:
            chunks.append(Chunk(index=index, text=section_text,
                                start_char=positions[i], end_char=positions[i+1],
                                strategy="regulatory"))
            index += 1
        else:
            # Section too large — split with paragraph/sentence fallback
            sub = chunk_recursive(section_text, target_size)
            for sc in sub:
                sc.index = index
                sc.strategy = "regulatory"
                sc.start_char += positions[i]
                sc.end_char += positions[i]
                chunks.append(sc)
                index += 1

    return chunks


# ── Strategy 6: Hierarchical (Day 10) ────────────────────────────────────────

# Headers that signal compliance-critical sections — always retrieve these
_DATE_HEADERS = re.compile(
    r'(?i)(effective\s+date|compliance\s+date|compliance\s+deadline|'
    r'dates?\s+and\s+deadline|implementation\s+date|applicability\s+date|'
    r'when\s+does|takes?\s+effect|effective\s+period)',
)

_INSTITUTION_HEADERS = re.compile(
    r'(?i)(affected\s+institution|applicability|who\s+must|covered\s+institution|'
    r'scope|which\s+bank|institution\s+type|covered\s+entit)',
)

# Table detection — rows of pipe-separated or tab-separated values
_TABLE_LINE = re.compile(r'.*\|.*\|.*|.*\t.*\t.*')

# All-caps header line (common in regulatory docs: "EFFECTIVE DATES AND COMPLIANCE")
_ALL_CAPS_HEADER = re.compile(r'^[A-Z][A-Z\s\-–—]{8,}[A-Z]$')

# Numbered/lettered section headers: "I. Purpose", "A. Background", "(a) General"
_NUMBERED_HEADER = re.compile(r'^(?:[IVXLC]+\.|[A-Z]\.|[a-z]\.|[(]\d+[)]|[(][a-z][)])\s+\S')


@dataclass
class HierarchicalChunk(Chunk):
    """
    A chunk with extra metadata about its structural role.
    is_date_section and is_institution_section are used by the retriever
    to boost these chunks to the top of the retrieved set regardless of score.
    """
    section_header: str = ""       # the header that introduced this chunk
    is_date_section: bool = False  # True if header mentions dates/deadlines
    is_institution_section: bool = False  # True if header mentions institutions
    is_table: bool = False         # True if chunk contains a table


def _detect_tables(text: str) -> list[tuple[int, int]]:
    """
    Return (start, end) character ranges of table blocks in the text.
    A table block = 2+ consecutive lines that look like table rows.
    """
    lines = text.split('\n')
    tables = []
    in_table = False
    table_start_line = 0
    char_pos = 0
    line_char_positions = []

    for line in lines:
        line_char_positions.append(char_pos)
        char_pos += len(line) + 1

    for i, line in enumerate(lines):
        is_table_line = bool(_TABLE_LINE.match(line.strip())) and len(line.strip()) > 5
        if is_table_line and not in_table:
            in_table = True
            table_start_line = i
        elif not is_table_line and in_table:
            # End of table — need at least 2 rows to count as a table
            if i - table_start_line >= 2:
                start = line_char_positions[table_start_line]
                end = line_char_positions[i] if i < len(line_char_positions) else char_pos
                tables.append((start, end))
            in_table = False

    if in_table and len(lines) - table_start_line >= 2:
        tables.append((line_char_positions[table_start_line], char_pos))

    return tables


def _is_header(line: str) -> bool:
    """True if a line looks like a section header."""
    stripped = line.strip()
    if not stripped:
        return False
    return (
        bool(_ALL_CAPS_HEADER.match(stripped))
        or bool(_NUMBERED_HEADER.match(stripped))
        or bool(_REGULATORY_MARKERS.match(stripped))
    )


def chunk_hierarchical(text: str, target_size: int = CHUNK_SIZE) -> list[HierarchicalChunk]:
    """
    Hierarchical chunking: detect structure, then chunk intelligently within it.

    Algorithm:
      1. Detect tables — keep each table as one intact chunk
      2. Detect section headers — use them as chunk boundaries
      3. For prose between headers — apply sentence chunking
      4. Tag each chunk with its parent header and priority flags

    Why this beats sentence chunking for compliance documents:
      - Tables are kept whole (institution type tables, date tables)
      - "EFFECTIVE DATE" header tags its section for priority retrieval
      - Headers provide context even when the chunk text doesn't contain
        compliance keywords (e.g., a section header "III. Compliance Dates"
        above otherwise-generic prose)

    Fallback: if no headers detected, falls back to sentence chunking.
    """
    if not text or not text.strip():
        return []

    lines = text.split('\n')
    chunks: list[HierarchicalChunk] = []
    index = 0

    # Pass 1: identify table regions (preserve intact)
    table_regions = _detect_tables(text)
    table_char_ranges = set()
    for start, end in table_regions:
        for pos in range(start, end):
            table_char_ranges.add(pos)

    # Build segments: (header, content_text, char_start, is_table)
    segments: list[dict] = []
    current_header = ""
    current_lines: list[str] = []
    char_pos = 0
    segment_start = 0

    for line in lines:
        line_end = char_pos + len(line) + 1

        if _is_header(line) and line.strip():
            # Save current segment
            if current_lines:
                segments.append({
                    "header": current_header,
                    "text": '\n'.join(current_lines).strip(),
                    "start": segment_start,
                    "end": char_pos,
                    "is_table": any(p in table_char_ranges for p in range(segment_start, char_pos)),
                })
            current_header = line.strip()
            current_lines = []
            segment_start = char_pos
        else:
            current_lines.append(line)

        char_pos = line_end

    # Save final segment
    if current_lines:
        segments.append({
            "header": current_header,
            "text": '\n'.join(current_lines).strip(),
            "start": segment_start,
            "end": char_pos,
            "is_table": any(p in table_char_ranges for p in range(segment_start, char_pos)),
        })

    # Fallback if no structure detected
    if len(segments) <= 1:
        fallback = chunk_sentences(text, target_size)
        result = []
        for c in fallback:
            hc = HierarchicalChunk(
                index=c.index, text=c.text,
                start_char=c.start_char, end_char=c.end_char,
                strategy="hierarchical",
            )
            result.append(hc)
        return result

    # Pass 2: convert segments to chunks
    for seg in segments:
        seg_text = seg["text"]
        header = seg["header"]
        if not seg_text or len(seg_text) < MIN_CHUNK_SIZE:
            continue

        is_date = bool(_DATE_HEADERS.search(header)) or bool(_DATE_HEADERS.search(seg_text[:200]))
        is_inst = bool(_INSTITUTION_HEADERS.search(header)) or bool(_INSTITUTION_HEADERS.search(seg_text[:200]))
        is_tbl = seg["is_table"]

        if is_tbl or len(seg_text) <= target_size:
            # Keep table or short section as one chunk
            display_text = (f"{header}\n\n{seg_text}".strip()
                            if header else seg_text.strip())
            if len(display_text) >= MIN_CHUNK_SIZE:
                chunks.append(HierarchicalChunk(
                    index=index, text=display_text[:MAX_CHUNK_SIZE],
                    start_char=seg["start"], end_char=seg["end"],
                    strategy="hierarchical",
                    section_header=header,
                    is_date_section=is_date,
                    is_institution_section=is_inst,
                    is_table=is_tbl,
                ))
                index += 1
        else:
            # Section too large — sentence-split the prose
            sub_chunks = chunk_sentences(seg_text, target_size)
            for sc in sub_chunks:
                display_text = (f"{header}\n\n{sc.text}".strip()
                                if header and sc.index == 0 else sc.text)
                chunks.append(HierarchicalChunk(
                    index=index, text=display_text,
                    start_char=seg["start"] + sc.start_char,
                    end_char=seg["start"] + sc.end_char,
                    strategy="hierarchical",
                    section_header=header,
                    is_date_section=is_date,
                    is_institution_section=is_inst,
                    is_table=False,
                ))
                index += 1

    # Re-index sequentially
    for i, c in enumerate(chunks):
        c.index = i

    return chunks


# ── Unified interface ──────────────────────────────────────────────────────────

STRATEGIES = {
    "fixed_size": chunk_fixed_size,
    "sentence": chunk_sentences,
    "paragraph": chunk_paragraphs,
    "recursive": chunk_recursive,
    "regulatory": chunk_regulatory,
    "hierarchical": chunk_hierarchical,
}


def chunk_with_strategy(text: str, strategy: str = "fixed_size") -> list[Chunk]:
    """
    Chunk a document using the named strategy.
    Valid strategies: fixed_size, sentence, paragraph, recursive, regulatory, hierarchical.
    """
    if strategy not in STRATEGIES:
        raise ValueError(f"Unknown strategy '{strategy}'. Choose from: {list(STRATEGIES)}")
    return STRATEGIES[strategy](text)


# ── Stats ──────────────────────────────────────────────────────────────────────

def chunk_stats(chunks: list[Chunk]) -> dict:
    """Return summary statistics about a set of chunks."""
    if not chunks:
        return {"count": 0, "avg_chars": 0, "min_chars": 0, "max_chars": 0,
                "strategy": "none"}

    sizes = [len(c.text) for c in chunks]
    return {
        "count": len(chunks),
        "avg_chars": round(sum(sizes) / len(sizes)),
        "min_chars": min(sizes),
        "max_chars": max(sizes),
        "strategy": chunks[0].strategy if chunks else "unknown",
    }
