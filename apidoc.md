# E2EXE-API 接口文档

## 基础信息

| 项目 | 说明 |
|------|------|
| 服务地址 | `http://localhost:8800` |
| 请求格式 | `application/json` |
| 响应格式 | `application/json` |
| 文件传输 | Base64 编码 |

## 支持编译类型

| 类型 | 说明 |
|------|------|
| `normal` | 普通编译 |
| `static` | 静态编译 |
| `independent` | 独立编译 |
| `blackmoon` | 黑月编译（默认模式） |
| `blackmoon_asm` | 黑月汇编模式 |
| `blackmoon_cpp` | 黑月 C++ 模式 |
| `blackmoon_mfc` | 黑月 MFC 模式 |
| `package` | 易包编译 |
| `debug` | 调试运行 |

---

## POST /MakeE

提交编译任务

### 请求体

```json
{
    "type": "static",
    "ecode": "base64编码的源码内容"
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `type` | string | 是 | 编译类型 |
| `ecode` | string | 是 | Base64 编码的易语言源码 |

### 响应

**成功 (200)**

```json
{
    "code": 200,
    "hash": "a1b2c3d4e5f67890..."
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | integer | 状态码 |
| `hash` | string | 任务唯一标识（SHA256） |

**错误 (400)**

```json
{
    "code": 400,
    "error": "错误描述"
}
```

---

## POST /State

查询编译状态

### 请求体

```json
{
    "hash": "a1b2c3d4e5f67890..."
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `hash` | string | 是 | 任务标识 |

### 响应

**成功 (200)**

```json
{
    "code": 200,
    "state": "OK",
    "message": "编译成功"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | integer | 状态码 |
| `state` | string | 状态：`Pending`/`Building`/`OK`/`Error` |
| `message` | string | 状态描述 |

**任务不存在 (404)**

```json
{
    "code": 404,
    "state": "NotFound"
}
```

---

## POST /DownFile

下载编译结果（**首次下载后自动删除，不可重复下载**）

### 请求体

```json
{
    "hash": "a1b2c3d4e5f67890..."
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `hash` | string | 是 | 任务标识 |

### 响应

**成功 (200)**

- 返回二进制文件流
- Content-Type: `application/octet-stream`
- 文件名: `{hash}.exe`

**文件未准备好 (400)**

```json
{
    "code": 400,
    "error": "文件未准备好，状态: Building"
}
```

**任务不存在 (404)**

```json
{
    "code": 404,
    "error": "未找到该任务"
}
```

**文件已下载或已过期 (410)**

```json
{
    "code": 410,
    "error": "文件已下载，已被删除"
}
```

或

```json
{
    "code": 410,
    "error": "文件已过期"
}
```

---

## POST /ErrorLog

获取编译错误日志

### 请求体

```json
{
    "hash": "a1b2c3d4e5f67890..."
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `hash` | string | 是 | 任务标识 |

### 响应

**成功 (200)**

```json
{
    "code": 200,
    "error_log": "详细错误日志内容..."
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | integer | 状态码 |
| `error_log` | string | 错误日志内容 |

**无日志 (200)**

```json
{
    "code": 200,
    "error_log": "错误日志已被清理"
}
```

---

## GET /Health

健康检查

### 响应

```json
{
    "status": "OK",
    "timestamp": "2024-01-01T12:00:00",
    "active_tasks": 5
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `status` | string | 服务状态 |
| `timestamp` | string | 当前时间（ISO格式） |
| `active_tasks` | integer | 当前活跃任务数 |

---

## GET /ListTasks

列出所有任务（调试用）

### 响应

```json
{
    "code": 200,
    "total": 2,
    "tasks": [
        {
            "hash": "a1b2c3d4...",
            "state": "OK",
            "compile_type": "static",
            "message": "编译成功",
            "downloaded": false,
            "start_time": "2024-01-01T12:00:00",
            "end_time": "2024-01-01T12:05:00"
        }
    ]
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | integer | 状态码 |
| `total` | integer | 任务总数 |
| `tasks` | array | 任务列表 |
| `tasks[].hash` | string | 任务标识 |
| `tasks[].state` | string | 任务状态 |
| `tasks[].compile_type` | string | 编译类型 |
| `tasks[].message` | string | 状态描述 |
| `tasks[].downloaded` | boolean | 是否已下载 |
| `tasks[].start_time` | string | 开始时间 |
| `tasks[].end_time` | string | 结束时间 |

---

## 状态码说明

| HTTP状态码 | 说明 |
|-----------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 404 | 任务未找到 |
| 410 | 文件已下载或已过期 |
| 500 | 服务器内部错误 |

---

## 使用示例

### Python

```python
import requests
import base64
import time

# 1. 提交编译
with open('test.e', 'rb') as f:
    ecode = base64.b64encode(f.read()).decode('utf-8')

response = requests.post('http://localhost:8800/MakeE', json={
    'type': 'static',
    'ecode': ecode
})
file_hash = response.json()['hash']
print(f'Hash: {file_hash}')

# 2. 查询状态
while True:
    response = requests.post('http://localhost:8800/State', json={
        'hash': file_hash
    })
    state = response.json()['state']
    if state == 'OK':
        break
    elif state == 'Error':
        print('编译失败')
        exit(1)
    time.sleep(2)

# 3. 下载文件（首次下载后自动删除）
response = requests.post('http://localhost:8800/DownFile', json={
    'hash': file_hash
})
with open('output.exe', 'wb') as f:
    f.write(response.content)
print('下载成功')
```

### PowerShell

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
    if ($state -eq 'OK') { break }
    if ($state -eq 'Error') { exit 1 }
    Start-Sleep -Seconds 2
}

# 下载文件
Invoke-RestMethod -Uri 'http://localhost:8800/DownFile' -Method Post -Body (@{ hash = $hash } | ConvertTo-Json) -ContentType 'application/json' -OutFile 'output.exe'
```

### curl

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
