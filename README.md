# E2EXE-API

> 易语言命令行编译服务 - 通过 HTTP API 远程编译易语言源码

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.6+-green.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/flask-2.3+-red.svg)](https://flask.palletsprojects.com/)

## 📖 简介

E2EXE-API 是一个基于 HTTP 的易语言编译服务，通过 RESTful API 方式远程编译易语言源码。它封装了易语言命令行编译工具 `ecl.exe`，支持普通编译、静态编译、独立编译、黑月编译等多种编译模式，便于集成到自动化构建、CI/CD 流程中。

### ✨ 特性

- 🚀 **HTTP API 调用** - 通过 JSON 格式的 HTTP 请求提交编译任务
- 🔧 **多种编译模式** - 支持普通、静态、独立、黑月（默认/汇编/C++/MFC）、易包、调试运行
- 📦 **异步编译** - 提交后异步处理，支持状态查询
- 💾 **自动文件管理** - 编译结果自动保存，1小时后自动清理
- 🔐 **源码安全** - 使用 SHA256 哈希标识，支持 base64 编码传输
- 📝 **详细日志** - 完整的编译日志和错误诊断
- 🏥 **健康检查** - 内置健康检查接口，便于监控
- 🪟 **Windows 原生** - 完美支持 Windows Server 2012 R2 及以上版本

## 📋 系统要求

- **操作系统**: Windows 7/8/10/11, Windows Server 2012 R2+
- **Python**: 3.6 或更高版本
- **易语言**: 5.0 或更高版本（需安装）
- **编译工具**: [ecl.exe](https://github.com/AlongsCode/ecl) (易语言命令行编译工具)

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

或使用国内镜像：

```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 2. 准备编译工具

将 `ecl.exe` 放置到项目根目录：

```
e2exe-api/
├── app.py
├── ecl.exe          # ← 在这里
├── requirements.txt
└── ...
```

### 3. 启动服务

**前台运行：**
```bash
python app.py
```

**后台运行（Windows 服务）：**
```bash
install_service.bat
```

**验证服务：**
```bash
curl http://localhost:8800/Health
```

### 4. 编译源码

**使用 PowerShell 一行命令：**
```powershell
$s='C:\test.e';$o='C:\test.exe';$b=[IO.File]::ReadAllBytes($s);$h=(Invoke-RestMethod -Uri 'http://localhost:8800/MakeE' -Method Post -Body (@{type='static';ecode=[Convert]::ToBase64String($b)}|ConvertTo-Json) -ContentType 'application/json').hash;while((Invoke-RestMethod -Uri 'http://localhost:8800/State' -Method Post -Body (@{hash=$h}|ConvertTo-Json) -ContentType 'application/json').state -ne 'OK'){Start-Sleep 2};Invoke-RestMethod -Uri 'http://localhost:8800/DownFile' -Method Post -Body (@{hash=$h}|ConvertTo-Json) -ContentType 'application/json' -OutFile $o
```

## 📚 API 文档

### 基础信息

| 项目 | 说明 |
|------|------|
| 服务地址 | `http://localhost:8800` |
| 请求格式 | `application/json` |
| 响应格式 | `application/json` |
| 文件传输 | Base64 编码 |

### 支持编译类型

| 类型 | 说明 | 对应参数 |
|------|------|----------|
| `normal` | 普通编译 | - |
| `static` | 静态编译 | `-s` |
| `independent` | 独立编译 | `-d` |
| `blackmoon` | 黑月编译（默认模式） | `-bm` |
| `blackmoon_asm` | 黑月汇编模式 | `-bm0` |
| `blackmoon_cpp` | 黑月 C++ 模式 | `-bm1` |
| `blackmoon_mfc` | 黑月 MFC 模式 | `-bm2` |
| `package` | 易包编译 | `-p` |
| `debug` | 调试运行 | `-r` |

---

### POST /MakeE - 提交编译任务

提交易语言源码并启动编译。

**请求体：**
```json
{
    "type": "static",
    "ecode": "base64编码的源码内容"
}
```

**参数说明：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `type` | string | 是 | 编译类型（见上表） |
| `ecode` | string | 是 | Base64 编码的易语言源码 |

**成功响应：**
```json
{
    "code": 200,
    "hash": "a1b2c3d4e5f67890..."
}
```

**错误响应：**
```json
{
    "code": 400,
    "error": "错误描述信息"
}
```

---

### POST /State - 查询编译状态

查询编译任务的当前状态。

**请求体：**
```json
{
    "hash": "a1b2c3d4e5f67890..."
}
```

**成功响应：**
```json
{
    "code": 200,
    "state": "OK",
    "message": "编译成功"
}
```

**状态说明：**

| 状态 | 说明 |
|------|------|
| `Pending` | 等待编译 |
| `Building` | 编译中 |
| `OK` | 编译成功，可下载 |
| `Error` | 编译失败 |
| `NotFound` | 任务不存在 |

---

### POST /DownFile - 下载编译结果

下载编译完成的可执行文件。

**请求体：**
```json
{
    "hash": "a1b2c3d4e5f67890..."
}
```

**成功响应：**
- 返回二进制文件流
- Content-Type: `application/octet-stream`
- 文件名: `{hash}.exe`

**错误响应：**
```json
{
    "code": 400,
    "error": "文件未准备好，状态: Building"
}
```

---

### POST /ErrorLog - 获取错误日志

获取编译失败的详细错误日志。

**请求体：**
```json
{
    "hash": "a1b2c3d4e5f67890..."
}
```

**成功响应：**
```json
{
    "code": 200,
    "error_log": "详细错误日志内容..."
}
```

---

### GET /Health - 健康检查

检查服务是否正常运行。

**响应：**
```json
{
    "status": "OK",
    "timestamp": "2024-01-01T12:00:00",
    "active_tasks": 5
}
```

---

### GET /ListTasks - 列出所有任务

列出当前所有编译任务（调试用）。

**响应：**
```json
{
    "code": 200,
    "total": 2,
    "tasks": [
        {
            "hash": "a1b2c3d4...",
            "state": "OK",
            "compile_type": "static",
            "start_time": "2024-01-01T12:00:00",
            "end_time": "2024-01-01T12:05:00"
        }
    ]
}
```

## 💻 使用示例

### Python 示例

```python
import requests
import base64
import time

# 1. 读取源码并 Base64 编码
with open('test.e', 'rb') as f:
    ecode = base64.b64encode(f.read()).decode('utf-8')

# 2. 提交编译任务
response = requests.post('http://localhost:8800/MakeE', json={
    'type': 'static',
    'ecode': ecode
})
result = response.json()
file_hash = result['hash']
print(f'任务已提交: {file_hash}')

# 3. 等待编译完成
while True:
    response = requests.post('http://localhost:8800/State', json={
        'hash': file_hash
    })
    state = response.json()['state']
    print(f'状态: {state}')
    
    if state == 'OK':
        break
    elif state == 'Error':
        print('编译失败！')
        exit(1)
    
    time.sleep(2)

# 4. 下载编译结果
response = requests.post('http://localhost:8800/DownFile', json={
    'hash': file_hash
})
with open('output.exe', 'wb') as f:
    f.write(response.content)
print('下载成功: output.exe')
```

### PowerShell 示例

```powershell
# 提交编译
$ecode = [Convert]::ToBase64String([IO.File]::ReadAllBytes('test.e'))
$response = Invoke-RestMethod -Uri 'http://localhost:8800/MakeE' -Method Post -Body (@{
    type = 'static'
    ecode = $ecode
} | ConvertTo-Json) -ContentType 'application/json'

$hash = $response.hash

# 查询状态
while ($true) {
    $state = (Invoke-RestMethod -Uri 'http://localhost:8800/State' -Method Post -Body (@{ hash = $hash } | ConvertTo-Json) -ContentType 'application/json').state
    Write-Host "状态: $state"
    if ($state -eq 'OK') { break }
    if ($state -eq 'Error') { exit 1 }
    Start-Sleep -Seconds 2
}

# 下载文件
Invoke-RestMethod -Uri 'http://localhost:8800/DownFile' -Method Post -Body (@{ hash = $hash } | ConvertTo-Json) -ContentType 'application/json' -OutFile 'output.exe'
```

### curl 示例

```bash
# 1. 提交编译
curl -X POST http://localhost:8800/MakeE \
  -H "Content-Type: application/json" \
  -d "{\"type\":\"static\",\"ecode\":\"$(base64 -w0 test.e)\"}"

# 2. 查询状态
curl -X POST http://localhost:8800/State \
  -H "Content-Type: application/json" \
  -d '{"hash":"a1b2c3d4..."}'

# 3. 下载文件
curl -X POST http://localhost:8800/DownFile \
  -H "Content-Type: application/json" \
  -d '{"hash":"a1b2c3d4..."}' \
  --output output.exe
```

## 🛠️ 部署指南

### Windows Server 2012 R2 部署

#### 1. 安装 Python

```bash
# 下载 Python 3.8+ 安装包
# https://www.python.org/downloads/windows/
# 安装时勾选 "Add Python to PATH"
```

#### 2. 安装依赖

```bash
cd C:\e2exe-api
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

#### 3. 配置防火墙

```bash
netsh advfirewall firewall add rule name="E2EXE-API" dir=in action=allow protocol=TCP localport=8800
```

#### 4. 安装为 Windows 服务（可选）

使用 NSSM 安装为系统服务：

```bash
# 下载 nssm: https://nssm.cc/download
nssm install E2EXE-API python.exe C:\e2exe-api\app.py
nssm set E2EXE-API DisplayName "E2EXE-API 易语言编译服务"
nssm set E2EXE-API Start SERVICE_AUTO_START
nssm set E2EXE-API AppDirectory C:\e2exe-api
nssm start E2EXE-API
```

### 验证部署

```bash
curl http://localhost:8800/Health
```

## 📁 项目结构

```
e2exe-api/
├── app.py                 # 主服务程序
├── ecl.exe               # 易语言命令行编译工具
├── requirements.txt      # Python 依赖
├── start.bat            # 启动脚本
├── install.bat          # 安装依赖脚本
├── install_service.bat  # 安装 Windows 服务
├── uninstall_service.bat # 卸载 Windows 服务
├── compile_stable.ps1   # PowerShell 编译脚本
├── temp/                # 临时文件目录（自动创建）
│   ├── upload/          # 上传的源码
│   ├── compile/         # 编译临时文件
│   └── output/          # 编译结果
└── service.log          # 服务日志
```

## ⚙️ 配置说明

在 `app.py` 的 `Config` 类中修改配置：

```python
class Config:
    HOST = '0.0.0.0'              # 监听地址
    PORT = 8800                   # 监听端口
    TEMP_DIR = './temp'           # 临时文件目录
    ECL_EXE = './ecl.exe'         # 编译工具路径
    EXPIRE_TIME = 3600            # 文件过期时间（秒）
```

## ❗ 常见问题

### Q: 编译失败，提示"未知错误"？

A: 查看详细错误日志：
```bash
curl -X POST http://localhost:8800/ErrorLog -H "Content-Type: application/json" -d '{"hash":"你的hash"}'
```

### Q: 服务无法启动？

A: 检查以下几点：
1. `ecl.exe` 是否存在于项目根目录
2. 端口 8800 是否被占用
3. Python 版本是否为 3.6+

### Q: 编译结果文件在哪里？

A: 文件通过 `/DownFile` 接口下载，默认在 `temp/output/` 目录中临时保存，1小时后自动删除。

### Q: 如何修改默认端口？

A: 修改 `app.py` 中的 `Config.PORT` 配置项。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 🙏 致谢

- [ecl](https://github.com/zhongjianhua163/ECommandPrompt) - 易语言命令行编译工具
- [Flask](https://flask.palletsprojects.com/) - Web 框架

---

**Made with ❤️ for the EasyLanguage Community**
