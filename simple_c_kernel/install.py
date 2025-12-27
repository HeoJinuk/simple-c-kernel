import json
import os
import sys
import tempfile
from jupyter_client.kernelspec import KernelSpecManager

def main():
    # 1. kernel.json 내용 정의
    kernel_json = {
        "argv": [sys.executable, "-m", "simple_c_kernel.kernel", "-f", "{connection_file}"],
        "display_name": "Simple C Kernel",
        "language": "c",
        "interrupt_mode": "signal"
    }

    # 2. 임시 폴더(TemporaryDirectory) 생성
    with tempfile.TemporaryDirectory() as td:
        os.chmod(td, 0o755) # 권한 설정 (안전장치)
        
        # 3. 임시 폴더 안에 kernel.json 파일 생성
        with open(os.path.join(td, 'kernel.json'), 'w') as f:
            json.dump(kernel_json, f, indent=4)

        # 4. Jupyter에 커널 설치 요청 (source_dir로 임시 폴더 지정)
        kernel_spec_manager = KernelSpecManager()
        dest_dir = kernel_spec_manager.install_kernel_spec(
            source_dir=td,
            kernel_name="simple_c_kernel",
            user=True,
            replace=True
        )

    print(f"✅ Simple C Kernel 설치 완료! (위치: {dest_dir})")

if __name__ == '__main__':
    main()