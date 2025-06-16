import json
import sys
import os
import io
import zipfile
import time
import datetime
import random
import base64
import requests
import logging 
from io import BytesIO
from PIL import Image
from urllib import request

from i18n_manager import i18n, tr

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                            QPushButton, QPlainTextEdit, QScrollArea, QFrame, 
                            QGridLayout, QDialog, QCheckBox, QButtonGroup, QSizePolicy,
                            QMainWindow, QAction, QFileDialog, QMessageBox, QApplication,
                            QActionGroup)
from PyQt5.QtCore import (Qt, pyqtSignal, QObject, QTimer, QSettings, QPoint, QSize, 
                          QCoreApplication, QThread)
from PyQt5.QtGui import QColor, QPalette, QFont

from gui_init import init_main_widget
from gui_dialog import LoginDialog, OptionDialog, GenerateDialog, MiniUtilDialog, FileIODialog

from consts import COLOR, DEFAULT_PARAMS, DEFAULT_PATH, RESOLUTION_FAMILIY_MASK, RESOLUTION_FAMILIY, prettify_naidict, DEFAULT_TAGCOMPLETION_PATH

import naiinfo_getter
from nai_generator import NAIGenerator, NAIAction, NAISessionManager
from wildcard_applier import WildcardApplier
from danbooru_tagger import DanbooruTagger
from logger import get_logger
logger = get_logger()


TITLE_NAME = "NAI Auto Generator V4.5_2.5.06.15"
TOP_NAME = "dcp_arca"
APP_NAME = "nag_gui"

MAX_COUNT_FOR_WHILE = 10

#############################################

def resource_path(relative_path):
    """실행 파일 또는 Python 스크립트에서 리소스 경로 가져오기"""
    try:
        # PyInstaller 번들 실행 시
        base_path = sys._MEIPASS
    except Exception:
        # 일반 Python 실행 시
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# 디버깅용 로그 추가
logger.error(f"Current directory: {os.getcwd()}")
logger.error(f"MEIPASS exists: {'sys._MEIPASS' in dir(sys)}")
if 'sys._MEIPASS' in dir(sys):
    logger.error(f"MEIPASS path: {sys._MEIPASS}")
    
    
def create_folder_if_not_exists(foldersrc):
    if not os.path.exists(foldersrc):
        os.makedirs(foldersrc)


def prettify_dict(d):
    return json.dumps(d, sort_keys=True, indent=4)


