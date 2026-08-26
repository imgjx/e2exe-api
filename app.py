# -*- coding: utf-8 -*-
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
from datetime import datetime
from flask import Flask, request, jsonify, send_file

app = Flask(__name__)

# ==================== 配置 ====================
class Config:
    HOST = '0.0.0.0'
    PORT = 8800
    TEMP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'temp_debug')
    UPLOAD_DIR = os.path.join(TEMP_DIR, 'upload')
    COMPILE_DIR = os.path.join(TEMP_DIR, 'compile')
    OUTPUT_DIR = os.path.join(TEMP_DIR, 'output')
    ECL_EXE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ecl.exe')
    EXPIRE_TIME = 3600
    LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'debug.log')

# 初始化目录
for dir_name in [Config.UPLOAD_DIR, Config.COMPILE_DIR, Config.OUTPUT_DIR]:
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Config.LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logging.getLogger('werkzeug').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

tasks = {}

# ==================== 任务类 ====================
class CompileTask:
    def __init__(self, file_hash):
        self.file_hash = file_hash
        self.state = 'Pending'
        self.message = ''
        self.error_detail = ''
        self.return_code = None
        self.start_time = datetime.now()
        self.end_time = None
        self.output_file = None
        self.source_path = None
        self.compile_dir = None
        self.downloaded = False

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

def force_delete_file(file_path, max_retries=6, delay=5):
    if not file_path or not os.path.exists(file_path):
        return True
    for attempt in range(max_retries + 1):
        try:
            os.remove(file_path)
            return True
        except PermissionError:
            if attempt < max_retries:
                time.sleep(delay)
            else:
                try:
                    os.system(f'del /f /q "{file_path}" 2>nul')
                    if not os.path.exists(file_path):
                        return True
                    os.chmod(file_path, 0o777)
                    os.remove(file_path)
                    return True
                except:
                    return False
        except:
            if attempt < max_retries:
                time.sleep(delay)
            else:
                return False
    return False

def force_delete_directory(dir_path):
    if not dir_path or not os.path.exists(dir_path):
        return True
    try:
        shutil.rmtree(dir_path, ignore_errors=True)
        return True
    except:
        try:
            os.system(f'rmdir /s /q "{dir_path}" 2>nul')
            return True
        except:
            return False

