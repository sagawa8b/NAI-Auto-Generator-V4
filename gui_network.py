"""
gui_network.py - 네트워크 모니터링 및 세션 관리

NetworkMonitor 클래스와 NAIAutoGeneratorWindow에 mix-in되는
세션/연결 관련 메서드들을 담당합니다.
"""

import socket

import requests
from PyQt5.QtCore import QObject, QTimer, pyqtSignal

from logger import get_logger
logger = get_logger()


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
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            
            # API 서버 확인
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


class NetworkMixin:
    """NAIAutoGeneratorWindow에 mix-in되는 네트워크/세션 관련 메서드.
    
    이 Mixin은 다음을 전제합니다:
    - self.nai: NAIGenerator 인스턴스
    - self.session_manager: NAISessionManager 인스턴스
    - self.settings: QSettings 인스턴스
    - self.label_connection_status: QLabel 인스턴스
    - self.network_monitor: NetworkMonitor 인스턴스
    """

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
                        logger.warning("세션 상태 불량, 강제 갱신 시도")
                        success = self.session_manager.force_refresh()
                        
                        if success:
                            self.set_statusbar_text("logged_in")
                            self.refresh_anlas()
                            logger.info("세션 강제 갱신 성공")
                        else:
                            # 실패 시 로그인 대화상자 표시 고려
                            self.set_statusbar_text("before_login")
                            logger.warning("세션 강제 갱신 실패, 사용자 개입 필요")
                            
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
                logger.error(f"세션 체크 오류: {e}")

    def keepalive(self):
        """세션 유지를 위한 경량 API 호출"""
        if hasattr(self, 'nai') and self.nai and self.nai.access_token:
            try:
                self.nai.get_anlas()  # 가벼운 API 호출
                logger.debug("Keepalive 성공")
            except Exception as e:
                logger.warning(f"Keepalive 실패: {e}")

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
                logger.error(f"세션 상태 업데이트 오류: {e}")

    def try_auto_relogin(self):
        """자동 재로그인 시도"""
        if self.trying_auto_login:
            return  # 이미 시도 중이면 중복 방지

        logger.info("자동 재로그인 시도 중...")
        self.trying_auto_login = True

        login_method = self.settings.value("login_method", "password")

        if login_method == "api_key":
            api_key = self.settings.value("api_key", "")
            if not api_key:
                logger.error("자동 로그인 실패: API 키 없음")
                self.trying_auto_login = False
                return
            self.nai.access_token = api_key
            self.nai.api_key = api_key
            self.nai.login_method = "api_key"
        else:
            access_token = self.settings.value("access_token", "")
            username = self.settings.value("username", "")
            password = self.settings.value("password", "")
            if not all([access_token, username, password]):
                logger.error("자동 로그인 실패: 자격 증명 부족")
                self.trying_auto_login = False
                return
            self.nai.access_token = access_token
            self.nai.username = username
            self.nai.password = password
            self.nai.login_method = "password"

        self.set_statusbar_text("LOGGINGIN")
        from gui_workers import TokenValidateThread
        validate_thread = TokenValidateThread(self)
        validate_thread.validation_result.connect(self.on_login_result)
        validate_thread.start()
    
    def attempt_reconnect(self):
        """연결 복구 시도 - 네트워크 복원력 향상"""
        logger.info("연결 복구 시도 중...")
        
        # 먼저 인터넷 연결 확인
        try:
            socket.create_connection(("www.google.com", 80), timeout=5)
            logger.info("인터넷 연결 확인됨")
        except OSError:
            logger.error("인터넷 연결 없음")
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
                        logger.info("연결 복구 성공 - 재로그인됨")
                        self.set_statusbar_text("LOGINED")
                        self.refresh_anlas()
                        
                        # 세션 관리자 재설정
                        if hasattr(self, 'session_manager'):
                            self.session_manager.consecutive_errors = 0
                            self.session_manager.image_count_since_login = 0
                    else:
                        logger.warning("연결 복구 실패 - 재로그인 필요")
                        # 자동 로그인 옵션 확인 및 시도
                        if self.settings.value("auto_login", False):
                            self.try_auto_relogin()
            except Exception as e:
                logger.error(f"연결 복구 시도 중 오류: {e}")
                QTimer.singleShot(30000, self.attempt_reconnect)  # 30초 후 재시도

    def update_connection_status(self, is_connected: bool, message: str):
        """네트워크 연결 상태 업데이트 — 팝업 없이 상태바 레이블만 사용"""
        from i18n_manager import tr
        
        was_connected = getattr(self, 'last_connected', True)

        if is_connected:
            label_text = "● " + tr('connection.connected')
            self.label_connection_status.setText(label_text)
            self.label_connection_status.setStyleSheet("color: green;")
            self.label_connection_status.setToolTip("")

            if not was_connected:
                # 끊김 → 연결됨 전환
                logger.info("네트워크 연결 복구 감지")
                self._flash_connection_label("lime", "green", label_text)
                if hasattr(self, 'nai') and hasattr(self.nai, 'session_manager'):
                    self.nai.session_manager.network_available = True
                    QTimer.singleShot(5000, self.nai.session_manager.perform_session_check)

            self.network_error_shown = False
        else:
            short_msg = message[:60] + "..." if len(message) > 60 else message
            label_text = "✕ " + short_msg
            self.label_connection_status.setText(label_text)
            self.label_connection_status.setStyleSheet("color: red;")
            self.label_connection_status.setToolTip(message)
            logger.error(f"네트워크 연결 문제: {message}")

            if was_connected:
                # 연결됨 → 끊김 전환
                logger.warning("네트워크 연결 끊김 감지")
                self._flash_connection_label("orange", "red", label_text, message)
                QTimer.singleShot(700, self._set_reconnecting_label)
                if hasattr(self, 'nai') and hasattr(self.nai, 'session_manager'):
                    self.nai.session_manager.network_available = False

        self.last_connected = is_connected

    def _flash_connection_label(self, flash_color: str, final_color: str, final_text: str, final_tooltip: str = ""):
        """상태바 연결 레이블을 짧게 번쩍여 상태 변화를 알림 (팝업 없음)"""
        if self._connection_flash_active:
            return
        self._connection_flash_active = True
        self.label_connection_status.setStyleSheet(f"color: {flash_color}; font-weight: bold;")

        def restore():
            self.label_connection_status.setText(final_text)
            self.label_connection_status.setStyleSheet(f"color: {final_color};")
            if final_tooltip:
                self.label_connection_status.setToolTip(final_tooltip)
            self._connection_flash_active = False

        QTimer.singleShot(600, restore)

    def _set_reconnecting_label(self):
        """연결 끊김 후 재연결 중 상태를 상태바에 표시"""
        from i18n_manager import tr
        
        if not self.last_connected:
            self.label_connection_status.setText("◐ " + tr('connection.reconnecting'))
            self.label_connection_status.setStyleSheet("color: orange;")
