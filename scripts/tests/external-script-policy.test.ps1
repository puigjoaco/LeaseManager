Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$connectScript = Join-Path $repoRoot "scripts\connect-frontend-to-backend.ps1"
$railwayScript = Join-Path $repoRoot "scripts\railway-backend-bootstrap.ps1"

function Assert-Condition {
    param(
        [bool]$Condition,
        [string]$Message
    )

    if (-not $Condition) {
        throw $Message
    }
}

function Assert-Parse {
    param([string]$Path)

    $tokens = $null
    $errors = $null
    [System.Management.Automation.Language.Parser]::ParseFile($Path, [ref]$tokens, [ref]$errors) | Out-Null
    Assert-Condition ($errors.Count -eq 0) "PowerShell parse errors en $Path`: $($errors | Out-String)"
}

function Invoke-IsolatedScript {
    param(
        [string]$Path,
        [string[]]$ScriptArgs
    )

    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $output = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $Path @ScriptArgs 2>&1 | Out-String
        return @{
            ExitCode = $LASTEXITCODE
            Output = $output
        }
    } finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
}

Assert-Condition (Test-Path -LiteralPath $connectScript) "No existe $connectScript"
Assert-Condition (Test-Path -LiteralPath $railwayScript) "No existe $railwayScript"

Assert-Parse -Path $connectScript
Assert-Parse -Path $railwayScript

$connectContent = Get-Content -LiteralPath $connectScript -Raw
$railwayContent = Get-Content -LiteralPath $railwayScript -Raw

Assert-Condition ($connectContent -notmatch 'Produccion 1\.0') 'connect-frontend-to-backend no debe apuntar a Produccion 1.0.'
Assert-Condition ($connectContent -notmatch 'deploy\.bat') 'connect-frontend-to-backend no debe leer deploy.bat como fallback.'
Assert-Condition ($connectContent -match 'AuthorizationRef') 'connect-frontend-to-backend debe exigir AuthorizationRef en modo Apply.'
Assert-Condition ($connectContent -match 'Modo plan') 'connect-frontend-to-backend debe tener modo plan por defecto.'
Assert-Condition ($connectContent -match '-Redeploy') 'connect-frontend-to-backend debe exigir redeploy explicito.'

Assert-Condition ($railwayContent -notmatch 'Produccion 1\.0') 'railway-backend-bootstrap no debe apuntar a Produccion 1.0.'
Assert-Condition ($railwayContent -match 'AuthorizationRef') 'railway-backend-bootstrap debe exigir AuthorizationRef en modo Apply.'
Assert-Condition ($railwayContent -match 'Modo plan') 'railway-backend-bootstrap debe tener modo plan por defecto.'
Assert-Condition ($railwayContent -match '<redacted>') 'railway-backend-bootstrap debe redactar valores de variables en salida.'

$connectPlan = Invoke-IsolatedScript -Path $connectScript -ScriptArgs @('-BackendUrl', 'https://api.example.test')
Assert-Condition ($connectPlan.ExitCode -eq 0) "connect plan debe terminar OK. Output: $($connectPlan.Output)"
Assert-Condition ($connectPlan.Output -match 'Modo plan') 'connect plan debe declarar modo plan.'
Assert-Condition ($connectPlan.Output -match 'backend_url_validada=true') 'connect plan debe validar URL sin imprimir el valor.'
Assert-Condition ($connectPlan.Output -notmatch 'api\.example\.test') 'connect plan no debe imprimir la URL backend completa.'

$connectApply = Invoke-IsolatedScript -Path $connectScript -ScriptArgs @('-BackendUrl', 'https://api.example.test', '-Apply')
Assert-Condition ($connectApply.ExitCode -ne 0) 'connect -Apply sin AuthorizationRef debe fallar.'
Assert-Condition ($connectApply.Output -match 'AuthorizationRef') 'connect -Apply sin AuthorizationRef debe fallar por AuthorizationRef.'

$railwayPlan = Invoke-IsolatedScript -Path $railwayScript -ScriptArgs @()
Assert-Condition ($railwayPlan.ExitCode -eq 0) "railway plan debe terminar OK. Output: $($railwayPlan.Output)"
Assert-Condition ($railwayPlan.Output -match 'Modo plan') 'railway plan debe declarar modo plan.'
Assert-Condition ($railwayPlan.Output -match 'backend_env_file_validado=true') 'railway plan debe validar archivo de variables.'
Assert-Condition ($railwayPlan.Output -notmatch 'railway whoami') 'railway plan no debe llamar Railway CLI.'
Assert-Condition ($railwayPlan.Output -notmatch 'variable set') 'railway plan no debe setear variables.'

$railwayRealEnv = Invoke-IsolatedScript -Path $railwayScript -ScriptArgs @('-BackendEnvPath', 'backend\.env')
Assert-Condition ($railwayRealEnv.ExitCode -ne 0) 'railway no debe aceptar BackendEnvPath apuntando a .env real.'
Assert-Condition ($railwayRealEnv.Output -match '\.env real') 'railway debe fallar por politica de .env real antes de leer el archivo.'
Assert-Condition ($railwayRealEnv.Output -notmatch 'No existe BackendEnvPath') 'railway debe rechazar .env por politica antes de intentar resolverlo.'
Assert-Condition ($railwayRealEnv.Output -notmatch 'railway whoami') 'railway con .env real no debe tocar Railway CLI.'

$railwayApply = Invoke-IsolatedScript -Path $railwayScript -ScriptArgs @('-Apply')
Assert-Condition ($railwayApply.ExitCode -ne 0) 'railway -Apply sin AuthorizationRef debe fallar.'
Assert-Condition ($railwayApply.Output -match 'AuthorizationRef') 'railway -Apply sin AuthorizationRef debe fallar por AuthorizationRef.'
Assert-Condition ($railwayApply.Output -notmatch 'railway whoami') 'railway -Apply sin AuthorizationRef no debe tocar Railway CLI.'

Write-Host "external-script-policy OK" -ForegroundColor Green
