# 易语言编译服务 API 文档

## 概述

易语言编译服务是一个基于 HTTP 的 RESTful API 服务，用于在命令行中编译易语言源码文件，便于自动构建、批处理和部署流程。

### 基本信息

- **服务地址**: `http://localhost:8800`
- **请求格式**: JSON
- **响应格式**: JSON / 二进制文件

### 支持编译类型

| 类型 | 说明 |
|------|------|
| `normal` | 普通编译 |
| `static` | 静态编译 |
| `independent` | 独立编译 |
| `blackmoon` | 黑月编译 |
| `package` | 易包编译 |
| `debug` | 调试运行 |

---

## 1. 提交编译 - POST /MakeE

提交易语言源码并启动编译任务。

### 请求

**URL**: `/MakeE`  
**Method**: `POST`  
**Content-Type**: `application/json`

**请求体**:

```json
{
    "type": "normal",
    "ecode": "base64编码的源码内容"
}
```

**参数说明**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `type` | string | 是 | 编译类型：`normal`/`static`/`independent`/`blackmoon`/`package`/`debug` |
| `ecode` | string | 是 | Base64 编码的易语言源码文件内容 |

### 响应

**成功响应** (200):

```json
{
    "code": 200,
    "hash": "a1b2c3d4e5f6..."
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | integer | 状态码，200 表示成功 |
| `hash` | string | 源码文件的 SHA256 哈希值，用于后续查询和下载 |

**错误响应**:

```json
{
    "code": 400,
    "error": "错误描述信息"
}
```

### 示例

**请求示例**:

```bash
curl -X POST http://localhost:8800/MakeE \
  -H "Content-Type: application/json" \
  -d '{
    "type": "static",
    "ecode": "5L2g5aW955qE5rqQ56CB5YaF5rOo..."
  }'
```

**Python 示例**:

```python
import requests
import base64

with open('test.e', 'rb') as f:
    file_data = f.read()

response = requests.post('http://localhost:8800/MakeE', json={
    'type': 'static',
    'ecode': base64.b64encode(file_data).decode('utf-8')
})

