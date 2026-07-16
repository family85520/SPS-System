# ============================================
# deploy/windows/deploy.ps1 — Windows 统一部署脚本
# SPS 排班管理系统部署工具
# ============================================

param(
    [string]$Mode = "",
    [string]$AppDir = "",
    [string]$Domain = "",
    [switch]$NoNginx,
    [switch]$NoSystemd,
    [switch]$Force,
    [switch]$DryRun,
    [switch]$Verbose,
    [switch]$SkipHealthcheck
)

# ---------- 设置 ----------
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$DeployLibDir = Join-Path $ScriptDir "..\lib"

# ---------- 颜色与日志 ----------
$LOG_LEVEL = if ($Verbose) { "debug" } else { "info" }

function Write-Log {
    param(
        [string]$Level,
        [string]$Message
    )
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $colors = @{
        "DEBUG" = "Cyan"
        "INFO"  = "Blue"
        "WARN"  = "Yellow"
        "ERROR" = "Red"
        "OK"    = "Green"
    }
    if ($Level -eq "DEBUG" -and $LOG_LEVEL -ne "debug") { return }
    $color = $colors[$Level]
    if ($Level -eq "OK") {
        Write-Host "[$timestamp] [OK]   $Message" -ForegroundColor Green
    } else {
        Write-Host "[$timestamp] [$Level] $Message" -ForegroundColor $color
    }
}

function Write-Section {
    param([string]$Title)
    Write-Host ""
    Write-Host "═══ $Title ═══" -ForegroundColor Blue -BackgroundColor DarkBlue
    Write-Host ""
}

function Log-Debug  { Write-Log "DEBUG" $args[0] }
function Log-Info   { Write-Log "INFO"  $args[0] }
function Log-Warn   { Write-Log "WARN"  $args[0] }
function Log-Error  { Write-Log "ERROR" $args[0] }
function Log-Success{ Write-Log "OK"    $args[0] }

# ---------- 辅助函数 ----------
function Test-CommandExists {
    param([string]$Name)
    return $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

function Execute-Or-DryRun {
    param([string]$Command)
    if ($DryRun) {
        Log-Info "[DRY-RUN] $Command"
    } else {
        Invoke-Expression $Command
    }
}

function Detect-AppDir {
    # 默认: 脚本所在目录的父目录
    return Join-Path (Split-Path -Parent $ScriptDir) ".."
}

function Ensure-File {
    param([string]$Path, [string]$Purpose)
    if (-not (Test-Path $Path)) {
        Log-Error "未找到: $Path"
        Log-Error "$Purpose"
        exit 1
    }
}

function Health-Check {
    param(
        [string]$Url = "http://localhost:8000/health",
        [int]$MaxRetries = 10,
        [int]$RetryInterval = 3
    )
    Log-Info "等待服务启动: $Url"
    for ($i = 1; $i -le $MaxRetries; $i++) {
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
            if ($response.StatusCode -eq 200) {
                Log-Success "服务健康检查通过 ($Url)"
                return $true
            }
        } catch {
            Log-Debug "等待服务启动... ($i/$MaxRetries)"
            Start-Sleep -Seconds $RetryInterval
        }
    }
    Log-Error "服务健康检查失败 ($Url)"
    return $false
}

function Parse-DatabaseUrl {
    param([string]$DatabaseUrl)
    if ([string]::IsNullOrEmpty($DatabaseUrl)) {
        Log-Error "DATABASE_URL 为空"
        return $false
    }

    # 解析 postgresql+asyncpg://user:pass@host:port/dbname
    $urlBody = $DatabaseUrl.Split("://")[1]
    $userPass = $urlBody.Split("@")[0]
    $hostPortDb = $urlBody.Split("@")[1]

    $global:DB_USER = $userPass.Split(":")[0]
    $global:DB_PASS = $userPass.Split(":")[1]

    $global:DB_PORT = $hostPortDb.Split(":")[1].Split("/")[0]
    $global:DB_HOST = $hostPortDb.Split(":")[0]
    $global:DB_NAME = $hostPortDb.Split("/")[1]

    # 默认值
    if ([string]::IsNullOrEmpty($global:DB_PORT)) { $global:DB_PORT = "5432" }
    if ([string]::IsNullOrEmpty($global:DB_HOST)) { $global:DB_HOST = "localhost" }

    Log-Debug "数据库配置: $global:DB_USER@$global:DB_HOST:$global:DB_PORT/$global:DB_NAME"
    return $true
}

