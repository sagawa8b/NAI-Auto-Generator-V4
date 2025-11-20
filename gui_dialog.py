import os
import sys
import re
import webbrowser
import time
import io
from PIL import Image
import numpy as np

from PyQt5.QtWidgets import (QDialog, QLabel, QPushButton, QVBoxLayout,
                             QHBoxLayout, QGroupBox, QFormLayout, QLineEdit,
                             QFileDialog, QMessageBox, QRadioButton,
                             QButtonGroup, QDialogButtonBox, QWidget, QCheckBox,
                             QComboBox, QSlider, QApplication, QSpinBox, QDoubleSpinBox,
                             QColorDialog, QScrollArea)
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QPoint
from PyQt5.QtGui import QFont, QColor, QPalette, QPixmap, QImage, QPainter, QPen, QCursor

from consts import DEFAULT_PATH, DEFAULT_TAGCOMPLETION_PATH

from i18n_manager import tr

from logger import get_logger
logger = get_logger()



class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.auto_login = False
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle(tr('dialogs.login_title'))
        self.setFixedWidth(480)

        main_layout = QVBoxLayout()

        # 로그인 상태 확인
        is_logged_in = hasattr(self.parent, 'nai') and self.parent.nai and self.parent.nai.access_token

        if is_logged_in:
            # 로그인 상태일 때 UI
            login_label = QLabel(tr('dialogs.logged_in'))
            login_label.setAlignment(Qt.AlignCenter)
            
            username_label = QLabel(tr('dialogs.user') + f" {self.parent.nai.username if hasattr(self.parent.nai, 'username') else tr('misc.unknown')}")
            username_label.setAlignment(Qt.AlignCenter)
            
            username_label = QLabel(f"사용자: {self.parent.nai.username if hasattr(self.parent.nai, 'username') else '알 수 없음'}")
            username_label.setAlignment(Qt.AlignCenter)
            
            main_layout.addWidget(login_label)
            main_layout.addSpacing(15)
            main_layout.addWidget(username_label)
            main_layout.addSpacing(15)
            
            # 로그아웃 버튼
            logout_button = QPushButton("로그아웃하기")
            logout_button.clicked.connect(self.on_logout_click)
            
            buttons_layout = QHBoxLayout()
            buttons_layout.addStretch()
            buttons_layout.addWidget(logout_button)
            
            main_layout.addLayout(buttons_layout)
        else:
            # 로그인되지 않은 상태일 때 UI
            login_label = QLabel(tr('dialogs.login_welcome'))
            login_label.setAlignment(Qt.AlignCenter)

            username_label = QLabel(tr('dialogs.username'))
            password_label = QLabel(tr('dialogs.password'))

            self.username_field = QLineEdit()
            self.password_field = QLineEdit()
            self.password_field.setEchoMode(QLineEdit.Password)

            info_label = QLabel(
                "※ 입력하신 아이디와 비밀번호는 Novel AI 서버에만 전송되며,\n이 앱의 서버로 전송되지 않습니다.")
            auto_login_checkbox = QCheckBox("다음에도 자동 로그인")

            form_layout = QFormLayout()
            form_layout.addRow(username_label, self.username_field)
            form_layout.addRow(password_label, self.password_field)

            login_button = QPushButton("로그인하기")

            buttons_layout = QHBoxLayout()
            buttons_layout.addStretch()
            buttons_layout.addWidget(login_button)

            main_layout.addWidget(login_label)
            main_layout.addSpacing(15)
            main_layout.addLayout(form_layout)
            main_layout.addWidget(auto_login_checkbox)
            main_layout.addSpacing(15)
            main_layout.addLayout(buttons_layout)
            main_layout.addSpacing(15)
            main_layout.addWidget(info_label)

            # 이벤트 연결
            login_button.clicked.connect(self.on_login_click)
            auto_login_checkbox.stateChanged.connect(self.on_auto_login)
            self.password_field.returnPressed.connect(self.on_login_click)

            # 자동 로그인 체크박스 초기 상태
            auto_login_value = self.parent.settings.value("auto_login", False)
            if isinstance(auto_login_value, str):
                auto_login_value = auto_login_value.lower() in ('true', 'yes', '1', 't', 'y')
            auto_login_checkbox.setChecked(auto_login_value)

            # 이전 아이디 로딩
            self.username_field.setText(self.parent.settings.value("username", ""))

        self.setLayout(main_layout)

    def on_auto_login(self, state):
        self.auto_login = state == Qt.Checked

    def on_login_click(self):
        username = self.username_field.text()
        password = self.password_field.text()

        if username and password:
            self.parent.set_statusbar_text("LOGGINGIN")

            # 로그인 스레드 생성
            self.login_thread = LoginThread(self.parent, self.parent.nai, username, password)
            self.login_thread.login_result.connect(self.on_login_result)
            self.login_thread.start()

            # 여기서 바로 닫지 않도록 수정
            # self.close()  # 이 줄 주석 처리
        else:
            QMessageBox.critical(self, "오류", "아이디와 비밀번호를 입력해주세요.")
            
    def on_logout_click(self):
        # 로그아웃 처리
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setText("정말 로그아웃 하시겠습니까?")
        msg_box.setWindowTitle("로그아웃 확인")
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg_box.setDefaultButton(QMessageBox.No)
        
        if msg_box.exec_() == QMessageBox.Yes:
            try:
                # 로그아웃 처리 (NAIGenerator에 logout 메서드가 없으므로 직접 처리)
                # 기존 로그인 정보를 리셋합니다
                self.parent.nai.access_token = None
                self.parent.nai.username = None
                self.parent.nai.password = None
                
                # 부모 클래스에서 로그아웃 처리
                self.parent.on_logout()
                self.parent.set_auto_login(False)
                QMessageBox.information(self, "로그아웃 완료", "로그아웃 되었습니다.")
                self.close()
            except Exception as e:
                QMessageBox.critical(self, "로그아웃 오류", f"로그아웃 처리 중 오류가 발생했습니다:\n{str(e)}")

    def on_login_result(self, error_code):
        if error_code == 0:
            QMessageBox.information(self, "로그인 성공", "로그인에 성공했습니다.")
            
            # 로그인 상태 업데이트
            self.parent.label_loginstate.set_logged_in(True)
            self.parent.set_statusbar_text("LOGINED")
            self.parent.set_disable_button(False)
            self.parent.refresh_anlas()
            
            # 로그인 성공 후 창 닫기
            self.close()
        else:
            QMessageBox.critical(
                self, "로그인 실패", "로그인에 실패했습니다.\n아이디와 비밀번호를 확인해주세요.")
            self.close()  # 실패 시에도 창 닫기

    def apply_login_settings(self):
        """로그인 성공 후 UI 설정 적용"""
        if self.auto_login:
            self.parent.set_auto_login(True)
        
        # 로그인 상태 업데이트
        self.parent.set_statusbar_text("LOGINED")
        self.parent.label_loginstate.set_logged_in(True)
        self.parent.set_disable_button(False)
        
        # ANLAS 잔액 새로고침
        self.parent.refresh_anlas()

class OptionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle('옵션')
        self.setup_ui()

    def setup_ui(self):
        self.resize(800, 600)

        # 메인 레이아웃
        main_layout = QVBoxLayout()
       
        # 폴더 경로 설정 그룹
        path_group = QGroupBox("폴더 경로 설정")
        path_layout = QVBoxLayout()
        
        # 로깅 설정 그룹
        log_group = QGroupBox("로그 설정")
        log_layout = QVBoxLayout()

        # 결과 저장 폴더
        output_label = QLabel("결과 저장 폴더:")
        path_results = self.parent.settings.value("path_results", DEFAULT_PATH["path_results"])
        if os.name == 'nt':
            path_results = os.path.normpath(path_results)
        self.output_path = QLineEdit(path_results)
        output_button = QPushButton("찾아보기")
        output_button.clicked.connect(lambda: self.browse_folder("path_results"))
        output_layout = QHBoxLayout()
        output_layout.addWidget(output_label)
        output_layout.addWidget(self.output_path)
        output_layout.addWidget(output_button)
        path_layout.addLayout(output_layout)

        # 세팅 파일 저장 폴더
        settings_label = QLabel("세팅 파일 저장 폴더:")
        self.settings_path = QLineEdit(
            self.parent.settings.value("path_settings", DEFAULT_PATH["path_settings"]))
        settings_button = QPushButton("찾아보기")
        settings_button.clicked.connect(lambda: self.browse_folder("path_settings"))
        settings_layout = QHBoxLayout()
        settings_layout.addWidget(settings_label)
        settings_layout.addWidget(self.settings_path)
        settings_layout.addWidget(settings_button)
        path_layout.addLayout(settings_layout)

        # 와일드카드 파일 폴더
        wildcards_label = QLabel("와일드카드 파일 폴더:")
        self.wildcards_path = QLineEdit(
            self.parent.settings.value("path_wildcards", DEFAULT_PATH["path_wildcards"]))
        wildcards_button = QPushButton("찾아보기")
        wildcards_button.clicked.connect(lambda: self.browse_folder("path_wildcards"))
        wildcards_layout = QHBoxLayout()
        wildcards_layout.addWidget(wildcards_label)
        wildcards_layout.addWidget(self.wildcards_path)
        wildcards_layout.addWidget(wildcards_button)
        path_layout.addLayout(wildcards_layout)

        # 모델 파일 폴더
        #models_label = QLabel("모델 파일 폴더:")
        #self.models_path = QLineEdit(
            #self.parent.settings.value("path_models", DEFAULT_PATH["path_models"]))
        #models_button = QPushButton("찾아보기")
        #models_button.clicked.connect(lambda: self.browse_folder("path_models"))
        #models_layout = QHBoxLayout()
        #models_layout.addWidget(models_label)
        #models_layout.addWidget(self.models_path)
        #models_layout.addWidget(models_button)
        #path_layout.addLayout(models_layout)

        # 디버그 모드 체크박스
        self.debug_mode_checkbox = QCheckBox("디버그 모드 활성화")
        self.debug_mode_checkbox.setToolTip("활성화하면 상세한 로그가 파일에 기록됩니다")
        self.debug_mode_checkbox.setChecked(self.parent.settings.value("debug_mode", False, type=bool))
        log_layout.addWidget(self.debug_mode_checkbox)
        
        # 로그 수준 선택 UI 간소화
        log_level_layout = QHBoxLayout()
        log_level_layout.addWidget(QLabel("로그 상세 수준:"))
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["NORMAL", "DETAILED"])

        # 설정에서 저장된 로그 수준 가져오기
        current_level = self.parent.settings.value("log_level", "NORMAL")
        index = self.log_level_combo.findText(current_level)
        if index >= 0:
            self.log_level_combo.setCurrentIndex(index)

        log_level_layout.addWidget(self.log_level_combo)
        log_layout.addLayout(log_level_layout)

        # 로그 수준 설명 라벨
        log_level_desc = QLabel("NORMAL: 일반적인 작업 정보, DETAILED: 상세한 디버깅 정보")
        log_level_desc.setWordWrap(True)
        log_layout.addWidget(log_level_desc)

        # 로그 폴더 경로
        log_path_layout = QHBoxLayout()
        log_path_layout.addWidget(QLabel("로그 파일 위치:"))
        self.log_path = QLineEdit(self.parent.settings.value("log_folder", os.path.join(os.path.expanduser("~"), "NAI-Auto-Generator", "logs")))
        log_path_layout.addWidget(self.log_path)
        log_path_button = QPushButton("찾아보기")
        log_path_button.clicked.connect(lambda: self.browse_folder("log_folder"))
        log_path_layout.addWidget(log_path_button)
        log_layout.addLayout(log_path_layout)

        # 로그 폴더 열기 버튼
        open_log_layout = QHBoxLayout()
        open_log_button = QPushButton("로그 폴더 열기")
        open_log_button.clicked.connect(self.open_log_folder)
        open_log_layout.addWidget(open_log_button)
        log_layout.addLayout(open_log_layout)

        log_group.setLayout(log_layout)
        main_layout.addWidget(log_group)


        path_group.setLayout(path_layout)
        main_layout.addWidget(path_group)

        # === 연속생성 설정 그룹 추가 ===
        generation_group = QGroupBox("연속생성 설정 (Generation Settings)")
        generation_layout = QVBoxLayout()
        
        # Quick Generation 매수 설정
        quick_gen_layout = QHBoxLayout()
        quick_gen_layout.addWidget(QLabel("Quick Generation 매수:"))
        
        self.quick_gen_5_spinbox = QSpinBox()
        self.quick_gen_5_spinbox.setRange(1, 9999)
        self.quick_gen_5_spinbox.setValue(int(self.parent.settings.value("quick_gen_count_1", 5)))
        quick_gen_layout.addWidget(QLabel("1번 버튼:"))
        quick_gen_layout.addWidget(self.quick_gen_5_spinbox)
        
        self.quick_gen_10_spinbox = QSpinBox()
        self.quick_gen_10_spinbox.setRange(1, 9999)
        self.quick_gen_10_spinbox.setValue(int(self.parent.settings.value("quick_gen_count_2", 10)))
        quick_gen_layout.addWidget(QLabel("2번 버튼:"))
        quick_gen_layout.addWidget(self.quick_gen_10_spinbox)
        
        self.quick_gen_50_spinbox = QSpinBox()
        self.quick_gen_50_spinbox.setRange(1, 9999)
        self.quick_gen_50_spinbox.setValue(int(self.parent.settings.value("quick_gen_count_3", 50)))
        quick_gen_layout.addWidget(QLabel("3번 버튼:"))
        quick_gen_layout.addWidget(self.quick_gen_50_spinbox)
        
        self.quick_gen_100_spinbox = QSpinBox()
        self.quick_gen_100_spinbox.setRange(1, 9999)
        self.quick_gen_100_spinbox.setValue(int(self.parent.settings.value("quick_gen_count_4", 100)))
        quick_gen_layout.addWidget(QLabel("4번 버튼:"))
        quick_gen_layout.addWidget(self.quick_gen_100_spinbox)
        
        generation_layout.addLayout(quick_gen_layout)
        
        # 기본 생성 간격 설정
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("기본 생성 간격(초):"))
        self.default_interval_spinbox = QDoubleSpinBox()
        self.default_interval_spinbox.setRange(0.1, 3600.0)
        self.default_interval_spinbox.setDecimals(1)
        self.default_interval_spinbox.setValue(float(self.parent.settings.value("default_generation_interval", 3.0)))
        interval_layout.addWidget(self.default_interval_spinbox)
        interval_layout.addStretch()
        generation_layout.addLayout(interval_layout)
        
        generation_group.setLayout(generation_layout)
        main_layout.addWidget(generation_group)

        
        # === Theme Settings Group ===
        theme_group = QGroupBox("테마 설정 (Theme Settings)")
        theme_layout = QVBoxLayout()
    
        # Theme selection
        theme_selector_layout = QHBoxLayout()
        theme_selector_layout.addWidget(QLabel("테마 모드:"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["기본 테마 (System Default)", "어두운 모드 (Dark)", "밝은 모드 (Light)"])
        # Load saved theme
        saved_theme = self.parent.settings.value("theme_mode", "기본 테마 (System Default)")
        self.theme_combo.setCurrentText(saved_theme)
        theme_selector_layout.addWidget(self.theme_combo, 1)
        theme_layout.addLayout(theme_selector_layout)

        # Accent color
        self.accent_color_btn = QPushButton("액센트 색상 변경")
        self.accent_color_btn.clicked.connect(self.pick_accent_color)
        theme_layout.addWidget(self.accent_color_btn)
        theme_group.setLayout(theme_layout)        
        main_layout.insertWidget(1, theme_group)  # Insert after font settings
        
        # === 프롬프트 설정 그룹 추가 ===
        prompt_group = QGroupBox("프롬프트 설정")
        prompt_layout = QVBoxLayout()

        # 가중치 하이라이트 활성화 체크박스
        self.emphasis_highlight_checkbox = QCheckBox("가중치 하이라이트 활성화 (::)")
        self.emphasis_highlight_checkbox.setChecked(self.parent.settings.value("emphasis_highlight", True, type=bool))
        self.emphasis_highlight_checkbox.setToolTip("프롬프트 내 가중치 구문(1.5::텍스트::)을 색상으로 강조합니다")
        prompt_layout.addWidget(self.emphasis_highlight_checkbox)

        # 가중치 하이라이트 색상 설정
        colors_layout = QHBoxLayout()
        colors_layout.addWidget(QLabel("강조(>1) 색상:"))
        self.high_emphasis_btn = QPushButton()
        high_emphasis_color = QColor(self.parent.settings.value("high_emphasis_color", "#6495ED"))
        self.high_emphasis_btn.setStyleSheet(f"background-color: {high_emphasis_color.name()}")
        self.high_emphasis_btn.clicked.connect(lambda: self.pick_emphasis_color("high"))
        colors_layout.addWidget(self.high_emphasis_btn)

        colors_layout.addWidget(QLabel("약화(<1) 색상:"))
        self.low_emphasis_btn = QPushButton()
        low_emphasis_color = QColor(self.parent.settings.value("low_emphasis_color", "#A9A9A9"))
        self.low_emphasis_btn.setStyleSheet(f"background-color: {low_emphasis_color.name()}")
        self.low_emphasis_btn.clicked.connect(lambda: self.pick_emphasis_color("low"))
        colors_layout.addWidget(self.low_emphasis_btn)

        prompt_layout.addLayout(colors_layout)

        # 도움말 텍스트
        help_text = QLabel("V4 모델에서는 ::를 사용해 가중치를 직접 지정할 수 있습니다. 예: 1.5::강조할 텍스트::")
        help_text.setWordWrap(True)
        prompt_layout.addWidget(help_text)

        prompt_group.setLayout(prompt_layout)
        main_layout.addWidget(prompt_group)
      
        # 글꼴 설정 그룹
        font_group = QGroupBox("글꼴 설정")
        font_layout = QHBoxLayout()

        font_layout.addWidget(QLabel("글꼴 크기:"))
        self.font_size_spinbox = QSpinBox()
        self.font_size_spinbox.setRange(8, 32)
        self.font_size_spinbox.setValue(int(self.parent.settings.value("nag_font_size", 18)))
        font_layout.addWidget(self.font_size_spinbox)
        font_layout.addStretch()

        font_group.setLayout(font_layout)
        main_layout.addWidget(font_group)

        # === 파일명 설정 그룹 추가 ===
        filename_group = QGroupBox("파일명 설정 (Filename Settings)")
        filename_layout = QVBoxLayout()

        # 파일명 포맷 설정
        format_layout = QVBoxLayout()
        format_label = QLabel("파일명 형식 (Filename Format):")
        format_layout.addWidget(format_label)

        self.filename_format_input = QLineEdit()
        default_format = self.parent.settings.value("filename_format", "[datetime]_[prompt]")
        self.filename_format_input.setText(default_format)
        format_layout.addWidget(self.filename_format_input)

        # 도움말 텍스트
        format_help = QLabel(
            "사용 가능한 플레이스홀더:\n"
            "[datetime] - 날짜+시간 (251118_11240833)\n"
            "[date] - 날짜만 (251118)\n"
            "[time] - 시간만 (11240833)\n"
            "[prompt] - 프롬프트 텍스트\n"
            "[character] - 캐릭터 프롬프트 (첫 번째)\n"
            "[seed] - 시드 값\n"
            "\n예시: [datetime]_[prompt] → 251118_11240833_1girl dancing.png"
        )
        format_help.setWordWrap(True)
        format_help.setStyleSheet("color: gray; font-size: 10px; padding: 5px;")
        format_layout.addWidget(format_help)

        filename_layout.addLayout(format_layout)

        # 프롬프트/캐릭터 길이 제한 설정
        limit_layout = QHBoxLayout()

        limit_layout.addWidget(QLabel("프롬프트 단어 수 제한:"))
        self.prompt_word_limit_spinbox = QSpinBox()
        self.prompt_word_limit_spinbox.setRange(5, 200)
        self.prompt_word_limit_spinbox.setValue(int(self.parent.settings.value("filename_prompt_word_limit", 50)))
        self.prompt_word_limit_spinbox.setToolTip("파일명에 포함할 프롬프트의 최대 문자 수")
        limit_layout.addWidget(self.prompt_word_limit_spinbox)

        limit_layout.addWidget(QLabel("캐릭터 단어 수 제한:"))
        self.character_word_limit_spinbox = QSpinBox()
        self.character_word_limit_spinbox.setRange(5, 200)
        self.character_word_limit_spinbox.setValue(int(self.parent.settings.value("filename_character_word_limit", 30)))
        self.character_word_limit_spinbox.setToolTip("파일명에 포함할 캐릭터 프롬프트의 최대 문자 수")
        limit_layout.addWidget(self.character_word_limit_spinbox)

        limit_layout.addStretch()
        filename_layout.addLayout(limit_layout)

        filename_group.setLayout(filename_layout)
        main_layout.addWidget(filename_group)

        # 태그 설정 그룹
        tag_group = QGroupBox("태그 설정")
        tag_layout = QVBoxLayout()

        # 태그 완성 파일 경로
        tag_file_label = QLabel("태그 자동완성 파일 (Tag Completion File):")
        self.tag_completion_path = QLineEdit(
            self.parent.settings.value("path_tag_completion", DEFAULT_TAGCOMPLETION_PATH))
        tag_file_button = QPushButton("찾아보기")
        tag_file_button.clicked.connect(self.browse_tag_file)
        tag_file_layout = QHBoxLayout()
        tag_file_layout.addWidget(tag_file_label)
        tag_file_layout.addWidget(self.tag_completion_path)
        tag_file_layout.addWidget(tag_file_button)
        tag_layout.addLayout(tag_file_layout)

        # 태그 파일 경로 도움말
        tag_help = QLabel("※ CSV 파일 형식: tag_name[post_count] (한 줄에 하나씩)")
        tag_help.setWordWrap(True)
        tag_help.setStyleSheet("color: gray; font-size: 10px;")
        tag_layout.addWidget(tag_help)

        # 태그 새로고침 버튼
        tag_refresh_button = QPushButton("태그 새로고침")
        tag_refresh_button.setToolTip("태그 목록을 다시 로드합니다.\n태그 파일 변경 후 사용하세요.")
        tag_refresh_button.clicked.connect(self.refresh_tags)
        tag_layout.addWidget(tag_refresh_button)

        tag_group.setLayout(tag_layout)
        main_layout.addWidget(tag_group)
        

        # 저장 & 취소 버튼
        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.save_option)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)

        self.setLayout(main_layout)

    def open_log_folder(self):
        """로그 폴더 열기"""
        log_path = self.log_path.text()
        if not os.path.exists(log_path):
            os.makedirs(log_path, exist_ok=True)
        
        # 운영체제에 맞게 폴더 열기
        try:
            if os.name == 'nt':  # Windows
                os.startfile(log_path)
            elif os.name == 'posix':  # macOS, Linux
                import subprocess
                if sys.platform == 'darwin':  # macOS
                    subprocess.Popen(['open', log_path])
                else:  # Linux
                    subprocess.Popen(['xdg-open', log_path])
        except Exception as e:
            QMessageBox.warning(self, "오류", f"로그 폴더를 열 수 없습니다: {e}")


    def pick_accent_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.parent.settings.setValue("accent_color", color.name())
            self.parent.apply_theme()  # Refresh immediately   
    
    def pick_emphasis_color(self, emphasis_type):
        """가중치 강조 색상 선택"""
        if emphasis_type == "high":
            current_color = QColor(self.parent.settings.value("high_emphasis_color", "#6495ED"))
            button = self.high_emphasis_btn
            setting_key = "high_emphasis_color"
        else:  # low
            current_color = QColor(self.parent.settings.value("low_emphasis_color", "#A9A9A9"))
            button = self.low_emphasis_btn
            setting_key = "low_emphasis_color"
        
        color = QColorDialog.getColor(current_color, self, f"{emphasis_type} 강조 색상 선택")
        if color.isValid():
            self.parent.settings.setValue(setting_key, color.name())
            button.setStyleSheet(f"background-color: {color.name()}")
    
    def update_artifacts_value(self):
        value = self.artifacts_slider.value() / 100.0
        self.artifacts_value.setText(f"{value:.2f}")

    def browse_folder(self, key):
        # 폴더 경로 설정의 LineEdit 위젯 매핑
        path_widgets = {
            "path_results": self.output_path,
            "path_settings": self.settings_path,
            "path_wildcards": self.wildcards_path,
            "log_folder": self.log_path
            # "path_models": self.models_path  # 주석 처리된 경우 제외
        }

        if key not in path_widgets:
            logger.error(f"Error: Unknown path key: {key}")
            return

        current_path = path_widgets[key].text()
        folder = QFileDialog.getExistingDirectory(self, "폴더 선택", current_path)
        if folder:
            # 경로 정규화 - Windows에서는 백슬래시 사용
            if os.name == 'nt':  # Windows
                folder = os.path.normpath(folder)  # 정규화된 경로(백슬래시 사용)

            path_widgets[key].setText(folder)
            # 부모 클래스의 경로 변경 메서드 호출
            self.parent.change_path(key, folder)

    def browse_tag_file(self):
        """태그 자동완성 CSV 파일 선택"""
        current_path = self.tag_completion_path.text()
        current_dir = os.path.dirname(current_path) if current_path else os.getcwd()

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "태그 자동완성 파일 선택",
            current_dir,
            "CSV 파일 (*.csv);;모든 파일 (*.*)"
        )

        if file_path:
            # 경로 정규화 - Windows에서는 백슬래시 사용
            if os.name == 'nt':  # Windows
                file_path = os.path.normpath(file_path)

            self.tag_completion_path.setText(file_path)
            logger.info(f"태그 완성 파일 경로 변경: {file_path}")
    
    def refresh_tags(self):
        """태그 자동 완성 새로고침"""
        # 기존 캐시 초기화
        from gui import CompletionTagLoadThread
        CompletionTagLoadThread.cached_tags = None
        
        # 부모 창의 tags_loaded 플래그 초기화
        if hasattr(self.parent, '_tags_loaded'):
            delattr(self.parent, '_tags_loaded')
        
        # 태그 다시 로드
        self.parent.init_completion(force_reload=True)
        QMessageBox.information(self, "태그 새로고침", "태그 캐시가 성공적으로 새로고침 되었습니다.")
        
    
    def save_option(self):
        
        """
        # V4 모델 설정 저장
        
        self.parent.settings.setValue("v4_model_preset", "Artistic")
        self.parent.settings.setValue("quality_toggle", True)
        self.parent.settings.setValue("dynamic_thresholding", False)
        self.parent.settings.setValue("anti_artifacts", 0.0)
        """
        
        # 로그 설정 저장
        self.parent.settings.setValue("debug_mode", self.debug_mode_checkbox.isChecked())
        self.parent.settings.setValue("log_folder", self.log_path.text())
        log_level = self.log_level_combo.currentText()
        self.parent.settings.setValue("log_level", log_level)
        
        # 로그 수준 변경 적용
        from logger import set_log_level
        set_log_level(log_level.lower())
        
        # 디버그 모드 변경 적용
        from logger import set_debug_mode, initialize_logger
        set_debug_mode(self.debug_mode_checkbox.isChecked())
        initialize_logger(self.log_path.text(), self.debug_mode_checkbox.isChecked())

        
        # 테마 설정 저장
        old_theme = self.parent.settings.value("theme_mode", "기본 테마 (System Default)")
        new_theme = self.theme_combo.currentText()
        self.parent.settings.setValue("theme_mode", new_theme)
        
        # 테마가 변경되었다면 즉시 적용
        if old_theme != new_theme:
            if "어두운" in new_theme:
                # 어두운 테마 설정
                dark_style = """
                QWidget {
                    background-color: #2D2D2D;
                    color: #FFFFFF;
                }
                QLineEdit, QTextEdit, QPlainTextEdit {
                    background-color: #404040;
                    color: #FFFFFF;
                    border: 1px solid #555555;
                }
                QComboBox, QComboBox QAbstractItemView {
                    background-color: #404040;
                    color: #FFFFFF;
                }
                QLabel, QCheckBox, QRadioButton, QGroupBox {
                    color: #FFFFFF;
                }
                """
                self.parent.app.setStyleSheet(dark_style)
                
                # 팔레트 설정
                dark_palette = QPalette()
                dark_palette.setColor(QPalette.Window, QColor("#2D2D2D"))
                dark_palette.setColor(QPalette.WindowText, QColor("#FFFFFF"))
                dark_palette.setColor(QPalette.Base, QColor("#404040"))
                dark_palette.setColor(QPalette.Text, QColor("#FFFFFF"))
                dark_palette.setColor(QPalette.Button, QColor("#353535"))
                dark_palette.setColor(QPalette.ButtonText, QColor("#FFFFFF"))
                self.parent.app.setPalette(dark_palette)
            else:
                # 밝은 테마나 기본 테마로 복원
                self.parent.app.setStyleSheet("")
                self.parent.app.setPalette(self.parent.palette)
        
        # 가중치 하이라이트 설정 저장
        self.parent.settings.setValue("emphasis_highlight", self.emphasis_highlight_checkbox.isChecked())
        
        # UI에 설정 적용
        for prompt_edit in [self.parent.dict_ui_settings["prompt"], self.parent.dict_ui_settings["negative_prompt"]]:
            if hasattr(prompt_edit, "setEmphasisHighlighting"):
                prompt_edit.setEmphasisHighlighting(self.emphasis_highlight_checkbox.isChecked())
                # 색상 설정도 적용
                emphasis_colors = {
                    "high": QColor(self.parent.settings.value("high_emphasis_color", "#6495ED")),
                    "low": QColor(self.parent.settings.value("low_emphasis_color", "#A9A9A9"))
                }
                prompt_edit.setEmphasisColors(emphasis_colors)
      
        """
        # 태거 모델 선택 저장
        model_text = self.tagger_combo.currentText()
        selected_model = model_text.split(" (설치됨)")[0] if "(설치됨)" in model_text else ""
        if selected_model == "-- 모델 없음 --":
            selected_model = ""
        self.parent.settings.setValue("selected_tagger_model", selected_model)
        self.parent.settings.setValue("will_complete_tag", self.tagger_check.isChecked())
        
        
        
        # 파일 이름 정책 저장
        self.parent.settings.setValue("will_savename_prompt", self.save_with_prompt.isChecked())
        self.parent.settings.setValue("will_savename_i2i", self.save_with_i2iname.isChecked())
        """

        # 글꼴 설정 저장
        self.parent.settings.setValue("nag_font_size", self.font_size_spinbox.value())
        self.parent.apply_theme()

        # 파일명 설정 저장
        self.parent.settings.setValue("filename_format", self.filename_format_input.text())
        self.parent.settings.setValue("filename_prompt_word_limit", self.prompt_word_limit_spinbox.value())
        self.parent.settings.setValue("filename_character_word_limit", self.character_word_limit_spinbox.value())

        # 연속생성 설정 저장
        self.parent.settings.setValue("quick_gen_count_1", self.quick_gen_5_spinbox.value())
        self.parent.settings.setValue("quick_gen_count_2", self.quick_gen_10_spinbox.value())
        self.parent.settings.setValue("quick_gen_count_3", self.quick_gen_50_spinbox.value())
        self.parent.settings.setValue("quick_gen_count_4", self.quick_gen_100_spinbox.value())
        self.parent.settings.setValue("default_generation_interval", self.default_interval_spinbox.value())

        # 태그 완성 파일 경로 저장
        old_tag_path = self.parent.settings.value("path_tag_completion", DEFAULT_TAGCOMPLETION_PATH)
        new_tag_path = self.tag_completion_path.text()
        self.parent.settings.setValue("path_tag_completion", new_tag_path)

        # 태그 파일 경로가 변경되었다면 캐시 초기화 및 재로드 제안
        if old_tag_path != new_tag_path:
            from gui import CompletionTagLoadThread
            CompletionTagLoadThread.cached_tags = None
            if hasattr(self.parent, '_tags_loaded'):
                delattr(self.parent, '_tags_loaded')
            logger.info(f"태그 완성 파일 경로 변경됨: {old_tag_path} -> {new_tag_path}")

            # 사용자에게 재로드 제안
            reply = QMessageBox.question(
                self,
                "태그 파일 경로 변경",
                "태그 완성 파일 경로가 변경되었습니다.\n지금 태그를 다시 로드하시겠습니까?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            if reply == QMessageBox.Yes:
                self.parent.init_completion(force_reload=True)
                QMessageBox.information(self, "태그 새로고침", "태그가 성공적으로 새로고침 되었습니다.")

        self.accept()
        
        
    def on_model_downloaded(self, model_name):
        # 다운로드 완료 후 모델 리스트 업데이트
        self.tagger_combo.addItem(model_name + " (설치됨)")
        self.tagger_combo.setCurrentText(model_name + " (설치됨)")
        QMessageBox.information(self, "모델 다운로드", f"{model_name} 모델이 성공적으로 다운로드되었습니다.")

class GenerateDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.count = "100"  # 기본값
        self.delay = "3"    # 기본값
        self.ignore_error = False  # 기본값
        self.setup_ui()
        self.setWindowTitle(tr('generate_dialog.title'))

    def setup_ui(self):
        main_layout = QVBoxLayout()

        # 연속생성 매수 영역 (원클릭 생성) - 설정값 반영
        preset_group = QGroupBox(tr('generate_dialog.preset_group'))
        preset_layout = QHBoxLayout()
        preset_group.setLayout(preset_layout)

        # 설정에서 매수값 가져오기
        count_1 = self.parent.settings.value("quick_gen_count_1", 5, type=int)
        count_2 = self.parent.settings.value("quick_gen_count_2", 10, type=int)
        count_3 = self.parent.settings.value("quick_gen_count_3", 50, type=int)
        count_4 = self.parent.settings.value("quick_gen_count_4", 100, type=int)

        # 프리셋 버튼들 - 동적 텍스트
        self.preset_1_btn = QPushButton(f"{count_1}장")
        self.preset_2_btn = QPushButton(f"{count_2}장")
        self.preset_3_btn = QPushButton(f"{count_3}장")
        self.preset_4_btn = QPushButton(f"{count_4}장")

        # 버튼 이벤트 연결 - 설정값 사용
        self.preset_1_btn.clicked.connect(lambda: self.quick_start(str(count_1)))
        self.preset_2_btn.clicked.connect(lambda: self.quick_start(str(count_2)))
        self.preset_3_btn.clicked.connect(lambda: self.quick_start(str(count_3)))
        self.preset_4_btn.clicked.connect(lambda: self.quick_start(str(count_4)))

        preset_layout.addWidget(self.preset_1_btn)
        preset_layout.addWidget(self.preset_2_btn)
        preset_layout.addWidget(self.preset_3_btn)
        preset_layout.addWidget(self.preset_4_btn)
        
        main_layout.addWidget(preset_group)

        # 연속생성 수동 입력 영역
        custom_group = QGroupBox(tr('generate_dialog.manual_group'))
        custom_layout = QVBoxLayout()
        custom_group.setLayout(custom_layout)

        # 기존의 수동 입력 필드
        count_layout = QHBoxLayout()
        count_layout.addWidget(QLabel(tr('generate_dialog.count_label')))
        self.count_edit = QLineEdit('100')
        count_layout.addWidget(self.count_edit)
        count_desc = QLabel(tr('generate_dialog.count_unlimited'))
        count_layout.addWidget(count_desc)
        custom_layout.addLayout(count_layout)

        main_layout.addWidget(custom_group)

        # 기타 설정 영역
        settings_group = QGroupBox(tr('generate_dialog.settings_group'))
        settings_layout = QVBoxLayout()
        settings_group.setLayout(settings_layout)

        # 생성 간격 - 기본값을 설정에서 가져오기
        delay_layout = QHBoxLayout()
        delay_layout.addWidget(QLabel(tr('generate_dialog.delay_label')))
        default_interval = self.parent.settings.value("default_generation_interval", 3.0, type=float)
        self.delay_edit = QLineEdit(str(default_interval))
        delay_layout.addWidget(self.delay_edit)
        settings_layout.addLayout(delay_layout)

        # 체크박스
        self.ignore_error_checkbox = QCheckBox(tr('generate_dialog.ignore_error'))
        settings_layout.addWidget(self.ignore_error_checkbox)

        main_layout.addWidget(settings_group)

        # 버튼
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept_and_set)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)

        self.setLayout(main_layout)

    def quick_start(self, count):
        """프리셋 버튼 클릭 시 값 설정 후 즉시 생성 시작"""
        # 값 설정
        self.count = count
        self.delay = self.delay_edit.text()
        self.ignore_error = self.ignore_error_checkbox.isChecked()
        
        # 다이얼로그 종료 및 생성 시작
        self.accept()

    def accept_and_set(self):
        """확인 버튼 클릭 시 값 설정"""
        self.count = self.count_edit.text()
        self.delay = self.delay_edit.text()
        self.ignore_error = self.ignore_error_checkbox.isChecked()
        self.accept()


