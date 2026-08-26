# -*- coding: utf-8 -*-
"""
易语言命令行编译服务 - 修复返回码判断
"""

import os
import sys
import json
import hashlib
import subprocess
import threading
import time
import shutil
import logging
import base64
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_file
from werkzeug.utils import secure_filename

app = Flask(__name__)

# ==================== 配置 ====================
class Config:
    HOST = '0.0.0.0'
    PORT = 8800
    
    TEMP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'temp')
    UPLOAD_DIR = os.path.join(TEMP_DIR, 'upload')
    COMPILE_DIR = os.path.join(TEMP_DIR, 'compile')
    OUTPUT_DIR = os.path.join(TEMP_DIR, 'output')
    
    ECL_EXE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ecl.exe')
    EXPIRE_TIME = 3600
    
    LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'service.log')

    COMPILE_TYPES = {
        'normal': [],
        'static': ['-s'],
        'independent': ['-d'],
        'blackmoon': ['-bm'],
        'blackmoon_asm': ['-bm0'],
        'blackmoon_cpp': ['-bm1'],
        'blackmoon_mfc': ['-bm2'],
        'package': ['-p'],
        'debug': ['-r'],
    }

# 初始化目录
for dir_name in [Config.UPLOAD_DIR, Config.COMPILE_DIR, Config.OUTPUT_DIR]:
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Config.LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

tasks = {}

# ==================== 任务类 ====================
class CompileTask:
    def __init__(self, file_hash, compile_type='normal'):
        self.file_hash = file_hash
        self.compile_type = compile_type
        self.state = 'Pending'
        self.message = ''
        self.error_detail = ''
        self.start_time = datetime.now()
        self.end_time = None
        self.output_file = None
        self.source_path = None

# ==================== 工具函数 ====================
def calculate_file_hash(file_data):
    sha256 = hashlib.sha256()
    sha256.update(file_data)
    return sha256.hexdigest()

def save_upload_file(file_data, file_hash):
    file_path = os.path.join(Config.UPLOAD_DIR, f"{file_hash}.e")
    with open(file_path, 'wb') as f:
        f.write(file_data)
    return file_path

def compile_e_source(source_path, file_hash, task):
    """执行编译 - 修复返回码判断"""
    try:
        task.state = 'Building'
        task.message = '编译中...'
        logger.info(f"开始编译: {file_hash}, 类型: {task.compile_type}")
        
        # 准备目录
        compile_dir = os.path.join(Config.COMPILE_DIR, file_hash)
        if not os.path.exists(compile_dir):
            os.makedirs(compile_dir)
        
        output_path = os.path.join(compile_dir, f"{file_hash}.exe")
        
        # 构建命令
        cmd = [Config.ECL_EXE, 'make', source_path, output_path]
        
        # 添加编译类型
        if task.compile_type in Config.COMPILE_TYPES:
            cmd.extend(Config.COMPILE_TYPES[task.compile_type])
        
        logger.info(f"执行命令: {' '.join(cmd)}")
        logger.info(f"工作目录: {compile_dir}")
        
        # 执行编译
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,
            cwd=compile_dir,
            encoding='gbk',
            errors='ignore'
        )
        
        # 记录输出
        logger.info(f"返回码: {result.returncode}")
        if result.stdout:
            logger.info(f"STDOUT: {result.stdout[:500]}")
        if result.stderr:
            logger.info(f"STDERR: {result.stderr[:500]}")
        
        # ========== 修复：检查输出文件是否存在，而不是依赖返回码 ==========
        # 检查输出文件是否生成
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            # 编译成功（即使返回码非0）
            task.state = 'OK'
            task.message = '编译成功'
            task.error_detail = ''
            
            final_output = os.path.join(Config.OUTPUT_DIR, f"{file_hash}.exe")
            shutil.copy2(output_path, final_output)
            task.output_file = final_output
            
            logger.info(f"编译成功: {file_hash}, 输出文件大小: {os.path.getsize(output_path)} bytes")
        else:
            # 编译失败
            error_msgs = []
            if result.stderr:
                error_msgs.append(result.stderr.strip())
            if result.stdout:
                error_msgs.append(result.stdout.strip())
            
            error_detail = '\n'.join(error_msgs) if error_msgs else "无详细错误信息"
            
            # 检查常见错误
            if "支持库" in error_detail or "library" in error_detail.lower():
                task.message = "编译失败: 缺少支持库"
            elif "密码" in error_detail or "password" in error_detail.lower():
                task.message = "编译失败: 源码需要密码"
            elif "找不到" in error_detail or "not found" in error_detail.lower():
                task.message = "编译失败: 文件或路径不存在"
            else:
                task.message = "编译失败"
            
            task.state = 'Error'
            task.error_detail = error_detail
            
            # 写入错误日志
            error_log_path = os.path.join(compile_dir, "error.log")
            with open(error_log_path, 'w', encoding='gbk', errors='ignore') as f:
                f.write(f"命令: {' '.join(cmd)}\n")
                f.write(f"返回码: {result.returncode}\n")
                f.write(f"STDOUT:\n{result.stdout}\n")
                f.write(f"STDERR:\n{result.stderr}\n")
            
            logger.error(f"编译失败: {file_hash}, 错误: {task.message}")
            logger.error(f"详细错误: {error_detail[:200]}")
            
    except subprocess.TimeoutExpired:
        task.state = 'Error'
        task.message = '编译超时（超过10分钟）'
        task.error_detail = '编译过程超过10分钟未完成'
        logger.error(f"编译超时: {file_hash}")
    except Exception as e:
        task.state = 'Error'
        task.message = f'编译异常: {str(e)}'
        task.error_detail = str(e)
        logger.error(f"编译异常: {file_hash}, {str(e)}")
    finally:
        task.end_time = datetime.now()
        logger.info(f"编译完成: {file_hash}, 状态: {task.state}")

