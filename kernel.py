from ipykernel.kernelbase import Kernel
import subprocess
import os
import threading
import queue
import time
import uuid
import socket
from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.parse
import shutil
import tempfile
import re

# ==========================================
# 1. Configuration & Templates
# ==========================================

C_BOOTSTRAP_CODE = r"""
#include <stdio.h>
#include <stdlib.h>
#include <windows.h> 

/* 초기화: 버퍼링 끄기 및 한글 설정 */
void __attribute__((constructor)) _init_jupyter() { 
    setvbuf(stdout, NULL, _IONBF, 0); 
    setvbuf(stderr, NULL, _IONBF, 0);
    SetConsoleOutputCP(65001); 
}

/* 입력 트리거 함수: 파이썬에게 입력창 띄우라고 신호 보냄 */
static void _trigger_input() {
    printf("<<__REQ__>>");
    fflush(stdout);
}

/* 핵심: 주요 입력 함수 매크로 오버라이딩 (Hooking) 
   - 원래 함수가 실행되기 전에 _trigger_input()을 먼저 실행함
*/

// 1. scanf
#define scanf(...) (_trigger_input(), scanf(__VA_ARGS__))

// 2. getchar: 문자 하나 입력
#define getchar() (_trigger_input(), getchar())

// 3. fgets: 파일 입출력이 아닌 stdin(표준 입력)일 때만 트리거
#define fgets(s, n, stream) ((stream) == stdin ? _trigger_input() : (void)0, fgets(s, n, stream))

// 4. gets: 보안상 위험하지만 교육용으로 필요하다면 사용 (C11에서는 삭제됨, 경고 뜰 수 있음)
// #define gets(s) (_trigger_input(), gets(s)) 
"""

INPUT_HTML_TEMPLATE = """
<div class="lm-Widget jp-Stdin jp-OutputArea-output">
    <div class="lm-Widget jp-InputArea jp-Stdin-inputWrapper">
        <input type="text" id="box-{req_id}" class="jp-Stdin-input" autocomplete="off" placeholder="">
    </div>
    <script>
        (function() {{
            var box = document.getElementById("box-{req_id}");
            setTimeout(function() {{ box.focus(); }}, 50);
            box.addEventListener("keydown", function(e) {{
                if (e.key === "Enter") {{
                    e.preventDefault();
                    var val = box.value;
                    box.disabled = true;
                    fetch("http://localhost:{port}", {{
                        method: "POST", headers: {{"Content-Type": "application/x-www-form-urlencoded"}},
                        body: "id={req_id}&value=" + encodeURIComponent(val)
                    }}).catch(console.error);
                }}
            }});
        }})();
    </script>
</div>
"""

# ==========================================
# 2. Input Server Manager
# ==========================================

class ServerState:
    data = {}
    event = threading.Event()

class RequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            parsed = urllib.parse.parse_qs(post_data)
            req_id = parsed.get('id', [None])[0]
            value = parsed.get('value', [''])[0]
            if req_id:
                ServerState.data[req_id] = value
                ServerState.event.set()
            self.send_response(200); self.end_headers(); self.wfile.write(b"OK")
        except: self.send_response(500)
    def log_message(self, format, *args): pass 