class MiniUtilDialog(QDialog):
    def __init__(self, parent=None, mode="getter"):
        super().__init__(parent)
        self.parent = parent
        self.mode = mode
        self.setup_ui()

    def setup_ui(self):
        if self.mode == "getter":
            self.setWindowTitle('이미지 정보 확인기')
            self.resize(800, 400)

            main_layout = QVBoxLayout()

            info_label = QLabel(
                "Novel AI로 생성된 이미지 파일을 드래그앤드롭 해보세요.")
            info_label.setAlignment(Qt.AlignCenter)
            main_layout.addWidget(info_label)

            self.result_box = QLabel("")
            self.result_box.setAlignment(Qt.AlignCenter)
            main_layout.addWidget(self.result_box)

            close_button = QPushButton("닫기")
            close_button.clicked.connect(self.close)
            main_layout.addWidget(close_button)

            self.setLayout(main_layout)
            self.setAcceptDrops(True)

        elif self.mode == "tagger":
            self.setWindowTitle('단부루 태거')
            self.resize(800, 400)

            main_layout = QVBoxLayout()
            
            info_label = QLabel(
                "태그를 확인할 이미지를 드래그앤드롭 해보세요. 오래 걸릴 수 있습니다.")
            info_label.setAlignment(Qt.AlignCenter)
            main_layout.addWidget(info_label)

            self.result_box = QLabel("")
            self.result_box.setAlignment(Qt.AlignCenter)
            main_layout.addWidget(self.result_box)

            close_button = QPushButton("닫기")
            close_button.clicked.connect(self.close)
            main_layout.addWidget(close_button)

            self.setLayout(main_layout)
            self.setAcceptDrops(True)

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

        file_path = files[0].toLocalFile()
        if not (file_path.endswith(".png") or file_path.endswith(".webp") or file_path.endswith(".jpg")):
            QMessageBox.information(self, '경고', "이미지 파일만 가능합니다.")
            return

        if self.mode == "getter":
            try:
                self.result_box.setText("정보를 불러오는 중...")
                QApplication.processEvents()

                self.parent.get_image_info_bysrc(file_path)
                self.result_box.setText("정보를 불러왔습니다.")
            except Exception as e:
                QMessageBox.critical(
                    self, "오류", f"파일을 처리하는 중 오류가 발생했습니다:\n{str(e)}")
                self.result_box.setText("실패했습니다.")

        elif self.mode == "tagger":
            try:
                self.result_box.setText("태그 분석 중...")
                QApplication.processEvents()

                result = self.parent.predict_tag_from("src", file_path, True)
                self.result_box.setText(result if result else "태그를 찾을 수 없습니다.")
            except Exception as e:
                QMessageBox.critical(
                    self, "오류", f"파일을 처리하는 중 오류가 발생했습니다:\n{str(e)}")
                self.result_box.setText("실패했습니다.")


