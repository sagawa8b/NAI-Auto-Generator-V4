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
import numpy as np
from io import BytesIO
from PIL import Image
from urllib import request

from i18n_manager import i18n, tr

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                            QPushButton, QPlainTextEdit, QScrollArea, QFrame,
                            QGridLayout, QDialog, QCheckBox, QButtonGroup, QSizePolicy,
                            QMainWindow, QAction, QFileDialog, QMessageBox, QApplication,
                            QActionGroup, QProgressBar)
from PyQt5.QtCore import (Qt, pyqtSignal, QObject, QTimer, QSettings, QPoint, QSize, 
                          QCoreApplication, QThread)
from PyQt5.QtGui import QColor, QPalette, QFont

from gui_init import init_main_widget, _populate_resolution_combo
from gui_dialog import LoginDialog, OptionDialog, GenerateDialog, MiniUtilDialog, FileIODialog
from gui_utils import (resource_path, create_folder_if_not_exists, prettify_dict,
                       get_imgcount_from_foldersrc, pick_imgsrc_from_foldersrc,
                       strtobool, pickedit_lessthan_str, create_windows_filepath,
                       inject_imagetag, get_filename_only, convert_qimage_to_imagedata,
                       MAX_COUNT_FOR_WHILE)
from gui_credentials import save_credential, load_credential, delete_credential
from gui_workers import (CompletionTagLoadThread, AutoGenerateThread, GenerateThread,
                         TokenValidateThread, AnlasThread, _threadfunc_generate_image)
from gui_network import NetworkMonitor, NetworkMixin
from gui_settings_io import SettingsIOMixin
from gui_image_handlers import ImageHandlersMixin
from gui_enhance import EnhanceMixin
from gui_generation import GenerationMixin

from consts import COLOR, DEFAULT_PARAMS, DEFAULT_PATH, RESOLUTION_FAMILIY_MASK, RESOLUTION_FAMILIY, prettify_naidict, DEFAULT_TAGCOMPLETION_PATH, DEFAULT_CUSTOM_RESOLUTIONS

import naiinfo_getter
from nai_generator import NAIGenerator, NAIAction, NAISessionManager
from wildcard_applier import WildcardApplier
from danbooru_tagger import DanbooruTagger
from completer import parse_tag_line, format_tag_display, TagData
from logger import get_logger
logger = get_logger()


TITLE_NAME = "NAI Auto Generator V4.5_2.6.04.28"
TOP_NAME = "dcp_arca"
APP_NAME = "nag_gui"

#############################################

# 디버깅용 로그 추가
logger.error(f"Current directory: {os.getcwd()}")
logger.error(f"MEIPASS exists: {'sys._MEIPASS' in dir(sys)}")
if 'sys._MEIPASS' in dir(sys):
    logger.error(f"MEIPASS path: {sys._MEIPASS}")



