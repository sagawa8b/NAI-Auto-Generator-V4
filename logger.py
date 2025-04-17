import os
import logging
import datetime
import sys
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler

class NAILogger:
    """NAI Auto Generator 로그 시스템"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(NAILogger, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if NAILogger._initialized:
            return
            
        self.logger = logging.getLogger('nai_auto_generator')
        # 로거 설정
        self.logger.propagate = False  # 상위 로거로 전파 방지
        
        self.logger.setLevel(logging.INFO)  # 기본 로그 레벨
        
        # 기본 로그 설정
        self.log_folder = os.path.join(os.path.expanduser("~"), "NAI-Auto-Generator", "logs")
        self.debug_mode = False
        self.max_log_size = 10 * 1024 * 1024  # 10MB
        self.backup_count = 5
        
        # 포맷터 설정
        self.default_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        self.debug_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s - %(message)s'
        )
        
        # 콘솔 핸들러 생성
        self.console_handler = None
        
        # 파일 핸들러 (비활성화 상태로 시작)
        self.file_handler = None
        self.debug_file_handler = None
        
        NAILogger._initialized = True
    
    def initialize(self, log_folder=None, debug_mode=False):
        """로그 시스템 초기화"""
        # 기존 핸들러 제거
        if self.logger.handlers:
            for handler in self.logger.handlers[:]:
                self.logger.removeHandler(handler)
        
        # 로그 폴더 설정
        if log_folder:
            self.log_folder = log_folder
        
        # 로그 폴더 생성
        os.makedirs(self.log_folder, exist_ok=True)
        
        # 디버그 모드 설정
        self.debug_mode = debug_mode
        
        # 로그 레벨 설정
        self.logger.setLevel(logging.DEBUG if debug_mode else logging.INFO)
        
        # 콘솔 핸들러 설정
        self.console_handler = logging.StreamHandler()
        self.console_handler.setLevel(logging.INFO)  # 항상 INFO 이상으로 설정
        self.console_handler.setFormatter(self.default_formatter)  # 항상 기본 포맷터 사용
        
        # 기본 로그 파일 핸들러 설정
        log_file = os.path.join(self.log_folder, f"nai_generator_{datetime.datetime.now().strftime('%Y%m%d')}.log")
        self.file_handler = RotatingFileHandler(
            log_file, 
            maxBytes=self.max_log_size, 
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        self.file_handler.setLevel(logging.INFO)
        self.file_handler.setFormatter(self.default_formatter)
        self.logger.addHandler(self.file_handler)
        
        # 디버그 모드일 경우 디버그 로그 파일 핸들러 추가
        if debug_mode:
            debug_log_file = os.path.join(self.log_folder, f"nai_generator_debug_{datetime.datetime.now().strftime('%Y%m%d')}.log")
            self.debug_file_handler = RotatingFileHandler(
                debug_log_file, 
                maxBytes=self.max_log_size, 
                backupCount=self.backup_count,
                encoding='utf-8'
            )
            self.debug_file_handler.setLevel(logging.DEBUG)
            self.debug_file_handler.setFormatter(self.debug_formatter)
            self.logger.addHandler(self.debug_file_handler)
        
        self.logger.info(f"로그 시스템 초기화 - 모드: {'디버그' if debug_mode else '일반'}")
        if debug_mode:
            self.logger.debug(f"디버그 로그 활성화 - 위치: {self.log_folder}")
    
    def set_debug_mode(self, enabled=True):
        """디버그 모드 설정 변경"""
        if self.debug_mode == enabled:
            return
            
        self.initialize(self.log_folder, enabled)
    
    def get_logger(self):
        """로거 인스턴스 반환"""
        return self.logger

# 싱글톤 인스턴스 생성
nai_logger = NAILogger()

# 편의를 위한 함수들
def initialize_logger(log_folder=None, debug_mode=False):
    nai_logger.initialize(log_folder, debug_mode)

def get_logger():
    return nai_logger.get_logger()

def set_debug_mode(enabled=True):
    nai_logger.set_debug_mode(enabled)
    
# logger.py 수정

def set_log_level(level_name):
    """로그 수준 설정 (간소화됨)
    
    Args:
        level_name (str): 'normal' 또는 'detailed'
    """
    if level_name.lower() == 'normal':
        level = logging.INFO
    else:  # detailed
        level = logging.DEBUG
    
    # 로거 수준 설정
    nai_logger.logger.setLevel(level)
    
    # 핸들러 수준 설정
    if nai_logger.console_handler:
        # 콘솔은 항상 INFO 이상만 표시
        nai_logger.console_handler.setLevel(logging.INFO)
    
    # 파일 핸들러 설정
    if nai_logger.file_handler:
        nai_logger.file_handler.setLevel(logging.INFO)
    
    # 디버그 파일 핸들러 설정
    if nai_logger.debug_file_handler:
        nai_logger.debug_file_handler.setLevel(level)
    
    nai_logger.logger.info(f"로그 수준이 {level_name.upper()}로 변경되었습니다")
    

def log_network_error(error, severity="error", context=None):
    """네트워크 오류 전용 로깅 함수
    
    Args:
        error: 발생한 오류 또는 오류 메시지
        severity: 로그 수준 (debug/info/warning/error/critical)
        context: 오류 발생 컨텍스트 정보 (선택적)
    """
    logger = get_logger()
    
    # 오류 유형 식별 및 메시지 구성
    error_type = "Unknown"
    error_str = str(error)
    
    if "getaddrinfo failed" in error_str:
        error_type = "DNS_RESOLUTION_ERROR"
    elif "NameResolutionError" in error_str:
        error_type = "DNS_RESOLUTION_ERROR"
    elif "ConnectionRefusedError" in error_str:
        error_type = "CONNECTION_REFUSED"
    elif "SSLError" in error_str:
        error_type = "SSL_ERROR"
    elif "Timeout" in error_str:
        error_type = "TIMEOUT"
    
    # 컨텍스트 정보 추가
    context_info = f" [{context}]" if context else ""
    log_message = f"NETWORK_ERROR{context_info}: {error_type} - {error_str}"
    
    # 적절한 로그 수준으로 기록
    if severity == "debug":
        logger.debug(log_message)
    elif severity == "info":
        logger.info(log_message)
    elif severity == "warning":
        logger.warning(log_message)
    elif severity == "critical":
        logger.critical(log_message)
    else:
        logger.error(log_message)
    
    # 로그 파일 강제 플러시 (즉시 기록 보장)
    for handler in logger.handlers:
        handler.flush()