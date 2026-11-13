$ErrorActionPreference='Stop'
$cases=@(
 @{Name='bh07-copy-edge-cohost';Browser='msedge';Label='edge-cohost-copy';Driver='scripts/bh07_browser/web_copy_qr_scenario.js'},
 @{Name='bh07-copy-edge-qr';Browser='msedge';Label='edge-guest-qr';Driver='.build/web-lifecycle-20261113/guest-qr-driver.js'},
 @{Name='bh07-copy-firefox-cohost';Browser='firefox';Label='firefox-cohost-copy';Driver='scripts/bh07_browser/web_copy_qr_scenario.js'},
 @{Name='bh07-copy-firefox-qr';Browser='firefox';Label='firefox-guest-qr';Driver='.build/web-lifecycle-20261113/guest-qr-driver.js'}
)
foreach($case in $cases){
 $sessionArg='-s='+$case.Name
 $capture=Join-Path '.build/web-lifecycle-20261113' ($case.Label+'.log')
 playwright-cli.cmd $sessionArg close *> $null
 try {
  playwright-cli.cmd $sessionArg open http://127.0.0.1:8088 ('--browser='+$case.Browser) *> $null
  if($LASTEXITCODE -ne 0){throw 'Browser open failed'}
  playwright-cli.cmd $sessionArg run-code ('--filename='+$case.Driver) *> $capture
  if($LASTEXITCODE -ne 0){throw ('Scenario command failed: '+$case.Label)}
  $data=@(Get-Content $capture | Where-Object {$_ -match '^\{"ok":true,'})
  if($data.Count -ne 1){throw ('No unique successful result: '+$case.Label)}
  $result=$data[0]|ConvertFrom-Json
  if($result.recorded_console_summary.pageerror_count -ne 0){throw 'Unexpected page error'}
  if($case.Browser -eq 'msedge' -and $result.clipboard.status -ne 'PASS'){throw 'Edge clipboard must be measured'}
  if($result.mode -eq 'guest_qr' -and (-not $result.qr.fallback_verified -or -not $result.qr.expected_info_matched -or -not $result.qr.payment_not_submitted)){throw 'QR gates incomplete'}
  $result|ConvertTo-Json -Depth 8|Set-Content -Encoding UTF8 (Join-Path '.build/web-lifecycle-20261113' ($case.Label+'.json'))
  Write-Output ($case.Label+' PASS; clipboard='+$result.clipboard.status)
 }finally{
  playwright-cli.cmd $sessionArg close *> $null
  if($LASTEXITCODE -ne 0){throw ('Browser cleanup failed: '+$case.Label)}
 }
}