class FileIODialog(QDialog):
    def __init__(self, message, function):
        super().__init__()
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.message = message
        self.function = function
        self.result = None
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("처리 중...")
        self.resize(300, 100)

        layout = QVBoxLayout()
        self.label = QLabel(self.message)
        layout.addWidget(self.label)

        self.setLayout(layout)

    def showEvent(self, event):
        super().showEvent(event)
        self.thread = WorkerThread(self.function)
        self.thread.finished.connect(self.on_finished)
        self.thread.start()

    def on_finished(self):
        self.result = self.thread.result
        self.accept()


class LoginThread(QThread):
    login_result = pyqtSignal(int)

    def __init__(self, parent, nai, username, password):
        super(LoginThread, self).__init__(parent)
        self.nai = nai
        self.username = username
        self.password = password
        self.auto_login = parent.settings.value("auto_login", False)

    def run(self):
        is_login_success = self.nai.try_login(self.username, self.password)

        if is_login_success:
            self.parent().set_auto_login(self.auto_login)
            self.login_result.emit(0)  # 성공
        else:
            self.login_result.emit(1)  # 실패


class WorkerThread(QThread):
    def __init__(self, function):
        super(WorkerThread, self).__init__()
        self.function = function
        self.result = None

    def run(self):
        self.result = self.function()


