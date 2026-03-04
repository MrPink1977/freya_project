# =============================================================================
# setup_knowledge_bases.ps1
# =============================================================================
# Organizes all three Freya knowledge bases into a clean, consistent directory
# structure under C:\AI_Projects\homeassistant\knowledge_bases\
#
# Knowledge Bases:
#   1. ha_docs                  — Home Assistant documentation (existing)
#   2. google_dorking_knowledge — Google dorking techniques (existing)
#   3. prompt_engineering_kb    — Prompt engineering techniques (new)
#
# Run this script once from PowerShell:
#   cd C:\AI_Projects\homeassistant
#   .\knowledge_bases\setup_knowledge_bases.ps1
# =============================================================================

$ErrorActionPreference = "Stop"
$ROOT = "C:\AI_Projects\homeassistant"
$KB_ROOT = "$ROOT\knowledge_bases"

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Freya Knowledge Base Setup" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# =============================================================================
# STEP 1 — Create the unified knowledge_bases directory structure
# =============================================================================
Write-Host "[1/4] Creating directory structure..." -ForegroundColor Yellow

$dirs = @(
    "$KB_ROOT\ha_docs\scripts",
    "$KB_ROOT\ha_docs\data",
    "$KB_ROOT\google_dorking_knowledge\scripts",
    "$KB_ROOT\google_dorking_knowledge\data",
    "$KB_ROOT\prompt_engineering_kb\scripts",
    "$KB_ROOT\prompt_engineering_kb\data"
)

foreach ($dir in $dirs) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Host "  Created: $dir" -ForegroundColor Green
    } else {
        Write-Host "  Exists:  $dir" -ForegroundColor DarkGray
    }
}

# =============================================================================
# STEP 2 — Move / copy existing ha_knowledge_base files
# =============================================================================
Write-Host ""
Write-Host "[2/4] Organizing ha_docs knowledge base..." -ForegroundColor Yellow

$HA_KB_OLD = "C:\AI_Projects\ha_knowledge_base"

if (Test-Path "$HA_KB_OLD\import_ha_docs_to_chromadb.py") {
    Copy-Item "$HA_KB_OLD\import_ha_docs_to_chromadb.py" `
              "$KB_ROOT\ha_docs\scripts\import_ha_docs_to_chromadb.py" -Force
    Write-Host "  Copied: import_ha_docs_to_chromadb.py" -ForegroundColor Green
} else {
    Write-Host "  [SKIP] import_ha_docs_to_chromadb.py not found at $HA_KB_OLD" -ForegroundColor DarkYellow
    Write-Host "         If it's elsewhere, copy it to: $KB_ROOT\ha_docs\scripts\" -ForegroundColor DarkYellow
}

# Note: The chroma_db data directory is large — we don't move it, just note its location
Write-Host "  NOTE: ha_docs ChromaDB data lives at $HA_KB_OLD\chroma_db\" -ForegroundColor DarkGray
Write-Host "        (Not moved — it's mounted read-only by Docker. No action needed.)" -ForegroundColor DarkGray

# =============================================================================
# STEP 3 — Move / copy existing Google dorking files
# =============================================================================
Write-Host ""
Write-Host "[3/4] Organizing google_dorking_knowledge base..." -ForegroundColor Yellow

# Common locations where the dorking import script might live
$DORK_CANDIDATES = @(
    "$ROOT\import_google_dorking.py",
    "$ROOT\scripts\import_google_dorking.py",
    "$ROOT\google_dorking_import.py",
    "$ROOT\scripts\google_dorking_import.py",
    "C:\AI_Projects\ha_knowledge_base\import_google_dorking.py"
)

$dorkFound = $false
foreach ($candidate in $DORK_CANDIDATES) {
    if (Test-Path $candidate) {
        Copy-Item $candidate "$KB_ROOT\google_dorking_knowledge\scripts\import_google_dorking.py" -Force
        Write-Host "  Copied from: $candidate" -ForegroundColor Green
        $dorkFound = $true
        break
    }
}

if (-not $dorkFound) {
    Write-Host "  [INFO] Google dorking import script not found in common locations." -ForegroundColor DarkYellow
    Write-Host "         Manually copy it to: $KB_ROOT\google_dorking_knowledge\scripts\" -ForegroundColor DarkYellow
}

# =============================================================================
# STEP 4 — Place prompt_engineering_kb files
# =============================================================================
Write-Host ""
Write-Host "[4/4] Organizing prompt_engineering_kb..." -ForegroundColor Yellow

# The user should have downloaded these from GitHub (PR #29)
# Check if they're already in the repo clone location
$PE_CANDIDATES = @(
    "$ROOT\prompt_engineering_kb",
    "$ROOT\freya_project\prompt_engineering_kb"
)

$peFound = $false
foreach ($candidate in $PE_CANDIDATES) {
    if (Test-Path "$candidate\data\prompt_engineering_chunks.json") {
        Copy-Item "$candidate\scripts\ingest_to_chromadb.py" `
                  "$KB_ROOT\prompt_engineering_kb\scripts\ingest_to_chromadb.py" -Force
        Copy-Item "$candidate\scripts\process_research.py" `
                  "$KB_ROOT\prompt_engineering_kb\scripts\process_research.py" -Force
        Copy-Item "$candidate\data\prompt_engineering_chunks.json" `
                  "$KB_ROOT\prompt_engineering_kb\data\prompt_engineering_chunks.json" -Force
        Copy-Item "$candidate\data\raw_research.json" `
                  "$KB_ROOT\prompt_engineering_kb\data\raw_research.json" -Force
        Write-Host "  Copied from: $candidate" -ForegroundColor Green
        $peFound = $true
        break
    }
}

if (-not $peFound) {
    Write-Host "  [INFO] prompt_engineering_kb files not found locally." -ForegroundColor DarkYellow
    Write-Host "         Download them from GitHub PR #29 and place in:" -ForegroundColor DarkYellow
    Write-Host "           $KB_ROOT\prompt_engineering_kb\scripts\" -ForegroundColor DarkYellow
    Write-Host "           $KB_ROOT\prompt_engineering_kb\data\" -ForegroundColor DarkYellow
}

# =============================================================================
# SUMMARY
# =============================================================================
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Setup Complete — Final Structure" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  $KB_ROOT\" -ForegroundColor White
Write-Host "  +-- ha_docs\" -ForegroundColor White
Write-Host "  |   +-- scripts\import_ha_docs_to_chromadb.py" -ForegroundColor DarkGray
Write-Host "  |   +-- data\  (source docs live at C:\AI_Projects\ha_knowledge_base\)" -ForegroundColor DarkGray
Write-Host "  +-- google_dorking_knowledge\" -ForegroundColor White
Write-Host "  |   +-- scripts\import_google_dorking.py" -ForegroundColor DarkGray
Write-Host "  +-- prompt_engineering_kb\" -ForegroundColor White
Write-Host "      +-- scripts\ingest_to_chromadb.py" -ForegroundColor DarkGray
Write-Host "      +-- scripts\process_research.py" -ForegroundColor DarkGray
Write-Host "      +-- data\prompt_engineering_chunks.json" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  Next step: Run the ingestion script to load prompt_engineering_kb" -ForegroundColor Yellow
Write-Host "  into ChromaDB:" -ForegroundColor Yellow
Write-Host ""
Write-Host "    python knowledge_bases\prompt_engineering_kb\scripts\ingest_to_chromadb.py" -ForegroundColor Cyan
Write-Host ""
