param(
    [string]$Base = 'main',
    [string]$Remote = 'origin',
    [string]$Branch = '',
    [string[]]$Path = @(),
    [switch]$StageAll,
    [string]$CommitMessage = '',
    [string]$PrTitle = '',
    [string]$PrBody = '',
    [string]$PrBodyFile = '',
    [switch]$Draft,
    [switch]$WatchChecks,
    [switch]$Merge,
    [ValidateSet('merge', 'squash', 'rebase')]
    [string]$MergeStrategy = 'merge',
    [switch]$DeleteRemoteBranch,
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Step([string]$message) {
    Write-Host ''
    Write-Host "==> $message" -ForegroundColor Cyan
}

function Assert-Condition($condition, [string]$message) {
    if (-not $condition) {
        throw $message
    }
}

function Invoke-External([string]$file, [string[]]$arguments) {
    Write-Host "+ $file $($arguments -join ' ')"
    if ($DryRun) {
        return
    }
    & $file @arguments
    Assert-Condition ($LASTEXITCODE -eq 0) "$file fallo con codigo $LASTEXITCODE."
}

function Get-ExternalOutput([string]$file, [string[]]$arguments, [switch]$AllowFailure) {
    $previousErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        $output = & $file @arguments 2>$null
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }

    if ((-not $AllowFailure) -and $exitCode -ne 0) {
        throw "$file fallo con codigo $exitCode."
    }
    return ($output | Out-String).Trim()
}

function Test-CommandAvailable([string]$file) {
    return $null -ne (Get-Command $file -ErrorAction SilentlyContinue)
}

function Get-GithubRepoSlugFromRemote() {
    $remoteUrl = Get-ExternalOutput 'git' @('remote', 'get-url', $Remote)
    if ($remoteUrl -match '^https://github\.com/([^/]+/[^/.]+)(?:\.git)?$') {
        return $Matches[1]
    }
    if ($remoteUrl -match '^git@github\.com:([^/]+/[^/.]+)(?:\.git)?$') {
        return $Matches[1]
    }
    throw "No se pudo resolver owner/repo desde remoto $Remote."
}

function Ensure-GithubApiToken() {
    if ($env:GH_TOKEN) {
        return $env:GH_TOKEN
    }
    if ($env:GITHUB_TOKEN) {
        return $env:GITHUB_TOKEN
    }

    $credentialInput = "protocol=https`nhost=github.com`n`n"
    $credential = $credentialInput | git credential fill
    Assert-Condition ($LASTEXITCODE -eq 0) 'No se pudo consultar git credential manager para GitHub.'

    $passwordLine = $credential | Where-Object { $_ -like 'password=*' } | Select-Object -First 1
    Assert-Condition (-not [string]::IsNullOrWhiteSpace($passwordLine)) 'GitHub CLI no esta disponible y git credential manager no entrego token.'

    return $passwordLine.Substring('password='.Length)
}

function Invoke-GithubApi([string]$method, [string]$path, $body = $null) {
    $token = Ensure-GithubApiToken
    $headers = @{
        Authorization = "Bearer $token"
        Accept = 'application/vnd.github+json'
        'X-GitHub-Api-Version' = '2022-11-28'
        'User-Agent' = 'codex-github-package'
    }
    $uri = "https://api.github.com/$path"
    if ($null -eq $body) {
        return Invoke-RestMethod -Method $method -Uri $uri -Headers $headers
    }

    $json = $body | ConvertTo-Json -Depth 10
    return Invoke-RestMethod -Method $method -Uri $uri -Headers $headers -Body $json -ContentType 'application/json'
}

function Test-GitClean() {
    $status = Get-ExternalOutput 'git' @('status', '--porcelain')
    return [string]::IsNullOrWhiteSpace($status)
}

function Get-CurrentBranch() {
    return Get-ExternalOutput 'git' @('branch', '--show-current')
}

function Ensure-GhToken() {
    if ($env:GH_TOKEN -or $env:GITHUB_TOKEN -or $DryRun) {
        return
    }

    $authStatus = Get-ExternalOutput 'gh' @('auth', 'status') -AllowFailure
    if ($LASTEXITCODE -eq 0) {
        return
    }

    $credentialInput = "protocol=https`nhost=github.com`n`n"
    $credential = $credentialInput | git credential fill
    Assert-Condition ($LASTEXITCODE -eq 0) 'No se pudo consultar git credential manager para GitHub.'

    $passwordLine = $credential | Where-Object { $_ -like 'password=*' } | Select-Object -First 1
    Assert-Condition (-not [string]::IsNullOrWhiteSpace($passwordLine)) 'gh no esta autenticado y git credential manager no entrego token.'

    $env:GH_TOKEN = $passwordLine.Substring('password='.Length)
}

function Get-Pr() {
    $json = Get-ExternalOutput 'gh' @('pr', 'view', $Branch, '--json', 'number,url,state') -AllowFailure
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($json)) {
        return $null
    }
    $pr = $json | ConvertFrom-Json
    if ($pr.state -ne 'OPEN') {
        return $null
    }
    return $pr
}