class MaskCanvas(QLabel):
    """Canvas widget for painting inpainting masks with 8x8 grid"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_dialog = parent
        self.image = None
        self.mask = None
        self.drawing = False
        self.last_grid_pos = None  # Track last grid position (not pixel position)
        self.brush_size = 1  # Grid cells (not pixels)
        self.grid_data = None  # 2D array of grid cells
        self.grid_width = 0
        self.grid_height = 0
        self.setMouseTracking(True)
        self.setCursor(QCursor(Qt.CrossCursor))

    def set_image(self, pil_image):
        """Set the base image to paint mask on"""
        self.image = pil_image.copy()

        # Initialize grid data structure (like NAIA2.0's mirror_image)
        w, h = self.image.size
        self.grid_width = w // 8
        self.grid_height = h // 8
        self.grid_data = [[0 for _ in range(self.grid_height)] for _ in range(self.grid_width)]

        # Create blank GRAYSCALE mask (pure black = 0)
        # CRITICAL: Use 'L' mode (grayscale), NOT 'RGBA', to avoid color bleeding
        self.mask = Image.new('L', self.image.size, 0)

        logger.info(f"Initialized grid canvas: {w}×{h} pixels = {self.grid_width}×{self.grid_height} grid cells")

        # Convert PIL image to QPixmap for display
        self.update_display()

    def update_display(self):
        """Update the displayed image with mask overlay and grid"""
        if self.image is None or self.mask is None:
            return

        # Create composite image with mask overlay
        display_image = self.image.copy().convert('RGBA')

        # Create red semi-transparent overlay for masked areas
        # Use grayscale mask values to create overlay
        mask_array = np.array(self.mask)  # Now pure grayscale
        overlay = np.zeros((*mask_array.shape, 4), dtype=np.uint8)
        overlay[mask_array > 0] = [255, 0, 0, 128]  # Red with 50% alpha where mask is white

        overlay_image = Image.fromarray(overlay, 'RGBA')
        display_image = Image.alpha_composite(display_image, overlay_image)

        # Convert to QPixmap
        img_byte_array = io.BytesIO()
        display_image.save(img_byte_array, format='PNG')
        qimage = QImage.fromData(img_byte_array.getvalue())
        pixmap = QPixmap.fromImage(qimage)

        # Draw 8×8 grid overlay
        painter = QPainter(pixmap)
        painter.setPen(QPen(QColor(0, 255, 0, 80), 1, Qt.SolidLine))  # Semi-transparent green

        # Draw vertical lines
        for gx in range(self.grid_width + 1):
            x = gx * 8
            painter.drawLine(x, 0, x, self.image.size[1])

        # Draw horizontal lines
        for gy in range(self.grid_height + 1):
            y = gy * 8
            painter.drawLine(0, y, self.image.size[0], y)

        painter.end()

        self.setPixmap(pixmap)
        self.resize(pixmap.size())

    def pixel_to_grid(self, pixel_x, pixel_y):
        """Convert pixel coordinates to grid coordinates"""
        gx = pixel_x // 8
        gy = pixel_y // 8
        # Clamp to grid boundaries
        gx = max(0, min(gx, self.grid_width - 1))
        gy = max(0, min(gy, self.grid_height - 1))
        return gx, gy

    def fill_grid_cell(self, gx, gy):
        """Fill grid cells based on brush size (brush_size × brush_size area)"""
        # Calculate brush area - centered on clicked cell
        half_brush = self.brush_size // 2

        # Get mask array once for efficiency
        mask_array = np.array(self.mask)
        w, h = self.image.size

        # Fill brush_size × brush_size area of grid cells
        for offset_y in range(-half_brush, half_brush + (self.brush_size % 2)):
            for offset_x in range(-half_brush, half_brush + (self.brush_size % 2)):
                target_gx = gx + offset_x
                target_gy = gy + offset_y

                # Check bounds
                if target_gx < 0 or target_gx >= self.grid_width or target_gy < 0 or target_gy >= self.grid_height:
                    continue

                # Mark grid cell as painted
                self.grid_data[target_gx][target_gy] = 1

                # Fill corresponding 8×8 block in mask
                y1 = target_gy * 8
                y2 = min((target_gy + 1) * 8, h)
                x1 = target_gx * 8
                x2 = min((target_gx + 1) * 8, w)

                # Fill block in mask (pure grayscale white = 255)
                mask_array[y1:y2, x1:x2] = 255

        # Update mask image once after all cells filled
        self.mask = Image.fromarray(mask_array, mode='L')

    def draw_grid_line(self, start_gx, start_gy, end_gx, end_gy):
        """Draw a line on the grid using Bresenham's algorithm"""
        # Bresenham's line algorithm for grid cells
        dx = abs(end_gx - start_gx)
        dy = abs(end_gy - start_gy)
        sx = 1 if start_gx < end_gx else -1
        sy = 1 if start_gy < end_gy else -1
        err = dx - dy

        gx, gy = start_gx, start_gy

        while True:
            self.fill_grid_cell(gx, gy)

            if gx == end_gx and gy == end_gy:
                break

            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                gx += sx
            if e2 < dx:
                err += dx
                gy += sy

    def mousePressEvent(self, event):
        """Handle mouse press to start drawing"""
        if event.button() == Qt.LeftButton and self.mask is not None:
            self.drawing = True
            gx, gy = self.pixel_to_grid(event.pos().x(), event.pos().y())
            self.last_grid_pos = (gx, gy)
            self.fill_grid_cell(gx, gy)
            self.update_display()

    def mouseMoveEvent(self, event):
        """Handle mouse move to draw mask"""
        if self.drawing and self.mask is not None:
            gx, gy = self.pixel_to_grid(event.pos().x(), event.pos().y())
            if self.last_grid_pos and (gx, gy) != self.last_grid_pos:
                # Draw line from last grid position to current
                self.draw_grid_line(self.last_grid_pos[0], self.last_grid_pos[1], gx, gy)
                self.update_display()
            self.last_grid_pos = (gx, gy)

    def mouseReleaseEvent(self, event):
        """Handle mouse release to stop drawing"""
        if event.button() == Qt.LeftButton:
            self.drawing = False
            self.last_grid_pos = None

    def clear_mask(self):
        """Clear the entire mask"""
        if self.mask is not None:
            # Reset grid data
            self.grid_data = [[0 for _ in range(self.grid_height)] for _ in range(self.grid_width)]
            # Reset to black grayscale mask (0 = preserve, 255 = inpaint)
            self.mask = Image.new('L', self.image.size, 0)
            self.update_display()
            logger.info("Cleared mask grid")

    def get_mask(self):
        """Get the current mask as PIL Image"""
        return self.mask.copy() if self.mask else None

    def set_brush_size(self, size):
        """Set the brush size for painting (grid cells, not pixels)"""
        self.brush_size = max(1, size)  # At least 1 grid cell

    def set_mask(self, mask):
        """Set an existing mask to continue editing"""
        if mask is not None and self.image is not None:
            # Ensure mask size matches image size
            if mask.size != self.image.size:
                mask = mask.resize(self.image.size, Image.LANCZOS)
            self.mask = mask.copy()

            # Rebuild grid_data from mask
            # Check each 8×8 block to see if it's painted
            mask_array = np.array(self.mask)
            w, h = self.image.size

            for gx in range(self.grid_width):
                for gy in range(self.grid_height):
                    y1 = gy * 8
                    y2 = min((gy + 1) * 8, h)
                    x1 = gx * 8
                    x2 = min((gx + 1) * 8, w)

                    block = mask_array[y1:y2, x1:x2]
                    # If ANY pixel in block is white (>127), mark grid cell as painted
                    if mask_array.ndim == 2 and np.any(block > 127):
                        self.grid_data[gx][gy] = 1

            self.update_display()
            logger.info("Loaded existing mask into grid canvas")


