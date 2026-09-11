# XFed-IDS Chat 04 -- Full 9-config instrumented sweep.
# Runs all (alpha, seed) combos at the locked 20 rounds, with LoggingFedAvg
# capturing per-round global checkpoints + per-silo weights/metrics.
# After each config, verifies file counts before moving to the next --
# stops immediately on a mismatch instead of burning hours on broken runs.
#
# Run from project root:
#   powershell -ExecutionPolicy Bypass -File tools\run_sweep.ps1

$ErrorActionPreference = "Stop"

# Encoding fix (Flower's box-drawing summary crashes cp1252 otherwise) --
# set again here in case this runs in a fresh terminal.
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

New-Item -ItemType Directory -Force -Path ".\results\inspection" | Out-Null

$configs = @(
    @{alpha='0.1'; seed=42},
    @{alpha='0.1'; seed=1337},
    @{alpha='0.1'; seed=2024},
    @{alpha='0.5'; seed=42},
    @{alpha='0.5'; seed=1337},
    @{alpha='0.5'; seed=2024},
    @{alpha='5.0'; seed=42},
    @{alpha='5.0'; seed=1337},
    @{alpha='5.0'; seed=2024}
)

$summaryPath = ".\results\inspection\sweep_summary.txt"
"XFed-IDS Chat 04 sweep started: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Out-File -FilePath $summaryPath

$overallStart = Get-Date

foreach ($c in $configs) {
    $tag = "fedavg_a$($c.alpha)_s$($c.seed)"
    $logPath = ".\results\inspection\sweep_$tag.log"
    $resultDir = ".\results\federated\$tag"

    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "STARTING: $tag" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan

    $configStart = Get-Date

    $runConfig = "alpha='$($c.alpha)' seed=$($c.seed) num-server-rounds=20"
    flwr run federated local-simulation --run-config $runConfig --stream 2>&1 |
        Tee-Object -FilePath $logPath

    $elapsed = (Get-Date) - $configStart
    Write-Host "`n$tag finished in $([math]::Round($elapsed.TotalMinutes,1)) min. Verifying..." -ForegroundColor Yellow

    # --- Verification: 20 rounds -> 21 round checkpoints (000-020),
    # 200 silo checkpoints (10 silos x 20 rounds), 400 metric lines
    # (10 silos x 20 rounds x 2 phases). ---
    $ok = $true
    $reasons = @()

    if (-not (Test-Path $resultDir)) {
        $ok = $false
        $reasons += "result dir missing entirely"
    } else {
        $roundCkpts = (Get-ChildItem "$resultDir\round_checkpoints" -ErrorAction SilentlyContinue).Count
        $siloCkpts  = (Get-ChildItem "$resultDir\silo_checkpoints" -ErrorAction SilentlyContinue).Count
        $metricsPath = "$resultDir\silo_metrics.jsonl"
        $metricsLines = 0
        if (Test-Path $metricsPath) {
            $metricsLines = (Get-Content $metricsPath).Count
        }
        $hasFinal = Test-Path "$resultDir\final_metrics.json"
        $hasBest  = Test-Path "$resultDir\model_best.pt"

        if ($roundCkpts -ne 21)  { $ok = $false; $reasons += "round_checkpoints=$roundCkpts (expected 21)" }
        if ($siloCkpts  -ne 200) { $ok = $false; $reasons += "silo_checkpoints=$siloCkpts (expected 200)" }
        if ($metricsLines -ne 400) { $ok = $false; $reasons += "metrics_lines=$metricsLines (expected 400)" }
        if (-not $hasFinal) { $ok = $false; $reasons += "final_metrics.json missing" }
        if (-not $hasBest)  { $ok = $false; $reasons += "model_best.pt missing" }
    }

    if ($ok) {
        $line = "PASS  $tag  ($([math]::Round($elapsed.TotalMinutes,1)) min)  round_ckpts=21 silo_ckpts=200 metrics=400"
        Write-Host $line -ForegroundColor Green
        $line | Out-File -FilePath $summaryPath -Append
    } else {
        $line = "FAIL  $tag  reasons: $($reasons -join '; ')"
        Write-Host $line -ForegroundColor Red
        $line | Out-File -FilePath $summaryPath -Append
        Write-Host "`nSTOPPING SWEEP -- do not continue to the next config until this is fixed." -ForegroundColor Red
        Write-Host "Full log for this run: $logPath" -ForegroundColor Red
        exit 1
    }
}

$overallElapsed = (Get-Date) - $overallStart
$finalLine = "`nALL 9 CONFIGS PASSED. Total time: $([math]::Round($overallElapsed.TotalHours,2)) hours."
Write-Host $finalLine -ForegroundColor Green
$finalLine | Out-File -FilePath $summaryPath -Append
