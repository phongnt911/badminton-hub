# BH-07 HTTP/Auth verification runner (local isolated Supabase only).
#
# It deliberately refuses non-local API URLs. It resets only the local Supabase
# database, creates Auth users through GoTrue Admin API, loads the deterministic
# fixture, then runs the real-repository/real-HTTP test. It never applies a
# remote project, deploys or uses production/staging data.

[CmdletBinding()]
param(
    [string]$EvidenceDir = '',
    [string]$BaseSha = '4da6339a1a92bcf27675f50ca4b785fbb45f1e78'
)

# Native tools such as `supabase status` write warnings to stderr. Keep those as
# log lines and use explicit exit-code checks instead of treating them as
# terminating PowerShell errors.
$ErrorActionPreference = 'Continue'
if (Get-Variable PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue) {
    $PSNativeCommandUseErrorActionPreference = $false
}
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Set-Location $projectRoot

$testedSha = (& git rev-parse HEAD).Trim()
$dirtyBefore = ((& git status --porcelain) -join "`n").Trim()

if ([string]::IsNullOrWhiteSpace($EvidenceDir)) {
    $EvidenceDir = Join-Path $projectRoot 'docs\reviews\bh07\http_concurrency_evidence'
}
$EvidenceDir = [System.IO.Path]::GetFullPath($EvidenceDir)
New-Item -ItemType Directory -Force -Path $EvidenceDir | Out-Null

$timestamp = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
$resetLog = Join-Path $EvidenceDir 'reset.log'
$authLog = Join-Path $EvidenceDir 'auth_users.log'
$seedLog = Join-Path $EvidenceDir 'seed.log'
$testLog = Join-Path $EvidenceDir 'flutter_test.log'
$commandsPath = Join-Path $EvidenceDir 'commands.md'
$envPath = Join-Path $EvidenceDir 'environment.json'
$exitsPath = Join-Path $EvidenceDir 'exits.json'
$hashPath = Join-Path $EvidenceDir 'hashes.sha256'

$projectId = (Select-String -Path (Join-Path $projectRoot 'supabase\config.toml') -Pattern '^project_id\s*=\s*"([^"]+)"' | Select-Object -First 1).Matches.Groups[1].Value
if ([string]::IsNullOrWhiteSpace($projectId)) {
    throw 'Could not read project_id from supabase/config.toml'
}
$dbContainer = "supabase_db_$projectId"

$commands = [System.Collections.Generic.List[string]]::new()
$commands.Add('# BH-07 HTTP/Auth verification commands')
$commands.Add('')
$commands.Add("Generated (UTC): $((Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ'))")
$commands.Add("Base SHA: ``$BaseSha``")
$commands.Add("Tested checkout SHA: ``$testedSha``")
$commands.Add('')
$commands.Add('```powershell')
$commands.Add('npx --yes supabase@2.121.0 start')
$commands.Add('npx --yes supabase@2.121.0 db reset --local --no-seed --yes')
$commands.Add('# POST /auth/v1/admin/users for each fixture email through GoTrue Admin API')
$commands.Add('# (service role key read from local `supabase status`; never sent to a remote URL)')
$commands.Add("Get-Content scripts/bh07_http/seed.sql -Raw | docker exec -i $dbContainer psql -U postgres -d postgres -v ON_ERROR_STOP=1")
$commands.Add('$env:BH07_HTTP_TEST = ''1''')
$commands.Add('$env:BH07_HTTP_URL = <local API_URL from `supabase status`>')
$commands.Add('$env:BH07_HTTP_ANON_KEY = <local ANON_KEY>')
$commands.Add('$env:BH07_HTTP_SERVICE_ROLE_KEY = <local SERVICE_ROLE_KEY>')
$commands.Add('flutter test test/integration/bh07_http_auth_test.dart --reporter expanded')
$commands.Add('flutter analyze')
$commands.Add('flutter test')
$commands.Add('```')
$commands.Add('')
$commands.Add('Local-only guard: the runner aborts unless API_URL host is 127.0.0.1, localhost or ::1.')

function Protect-EvidenceText {
    param([string]$Text)
    $safe = $Text
    $safe = $safe -replace 'eyJ[A-Za-z0-9_\-\.]{20,}', '<redacted-jwt>'
    $safe = $safe -replace 'sb_(publishable|secret)_[A-Za-z0-9_\-]+', '<redacted-key>'
    $safe = $safe -replace '(?i)("JWT_SECRET"\s*:\s*")[^"]+', '$1<redacted>'
    $safe = $safe -replace '(?i)("S3_PROTOCOL_ACCESS_KEY_SECRET"\s*:\s*")[^"]+', '$1<redacted>'
    $safe = $safe -replace '(?i)("S3_PROTOCOL_ACCESS_KEY_ID"\s*:\s*")[^"]+', '$1<redacted>'
    $safe = $safe -replace '(?i)("DB_URL"\s*:\s*")[^"]+', '$1<redacted>'
    return $safe
}