result = response.json()
file_hash = result['hash']
print(f"任务已提交，Hash: {file_hash}")
```

---

## 2. 查询状态 - POST /State

查询编译任务的当前状态。

### 请求

**URL**: `/State`  
**Method**: `POST`  
**Content-Type**: `application/json`

**请求体**:

```json
{
    "hash": "a1b2c3d4e5f6..."
}
```

**参数说明**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `hash` | string | 是 | 提交编译时返回的文件哈希值 |

### 响应

**成功响应** (200):

```json
{
    "code": 200,
    "state": "Building"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | integer | 状态码，200 表示成功 |
| `state` | string | 编译状态：`Pending`/`Building`/`OK`/`Error` |

**状态说明**:

| 状态 | 说明 |
|------|------|
| `Pending` | 等待编译 |
| `Building` | 编译中 |
| `OK` | 编译成功，可下载 |
| `Error` | 编译失败 |

**错误响应**:

```json
{
    "code": 404,
    "state": "NotFound"
}
```

### 示例

**请求示例**:

```bash
curl -X POST http://localhost:8800/State \
  -H "Content-Type: application/json" \
  -d '{
    "hash": "a1b2c3d4e5f6..."
  }'
```

**Python 示例**:

```python
import requests
import time

def wait_for_complete(file_hash):
    while True:
        response = requests.post('http://localhost:8800/State', json={
            'hash': file_hash
        })
        result = response.json()
        
        if result['state'] == 'OK':
            return True
        elif result['state'] == 'Error':
            return False
        
        time.sleep(3)

# 等待编译完成
if wait_for_complete(file_hash):
    print("编译成功！")
else:
    print("编译失败！")
```

---

## 3. 下载文件 - POST /DownFile

下载编译完成的可执行文件。

### 请求

**URL**: `/DownFile`  
**Method**: `POST`  
**Content-Type**: `application/json`

**请求体**:

```json
{
    "hash": "a1b2c3d4e5f6..."
}
```

**参数说明**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `hash` | string | 是 | 提交编译时返回的文件哈希值 |

### 响应

**成功响应** (200):

- 返回二进制文件流，文件名为 `{hash}.exe`
- Content-Type: `application/octet-stream`

**错误响应**:

```json
{
    "code": 400,
    "error": "文件未准备好，状态: Building"
}
```

或

```json
{
    "code": 404,
    "error": "未找到该任务"
}
```

或

```json
{
    "code": 410,
    "error": "文件已过期"
}
```

### 示例

**请求示例**:

```bash
curl -X POST http://localhost:8800/DownFile \
  -H "Content-Type: application/json" \
  -d '{
    "hash": "a1b2c3d4e5f6..."
  }' \
  --output output.exe
```

**Python 示例**:

```python
import requests

def download_file(file_hash, output_path):
    response = requests.post('http://localhost:8800/DownFile', json={
        'hash': file_hash
    })
    
    if response.status_code == 200:
        with open(output_path, 'wb') as f:
            f.write(response.content)
        print(f"下载成功: {output_path}")
        return True
    else:
        print(f"下载失败: {response.status_code}")
        return False

# 下载编译结果
download_file(file_hash, 'output.exe')
```

---

## 4. 健康检查 - GET /Health

检查服务是否正常运行。

### 请求

**URL**: `/Health`  
**Method**: `GET`

### 响应

**成功响应** (200):

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

### 示例

```bash
curl http://localhost:8800/Health
```

```python
import requests

response = requests.get('http://localhost:8800/Health')
print(response.json())
```

---

## 5. 列出任务 - GET /ListTasks

列出所有编译任务（调试用）。

### 请求

**URL**: `/ListTasks`  
**Method**: `GET`

### 响应

**成功响应** (200):

```json
{
    "code": 200,
    "total": 2,
    "tasks": [
        {
            "hash": "a1b2c3d4e5f6...",
            "state": "OK",
            "compile_type": "static",
            "start_time": "2024-01-01T12:00:00",
            "end_time": "2024-01-01T12:05:00"
        },
        {
            "hash": "f6e5d4c3b2a1...",
            "state": "Building",
            "compile_type": "normal",
            "start_time": "2024-01-01T12:10:00",
            "end_time": null
        }
    ]
}
```

### 示例

```bash
curl http://localhost:8800/ListTasks
```

---

## 完整工作流程示例

### Python 完整示例

```python
import requests
import base64
import time
import sys

def compile_e_file(file_path, compile_type='normal'):
    """完整的编译流程"""
    
    # 1. 读取并提交源码
    with open(file_path, 'rb') as f:
        file_data = f.read()
    
    response = requests.post('http://localhost:8800/MakeE', json={
        'type': compile_type,
        'ecode': base64.b64encode(file_data).decode('utf-8')
    })
    
    if response.status_code != 200:
        print(f"提交失败: {response.text}")
        return False
    
    result = response.json()
    file_hash = result['hash']
    print(f"✅ 任务已提交，Hash: {file_hash}")
    
    # 2. 等待编译完成
    print("⏳ 等待编译完成...")
    while True:
        response = requests.post('http://localhost:8800/State', json={
            'hash': file_hash
        })
        
        if response.status_code != 200:
            print(f"查询失败: {response.text}")
            return False
        
        state = response.json()['state']
        print(f"📊 当前状态: {state}")
        
        if state == 'OK':
            print("✅ 编译成功！")
            break
        elif state == 'Error':
            print("❌ 编译失败！")
            return False
        
        time.sleep(3)
    
    # 3. 下载编译结果
    response = requests.post('http://localhost:8800/DownFile', json={
        'hash': file_hash
    })
    
    if response.status_code == 200:
        output_path = file_path.replace('.e', '.exe')
        with open(output_path, 'wb') as f:
            f.write(response.content)
        print(f"✅ 下载成功: {output_path}")
        return True
    else:
        print(f"❌ 下载失败: {response.text}")
        return False

# 使用示例
if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python script.py <源码文件> [编译类型]")
        sys.exit(1)
    
    file_path = sys.argv[1]
    compile_type = sys.argv[2] if len(sys.argv) > 2 else 'normal'
    
    compile_e_file(file_path, compile_type)
```

### 使用 curl 的完整流程

```bash
#!/bin/bash

# 1. 提交编译
FILE_HASH=$(curl -s -X POST http://localhost:8800/MakeE \
  -H "Content-Type: application/json" \
  -d "{
    \"type\": \"static\",
    \"ecode\": \"$(base64 -w0 test.e)\"
  }" | jq -r '.hash')

echo "任务提交成功，Hash: $FILE_HASH"

# 2. 查询状态
while true; do
  STATE=$(curl -s -X POST http://localhost:8800/State \
    -H "Content-Type: application/json" \
    -d "{\"hash\": \"$FILE_HASH\"}" | jq -r '.state')
  
  echo "当前状态: $STATE"
  
  if [ "$STATE" = "OK" ]; then
    break
  elif [ "$STATE" = "Error" ]; then
    echo "编译失败"
    exit 1
  fi
  
  sleep 3
done

# 3. 下载文件
curl -X POST http://localhost:8800/DownFile \
  -H "Content-Type: application/json" \
  -d "{\"hash\": \"$FILE_HASH\"}" \
  --output output.exe

echo "下载完成: output.exe"
```

---

## 错误码说明

| HTTP状态码 | 说明 |
|-----------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 404 | 任务未找到 |
| 410 | 文件已过期 |
| 500 | 服务器内部错误 |

---

## 注意事项

1. **文件过期时间**: 编译完成后，文件在1小时后自动删除
2. **并发限制**: 多个任务会排队编译，建议合理控制提交频率
3. **超时时间**: 单个编译任务超时时间为10分钟
4. **安全建议**: 生产环境建议添加身份认证和访问控制
5. **日志查看**: 服务日志保存在 `service.log` 文件中

---

## 常见问题

### Q: 为什么返回"文件已过期"？
A: 编译成功后的文件会在1小时后自动删除，请及时下载。

### Q: 如何查看编译失败的具体原因？
A: 查看服务日志文件 `service.log`，其中包含详细的错误信息。

### Q: 支持哪些编译类型？
A: 支持 `normal`、`static`、`independent`、`blackmoon`、`package`、`debug`。

### Q: 如何提高编译速度？
A: 建议减少并发提交数量，确保系统资源充足。