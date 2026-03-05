# setup_knowledge_bases.ps1
# Organizes all Freya knowledge bases into a clean unified structure.
# Run from: C:\AI_Projects\homeassistant
# Command:  powershell -ExecutionPolicy Bypass -File "C:\AI_Projects\homeassistant\freya_project\knowledge_bases\setup_knowledge_bases.ps1"

$ErrorActionPreference = "Stop"
$ROOT    = "C:\AI_Projects\homeassistant"
$KB_ROOT = "$ROOT\knowledge_bases"
$REPO    = "$ROOT\freya_project"

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Freya Knowledge Base Setup" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# --- STEP 1: Create directory structure ---
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

# --- STEP 2: ha_docs ---
Write-Host ""
Write-Host "[2/4] Organizing ha_docs knowledge base..." -ForegroundColor Yellow

$HA_SCRIPT_CANDIDATES = @(
    "$ROOT\import_ha_docs_to_chromadb.py",
    "C:\AI_Projects\ha_knowledge_base\import_ha_docs_to_chromadb.py"
)

$haFound = $false
foreach ($candidate in $HA_SCRIPT_CANDIDATES) {
    if (Test-Path $candidate) {
        Copy-Item $candidate "$KB_ROOT\ha_docs\scripts\import_ha_docs_to_chromadb.py" -Force
        Write-Host "  Copied: import_ha_docs_to_chromadb.py" -ForegroundColor Green
        $haFound = $true
        break
    }
}

if (-not $haFound) {
    Write-Host "  [INFO] import_ha_docs_to_chromadb.py not found automatically." -ForegroundColor DarkYellow
    Write-Host "         Manually copy it to: $KB_ROOT\ha_docs\scripts\" -ForegroundColor DarkYellow
}

Write-Host "  NOTE: ha_docs ChromaDB data stays at C:\AI_Projects\ha_knowledge_base\chroma_db\" -ForegroundColor DarkGray
Write-Host "        It is mounted read-only by Docker. No action needed." -ForegroundColor DarkGray

# --- STEP 3: google_dorking_knowledge ---
Write-Host ""
Write-Host "[3/4] Organizing google_dorking_knowledge base..." -ForegroundColor Yellow

$DORK_CANDIDATES = @(
    "$ROOT\import_google_dorking.py",
    "$ROOT\scripts\import_google_dorking.py",
    "$ROOT\google_dorking_import.py",
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
    Write-Host "  [INFO] Google dorking import script not found automatically." -ForegroundColor DarkYellow
    Write-Host "         Manually copy it to: $KB_ROOT\google_dorking_knowledge\scripts\" -ForegroundColor DarkYellow
}

# --- STEP 4: prompt_engineering_kb ---
Write-Host ""
Write-Host "[4/4] Organizing prompt_engineering_kb..." -ForegroundColor Yellow

$PE_CANDIDATES = @(
    "$REPO\prompt_engineering_kb",
    "$REPO\knowledge_bases\prompt_engineering_kb",
    "$ROOT\prompt_engineering_kb"
)

$peFound = $false
foreach ($candidate in $PE_CANDIDATES) {
    if (Test-Path "$candidate\data\prompt_engineering_chunks.json") {
        Copy-Item "$candidate\scripts\ingest_to_chromadb.py"  "$KB_ROOT\prompt_engineering_kb\scripts\ingest_to_chromadb.py"  -Force
        Copy-Item "$candidate\scripts\process_research.py"    "$KB_ROOT\prompt_engineering_kb\scripts\process_research.py"    -Force
        Copy-Item "$candidate\data\prompt_engineering_chunks.json" "$KB_ROOT\prompt_engineering_kb\data\prompt_engineering_chunks.json" -Force
        if (Test-Path "$candidate\data\raw_research.json") {
            Copy-Item "$candidate\data\raw_research.json" "$KB_ROOT\prompt_engineering_kb\data\raw_research.json" -Force
        }
        Write-Host "  Copied from: $candidate" -ForegroundColor Green
        $peFound = $true
        break
    }
}

if (-not $peFound) {
    Write-Host "  [INFO] prompt_engineering_kb files not found automatically." -ForegroundColor DarkYellow
    Write-Host "         They should be in the freya_project repo clone." -ForegroundColor DarkYellow
    Write-Host "         Expected location: $REPO\knowledge_bases\prompt_engineering_kb\" -ForegroundColor DarkYellow
}

# --- SUMMARY ---
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Done!" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Knowledge bases organized under:" -ForegroundColor White
Write-Host "  $KB_ROOT" -ForegroundColor White
Write-Host ""
Write-Host "  ChromaDB collections already loaded:" -ForegroundColor White
Write-Host "  - ha_docs (37791 docs)" -ForegroundColor DarkGray
Write-Host "  - google_dorking_knowledge" -ForegroundColor DarkGray
Write-Host "  - prompt_engineering_kb (151 docs)" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  Next: Paste freya_system_prompt.txt into Home Agent." -ForegroundColor Yellow
Write-Host ""
