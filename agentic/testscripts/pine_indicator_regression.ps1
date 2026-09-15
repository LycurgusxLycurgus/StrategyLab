param(
    [ValidateRange(500, 5000)]
    [int]$Bars = 5000
)

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$python = Join-Path $repoRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    throw "StrategyLab virtualenv Python was not found at $python"
}

Set-Location -LiteralPath $repoRoot

& $python -m unittest `
    app.tests.MutationLabTests.test_pine_review_protects_source_and_selects_event_fixtures `
    app.tests.MutationLabTests.test_pine_workbench_prepares_fidelity_first_review_package `
    app.tests.MutationLabTests.test_rejected_tradingview_verdict_is_explicit `
    app.tests.MutationLabTests.test_pine_workbench_proof_and_tradingview_observation_are_linked `
    app.tests.MutationLabTests.test_pine_workbench_proof_includes_declared_state_history
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

$env:PYTHONPATH = Join-Path $repoRoot 'services\pine2python\src'
& $python -m unittest discover -s services\pine2python\tests -p 'test_*.py'
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

& $python agentic\testscripts\pine2python_vertical.py
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

& $python agentic\testscripts\smart_money_indicator_first.py `
    --bars $Bars `
    --register
exit $LASTEXITCODE
