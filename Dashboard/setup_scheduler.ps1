# setup_scheduler.ps1
# ────────────────────────────────────────────────────────────────────────
# Registra a tarefa do PMO Dashboard no Windows Task Scheduler.
# NÃO precisa de admin — cria a tarefa no contexto do usuário atual.
#
# Execução:
#   1. Abra PowerShell (normal, sem precisar de admin)
#   2. cd "C:\Apps Python\Repos\Python\Dashboard"
#   3. .\setup_scheduler.ps1
# ────────────────────────────────────────────────────────────────────────

$ErrorActionPreference = "Stop"

$TaskName      = "PMO_Dashboard_Fetcher"
$ProjectDir    = $PSScriptRoot
$PythonExe     = (Get-Command python).Source
$FetcherPy     = Join-Path $ProjectDir "fetcher.py"
$LogDir        = Join-Path $ProjectDir "data"
$ScheduleTimes = @("09:15", "14:15", "16:45")

if (-not (Test-Path $FetcherPy)) {
    Write-Error "fetcher.py nao encontrado em $FetcherPy"
    exit 1
}
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir | Out-Null
}

# Remove tarefa anterior se existir
try {
    Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop | Out-Null
    Write-Host "Removendo tarefa anterior..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
} catch {
    # tarefa nao existia, OK
}

# Triggers — um por horario, todos os dias
$triggers = @()
foreach ($t in $ScheduleTimes) {
    $triggers += New-ScheduledTaskTrigger -Daily -At $t
}

# Action: rodar fetcher.py com Python (oculto, sem janela)
$action = New-ScheduledTaskAction `
    -Execute  $PythonExe `
    -Argument "`"$FetcherPy`"" `
    -WorkingDirectory $ProjectDir

# Settings
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 15) `
    -MultipleInstances IgnoreNew

# Registra (sem -TaskPath, sem -Principal — usa user atual no contexto limited)
try {
    Register-ScheduledTask `
        -TaskName    $TaskName `
        -Action      $action `
        -Trigger     $triggers `
        -Settings    $settings `
        -Description "PMO Dashboard fetcher - coleta dados do PWA 3x ao dia." | Out-Null

    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host "  TAREFA REGISTRADA COM SUCESSO" -ForegroundColor Green
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Nome:      $TaskName"
    Write-Host "  Script:    $FetcherPy"
    Write-Host "  Horarios:  $($ScheduleTimes -join ' , ')  (diariamente)"
    Write-Host "  Roda como: $env:USERNAME (sem precisar de senha)"
    Write-Host ""
    Write-Host "  Logs:      $LogDir\fetcher.log"
    Write-Host "  Status:    $LogDir\last_update.json"
    Write-Host ""
    Write-Host "  Para testar agora:"
    Write-Host "    Start-ScheduledTask -TaskName '$TaskName'"
    Write-Host ""
    Write-Host "  Para ver historico:"
    Write-Host "    Get-ScheduledTaskInfo -TaskName '$TaskName'"
    Write-Host ""
    Write-Host "  Para remover:"
    Write-Host "    Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false"
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Green

} catch {
    Write-Host ""
    Write-Host "ERRO ao registrar tarefa via Register-ScheduledTask:" -ForegroundColor Red
    Write-Host "  $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Tentando metodo alternativo via schtasks.exe ..." -ForegroundColor Yellow
    Write-Host ""

    # Fallback: monta XML e usa schtasks.exe (funciona sem admin)
    $xmlPath = Join-Path $env:TEMP "PMO_Dashboard_Fetcher.xml"
    $triggersXml = ""
    foreach ($t in $ScheduleTimes) {
        $triggersXml += @"
    <CalendarTrigger>
      <StartBoundary>2026-01-01T${t}:00</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
    </CalendarTrigger>
"@
    }

    $xml = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>PMO Dashboard fetcher</Description>
  </RegistrationInfo>
  <Triggers>
$triggersXml
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <AllowStartIfOnBatteries>true</AllowStartIfOnBatteries>
    <DontStopIfGoingOnBatteries>true</DontStopIfGoingOnBatteries>
    <StartWhenAvailable>true</StartWhenAvailable>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <ExecutionTimeLimit>PT15M</ExecutionTimeLimit>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>$PythonExe</Command>
      <Arguments>"$FetcherPy"</Arguments>
      <WorkingDirectory>$ProjectDir</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
"@

    [System.IO.File]::WriteAllText($xmlPath, $xml, [System.Text.Encoding]::Unicode)

    schtasks /create /tn $TaskName /xml $xmlPath /f
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  OK via schtasks.exe!" -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "FALHOU pelos dois metodos." -ForegroundColor Red
        Write-Host ""
        Write-Host "Alternativa MANUAL via interface grafica:" -ForegroundColor Yellow
        Write-Host "  1. Win + R -> taskschd.msc"
        Write-Host "  2. Acao -> Importar Tarefa..."
        Write-Host "  3. Selecione: $xmlPath"
        Write-Host ""
    }
}