def cleanup_expired_files():
    while True:
        try:
            now = datetime.now()
            expired = []
            
            for file_hash, task in tasks.items():
                if task.state in ['OK', 'Error'] and task.end_time:
                    if (now - task.end_time).total_seconds() > Config.EXPIRE_TIME:
                        expired.append(file_hash)
            
            for file_hash in expired:
                task = tasks[file_hash]
                if task.output_file and os.path.exists(task.output_file):
                    os.remove(task.output_file)
                if task.source_path and os.path.exists(task.source_path):
                    os.remove(task.source_path)
                del tasks[file_hash]
                logger.info(f"清除过期任务: {file_hash}")
            
            time.sleep(300)
        except Exception as e:
            logger.error(f"清理异常: {str(e)}")
            time.sleep(300)

# ==================== API 接口 ====================

@app.route('/MakeE', methods=['POST'])
def make_e():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'code': 400, 'error': '请求体必须是JSON格式'}), 400
        
        compile_type = data.get('type', 'normal')
        ecode_base64 = data.get('ecode')
        
        if not ecode_base64:
            return jsonify({'code': 400, 'error': '缺少ecode字段'}), 400
        
        if compile_type not in Config.COMPILE_TYPES:
            return jsonify({
                'code': 400,
                'error': f'不支持的编译类型: {compile_type}'
            }), 400
        
        try:
            ecode = base64.b64decode(ecode_base64)
        except Exception as e:
            return jsonify({'code': 400, 'error': f'base64解码失败: {str(e)}'}), 400
        
        file_hash = calculate_file_hash(ecode)
        
        if file_hash in tasks:
            task = tasks[file_hash]
            if task.state in ['Pending', 'Building']:
                return jsonify({
                    'code': 200,
                    'hash': file_hash,
                    'message': '任务已存在，正在处理中'
                })
        
        source_path = save_upload_file(ecode, file_hash)
        
        task = CompileTask(file_hash, compile_type)
        task.source_path = source_path
        tasks[file_hash] = task
        
        thread = threading.Thread(
            target=compile_e_source,
            args=(source_path, file_hash, task)
        )
        thread.daemon = True
        thread.start()
        
        logger.info(f"提交任务: {file_hash}, 类型: {compile_type}, 大小: {len(ecode)} bytes")
        
        return jsonify({
            'code': 200,
            'hash': file_hash
        })
        
    except Exception as e:
        logger.error(f"处理请求异常: {str(e)}")
        return jsonify({'code': 500, 'error': str(e)}), 500