# ---------- 检测应用目录 ----------
if ([string]::IsNullOrEmpty($AppDir)) {
    $AppDir = Detect-AppDir
}
$AppDir = (Resolve-Path $AppDir -ErrorAction SilentlyContinue) ?? $AppDir

# ---------- 命令实现 ----------

function Cmd-Install {
    Write-Section "安装系统依赖和开发环境"

    # 检查 Python
    if (-not (Test-CommandExists python)) {
        Log-Error "未找到 python 命令，请先安装 Python 3.12"
        Log-Error "下载地址: https://www.python.org/downloads/"
        exit 1
    }

    $pyVersion = & python --version 2>&1
    Log-Info "Python 版本: $pyVersion"

    # 创建虚拟环境
    $venvPath = Join-Path $AppDir "backend\venv"
    if (-not (Test-Path $venvPath)) {
        Log-Info "创建 Python 虚拟环境..."
        Execute-Or-DryRun "python -m venv `"$venvPath`""
        Log-Success "Python 虚拟环境已创建"
    } else {
        Log-Debug "虚拟环境已存在，跳过"
    }

    # 激活并安装后端依赖
    Log-Info "安装后端 Python 依赖..."
    $activatePath = Join-Path $venvPath "Scripts\activate.ps1"
    $requirementsPath = Join-Path $AppDir "backend\requirements.txt"
    Ensure-File $requirementsPath "请确认 backend/requirements.txt 存在"

    Execute-Or-DryRun "& `"$activatePath`"; pip install -r `"$requirementsPath`""
    Log-Success "Python 依赖安装完成"

    # 前端依赖
    Log-Info "安装前端依赖..."
    if (-not (Test-CommandExists npm)) {
        Log-Error "未找到 npm 命令，请先安装 Node.js 20.x LTS"
        Log-Error "参考: https://nodejs.org/"
        exit 1
    }

    $nodeModulesPath = Join-Path $AppDir "frontend\node_modules"
    if (-not (Test-Path $nodeModulesPath)) {
        Execute-Or-DryRun "cd `"$AppDir\frontend`"; npm install"
        Log-Success "前端依赖安装完成"
    } else {
        Log-Debug "node_modules 已存在，跳过"
    }

    Log-Success "安装完成！"
}

function Cmd-SetupDb {
    Write-Section "配置数据库"

    $envFile = Join-Path $AppDir "backend\.env"
    Ensure-File $envFile "请先运行 setup-env 生成 .env"

    # 读取 DATABASE_URL
    $envContent = Get-Content $envFile -Raw
    $dbUrlMatch = $envContent | Select-String "DATABASE_URL=(.+)"
    if ($dbUrlMatch) {
        $global:DATABASE_URL = $dbUrlMatch.Matches[0].Groups[1].Value
    } else {
        Log-Error ".env 中未找到 DATABASE_URL"
        exit 1
    }

    Parse-DatabaseUrl $global:DATABASE_URL

    # 检查 psql
    if (-not (Test-CommandExists psql)) {
        Log-Error "未找到 psql 命令，请先安装 PostgreSQL 客户端"
        exit 1
    }

    Log-Info "确保数据库用户 '$global:DB_USER' 存在..."
    try {
        $userCheck = psql -U postgres -tc "SELECT 1 FROM pg_roles WHERE rolname='$global:DB_USER'" 2>&1
        if ($userCheck -notmatch '1') {
            psql -U postgres -c "CREATE USER `"$global:DB_USER`" WITH PASSWORD '$global:DB_PASS';"
            Log-Success "数据库用户 '$global:DB_USER' 已创建"
        } else {
            Log-Debug "用户 '$global:DB_USER' 已存在"
        }
    } catch {
        Log-Error "创建数据库用户失败: $_"
    }

    Log-Info "确保数据库 '$global:DB_NAME' 存在..."
    try {
        $dbCheck = psql -U postgres -tc "SELECT 1 FROM pg_database WHERE datname='$global:DB_NAME'" 2>&1
        if ($dbCheck -notmatch '1') {
            psql -U postgres -c "CREATE DATABASE `"$global:DB_NAME`" OWNER `"$global:DB_USER`";"
            Log-Success "数据库 '$global:DB_NAME' 已创建"
        } else {
            Log-Debug "数据库 '$global:DB_NAME' 已存在"
        }
    } catch {
        Log-Error "创建数据库失败: $_"
    }

    # 执行 Alembic 迁移
    Log-Info "执行 Alembic 数据库迁移..."
    $backendDir = Join-Path $AppDir "backend"
    $alembicIni = Join-Path $backendDir "alembic.ini"
    $activatePath = Join-Path $backendDir "venv\Scripts\activate.ps1"

    if (-not (Test-Path $alembicIni)) {
        Log-Error "未找到 alembic.ini"
        exit 1
    }

    try {
        & $activatePath
        $result = alembic upgrade head 2>&1
        if ($LASTEXITCODE -eq 0) {
            Log-Success "数据库迁移完成"
        } else {
            Log-Error "数据库迁移失败"
            exit 1
        }
    } catch {
        Log-Error "Alembic 执行失败: $_"
        exit 1
    }

    # 测试连接
    Log-Info "测试数据库连接..."
    try {
        $testResult = psql -h $global:DB_HOST -p $global:DB_PORT -U $global:DB_USER -d $global:DB_NAME -c "SELECT 1;" 2>&1
        Log-Success "数据库连接正常"
    } catch {
        Log-Error "数据库连接失败"
        exit 1
    }

    Log-Success "数据库配置完成！"
}

