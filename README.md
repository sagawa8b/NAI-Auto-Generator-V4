# NAI Auto Generator V4.5

### 📸 스크린샷
<img width="960" alt="image1" src="https://github.com/sagawa8b/NAI-Auto-Generator-V4/blob/main/nai_ui_01.png">
<img width="960" alt="image2" src="https://github.com/sagawa8b/NAI-Auto-Generator-V4/blob/main/nai_ui_02.png">
<img width="960" alt="image3" src="https://github.com/sagawa8b/NAI-Auto-Generator-V4/blob/main/nai_ui_03.png">

[![Version](https://img.shields.io/badge/version-4.5__2.6.04.28-blue.svg)](https://github.com/sagawa8b/NAI-Auto-Generator-V4/releases)
[![License](https://img.shields.io/badge/license-CC%20BY--NC%204.0-orange.svg)](LICENSE)
[![Downloads](https://img.shields.io/github/downloads/sagawa8b/NAI-Auto-Generator-V4/total.svg)](https://github.com/sagawa8b/NAI-Auto-Generator-V4/releases)

[한국어](#한국어) | [English](#english)

---

## 한국어

NovelAI의 이미지 생성 API를 활용한 데스크톱 애플리케이션입니다.  
NovelAI 웹 인터페이스에서 제공하지 않는 자동화 기능들을 제공하여, 더욱 효율적인 AI 이미지 생성을 가능하게 합니다.

### ✨ 주요 기능

- **🎨 V4.5 모델 완전 지원** - NovelAI Diffusion V4.5 Full 모델 지원
- **👤 고급 캐릭터 제어** - Character Prompts와 Character Reference를 통한 정밀한 캐릭터 생성
- **🖼️ 이미지 편집** - Image to Image, Enhancement, Inpainting 기능
- **🎭 Vibe Transfer** - 참조 이미지의 분위기와 스타일 적용
- **⚡ 자동화 기능** - 와일드카드, 배치 생성, 자동 생성, 일시정지/재개 등 워크플로우 최적화
- **🌍 다국어 지원** - 한국어, 영어, 일본어, 중국어 인터페이스
- **🔒 보안** - OS Keyring 기반 자격증명 저장, 로그 민감정보 자동 마스킹
- **✅ 입력 검증** - 생성 파라미터 자동 검증으로 오류 사전 방지
- **🏷️ 태그 자동완성** - Danbooru 태그 DB 기반 스마트 자동완성

### 🚀 빠른 시작

#### 1. 다운로드
[최신 릴리스](https://github.com/sagawa8b/NAI-Auto-Generator-V4/releases)에서 `NAI_Auto_Generator_V4.5_***.zip` 파일을 다운로드하세요.

#### 2. 실행
다운로드한 exe 파일을 실행합니다. (설치 불필요)

#### 3. 로그인
- `Files` → `Log in` 메뉴 선택
- NovelAI 계정 정보 입력
- (선택) `Auto login next time` 체크 시 자동 로그인

#### 4. 이미지 생성
1. **프롬프트 입력**: 생성하고 싶은 이미지 설명
   ```
   1girl, blue eyes, long hair, standing, outdoor, smile, masterpiece, best quality
   ```

2. **해상도 선택**: 드롭다운에서 원하는 크기 선택 (예: 1024×1024)

3. **Generate 버튼 클릭**: 이미지 생성 시작

#### 5. 고급 기능 사용
- **F1**: Character Reference 활성화 - 참조 이미지로 캐릭터 일관성 유지
- **F2**: Image to Image 활성화 - 기존 이미지 수정
- **F3**: Image Enhancement 활성화 - 이미지 업스케일 및 디테일 향상

### 📖 상세 매뉴얼

모든 기능에 대한 자세한 설명은 아래 매뉴얼을 참고하세요:

- **[📘 한국어 매뉴얼](MANUAL_KR.md)** - 전체 기능 설명 및 사용법
- **[📗 English Manual](MANUAL_EN.md)** - Complete guide


### 💻 시스템 요구사항

- **OS**: Windows 10 이상
- **NovelAI**: 활성화된 NovelAI 구독 (Opus 티어 권장)
- **ANLAS**: 일부 기능은 ANLAS 소모 (Large 해상도, Enhancement 등)

### 🛠️ 개발자용 - 소스에서 빌드

Python 환경에서 소스 코드로 실행하려면:

**요구사항**
- Python 3.10 이상
- PyQt5

**설치 및 실행**
```bash
# 저장소 클론
git clone https://github.com/sagawa8b/NAI-Auto-Generator-V4.git
cd NAI-Auto-Generator-V4

# 의존성 설치
pip install -r requirements.txt

# 실행
python gui.py
```

**테스트 실행**
```bash
pip install pytest
pytest tests/ -v
```

### 📁 프로젝트 구조

```
NAI-Auto-V4/
├── gui.py                   - 메인 윈도우 (Mixin 조합)
├── gui_init.py              - 위젯 초기화 & 레이아웃
├── gui_generation.py        - 이미지 생성 로직 (Mixin)
├── gui_enhance.py           - 이미지 향상 (Mixin)
├── gui_workers.py           - QThread 워커 클래스
├── gui_network.py           - 네트워크 모니터링 (Mixin)
├── gui_settings_io.py       - 설정 저장/로드 (Mixin)
├── gui_image_handlers.py    - 이미지 핸들링 (Mixin)
├── gui_credentials.py       - 자격증명 보안 저장
├── gui_dialog.py            - 다이얼로그 윈도우
├── gui_utils.py             - 유틸리티 함수
├── nai_generator.py         - NovelAI API 클라이언트
├── wildcard_applier.py      - 와일드카드 확장 엔진
├── completer.py             - 태그 자동완성
├── validation.py            - 입력 파라미터 검증
├── i18n_manager.py          - 다국어 관리
├── logger.py                - 로깅 시스템
├── consts.py                - 상수 & 기본값
├── languages/               - 번역 파일 (ko/en/ja/zh)
├── tests/                   - 단위 테스트
└── wildcards/               - 와일드카드 파일
```

### 📜 라이선스

이 프로젝트는 **Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)** 라이선스 하에 배포됩니다.

- ✅ 개인적 사용 가능
- ✅ 수정 및 재배포 가능 (출처 표시 필수)
- ❌ 상업적 사용 금지


### 🙏 크레딧

- **원작**: [DCP-arca/NAI-Auto-Generator](https://github.com/DCP-arca/NAI-Auto-Generator)
- **V4/V4.5 업데이트**: sagawa8b


### ⚠️ 면책 조항

본 애플리케이션은 제3자가 개발한 비공식 도구로, NovelAI에서 개발하거나 관리하지 않으며 NovelAI와는 무관합니다.

**This app is a third-party app that is not developed or managed by NovelAI and is unaffiliated with NovelAI.**

### 💬 지원 및 커뮤니티

- **Issues**: [GitHub Issues](https://github.com/sagawa8b/NAI-Auto-Generator-V4/issues)
- **Discussions**: [GitHub Discussions](https://github.com/sagawa8b/NAI-Auto-Generator-V4/discussions)


---

## English

This desktop application leverages NovelAI's image generation API.
It provides automated features not available in the NovelAI web interface, enabling more efficient AI image generation.

### ✨ Key Features

- **🎨 Full V4.5 Model Support** - NovelAI Diffusion V4.5 Full model support
- **👤 Advanced Character Control** - Precise character generation via Character Prompts and Character Reference
- **🖼️ Image Editing** - Image to Image, Enhancement, Inpainting features
- **🎭 Vibe Transfer** - Apply mood and style from reference images
- **⚡ Automation** - Wildcards, batch generation, auto-generation with pause/resume for workflow optimization
- **🌍 Multi-language Support** - Korean, English, Japanese, Chinese interface
- **🔒 Security** - OS Keyring credential storage, automatic log sensitive data masking
- **✅ Input Validation** - Automatic parameter validation to prevent errors
- **🏷️ Tag Autocomplete** - Smart autocomplete based on Danbooru tag database

### 🚀 Quick Start

#### 1. Download
Download `NAI_Auto_Generator_V4.5_***.zip` from [latest release](https://github.com/sagawa8b/NAI-Auto-Generator-V4/releases).

#### 2. Run
Execute the downloaded exe file. (No installation required)

#### 3. Login
- Select `Files` → `Log in` menu
- Enter your NovelAI account credentials
- (Optional) Check `Auto login next time` for automatic login

#### 4. Generate Images
1. **Enter Prompt**: Describe the image you want
   ```
   1girl, blue eyes, long hair, standing, outdoor, smile, masterpiece, best quality
   ```

2. **Select Resolution**: Choose size from dropdown (e.g., 1024×1024)

3. **Click Generate Button**: Start image generation

#### 5. Use Advanced Features
- **F1**: Activate Character Reference - Maintain character consistency with reference image
- **F2**: Activate Image to Image - Modify existing images
- **F3**: Activate Image Enhancement - Upscale and enhance image details

### 📖 Detailed Manual

For detailed explanations of all features, please refer to the manuals:

- **[📘 Korean Manual](MANUAL_KR.md)** - Complete feature guide
- **[📗 English Manual](MANUAL_EN.md)** - Complete guide

### 💻 System Requirements

- **OS**: Windows 10 or higher
- **NovelAI**: Active NovelAI subscription (Opus tier recommended)
- **ANLAS**: Some features consume ANLAS (Large resolution, Enhancement, etc.)

### 🛠️ For Developers - Build from Source

To run from source code in Python environment:

**Requirements**
- Python 3.10 or higher
- PyQt5

**Installation & Execution**
```bash
# Clone repository
git clone https://github.com/sagawa8b/NAI-Auto-Generator-V4.git
cd NAI-Auto-Generator-V4

# Install dependencies
pip install -r requirements.txt

# Run
python gui.py
```

**Run Tests**
```bash
pip install pytest
pytest tests/ -v
```

### 📁 Project Structure

```
NAI-Auto-V4/
├── gui.py                   - Main window (Mixin composition)
├── gui_init.py              - Widget initialization & layout
├── gui_generation.py        - Image generation logic (Mixin)
├── gui_enhance.py           - Image enhancement (Mixin)
├── gui_workers.py           - QThread worker classes
├── gui_network.py           - Network monitoring (Mixin)
├── gui_settings_io.py       - Settings save/load (Mixin)
├── gui_image_handlers.py    - Image handling (Mixin)
├── gui_credentials.py       - Credential secure storage
├── gui_dialog.py            - Dialog windows
├── gui_utils.py             - Utility functions
├── nai_generator.py         - NovelAI API client
├── wildcard_applier.py      - Wildcard expansion engine
├── completer.py             - Tag autocomplete
├── validation.py            - Input parameter validation
├── i18n_manager.py          - i18n manager
├── logger.py                - Logging system
├── consts.py                - Constants & defaults
├── languages/               - Translation files (ko/en/ja/zh)
├── tests/                   - Unit tests
└── wildcards/               - Wildcard files
```

### 📜 License

This project is distributed under the **Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)** license.

- ✅ Personal use allowed
- ✅ Modification and redistribution allowed (attribution required)
- ❌ Commercial use prohibited


### 🙏 Credits

- **Original**: [DCP-arca/NAI-Auto-Generator](https://github.com/DCP-arca/NAI-Auto-Generator)
- **V4/V4.5 Update**: sagawa8b


### ⚠️ Disclaimer

This application is an unofficial third-party tool not developed or managed by NovelAI and is unaffiliated with NovelAI.

### 💬 Support & Community

- **Issues**: [GitHub Issues](https://github.com/sagawa8b/NAI-Auto-Generator-V4/issues)
- **Discussions**: [GitHub Discussions](https://github.com/sagawa8b/NAI-Auto-Generator-V4/discussions)