@app.route('/State', methods=['POST'])
def get_state():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'code': 400, 'error': '请求体必须是JSON格式'}), 400
        
        file_hash = data.get('hash')
        if not file_hash:
            return jsonify({'code': 400, 'error': '缺少hash参数'}), 400
        
        task = tasks.get(file_hash)
        if not task:
            return jsonify({
                'code': 404,
                'state': 'NotFound'
            }), 404
        
        response = {
            'code': 200,
            'state': task.state,
            'message': task.message
        }
        
        if task.state == 'Error' and task.error_detail:
            response['error_detail'] = task.error_detail
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"查询状态异常: {str(e)}")
        return jsonify({'code': 500, 'error': str(e)}), 500

@app.route('/DownFile', methods=['POST'])
def download_file():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'code': 400, 'error': '请求体必须是JSON格式'}), 400
        
        file_hash = data.get('hash')
        if not file_hash:
            return jsonify({'code': 400, 'error': '缺少hash参数'}), 400
        
        task = tasks.get(file_hash)
        if not task:
            return jsonify({'code': 404, 'error': '未找到该任务'}), 404
        
        if task.state != 'OK':
            return jsonify({'code': 400, 'error': f'文件未准备好，状态: {task.state}'}), 400
        
        if not task.output_file or not os.path.exists(task.output_file):
            return jsonify({'code': 404, 'error': '输出文件不存在'}), 404
        
        if task.end_time:
            if (datetime.now() - task.end_time).total_seconds() > Config.EXPIRE_TIME:
                return jsonify({'code': 410, 'error': '文件已过期'}), 410
        
        return send_file(
            task.output_file,
            as_attachment=True,
            download_name=f"{file_hash}.exe",
            mimetype='application/octet-stream'
        )
        
    except Exception as e:
        logger.error(f"下载文件异常: {str(e)}")
        return jsonify({'code': 500, 'error': str(e)}), 500

@app.route('/ErrorLog', methods=['POST'])
def get_error_log():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'code': 400, 'error': '请求体必须是JSON格式'}), 400
        
        file_hash = data.get('hash')
        if not file_hash:
            return jsonify({'code': 400, 'error': '缺少hash参数'}), 400
        
        task = tasks.get(file_hash)
        if not task:
            return jsonify({'code': 404, 'error': '未找到该任务'}), 404
        
        error_log_path = os.path.join(Config.COMPILE_DIR, file_hash, "error.log")
        if os.path.exists(error_log_path):
            with open(error_log_path, 'r', encoding='gbk', errors='ignore') as f:
                content = f.read()
            return jsonify({
                'code': 200,
                'error_log': content
            })
        else:
            return jsonify({
                'code': 200,
                'error_log': task.error_detail or "无错误日志"
            })
        
    except Exception as e:
        logger.error(f"获取错误日志异常: {str(e)}")
        return jsonify({'code': 500, 'error': str(e)}), 500

@app.route('/Health', methods=['GET'])
def health():
    return jsonify({
        'status': 'OK',
        'timestamp': datetime.now().isoformat(),
        'active_tasks': len(tasks)
    })

@app.route('/ListTasks', methods=['GET'])
def list_tasks():
    task_list = []
    for file_hash, task in tasks.items():
        task_list.append({
            'hash': file_hash,
            'state': task.state,
            'compile_type': task.compile_type,
            'message': task.message,
            'start_time': task.start_time.isoformat() if task.start_time else None,
            'end_time': task.end_time.isoformat() if task.end_time else None
        })
    
    return jsonify({
        'code': 200,
        'total': len(task_list),
        'tasks': task_list
    })

# ==================== 启动服务 ====================
if __name__ == '__main__':
    if not os.path.exists(Config.ECL_EXE):
        logger.error(f"未找到编译工具: {Config.ECL_EXE}")
        logger.error("请将 ecl.exe 放置到服务目录")
        sys.exit(1)
    
    cleanup_thread = threading.Thread(target=cleanup_expired_files, daemon=True)
    cleanup_thread.start()
    
    logger.info(f"服务启动: http://{Config.HOST}:{Config.PORT}")
    logger.info(f"支持编译类型: {', '.join(Config.COMPILE_TYPES.keys())}")
    
    app.run(host=Config.HOST, port=Config.PORT, threaded=True, debug=False)