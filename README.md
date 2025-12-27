# Simple C Kernel for Jupyter

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)

**Jupyter Notebook에서 C언어를 완벽하게 학습할 수 있는 커널입니다.**

기존 C 커널들은 `scanf` 입력이 안 되거나, 한글이 깨지고, 설치가 복잡하다는 문제가 있었습니다.
**Simple C Kernel**은 이 모든 문제를 해결했습니다. OS에 상관없이 설치 한 번으로 실습 환경을 구축하세요.

---

## ✨ 주요 기능

* **크로스 플랫폼:** Windows, macOS, Linux(Ubuntu) 등 어디서든 동작합니다.
* **Jupyter에서 입력 지원:** `scanf`, `fgets` 실행 시 하단에 **입력창**이 즉시 뜹니다. (터미널과 동일한 경험)
* **무한 루프 방지:** 실수로 `while(1)`을 돌려도 주피터 상단의 **[⏹ 정지]** 버튼을 누르면 즉시 멈춥니다.
* **에러 컬러링:** 컴파일 에러가 발생하면 **빨간색/노란색**으로 강조되어 문제 원인을 찾기 쉽습니다.
* **매직 커맨드:** `//%cflags -lm` 등을 사용하여 수학 라이브러리나 컴파일 옵션을 자유롭게 추가할 수 있습니다.
---

## 🛠️ 설치 가이드 (Installation)

이 커널을 사용하려면 **Python**과 **C 컴파일러(GCC)**가 필요합니다.

### 1단계: Python 설치 확인

1. 터미널(CMD)을 열고 아래 명령어를 입력하세요.
```bash
python --version
```

2. 버전이 `3.8` 이상이라면 통과!
3. 에러가 난다면 [Python 공식 홈페이지](https://www.python.org/downloads/)에서 다운로드하여 설치하세요.
* ⚠️ **주의:** 설치 화면 하단의 **"Add Python to PATH"** 체크박스를 **반드시** 선택해야 합니다!



### 2단계: GCC 컴파일러 설치 (OS별 안내)

사용 중인 운영체제에 맞는 방법을 따라하세요.

#### Windows 사용자 (MinGW-w64)

1. **[WinLibs 다운로드 링크](https://winlibs.com/#download-release)**로 이동합니다.
2. 최신 버전의 **Zip archive** (UCRT runtime)을 다운로드합니다.
3. 다운로드한 압축 파일을 `C:\` 드라이브 최상단에 풉니다. (예: `C:\mingw64`)
4. **환경 변수 설정 (필수):**
* 윈도우 검색창에 **"시스템 환경 변수 편집"** 검색 -> 실행.
* **[환경 변수]** 버튼 클릭 -> **[시스템 변수]** 목록에서 **`Path`** 더블 클릭.
* **[새로 만들기]** 클릭 -> `C:\mingw64\bin` 입력 후 엔터.
* [확인]을 눌러 모든 창을 닫습니다.


5. **확인:** 새 CMD 창을 열고 `gcc --version` 입력 시 버전이 나오면 성공!

#### macOS 사용자

터미널을 열고 아래 명령어를 입력하여 Xcode Command Line Tools를 설치합니다.

```bash
xcode-select --install
```

#### Linux (Ubuntu) 사용자

터미널에서 아래 명령어로 GCC를 설치합니다.

```bash
sudo apt update
sudo apt install build-essential
```

### 3단계: 커널 설치 (마무리)

이 저장소(폴더)를 다운로드한 후, 폴더 안에서 터미널을 열고 아래 명령어 두 줄을 입력하면 끝입니다.

```bash
# 1. Jupyter 및 필수 라이브러리 설치
pip install -r requirements.txt

# 2. 커널 등록 (자동 설치 스크립트)
python install.py
```

"✅ 설치가 완료되었습니다!" 메시지가 나오면 모든 준비가 끝났습니다.

---

## 사용 방법

1. 터미널에 `jupyter notebook`을 입력하여 실행합니다.
2. 우측 상단 **[New]** 버튼을 누르고 **Simple C Kernel**을 선택합니다.
3. 이제 C 코드를 작성하고 실행(`Shift + Enter`)하세요!

### 예제 코드 따라해보기

#### 1. 입력 받기 (`scanf`)

```c
#include <stdio.h>

int main() {
    int age;
    printf("나이를 입력하세요: ");
    scanf("%d", &age); // 실행하면 하단에 입력창이 뜹니다!
    printf("당신의 나이는 %d세입니다.\n", age);
    return 0;
}
```

#### 2. 수학 함수 사용 (매직 커맨드)

`math.h` 등을 사용할 때는 코드 맨 윗줄에 `//%cflags` 옵션을 적어주세요.

```c
//%cflags -lm
#include <stdio.h>
#include <math.h>

int main() {
    printf("루트 2의 값: %f\n", sqrt(2.0));
    return 0;
}
```

#### 3. 에러 메시지 확인

일부러 문법을 틀려보세요. 에러 위치가 **빨간색**으로 표시됩니다.

```c
#include <stdio.h>
int main() {
    printf("세미콜론을 빼먹었어요") // Error!
    return 0;
}
```