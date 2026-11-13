$ErrorActionPreference = 'Stop'
$capture = Join-Path (Get-Location) '.build/web-v2-20261113'
$precondition = Get-Content -Raw (Join-Path $capture 'edge-cold-precondition.log')
if ($precondition -notmatch '"ok":true' -or $precondition -match '### Error') { throw 'Cold restart precondition failed' }
$owned = @(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'msedge.exe' -and $_.CommandLine -like '*web-v2-edge-cold-profile*' })
if ($owned.Count -lt 1) { throw 'No owned Edge processes before close' }
$oldIds = @($owned.ProcessId)
playwright-cli.cmd -s=bh07-v2-edge-cold close *> (Join-Path $capture 'edge-cold-close.log')
if ($LASTEXITCODE -ne 0) { throw 'Cold close command failed' }
for ($attempt = 0; $attempt -lt 30; $attempt++) {
    $remaining = @(Get-Process -Id $oldIds -ErrorAction SilentlyContinue)
    if ($remaining.Count -eq 0) { break }
    Start-Sleep -Milliseconds 200
}
if ($remaining.Count -ne 0) { throw 'Old owned Edge process still exists' }
playwright-cli.cmd -s=bh07-v2-edge-cold open http://127.0.0.1:8088 --browser=msedge --profile=.build/web-v2-edge-cold-profile *> (Join-Path $capture 'edge-cold-open.log')
if ($LASTEXITCODE -ne 0) { throw 'Cold open command failed' }
$newOwned = @(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'msedge.exe' -and $_.CommandLine -like '*web-v2-edge-cold-profile*' })
if ($newOwned.Count -lt 1) { throw 'No owned Edge process after reopen' }
if (@($newOwned | Where-Object { $_.ProcessId -in $oldIds }).Count -ne 0) { throw 'Old process reused' }
playwright-cli.cmd -s=bh07-v2-edge-cold run-code --filename=scripts/bh07_browser/web_reopen_scenario.js *> (Join-Path $capture 'edge-cold-restored-reopen.log')
if ($LASTEXITCODE -ne 0) { throw 'Cold restored scenario command failed' }
$resultText = Get-Content -Raw (Join-Path $capture 'edge-cold-restored-reopen.log')
if ($resultText -notmatch '"ok":true' -or $resultText -match '### Error') { throw 'Cold restored scenario assertions failed' }
@{
    status = 'PASS'
    browser = 'Edge'
    profile = 'dedicated local test profile'
    old_process_count = $oldIds.Count
    old_processes_absent_before_reopen = $true
    new_process_count = $newOwned.Count
    new_processes_disjoint = $true
    restored_member_and_fee_then_logout_guest = $true
    tab_scenario = 'edge-cold-restored-reopen.json'
} | ConvertTo-Json | Set-Content -Encoding utf8 (Join-Path $capture 'edge-cold-restart.json')
Write-Output 'Cold Edge restart PASS; old owned processes absent and restored Member verified through UI'