class NAIAutoGeneratorWindow(QMainWindow, NetworkMixin, SettingsIOMixin, ImageHandlersMixin, EnhanceMixin, GenerationMixin):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.palette = self.palette()
        self.is_initializing = True
        self.is_expand = True

        # Character Reference 관련 변수 추가
        self.character_reference_visible = False
        self.character_reference_image = None
        self.character_reference_path = None
        self.character_reference_style_aware = True
        self.character_reference_fidelity = 1.0  # Fidelity 기본값 1.0

        # Image to Image 관련 변수 추가
        self.img2img_visible = False
        self.img2img_image = None
        self.img2img_path = None
        self.img2img_strength = 0.5  # 기본값 0.5
        self.img2img_noise = 0.0  # 기본값 0.0

        # Inpainting 관련 변수 추가
        self.inpaint_mode = False  # Inpainting 모드 활성화 여부
        self.inpaint_mask = None   # 페인트된 마스크 이미지

        # Image Enhance 관련 변수 추가
        self.enhance_visible = False
        self.enhance_image = None
        self.enhance_path = None
        self.enhance_metadata = None  # Enhancement 이미지의 메타데이터 저장
        self.enhance_strength = 0.4  # 기본값 0.4 (0.01-0.99)
        self.enhance_noise = 0.0  # 기본값 0.0 (0.00-0.99)
        self.enhance_ratio = 1.5  # 기본값 1.5x (1.0 or 1.5)

        # Bulk Enhancement 관련 변수 추가
        self.enhance_folder_path = None  # 선택된 폴더 경로
        self.enhance_image_list = []  # 처리할 이미지 파일 목록
        self.enhance_current_index = 0  # 현재 처리 중인 이미지 인덱스
        self.enhance_bulk_mode = False  # 벌크 모드 활성화 여부
        self.enhance_bulk_thread = None  # 벌크 처리 스레드
        self.enhance_bulk_stopped = False  # 벌크 처리 중단 플래그

        self.last_generated_image = None  # 마지막 생성된 이미지 저장

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
        self._connection_flash_active = False
        self.network_error_shown = False

        # 언어 초기화 (기존 코드의 적절한 위치에 추가)
        saved_language = self.settings.value("language", "ko")
        i18n.set_language(saved_language)
        
        # 언어 변경 시그널 연결
        i18n.language_changed.connect(self.on_language_changed)
        
        
        # 테마 적용
        self.apply_theme()

        # 저장된 오버레이 텍스트 색상 적용
        overlay_color = self.settings.value("overlay_text_color", "#ffffff")
        if hasattr(self, 'image_result'):
            self.image_result.apply_overlay_color(overlay_color)
        
        # 라벨 생성 - 상태바에 추가
        self.label_connection_status = QLabel(tr('connection.server') + " " + tr('connection.checking'))
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

        # Main splitter 상태 복원
        saved_state = self.settings.value("splitterSizes")
        if saved_state:
            try:
                self.main_splitter.restoreState(saved_state)
                # Ensure right panel visibility matches is_expand state
                right_visible = sum(self.main_splitter.sizes()[1:]) > 0
                self.is_expand = right_visible
            except Exception as e:
                logger.error(f"Error restoring main splitter: {e}")
                self.set_default_splitter()
        else:
            self.set_default_splitter()

        # 각 개별 스플리터 상태 복원
        self.restore_individual_splitters()

    def restore_individual_splitters(self):
        """모든 개별 스플리터의 저장된 상태를 복원"""
        # Prompt splitter (Prompt ↔ Negative Prompt) 복원
        if hasattr(self, 'prompt_splitter'):
            saved_state = self.settings.value("promptSplitterSizes")
            if saved_state:
                try:
                    self.prompt_splitter.restoreState(saved_state)
                    logger.info("Prompt splitter state restored")
                except Exception as e:
                    logger.error(f"Error restoring prompt splitter: {e}")

        # Prompt-Character splitter 복원
        if hasattr(self, 'prompt_char_splitter'):
            saved_state = self.settings.value("promptCharSplitterSizes")
            if saved_state:
                try:
                    self.prompt_char_splitter.restoreState(saved_state)
                    logger.info("Prompt-Character splitter state restored")
                except Exception as e:
                    logger.error(f"Error restoring prompt-character splitter: {e}")

        # Settings splitter 복원
        if hasattr(self, 'settings_splitter'):
            saved_state = self.settings.value("settingsSplitterSizes")
            if saved_state:
                try:
                    self.settings_splitter.restoreState(saved_state)
                    logger.info("Settings splitter state restored")
                except Exception as e:
                    logger.error(f"Error restoring settings splitter: {e}")

        # Main vertical splitter 복원
        if hasattr(self, 'main_vertical_splitter'):
            saved_state = self.settings.value("mainVerticalSplitterSizes")
            if saved_state:
                try:
                    self.main_vertical_splitter.restoreState(saved_state)
                    logger.info("Main vertical splitter state restored")
                except Exception as e:
                    logger.error(f"Error restoring main vertical splitter: {e}")

        # Right vertical splitter 복원
        if hasattr(self, 'right_vertical_splitter'):
            saved_state = self.settings.value("rightVerticalSplitterSizes")
            if saved_state:
                try:
                    self.right_vertical_splitter.restoreState(saved_state)
                    logger.info("Right vertical splitter state restored")
                except Exception as e:
                    logger.error(f"Error restoring right vertical splitter: {e}")

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
            
        # Character Reference 테마 적용 추가
        self.apply_character_reference_theme(theme_mode, font_size)

    def apply_character_reference_theme(self, theme_mode, font_size):
        """Character Reference UI에 현재 테마 적용"""
        if not hasattr(self, 'character_reference_widget'):
            return
        
        is_dark = "어두운" in theme_mode
        
        if is_dark:
            # 어두운 테마
            widget_bg = "#2D2D2D"
            text_color = "#FFFFFF"
            border_color = "#444444"
            image_bg = "#1a1a1a"
            button_bg = "#404040"
            button_hover = "#4a4a4a"
        else:
            # 밝은 테마
            widget_bg = "#FFFFFF"
            text_color = "#000000"
            border_color = "#CCCCCC"
            image_bg = "#F5F5F5"
            button_bg = "#E0E0E0"
            button_hover = "#D0D0D0"
        
        # Character Reference 위젯 전체 스타일
        widget_style = f"""
            QWidget {{
                background-color: {widget_bg};
                color: {text_color};
                font-size: {font_size}px;
            }}
            QLabel {{
                color: {text_color};
            }}
            QPushButton {{
                background-color: {button_bg};
                color: {text_color};
                border: 1px solid {border_color};
                padding: 5px 15px;
                border-radius: 3px;
            }}
            QPushButton:hover {{
                background-color: {button_hover};
            }}
            QPushButton:disabled {{
                background-color: {border_color};
                color: #888888;
            }}
            QCheckBox {{
                color: {text_color};
            }}
        """
        
        self.character_reference_widget.setStyleSheet(widget_style)
        
        # 이미지 라벨 스타일 (별도 적용)
        if hasattr(self, 'character_image_label'):
            self.character_image_label.setStyleSheet(
                f"QLabel {{ border: 1px solid {border_color}; background: {image_bg}; color: {text_color}; }}"
            )

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
        
        # 설정 관련 코드는 모두 제거 (init_window에서 처리)
                      

    def init_window(self):
        self.setWindowTitle(TITLE_NAME)
        self.settings = QSettings(TOP_NAME, APP_NAME)
        
        # 연속생성 설정 기본값 초기화 (여기로 이동)
        if not self.settings.contains("quick_gen_count_1"):
            self.settings.setValue("quick_gen_count_1", 5)
            self.settings.setValue("quick_gen_count_2", 10)
            self.settings.setValue("quick_gen_count_3", 50)
            self.settings.setValue("quick_gen_count_4", 100)
            self.settings.setValue("default_generation_interval", 3.0)
        
        
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
                logger.warning("저장된 크기 정보가 유효하지 않습니다. 기본 HD 해상도를 사용합니다.")
                self.resize(default_size)
        else:
            # 설정 없으면 기본값 사용
            self.resize(default_size)

        # 드래그 앤 드롭 허용
        self.setAcceptDrops(True)

    def init_statusbar(self):
        statusbar = self.statusBar()
        statusbar.messageChanged.connect(self.on_statusbar_message_changed)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedWidth(160)
        self.progress_bar.setFixedHeight(14)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.hide()
        statusbar.addWidget(self.progress_bar)

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

        # 태그 자동완성 새로고침 액션 추가
        reloadTagsAction = QAction(tr('menu.reload_tags', '태그 자동완성 새로고침(Reload Tag Completion)'), self)
        reloadTagsAction.setShortcut('Ctrl+Shift+R')
        reloadTagsAction.triggered.connect(self.reload_tag_completion)

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
        togglePanelAction = QAction(tr('menu.toggle_panel', 'Toggle Result Panel'), self)
        togglePanelAction.setShortcut('F11')
        togglePanelAction.triggered.connect(self.on_click_expand)

        # 이미지 크기 리셋 액션
        resetImageSizeAction = QAction(tr('menu.reset_image_size', 'Reset Image Window Size'), self)
        resetImageSizeAction.setShortcut('Ctrl+Shift+I')
        resetImageSizeAction.triggered.connect(lambda: self.image_result.reset_to_default_size())

        # 폴더 열기 액션들
        openResultsFolderAction = QAction(tr('folders.results', 'Results Folder'), self)
        openResultsFolderAction.setShortcut('F5')
        openResultsFolderAction.triggered.connect(lambda: self.on_click_open_folder("path_results"))

        openWildcardsFolderAction = QAction(tr('folders.wildcards', 'Wildcards Folder'), self)
        openWildcardsFolderAction.setShortcut('F6')
        openWildcardsFolderAction.triggered.connect(lambda: self.on_click_open_folder("path_wildcards"))

        openSettingsFolderAction = QAction(tr('folders.settings', 'Settings Folder'), self)
        openSettingsFolderAction.setShortcut('F7')
        openSettingsFolderAction.triggered.connect(lambda: self.on_click_open_folder("path_settings"))

        # 메뉴 생성
        menubar = self.menuBar()
        menubar.setNativeMenuBar(False)


        # 기존 메뉴 추가
        filemenu_file = menubar.addMenu(tr('menu.file'))
        filemenu_file.addAction(openAction)
        filemenu_file.addAction(saveSettingsAction)
        filemenu_file.addAction(loadSettingsAction)
        filemenu_file.addAction(reloadTagsAction)
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
        viewMenu.addAction(resetImageSizeAction)

        # 구분선 추가
        viewMenu.addSeparator()

        # 레이아웃 초기화 액션 추가
        resetLayoutAction = QAction(tr('menu.reset_layout', 'Reset Layout'), self)
        resetLayoutAction.setShortcut('Ctrl+R')
        resetLayoutAction.triggered.connect(self.reset_layout)
        viewMenu.addAction(resetLayoutAction)

        # View 메뉴 찾기 또는 생성
        view_menu = None
        for action in self.menuBar().actions():
            if action.text() == "View" or action.text() == "보기":
                view_menu = action.menu()
                break
        
        if view_menu is None:
            view_menu = self.menuBar().addMenu("View")
        
        # Character Reference 토글 액션 추가
        self.action_character_reference = QAction("Character Reference", self)
        self.action_character_reference.setCheckable(True)
        self.action_character_reference.setChecked(False)
        self.action_character_reference.setShortcut('F1')
        self.action_character_reference.triggered.connect(self.toggle_character_reference)
        view_menu.addAction(self.action_character_reference)

        # Image to Image 토글 액션 추가
        self.action_img2img = QAction("Image to Image", self)
        self.action_img2img.setCheckable(True)
        self.action_img2img.setChecked(False)
        self.action_img2img.setShortcut('F2')
        self.action_img2img.triggered.connect(self.toggle_img2img)
        view_menu.addAction(self.action_img2img)

        # Image Enhance 토글 액션 추가
        self.action_enhance = QAction("Image Enhance", self)
        self.action_enhance.setCheckable(True)
        self.action_enhance.setChecked(False)
        self.action_enhance.setShortcut('F3')
        self.action_enhance.triggered.connect(self.toggle_enhance)
        view_menu.addAction(self.action_enhance)

        # 폴더 메뉴 추가 (View와 Etc 사이)
        foldersMenu = menubar.addMenu(tr('folders.title', 'Folders'))
        foldersMenu.addAction(openResultsFolderAction)
        foldersMenu.addAction(openWildcardsFolderAction)
        foldersMenu.addAction(openSettingsFolderAction)

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
                        elif 'reload' in text.lower() or '새로고침' in text:
                            sub_action.setText(tr('menu.reload_tags', '태그 자동완성 새로고침(Reload Tag Completion)'))
                        elif 'load' in text.lower() or '불러오기' in text:
                            sub_action.setText(tr('menu.load_settings'))
                        elif 'reload' in text.lower() or '새로고침' in text:
                            sub_action.setText(tr('menu.reload_tags', '태그 자동완성 새로고침(Reload Tag Completion)'))
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
            status_key = getattr(self, 'status_state', 'IDLE')
            list_format = getattr(self, 'status_list_format', [])
        
        # 번역된 텍스트 사용 - 키 매핑 개선
        status_mapping = {
            'BEFORE_LOGIN': 'statusbar.before_login',
            'LOGINED': 'statusbar.logged_in', 
            'LOGGED_IN': 'statusbar.logged_in',  # 추가 매핑
            'LOGGINGIN': 'statusbar.logging_in',
            'GENERATING': 'statusbar.generating',
            'IDLE': 'statusbar.idle',
            'LOAD_COMPLETE': 'statusbar.load_complete',
            'LOADING': 'statusbar.loading',
            'AUTO_GENERATING_COUNT': 'statusbar.auto_generating_count',
            'AUTO_GENERATING_INF': 'statusbar.auto_generating_inf',
            'AUTO_WAIT': 'statusbar.auto_wait',
            'AUTO_ERROR_WAIT': 'statusbar.auto_error_wait'
        }
        
        # 상태 키를 번역 키로 변환
        translation_key = status_mapping.get(status_key.upper(), f'statusbar.{status_key.lower()}')
        
        try:
            status_text = tr(translation_key, *list_format)
            # 번역이 키 그대로 반환되면 기본 텍스트 사용
            if status_text == translation_key:
                status_text = status_key.replace('_', ' ').title()
        except Exception:
            status_text = status_key.replace('_', ' ').title()
        
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
            login_method = self.settings.value("login_method", "password")

            if login_method == "api_key":
                api_key = load_credential("api_key", self.settings)
                if not api_key:
                    return
                self.nai.access_token = api_key
                self.nai.api_key = api_key
                self.nai.login_method = "api_key"
            else:
                access_token = load_credential("access_token", self.settings)
                username = self.settings.value("username", "")
                password = load_credential("password", self.settings)
                if not access_token or not username or not password:
                    return
                self.nai.access_token = access_token
                self.nai.username = username
                self.nai.password = password
                self.nai.login_method = "password"

            self.set_statusbar_text("LOGGINGIN")
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
            logger.info("태그 자동 완성 초기화 시작")
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

    def reload_tag_completion(self):
        """태그 자동완성 데이터베이스를 새로고침"""
        logger.info("태그 자동완성 새로고침 시작")

        # 캐시 초기화
        CompletionTagLoadThread.cached_tags = None
        self._tags_loaded = False

        # 강제로 다시 로드
        self.init_completion(force_reload=True)

        # 사용자에게 알림
        self.statusBar().showMessage(tr('status.tags_reloaded', '태그 자동완성이 새로고침되었습니다.'), 3000)
        logger.info("태그 자동완성 새로고침 완료")



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
                    logger.debug("캐릭터 프롬프트 필드에 자동 완성 적용 시도...")
                    self.character_prompts_container.set_tag_completion(tag_list)
                    logger.info(f"캐릭터 프롬프트 필드에 자동 완성 활성화됨 ({len(tag_list)}개 태그)")
                except Exception as e:
                    logger.error(f"캐릭터 프롬프트 필드 자동 완성 설정 실패: {str(e)}")
                    import traceback
                    traceback.print_exc()
        else:
            logger.warning("태그 목록이 비어 있음")
        logger.error(f"----- 자동 완성 적용 종료 -----")


    def on_click_open_folder(self, target_pathcode):
        path = self.settings.value(
            target_pathcode, DEFAULT_PATH[target_pathcode])
        path = os.path.abspath(path)
        create_folder_if_not_exists(path)
        os.startfile(path)


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

            # Manual custom input
            if current_text == tr('ui.custom_resolution') or current_text == "Custom (직접 입력)":
                return []

            # Check if it's a custom resolution (Custom 1, Custom 2, Custom 3)
            if current_text.startswith("Custom ") and "(" in current_text:
                # Return all enabled custom resolutions
                return self._get_custom_resolution_list()

            # 현재 선택된 해상도가 어느 패밀리에 속하는지 확인
            for family_idx, resolutions in RESOLUTION_FAMILIY.items():
                if current_text in resolutions:
                    # Check if this family is enabled
                    if family_idx == 1:  # Large
                        if not self.settings.value("resolution_family_large_enabled",
                                                   DEFAULT_CUSTOM_RESOLUTIONS["resolution_family_large_enabled"], type=bool):
                            return []
                    elif family_idx == 2:  # Wallpaper
                        if not self.settings.value("resolution_family_wallpaper_enabled",
                                                   DEFAULT_CUSTOM_RESOLUTIONS["resolution_family_wallpaper_enabled"], type=bool):
                            return []
                    return resolutions

            # 만약 찾지 못했다면 기본 HD 패밀리 반환
            return RESOLUTION_FAMILIY[0]  # 기본 해상도 모음 (HD 포함)
        except Exception as e:
            logger.error(f"Resolution family error: {e}")
            return []

    def _get_custom_resolution_list(self):
        """Get list of enabled custom resolutions for random selection"""
        custom_resolutions = []
        for i in range(1, 7):  # Support up to 6 custom resolutions
            enabled = self.settings.value(f"custom_resolution_{i}_enabled",
                                          DEFAULT_CUSTOM_RESOLUTIONS.get(f"custom_resolution_{i}_enabled", False), type=bool)
            if enabled:
                width = self.settings.value(f"custom_resolution_{i}_width",
                                            DEFAULT_CUSTOM_RESOLUTIONS.get(f"custom_resolution_{i}_width", "1024"))
                height = self.settings.value(f"custom_resolution_{i}_height",
                                             DEFAULT_CUSTOM_RESOLUTIONS.get(f"custom_resolution_{i}_height", "1024"))
                try:
                    w = int(width)
                    h = int(height)
                    if w > 0 and h > 0:
                        custom_resolutions.append(f"Custom {i} ({w}x{h})")
                except (ValueError, TypeError):
                    pass
        return custom_resolutions

    def refresh_resolution_combo(self):
        """Refresh resolution combo box after settings change"""
        try:
            # Remember current selection
            current_text = self.combo_resolution.currentText()
            current_width = self.dict_ui_settings["width"].text()
            current_height = self.dict_ui_settings["height"].text()

            # Repopulate combo box
            _populate_resolution_combo(self, self.combo_resolution)

            # Try to restore selection
            restored = False
            for i in range(self.combo_resolution.count()):
                if self.combo_resolution.itemText(i) == current_text:
                    self.combo_resolution.setCurrentIndex(i)
                    restored = True
                    break

            # If original selection not found, select first valid item (Normal Square)
            if not restored:
                for i in range(self.combo_resolution.count()):
                    text = self.combo_resolution.itemText(i)
                    if not text.startswith("---") and text != tr('ui.custom_resolution'):
                        self.combo_resolution.setCurrentIndex(i)
                        break

            # Restore width/height values
            self.dict_ui_settings["width"].setText(current_width)
            self.dict_ui_settings["height"].setText(current_height)

            logger.info("Resolution combo box refreshed")
        except Exception as e:
            logger.error(f"Error refreshing resolution combo: {e}")

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

        QTimer.singleShot(50, self.image_result.refresh_size)


    def reset_layout(self):
        """모든 레이아웃을 초기 설정으로 되돌립니다"""
        try:
            # 1. 프롬프트 내부 스플리터 초기화 (Prompt ↔ Negative Prompt)
            if hasattr(self, 'prompt_splitter'):
                self.prompt_splitter.setSizes([600, 400])
            
            # 2. 프롬프트-캐릭터 스플리터 초기화
            if hasattr(self, 'prompt_char_splitter'):
                self.prompt_char_splitter.setSizes([600, 400])
            
            # 3. 메인 수직 스플리터 초기화 (프롬프트 영역 ↔ 설정 영역)
            if hasattr(self, 'main_vertical_splitter'):
                self.main_vertical_splitter.setSizes([600, 400])
            
            # 4. 설정 영역 수평 스플리터 초기화 (Image Options ↔ Advanced ↔ Folder ↔ Generate)
            if hasattr(self, 'settings_splitter'):
                self.settings_splitter.setSizes([400, 400, 200, 300])
            
            # 5. 메인 좌우 스플리터 초기화
            if hasattr(self, 'main_splitter'):
                self.set_default_splitter()

            # 6. 우측 수직 스플리터 초기화 (Result Image ↔ Result Prompt)
            if hasattr(self, 'right_vertical_splitter'):
                self.right_vertical_splitter.setSizes([700, 300])

            # 7. 저장된 모든 스플리터 설정 초기화
            self.settings.remove("splitterSizes")
            self.settings.remove("promptSplitterSizes")
            self.settings.remove("promptCharSplitterSizes")
            self.settings.remove("settingsSplitterSizes")
            self.settings.remove("mainVerticalSplitterSizes")
            self.settings.remove("rightVerticalSplitterSizes")

            # 사용자에게 알림
            self.set_statusbar_text("IDLE")
            logger.info("레이아웃이 초기 설정으로 리셋되었습니다")
            
        except Exception as e:
            logger.error(f"레이아웃 초기화 중 오류 발생: {e}")


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
                has_custom_positions = False  # 커스텀 위치 여부 확인용
                
                for i, char in enumerate(char_captions):
                    char_prompt = {
                        "prompt": char.get("char_caption", ""),
                        "negative_prompt": "",
                        "position": None
                    }
                    
                    # 위치 정보 추가 (있을 경우)
                    if "centers" in char and len(char["centers"]) > 0:
                        center = char["centers"][0]
                        position = [center.get("x", 0.5), center.get("y", 0.5)]
                        char_prompt["position"] = position
                        
                        # 중앙(0.5, 0.5)이 아닌 위치가 있으면 커스텀 위치로 판단
                        if position[0] != 0.5 or position[1] != 0.5:
                            has_custom_positions = True
                    
                    # 네거티브 프롬프트 추가 (존재하는 경우)
                    if i < len(neg_char_captions):
                        char_prompt["negative_prompt"] = neg_char_captions[i].get("char_caption", "")
                    
                    character_prompts.append(char_prompt)
                
                if character_prompts:
                    new_dict["characterPrompts"] = character_prompts
                    
                    # use_character_coords 복원 로직 개선
                    use_character_coords = new_dict.get("use_character_coords", None)
                    
                    if use_character_coords is not None:
                        # 메타데이터에 use_character_coords가 있으면 그 값 사용
                        use_ai_positions = not use_character_coords
                        logger.debug(f"메타데이터에서 use_character_coords 복원: {use_character_coords}")
                    else:
                        # 메타데이터에 없으면 위치 정보로 추론
                        use_ai_positions = not has_custom_positions
                        logger.debug(f"위치 정보로 AI 위치 설정 추론: has_custom_positions={has_custom_positions}, use_ai_positions={use_ai_positions}")
                    
                    # v4_prompt의 use_coords 값도 확인 (추가 검증)
                    if "v4_prompt" in nai_dict["etc"]:
                        v4_use_coords = nai_dict["etc"]["v4_prompt"].get("use_coords", None)
                        if v4_use_coords is False:
                            # API에서 use_coords가 false면 AI Choice 모드였음
                            use_ai_positions = True
                        else:
                            # use_coords가 true면 수동 위치 모드였음
                            use_ai_positions = False

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
                    "use_ai_positions": use_ai_positions,  # 개선된 로직으로 설정
                    "characters": characters
                }
                
                self.character_prompts_container.set_data(character_data)                
                logger.debug(f"캐릭터 프롬프트 UI 적용: use_ai_positions={use_ai_positions}")
                
            
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
        about_text = (
            "NAI Auto Generator v4.5\n"
            "\n"
            "Community : https://arca.live/b/aiart\n"
            "\n"
            "Original : https://github.com/DCP-arca/NAI-Auto-Generator\n"
            "\n"
            "v4/v4.5 update : sagawa8b\n"
            "\n"
            "Credits :\n"
            "  https://huggingface.co/baqu2213\n"
            "  https://github.com/neggles/sd-webui-stealth-pnginfo/\n"
            "  https://github.com/DCP-arca/NAI-Auto-Generator\n"
            "\n"
            "Notice :\n"
            "본 앱은 제3자가 개발한 앱으로 Novel AI 에서 개발하거나 관리하지 않으며,\n"
            "이들 회사와는 무관합니다.\n"
            "\n"
            "This app is a third-party app that is not developed or managed\n"
            "by Novel AI and is unaffiliated with those companies."
        )
        QMessageBox.about(self, 'About', about_text)
    

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

        # 디버그: 캐릭터 프롬프트 확인
        if 'characterPrompts' in nai_dict:
            char_count = len(nai_dict['characterPrompts']) if nai_dict['characterPrompts'] else 0
            logger.debug(f"Result prompt - Character prompts count: {char_count}")
            if char_count > 0:
                logger.debug(f"Character prompts data: {nai_dict['characterPrompts']}")

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
        self.settings.setValue("auto_login", True if is_auto_login else False)
        self.settings.setValue("username",
                               self.nai.username if is_auto_login else None)
        self.settings.setValue("login_method",
                               self.nai.login_method if is_auto_login else None)
        if is_auto_login:
            save_credential("access_token", self.nai.access_token, self.settings)
            save_credential("password", self.nai.password, self.settings)
            save_credential("api_key", self.nai.api_key, self.settings)
        else:
            delete_credential("access_token", self.settings)
            delete_credential("password", self.settings)
            delete_credential("api_key", self.settings)

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
                logger.error(f"Error tagging image: {e}")

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
                logger.error(f"Error downloading image: {e}")
                self.set_statusbar_text("IDLE")
                QMessageBox.information(self, '경고', "이미지 파일 다운로드에 실패했습니다.")
                return

    def on_statusbar_message_changed(self, t):
        if not t:
            self.set_statusbar_text()

    def closeEvent(self, e):
        # 창 크기 저장 (확장 여부에 따른 조정 없이 현재 전체 크기 저장)
        current_size = self.size()
        self.settings.setValue("size", current_size)
        self.settings.setValue("pos", self.pos())

        # 모든 스플리터 상태 저장
        self.settings.setValue("splitterSizes", self.main_splitter.saveState())

        # 각 개별 스플리터 상태 저장
        if hasattr(self, 'prompt_splitter'):
            self.settings.setValue("promptSplitterSizes", self.prompt_splitter.saveState())

        if hasattr(self, 'prompt_char_splitter'):
            self.settings.setValue("promptCharSplitterSizes", self.prompt_char_splitter.saveState())

        if hasattr(self, 'settings_splitter'):
            self.settings.setValue("settingsSplitterSizes", self.settings_splitter.saveState())

        if hasattr(self, 'main_vertical_splitter'):
            self.settings.setValue("mainVerticalSplitterSizes", self.main_vertical_splitter.saveState())

        if hasattr(self, 'right_vertical_splitter'):
            self.settings.setValue("rightVerticalSplitterSizes", self.right_vertical_splitter.saveState())

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