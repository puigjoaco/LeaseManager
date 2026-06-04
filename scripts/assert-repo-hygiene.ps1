param(
    [switch]$IncludeUntracked
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Assert-Condition($condition, [string]$message) {
    if (-not $condition) {
        throw $message
    }
}

function Get-GitOutput([string[]]$arguments) {
    $output = & git @arguments
    Assert-Condition ($LASTEXITCODE -eq 0) "git $($arguments -join ' ') fallo."
    return @($output)
}

function Normalize-GitPath([string]$path) {
    return $path.Replace('\', '/').Trim()
}

function Test-AllowlistedPath([string]$path) {
    $allowlistedPaths = @(
        'backend/.env.example',
        'frontend/.env.example',
        'migration/bundles/.gitkeep',
        'migration/bundles/README.md'
    )

    return $allowlistedPaths -contains $path
}

$repoRoot = (Get-GitOutput @('rev-parse', '--show-toplevel') | Select-Object -First 1)
Assert-Condition (-not [string]::IsNullOrWhiteSpace($repoRoot)) 'No se pudo resolver el root Git.'
Set-Location $repoRoot

$blockedRules = @(
    @{
        code = 'repo_hygiene.env_file_versioned'
        pattern = '(^|/)\.env($|\.)'
        message = 'No versionar .env reales ni variantes locales.'
    },
    @{
        code = 'repo_hygiene.database_artifact_versioned'
        pattern = '\.(sqlite3|sqlite|db)$'
        message = 'No versionar bases SQLite/DB locales o historicas.'
    },
    @{
        code = 'repo_hygiene.local_evidence_versioned'
        pattern = '^local-evidence/'
        message = 'No versionar evidencia local; debe quedar ignorada por Git.'
    },
    @{
        code = 'repo_hygiene.generated_migration_bundle_versioned'
        pattern = '^migration/bundles/(?!README\.md$|\.gitkeep$).+'
        message = 'No versionar bundles, reportes o capturas generadas de migracion.'
    },
    @{
        code = 'repo_hygiene.screenshot_versioned'
        pattern = '^screenshots/'
        message = 'No versionar capturas locales generadas.'
    },
    @{
        code = 'repo_hygiene.handoff_versioned'
        pattern = '^(HANDOFF/|docs/HANDOFF_GREENFIELD_.*\.md$)'
        message = 'No versionar handoffs historicos del root anterior.'
    },
    @{
        code = 'repo_hygiene.secret_material_versioned'
        pattern = '\.(p12|pfx|pem|key|crt|cer|jks|keystore)$'
        message = 'No versionar certificados, llaves ni material criptografico.'
    },
    @{
        code = 'repo_hygiene.dump_or_snapshot_versioned'
        pattern = '(^|/)[^/]*(dump|backup|snapshot|export|bundle)[^/]*\.(json|csv|sql|xlsx?|zip|gz|dump|bak|backup)$'
        message = 'No versionar dumps, snapshots, exports o backups operativos.'
    }
)

$violations = New-Object System.Collections.Generic.List[object]

function Add-ViolationsForPaths([string[]]$paths, [string]$source) {
    foreach ($rawPath in $paths) {
        $path = Normalize-GitPath $rawPath
        if ([string]::IsNullOrWhiteSpace($path) -or (Test-AllowlistedPath $path)) {
            continue
        }

        foreach ($rule in $blockedRules) {
            if ($path -match $rule.pattern) {
                $violations.Add([ordered]@{
                    source = $source
                    path = $path
                    code = $rule.code
                    message = $rule.message
                })
            }
        }
    }
}

$trackedPaths = @(Get-GitOutput @('ls-files'))
Add-ViolationsForPaths -paths $trackedPaths -source 'tracked'

$untrackedPaths = @()
if ($IncludeUntracked) {
    $untrackedPaths = @(Get-GitOutput @('ls-files', '--others', '--exclude-standard'))
    Add-ViolationsForPaths -paths $untrackedPaths -source 'untracked'
}

if ($violations.Count -gt 0) {
    Write-Host 'Repo hygiene guard failed:' -ForegroundColor Red
    Write-Host ($violations | ConvertTo-Json -Depth 5)
    throw 'El repo contiene artefactos sensibles/locales que no deben versionarse.'
}

if ($IncludeUntracked) {
    Write-Host (
        "Repo hygiene OK: $($trackedPaths.Count) tracked paths and " +
        "$($untrackedPaths.Count) untracked paths reviewed; no sensitive local artifacts are versioned or left unignored."
    ) -ForegroundColor Green
} else {
    Write-Host "Repo hygiene OK: $($trackedPaths.Count) tracked paths reviewed; no sensitive local artifacts are versioned." -ForegroundColor Green
}
