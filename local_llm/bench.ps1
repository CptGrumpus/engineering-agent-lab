<#
.SYNOPSIS
  Run llama-bench on Inkling 2 Mini and append each result, with the host state, to ledger.jsonl.

.EXAMPLE
  .\local_llm\bench.ps1 -Label "O4 t=6 ccd2" -BenchArgs "-t 6 -C 0xFFF000 -p 512 -n 64 -r 5"

  Always passed: -m <model> -ngl 99 -o jsonl. Defaults (overridable in BenchArgs): -ncmoe 99.
  Host state is recorded before and after; if solver processes start or stop mid-run, the line gets
  "host_changed": true and the run should be treated as void.
#>
param(
    [Parameter(Mandatory)] [string] $Label,
    [string] $BenchArgs = "",   # one string, split on spaces, so it works from PowerShell and from `powershell -File`
    [string] $Note = ""
)
$ErrorActionPreference = 'Stop'
$BenchList = @($BenchArgs -split '\s+' | Where-Object { $_ })

$Engine = "$env:LOCALAPPDATA\Programs\llama.cpp-unsloth-b12588"
# The Unsloth zip lacks the CUDA runtime; the mainline b12608 folder ships it (CUDA 12.4). See PLAN.md O2.
$CudaRuntime = "$env:LOCALAPPDATA\Programs\llama.cpp-b12608"
$Model = "$env:USERPROFILE\.ollama\models\blobs\sha256-f90c5a4df44d335ac9f9eea2a15c31d6c5a377b1b3cd9ff7fc2cf123f3cdf7e1"
$Ledger = Join-Path $PSScriptRoot 'ledger.jsonl'
$SolverPattern = 'pimpleFoam|simpleFoam|icoFoam|ccx|CalculiX|ElmerSolver|code_aster|mpirun|foamRun'

function Get-HostState {
    $cpu = (Get-CimInstance Win32_Processor | Measure-Object LoadPercentage -Average).Average
    $solvers = @(wsl -e sh -c "ps -eo comm=" 2>$null | Where-Object { $_ -match $SolverPattern })
    $gpuUsed = [int](nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits)
    [ordered]@{ cpu_load_pct = $cpu; solvers = ($solvers | Sort-Object -Unique) -join ','; solver_procs = $solvers.Count; gpu_mem_used_mib = $gpuUsed }
}

$env:PATH = "$CudaRuntime;$env:PATH"
$args2 = @('-m', $Model, '-ngl', '99', '-o', 'jsonl')
if ($BenchList -notcontains '-ncmoe' -and $BenchList -notcontains '--n-cpu-moe' -and $BenchList -notcontains '-ot') { $args2 += @('-ncmoe', '99') }
$args2 += $BenchList

$before = Get-HostState
$started = Get-Date
# PowerShell 5.1 turns native stderr lines into errors under 'Stop'; llama-bench logs to stderr.
$ErrorActionPreference = 'Continue'
# Sample GPU memory once a second in the background to record the peak during the run.
$vramJob = Start-Job { $max = 0; while ($true) { $v = [int](nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits); if ($v -gt $max) { $max = $v; Set-Content -Path $using:env:TEMP\llm_vram_peak.txt -Value $max }; Start-Sleep -Milliseconds 1000 } }
$out = & "$Engine\llama-bench.exe" @args2 2>$null
Stop-Job $vramJob; Remove-Job $vramJob
$vramPeak = [int](Get-Content "$env:TEMP\llm_vram_peak.txt" -ErrorAction SilentlyContinue); Remove-Item "$env:TEMP\llm_vram_peak.txt" -ErrorAction SilentlyContinue
$ErrorActionPreference = 'Stop'
$after = Get-HostState
$changed = ($before.solvers -ne $after.solvers)

$n = 0
foreach ($line in $out) {
    if ($line -notmatch '^\s*\{') { continue }
    $r = $line | ConvertFrom-Json
    $r.model_filename = Split-Path $r.model_filename -Leaf   # keep home-directory paths out of the repo
    $test = if ($r.n_gen -gt 0) { "tg$($r.n_gen)" } else { "pp$($r.n_prompt)" }
    $rec = [ordered]@{
        time = $started.ToString('s'); label = $Label; note = $Note; test = $test
        tok_s = [math]::Round($r.avg_ts, 2); tok_s_sd = [math]::Round($r.stddev_ts, 2); reps = @($r.samples_ts).Count
        args = ($BenchList -join ' '); host_before = $before; host_after = $after; host_changed = $changed
        gpu_mem_peak_mib = $vramPeak; raw = $r
    }
    ($rec | ConvertTo-Json -Compress -Depth 6) | Add-Content -Path $Ledger -Encoding utf8
    "{0,-28} {1,-8} b={6} ub={7} t={8} {2,9:N2} +/- {3,-6:N2} tok/s  vram peak {9} MiB  (solvers: {4}; changed: {5})" -f $Label, $test, $rec.tok_s, $rec.tok_s_sd, ($before.solvers -replace '^$', 'none'), $changed, $r.n_batch, $r.n_ubatch, $r.n_threads, $vramPeak
    $n++
}
if ($n -eq 0) { Write-Error "llama-bench produced no results. Output:`n$($out -join "`n")" }