function Resolve-PrBody() {
    if (-not [string]::IsNullOrWhiteSpace($PrBodyFile)) {
        Assert-Condition (Test-Path -LiteralPath $PrBodyFile) "No existe PrBodyFile: $PrBodyFile"
        return Get-Content -LiteralPath $PrBodyFile -Raw
    }

    if (-not [string]::IsNullOrWhiteSpace($PrBody)) {
        return $PrBody
    }

    return @"
Paquete cerrado por flujo Codex automatizado con Git/GitHub CLI.

Validacion:
- revisar commits, checks de GitHub Actions y evidencia aplicable del paquete.
"@
}

function Wait-PrChecks([int]$prNumber) {
    $deadline = (Get-Date).AddMinutes(30)
    $checksJson = ''

    while ((Get-Date) -lt $deadline) {
        $checksJson = Get-ExternalOutput 'gh' @(
            'pr', 'checks', "$prNumber",
            '--json', 'bucket,name,state,workflow'
        ) -AllowFailure
        if ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace($checksJson)) {
            $checks = $checksJson | ConvertFrom-Json
            if (@($checks).Count -gt 0) {
                Invoke-External 'gh' @(
                    'pr', 'checks', "$prNumber",
                    '--watch', '--fail-fast', '--interval', '10'
                )
                return
            }
        }

        Write-Host 'Checks aun no reportados; esperando 10s...'
        Start-Sleep -Seconds 10
    }

    throw "No aparecieron checks para PR #$prNumber despues de 30 minutos."
}

function Get-GithubRepoSlug() {
    if (-not (Test-CommandAvailable 'gh')) {
        return Get-GithubRepoSlugFromRemote
    }
    $repo = Get-ExternalOutput 'gh' @('repo', 'view', '--json', 'nameWithOwner', '--jq', '.nameWithOwner')
    Assert-Condition (-not [string]::IsNullOrWhiteSpace($repo)) 'No se pudo resolver owner/repo con gh.'
    return $repo
}

function Get-PrApi() {
    $repo = Get-GithubRepoSlugFromRemote
    $owner = $repo.Split('/')[0]
    $head = [uri]::EscapeDataString("$owner`:$Branch")
    $baseQuery = [uri]::EscapeDataString($Base)
    $pulls = Invoke-GithubApi 'GET' "repos/$repo/pulls?state=open&head=$head&base=$baseQuery&per_page=1"
    if (@($pulls).Count -eq 0) {
        return $null
    }

    $pull = @($pulls)[0]
    return [pscustomobject]@{
        number = [int]$pull.number
        url = [string]$pull.html_url
        state = [string]$pull.state.ToUpperInvariant()
        headSha = [string]$pull.head.sha
    }
}

function New-PrApi() {
    if ([string]::IsNullOrWhiteSpace($PrTitle)) {
        $script:PrTitle = Get-ExternalOutput 'git' @('log', '-1', '--pretty=%s')
    }

    $repo = Get-GithubRepoSlugFromRemote
    $body = @{
        title = $PrTitle
        head = $Branch
        base = $Base
        body = Resolve-PrBody
        draft = [bool]$Draft
    }
    $pull = Invoke-GithubApi 'POST' "repos/$repo/pulls" $body
    return [pscustomobject]@{
        number = [int]$pull.number
        url = [string]$pull.html_url
        state = [string]$pull.state.ToUpperInvariant()
        headSha = [string]$pull.head.sha
    }
}

function Wait-PrChecksApi($pr) {
    $deadline = (Get-Date).AddMinutes(30)
    $repo = Get-GithubRepoSlugFromRemote
    $headSha = $pr.headSha

    while ((Get-Date) -lt $deadline) {
        $runs = Invoke-GithubApi 'GET' "repos/$repo/commits/$headSha/check-runs?per_page=100"
        $checkRuns = @($runs.check_runs)
        if ($checkRuns.Count -gt 0) {
            $failed = @($checkRuns | Where-Object {
                $_.status -eq 'completed' -and
                $_.conclusion -notin @('success', 'neutral', 'skipped')
            })
            if ($failed.Count -gt 0) {
                $names = ($failed | ForEach-Object { "$($_.name):$($_.conclusion)" }) -join ', '
                throw "Checks fallidos para PR #$($pr.number): $names"
            }

            $pending = @($checkRuns | Where-Object { $_.status -ne 'completed' })
            if ($pending.Count -eq 0) {
                Write-Host "Checks completados para PR #$($pr.number)."
                return
            }
        }

        Write-Host 'Checks aun no reportados o pendientes; esperando 10s...'
        Start-Sleep -Seconds 10
    }

    throw "No se completaron checks para PR #$($pr.number) despues de 30 minutos."
}

