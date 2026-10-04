"""All numeric thresholds in one place (CS5, K3).

K3: كل عتبة هنا بتعليق: القيمة، وتاريخها المعياري. أي تغيير يستلزم
تشغيل `make eval` وإلحاق النتيجة في eval/results/.

Calibration baseline: initial values proposed from requirements
(Needs Clarification, §17.2 — تُعايَر على Gold Set). Date: 2026-10-04.
"""

from __future__ import annotations

# --- Matching (match.py) ---
# Minimum similarity (0..1) for a fuzzy window to count as a candidate
# location. Baseline 0.60 — calibrate on Gold Set (Needs Clarification).
FUZZY_CANDIDATE_THRESHOLD: float = 0.60

# Similarity at or above which a fuzzy match is MINOR_DIFF
# (differences limited to tashkil/tatweel/punctuation/hamza-form).
# Baseline 0.95 — calibrate on Gold Set.
MINOR_DIFF_THRESHOLD: float = 0.95

# Similarity at or above which a fuzzy match is ALTERED rather than
# NOT_FOUND. Below this, falls back to SEMANTIC_ONLY / NOT_FOUND.
# Baseline 0.75 — single-word substitution scores ~0.79 with fuzz.ratio;
# unrelated text scores <0.60. Calibrate on Gold Set (§17.2).
ALTERED_THRESHOLD: float = 0.75

# Semantic-only similarity band: a paragraph close in meaning but not a
# literal quote (S5). Baseline 0.60 — calibrate on Gold Set.
SEMANTIC_ONLY_THRESHOLD: float = 0.60

# Sliding window: how many quote-word multiples around the quote length
# to scan when fuzzy matching.
WINDOW_PADDING_WORDS: int = 4

# Quotes shorter than this many words get a reliability warning (TC-18).
MIN_RELIABLE_QUOTE_WORDS: int = 3

# Maximum words of matched source text displayed per quote (§17.3).
MAX_DISPLAY_QUOTE_WORDS: int = 60

# --- OCR quality (M9, FR-06) ---
# Pages whose OCR mean confidence is below this are flagged low quality.
OCR_LOW_QUALITY_THRESHOLD: float = 0.60

# --- Retrieval (retrieve.py) ---
# Hybrid retrieval: number of candidates taken from each channel before
# Reciprocal Rank Fusion (§16.2: K between 5 and 8, tuned by experiment).
RETRIEVE_TOP_K: int = 6

# Abstention threshold: fused RRF score below this means no usable
# evidence (§16.3 — calibrate on Gold Set). Best two-channel score is
# ~0.033 with RRF_K=60; a lone single-channel hit is ~0.016.
ABSTAIN_SCORE_THRESHOLD: float = 0.012

# Upper bound of the single-channel RRF band; a semantic-only best hit
# below this means the question shares no keywords with the source.
RRF_SINGLE_CHANNEL_MAX: float = 0.020

# Reciprocal Rank Fusion smoothing constant.
RRF_K: int = 60

# --- Chunking (§16.1) ---
CHUNK_TARGET_WORDS: int = 180
CHUNK_OVERLAP_WORDS: int = 40

# --- LLM ---
LLM_MAX_RETRIES: int = 1  # E4: one retry, then ABSTAIN