def build_compile_args(options):
    args = []
    compile_type = options.get('type', 'normal')
    type_map = {
        'normal': [], 'static': ['-s'], 'independent': ['-d'],
        'blackmoon': ['-bm'], 'blackmoon_asm': ['-bm0'],
        'blackmoon_cpp': ['-bm1'], 'blackmoon_mfc': ['-bm2'],
        'package': ['-p'], 'debug': ['-r'],
    }
    if compile_type in type_map:
        args.extend(type_map[compile_type])
    
    if options.get('epath'): args.extend(['-epath', options['epath']])
    if options.get('password'): args.extend(['-pwd', options['password']])
    if options.get('bmcfg'): args.extend(['-bmcfg', options['bmcfg']])
    if options.get('bmdes'): args.extend(['-bmdes', options['bmdes']])
    if options.get('libs'):
        libs = options['libs']
        if isinstance(libs, list): libs = ';'.join(libs)
        args.extend(['-lib', libs])
    if options.get('show'): args.append('-show')
    if options.get('wait_key'): args.append('-k')
    if options.get('start_timeout'): args.extend(['-st', str(options['start_timeout'])])
    if options.get('compile_timeout'): args.extend(['-ct', str(options['compile_timeout'])])
    if options.get('quiet'): args.append('-q')
    if options.get('no_logo'): args.append('-nologo')
    if options.get('utf8'): args.append('-utf8')
    elif options.get('unicode'): args.append('-unicode')
    if options.get('version'): args.extend(['-ver', options['version']])
    
    if options.get('consts'):
        const_str = options['consts']
        if isinstance(const_str, dict):
            parts = []
            for k, v in const_str.items():
                if isinstance(v, str) and v.startswith('@'):
                    parts.append(f"{k}={v}")
                else:
                    parts.append(f'{k}="{v}"')
            const_str = ';'.join(parts)
        args.extend(['-const', const_str])
    
    if options.get('pictures'):
        pic_str = options['pictures']
        if isinstance(pic_str, dict):
            parts = []
            for k, v in pic_str.items():
                parts.append(f"{k}=@{v}" if not v.startswith('@') else f"{k}={v}")
            pic_str = ';'.join(parts)
        args.extend(['-pic', pic_str])
    
    if options.get('sounds'):
        sound_str = options['sounds']
        if isinstance(sound_str, dict):
            parts = []
            for k, v in sound_str.items():
                parts.append(f"{k}=@{v}" if not v.startswith('@') else f"{k}={v}")
            sound_str = ';'.join(parts)
        args.extend(['-sound', sound_str])
    
    sys_opts = {
        'fast_array': '-FastArry', 'no_fast_array': '-FastArry-',
        'check_dll_stack': '-CheckDllStack', 'no_check_dll_stack': '-CheckDllStack-',
        'check_loop': '-CheckLoop', 'no_check_loop': '-CheckLoop-',
        'windows6': '-Windows6.0', 'no_windows6': '-Windows6.0-',
        'uac': '-UAC', 'no_uac': '-UAC-',
        'out_lib': '-OutLib', 'no_out_lib': '-OutLib-',
        'check_name': '-CheckName', 'no_check_name': '-CheckName-',
    }
    for opt_name, opt_arg in sys_opts.items():
        if options.get(opt_name):
            args.append(opt_arg)
    
    if options.get('junk_level') is not None:
        args.extend(['-JunkLevel', str(options['junk_level'])])
    if options.get('upset'):
        args.extend(['-Upset', str(options['upset'])])
    if options.get('keep_e_config'):
        args.append('-KeepEConfig')
    if options.get('keep_lib_list'):
        args.append('-KeepLibList')
    
    link_params = {
        'linker': '-e_linker', 'output_file': '-e_output_file',
        'extra_args': '-e_extra_args', 'show_command_line': '-e_show_command_line',
        'retain_intermediate': '-e_retain_intermediate_files',
        'show_warning': '-e_show_warning',
    }
    for param_name, param_arg in link_params.items():
        if options.get(param_name):
            args.extend([param_arg, str(options[param_name])])
    
    return args

def compile_e_source(source_path, file_hash, task, options):
    try:
        task.state = 'Building'
        task.message = '编译中...'
        logger.info(f"编译: {file_hash[:16]}..., 类型: {options.get('type', 'normal')}")
        
        compile_dir = os.path.join(Config.COMPILE_DIR, file_hash)
        task.compile_dir = compile_dir
        if not os.path.exists(compile_dir):
            os.makedirs(compile_dir)
        
        output_path = os.path.join(compile_dir, f"{file_hash}.exe")
        
        cmd = [Config.ECL_EXE, 'make', source_path, output_path]
        cmd.extend(build_compile_args(options))
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,
            cwd=compile_dir,
            encoding='gbk',
            errors='ignore'
        )
        
        task.return_code = result.returncode
        
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            task.state = 'OK'
            task.message = '编译成功'
            final_output = os.path.join(Config.OUTPUT_DIR, f"{file_hash}.exe")
            shutil.copy2(output_path, final_output)
            task.output_file = final_output
            logger.info(f"编译成功: {file_hash[:16]}...")
        else:
            task.state = 'Error'
            task.message = '编译失败'
            task.error_detail = result.stderr or result.stdout or "未知错误"
            logger.error(f"编译失败: {file_hash[:16]}...")
            
    except subprocess.TimeoutExpired:
        task.state = 'Error'
        task.message = '编译超时'
        task.error_detail = '编译超过10分钟'
    except Exception as e:
        task.state = 'Error'
        task.message = f'编译异常: {str(e)}'
        task.error_detail = str(e)
    finally:
        task.end_time = datetime.now()
        if task.source_path and os.path.exists(task.source_path):
            force_delete_file(task.source_path)
        if task.compile_dir and os.path.exists(task.compile_dir):
            force_delete_directory(task.compile_dir)
        logger.info(f"编译完成: {file_hash[:16]}..., 状态: {task.state}")

