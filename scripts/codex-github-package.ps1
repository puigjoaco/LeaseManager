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
    $output = & $file @arguments 2>$null
    if ((-not $AllowFailure) -and $LASTEXITCODE -ne 0) {
        throw "$file fallo con codigo $LASTEXITCODE."
    }
    return ($output | Out-String).Trim()
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
    return ($json | ConvertFrom-Json)
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

Ensure-GhToken

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

Assert-Condition ($null -ne $pr) 'No se pudo crear o resolver el PR.'
Write-Host "PR #$($pr.number): $($pr.url)"

if ($WatchChecks -or $Merge) {
    Step 'Watch checks'
    Invoke-External 'gh' @('pr', 'checks', "$($pr.number)", '--watch', '--fail-fast', '--interval', '10')
}

if ($Merge) {
    Step 'Merge PR'
    $headSha = Get-ExternalOutput 'git' @('rev-parse', 'HEAD')
    $mergeArgs = @('pr', 'merge', "$($pr.number)", '--match-head-commit', $headSha)
    if ($MergeStrategy -eq 'squash') {
        $mergeArgs += '--squash'
    }
    elseif ($MergeStrategy -eq 'rebase') {
        $mergeArgs += '--rebase'
    }
    else {
        $mergeArgs += '--merge'
    }
    if ($DeleteRemoteBranch) {
        $mergeArgs += '--delete-branch'
    }
    Invoke-External 'gh' $mergeArgs
}

Step 'Done'
if ($Merge) {
    Write-Host "Paquete integrado. Actualiza $Base en el worktree principal y elimina el worktree tactico si corresponde." -ForegroundColor Green
}
else {
    Write-Host "Paquete publicado. PR: $($pr.url)" -ForegroundColor Green
}