class InputServer:
    def __init__(self):
        self.port = self._find_free_port()
        self.server = HTTPServer(('localhost', self.port), RequestHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def _find_free_port(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('localhost', 0))
            return s.getsockname()[1]

    def wait_for_input(self, req_id):
        ServerState.event.clear()
        while True:
            is_set = ServerState.event.wait(timeout=0.1)
            if is_set and req_id in ServerState.data:
                return ServerState.data.pop(req_id)
            if self._check_interrupt(): return None
        return None
    
    def _check_interrupt(self): return False # Placeholder
    def get_port(self): return self.port

# ==========================================
# 3. Main Kernel Class
# ==========================================

class SimpleCKernel(Kernel):
    implementation = 'SimpleCKernel'
    implementation_version = '1.2'
    language = 'c'
    language_version = 'C11'
    banner = "Simple C Kernel v1.2"
    language_info = {'name': 'c', 'mimetype': 'text/x-csrc', 'file_extension': '.c'}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.input_server = InputServer()
        self.cell_output_buffer = ""
        self.current_process = None

    def do_execute(self, code, silent, store_history=True, user_expressions=None, allow_stdin=True):
        self.cell_output_buffer = ""
        self.build_dir = tempfile.mkdtemp()
        src_file = os.path.join(self.build_dir, 'source.c')
        exe_file = os.path.join(self.build_dir, 'source.exe')

        try:
            # 실행 과정을 try로 감싸서 KeyboardInterrupt 감지
            if self._compile_code(code, src_file, exe_file):
                self._run_process(exe_file)
                
            return {'status': 'ok', 'execution_count': self.execution_count, 'payload': [], 'user_expressions': {}}

        except KeyboardInterrupt:
            # 주피터 'Stop' 버튼 클릭 시
            self._kill_process()
            self._print_stream("\n\033[31m> 사용자에 의해 실행이 중단되었습니다.\033[0m\n")
            self.send_response(self.iopub_socket, 'clear_output', {'wait': True})
            return {'status': 'abort', 'execution_count': self.execution_count}
        
        finally:
            self._kill_process()
            self._cleanup()

    def _compile_code(self, code, src_file, exe_file):
        # 코드에서 특별한 컴파일 옵션 추출
        extra_args = []
        for line in code.splitlines():
            if line.strip().startswith("//%cflags"):
                options = line.replace("//%cflags", "").strip().split()
                extra_args.extend(options)

        full_code = C_BOOTSTRAP_CODE + "\n" + code
        with open(src_file, 'w', encoding='utf-8') as f:
            f.write(full_code)

        try:
            cmd = ['gcc', src_file, '-o', exe_file, '-fexec-charset=UTF-8'] + extra_args
            # cwd(현재 작업 경로)를 임시 폴더로 지정하여 컴파일
            subprocess.check_output(
                cmd,
                stderr=subprocess.STDOUT, 
                encoding='utf-8',
                cwd=self.build_dir 
            )
            return True
        except subprocess.CalledProcessError as e:
            colored_error = self._colorize_gcc_output(e.output)
            self._print_stream(colored_error)
            return False
        except FileNotFoundError:
            self._print_stream("Error: GCC not found. Please install MinGW or GCC.")
            return False

    def _colorize_gcc_output(self, text):
        text = re.sub(r"(error:.*)", r"\033[1;31m\1\033[0m", text)
        text = re.sub(r"(warning:.*)", r"\033[1;33m\1\033[0m", text)
        text = re.sub(r"(note:.*)", r"\033[1;36m\1\033[0m", text)
        text = re.sub(r"(source\.c:\d+:\d+:)", r"\033[1m\1\033[0m", text)
        return text

    def _run_process(self, exe_file):
        if not os.path.exists(exe_file): return

        self.current_process = subprocess.Popen(
            [exe_file],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace',
            bufsize=0,
            cwd=self.build_dir
        )
        
        q = queue.Queue()
        def reader_thread(proc, out_q):
            while True:
                if proc.poll() is not None: break
                try:
                    char = proc.stdout.read(1)
                except ValueError: break 
                
                if not char: break
                out_q.put(char)
            try: proc.stdout.close()
            except: pass
        
        t = threading.Thread(target=reader_thread, args=(self.current_process, q), daemon=True)
        t.start()

        output_chunk = ""
        req_marker = "<<__REQ__>>"

        while t.is_alive() or not q.empty():
            try:
                char = q.get(timeout=0.05)
                output_chunk += char
                
                if req_marker in output_chunk:
                    pre_text = output_chunk.replace(req_marker, "")
                    self._print_stream(pre_text)
                    output_chunk = ""
                    
                    user_input = self._handle_input_request()
                    
                    try:
                        if self.current_process and self.current_process.stdin:
                            self.current_process.stdin.write(user_input + "\n")
                            self.current_process.stdin.flush()
                    except OSError: pass

                elif char == '\n' or len(output_chunk) > 200:
                    self._print_stream(output_chunk)
                    output_chunk = ""
                    
            except queue.Empty:
                if self.current_process.poll() is not None and q.empty():
                    break
                continue

        if output_chunk: self._print_stream(output_chunk)

    def _handle_input_request(self):
        req_id = str(uuid.uuid4())
        self._display_html_input(req_id)
        
        user_input = self.input_server.wait_for_input(req_id)
        if user_input is None: user_input = "0"

        self.send_response(self.iopub_socket, 'clear_output', {'wait': True})
        
        prefix = "\n" if self.cell_output_buffer and not self.cell_output_buffer.endswith('\n') else ""
        formatted_input = f"{prefix}{user_input}\n"
        
        self._print_stream(formatted_input)
        
        return user_input

    def _display_html_input(self, req_id):
        html_content = INPUT_HTML_TEMPLATE.format(req_id=req_id, port=self.input_server.get_port())
        self.send_response(self.iopub_socket, 'display_data', {'data': {'text/html': html_content}, 'metadata': {}})

    def _print_stream(self, text):
        self.cell_output_buffer += text
        self.send_response(self.iopub_socket, 'stream', {'name': 'stdout', 'text': text})
    
    def _kill_process(self):
        """무한 루프 탈출을 위한 강력한 프로세스 종료"""
        if self.current_process:
            try:
                self.current_process.terminate()
                try:
                    self.current_process.wait(timeout=0.2)
                except subprocess.TimeoutExpired:
                    # 좀비 프로세스 확인 사살
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(self.current_process.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except: pass
            finally: self.current_process = None

    def _cleanup(self):
        """임시 폴더 전체 삭제 (파일 잠금 시 에러 무시)"""
        if hasattr(self, 'build_dir') and os.path.exists(self.build_dir):
            # ignore_errors=True: 파일이 잠겨있어도 에러 없이 넘어감 (OS가 나중에 처리)
            shutil.rmtree(self.build_dir, ignore_errors=True)

if __name__ == '__main__':
    from ipykernel.kernelapp import IPKernelApp
    IPKernelApp.launch_instance(kernel_class=SimpleCKernel)