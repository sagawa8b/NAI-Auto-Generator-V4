import json
import os
from PyQt5.QtCore import QObject, pyqtSignal
from logger import get_logger

logger = get_logger()

class I18nManager(QObject):
    """다국어 지원 관리 클래스"""
    language_changed = pyqtSignal(str)  # 언어 변경 시그널
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(I18nManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        super().__init__()
        
        if hasattr(self, '_initialized'):
            return
                
        self._initialized = True
        self.current_language = "ko"  # 기본 언어: 한국어
        self.fallback_language = "ko"  # 폴백 언어
        self.translations = {}
        self.language_path = "./languages"
        self.available_languages = {}
        
        # 언어 파일 로드
        self.load_languages()
    
    def load_languages(self):
        """사용 가능한 모든 언어 파일 로드"""
        # 언어 폴더 생성
        os.makedirs(self.language_path, exist_ok=True)
        
        # JSON 파일 검색
        for filename in os.listdir(self.language_path):
            if filename.endswith('.json'):
                lang_code = filename[:-5]  # .json 제거
                filepath = os.path.join(self.language_path, filename)
                
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        lang_data = json.load(f)
                        
                    # 언어 데이터 저장
                    self.translations[lang_code] = lang_data.get("translations", {})
                    self.available_languages[lang_code] = lang_data.get("language_name", lang_code)
                    
                    logger.info(f"언어 파일 로드 완료: {filename}")
                    
                except Exception as e:
                    logger.error(f"언어 파일 로드 실패 ({filename}): {e}")
        
        # 기본 언어 파일이 없으면 생성
        if not self.translations:
            self.create_default_language_files()
            self.load_languages()  # 재귀적으로 다시 로드
    
    def create_default_language_files(self):
        """기본 언어 파일 생성 (한국어, 영어)"""
        # 한국어 파일
        ko_data = {
            "language_name": "한국어",
            "language_code": "ko",
            "translations": {
                # 메뉴
                "menu": {
                    "languages": "언어",
                    "file": "파일(Files)",
                    "open_file": "파일 열기(Open file)",
                    "save_settings": "설정 저장(Save Settings)",
                    "load_settings": "설정 불러오기(Load Settings)",
                    "login": "로그인(Log in)",
                    "option": "옵션(Option)",
                    "exit": "종료(Exit)",
                    "view": "보기",
                    "toggle_panel": "결과 패널 토글",
                    "etc": "기타(Etc)",
                    "about": "만든 이(About)"
                },
                
                # 상태바
                "statusbar": {
                    "before_login": "로그인이 필요합니다.",
                    "logged_in": "로그인 완료. 이제 생성이 가능합니다.",
                    "logging_in": "로그인 중...",
                    "generating": "이미지를 생성하는 중...",
                    "idle": "대기 중",
                    "load_complete": "파일 로드 완료",
                    "loading": "로드 중...",
                    "auto_generating_count": "연속 생성 중 ({}/{})",
                    "auto_generating_inf": "연속 생성 중",
                    "auto_wait": "다음 생성 대기 중... ({}초)",
                    "auto_error_wait": "에러 발생. {}초 후 재시도..."
                },
                
                # UI 요소
                "ui": {
                    "languages": "언어",
                    "prompt_group": "프롬프트",
                    "prompt": "프롬프트(Prompt):",
                    "negative_prompt": "네거티브 프롬프트(Negative Prompt):",
                    "prompt_placeholder": "이미지에 포함할 내용을 입력하세요...",
                    "negative_prompt_placeholder": "이미지에서 제외할 내용을 입력하세요...",
                    "character_prompts": "Character Prompts (V4)",
                    "character_prompt_info": "캐릭터 프롬프트: V4 모델에서는 이미지 내 여러 캐릭터를 개별적으로 지정할 수 있습니다.",
                    "ai_position": "AI 위치 선택",
                    "add_character": "+ 캐릭터 추가",
                    "clear_all": "모두 삭제",
                    "sync_width": "너비 동기화",
                    "character_n": "캐릭터 {}",
                    "character_prompt": "캐릭터 프롬프트:",
                    "position": "위치",
                    "negative_prompt_add": "네거티브 프롬프트 추가",
                    "reset_image_size": "이미지 크기 초기화",
                    "reset_image_size_tooltip": "결과 이미지 창을 기본 크기로 복원합니다"
                },
                
                # 이미지 옵션
                "image_options": {
                    "title": "Image Options",
                    "size": "Size:",
                    "width": "W:",
                    "height": "H:",
                    "random": "랜덤 (Random)",
                    "sampler": "Sampler:",
                    "steps": "Steps:",
                    "seed": "Seed:",
                    "fix": "고정 (Fix)",
                    "random_button": "랜덤 (Random)"
                },
                
                # 고급 설정
                "advanced": {
                    "title": "Advanced Settings",
                    "prompt_guidance": "Prompt Guidance:",
                    "prompt_guidance_rescale": "Prompt Guidance Rescale:",
                    "variety_plus": "Variety+",
                    "variety_plus_tooltip": "이미지 초기 생성 단계에서 CFG를 스킵하여 더 다양한 결과 생성",
                    "noise_schedule": "Noise Schedule:",
                    "legacy_mode": "Legacy Prompt Conditioning Mode"
                },
                
                # 생성 버튼
                "generate": {
                    "title": "Generate",
                    "once": "1회 생성",
                    "by_settings": "세팅별 연속 생성",
                    "auto": "연속 생성 (Auto)",
                    "stop": "생성 중지"
                },
                
                # 폴더
                "folders": {
                    "title": "폴더 열기",
                    "results": "생성 결과 폴더",
                    "wildcards": "와일드카드 폴더",
                    "settings": "세팅 파일 폴더"
                },
                
                # 결과
                "result": {
                    "image_title": "결과 이미지 (Result Image)",
                    "no_image": "결과 이미지가 없습니다",
                    "save_image": "이미지 저장 (Save Image)",
                    "prompt_title": "결과 프롬프트 (Result Prompt)"
                },
                
                # 대화상자
                "dialogs": {
                    "login_title": "NAI API 로그인",
                    "login_welcome": "안녕하세요!\\nNovel AI 계정으로 로그인해 주세요.",
                    "logged_in": "현재 Novel AI 계정으로 로그인되어 있습니다.",
                    "user": "사용자:",
                    "username": "아이디:",
                    "password": "암호:",
                    "auto_login": "다음에도 자동 로그인",
                    "login_button": "로그인하기",
                    "logout_button": "로그아웃하기",
                    "login_info": "※ 입력하신 아이디와 비밀번호는 Novel AI 서버에만 전송되며,\\n이 앱의 서버로 전송되지 않습니다.",
                    "logout_confirm": "정말 로그아웃 하시겠습니까?",
                    "logout_complete": "로그아웃 되었습니다.",
                    "login_success": "로그인에 성공했습니다.",
                    "login_failed": "로그인에 실패했습니다.\\n아이디와 비밀번호를 확인해주세요."
                },
                
                # 에러 메시지
                "errors": {
                    "title": "오류",
                    "warning": "경고",
                    "info": "알림",
                    "network_error": "인터넷 연결 문제: 서버에 연결할 수 없습니다. 네트워크 상태를 확인해주세요.",
                    "auth_error": "인증 오류: 로그인이 필요합니다.",
                    "payment_required": "결제 필요: Anlas가 부족합니다.",
                    "api_error": "API 요청 오류",
                    "generation_error": "이미지 생성 중 오류 발생",
                    "file_save_error": "파일 저장 중 오류 발생",
                    "file_load_error": "파일 로드 중 오류 발생"
                },
                
                # 연결 상태
                "connection": {
                    "server": "서버:",
                    "connected": "연결됨",
                    "disconnected": "연결 끊김",
                    "checking": "확인 중...",
                    "network_disconnected": "네트워크 연결 없음",
                    "network_restored": "인터넷 연결이 복구되었습니다."
                },
                
                # 기타
                "misc": {
                    "login_state": "로그인 상태",
                    "logged_in": "로그인 됨",
                    "not_logged_in": "로그인 필요",
                    "anlas": "Anlas:",
                    "unknown": "알 수 없음"
                }
            }
        }
        
        # 영어 파일
        en_data = {
            "language_name": "English",
            "language_code": "en",
            "translations": {
                # 메뉴
                "menu": {
                    "languages": "Languages",
                    "file": "Files",
                    "open_file": "Open file",
                    "save_settings": "Save Settings",
                    "load_settings": "Load Settings",
                    "login": "Log in",
                    "option": "Option",
                    "exit": "Exit",
                    "view": "View",
                    "toggle_panel": "Toggle Result Panel",
                    "etc": "Etc",
                    "about": "About"
                },
                
                # 상태바
                "statusbar": {
                    "before_login": "Login required.",
                    "logged_in": "Login complete. You can now generate images.",
                    "logging_in": "Logging in...",
                    "generating": "Generating image...",
                    "idle": "Idle",
                    "load_complete": "File load complete",
                    "loading": "Loading...",
                    "auto_generating_count": "Auto generating ({}/{})",
                    "auto_generating_inf": "Auto generating",
                    "auto_wait": "Waiting for next generation... ({} seconds)",
                    "auto_error_wait": "Error occurred. Retrying in {} seconds..."
                },
                
                # UI 요소
                "ui": {
                    "languages": "Languages",
                    "prompt_group": "Prompt",
                    "prompt": "Prompt:",
                    "negative_prompt": "Negative Prompt:",
                    "prompt_placeholder": "Enter what to include in the image...",
                    "negative_prompt_placeholder": "Enter what to exclude from the image...",
                    "character_prompts": "Character Prompts (V4)",
                    "character_prompt_info": "Character prompt: V4 models allow you to specify multiple characters individually in an image.",
                    "ai_position": "Select AI position",
                    "add_character": "+ Add character",
                    "clear_all": "Clear all",
                    "sync_width": "Sync width",
                    "character_n": "Character {}",
                    "character_prompt": "Character prompt:",
                    "position": "Position",
                    "negative_prompt_add": "Add Negative Prompt",
                    "reset_image_size": "Reset image size",
                    "reset_image_size_tooltip": "Restores the resulting image window to its default size"
                },
                
                # 이미지 옵션
                "image_options": {
                    "title": "Image Options",
                    "size": "Size:",
                    "width": "W:",
                    "height": "H:",
                    "random": "Random",
                    "sampler": "Sampler:",
                    "steps": "Steps:",
                    "seed": "Seed:",
                    "fix": "Fix",
                    "random_button": "Random"
                },
                
                # 고급 설정
                "advanced": {
                    "title": "Advanced Settings",
                    "prompt_guidance": "Prompt Guidance:",
                    "prompt_guidance_rescale": "Prompt Guidance Rescale:",
                    "variety_plus": "Variety+",
                    "variety_plus_tooltip": "Skip CFG in early generation stages for more diverse results",
                    "noise_schedule": "Noise Schedule:",
                    "legacy_mode": "Legacy Prompt Conditioning Mode"
                },
                
                # 생성 버튼
                "generate": {
                    "title": "Generate",
                    "once": "Generate Once",
                    "by_settings": "Generate by Settings",
                    "auto": "Auto Generate",
                    "stop": "Stop Generation"
                },
                
                # 폴더
                "folders": {
                    "title": "Open Folder",
                    "results": "Results Folder",
                    "wildcards": "Wildcards Folder",
                    "settings": "Settings Folder"
                },
                
                # 결과
                "result": {
                    "image_title": "Result Image",
                    "no_image": "No result image",
                    "save_image": "Save Image",
                    "prompt_title": "Result Prompt"
                },
                
                # 대화상자
                "dialogs": {
                    "login_title": "NAI API Login",
                    "login_welcome": "Hello!\\nPlease log in with your Novel AI account.",
                    "logged_in": "You are currently logged in to your Novel AI account.",
                    "user": "User:",
                    "username": "Username:",
                    "password": "Password:",
                    "auto_login": "Auto login next time",
                    "login_button": "Login",
                    "logout_button": "Logout",
                    "login_info": "※ Your username and password are sent only to Novel AI servers,\\nnot to this app's servers.",
                    "logout_confirm": "Are you sure you want to logout?",
                    "logout_complete": "Logout complete.",
                    "login_success": "Login successful.",
                    "login_failed": "Login failed.\\nPlease check your username and password."
                },
                
                # 에러 메시지
                "errors": {
                    "title": "Error",
                    "warning": "Warning",
                    "info": "Information",
                    "network_error": "Internet connection problem: Cannot connect to server. Please check your network status.",
                    "auth_error": "Authentication error: Login required.",
                    "payment_required": "Payment required: Insufficient Anlas.",
                    "api_error": "API request error",
                    "generation_error": "Error during image generation",
                    "file_save_error": "Error saving file",
                    "file_load_error": "Error loading file"
                },
                
                # 연결 상태
                "connection": {
                    "server": "Server:",
                    "connected": "Connected",
                    "disconnected": "Disconnected",
                    "checking": "Checking...",
                    "network_disconnected": "No network connection",
                    "network_restored": "Internet connection restored."
                },
                
                # 기타
                "misc": {
                    "login_state": "Login State",
                    "logged_in": "Logged In",
                    "not_logged_in": "Login Required",
                    "anlas": "Anlas:",
                    "unknown": "Unknown"
                }
            }
        }
        
        # 파일 저장
        try:
            with open(os.path.join(self.language_path, "ko.json"), 'w', encoding='utf-8') as f:
                json.dump(ko_data, f, ensure_ascii=False, indent=2)
                
            with open(os.path.join(self.language_path, "en.json"), 'w', encoding='utf-8') as f:
                json.dump(en_data, f, ensure_ascii=False, indent=2)
                
            logger.info("기본 언어 파일 생성 완료")
            
        except Exception as e:
            logger.error(f"기본 언어 파일 생성 실패: {e}")
    
    def set_language(self, language_code):
        if language_code in self.translations:
            self.current_language = language_code
            # 설정 저장 추가
            from PyQt5.QtCore import QSettings
            settings = QSettings("dcp_arca", "nag_gui")
            settings.setValue("language", language_code)
            
            self.language_changed.emit(language_code)
            return True
    
    def get_text(self, key_path, *args):
        """키 경로로 번역 텍스트 가져오기
        
        Args:
            key_path: 점(.)으로 구분된 키 경로 (예: "menu.file", "ui.prompt")
            *args: 텍스트 포맷팅 인자
        
        Returns:
            번역된 텍스트 또는 키 경로
        """
        # 현재 언어 번역 가져오기
        translations = self.translations.get(self.current_language, {})
        
        # 키 경로를 따라 값 찾기
        keys = key_path.split('.')
        value = translations
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                # 현재 언어에서 찾지 못하면 폴백 언어 시도
                value = self._get_fallback_text(key_path)
                break
        
        # 값이 문자열이 아니면 키 반환
        if not isinstance(value, str):
            logger.warning(f"번역 키를 찾을 수 없음: {key_path}")
            return key_path
        
        # 포맷팅 인자가 있으면 적용
        if args:
            try:
                return value.format(*args)
            except:
                return value
        
        return value
    
    def _get_fallback_text(self, key_path):
        """폴백 언어에서 텍스트 가져오기"""
        if self.current_language == self.fallback_language:
            return key_path
            
        translations = self.translations.get(self.fallback_language, {})
        keys = key_path.split('.')
        value = translations
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return key_path
                
        return value if isinstance(value, str) else key_path
    
    def get_available_languages(self):
        """사용 가능한 언어 목록 반환"""
        return self.available_languages
    
    def reload_languages(self):
        """언어 파일 다시 로드"""
        self.translations.clear()
        self.available_languages.clear()
        self.load_languages()

# 전역 인스턴스
i18n = I18nManager()

# 편의 함수
def tr(key_path, *args):
    """번역 함수 축약형"""
    return i18n.get_text(key_path, *args)