function Invoke-PrMergeApi([int]$prNumber, [string]$headSha) {
    $repo = Get-GithubRepoSlug
    if (-not (Test-CommandAvailable 'gh')) {
        Invoke-GithubApi 'PUT' "repos/$repo/pulls/$prNumber/merge" @{
            merge_method = $MergeStrategy
            sha = $headSha
        } | Out-Null
        return
    }
    Invoke-External 'gh' @(
        'api',
        '--method', 'PUT',
        "repos/$repo/pulls/$prNumber/merge",
        '-f', "merge_method=$MergeStrategy",
        '-f', "sha=$headSha"
    )
}

$repoRoot = (Get-ExternalOutput 'git' @('rev-parse', '--show-toplevel')).Replace('\', '/')
Set-Location $repoRoot

if ([string]::IsNullOrWhiteSpace($Branch)) {
    $Branch = Get-CurrentBranch
}

Assert-Condition (-not [string]::IsNullOrWhiteSpace($Branch)) 'No se pudo resolver la rama actual.'
Assert-Condition ($Branch -ne $Base) "No se puede cerrar un paquete desde $Base; usa una rama codex/..."
Assert-Condition ($Branch -like 'codex/*') "La rama debe usar prefijo codex/...; rama actual: $Branch"

Step 'Preflight git'
Invoke-External 'git' @('fetch', '--prune', $Remote, $Base)
$baseRef = "$Remote/$Base"
$isFromBase = $true
& git merge-base --is-ancestor $baseRef HEAD
if ($LASTEXITCODE -ne 0) {
    $isFromBase = $false
}
Assert-Condition $isFromBase "La rama $Branch no contiene $baseRef; sincroniza/rebasa antes de cerrar paquete."

$dirty = -not (Test-GitClean)
if ($dirty) {
    Assert-Condition (-not [string]::IsNullOrWhiteSpace($CommitMessage)) 'Hay cambios locales; CommitMessage es obligatorio.'
    Assert-Condition ($StageAll -or $Path.Count -gt 0) 'Hay cambios locales; usa -StageAll o -Path para stage explicito.'

    Step 'Stage'
    if ($StageAll) {
        Invoke-External 'git' @('add', '-A')
    }
    else {
        Invoke-External 'git' (@('add', '--') + $Path)
    }

    if ($DryRun) {
        Write-Host 'DryRun: stage y commit no se ejecutan.'
    }
    else {
        & git diff --cached --quiet
        Assert-Condition ($LASTEXITCODE -ne 0) 'No hay cambios staged para commitear.'

        Step 'Commit'
        Invoke-External 'git' @('commit', '-m', $CommitMessage)
    }
}

Step 'Push'
Invoke-External 'git' @('push', '-u', $Remote, $Branch)

if ($DryRun) {
    Step 'Done'
    Write-Host 'DryRun completo: no se ejecuto push real, PR, checks ni merge.' -ForegroundColor Green
    exit 0
}

$useGithubCli = Test-CommandAvailable 'gh'
if ($useGithubCli) {
    Ensure-GhToken
}

if ($useGithubCli) {
    $pr = Get-Pr
    if ($null -eq $pr) {
        Step 'Create PR'
        if ([string]::IsNullOrWhiteSpace($PrTitle)) {
            $PrTitle = Get-ExternalOutput 'git' @('log', '-1', '--pretty=%s')
        }

        $body = Resolve-PrBody
        $args = @(
            'pr', 'create',
            '--base', $Base,
            '--head', $Branch,
            '--title', $PrTitle,
            '--body', $body
        )
        if ($Draft) {
            $args += '--draft'
        }

        $createdUrl = Get-ExternalOutput 'gh' $args
        if (-not [string]::IsNullOrWhiteSpace($createdUrl)) {
            Write-Host $createdUrl
        }
        $pr = Get-Pr
    }
    else {
        Step "Use existing PR #$($pr.number)"
    }
}
else {
    Write-Host 'GitHub CLI no esta disponible; usando GitHub REST API con token de entorno o Git Credential Manager.'
    $pr = Get-PrApi
    if ($null -eq $pr) {
        Step 'Create PR'
        $pr = New-PrApi
    }
    else {
        Step "Use existing PR #$($pr.number)"
    }
}

Assert-Condition ($null -ne $pr) 'No se pudo crear o resolver el PR.'
Write-Host "PR #$($pr.number): $($pr.url)"

if ($WatchChecks -or $Merge) {
    Step 'Watch checks'
    if ($useGithubCli) {
        Wait-PrChecks $pr.number
    }
    else {
        Wait-PrChecksApi $pr
    }
}

if ($Merge) {
    Step 'Merge PR'
    $headSha = Get-ExternalOutput 'git' @('rev-parse', 'HEAD')
    Invoke-PrMergeApi $pr.number $headSha
    if ($DeleteRemoteBranch) {
        Invoke-External 'git' @('push', $Remote, '--delete', $Branch)
    }
}

Step 'Done'
if ($Merge) {
    Write-Host "Paquete integrado. Actualiza $Base en el worktree principal y elimina el worktree tactico si corresponde." -ForegroundColor Green
}
else {
    Write-Host "Paquete publicado. PR: $($pr.url)" -ForegroundColor Green
}