class MaskPaintDialog(QDialog):
    """Dialog for painting inpainting masks on images"""

    def __init__(self, parent=None, image=None, existing_mask=None):
        super().__init__(parent)
        self.image = image
        self.mask = None
        self.existing_mask = existing_mask
        self.setup_ui()

        if self.image:
            self.canvas.set_image(self.image)

            # Load existing mask if provided
            if self.existing_mask:
                self.canvas.set_mask(self.existing_mask)

    def setup_ui(self):
        """Setup the mask painting UI"""
        self.setWindowTitle(tr('dialogs.mask_paint_title'))
        self.resize(900, 700)

        main_layout = QVBoxLayout()

        # Title and instructions
        title_label = QLabel(tr('dialogs.mask_paint_instruction'))
        title_label.setStyleSheet("font-size: 12pt; font-weight: bold;")
        title_label.setWordWrap(True)
        main_layout.addWidget(title_label)

        # Canvas area with scroll
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(False)
        scroll_area.setStyleSheet("background-color: #2b2b2b;")

        self.canvas = MaskCanvas(self)
        scroll_area.setWidget(self.canvas)
        main_layout.addWidget(scroll_area)

        # Controls
        controls_layout = QHBoxLayout()

        # Brush size control
        brush_size_label = QLabel(tr('dialogs.mask_brush_size'))
        controls_layout.addWidget(brush_size_label)

        self.brush_size_slider = QSlider(Qt.Horizontal)
        self.brush_size_slider.setMinimum(1)
        self.brush_size_slider.setMaximum(20)
        self.brush_size_slider.setValue(3)
        self.brush_size_slider.valueChanged.connect(self.on_brush_size_changed)
        self.brush_size_slider.setMaximumWidth(200)
        controls_layout.addWidget(self.brush_size_slider)

        self.brush_size_value_label = QLabel("3")
        self.brush_size_value_label.setStyleSheet("font-weight: bold; min-width: 50px;")
        controls_layout.addWidget(self.brush_size_value_label)

        # Set initial brush size on canvas
        self.canvas.set_brush_size(3)

        controls_layout.addStretch()

        # Invert mask checkbox
        self.invert_mask_checkbox = QCheckBox(tr('dialogs.mask_invert'))
        self.invert_mask_checkbox.setToolTip(tr('dialogs.mask_invert_tooltip'))
        controls_layout.addWidget(self.invert_mask_checkbox)

        # Clear button
        clear_button = QPushButton(tr('dialogs.mask_clear'))
        clear_button.clicked.connect(self.on_clear_clicked)
        controls_layout.addWidget(clear_button)

        main_layout.addLayout(controls_layout)

        # Dialog buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_button = QPushButton(tr('dialogs.cancel'))
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        ok_button = QPushButton(tr('dialogs.ok'))
        ok_button.setDefault(True)
        ok_button.clicked.connect(self.on_ok_clicked)
        button_layout.addWidget(ok_button)

        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)

    def on_brush_size_changed(self, value):
        """Handle brush size slider change"""
        self.canvas.set_brush_size(value)
        # Value represents grid cells (each cell = 8×8 pixels)
        self.brush_size_value_label.setText(f"{value}")

    def on_clear_clicked(self):
        """Handle clear button click"""
        reply = QMessageBox.question(
            self,
            tr('dialogs.confirm'),
            tr('dialogs.mask_clear_confirm'),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.canvas.clear_mask()

    def on_ok_clicked(self):
        """Handle OK button click"""
        self.mask = self.canvas.get_mask()

        # Check if mask is empty
        if self.mask:
            mask_array = np.array(self.mask)

            # Check if grayscale mask has any painted areas
            if mask_array.ndim == 2:  # Grayscale 'L' mode
                if mask_array.max() == 0:
                    QMessageBox.warning(
                        self,
                        tr('dialogs.warning'),
                        tr('dialogs.mask_empty_warning')
                    )
                    return

                # Apply binary threshold (ensure only 0 or 255 values)
                # 0 = preserve (black), 255 = inpaint (white)
                mask_binary = np.where(mask_array > 127, 255, 0).astype(np.uint8)

                logger.info("Binary threshold applied to grayscale mask - ensuring clean edges")

                # Apply mask inversion if checkbox is checked
                if self.invert_mask_checkbox.isChecked():
                    # Invert grayscale: white becomes black, black becomes white
                    mask_binary = 255 - mask_binary
                    logger.info("Mask inverted: painted areas will be KEPT, unpainted areas will be INPAINTED")
                else:
                    logger.info("Mask not inverted: painted areas will be INPAINTED")

                self.mask = Image.fromarray(mask_binary, mode='L')
            else:
                # Fallback for non-grayscale masks (shouldn't happen)
                logger.warning(f"Mask is not in grayscale 'L' format, unexpected (shape: {mask_array.shape})")
                return

        self.accept()

    def get_mask(self):
        """Get the painted mask"""
        return self.mask