function Invoke-CommandCaptured {
    param([string]$CommandText)
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $env:ComSpec
    $psi.Arguments = "/d /s /c `"$CommandText`""
    $psi.WorkingDirectory = $projectRoot
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.CreateNoWindow = $true
    $process = [System.Diagnostics.Process]::Start($psi)
    $stdoutTask = $process.StandardOutput.ReadToEndAsync()
    $stderrTask = $process.StandardError.ReadToEndAsync()
    $process.WaitForExit()
    $stdout = $stdoutTask.Result
    $stderr = $stderrTask.Result
    return [pscustomobject]@{
        ExitCode = $process.ExitCode
        StdOut = $stdout
        StdErr = $stderr
        Output = (($stdout + $stderr).TrimEnd())
    }
}

function Invoke-Logged {
    param(
        [string]$CommandText,
        [string]$LogPath
    )
    $result = Invoke-CommandCaptured -CommandText $CommandText
    $safe = Protect-EvidenceText -Text $result.Output
    $safe | Set-Content -Path $LogPath -Encoding utf8
    Write-Host $safe
    return $result.ExitCode
}

# Start is idempotent. If the local stack cannot start, stop before touching data.
$startExit = Invoke-Logged -CommandText 'npx --yes supabase@2.121.0 start' -LogPath (Join-Path $EvidenceDir 'start.log')
if ($startExit -ne 0) {
    throw "Local Supabase start failed with exit $startExit"
}

$statusResult = Invoke-CommandCaptured -CommandText 'npx --yes supabase@2.121.0 status -o json'
$statusExit = $statusResult.ExitCode
if ($statusExit -ne 0) {
    throw "Local Supabase status failed with exit $statusExit"
}
$statusText = $statusResult.StdOut
$jsonStart = $statusText.IndexOf('{')
$jsonEnd = $statusText.LastIndexOf('}')
if ($jsonStart -lt 0 -or $jsonEnd -le $jsonStart) {
    throw 'Local Supabase status did not emit JSON'
}
$statusJson = $statusText.Substring($jsonStart, $jsonEnd - $jsonStart + 1)
$status = $statusJson | ConvertFrom-Json
$apiUrl = [string]$status.API_URL
$anonKey = [string]$status.ANON_KEY
$serviceRoleKey = [string]$status.SERVICE_ROLE_KEY
$uri = [Uri]$apiUrl
if (-not (@('127.0.0.1', 'localhost', '::1') -contains $uri.Host)) {
    throw "Refusing non-local Supabase API_URL: $apiUrl"
}
if ([string]::IsNullOrWhiteSpace($anonKey) -or [string]::IsNullOrWhiteSpace($serviceRoleKey)) {
    throw 'Local Supabase status did not return anon/service role keys'
}

$resetExit = Invoke-Logged -CommandText 'npx --yes supabase@2.121.0 db reset --local --no-seed --yes' -LogPath $resetLog
if ($resetExit -ne 0) {
    throw "Local database reset failed with exit $resetExit"
}

$users = @(
    @{ email = 'ownera@example.test'; name = 'Owner A' },
    @{ email = 'financea@example.test'; name = 'Finance A' },
    @{ email = 'cohosta@example.test'; name = 'Cohost A' },
    @{ email = 'membera@example.test'; name = 'Member A' },
    @{ email = 'guesta@example.test'; name = 'Guest A' },
    @{ email = 'ownerb@example.test'; name = 'Owner B' },
    @{ email = 'outsider@example.test'; name = 'Outsider' }
)
$adminHeaders = @{
    apikey = $serviceRoleKey
    Authorization = "Bearer $serviceRoleKey"
    'Content-Type' = 'application/json'
}
$authLines = [System.Collections.Generic.List[string]]::new()
foreach ($user in $users) {
    $body = @{
        email = $user.email
        password = 'bh07-http-pass-123456'
        email_confirm = $true
        user_metadata = @{ display_name = $user.name }
    } | ConvertTo-Json -Depth 4
    try {
        $created = Invoke-RestMethod -Method Post -Uri "$apiUrl/auth/v1/admin/users" -Headers $adminHeaders -Body $body
        $authLines.Add("created $($created.email) id=$($created.id)")
    }
    catch {
        $detail = $_.ErrorDetails.Message
        $authLines.Add("FAILED $($user.email): $detail")
        $authLines | Set-Content -Path $authLog -Encoding utf8
        throw "GoTrue Admin API failed for $($user.email): $detail"
    }
}
$authLines.Add('GoTrue Admin API creates users; passwords are not written to evidence.')
$authLines | Set-Content -Path $authLog -Encoding utf8

$seedText = Get-Content -LiteralPath (Join-Path $projectRoot 'scripts\bh07_http\seed.sql') -Raw -Encoding utf8
$seedOutput = $seedText | docker exec -i $dbContainer psql -U postgres -d postgres -v ON_ERROR_STOP=1 2>&1
$seedExit = $LASTEXITCODE
$seedOutput | Tee-Object -FilePath $seedLog | Out-Host
if ($seedExit -ne 0) {
    throw "Fixture seed failed with exit $seedExit"
}

$env:BH07_HTTP_TEST = '1'
$env:BH07_HTTP_URL = $apiUrl
$env:BH07_HTTP_ANON_KEY = $anonKey
$env:BH07_HTTP_SERVICE_ROLE_KEY = $serviceRoleKey
$env:BH07_HTTP_EVIDENCE_DIR = $EvidenceDir
$env:BH07_HTTP_BASE_SHA = $BaseSha
$env:BH07_HTTP_TESTED_SHA = $testedSha
$env:TZ = 'UTC'

$testExit = Invoke-Logged -CommandText 'flutter test test\integration\bh07_http_auth_test.dart --reporter expanded' -LogPath $testLog

$summaryPath = Join-Path $EvidenceDir 'summary.json'
$summaryCounts = $null
if (Test-Path $summaryPath) {
    $summary = Get-Content -LiteralPath $summaryPath -Raw -Encoding utf8 | ConvertFrom-Json
    $summaryCounts = $summary.counts
}

$serviceImages = @(
    & docker ps --format '{{.Names}}|{{.Image}}' |
        Where-Object { $_ -match "^supabase_.*_$([regex]::Escape($projectId))\|" } |
        Sort-Object
)

$environment = [ordered]@{
    generated_at_utc = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    project_id = $projectId
    api_url = $apiUrl
    local_only_guard = $true
    db_container = $dbContainer
    docker = (& docker --version)
    supabase_services = $serviceImages
    flutter = (& flutter --version 2>&1 | Select-Object -First 3)
    base_sha = $BaseSha
    tested_checkout_sha = $testedSha
    worktree_dirty_before_run = -not [string]::IsNullOrWhiteSpace($dirtyBefore)
    worktree_status_before_run = $dirtyBefore
    environment_variables = @(
        'BH07_HTTP_TEST=1',
        'BH07_HTTP_URL=<local>',
        'BH07_HTTP_ANON_KEY=<redacted>',
        'BH07_HTTP_SERVICE_ROLE_KEY=<redacted>',
        'TZ=UTC'
    )
}
$environment | ConvertTo-Json -Depth 5 | Set-Content -Path $envPath -Encoding utf8

$exits = [ordered]@{
    start = $startExit
    status = $statusExit
    db_reset = $resetExit
    auth_users = 0
    seed = $seedExit
    flutter_http_test = $testExit
    summary_total = if ($null -ne $summaryCounts) { $summaryCounts.total } else { $null }
    summary_passed = if ($null -ne $summaryCounts) { $summaryCounts.passed } else { $null }
    summary_failed = if ($null -ne $summaryCounts) { $summaryCounts.failed } else { $null }
}
$exits | ConvertTo-Json | Set-Content -Path $exitsPath -Encoding utf8

$commands | Set-Content -Path $commandsPath -Encoding utf8

$evidenceRel = $EvidenceDir.Substring($projectRoot.Length).TrimStart('\', '/')
$hashTargets = [System.Collections.Generic.List[string]]::new()
$hashTargets.Add('scripts\bh07_http\run.ps1')
$hashTargets.Add('scripts\bh07_http\seed.sql')
$hashTargets.Add('test\integration\bh07_http_auth_test.dart')
$hashTargets.Add((Join-Path $evidenceRel 'start.log'))
$hashTargets.Add((Join-Path $evidenceRel 'reset.log'))
$hashTargets.Add((Join-Path $evidenceRel 'auth_users.log'))
$hashTargets.Add((Join-Path $evidenceRel 'seed.log'))
$hashTargets.Add((Join-Path $evidenceRel 'flutter_test.log'))
$hashTargets.Add((Join-Path $evidenceRel 'summary.json'))
$hashTargets.Add((Join-Path $evidenceRel 'environment.json'))
$hashTargets.Add((Join-Path $evidenceRel 'exits.json'))
$hashTargets.Add((Join-Path $evidenceRel 'commands.md'))
if (Test-Path (Join-Path $projectRoot (Join-Path $evidenceRel 'red_run_summary.json'))) {
    $hashTargets.Add((Join-Path $evidenceRel 'red_run_summary.json'))
}
if (Test-Path (Join-Path $projectRoot (Join-Path $evidenceRel 'red_run_flutter_test.log'))) {
    $hashTargets.Add((Join-Path $evidenceRel 'red_run_flutter_test.log'))
}

$hashLines = foreach ($relative in $hashTargets) {
    $full = Join-Path $projectRoot $relative
    if (Test-Path $full) {
        $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $full).Hash.ToLowerInvariant()
        "$hash  $relative"
    }
}
$hashText = ($hashLines -join "`n") + "`n"
[System.IO.File]::WriteAllText($hashPath, $hashText, [System.Text.Encoding]::UTF8)

if ($testExit -ne 0) {
    Write-Error "BH-07 HTTP/Auth test failed with exit $testExit; see $testLog"
    exit $testExit
}
if ($null -eq $summaryCounts -or [int]$summaryCounts.failed -ne 0) {
    Write-Error 'BH-07 HTTP/Auth test did not produce a green summary.json'
    exit 1
}

Write-Host ''
Write-Host "BH-07 HTTP/Auth verification PASS: $($summaryCounts.passed)/$($summaryCounts.total) checks"
Write-Host "Evidence: $EvidenceDir"
exit 0