def get_imgcount_from_foldersrc(foldersrc):
    return len([file for file in os.listdir(foldersrc) if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp'))])


def pick_imgsrc_from_foldersrc(foldersrc, index, sort_order):
    files = [file for file in os.listdir(foldersrc) if file.lower(
    ).endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp'))]

    is_reset = False
    if index != 0 and index % len(files) == 0:
        is_reset = True

    # 파일들을 정렬
    if sort_order == '오름차순':
        files.sort()
    elif sort_order == '내림차순':
        files.sort(reverse=True)
    elif sort_order == '랜덤':
        random.seed(random.randint(0, 1000000))
        random.shuffle(files)
        is_reset = False

    # 인덱스가 파일 개수를 초과하는 경우
    while index >= len(files):
        index -= len(files)

    # 정렬된 파일 리스트에서 인덱스에 해당하는 파일의 주소 반환
    return os.path.join(foldersrc, files[index]), is_reset


def strtobool(val):
    """Convert a string representation of truth to true (1) or false (0).
    True values are 'y', 'yes', 't', 'true', 'on', and '1'; false values
    are 'n', 'no', 'f', 'false', 'off', and '0'.  Raises ValueError if
    'val' is anything else.
    """
    if isinstance(val, bool):
        return val

    val = val.lower()
    if val in ('y', 'yes', 't', 'true', 'on', '1'):
        return True
    elif val in ('n', 'no', 'f', 'false', 'off', '0'):
        return False
    else:
        raise ValueError("invalid truth value %r" % (val,))


def pickedit_lessthan_str(original_str):
    try_count = 0

    edited_str = original_str
    while try_count < MAX_COUNT_FOR_WHILE:
        try_count += 1

        before_edit_str = edited_str
        pos_prev = 0
        while True:
            pos_r = edited_str.find(">", pos_prev + 1)
            if pos_r == -1:
                break

            pos_l = edited_str.rfind("<", pos_prev, pos_r)
            if pos_l != -1:
                left = edited_str[0:pos_l]
                center = edited_str[pos_l + 1:pos_r]
                right = edited_str[pos_r + 1:len(edited_str)]

                center_splited = center.split("|")
                center_picked = center_splited[random.randrange(
                    0, len(center_splited))]

                result_left = left + center_picked
                pos_prev = len(result_left)
                edited_str = result_left + right
            else:
                pos_prev = pos_r

        if before_edit_str == edited_str:
            break

    return edited_str


def create_windows_filepath(base_path, filename, extension, max_length=150):
    # 파일 이름으로 사용할 수 없는 문자 제거
    cleaned_filename = filename.replace("\n", "")
    cleaned_filename = cleaned_filename.replace("\\", "")

    invalid_chars = r'<>:"/\|?*'
    cleaned_filename = ''.join(
        char for char in cleaned_filename if char not in invalid_chars)

    # 파일 이름의 최대 길이 제한 (확장자 길이 고려)
    max_filename_length = max_length - len(base_path) - len(extension) - 1
    if max_filename_length < 5:
        return None
    cleaned_filename = cleaned_filename[:max_filename_length]

    # 경로, 파일 이름, 확장자 합치기
    filepath = os.path.join(base_path, cleaned_filename + extension)

    return filepath


def inject_imagetag(original_str, tagname, additional_str):
    result_str = original_str[:]

    tag_str_left = "@@" + tagname
    left_pos = original_str.find(tag_str_left)
    if left_pos != -1:
        right_pos = original_str.find("@@", left_pos + 1)
        except_tag_list = [x.strip() for x in original_str[left_pos +
                                                           len(tag_str_left) + 1:right_pos].split(",")]
        original_tag_list = [x.strip() for x in additional_str.split(',')]
        target_tag_list = [
            x for x in original_tag_list if x not in except_tag_list]

        result_str = original_str[0:left_pos] + ", ".join(target_tag_list) + \
            original_str[right_pos + 2:len(original_str)]

    return result_str


def get_filename_only(path):
    filename, _ = os.path.splitext(os.path.basename(path))
    return filename


def convert_qimage_to_imagedata(qimage):
    try:
        buf = QBuffer()
        buf.open(QBuffer.ReadWrite)
        qimage.save(buf, "PNG")
        pil_im = Image.open(io.BytesIO(buf.data()))

        buf = io.BytesIO()
        pil_im.save(buf, format='png', quality=100)
        return base64.b64encode(buf.getvalue()).decode("utf-8")
    except Exception as e:
        return ""


class NetworkMonitor(QObject):
    """네트워크 연결 상태를 모니터링하는 클래스"""
    connection_status_changed = pyqtSignal(bool, str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.url = "https://image.novelai.net"
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_connection)
        self.reconnect_timer = None  # 재연결 타이머 추가
        self.max_retries = 0  # 재시도 카운터
        
    def start_monitoring(self, interval=60000):  # 1분 간격으로 체크
        """모니터링 시작"""
        self.timer.start(interval)
        # 즉시 첫 번째 체크 실행
        QTimer.singleShot(100, self.check_connection)
        
    def stop_monitoring(self):
        """모니터링 중지"""
        self.timer.stop()
        if self.reconnect_timer and self.reconnect_timer.isActive():
            self.reconnect_timer.stop()
        
    def check_connection(self):
        """연결 상태 확인 - 향상된 오류 처리"""
        try:
            # DNS 확인 테스트 (socket 사용)
            import socket
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            
            # API 서버 확인
            import requests
            response = requests.get(self.url, timeout=5)
            if response.status_code == 200:
                self.connection_status_changed.emit(True, "연결됨")
                self.max_retries = 0  # 재시도 카운터 리셋
                
                # 재연결 타이머가 있다면 중지
                if self.reconnect_timer and self.reconnect_timer.isActive():
                    self.reconnect_timer.stop()
            else:
                self.connection_status_changed.emit(False, f"서버 응답 문제 (상태 코드: {response.status_code})")
                self.schedule_reconnect_check()
        except socket.error:
            # DNS/소켓 오류 - 네트워크 연결 문제
            self.connection_status_changed.emit(False, "네트워크 연결 없음: DNS 연결 실패")
            self.schedule_reconnect_check()
        except requests.exceptions.Timeout:
            self.connection_status_changed.emit(False, "서버 응답 시간 초과")
            self.schedule_reconnect_check()
        except requests.exceptions.ConnectionError as e:
            self.connection_status_changed.emit(False, f"연결 오류: {str(e)[:50]}...")
            self.schedule_reconnect_check()
        except Exception as e:
            self.connection_status_changed.emit(False, f"연결 확인 오류: {str(e)[:50]}...")
            self.schedule_reconnect_check()
    
    def schedule_reconnect_check(self):
        """재연결 시도 스케줄링 - 적응형 간격"""
        if not self.reconnect_timer:
            self.reconnect_timer = QTimer(self)
            self.reconnect_timer.setSingleShot(True)
            self.reconnect_timer.timeout.connect(self.check_connection)
        
        # 최대 10번까지 지수적으로 간격 증가
        self.max_retries = min(self.max_retries + 1, 10)
        interval = min(5000 * (2 ** self.max_retries), 300000)  # 최대 5분
        self.reconnect_timer.start(interval)


class NAIAutoGeneratorWindow(QMainWindow):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.palette = self.palette()
        self.is_initializing = True
        self.is_expand = True

        # 변수 및 창 초기화 (settings 초기화)
        self.init_variable()
        self.init_window()  # 여기서 self.settings가 초기화됨
        
        # 언어 초기화를 가장 먼저 실행
        saved_language = self.settings.value("language", "ko")
        i18n.set_language(saved_language)
        i18n.language_changed.connect(self.on_language_changed)
        
        # 나머지 초기화
        self.init_statusbar()
        self.init_menubar()        
        self.init_content()
        self.load_data()
        self.check_folders()
        
        # 기존 초기화 코드 후에 추가
        self.last_connected = True
        self.session_timer = None

        # 언어 초기화 (기존 코드의 적절한 위치에 추가)
        saved_language = self.settings.value("language", "ko")
        i18n.set_language(saved_language)
        
        # 언어 변경 시그널 연결
        i18n.language_changed.connect(self.on_language_changed)
        
        
        # 테마 적용
        self.apply_theme()
        
        # 라벨 생성 - 상태바에 추가
        self.label_connection_status = QLabel("서버: 확인 중...")
        self.statusBar().addPermanentWidget(self.label_connection_status)
        
        # 네트워크 모니터 설정
        self.network_monitor = NetworkMonitor(self)
        self.network_monitor.connection_status_changed.connect(self.update_connection_status)
        self.network_monitor.start_monitoring()
        # 즉시 첫 번째 연결 체크 실행 (추가)
        self.network_monitor.check_connection()
        self.start_session_monitoring()
        
        
        # 스플리터 상태 초기화
        QTimer.singleShot(100, self.initialize_splitter_state)
        
        self.is_initializing = False  # 초기화 완료 표시
        self.show()

        # NAI 관련 기능 초기화
        self.init_nai()
        self.init_wc()
        self.init_tagger()
        self.init_completion()
    
    
    def start_session_monitoring(self, interval=1800000):
        """주기적 세션 유효성 검사 및 갱신 - 향상된 모니터링"""
        self.session_timer = QTimer(self)
        self.session_timer.timeout.connect(self.check_and_refresh_session)
        self.session_timer.start(interval)
        
        # 상태 표시 타이머 (더 자주 업데이트)
        self.session_status_timer = QTimer(self)
        self.session_status_timer.timeout.connect(self.update_session_status)
        self.session_status_timer.start(60000)  # 1분마다 상태 업데이트
        
        # keepalive 타이머 (더 자주)
        self.keepalive_timer = QTimer(self)
        self.keepalive_timer.timeout.connect(self.keepalive)
        self.keepalive_timer.start(600000)  # 10분
        
        # 즉시 첫 검사 실행
        QTimer.singleShot(100, self.check_and_refresh_session)
    
    def check_and_refresh_session(self):
        """세션 상태 확인 및 필요시 갱신 - 개선된 복구 로직"""
        if hasattr(self, 'nai') and self.nai:
            try:
                # 세션 관리자를 통한 체계적 관리
                if hasattr(self, 'session_manager'):
                    session_health = self.session_manager.update()
                    
                    # 0.5 미만이면 즉시 강제 갱신
                    if session_health < 0.5:
                        logging.warning("세션 상태 불량, 강제 갱신 시도")
                        success = self.session_manager.force_refresh()
                        
                        if success:
                            self.set_statusbar_text("logged_in")
                            self.refresh_anlas()
                            logging.info("세션 강제 갱신 성공")
                        else:
                            # 실패 시 로그인 대화상자 표시 고려
                            self.set_statusbar_text("before_login")
                            logging.warning("세션 강제 갱신 실패, 사용자 개입 필요")
                            
                            # 자동 로그인 옵션이 켜져 있으면 자동 재로그인 시도
                            if self.settings.value("auto_login", False):
                                self.try_auto_relogin()
                else:
                    # 기존 방식 (단순 체크)
                    if not self.nai.check_logged_in():
                        success = self.nai.refresh_token()
                        if success:
                            self.set_statusbar_text("logged_in")
                            self.refresh_anlas()
                        else:
                            self.set_statusbar_text("before_login")
            except Exception as e:
                logging.error(f"세션 체크 오류: {e}")

    def keepalive(self):
        """세션 유지를 위한 경량 API 호출"""
        if hasattr(self, 'nai') and self.nai and self.nai.access_token:
            try:
                self.nai.get_anlas()  # 가벼운 API 호출
                logging.debug("Keepalive 성공")
            except Exception as e:
                logging.warning(f"Keepalive 실패: {e}")

    def update_session_status(self):
        """세션 상태 UI 업데이트"""
        if hasattr(self, 'session_manager') and hasattr(self, 'session_status_indicator'):
            try:
                status = self.session_manager.get_status_info()
                health = status["health"]
                
                # 상태에 따른 아이콘/색상 설정
                if health > 0.8:
                    color = "green"
                    icon = "●"  # 건강한 상태
                elif health > 0.5:
                    color = "orange"
                    icon = "◐"  # 주의 상태
                else:
                    color = "red"
                    icon = "○"  # 위험 상태
                
                # 이미지 카운트 정보
                img_count = status["image_count"]
                max_img = status["max_images"]
                percent = (img_count / max_img) * 100
                
                # 상태 텍스트 설정
                status_text = f"{icon} {percent:.0f}%"
                tooltip = f"세션 상태: {health:.1f}\n생성된 이미지: {img_count}/{max_img}\n연속 오류: {status['errors']}"
                
                self.session_status_indicator.setText(status_text)
                self.session_status_indicator.setStyleSheet(f"color: {color}; font-weight: bold;")
                self.session_status_indicator.setToolTip(tooltip)
                
            except Exception as e:
                logging.error(f"세션 상태 업데이트 오류: {e}")

    def try_auto_relogin(self):
        """자동 재로그인 시도"""
        if self.trying_auto_login:
            return  # 이미 시도 중이면 중복 방지
            
        logging.info("자동 재로그인 시도 중...")
        self.trying_auto_login = True
        
        access_token = self.settings.value("access_token", "")
        username = self.settings.value("username", "")
        password = self.settings.value("password", "")
        
        if not all([access_token, username, password]):
            logging.error("자동 로그인 실패: 자격 증명 부족")
            self.trying_auto_login = False
            return
            
        self.set_statusbar_text("LOGGINGIN")
        self.nai.access_token = access_token
        self.nai.username = username
        self.nai.password = password
        
        validate_thread = TokenValidateThread(self)
        validate_thread.validation_result.connect(self.on_login_result)
        validate_thread.start()
    
    
    def attempt_reconnect(self):
        """연결 복구 시도 - 네트워크 복원력 향상"""
        logging.info("연결 복구 시도 중...")
        
        # 먼저 인터넷 연결 확인
        try:
            import socket
            socket.create_connection(("www.google.com", 80), timeout=5)
            logging.info("인터넷 연결 확인됨")
        except:
            logging.error("인터넷 연결 없음")
            QTimer.singleShot(60000, self.attempt_reconnect)  # 1분 후 재시도
            return
        
        # 연결 상태 확인
        self.network_monitor.check_connection()
        
        # 로그인 상태 확인 및 복구
        if hasattr(self, 'nai') and self.nai:
            try:
                if not self.nai.check_logged_in():
                    success = self.nai.refresh_token()
                    if success:
                        logging.info("연결 복구 성공 - 재로그인됨")
                        self.set_statusbar_text("LOGINED")
                        self.refresh_anlas()
                        
                        # 세션 관리자 재설정
                        if hasattr(self, 'session_manager'):
                            self.session_manager.consecutive_errors = 0
                            self.session_manager.image_count_since_login = 0
                    else:
                        logging.warning("연결 복구 실패 - 재로그인 필요")
                        # 자동 로그인 옵션 확인 및 시도
                        if self.settings.value("auto_login", False):
                            self.try_auto_relogin()
            except Exception as e:
                logging.error(f"연결 복구 시도 중 오류: {e}")
                QTimer.singleShot(30000, self.attempt_reconnect)  # 30초 후 재시도
    
    
    def update_connection_status(self, is_connected, message):
        """네트워크 연결 상태 업데이트 - 개선된 버전"""
        if is_connected:
            self.label_connection_status.setText("서버: 연결됨")
            self.label_connection_status.setStyleSheet("color: green;")
        else:
            self.label_connection_status.setText(f"서버: {message}")
            self.label_connection_status.setStyleSheet("color: red;")
            logger.error(f"네트워크 연결 문제: {message}")
            
            # 추가: 연결 상태 변경 감지 및 복구 시도
            if hasattr(self, 'last_connected') and self.last_connected:
                logging.warning("네트워크 연결 끊김 감지")
                self.show_network_error_notification(message)
                
                # 즉시 세션 상태 업데이트
                if hasattr(self, 'nai') and hasattr(self.nai, 'session_manager'):
                    self.nai.session_manager.network_available = False
        
        # 이전 상태가 끊김에서 연결됨으로 변경된 경우
        if is_connected and hasattr(self, 'last_connected') and not self.last_connected:
            logging.info("네트워크 연결 복구 감지")
            self.show_network_restored_notification()
            
            # 연결 복구 시 세션 검증
            if hasattr(self, 'nai') and hasattr(self.nai, 'session_manager'):
                self.nai.session_manager.network_available = True
                # 5초 후 세션 상태 확인 (즉시 하면 불안정할 수 있음)
                QTimer.singleShot(5000, self.nai.session_manager.perform_session_check)
        
        if hasattr(self, 'last_connected'):
            self.last_connected = is_connected

    def show_network_error_notification(self, error_message):
        """네트워크 오류 알림 표시"""
        from PyQt5.QtWidgets import QMessageBox
        
        # 중복 알림 방지를 위한 플래그
        if not hasattr(self, 'network_error_shown') or not self.network_error_shown:
            self.network_error_shown = True
            
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("네트워크 연결 오류")
            msg.setText("인터넷 연결이 끊어졌습니다.")
            msg.setInformativeText(f"세부 정보: {error_message}\n\n연결이 복구되면 자동으로 재시도합니다.")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.setDefaultButton(QMessageBox.Ok)
            
            # 비동기적으로 표시 (UI 블로킹 방지)
            QTimer.singleShot(100, lambda: msg.exec_())

    def show_network_restored_notification(self):
        """네트워크 복구 알림 표시"""
        from PyQt5.QtWidgets import QMessageBox
        
        # 오류 표시 플래그 리셋
        self.network_error_shown = False
        
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("네트워크 연결 복구")
        msg.setText("인터넷 연결이 복구되었습니다.")
        msg.setInformativeText("이제 이미지 생성을 계속할 수 있습니다.")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.setDefaultButton(QMessageBox.Ok)
        
        # 비동기적으로 표시 (UI 블로킹 방지)
        QTimer.singleShot(100, lambda: msg.exec_())
    
    def create_collapsible_section(self, title, content_widget):
        """접기/펼치기 가능한 섹션 위젯 생성"""
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 헤더 (클릭 가능)
        header = QPushButton(f"▼ {title}")
        header.setStyleSheet("text-align: left; padding: 5px;")
        
        # 내용물
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.addWidget(content_widget)
        
        # 레이아웃에 추가
        layout.addWidget(header)
        layout.addWidget(content)
        
        # 접기/펼치기 토글 기능
        header.clicked.connect(lambda: self.toggle_section(header, content))
        
        return section
        
    def toggle_section(self, header, content):
        """섹션 접기/펼치기 토글"""
        if content.isVisible():
            content.hide()
            header.setText(header.text().replace("▼", "▶"))
        else:
            content.show()
            header.setText(header.text().replace("▶", "▼"))
    
    def resizeEvent(self, event):
        """윈도우 크기 변경 이벤트 처리 - 반응형 UI 구현"""
        super().resizeEvent(event)
        
        # 화면 크기에 따라 UI 조정
        width = event.size().width()
        height = event.size().height()
        
        # 화면 크기별 조정
        if width < 800:  # 좁은 화면
            self.adjust_for_small_screen()
        elif width < 1200:  # 중간 화면
            self.adjust_for_medium_screen()
        else:  # 넓은 화면
            self.adjust_for_large_screen()
        
        # 화면 비율에 따른 프롬프트 스플리터 비율 조정
        if hasattr(self, 'prompt_splitter'):
            aspect_ratio = width / height if height > 0 else 1.0
            
            if aspect_ratio < 1.0:  # 세로 형태 화면
                # 프롬프트와 네거티브 프롬프트의 비율 조정 (70:30)
                total = sum(self.prompt_splitter.sizes())
                self.prompt_splitter.setSizes([int(total * 0.7), int(total * 0.3)])
            elif aspect_ratio > 1.5:  # 매우 넓은 화면
                # 프롬프트와 네거티브 프롬프트의 비율 조정 (50:50)
                total = sum(self.prompt_splitter.sizes())
                self.prompt_splitter.setSizes([int(total * 0.5), int(total * 0.5)])
            else:  # 일반 비율 화면
                # 프롬프트와 네거티브 프롬프트의 비율 조정 (60:40)
                total = sum(self.prompt_splitter.sizes())
                self.prompt_splitter.setSizes([int(total * 0.6), int(total * 0.4)])
                
        # 이미지 크기 조정
        QTimer.singleShot(100, self.image_result.refresh_size)


    # 기존 adjust_for_small_screen 메서드를 대체하는 코드
    def adjust_for_small_screen(self):
        """좁은 화면에 맞게 UI 조정"""
                
                
        # 버튼 크기 조정
        for btn in [self.button_generate_once, self.button_generate_sett, self.button_generate_auto]:
            btn.setMinimumWidth(100)
            # 짧은 텍스트만 표시
            if hasattr(btn, 'original_text'):
                # 원래 텍스트가 저장되어 있으면 사용
                original_text = btn.original_text
            else:
                # 원래 텍스트 저장
                original_text = btn.text()
                setattr(btn, 'original_text', original_text)
            
            if '(' in original_text:
                btn.setText(original_text.split('(')[0])

    def adjust_for_medium_screen(self):
        """중간 크기 화면에 맞게 UI 조정 (800px <= 너비 < 1200px)"""
        
        
        # 버튼 기본 설정으로 복원
        for btn in [self.button_generate_once, self.button_generate_sett, self.button_generate_auto]:
            btn.setMinimumWidth(120)
            if hasattr(btn, 'original_text'):
                btn.setText(btn.original_text)

    def adjust_for_large_screen(self):
        """큰 화면에 맞게 UI 조정 (너비 >= 1200px)"""
        
        # 버튼 기본 설정으로 복원
        for btn in [self.button_generate_once, self.button_generate_sett, self.button_generate_auto]:
            btn.setMinimumWidth(150)
            if hasattr(btn, 'original_text'):
                btn.setText(btn.original_text)

    def apply_emphasis_settings(self):
        """프롬프트 에디터에 가중치 하이라이트 설정 적용"""
        try:
            # 설정 불러오기
            highlight_enabled = self.settings.value("emphasis_highlight", True, type=bool)
            high_color = QColor(self.settings.value("high_emphasis_color", "#6495ED"))
            low_color = QColor(self.settings.value("low_emphasis_color", "#A9A9A9"))
            
            # 프롬프트 에디터에 설정 적용
            for editor_key in ["prompt", "negative_prompt"]:
                if editor_key in self.dict_ui_settings:
                    editor = self.dict_ui_settings[editor_key]
                    if hasattr(editor, "setEmphasisHighlighting"):
                        editor.setEmphasisHighlighting(highlight_enabled)
                        editor.setEmphasisColors({
                            "high": high_color,
                            "low": low_color
                        })
                        # 변경 내용을 즉시 적용하기 위해 수동으로 한 번 강조 실행
                        if hasattr(editor, "highlightSyntax"):
                            editor.highlightSyntax()
                        logger.debug(f"{editor_key} 에디터에 가중치 하이라이트 설정 적용")
            
            # 캐릭터 프롬프트 에디터에도 적용
            if hasattr(self, 'character_prompts_container'):
                for widget in self.character_prompts_container.character_widgets:
                    for editor in [widget.prompt_edit, widget.neg_prompt_edit]:
                        if hasattr(editor, "setEmphasisHighlighting"):
                            editor.setEmphasisHighlighting(highlight_enabled)
                            editor.setEmphasisColors({
                                "high": high_color,
                                "low": low_color
                            })
                            # 변경 내용을 즉시 적용하기 위해 수동으로 한 번 강조 실행
                            if hasattr(editor, "highlightSyntax"):
                                editor.highlightSyntax()
                logger.debug("캐릭터 프롬프트 에디터에 가중치 하이라이트 설정 적용")
        
        except Exception as e:
            logger.error(f"가중치 하이라이트 설정 적용 중 오류: {e}")
        
    def setup_layout_modes(self):
        """다양한 레이아웃 모드 설정"""
        # 메뉴에 레이아웃 모드 선택 추가
        layouts_menu = self.menuBar().addMenu("레이아웃")
        
        horizontal_action = QAction("가로 분할 모드", self)
        horizontal_action.triggered.connect(lambda: self.change_layout_mode("horizontal"))
        layouts_menu.addAction(horizontal_action)
        
        vertical_action = QAction("세로 분할 모드", self)
        vertical_action.triggered.connect(lambda: self.change_layout_mode("vertical"))
        layouts_menu.addAction(vertical_action)
        
        tabbed_action = QAction("탭 모드", self)
        tabbed_action.triggered.connect(lambda: self.change_layout_mode("tabbed"))
        layouts_menu.addAction(tabbed_action)

    def change_layout_mode(self, mode):
        """레이아웃 모드 변경"""
        # 현재 위젯 추출
        left_widget = self.main_splitter.widget(0)
        right_widget = self.main_splitter.widget(1)
        
        # 기존 레이아웃 제거
        self.main_splitter.setParent(None)
        
        if mode == "horizontal":  # 가로 분할 (기본)
            self.main_splitter = QSplitter(Qt.Horizontal)
            self.main_splitter.addWidget(left_widget)
            self.main_splitter.addWidget(right_widget)
            
        elif mode == "vertical":  # 세로 분할
            self.main_splitter = QSplitter(Qt.Vertical)
            self.main_splitter.addWidget(left_widget)
            self.main_splitter.addWidget(right_widget)
            
        elif mode == "tabbed":  # 탭 모드
            tab_widget = QTabWidget()
            tab_widget.addTab(left_widget, "설정")
            tab_widget.addTab(right_widget, "결과")
            
            self.main_splitter = QSplitter()  # 더미 스플리터
            self.main_splitter.addWidget(tab_widget)
        
        # 새 레이아웃 적용
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.main_splitter)
        
        # 중앙 위젯에 설정
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
    
    
    def initialize_splitter_state(self):
        # 최소 사이즈 설정으로 컨텐츠가 너무 작아지지 않도록 함
        self.main_splitter.setChildrenCollapsible(False)
        self.main_splitter.setHandleWidth(6)  # 구분선 두께 증가
        
        # 좌우 패널 최소 너비 설정
        left_widget = self.main_splitter.widget(0)
        left_widget.setMinimumWidth(350)  # 좌측 패널 최소 너비
        
        right_widget = self.main_splitter.widget(1)
        right_widget.setMinimumWidth(300)  # 우측 패널 최소 너비
        
        saved_state = self.settings.value("splitterSizes")
        if saved_state:
            try:
                self.main_splitter.restoreState(saved_state)
                # Ensure right panel visibility matches is_expand state
                right_visible = sum(self.main_splitter.sizes()[1:]) > 0
                self.is_expand = right_visible
            except Exception as e:
                logger.error(f"Error restoring splitter: {e}")
                self.set_default_splitter()
        else:
            self.set_default_splitter()
        
        self.update_expand_button()

    def set_default_splitter(self):
        total = self.main_splitter.width()
        self.main_splitter.setSizes([int(total*0.6), int(total*0.4)])
        
    def apply_theme(self):
        """현재 테마 설정을 적용합니다."""
        theme_mode = self.settings.value("theme_mode", "기본 테마 (System Default)")
        accent_color = self.settings.value("accent_color", "#2196F3")
        font_size = int(self.settings.value("nag_font_size", 18))  # 문자열에서 정수로 변환
        
        # 폰트 크기 적용을 명시적으로 포함한 스타일시트
        base_style = f"""
        * {{
            font-size: {font_size}px;
        }}
        """
        
        # 어두운 테마일 경우 추가 스타일
        if "어두운" in theme_mode:
            style = base_style + """
            QWidget {
                background-color: #2D2D2D;
                color: #FFFFFF;
            }
            QLineEdit, QTextEdit, QPlainTextEdit {
                background-color: #404040;
                color: #FFFFFF;
                border: 1px solid #555555;
            }
            /* 나머지 어두운 테마 스타일 */
            """
            self.app.setStyleSheet(style)
            
            # 팔레트 설정 (기존 코드)
        else:
            # 기본 테마에도 폰트 크기는 적용
            self.app.setStyleSheet(base_style)
            self.app.setPalette(self.palette)

    def init_variable(self):
        self.trying_auto_login = False
        self.autogenerate_thread = None
        self.list_settings_batch_target = []
        self.index_settings_batch_target = -1
        self.dict_img_batch_target = {
            "img2img_foldersrc": "",
            "img2img_index": -1,
            "i2i_last_src": "",
            "i2i_last_dst": "",
            "vibe_foldersrc": "",
            "vibe_index": -1,
            "vibe_last_src": "",
            "vibe_last_dst": "",
        }
        # UI 요소를 저장할 딕셔너리 초기화
        self.dict_ui_settings = {}
        # is_expand 변수는 여기서 초기화하지 않음

    def init_window(self):
        self.setWindowTitle(TITLE_NAME)
        self.settings = QSettings(TOP_NAME, APP_NAME)
        
        # 설정에서 위치 정보 불러오기 (기본값: 화면 중앙)
        if self.settings.contains("pos"):
            saved_pos = self.settings.value("pos")
            self.move(saved_pos)
        else:
            # 화면 중앙에 배치
            screen_geometry = QApplication.desktop().availableGeometry()
            self.move(screen_geometry.center() - self.rect().center())
        
        # 설정에서 크기 정보 불러오기 (기본값: HD 해상도)
        default_size = QSize(1280, 720)  # HD 해상도 기본값
        
        if self.settings.contains("size"):
            saved_size = self.settings.value("size")
            
            # QSize 객체인지 확인 (타입 호환성 검사)
            if isinstance(saved_size, QSize):
                self.resize(saved_size)
            else:
                # 저장된 값이 QSize가 아니면 기본값 사용
                print("저장된 크기 정보가 유효하지 않습니다. 기본 HD 해상도를 사용합니다.")
                self.resize(default_size)
        else:
            # 설정 없으면 기본값 사용
            self.resize(default_size)
        
        # 스플리터 크기 정보 초기화
        self.settings.setValue("splitterSizes", None)
        
        # 드래그 앤 드롭 허용
        self.setAcceptDrops(True)

    def init_statusbar(self):
        statusbar = self.statusBar()
        statusbar.messageChanged.connect(self.on_statusbar_message_changed)
        self.set_statusbar_text("BEFORE_LOGIN")

    def init_menubar(self):
        # 기존 액션들을 번역된 텍스트로 변경
        openAction = QAction(tr('menu.open_file'), self)
        openAction.setShortcut('Ctrl+O')
        openAction.triggered.connect(lambda: self.show_file_dialog("file"))

        saveSettingsAction = QAction(tr('menu.save_settings'), self)
        saveSettingsAction.setShortcut('Ctrl+S')
        saveSettingsAction.triggered.connect(self.on_click_save_settings)
        
        # 설정 불러오기 액션 추가
        loadSettingsAction = QAction('설정 불러오기(Load Settings)', self)
        loadSettingsAction.setShortcut('Ctrl+L')
        loadSettingsAction.triggered.connect(self.on_click_load_settings)

        loginAction = QAction('로그인(Log in)', self)
        loginAction.setShortcut('Ctrl+I')
        loginAction.triggered.connect(self.show_login_dialog)

        optionAction = QAction('옵션(Option)', self)
        optionAction.setShortcut('Ctrl+U')
        optionAction.triggered.connect(self.show_option_dialog)

        exitAction = QAction('종료(Exit)', self)
        exitAction.setShortcut('Ctrl+W')
        exitAction.triggered.connect(self.quit_app)

        aboutAction = QAction('만든 이(About)', self)
        aboutAction.triggered.connect(self.show_about_dialog)

        getterAction = QAction('이미지 정보 확인기(Info Getter)', self)
        getterAction.setShortcut('Ctrl+I')
        getterAction.triggered.connect(self.on_click_getter)

        taggerAction = QAction('태그 확인기(Danbooru Tagger)', self)
        taggerAction.setShortcut('Ctrl+T')
        taggerAction.triggered.connect(self.on_click_tagger)
        
        # 결과 패널 토글 액션
        togglePanelAction = QAction('결과 패널 토글', self)
        togglePanelAction.setShortcut('F11')
        togglePanelAction.triggered.connect(self.on_click_expand)
        
        # 메뉴 생성
        menubar = self.menuBar()
        menubar.setNativeMenuBar(False)
        
        
        # 기존 메뉴 추가
        filemenu_file = menubar.addMenu(tr('menu.file')) 
        filemenu_file.addAction(openAction)
        filemenu_file.addAction(saveSettingsAction)
        filemenu_file.addAction(loadSettingsAction)
        filemenu_file.addSeparator()  # 구분선 추가
        filemenu_file.addAction(loginAction)
        filemenu_file.addAction(optionAction)
        filemenu_file.addAction(exitAction)
        
        #filemenu_tool = menubar.addMenu(tr('menu.tools'))
        #filemenu_tool.addAction(getterAction)
        #filemenu_tool.addAction(taggerAction)
        
        # 보기 메뉴 추가
        viewMenu = menubar.addMenu(tr('menu.view'))
        viewMenu.addAction(togglePanelAction)
        
        filemenu_etc = menubar.addMenu(tr('menu.etc'))
        filemenu_etc.addAction(aboutAction)
        
        # 언어 메뉴 추가
        self.lang_menu = menubar.addMenu(tr('menu.languages', 'Languages'))
        self.setup_language_menu()

    def setup_language_menu(self):
        """언어 선택 메뉴 설정"""
        self.lang_menu.clear()
        
        # 언어 액션 그룹
        lang_group = QActionGroup(self)
        
        for lang_code, lang_name in i18n.get_available_languages().items():
            action = QAction(lang_name, self)
            action.setCheckable(True)
            action.setData(lang_code)
            
            # 현재 언어 체크
            if lang_code == i18n.current_language:
                action.setChecked(True)
            
            # 언어 변경 연결
            action.triggered.connect(lambda checked, code=lang_code: self.change_language(code))
            
            lang_group.addAction(action)
            self.lang_menu.addAction(action)
        
    
    def change_language(self, language_code):
        """언어 변경 처리"""
        if i18n.set_language(language_code):
            # 설정 저장
            self.settings.setValue("language", language_code)
            
            # 메뉴만 업데이트
            self.update_menu_texts()
            
            # 재시작 안내 메시지
            QMessageBox.information(self, "Language Changed", 
                                   "Language has been changed. Please restart the application to apply all changes.\n\n"
                                   "언어가 변경되었습니다. 모든 변경사항을 적용하려면 애플리케이션을 재시작해주세요.")
    
    def on_language_changed(self, language_code):
        """언어 변경 시그널 처리"""
        self.update_all_texts()

    def update_all_texts(self):
        """모든 UI 텍스트 업데이트"""
        # 윈도우 타이틀 (하드코딩 사용)
        self.setWindowTitle(TITLE_NAME) 
        
        # 메뉴 업데이트
        self.update_menu_texts()
        
        # 버튼 텍스트 업데이트
        self.button_generate_once.setText(tr('generate.once'))
        self.button_generate_sett.setText(tr('generate.by_settings'))
        self.button_generate_auto.setText(tr('generate.auto'))
        
        # 그룹 박스 타이틀 업데이트
        if hasattr(self, 'prompt_group'):
            self.prompt_group.setTitle(tr('ui.prompt_group', 'Prompt'))
        
        # 라벨 업데이트
        self.label_anlas.setText(tr('misc.anlas') + " ?")
        
        # 상태바 업데이트
        self.set_statusbar_text()

        # 라벨 업데이트 (프롬프트 영역의 라벨들 찾아서 업데이트)
        if hasattr(self, 'prompt_splitter'):
            # 스플리터 내 라벨들 업데이트 로직 추가
            pass

    
    def update_menu_texts(self):
        """메뉴 텍스트 업데이트"""
        for action in self.menuBar().actions():
            menu = action.menu()
            if menu:
                # 메뉴 제목 업데이트
                if 'file' in action.text().lower() or '파일' in action.text():
                    menu.setTitle(tr('menu.file'))
                elif 'view' in action.text().lower() or '보기' in action.text():
                    menu.setTitle(tr('menu.view'))
                elif 'etc' in action.text().lower() or '기타' in action.text():
                    menu.setTitle(tr('menu.etc'))
                elif 'language' in action.text().lower():
                    menu.setTitle(tr('menu.languages', 'Languages'))
                
                # 메뉴 내 액션들 업데이트
                for sub_action in menu.actions():
                    if not sub_action.isSeparator():
                        text = sub_action.text()
                        if 'open' in text.lower() or '열기' in text:
                            sub_action.setText(tr('menu.open_file'))
                        elif 'save' in text.lower() and 'settings' in text.lower():
                            sub_action.setText(tr('menu.save_settings'))
                        elif 'load' in text.lower() or '불러오기' in text:
                            sub_action.setText(tr('menu.load_settings'))
                        elif 'login' in text.lower() or '로그인' in text:
                            sub_action.setText(tr('menu.login'))
                        elif 'option' in text.lower() or '옵션' in text:
                            sub_action.setText(tr('menu.option'))
                        elif 'exit' in text.lower() or '종료' in text:
                            sub_action.setText(tr('menu.exit'))
                        elif 'about' in text.lower() or '만든' in text:
                            sub_action.setText(tr('menu.about'))
                        elif 'toggle' in text.lower() or '토글' in text:
                            sub_action.setText(tr('menu.toggle_panel'))

    
    def set_statusbar_text(self, status_key="", list_format=[]):
        statusbar = self.statusBar()
        
        if status_key:
            self.status_state = status_key
            self.status_list_format = list_format
        else:
            status_key = self.status_state
            list_format = self.status_list_format
        
        # 번역된 텍스트 사용
        status_text = tr(f'statusbar.{status_key.lower()}', *list_format)
        statusbar.showMessage(status_text)

    
    def refresh_languages(self):
        """언어 파일 새로고침"""
        i18n.reload_languages()
        self.setup_language_menu()
        QMessageBox.information(self, tr('dialogs.info'), 
                               tr('dialogs.languages_refreshed', 'Languages refreshed successfully'))


    def init_content(self):
        widget = init_main_widget(self)
        self.setCentralWidget(widget)

    def init_nai(self):
        self.nai = NAIGenerator()
        
        # NAIGenerator에 세션 속성 확인 및 초기화
        if not hasattr(self.nai, '_estimated_token_lifetime'):
            self.nai._estimated_token_lifetime = 24 * 3600
        
         # 로그 설정 초기화
        from logger import initialize_logger, set_log_level, set_debug_mode
        log_folder = self.settings.value("log_folder", os.path.join(os.path.expanduser("~"), "NAI-Auto-Generator", "logs"))
        debug_mode = self.settings.value("debug_mode", False, type=bool)
        log_level = self.settings.value("log_level", "NORMAL")
        
        initialize_logger(log_folder, debug_mode)
        set_log_level(log_level.lower())
        
        # 세션 관리자 생성
        self.session_manager = NAISessionManager(self.nai)
        self.nai.session_manager = self.session_manager  # 양방향 참조 설정
        
        # 정기 세션 확인을 위한 타이머 시작
        self.session_timer = QTimer(self)
        self.session_timer.timeout.connect(self.update_session)
        self.session_timer.start(60000)  # 1분마다 확인
        
        if self.settings.value("auto_login", False):
            access_token = self.settings.value("access_token", "")
            username = self.settings.value("username", "")
            password = self.settings.value("password", "")
            if not access_token or not username or not password:
                return

            self.set_statusbar_text("LOGGINGIN")
            self.nai.access_token = access_token
            self.nai.username = username
            self.nai.password = password

            self.trying_auto_login = True
            validate_thread = TokenValidateThread(self)
            validate_thread.validation_result.connect(self.on_login_result)
            validate_thread.start()
    
    def update_session(self):
        """세션 관리 정기 업데이트"""
        if hasattr(self, 'nai') and self.nai and self.nai.access_token:
            self.session_manager.update()
        
    def init_wc(self):
        """와일드카드 처리기 초기화"""
        wildcard_path = self.settings.value("path_wildcards", os.path.abspath(DEFAULT_PATH["path_wildcards"]))
        logger.error(f"와일드카드 폴더 경로: {wildcard_path}")
        
        # 폴더 존재 확인
        if not os.path.exists(wildcard_path):
            try:
                os.makedirs(wildcard_path)
                logger.error(f"와일드카드 폴더 생성: {wildcard_path}")
            except Exception as e:
                logger.error(f"와일드카드 폴더 생성 실패: {e}")
        
        self.wcapplier = WildcardApplier(wildcard_path)
        self.wcapplier.load_wildcards()  # 초기화 시 바로 로드

    def init_tagger(self):
        self.dtagger = DanbooruTagger(self.settings.value(
            "path_models", os.path.abspath(DEFAULT_PATH["path_models"])))

    def init_completion(self, force_reload=False):
        # 이미 태그가 로드되었는지 확인하는 플래그 추가
        if (not hasattr(self, '_tags_loaded') or force_reload) and strtobool(self.settings.value("will_complete_tag", True)):
            print("태그 자동 완성 초기화 시작")
            generate_thread = CompletionTagLoadThread(self, force_reload)
            generate_thread.on_load_completiontag_sucess.connect(self._on_load_completiontag_sucess)
            generate_thread.start()
            # 태그가 로드되었음을 표시
            self._tags_loaded = True
        else:
            # 메시지 변경 또는 제거 (아래 주석 처리된 줄 사용)
            # print("태그 자동 완성 이미 초기화됨")
            pass  # 로그 메시지 출력하지 않음
        
        # 가중치 하이라이트 설정 적용
        self.apply_emphasis_settings()

    def save_data(self):
        data_dict = self.get_data()

        data_dict["seed_fix_checkbox"] = self.dict_ui_settings["seed_fix_checkbox"].isChecked()
        
        # Variety+ 설정 저장 추가
        data_dict["variety_plus"] = self.dict_ui_settings["variety_plus"].isChecked()
        
        for k, v in data_dict.items():
            self.settings.setValue(k, v)
        
        # 캐릭터 프롬프트 데이터 저장
        if hasattr(self, 'character_prompts_container'):
            character_data = self.character_prompts_container.get_data()
            self.settings.setValue("character_prompts", character_data)

    def set_data(self, data_dict):
        dict_ui = self.dict_ui_settings
        
        # 샘플러 설정
        if "sampler" in data_dict:
            from gui_init import set_sampler_by_api_value
            set_sampler_by_api_value(self, data_dict["sampler"])
        else:
            dict_ui["sampler"].setCurrentIndex(0)
        
        # 모델 설정
        if "model" in data_dict:
            model_id = data_dict["model"]
            for i in range(dict_ui["model"].count()):
                if dict_ui["model"].itemData(i) == model_id:
                    dict_ui["model"].setCurrentIndex(i)
                    break
        
        # 텍스트 필드별 다른 메서드 사용
        dict_ui["prompt"].setPlainText(str(data_dict["prompt"]))
        dict_ui["negative_prompt"].setPlainText(str(data_dict["negative_prompt"]))
        
        # 일반 텍스트 필드용
        text_fields = ["width", "height", "steps", "seed", "scale", "cfg_rescale",
                      "strength", "noise", "reference_information_extracted", "reference_strength"]
        for key in text_fields:
            if key in data_dict:
                dict_ui[key].setText(str(data_dict[key]))
            else:
                print(key)
        
        # 체크박스 설정
        dict_ui["autoSmea"].setChecked(bool(data_dict.get("autoSmea", True)))

    def load_data(self):
        data_dict = {}
        for key in DEFAULT_PARAMS:
            data_dict[key] = str(self.settings.value(key, DEFAULT_PARAMS[key]))

        self.set_data(data_dict)
        
        # Variety+ 설정 로드 추가
        variety_plus_checked = self.settings.value("variety_plus", False, type=bool)
        if 'variety_plus' in self.dict_ui_settings:
            self.dict_ui_settings["variety_plus"].setChecked(variety_plus_checked)
                
        # 캐릭터 프롬프트 데이터 로드
        if hasattr(self, 'character_prompts_container'):
            character_data = self.settings.value("character_prompts", {"use_ai_positions": True, "characters": []})
            if character_data and "characters" in character_data:
                try:
                    self.character_prompts_container.set_data(character_data)
                except Exception as e:
                    logger.error(f"캐릭터 프롬프트 데이터 로드 중 오류: {e}")

    def check_folders(self):
        for key, default_path in DEFAULT_PATH.items():
            path = self.settings.value(key, os.path.abspath(default_path))
            create_folder_if_not_exists(path)

    def _on_load_completiontag_sucess(self, tag_list):
        logger.debug("----자동 완성 적용 시작----")   
        logger.info(f"태그 로딩 완료: {len(tag_list)}개")
        if tag_list:
            target_code = ["prompt", "negative_prompt"]
            for code in target_code:
                try:
                    # CompletionTextEdit 클래스의 start_complete_mode 메서드 호출
                    if hasattr(self.dict_ui_settings[code], 'start_complete_mode'):
                        logger.error(f"{code} 필드에 자동 완성 적용 시도...")
                        # 태그 목록을 직접 전달 
                        self.dict_ui_settings[code].start_complete_mode(tag_list)
                        logger.error(f"{code} 필드에 자동 완성 활성화됨 ({len(tag_list)}개 태그)")
                    else:
                        logger.error(f"{code} 필드에 start_complete_mode 메서드가 없음")
                except Exception as e:
                    logger.error(f"{code} 필드 자동 완성 설정 실패: {str(e)}")
                    import traceback
                    traceback.print_exc()
            
            # 캐릭터 프롬프트 컨테이너에도 태그 자동 완성 적용
            if hasattr(self, 'character_prompts_container'):
                try:
                    print("캐릭터 프롬프트 필드에 자동 완성 적용 시도...")
                    self.character_prompts_container.set_tag_completion(tag_list)
                    logger.error(f"캐릭터 프롬프트 필드에 자동 완성 활성화됨 ({len(tag_list)}개 태그)")
                except Exception as e:
                    logger.error(f"캐릭터 프롬프트 필드 자동 완성 설정 실패: {str(e)}")
                    import traceback
                    traceback.print_exc()
        else:
            print("태그 목록이 비어 있음")
        logger.error(f"----- 자동 완성 적용 종료 -----")

    def get_data(self, do_convert_type=False):
        data = {
            "prompt": self.dict_ui_settings["prompt"].toPlainText(),
            "negative_prompt": self.dict_ui_settings["negative_prompt"].toPlainText(),
            "width": self.dict_ui_settings["width"].text(),
            "height": self.dict_ui_settings["height"].text(),
            "sampler": self.dict_ui_settings["sampler"].currentText(),
            "steps": self.dict_ui_settings["steps"].text(),
            "seed": self.dict_ui_settings["seed"].text(),
            "scale": self.dict_ui_settings["scale"].text(),
            "cfg_rescale": self.dict_ui_settings["cfg_rescale"].text(),
            "autoSmea": str(self.dict_ui_settings["autoSmea"].isChecked()),
            "strength": self.dict_ui_settings["strength"].text(),
            "noise": self.dict_ui_settings["noise"].text(),
            "reference_information_extracted": self.dict_ui_settings["reference_information_extracted"].text(),
            "reference_strength": self.dict_ui_settings["reference_strength"].text(),
            "quality_toggle": str(self.settings.value("quality_toggle", True)),
            "dynamic_thresholding": str(self.settings.value("dynamic_thresholding", False)),
            "anti_artifacts": str(self.settings.value("anti_artifacts", 0.0)),
            "v4_model_preset": self.settings.value("v4_model_preset", "Artistic"),
            "model": self.dict_ui_settings["model"].currentData()  # 모델 ID 추가
        }
        
        # 샘플러 UI 이름을 API 값으로 변환
        if hasattr(self, 'sampler_mapping') and data["sampler"] in self.sampler_mapping:
            data["sampler"] = self.sampler_mapping[data["sampler"]]
        
        if do_convert_type:
            data["width"] = int(data["width"])
            data["height"] = int(data["height"])
            data["steps"] = int(data["steps"])
            data["seed"] = int(data["seed"] or 0)
            data["scale"] = float(data["scale"])
            data["cfg_rescale"] = float(data["cfg_rescale"])
            data["autoSmea"] = bool(data["autoSmea"] == "True")
            #data["uncond_scale"] = float(data["uncond_scale"])
            data["strength"] = float(data["strength"])
            data["noise"] = float(data["noise"])
            data["reference_information_extracted"] = float(data["reference_information_extracted"])
            data["reference_strength"] = float(data["reference_strength"])
            data["quality_toggle"] = bool(data["quality_toggle"] == "True")
            data["dynamic_thresholding"] = bool(data["dynamic_thresholding"] == "True")
            data["anti_artifacts"] = float(data["anti_artifacts"])

        return data

    def save_all_data(self):
        """모든 데이터 저장 (캐릭터 프롬프트 포함)"""
        self.save_data()
        
        # 캐릭터 프롬프트 데이터 저장
        if hasattr(self, 'character_prompts_container'):
            character_data = self.character_prompts_container.get_data()
            self.settings.setValue("character_prompts", character_data)

    def load_all_data(self):
        """모든 데이터 로드 (캐릭터 프롬프트 포함)"""
        self.load_data()
        
        # 캐릭터 프롬프트 데이터 로드
        if hasattr(self, 'character_prompts_container'):
            character_data = self.settings.value("character_prompts", {})
            if character_data:
                self.character_prompts_container.set_data(character_data)

    # Warning! Don't interact with pyqt gui in this function
    def _get_data_for_generate(self):
        try:
            logger.debug("_get_data_for_generate 시작")
            
            # 기존 데이터 가져오기
            data = self.get_data(True)
            if not data:
                logger.error("get_data 메서드가 None 또는 빈 데이터를 반환했습니다.")
                return {}  # 빈 딕셔너리 반환 (None 대신)
                
            # 설정 저장
            self.save_data()

            # 샘플러 체크
            if data.get('sampler') == 'ddim_v3':
                data['autoSmea'] = False

            # 데이터 전처리
            data["prompt"], data["negative_prompt"] = self._preedit_prompt(
                data.get("prompt", ""), data.get("negative_prompt", ""))

            # 시드 설정
            if not self.dict_ui_settings["seed_fix_checkbox"].isChecked() or data.get("seed", -1) == -1:
                data["seed"] = random.randint(0, 2**32-1)

            # 해상도 설정
            if hasattr(self, 'checkbox_random_resolution') and self.checkbox_random_resolution.isChecked():
                fl = self.get_now_resolution_familly_list()
                if fl:
                    text = fl[random.randrange(0, len(fl))]
                    res_text = text.split("(")[1].split(")")[0]
                    width, height = res_text.split("x")
                    data["width"], data["height"] = int(width), int(height)

            # 이미지 설정 초기화
            data["image"] = None
            data["reference_image"] = None
            data["mask"] = None
            
            # img2img 설정
            if hasattr(self, 'i2i_settings_group') and self.i2i_settings_group.src:
                try:
                    imgdata_i2i = self.nai.convert_src_to_imagedata(
                        self.i2i_settings_group.src)
                    if imgdata_i2i:
                        data["image"] = imgdata_i2i
                        # 만약 i2i가 켜져있다면 autoSmea 설정을 반드시 꺼야함
                        data['autoSmea'] = False

                        # mask 체크
                        if hasattr(self.i2i_settings_group, 'mask') and self.i2i_settings_group.mask:
                            data['mask'] = convert_qimage_to_imagedata(
                                self.i2i_settings_group.mask)
                    else:
                        # 이미지 로딩 실패 시 초기화
                        if hasattr(self, 'i2i_settings_group') and hasattr(self.i2i_settings_group, 'on_click_removebutton'):
                            self.i2i_settings_group.on_click_removebutton()
                except Exception as e:
                    logger.error(f"img2img 설정 중 오류: {e}")
                    # 오류가 있어도 계속 진행
                    
            # 참조 이미지 설정
            if hasattr(self, 'vibe_settings_group') and hasattr(self.vibe_settings_group, 'src') and self.vibe_settings_group.src:
                try:
                    imgdata_vibe = self.nai.convert_src_to_imagedata(
                        self.vibe_settings_group.src)
                    if imgdata_vibe:
                        data["reference_image"] = imgdata_vibe
                    else:
                        # 이미지 로딩 실패 시 초기화
                        if hasattr(self, 'vibe_settings_group') and hasattr(self.vibe_settings_group, 'on_click_removebutton'):
                            self.vibe_settings_group.on_click_removebutton()
                except Exception as e:
                    logger.error(f"참조 이미지 설정 중 오류: {e}")
                    # 오류가 있어도 계속 진행

            # i2i 와 vibe 세팅
            batch = self.dict_img_batch_target
            for mode_str in ["i2i", "vibe"]:
                target_group = self.i2i_settings_group if mode_str == "i2i" else self.vibe_settings_group
                
                if hasattr(target_group, 'tagcheck_checkbox') and target_group.tagcheck_checkbox.isChecked():
                    if hasattr(target_group, 'src') and target_group.src:
                        if batch[mode_str + "_last_src"] != target_group.src:
                            batch[mode_str + "_last_src"] = target_group.src
                            batch[mode_str + "_last_dst"] = self.predict_tag_from(
                                "src", target_group.src, False)
                            if not batch[mode_str + "_last_dst"]:
                                batch[mode_str + "_last_src"] = ""
                                batch[mode_str + "_last_dst"] = ""

                        data["prompt"] = inject_imagetag(
                            data["prompt"], "img2img" if mode_str == "i2i" else "vibe", batch[mode_str + "_last_dst"])
                        data["negative_prompt"] = inject_imagetag(
                            data["negative_prompt"], "img2img" if mode_str == "i2i" else "vibe", batch[mode_str + "_last_dst"])
                else:
                    batch[mode_str + "_last_src"] = ""
                    batch[mode_str + "_last_dst"] = ""

            # V4 특화 설정 추가
            data["params_version"] = 3
            data["add_original_image"] = True
            
            # Variety+ 설정 추가
            if hasattr(self, 'dict_ui_settings') and 'variety_plus' in self.dict_ui_settings and self.dict_ui_settings["variety_plus"].isChecked():
                data["skip_cfg_above_sigma"] = 19
            else:
                data["skip_cfg_above_sigma"] = None

            if "legacy" not in data and hasattr(self, 'dict_ui_settings') and 'legacy' in self.dict_ui_settings:
                data["legacy"] = bool(self.dict_ui_settings["legacy"].isChecked())
                
            data["legacy_v3_extend"] = False
            
            if "noise_schedule" not in data and hasattr(self, 'dict_ui_settings') and 'noise_schedule' in self.dict_ui_settings:
                data["noise_schedule"] = self.dict_ui_settings["noise_schedule"].currentText()
            
            # 웹 UI에서 보이지 않는 옵션들의 기본값 설정
            data["prefer_brownian"] = True
            data["deliberate_euler_ancestral_bug"] = True
            data["dynamic_thresholding"] = False
            data["sm_dyn"] = False
            data["quality_toggle"] = True
            
            # autoSmea 값 선택적 적용 (샘플러가 ddim_v3일 때 비활성화)
            if data.get('sampler') == 'ddim_v3':
                data['autoSmea'] = False
            elif "autoSmea" not in data and hasattr(self, 'dict_ui_settings') and 'autoSmea' in self.dict_ui_settings:
                data['autoSmea'] = bool(self.dict_ui_settings["autoSmea"].isChecked())
            
            # 캐릭터 프롬프트 데이터 가져오기
            if hasattr(self, 'character_prompts_container'):
                # 🔧 스냅샷 생성 추가
                if hasattr(self, 'wcapplier'):
                    self.wcapplier.create_index_snapshot()
                try:
                    char_data = self.character_prompts_container.get_data()
                    logger.debug(f"캐릭터 프롬프트 가져오기: {len(char_data.get('characters', []))}개")
                    
                    data["characterPrompts"] = []
                    
                    # use_character_coords 설정 (AI 위치 선택이 비활성화되면 좌표 사용)
                    if "use_ai_positions" in char_data:
                        data["use_character_coords"] = not char_data["use_ai_positions"]
                        logger.debug(f"use_character_coords 설정: {data['use_character_coords']}")
                    
                    if "characters" in char_data:
                        for i, char in enumerate(char_data["characters"]):
                            # 원본 프롬프트 텍스트 가져오기
                            raw_prompt = char.get("prompt", "")
                            raw_negative_prompt = char.get("negative_prompt", "") if char.get("negative_prompt") else ""
                            
                            # 전처리 함수 사용 (일반 프롬프트와 동일한 처리)
                            prompt = self._preprocess_character_prompt(raw_prompt)
                            negative_prompt = self._preprocess_character_prompt(raw_negative_prompt)
                            
                            logger.debug(f"캐릭터 {i+1} 프롬프트 전처리:")
                            logger.debug(f"  원본: {repr(raw_prompt[:50])}...")
                            logger.debug(f"  처리후: {repr(prompt[:50])}...")
                            
                            char_prompt = {
                                "prompt": prompt,
                                "negative_prompt": negative_prompt
                            }
                            
                            # 위치 정보 처리 개선
                            if char.get("position") and isinstance(char["position"], (list, tuple)) and len(char["position"]) == 2:
                                char_prompt["position"] = [float(char["position"][0]), float(char["position"][1])]
                                logger.debug(f"캐릭터 {i+1} 위치 정보: {char_prompt['position']}")
                            else:
                                logger.debug(f"캐릭터 {i+1} 위치 정보 없음")
                                
                            data["characterPrompts"].append(char_prompt)
                            
                    logger.debug(f"생성 요청에 포함된 캐릭터 수: {len(data['characterPrompts'])}")
                    
                    # 🔧 인덱스 진행 추가
                    if hasattr(self, 'wcapplier'):
                        self.wcapplier.advance_loopcard_indices()
                except Exception as e:                
                    logger.error(f"캐릭터 프롬프트 처리 중 오류: {e}")
                    
            # 모든 필수 필드가 있는지 확인
            required_fields = ["prompt", "negative_prompt", "width", "height", "steps", "scale"]
            for field in required_fields:
                if field not in data or data[field] is None:
                    logger.error(f"필수 필드 없음: {field}")
                    if field in ["width", "height"]:
                        data[field] = 1024  # 기본값 설정
                    elif field == "steps":
                        data[field] = 28
                    elif field == "scale":
                        data[field] = 5.0
                    else:
                        data[field] = ""  # 텍스트 필드 기본값
            
            logger.debug("_get_data_for_generate 완료")
            return data
            
        except Exception as e:
            logger.error(f"_get_data_for_generate 오류: {e}", exc_info=True)
            # 기본 데이터 반환 (오류 발생 시)
            return {
                "prompt": "",
                "negative_prompt": "",
                "width": 1024,
                "height": 1024,
                "steps": 28,
                "scale": 5.0,
                "seed": random.randint(0, 2**32-1),
                "sampler": "k_euler_ancestral",
                "autoSmea": True,
                "params_version": 3,
                "add_original_image": True,
                "legacy": False,
                "noise_schedule": "karras",
                "prefer_brownian": True,
                "deliberate_euler_ancestral_bug": True,
                "quality_toggle": True
            }
        
        
    def _preedit_prompt(self, prompt, nprompt):
        try_count = 0
        edited_prompt = prompt
        while try_count < MAX_COUNT_FOR_WHILE:
            try_count += 1

            before_edit_prompt = edited_prompt

            # 줄바꿈을 공백으로 대체
            edited_prompt = edited_prompt.replace("\n", " ")
            
            edited_prompt = pickedit_lessthan_str(edited_prompt)
            edited_prompt = self.apply_wildcards(edited_prompt)

            if before_edit_prompt == edited_prompt:
                break

        try_count = 0
        edited_nprompt = nprompt
        while try_count < MAX_COUNT_FOR_WHILE:
            try_count += 1

            before_edit_nprompt = edited_nprompt
            
            # 줄바꿈을 공백으로 대체
            edited_nprompt = edited_nprompt.replace("\n", " ")
            
            # lessthan pick
            edited_nprompt = pickedit_lessthan_str(edited_nprompt)
            # wildcards pick
            edited_nprompt = self.apply_wildcards(edited_nprompt)

            if before_edit_nprompt == edited_nprompt:
                break

        return edited_prompt, edited_nprompt
    
    def _preprocess_character_prompt(self, prompt_text):
        """캐릭터 프롬프트 전처리 (일반 프롬프트와 동일한 처리)"""
        if not prompt_text:
            return ""
        
        # 1. 줄바꿈을 공백으로 변환
        processed = prompt_text.replace("\n", " ")
        
        # 2. 연속된 공백을 하나로 통합
        import re
        processed = re.sub(r'\s+', ' ', processed).strip()
        
        # 3. 와일드카드와 기타 전처리 적용 (기존 _preedit_prompt 로직과 동일)
        try_count = 0
        while try_count < MAX_COUNT_FOR_WHILE:
            try_count += 1
            before_edit = processed
            
            # lessthan pick (<>)
            processed = pickedit_lessthan_str(processed)
            # wildcards pick
            processed = self.apply_wildcards_with_snapshot(processed)
            
            if before_edit == processed:
                break
        
        return processed
        
    def _on_after_create_data_apply_gui(self):
        data = self.nai.parameters

        # resolution text
        fl = self.get_now_resolution_familly_list()
        if fl:
            for resol in fl:
                if str(data["width"]) + "x" + str(data["height"]) in resol:
                    self.combo_resolution.setCurrentText(resol)
                    break

        # seed text
        self.dict_ui_settings["seed"].setText(str(data["seed"]))

        # result text
        self.set_result_text(data)

    def on_click_generate_once(self):
        try:
            # 생성 전 세션 유효성 확인
            if hasattr(self, 'nai') and self.nai:
                # 먼저 로그인 갱신이 필요한지 확인
                if self.session_manager.image_count_since_login >= self.session_manager.max_images_per_session:
                    self.session_manager.force_refresh()
                    self.session_manager.image_count_since_login = 0
                
            if hasattr(self, 'generate_thread') and self.generate_thread.isRunning():
                self.generate_thread.stop()
                
            self.list_settings_batch_target = []
            data = self._get_data_for_generate()
            self.nai.set_param_dict(data)
            self._on_after_create_data_apply_gui()
            
            generate_thread = GenerateThread(self)
            generate_thread.generate_result.connect(self._on_result_generate)
            generate_thread.start()
            
            self.set_statusbar_text("GENERATING")  # 올바른 키로 수정됨
            self.set_disable_button(True)
            self.generate_thread = generate_thread
        
        except Exception as e:
            # 로깅 추가
            logging.error(f"Generate once error: {e}", exc_info=True)
            # 사용자에게 오류 표시
            QMessageBox.critical(self, "생성 오류", f"이미지 생성 중 오류 발생: {e}")
            # 버튼 상태 복원
            self.set_disable_button(False)

    def _on_result_generate(self, error_code, result_str):
        """세션 추적이 포함된 생성 결과 처리"""
        try:                        
            if error_code == 0:
                # 성공적인 생성 - 이미지 결과 설정
                self.image_result.set_custom_pixmap(result_str)
                self.set_statusbar_text("IDLE")
                
                # 세션 모니터링 업데이트
                if hasattr(self, 'session_manager'):
                    self.session_manager.increment_image_count()
            
            else:
                # 오류 케이스 - 인증 문제인지 확인
                if error_code == 401 or "authentication" in result_str.lower():
                    # 인증 오류 - 갱신 시도
                    if hasattr(self, 'nai') and self.nai:
                        success = self.nai.refresh_token()
                        if not success:
                            # 갱신 실패 - 로그인 대화상자 표시
                            QMessageBox.critical(self, "인증 오류", "세션이 만료되었습니다. 다시 로그인해주세요.")
                            self.show_login_dialog()
                else:
                    # 다른 오류 처리
                    error_messages = {
                        1: "서버에서 정보를 가져오는데 실패했습니다.",
                        2: "이미지를 열 수 없습니다.",
                        3: "이미지를 저장할 수 없습니다.",
                        4: "예기치 못한 오류가 발생했습니다."
                    }
                    error_msg = error_messages.get(error_code, "알 수 없는 오류")
                    
                    logging.error(f"Generation error {error_code}: {error_msg}")
                    QMessageBox.critical(self, "생성 오류", f"{error_msg}\n{result_str}")
        
        except Exception as e:
            logging.error(f"Result processing error: {e}", exc_info=True)
        
        finally:
            self.set_disable_button(False)
            self.set_statusbar_text("IDLE")

    def show_api_error_dialog(self, error_code, error_message):
        """API 오류를 사용자 친화적으로 표시"""
        title = "API 요청 오류"
        
        # 오류 코드별 사용자 친화적 메시지
        friendly_messages = {
            401: "인증에 실패했습니다. 다시 로그인해 주세요.",
            402: "Anlas가 부족합니다. 충전 후 다시 시도해 주세요.",
            429: "너무 많은 요청을 보냈습니다. 잠시 후 다시 시도해 주세요.",
            500: "Novel AI 서버에 문제가 있습니다. 잠시 후 다시 시도해 주세요.",
            503: "Novel AI 서비스를 일시적으로 사용할 수 없습니다. 잠시 후 다시 시도해 주세요."
        }
        
        # 사용자 친화적 메시지
        if error_code in friendly_messages:
            friendly_message = friendly_messages[error_code]
            message = f"{friendly_message}\n\n기술적 정보: {error_message}"
        else:
            message = f"이미지를 생성하는데 문제가 있습니다.\n\n{error_message}"
        
        QMessageBox.critical(self, title, message)

    def show_error_dialog(self, title, message):
        """일반 오류 메시지 표시"""
        QMessageBox.critical(self, title, message)

    def on_click_generate_sett(self):
        path_list, _ = QFileDialog().getOpenFileNames(self,
                                                      caption="불러올 세팅 파일들을 선택해주세요",
                                                      filter="Txt File (*.txt)")
        if path_list:
            if len(path_list) < 2:
                QMessageBox.information(
                    self, '경고', "두개 이상 선택해주세요.")
                return

            for path in path_list:
                if not path.endswith(".txt") or not os.path.isfile(path):
                    QMessageBox.information(
                        self, '경고', ".txt로 된 세팅 파일만 선택해주세요.")
                    return

            self.on_click_generate_auto(path_list)

    def proceed_settings_batch(self):
        self.index_settings_batch_target += 1

        while len(self.list_settings_batch_target) <= self.index_settings_batch_target:
            self.index_settings_batch_target -= len(self.list_settings_batch_target)

        path = self.list_settings_batch_target[self.index_settings_batch_target]
        logger.debug(f"설정 파일 로드 시도: {path}")
        is_success = self._load_settings(path)

        if is_success:
            logger.debug("설정 파일 로드 성공")
            # 캐릭터 프롬프트 데이터 확인
            if hasattr(self, 'character_prompts_container'):
                logger.debug(f"캐릭터 프롬프트 데이터: {self.character_prompts_container.get_data()}")
        else:
            logger.error(f"설정 파일 로드 실패: {path}")

        return is_success

    def on_click_generate_auto(self, setting_batch_target=[]):
        if not self.autogenerate_thread:
            d = GenerateDialog(self)
            if d.exec_() == QDialog.Accepted:
                self.list_settings_batch_target = setting_batch_target
                if setting_batch_target:
                    self.index_settings_batch_target = -1
                    is_success = self.proceed_settings_batch()
                    if not is_success:
                        QMessageBox.information(
                            self, '경고', "세팅을 불러오는데 실패했습니다.")
                        return

                agt = AutoGenerateThread(
                    self, d.count, d.delay, d.ignore_error)
                agt.on_data_created.connect(
                    self._on_after_create_data_apply_gui)
                agt.on_error.connect(self._on_error_autogenerate)
                agt.on_end.connect(self._on_end_autogenerate)
                agt.on_statusbar_change.connect(self.set_statusbar_text)
                agt.on_success.connect(self._on_success_autogenerate)
                agt.start()

                self.set_autogenerate_mode(True)
                self.autogenerate_thread = agt
        else:
            self._on_end_autogenerate()

    def _on_error_autogenerate(self, error_code, result):
        QMessageBox.information(
            self, '경고', "이미지를 생성하는데 문제가 있습니다.\n\n" + str(result))
        self._on_end_autogenerate()

    def _on_end_autogenerate(self):
        self.autogenerate_thread.stop()
        self.autogenerate_thread = None
        self.set_autogenerate_mode(False)
        self.set_statusbar_text("IDLE")
        self.refresh_anlas()

    def _on_success_autogenerate(self, result_str):
        self._on_refresh_anlas(self.nai.get_anlas() or -1)

        self.image_result.set_custom_pixmap(result_str)

        if self.dict_img_batch_target["img2img_foldersrc"]:
            self.proceed_image_batch("img2img")
        if self.dict_img_batch_target["vibe_foldersrc"]:
            self.proceed_image_batch("vibe")
        if self.list_settings_batch_target:
            # 설정 파일 변경
            success = self.proceed_settings_batch()
            logger.debug(f"새 설정 파일 적용 결과: {success}")
            
            # UI 업데이트 강제
            QApplication.processEvents()

    def set_autogenerate_mode(self, is_autogenrate):
        self.button_generate_once.setDisabled(is_autogenrate)
        self.button_generate_sett.setDisabled(is_autogenrate)

        stylesheet = """
            color:black;
            background-color: """ + COLOR.BUTTON_AUTOGENERATE + """;
        """ if is_autogenrate else ""
        self.button_generate_auto.setStyleSheet(stylesheet)
        self.button_generate_auto.setText(
            "생성 중지" if is_autogenrate else "연속 생성")
        self.button_generate_auto.setDisabled(False)

    def apply_wildcards(self, prompt):
        """와일드카드와 루프카드를 적용하는 메서드"""
        if not prompt or ("__" not in prompt and "##" not in prompt):
            return prompt  # 와일드카드/루프카드가 없으면 반환
        
        self.check_folders()
        
        if not hasattr(self, 'wcapplier') or not self.wcapplier:
            self.init_wc()
            
        return self.wcapplier.apply_wildcards(prompt)

    def apply_wildcards_with_snapshot(self, prompt):
        """스냅샷을 사용한 와일드카드 적용"""
        if not prompt or ("__" not in prompt and "##" not in prompt):
            return prompt
        if not hasattr(self, 'wcapplier') or not self.wcapplier:
            self.init_wc()
        return self.wcapplier.apply_wildcards_with_snapshot(prompt)

    # gui.py의 debug_wildcards() 메서드를 이렇게 수정:
    def debug_wildcards(self):
        """와일드카드 시스템 디버깅 - 개선된 버전"""
        if not hasattr(self, 'wcapplier'):
            self.init_wc()
            
        print("=== 루프카드 디버깅 시작 ===")
        
        # 1. 와일드카드 로딩 확인
        self.wcapplier.load_wildcards()
        wildcards = self.wcapplier._wildcards_dict
        
        print(f"로드된 와일드카드 수: {len(wildcards)}")
        print("사용 가능한 키들:")
        for key in wildcards.keys():
            print(f"  - '{key}': {len(wildcards[key])}개 라인")
        
        # 2. 특정 키 확인
        test_key = "1_chara"
        print(f"\n키 '{test_key}' 확인:")
        if test_key in wildcards:
            print(f"✅ 발견! 내용: {wildcards[test_key]}")
        else:
            print(f"❌ 없음")
        
        # 3. 루프카드 테스트
        test_prompt = "##1_chara##"
        print(f"\n루프카드 테스트: {test_prompt}")
        
        for i in range(3):
            result = self.wcapplier.apply_wildcards(test_prompt)
            print(f"시도 {i+1}: {result}")
        
        print("=== 루프카드 디버깅 완료 ===")
                
                
    def on_click_open_folder(self, target_pathcode):
        path = self.settings.value(
            target_pathcode, DEFAULT_PATH[target_pathcode])
        path = os.path.abspath(path)
        create_folder_if_not_exists(path)
        os.startfile(path)

    def on_click_save_settings(self):
        path = self.settings.value(
            "path_settings", DEFAULT_PATH["path_settings"])
        path, _ = QFileDialog.getSaveFileName(
            self, "세팅 파일을 저장할 곳을 선택해주세요", path, "Txt File (*.txt)")
        if path:
            try:
                # 기본 데이터 가져오기
                data = self.get_data(True)
                
                # 추가 설정 정보 포함
                data["seed_fix_checkbox"] = self.dict_ui_settings["seed_fix_checkbox"].isChecked()
                data["variety_plus"] = self.dict_ui_settings["variety_plus"].isChecked()
                
                # 메타데이터 추가
                import datetime
                data["metadata"] = {
                    "saved_at": datetime.datetime.now().isoformat(),
                    "app_version": "2.5.29"  # 앱 버전 상수화 필요
                }
                
                # 캐릭터 프롬프트 데이터 추가
                if hasattr(self, 'character_prompts_container'):
                    character_data = self.character_prompts_container.get_data()
                    
                    if character_data["characters"]:
                        # characterPrompts 배열 생성
                        data["characterPrompts"] = []
                        data["use_character_coords"] = not character_data["use_ai_positions"]
                        
                        for char in character_data["characters"]:
                            char_prompt = {
                                "prompt": char["prompt"],
                                "negative_prompt": char["negative_prompt"]
                            }
                            
                            # 위치 정보가 있으면 추가
                            if char["position"] and not character_data["use_ai_positions"]:
                                char_prompt["position"] = char["position"]
                            
                            data["characterPrompts"].append(char_prompt)
                
                json_str = json.dumps(data, indent=2)  # 포맷팅 추가로 가독성 향상
                with open(path, "w", encoding="utf8") as f:
                    f.write(json_str)
                    
                QMessageBox.information(self, '알림', "설정이 성공적으로 저장되었습니다.")
                
            except Exception as e:
                print(e)
                QMessageBox.information(
                    self, '경고', "세팅 저장에 실패했습니다.\n\n" + str(e))

    def _process_prompt_with_wildcards(self, prompt_text):
        """프롬프트 텍스트에 와일드카드와 <> 처리를 적용"""
        if not prompt_text:
            return ""
            
        edited_text = prompt_text
        try_count = 0
        while try_count < MAX_COUNT_FOR_WHILE:
            try_count += 1
            before_edit = edited_text
            edited_text = pickedit_lessthan_str(edited_text)
            edited_text = self.apply_wildcards(edited_text)
            if before_edit == edited_text:
                break
        
        # 줄바꿈 제거
        return edited_text.replace("\n", " ")
        

    def on_click_load_settings(self):
        path = self.settings.value(
            "path_settings", DEFAULT_PATH["path_settings"])

        select_dialog = QFileDialog()
        select_dialog.setFileMode(QFileDialog.ExistingFile)
        path, _ = select_dialog.getOpenFileName(
            self, "불러올 세팅 파일을 선택해주세요", path, "Txt File (*.txt)")
        if path:
            is_success = self._load_settings(path)

            if not is_success:
                QMessageBox.information(
                    self, '경고', "세팅을 불러오는데 실패했습니다.\n\n" + str(e))

    def _load_settings(self, path):
        try:
            with open(path, "r", encoding="utf8") as f:
                json_str = f.read()
            json_obj = json.loads(json_str)

            self.set_data(json_obj)
            
            # 추가 설정 불러오기
            if "seed_fix_checkbox" in json_obj:
                self.dict_ui_settings["seed_fix_checkbox"].setChecked(json_obj["seed_fix_checkbox"])
                
            if "variety_plus" in json_obj:
                self.dict_ui_settings["variety_plus"].setChecked(json_obj["variety_plus"])
                
            # 메타데이터 처리 (필요시)
            if "metadata" in json_obj:
                print(f"설정 파일 메타데이터: {json_obj['metadata']}")
                
            # 캐릭터 프롬프트 데이터가 있으면 로드
            if "characterPrompts" in json_obj and hasattr(self, 'character_prompts_container'):
                # API 형식에서 GUI 형식으로 변환
                characters = []
                for char in json_obj["characterPrompts"]:
                    character = {
                        "prompt": char.get("prompt", ""),
                        "negative_prompt": char.get("negative_prompt", ""),
                        "position": char.get("position", None)
                    }
                    characters.append(character)
                
                character_data = {
                    "use_ai_positions": not json_obj.get("use_character_coords", True),
                    "characters": characters
                }
                
                self.character_prompts_container.set_data(character_data)

            return True
        except Exception as e:
            print(e)

        return False

    def show_prompt_dialog(self, title, prompt, nprompt):
        QMessageBox.about(self, title,
                          "프롬프트:\n" +
                          prompt +
                          "\n\n" +
                          "네거티브 프롬프트:\n" +
                          nprompt)

    def on_random_resolution_checked(self, is_checked):
        # 초기화 중이면 다이얼로그를 표시하지 않음
        is_checked_bool = is_checked == Qt.Checked
        
        if self.is_initializing:
            self.settings.setValue("image_random_checkbox", is_checked_bool)
            return
                
        if is_checked == Qt.Checked:
            fl = self.get_now_resolution_familly_list()
            if not fl:
                QMessageBox.information(
                    self, '이미지 크기 랜덤', "랜덤이 지원되지 않는 형식입니다.\n")
            else:
                s = ""
                for f in fl:
                    s += f + "\n"
                QMessageBox.information(
                    self, '이미지 크기 랜덤', "다음 크기 중 하나가 랜덤으로 선택됩니다.\n\n" + s)

        # 명시적으로 bool 타입으로 저장
        self.settings.setValue("image_random_checkbox", is_checked_bool)
        
        # 설정이 제대로 저장되었는지 확인 (디버깅용)
        logger.debug(f"랜덤 체크박스 상태 저장: {is_checked_bool}")

    def get_now_resolution_familly_list(self):
        try:
            current_text = self.combo_resolution.currentText()
            if current_text == "Custom (직접 입력)":
                return []
                
            # 현재 선택된 해상도가 어느 패밀리에 속하는지 확인
            for family_idx, resolutions in RESOLUTION_FAMILIY.items():
                if current_text in resolutions:
                    return resolutions
                    
            # 만약 찾지 못했다면 기본 HD 패밀리 반환
            return RESOLUTION_FAMILIY[0]  # 기본 해상도 모음 (HD 포함)
        except Exception as e:
            logger.error(f"Resolution family error: {e}")
            return []

    def change_path(self, code, src):
        # 절대 경로로 변환
        path = os.path.abspath(src)
        
        # Windows에서는 백슬래시 사용하도록 정규화
        if os.name == 'nt':
            path = os.path.normpath(path)
        
        self.settings.setValue(code, path)
        
        create_folder_if_not_exists(path)
        
        if code == "path_wildcards":
            self.init_wc()
        elif code == "path_models":
            self.init_tagger()

    def on_click_getter(self):
        MiniUtilDialog(self, "getter").show()

    def on_click_tagger(self):
        MiniUtilDialog(self, "tagger").show()

    def on_click_expand(self):
        self.is_expand = not self.is_expand
        
        if self.is_expand:
            # Save current state before collapsing
            self.settings.setValue("splitterSizes", self.main_splitter.saveState())
            
            # Restore or set default sizes
            if self.main_splitter.sizes()[1] == 0:
                self.set_default_splitter()
                
            self.main_splitter.handle(1).setEnabled(True)
            self.main_splitter.widget(1).show()
        else:
            # Collapse right panel
            self.settings.setValue("splitterSizes", self.main_splitter.saveState())
            self.main_splitter.setSizes([self.main_splitter.width(), 0])
            self.main_splitter.handle(1).setEnabled(False)
            self.main_splitter.widget(1).hide()
        
        self.update_expand_button()
        QTimer.singleShot(50, self.image_result.refresh_size)

    def update_expand_button(self):
        self.button_expand.setText("◀▶" if self.is_expand else "▶◀")
        self.button_expand.setToolTip("Collapse right panel" if self.is_expand else "Expand right panel")

    def update_ui_after_expand(self):
        # UI 갱신 및 이미지 크기 조정
        self.repaint()
        if self.is_expand:
            self.image_result.refresh_size()

    def install_model(self, model_name):
        loading_dialog = FileIODialog(
            "모델 다운 받는 중...\n이 작업은 오래 걸릴 수 있습니다.", lambda: str(self.dtagger.download_model(model_name)))
        if loading_dialog.exec_() == QDialog.Accepted:
            if loading_dialog.result == "True":
                self.option_dialog.on_model_downloaded(model_name)

    def get_image_info_bysrc(self, file_src):
        nai_dict, error_code = naiinfo_getter.get_naidict_from_file(file_src)

        self._get_image_info_byinfo(nai_dict, error_code, file_src)

    def get_image_info_bytxt(self, file_src):
        nai_dict, error_code = naiinfo_getter.get_naidict_from_txt(file_src)

        self._get_image_info_byinfo(nai_dict, error_code, None)

    def get_image_info_byimg(self, img):
        nai_dict, error_code = naiinfo_getter.get_naidict_from_img(img)

        self._get_image_info_byinfo(nai_dict, error_code, img)

    def _get_image_info_byinfo(self, nai_dict, error_code, img_obj):
        if error_code == 0:
            QMessageBox.information(self, '경고', "EXIF가 존재하지 않는 파일입니다.")
            self.set_statusbar_text("IDLE")
        elif error_code == 1 or error_code == 2:
            QMessageBox.information(
                self, '경고', "EXIF는 존재하나 NAI로부터 만들어진 것이 아닌 듯 합니다.")
            self.set_statusbar_text("IDLE")
        elif error_code == 3:
            new_dict = {
                "prompt": nai_dict["prompt"], "negative_prompt": nai_dict["negative_prompt"]}
            new_dict.update(nai_dict["option"])
            new_dict.update(nai_dict["etc"])
            
            # v4_prompt에서 캐릭터 정보 추출
            if "v4_prompt" in nai_dict["etc"] and "caption" in nai_dict["etc"]["v4_prompt"]:
                char_captions = nai_dict["etc"]["v4_prompt"]["caption"].get("char_captions", [])
                v4_neg_prompt = nai_dict["etc"].get("v4_negative_prompt", {})
                neg_char_captions = []
                
                if "caption" in v4_neg_prompt:
                    neg_char_captions = v4_neg_prompt["caption"].get("char_captions", [])
                
                # characterPrompts 배열 생성
                character_prompts = []
                for i, char in enumerate(char_captions):
                    char_prompt = {
                        "prompt": char.get("char_caption", ""),
                        "negative_prompt": "",
                        "position": None
                    }
                    
                    # 위치 정보 추가 (있을 경우)
                    if "centers" in char and len(char["centers"]) > 0:
                        center = char["centers"][0]
                        char_prompt["position"] = [center.get("x", 0.5), center.get("y", 0.5)]
                    
                    # 네거티브 프롬프트 추가 (존재하는 경우)
                    if i < len(neg_char_captions):
                        char_prompt["negative_prompt"] = neg_char_captions[i].get("char_caption", "")
                    
                    character_prompts.append(char_prompt)
                
                if character_prompts:
                    new_dict["characterPrompts"] = character_prompts

            self.set_data(new_dict)
            
            # 캐릭터 프롬프트 데이터가 있으면 UI에 적용
            if "characterPrompts" in new_dict and hasattr(self, 'character_prompts_container'):
                characters = []
                for char in new_dict["characterPrompts"]:
                    character = {
                        "prompt": char.get("prompt", ""),
                        "negative_prompt": char.get("negative_prompt", ""),
                        "position": char.get("position", None)
                    }
                    characters.append(character)
                
                character_data = {
                    "use_ai_positions": not new_dict.get("use_character_coords", True),
                    "characters": characters
                }
                
                self.character_prompts_container.set_data(character_data)
            
            # 메타데이터 표시
            params_copy = self.nai.parameters.copy()
            params_copy.update(new_dict)
            self.set_result_text(params_copy)
            
            if img_obj:
                self.image_result.set_custom_pixmap(img_obj)
            self.set_statusbar_text("LOAD_COMPLETE")


    def show_option_dialog(self):
        """옵션 대화상자를 표시합니다."""
        dialog = OptionDialog(self)
        dialog.exec_()

    def show_login_dialog(self):
        dialog = LoginDialog(self)
        dialog.exec_() 
        # 여기서 dialog가 모달로 실행되고 완료됩니다
        # 로그인 성공/실패 처리는 dialog에서 이루어집니다

    def show_about_dialog(self):
        about_text = """NAI Auto Generator v4.5    

        Community : https://arca.live/b/aiart
          
        Original :  https://github.com/DCP-arca/NAI-Auto-Generator

        v4/v4.5 update : sagawa8b
          
        크레딧 : https://huggingface.co/baqu2213
                https://github.com/neggles/sd-webui-stealth-pnginfo/  
                https://github.com/DCP-arca/NAI-Auto-Generator

        Notice : "본 앱은 제3자가 개발한 앱으로 Novel AI 에서 개발하거나 관리하지 않으며, 이들 회사와는 무관합니다."

        ="This app is a third-party app that is not developed or managed by Novel AI is unaffiliated with those companies."
        """
        QMessageBox.about(self, 'About', about_text)

        self.option_dialog.exec_()
    

    def set_disable_button(self, will_disable):
        self.button_generate_once.setDisabled(will_disable)
        self.button_generate_sett.setDisabled(will_disable)
        self.button_generate_auto.setDisabled(will_disable)

    def set_result_text(self, nai_dict):
        additional_dict = {}

        if 'image' in nai_dict and nai_dict['image']:
            additional_dict["image_src"] = self.i2i_settings_group.src or ""
        if 'reference_image' in nai_dict and nai_dict['reference_image']:
            additional_dict["reference_image_src"] = self.vibe_settings_group.src or ""

        if self.dict_img_batch_target["i2i_last_dst"]:
            additional_dict["image_tag"] = self.dict_img_batch_target["i2i_last_dst"]
        if self.dict_img_batch_target["vibe_last_dst"]:
            additional_dict["reference_image_tag"] = self.dict_img_batch_target["vibe_last_dst"]
        
        # 캐릭터 프롬프트도 처리된 형태로 표시
        if 'characterPrompts' in nai_dict and nai_dict['characterPrompts']:
            additional_dict["processed_characters"] = nai_dict['characterPrompts']

        content = prettify_naidict(nai_dict, additional_dict)

        self.prompt_result.setText(content)

    def refresh_anlas(self):
        anlas_thread = AnlasThread(self)
        anlas_thread.anlas_result.connect(self._on_refresh_anlas)
        anlas_thread.start()

    def _on_refresh_anlas(self, anlas):
        if anlas == -1:
            anlas = "?"
        self.label_anlas.setText("Anlas: " + str(anlas))

    def on_login_result(self, error_code):
        if error_code == 0:
            self.set_statusbar_text("LOGINED")
            self.label_loginstate.set_logged_in(True)
            self.set_disable_button(False)
            self.refresh_anlas()  # 이 부분이 제대로 실행되는지 확인
        else:
            self.nai = NAIGenerator()  # reset
            self.set_statusbar_text("BEFORE_LOGIN")
            self.label_loginstate.set_logged_in(False)
            self.set_disable_button(True)
            self.set_auto_login(False)

        self.trying_auto_login = False

    def set_auto_login(self, is_auto_login):
        self.settings.setValue("auto_login",
                               True if is_auto_login else False)
        self.settings.setValue("access_token",
                               self.nai.access_token if is_auto_login else None)
        self.settings.setValue("username",
                               self.nai.username if is_auto_login else None)
        self.settings.setValue("password",
                               self.nai.password if is_auto_login else None)

    def on_logout(self):
        self.set_statusbar_text("BEFORE_LOGIN")

        self.label_loginstate.set_logged_in(False)

        self.set_disable_button(True)

        self.set_auto_login(False)

    def show_file_dialog(self, mode):
        select_dialog = QFileDialog()
        select_dialog.setFileMode(QFileDialog.ExistingFile)
        target_type = '이미지, 텍스트 파일(*.txt *.png *.webp)' if mode == 'file' else '이미지 파일(*.jpg *.png *.webp)'
        fname = select_dialog.getOpenFileName(
            self, '불러올 파일을 선택해 주세요.', '', target_type)

        if fname[0]:
            fname = fname[0]

            if mode == "file":
                if fname.endswith(".png") or fname.endswith(".webp"):
                    self.get_image_info_bysrc(fname)
                elif fname.endswith(".txt"):
                    self.get_image_info_bytxt(fname)
                else:
                    QMessageBox.information(
                        self, '경고', "png, webp, txt 파일만 가능합니다.")
                    return

    def show_openfolder_dialog(self, mode):
        select_dialog = QFileDialog()
        select_dialog.setFileMode(QFileDialog.Directory)
        select_dialog.setOption(QFileDialog.Option.ShowDirsOnly)
        fname = select_dialog.getExistingDirectory(
            self, mode + '모드로 열 폴더를 선택해주세요.', '')

        if fname:
            if os.path.isdir(fname):
                self.set_imagefolder_as_param(mode, fname)
            else:
                QMessageBox.information(
                    self, '경고', "폴더만 선택 가능합니다.")

    def _set_image_gui(self, mode, src):
        if mode == "img2img":
            self.i2i_settings_group.set_image(src)
            self.image_options_layout.setStretch(0, 1)
        if mode == "vibe":
            self.vibe_settings_group.set_image(src)
            self.image_options_layout.setStretch(1, 1)
        self.image_options_layout.setStretch(2, 0)

    def set_image_as_param(self, mode, src):
        self.dict_img_batch_target[mode + "_foldersrc"] = ""
        target_group = self.i2i_settings_group if mode == "img2img" else self.vibe_settings_group
        target_group.set_folder_mode(False)
        self._set_image_gui(mode, src)

    def set_imagefolder_as_param(self, mode, foldersrc):
        if get_imgcount_from_foldersrc(foldersrc) == 0:
            QMessageBox.information(
                self, '경고', "이미지 파일이 없는 폴더입니다")
            return

        target_group = self.i2i_settings_group if mode == "img2img" else self.vibe_settings_group
        target_group.set_folder_mode(True)

        self.dict_img_batch_target[mode + "_foldersrc"] = foldersrc
        self.dict_img_batch_target[mode + "_index"] = -1

        self.proceed_image_batch(mode)

    def proceed_image_batch(self, mode):
        self.dict_img_batch_target[mode + "_index"] += 1
        target_group = self.i2i_settings_group if mode == "img2img" else self.vibe_settings_group

        src, is_reset = pick_imgsrc_from_foldersrc(
            foldersrc=self.dict_img_batch_target[mode + "_foldersrc"],
            index=self.dict_img_batch_target[mode + "_index"],
            sort_order=target_group.get_folder_sort_mode()
        )

        if is_reset:
            seed = random.randint(0, 9999999999)
            self.dict_ui_settings["seed"].setText(str(seed))

        self._set_image_gui(mode, src)

    def on_click_tagcheckbox(self, mode):
        box = self.sender()
        if box.isChecked():
            if not self.settings.value("selected_tagger_model", ""):
                box.setChecked(False)
                QMessageBox.information(
                    self, '경고', "먼저 옵션에서 태깅 모델을 다운/선택 해주세요.")
                return

            QMessageBox.information(
                self, '안내', "새로운 이미지를 불러올때마다 태그를 읽습니다.\n프롬프트 내에 @@" + mode + "@@를 입력해주세요.\n해당 자리에 삽입됩니다.")
            return

    # warning! Don't use this function in thread if with_dialog==True
    def predict_tag_from(self, filemode, target, with_dialog):
        result = ""

        target_model_name = self.settings.value("selected_tagger_model", '')
        if not target_model_name:
            QMessageBox.information(
                self, '경고', "먼저 옵션에서 태깅 모델을 다운/선택 해주세요.")
            return ""
        else:
            self.dtagger.options["model_name"] = target_model_name

        if filemode == "src":
            target = Image.open(target)

        if with_dialog:
            loading_dialog = FileIODialog(
                "태그하는 중...", lambda: self.dtagger.tag(target))
            if loading_dialog.exec_() == QDialog.Accepted:
                result = loading_dialog.result
                if not result:
                    list_installed_model = self.dtagger.get_installed_models()
                    if not (target_model_name in list_installed_model):
                        self.settings.setValue("selected_tagger_model", '')
        else:
            try:
                result = self.dtagger.tag(target)
            except Exception as e:
                print(e)

        return result

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        files = [u for u in event.mimeData().urls()]

        if len(files) != 1:
            QMessageBox.information(self, '경고', "파일을 하나만 옮겨주세요.")
            return

        furl = files[0]
        if furl.isLocalFile():
            fname = furl.toLocalFile()
            if fname.endswith(".png") or fname.endswith(".webp") or fname.endswith(".jpg"):
                if self.i2i_settings_group.geometry().contains(event.pos()):
                    self.set_image_as_param("img2img", fname)
                    return
                elif self.vibe_settings_group.geometry().contains(event.pos()):
                    self.set_image_as_param("vibe", fname)
                    return
                elif not fname.endswith(".jpg"):
                    self.get_image_info_bysrc(fname)
                    return
            elif fname.endswith(".txt"):
                self.get_image_info_bytxt(fname)
                return
            elif os.path.isdir(fname):
                if self.i2i_settings_group.geometry().contains(event.pos()):
                    self.set_imagefolder_as_param("img2img", fname)
                    return
                elif self.vibe_settings_group.geometry().contains(event.pos()):
                    self.set_imagefolder_as_param("vibe", fname)
                    return

            QMessageBox.information(
                self, '경고', "세팅 불러오기는 png, webp, txt 파일만 가능합니다.\ni2i와 vibe를 사용하고 싶다면 해당 칸에 떨어트려주세요.")
        else:
            self.set_statusbar_text("LOADING")
            try:
                url = furl.url()
                res = request.urlopen(url).read()
                img = Image.open(BytesIO(res))
                if img:
                    self.get_image_info_byimg(img)

            except Exception as e:
                print(e)
                self.set_statusbar_text("IDLE")
                QMessageBox.information(self, '경고', "이미지 파일 다운로드에 실패했습니다.")
                return

    def set_statusbar_text(self, status_key="", list_format=[]):
        statusbar = self.statusBar()

        if status_key:
            self.status_state = status_key
            self.status_list_format = list_format
        else:
            status_key = self.status_state
            list_format = self.status_list_format

        # 번역된 텍스트 사용
        status_text = tr(f'statusbar.{status_key.lower()}', *list_format)
        statusbar.showMessage(status_text)

    def on_statusbar_message_changed(self, t):
        if not t:
            self.set_statusbar_text()

    def closeEvent(self, e):
        # 창 크기 저장 (확장 여부에 따른 조정 없이 현재 전체 크기 저장)
        current_size = self.size()
        self.settings.setValue("size", current_size)
        self.settings.setValue("pos", self.pos())
        
        # 스플리터 상태 저장
        self.settings.setValue("splitterSizes", self.main_splitter.saveState())
        
        # 기타 데이터 저장
        self.save_data()
        
        # 설정 즉시 동기화 (종료 전에 설정이 확실히 저장되도록)
        self.settings.sync()
        
        e.accept()

    def quit_app(self):
        time.sleep(0.1)
        self.close()
        self.app.closeAllWindows()
        QCoreApplication.exit(0)


class CompletionTagLoadThread(QThread):
    on_load_completiontag_sucess = pyqtSignal(list)

    def __init__(self, parent, force_reload=False):
        super(CompletionTagLoadThread, self).__init__(parent)
        self.parent = parent
        self.force_reload = force_reload
        
        # 태그 목록을 캐시하는 클래스 변수 추가 (모든 인스턴스가 공유)
        if not hasattr(CompletionTagLoadThread, 'cached_tags'):
            CompletionTagLoadThread.cached_tags = None

    def run(self):
        # 이미 캐시된 태그가 있고, 강제 새로고침이 아니면 재사용
        if CompletionTagLoadThread.cached_tags is not None and not self.force_reload:
            print("캐시된 태그 사용 (다시 로드하지 않음)")
            self.on_load_completiontag_sucess.emit(CompletionTagLoadThread.cached_tags)
            return
            
        try:
            print("----- 태그 자동 완성 로딩 시작 -----")
            # 경로 변환 - 리소스 경로 사용
            default_path = self.parent.settings.value("path_tag_completion", DEFAULT_TAGCOMPLETION_PATH)
            logger.error(f"기본 태그 파일 경로: {default_path}")
            tag_path = resource_path(default_path)
            logger.error(f"변환된 태그 파일 경로: {tag_path}")
            logger.error(f"파일 존재 여부: {os.path.exists(tag_path)}")
            
            # 파일이 존재하는지 확인
            if not os.path.exists(tag_path):
                print("기본 경로에 파일이 없습니다. 대체 경로 시도...")
                # 대체 경로 시도
                alt_paths = [
                    resource_path("danbooru_tags_post_count.csv"),
                    resource_path("./danbooru_tags_post_count.csv"),
                    os.path.join(os.path.dirname(os.path.abspath(__file__)), "danbooru_tags_post_count.csv"),
                    os.path.join(os.getcwd(), "danbooru_tags_post_count.csv")
                ]
                
                for alt_path in alt_paths:
                    logger.error(f"대체 경로 시도: {alt_path}")
                    if os.path.exists(alt_path):
                        tag_path = alt_path
                        logger.error(f"대체 경로 발견: {tag_path}")
                        break
                    else:
                        logger.error(f"  - 파일 없음")
            
            # 태그 파일 다운로드 URL (만약 파일이 없다면)
            download_url = "https://raw.githubusercontent.com/DCP-arca/NAI-Auto-Generator/main/danbooru_tags_post_count.csv"
            
            tag_list = []
            
            # 파일이 없으면 다운로드 시도
            if not os.path.exists(tag_path):
                logger.error(f"태그 파일을 찾을 수 없어 다운로드를 시도합니다: {download_url}")
                try:
                    import requests
                    response = requests.get(download_url)
                    if response.status_code == 200:
                        # 다운로드 성공, 파일 저장
                        save_path = os.path.join(os.getcwd(), "danbooru_tags_post_count.csv")
                        with open(save_path, "wb") as f:
                            f.write(response.content)
                        logger.error(f"태그 파일 다운로드 성공: {save_path}")
                        tag_path = save_path
                    else:
                        logger.error(f"태그 파일 다운로드 실패: {response.status_code}")
                except Exception as e:
                    logger.error(f"다운로드 중 오류 발생: {str(e)}")
            
            # CSV 파일 처리
            if os.path.exists(tag_path):
                logger.error(f"태그 파일 로딩 중: {tag_path}")
                if tag_path.endswith('.csv'):
                    with open(tag_path, "r", encoding='utf8') as f:
                        for line in f:
                            line = line.strip()
                            if ',' in line:  # CSV 형식 확인
                                parts = line.split(',')
                                if len(parts) >= 2:
                                    tag = parts[0]
                                    count = parts[1]
                                    tag_list.append(f"{tag}[{count}]")
                            else:  # 일반 텍스트 형식
                                tag_list.append(line)
                else:
                    with open(tag_path, "r", encoding='utf8') as f:
                        tag_list = [line.strip() for line in f.readlines()]
                        
                logger.info(f"태그 로딩 완료: {len(tag_list)}개 태그")
                
                # 첫 10개 태그 샘플 출력
            if len(tag_list) > 0:
                CompletionTagLoadThread.cached_tags = tag_list
                
                self.on_load_completiontag_sucess.emit(tag_list)
        except Exception as e:
            logger.error(f"태그 로딩 실패: {str(e)}")
            import traceback
            traceback.print_exc()
            self.on_load_completiontag_sucess.emit([])
            
        print("----- 태그 자동 완성 로딩 종료 -----")


class AutoGenerateThread(QThread):
    on_data_created = pyqtSignal()
    on_error = pyqtSignal(int, str)
    on_success = pyqtSignal(str)
    on_end = pyqtSignal()
    on_statusbar_change = pyqtSignal(str, list)

    def __init__(self, parent, count, delay, ignore_error):
        super(AutoGenerateThread, self).__init__(parent)
        self.count = int(count or -1)
        self.delay = float(delay or 0.01)
        self.ignore_error = ignore_error
        self.is_dead = False

    def run(self):
        parent = self.parent()

        count = self.count
        delay = float(self.delay)

        temp_preserve_data_once = False
        while count != 0:
            # 1. Generate

            # generate data
            if not temp_preserve_data_once:
                try:
                    data = parent._get_data_for_generate()
                    if data is None:
                        self.on_error.emit(1, "데이터 생성 실패: None이 반환되었습니다.")
                        return
                    parent.nai.set_param_dict(data)
                    self.on_data_created.emit()
                except Exception as e:
                    self.on_error.emit(1, f"데이터 생성 중 오류 발생: {str(e)}")
                    return

            # set status bar
            if count <= -1:
                self.on_statusbar_change.emit("AUTO_GENERATING_INF", [])
            else:
                self.on_statusbar_change.emit("AUTO_GENERATING_COUNT", [
                    self.count, self.count - count + 1])

            # before generate, if setting batch
            path = parent.settings.value(
                "path_results", DEFAULT_PATH["path_results"])
            create_folder_if_not_exists(path)
            if parent.list_settings_batch_target:
                setting_path = parent.list_settings_batch_target[parent.index_settings_batch_target]
                setting_name = get_filename_only(setting_path)
                path = path + "/" + setting_name
                create_folder_if_not_exists(path)

            # generate image
            error_code, result_str = _threadfunc_generate_image(
                self, path)
            if self.is_dead:
                return
            if error_code == 0:
                self.on_success.emit(result_str)
            else:
                if self.ignore_error:
                    for t in range(int(delay), 0, -1):
                        self.on_statusbar_change.emit("AUTO_ERROR_WAIT", [t])
                        time.sleep(1)
                        if self.is_dead:
                            return

                    temp_preserve_data_once = True
                    continue
                else:
                    self.on_error.emit(error_code, result_str)
                    return

            # 2. Wait
            count -= 1
            if count != 0:
                temp_delay = delay
                for x in range(int(delay)):
                    self.on_statusbar_change.emit("AUTO_WAIT", [temp_delay])
                    time.sleep(1)
                    if self.is_dead:
                        return
                    temp_delay -= 1

        self.on_end.emit()

    def stop(self):
        self.is_dead = True
        self.quit()


def _threadfunc_generate_image(thread_self, path):
    try:
        
        # 기존 로깅 초기화 코드 제거
        # logging.basicConfig(level=logging.DEBUG)
        # logger = logging.getLogger(__name__)
        
        # 중앙 로거 가져오기로 대체
        from logger import get_logger
        logger = get_logger()
        
        # 1: 이미지 생성
        parent = thread_self.parent()
        nai = parent.nai
        action = NAIAction.generate
        
        # 액션 타입 로깅
        logger.debug(f"Image generation action: {action}")
        
        # 이 부분 수정: 튜플 반환값 확인 및 처리
        result = nai.generate_image(action)
        
        # 튜플 반환 확인 (오류 발생 시)
        if isinstance(result, tuple) and len(result) == 2 and result[0] is None:
            error_message = result[1]
            logger.error(f"API 오류: {error_message}")
            return 1, error_message  # 오류 코드와 메시지 반환
            
        if not result:
            logger.error("서버에서 정보를 가져오는데 실패했습니다.")
            return 1, "서버에서 정보를 가져오는데 실패했습니다."
        
        # 2: 이미지 열기
        try:
            zipped = zipfile.ZipFile(io.BytesIO(result))
            image_bytes = zipped.read(zipped.infolist()[0])
            img = Image.open(io.BytesIO(image_bytes))
        except Exception as e:
            logger.error(f"이미지 열기 오류: {e}")
            return 2, str(e)
        
        # 3: 이미지 저장
        create_folder_if_not_exists(path)
        
        # 안전한 파일명 생성
        def sanitize_filename(filename):
            # 윈도우 파일명에 허용되지 않는 문자 제거
            return "".join(c for c in filename if c.isalnum() or c in (' ', '_', '-', '.')).rstrip()
            
        # 파일명 생성 로직 개선
        timename = datetime.datetime.now().strftime("%y%m%d_%H%M%S%f")[:-4]
        filename = timename
        
        # 프롬프트 기반 파일명 생성 (안전하게)
        if bool(thread_self.parent().settings.value("will_savename_prompt", True)):
            safe_prompt = sanitize_filename(nai.parameters["prompt"])
            # 프롬프트 길이 제한 (예: 최대 50자)
            filename += "_" + safe_prompt[:50]
        # 파일 확장자 추가
        filename += ".png"
        
        # 최종 저장 경로 생성
        dst = os.path.join(path, filename)
        
        # 중복 파일명 처리
        counter = 1
        base, ext = os.path.splitext(dst)
        while os.path.exists(dst):
            dst = f"{base}_{counter}{ext}"
            counter += 1
        
        # 상세 로깅
        logger.debug(f"최종 저장 경로: {dst}")
        logger.debug(f"파일명: {filename}")
        
        try:
            img.save(dst)
            logger.info(f"이미지 성공적으로 저장: {dst}")
        except Exception as e:
            logger.error(f"이미지 저장 오류: {e}")
            return 3, str(e)
        
        return 0, dst
    
    except Exception as e:
        # 중앙 로거 사용 및 예외 정보 포함
        from logger import get_logger
        logger = get_logger()
        logger.critical(f"예기치 못한 오류: {e}", exc_info=True)
        return 4, str(e)


class GenerateThread(QThread):
    generate_result = pyqtSignal(int, str)

    def __init__(self, parent):
        super(GenerateThread, self).__init__(parent)
        self.is_stopped = False

    def run(self):
        path = self.parent().settings.value(
            "path_results", DEFAULT_PATH["path_results"])
        error_code, result_str = _threadfunc_generate_image(self, path)
        
        if not self.is_stopped:
            self.generate_result.emit(error_code, result_str)
    
    def stop(self):
        self.is_stopped = True
        self.wait()  # 스레드가 종료될 때까지 대기

class TokenValidateThread(QThread):
    validation_result = pyqtSignal(int)

    def __init__(self, parent):
        super(TokenValidateThread, self).__init__(parent)
        self.parent = parent

    def run(self):
        try:
            is_login_success = self.parent.nai.check_logged_in()
            
            # 속성 존재 확인 및 초기화
            if is_login_success and not hasattr(self.parent.nai, '_estimated_token_lifetime'):
                self.parent.nai._estimated_token_lifetime = 24 * 3600
                
            self.validation_result.emit(0 if is_login_success else 1)
        except Exception as e:
            logger.error(f"토큰 검증 오류: {e}")
            self.validation_result.emit(1)  # 오류 발생 시 실패로 처리


class AnlasThread(QThread):
    anlas_result = pyqtSignal(int)

    def __init__(self, parent):
        super(AnlasThread, self).__init__(parent)

    def run(self):
        anlas = self.parent().nai.get_anlas() or -1

        self.anlas_result.emit(anlas)


def toggle_debug_mode(self):
    """디버그 모드 토글"""
    self.debug_mode = not getattr(self, 'debug_mode', False)
    
    # 로그 레벨 조정
    if self.debug_mode:
        logging.getLogger('nai_generator').setLevel(logging.DEBUG)
        QMessageBox.information(self, "디버그 모드", "디버그 모드가 활성화되었습니다. 자세한 로그가 콘솔과 로그 파일에 기록됩니다.")
    else:
        logging.getLogger('nai_generator').setLevel(logging.INFO)
        QMessageBox.information(self, "디버그 모드", "디버그 모드가 비활성화되었습니다.")
        
    # 디버그 모드 설정 저장
    self.settings.setValue("debug_mode", self.debug_mode)

if __name__ == '__main__':
    input_list = sys.argv
    app = QApplication(sys.argv)

    widget = NAIAutoGeneratorWindow(app)

    time.sleep(0.1)

    sys.exit(app.exec_())