def cleanup_expired_files():
    while True:
        try:
            now = datetime.now()
            expired = []
            for file_hash, task in tasks.items():
                if task.downloaded:
                    expired.append(file_hash)
                    continue
                if task.state == 'OK' and task.end_time:
                    if (now - task.end_time).total_seconds() > Config.EXPIRE_TIME:
                        expired.append(file_hash)
            for file_hash in expired:
                task = tasks[file_hash]
                if task.output_file and os.path.exists(task.output_file):
                    force_delete_file(task.output_file)
                del tasks[file_hash]
            time.sleep(60)
        except:
            time.sleep(60)

# ==================== API 接口 ====================

@app.route('/MakeE', methods=['POST'])
def make_e():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'code': 400, 'error': '请求体必须是JSON格式'}), 400
        
        ecode_base64 = data.get('ecode')
        if not ecode_base64:
            return jsonify({'code': 400, 'error': '缺少ecode字段'}), 400
        
        try:
            ecode = base64.b64decode(ecode_base64)
        except:
            return jsonify({'code': 400, 'error': 'base64解码失败'}), 400
        
        file_hash = calculate_file_hash(ecode)
        
        if file_hash in tasks:
            task = tasks[file_hash]
            if task.state in ['Pending', 'Building']:
                return jsonify({'code': 200, 'hash': file_hash, 'message': '任务已存在'})
        
        source_path = save_upload_file(ecode, file_hash)
        
        options = data.get('options', {})
        options['type'] = data.get('type', 'normal')
        
        task = CompileTask(file_hash)
        task.source_path = source_path
        tasks[file_hash] = task
        
        thread = threading.Thread(
            target=compile_e_source,
            args=(source_path, file_hash, task, options)
        )
        thread.daemon = True
        thread.start()
        
        logger.info(f"提交任务: {file_hash[:16]}..., 类型: {options['type']}")
        
        return jsonify({'code': 200, 'hash': file_hash})
        
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
            return jsonify({'code': 404, 'state': 'NotFound'}), 404
        
        response = {'code': 200, 'state': task.state, 'message': task.message}
        if task.error_detail:
            response['error_detail'] = task.error_detail
        if task.return_code is not None:
            response['return_code'] = task.return_code
        
        return jsonify(response)
        
    except Exception as e:
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
        
        if task.downloaded:
            return jsonify({'code': 410, 'error': '文件已下载'}), 410
        
        if task.end_time and (datetime.now() - task.end_time).total_seconds() > Config.EXPIRE_TIME:
            force_delete_file(task.output_file)
            del tasks[file_hash]
            return jsonify({'code': 410, 'error': '文件已过期'}), 410
        
        response = send_file(
            task.output_file,
            as_attachment=True,
            download_name=f"{file_hash}.exe",
            mimetype='application/octet-stream'
        )
        
        task.downloaded = True
        force_delete_file(task.output_file)
        del tasks[file_hash]
        logger.info(f"下载后删除: {file_hash[:16]}...")
        
        return response
        
    except Exception as e:
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
        
        return jsonify({'code': 200, 'error_log': task.error_detail or '无错误日志'})
        
    except Exception as e:
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
            'message': task.message,
            'downloaded': task.downloaded,
            'return_code': task.return_code
        })
    return jsonify({'code': 200, 'total': len(task_list), 'tasks': task_list})

if __name__ == '__main__':
    if not os.path.exists(Config.ECL_EXE):
        logger.error(f"未找到编译工具: {Config.ECL_EXE}")
        sys.exit(1)
    
    cleanup_thread = threading.Thread(target=cleanup_expired_files, daemon=True)
    cleanup_thread.start()
    
    logger.info(f"Debug服务启动: http://{Config.HOST}:{Config.PORT}")
    
    app.run(host=Config.HOST, port=Config.PORT, threaded=True, debug=False)