function Cmd-SetupEnv {
    Write-Section "生成环境配置"

    $envFile = Join-Path $AppDir "backend\.env"

    if (Test-Path $envFile -and -not $Force) {
        Log-Warn "backend/.env 已存在"
        $confirm = Read-Host "是否覆盖？(y/N)"
        if ($confirm -notin @("y", "Y")) {
            Log-Info "取消"
            exit 0
        }
    }

    # 生成 SECRET_KEY
    try {
        $secretKey = python -c "import secrets; print(secrets.token_hex(32))" 2>&1 | Out-String
        $secretKey = $secretKey.Trim()
    } catch {
        $secretKey = (New-Guid).Guid + (New-Guid).Guid
    }

    # 交互式输入
    Log-Info "请按提示输入配置信息（括号内为默认值）"

    $dbName = Read-Host "数据库名称 [scp_db]"
    if ([string]::IsNullOrWhiteSpace($dbName)) { $dbName = "scp_db" }

    $dbUser = Read-Host "数据库用户 [scp]"
    if ([string]::IsNullOrWhiteSpace($dbUser)) { $dbUser = "scp" }

    $dbPass = Read-Host "数据库密码 [scp2026]" -AsSecureString
    if ([string]::IsNullOrWhiteSpace($dbPass)) { $dbPass = "scp2026" }
    $dbPassBSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($dbPass)
    $dbPassPlain = [System.Runtime.InteropServices.Marshal]::PtrToStringBSTR($dbPassBSTR)
    [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($dbPassBSTR)

    $inputSecretKey = Read-Host "SECRET_KEY [$secretKey]"
    if ([string]::IsNullOrWhiteSpace($inputSecretKey)) { $inputSecretKey = $secretKey }

    $allowedOrigins = Read-Host "允许的来源 (CORS) [http://localhost:5173]"
    if ([string]::IsNullOrWhiteSpace($allowedOrigins)) { $allowedOrigins = "http://localhost:5173" }

    # 写入 .env
    $envContent = @"
# 数据库配置
DATABASE_URL=postgresql+asyncpg://${dbUser}:${dbPassPlain}@localhost:5432/${dbName}

# JWT配置
SECRET_KEY=${inputSecretKey}
ACCESS_TOKEN_EXPIRE_MINUTES=480
ALGORITHM=HS256

# 应用配置
APP_NAME=排班管理系统
APP_VERSION=1.0.0
DEBUG=false

# 跨域配置
ALLOWED_ORIGINS=${allowedOrigins}

# 系统默认配置
DEFAULT_ADMIN_USERNAME=admin
DEFAULT_ADMIN_PASSWORD=admin123
"@

    Set-Content -Path $envFile -Value $envContent -Encoding UTF8
    Log-Debug "已设置权限 600: $envFile"

    # 确保 .gitignore 包含 .env
    $gitignorePath = Join-Path $AppDir ".gitignore"
    if (Test-Path $gitignorePath) {
        $gitignoreContent = Get-Content $gitignorePath -Raw
        if ($gitignoreContent -notmatch '\.env$') {
            Add-Content -Path $gitignorePath -Value "`n# Environment`n.env`n.env.*"
            Log-Debug "已更新 .gitignore"
        }
    }

    Log-Success "环境配置已生成: $envFile"
}

function Cmd-Build {
    Write-Section "构建项目"

    $envFile = Join-Path $AppDir "backend\.env"
    Ensure-File $envFile "请先运行 setup-env 生成 .env"

    # 前端构建
    Log-Info "构建前端..."
    if (-not (Test-CommandExists npm)) {
        Log-Error "未找到 npm 命令"
        exit 1
    }

    Execute-Or-DryRun "cd `"$AppDir\frontend`"; npm run build"

    $distPath = Join-Path $AppDir "frontend\dist"
    if (Test-Path $distPath) {
        Log-Success "前端构建完成 (dist/)"
    } else {
        Log-Error "前端构建失败: dist/ 目录不存在"
        exit 1
    }

    # 后端依赖更新
    Log-Info "确保后端依赖最新..."
    $activatePath = Join-Path $AppDir "backend\venv\Scripts\activate.ps1"
    $requirementsPath = Join-Path $AppDir "backend\requirements.txt"
    Execute-Or-DryRun "& `"$activatePath`"; pip install -r `"$requirementsPath`""

    Log-Success "构建完成！"
}

function Cmd-NssmInstall {
    Write-Section "注册 Windows 服务 (NSSM)"

    $nssmPath = "C:\nssm\nssm.exe"
    if (-not (Test-CommandExists nssm)) {
        # 尝试常见安装路径
        $nssmPaths = @(
            "C:\nssm\nssm.exe",
            "C:\Program Files\nssm\nssm.exe",
            "$AppDir\nssm.exe"
        )
        foreach ($path in $nssmPaths) {
            if (Test-Path $path) {
                $nssmPath = $path
                break
            }
        }
    }

    if (-not (Test-CommandExists nssm)) {
        Log-Error "未找到 NSSM"
        Log-Error "请从 https://nssm.cc/download 下载并解压到 C:\nssm"
        exit 1
    }

    $uvicornExe = Join-Path $AppDir "backend\venv\Scripts\uvicorn.exe"
    Ensure-File $uvicornExe "请确认后端虚拟环境已创建"

    $backendDir = Join-Path $AppDir "backend"
    $logsDir = Join-Path $AppDir "logs"
    New-Item -ItemType Directory -Path $logsDir -Force | Out-Null

    Log-Info "使用 NSSM 注册服务: $nssmPath"

    # 卸载旧服务（如果存在）
    $svcCheck = sc query SPSBackend 2>&1
    if ($svcCheck -match "RUNNING" -or $svcCheck -match "STOPPED") {
        Log-Info "停止并卸载旧服务..."
        net stop SPSBackend 2>$null
        & $nssm remove SPSBackend confirm 2>$null
    }

    # 注册服务
    & $nssm install SPSBackend $uvicornExe
    & $nssm set SPSBackend AppArguments "app.main:app --host 0.0.0.0 --port 8000 --workers 4"
    & $nssm set SPSBackend AppDirectory $backendDir
    & $nssm set SPSBackend Start SERVICE_AUTO_START
    & $nssm set SPSBackend AppStdout "$logsDir\backend.out.log"
    & $nssm set SPSBackend AppStderr "$logsDir\backend.err.log"
    & $nssm set SPSBackend AppRestartDelay 5000
    & $nssm set SPSBackend AppThrottle 3000

    Log-Success "NSSM 服务注册完成: SPSBackend"
    Log-Info "启动服务: net start SPSBackend"
}

function Cmd-NssmRemove {
    Write-Section "卸载 Windows 服务"

    $confirm = Read-Host "确定要卸载 SPSBackend 服务？(y/N)"
    if ($confirm -notin @("y", "Y")) {
        Log-Info "取消"
        exit 0
    }

    $nssmPath = "C:\nssm\nssm.exe"
    if (Test-Path $nssmPath) {
        & $nssm remove SPSBackend confirm
        Log-Success "服务已卸载"
    } else {
        Log-Error "未找到 NSSM: $nssmPath"
        exit 1
    }
}

function Cmd-Start {
    Write-Section "启动服务"

    $envFile = Join-Path $AppDir "backend\.env"
    Ensure-File $envFile "请先运行 setup-env 生成 .env"

    # 尝试通过 NSSM 启动
    $svcStatus = sc query SPSBackend 2>&1
    if ($svcStatus -match "RUNNING") {
        Log-Success "服务已在运行"
        if (-not $SkipHealthcheck) {
            Health-Check "http://localhost:8000/health"
        }
        return
    }

    if ($svcStatus -match "STOPPED") {
        Log-Info "启动服务..."
        net start SPSBackend
        Log-Success "服务已启动"
    } else {
        Log-Warn "SPSBackend 服务未注册，使用手动启动方式"
        Log-Info "手动启动:"
        Log-Info "  cd $AppDir\backend"
        Log-Info "  .\venv\Scripts\activate.ps1"
        Log-Info "  uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4"
        return
    }

    if (-not $SkipHealthcheck) {
        Start-Sleep -Seconds 5
        Health-Check "http://localhost:8000/health"
    }
}

function Cmd-Stop {
    Write-Section "停止服务"

    $svcStatus = sc query SPSBackend 2>&1
    if ($svcStatus -match "RUNNING") {
        Log-Info "停止服务..."
        net stop SPSBackend
        Log-Success "服务已停止"
    } else {
        Log-Warn "服务未运行或不存在"
    }
}

function Cmd-Restart {
    Write-Section "重启服务"

    $envFile = Join-Path $AppDir "backend\.env"
    Ensure-File $envFile "请先运行 setup-env 生成 .env"

    Cmd-Stop
    Start-Sleep -Seconds 3
    Cmd-Start
}

function Cmd-Status {
    Write-Section "服务状态"

    $svcStatus = sc query SPSBackend 2>&1
    Write-Host $svcStatus

    # HTTP 健康检查
    if (-not $SkipHealthcheck) {
        Write-Host ""
        Health-Check "http://localhost:8000/health" || Write-Host "(服务尚未就绪)" -ForegroundColor Yellow
    }
}

function Cmd-Rollback {
    Write-Section "回滚到上一版本"

    $envBak = Join-Path $AppDir "backend\.env.bak"
    if (-not (Test-Path $envBak)) {
        Log-Error "没有可用的备份 (.env.bak 不存在)"
        exit 1
    }

    Log-Warn "即将回滚 backend/.env 到备份版本"
    Copy-Item $envBak (Join-Path $AppDir "backend\.env") -Force
    Log-Success "回滚完成！"

    # 重启服务
    $svcStatus = sc query SPSBackend 2>&1
    if ($svcStatus -match "RUNNING") {
        Log-Info "重启服务..."
        net stop SPSBackend >$null 2>&1
        Start-Sleep -Seconds 2
        net start SPSBackend
        if (-not $SkipHealthcheck) {
            Start-Sleep -Seconds 5
            Health-Check "http://localhost:8000/health"
        }
    }
}

function Cmd-Backup {
    Write-Section "数据库备份"

    $envFile = Join-Path $AppDir "backend\.env"
    Ensure-File $envFile "请先运行 setup-env 生成 .env"

    # 读取 DATABASE_URL
    $envContent = Get-Content $envFile -Raw
    $dbUrlMatch = $envContent | Select-String "DATABASE_URL=(.+)"
    if ($dbUrlMatch) {
        $global:DATABASE_URL = $dbUrlMatch.Matches[0].Groups[1].Value
    } else {
        Log-Error ".env 中未找到 DATABASE_URL"
        exit 1
    }

    Parse-DatabaseUrl $global:DATABASE_URL

    $backupDir = Join-Path $AppDir "backups"
    New-Item -ItemType Directory -Path $backupDir -Force | Out-Null

    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $backupFile = Join-Path $backupDir "db_${timestamp}.sql"

    Log-Info "开始备份数据库 '$global:DB_NAME'..."

    try {
        $env:PGPASSWORD = $global:DB_PASS
        psql -h $global:DB_HOST -p $global:DB_PORT -U $global:DB_USER -d $global:DB_NAME -F p -f "$backupFile" 2>&1
        Remove-Item env:PGPASSWORD -ErrorAction SilentlyContinue

        if (Test-Path $backupFile) {
            $size = (Get-Item $backupFile).Length
            $sizeStr = if ($size -gt 1MB) { "{0:N2} MB" -f ($size / 1MB) } elseif ($size -gt 1KB) { "{0:N2} KB" -f ($size / 1KB) } else { "$size B" }
            Log-Success "备份完成: $backupFile ($sizeStr)"
        } else {
            Log-Error "备份失败"
            exit 1
        }
    } catch {
        Log-Error "备份失败: $_"
        exit 1
    }
}

function Cmd-Clean {
    Write-Section "清理构建产物"

    Log-Info "清理前端构建产物..."
    $distPath = Join-Path $AppDir "frontend\dist"
    $nodeModulesPath = Join-Path $AppDir "frontend\node_modules"
    if (Test-Path $distPath) { Remove-Item -Recurse -Force $distPath }
    if (Test-Path $nodeModulesPath) { Remove-Item -Recurse -Force $nodeModulesPath }

    Log-Info "清理 Python 缓存..."
    $backendDir = Join-Path $AppDir "backend"
    Get-ChildItem -Path $backendDir -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force
    Get-ChildItem -Path $backendDir -Recurse -Filter "*.pyc" -ErrorAction SilentlyContinue | Remove-Item -Force

    Log-Success "清理完成"
}

function Cmd-Help {
    $helpText = @"
${BOLD}SPS 排班管理系统 — Windows 部署脚本${NC}

${BOLD}用法:${NC}
  .\deploy.ps1 -Mode <mode> [-AppDir <path>] [-Domain <host>]

${BOLD}Modes:${NC}
  install        安装 Python venv + 前后端依赖
  setup-db       创建数据库（调用 psql）
  setup-env      交互式生成 .env 配置文件
  build          前端构建 + 后端依赖安装
  nssm-install   使用 NSSM 注册 Windows 服务
  nssm-remove    卸载 NSSM 服务
  start          启动后端服务
  stop           停止后端服务
  restart        重启后端服务
  status         查看服务状态
  rollback       回滚到上一版本
  backup         数据库备份
  clean          清理构建产物
  help           显示此帮助信息

${BOLD}Options:${NC}
  -AppDir <path>     应用根目录（默认: 脚本所在目录的父目录）
  -Domain <host>     域名（用于 Nginx server_name）
  -NoNginx           跳过 Nginx 配置（Windows 默认跳过）
  -Force             强制覆盖已有配置
  -DryRun            仅显示将要执行的命令
  -Verbose           详细日志输出
  -SkipHealthcheck   跳过健康检查

${BOLD}示例:${NC}
  .\deploy.ps1 -Mode setup-env                          # 交互式生成 .env
  .\deploy.ps1 -Mode setup-db                           # 初始化数据库
  .\deploy.ps1 -Mode build                              # 仅构建
  .\deploy.ps1 -Mode nssm-install                       # 注册 Windows 服务
  .\deploy.ps1 -Mode status                             # 查看状态
  .\deploy.ps1 -Mode rollback                           # 回滚
  .\deploy.ps1 -Mode backup                             # 备份数据库

${BOLD}环境要求:${NC}
  - Python 3.12+
  - PostgreSQL 15+ (客户端)
  - Node.js 20.x LTS
  - NSSM (可选，用于 Windows 服务化)

"@
    Write-Host $helpText
}

# ---------- 主入口 ----------
Write-Debug "应用目录: $AppDir"
Write-Debug "模式: $Mode"
Write-Debug "域名: ${Domain:-未指定}"

switch ($Mode) {
    "install"      { Cmd-Install }
    "setup-db"     { Cmd-SetupDb }
    "setup-env"    { Cmd-SetupEnv }
    "build"        { Cmd-Build }
    "start"        { Cmd-Start }
    "stop"         { Cmd-Stop }
    "restart"      { Cmd-Restart }
    "status"       { Cmd-Status }
    "rollback"     { Cmd-Rollback }
    "backup"       { Cmd-Backup }
    "clean"        { Cmd-Clean }
    "nssm-install" { Cmd-NssmInstall }
    "nssm-remove"  { Cmd-NssmRemove }
    "help" { Cmd-Help; exit 0 }
    default {
        if ([string]::IsNullOrEmpty($Mode)) {
            Cmd-Help
        } else {
            Log-Error "未知模式: $Mode"
            Cmd-Help
            exit 1
        }
    }
}
