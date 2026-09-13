param(
    [switch]$Auto,
    [switch]$SkipOpen
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repoRoot

$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
$paylab = Join-Path $repoRoot ".venv\Scripts\paylab.exe"
$dashboardUrl = "http://127.0.0.1:8787/dashboard"
$healthUrl = "http://127.0.0.1:8787/health"
$merchantUrl = "http://127.0.0.1:9000/"
$webhookUrl = "http://127.0.0.1:9000/webhooks/paystack"
$probeUrl = "http://127.0.0.1:9000/paylab/probe"
$reportPath = Join-Path $repoRoot "paylab-demo-report.html"

function Write-Stage([string]$Title, [string]$Message) {
    Write-Host ""
    Write-Host "============================================================"
    Write-Host $Title
    Write-Host "============================================================"
    Write-Host $Message
    Write-Host ""
}

function Pause-Demo([string]$Prompt) {
    if (-not $Auto) {
        Read-Host "$Prompt  Press Enter to continue"
    }
}

function Test-Endpoint([string]$Url) {
    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2
        return ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500)
    }
    catch {
        return $false
    }
}

function Wait-Endpoint([string]$Url, [string]$Name) {
    for ($i = 0; $i -lt 30; $i++) {
        if (Test-Endpoint $Url) {
            Write-Host "$Name is ready: $Url"
            return
        }
        Start-Sleep -Milliseconds 500
    }
    throw "$Name did not become ready at $Url"
}

if (-not (Test-Path $python)) {
    throw "Missing .venv. From the repository root run: python -m venv .venv; .\.venv\Scripts\Activate.ps1; python -m pip install -e `".[dev]`""
}

if (-not (Test-Path $paylab)) {
    throw "PayLab CLI is not installed in .venv. Run: .\.venv\Scripts\Activate.ps1; python -m pip install -e `".[dev]`""
}

Write-Stage "PAYLAB LAUNCH DEMO" "Break your payment integration before your customers do."

if (-not (Test-Endpoint $healthUrl)) {
    Write-Host "Starting PayLab API on port 8787..."
    Start-Process -FilePath $paylab -ArgumentList @("start") -WorkingDirectory $repoRoot | Out-Null
}
Wait-Endpoint $healthUrl "PayLab API"

if (-not (Test-Endpoint $merchantUrl)) {
    Write-Host "Starting demo merchant on port 9000..."
    Start-Process -FilePath $python -ArgumentList @("-m", "uvicorn", "examples.demo_receiver:app", "--port", "9000") -WorkingDirectory $repoRoot | Out-Null
}
Wait-Endpoint $merchantUrl "Demo merchant"

if (-not $SkipOpen) {
    Start-Process $dashboardUrl
}

Pause-Demo "Dashboard opened at $dashboardUrl. Put the dashboard and this terminal side-by-side for recording."

Write-Stage "1. HEALTHY SIGNED WEBHOOK" "First, prove the normal payment webhook works."
& $paylab trigger paystack charge.success $webhookUrl --secret sk_test_paylab
Pause-Demo "Show the successful delivery in the terminal and dashboard."

Write-Stage "2. DUPLICATE DELIVERY" "Now simulate a provider delivering the same payment webhook three times. A safe integration should acknowledge duplicates without creating duplicate business side effects."
& $paylab trigger paystack charge.success $webhookUrl --secret sk_test_paylab --duplicate 3
Pause-Demo "Point at delivery 1, 2 and 3 in the terminal, then show the dashboard activity."

Write-Stage "3. INVALID SIGNATURE" "Now send a webhook signed with the wrong secret. The demo merchant should reject it."
& $paylab trigger paystack charge.success $webhookUrl --secret sk_test_paylab --invalid-signature
Pause-Demo "Show the rejected delivery. This demonstrates signature-verification testing."

Write-Stage "4. OUT-OF-ORDER LIFECYCLE" "Payment providers do not guarantee perfect event ordering. PayLab can reverse a lifecycle to expose fragile state assumptions."
& $paylab lifecycle paystack $webhookUrl --secret sk_test_paylab --out-of-order
Pause-Demo "Show the lifecycle output, then glance back at the dashboard."

Write-Stage "5. CHECKOUT CHAOS SUITE" "Run the full checkout reliability suite with retry/fault recovery and a business-level idempotency probe."
if (Test-Path $reportPath) {
    Remove-Item $reportPath -Force
}

& $paylab chaos checkout paystack charge.success $webhookUrl `
    --secret sk_test_paylab `
    --deep `
    --probe-url $probeUrl `
    --html $reportPath

$chaosExitCode = $LASTEXITCODE
if ($chaosExitCode -notin @(0, 2)) {
    throw "PayLab chaos demo failed unexpectedly with exit code $chaosExitCode"
}

if (Test-Path $reportPath) {
    Write-Host ""
    Write-Host "HTML reliability report: $reportPath"
    if (-not $SkipOpen) {
        Start-Process $reportPath
    }
}

Pause-Demo "Show the reliability score/grade and the generated HTML report."

Write-Stage "DEMO COMPLETE" "You just tested healthy delivery, duplicates, bad signatures, out-of-order events, retries/fault recovery, idempotency, dashboard visibility, and a reliability report."
Write-Host "Dashboard: $dashboardUrl"
Write-Host "Report:    $reportPath"
Write-Host ""
Write-Host "Launch line: PayLab breaks payment integrations safely in CI before customers discover the bugs in production."
