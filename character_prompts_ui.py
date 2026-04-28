from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                            QPushButton, QPlainTextEdit, QScrollArea, QFrame,
                            QGridLayout, QDialog, QCheckBox, QButtonGroup, QSizePolicy,
                            QSplitter, QTabWidget)
from PyQt5.QtCore import Qt, pyqtSignal, QSettings
from PyQt5.QtGui import QColor, QPalette
from completer import CompletionTextEdit
from i18n_manager import tr
from logger import get_logger
logger = get_logger()


class PositionSelectorWidget(QWidget):
    """캐릭터 위치 선택 위젯 — 탭 내 인라인 표시용"""

    position_changed = pyqtSignal(object)  # (x, y) tuple or None

    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_position = None
        self.buttons = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(4, 4, 4, 4)
        self.setLayout(layout)

        info_label = QLabel(tr('ui.char_position_grid_info'))
        layout.addWidget(info_label)

        grid_layout = QGridLayout()
        grid_layout.setSpacing(3)
        for row in range(5):
            for col in range(5):
                btn = QPushButton()
                btn.setFixedSize(40, 40)
                btn.setStyleSheet("background-color: #f0f0f0;")
                btn.clicked.connect(lambda checked=False, r=row, c=col: self._on_selected(r, c))
                grid_layout.addWidget(btn, row, col)
                self.buttons.append(btn)
        layout.addLayout(grid_layout)

        clear_btn = QPushButton(tr('ui.char_position_clear'))
        clear_btn.clicked.connect(self.clear_position)
        layout.addWidget(clear_btn)
        layout.addStretch()

    def _on_selected(self, row, col):
        for btn in self.buttons:
            btn.setStyleSheet("background-color: #f0f0f0;")
        self.buttons[row * 5 + col].setStyleSheet("background-color: #559977;")
        self.selected_position = ((col + 0.5) / 5, (row + 0.5) / 5)
        self.position_changed.emit(self.selected_position)

    def clear_position(self):
        for btn in self.buttons:
            btn.setStyleSheet("background-color: #f0f0f0;")
        self.selected_position = None
        self.position_changed.emit(None)

    def set_position(self, position):
        """외부에서 위치 설정"""
        self.clear_position()
        if position:
            col = max(0, min(4, int(position[0] * 5)))
            row = max(0, min(4, int(position[1] * 5)))
            self.buttons[row * 5 + col].setStyleSheet("background-color: #559977;")
            self.selected_position = position


class PositionSelectorDialog(QDialog):
    """캐릭터 위치 선택 다이얼로그"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr('ui.char_position_dialog_title'))
        self.selected_position = None
        self.setup_ui()
        
    def setup_ui(self):
        try:
            layout = QVBoxLayout()
            self.setLayout(layout)
            
            # 설명 라벨
            info_label = QLabel(tr('ui.char_position_grid_info'))
            layout.addWidget(info_label)
            
            # 그리드 생성 (5x5)
            grid_layout = QGridLayout()
            self.buttons = []
            
            for row in range(5):
                for col in range(5):
                    btn = QPushButton()
                    btn.setFixedSize(50, 50)
                    # 람다 함수에 위치 정보를 명시적으로 전달
                    btn.clicked.connect(lambda checked=False, r=row, c=col: self.on_position_selected(r, c))
                    grid_layout.addWidget(btn, row, col)
                    self.buttons.append(btn)
            
            layout.addLayout(grid_layout)
            
            # 완료/취소 버튼
            buttons_layout = QHBoxLayout()
            done_button = QPushButton(tr('ui.char_done'))
            done_button.clicked.connect(self.accept)
            cancel_button = QPushButton(tr('dialogs.cancel'))
            cancel_button.clicked.connect(self.reject)
            
            buttons_layout.addStretch()
            buttons_layout.addWidget(done_button)
            buttons_layout.addWidget(cancel_button)
            layout.addLayout(buttons_layout)
        except Exception as e:
            logger.error(f"위치 선택자 UI 초기화 오류: {e}")
            import traceback
            traceback.print_exc()
    
    def on_position_selected(self, row, col):
        try:
            logger.error(f"위치 선택: 행={row}, 열={col}")
            # 다른 버튼들은 원래 색으로 복원
            for btn in self.buttons:
                btn.setStyleSheet("")
            
            # 선택된 버튼 하이라이트
            index = row * 5 + col
            self.buttons[index].setStyleSheet("background-color: #559977;")
            
            # 위치 저장 (0~1 범위의 비율로 저장)
            self.selected_position = ((col + 0.5) / 5, (row + 0.5) / 5)
            logger.error(f"저장된 위치: {self.selected_position}")
        except Exception as e:
            logger.error(f"위치 선택 처리 오류: {e}")
            import traceback
            traceback.print_exc()


class ResizeHandle(QWidget):
    """드래그로 대상 위젯의 높이를 변경하는 핸들 바"""

    def __init__(self, target, min_height=120, parent=None):
        super().__init__(parent)
        self.target = target
        self.min_height = min_height
        self._drag_start_y = None
        self._drag_start_height = None
        self.setFixedHeight(6)
        self.setCursor(Qt.SizeVerCursor)
        self.setToolTip("드래그하여 높이 조절")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def paintEvent(self, event):
        from PyQt5.QtGui import QPainter, QColor
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#bbbbbb"))
        # Draw two short grip lines in the center
        mid_x = self.width() // 2
        mid_y = self.height() // 2
        painter.setPen(QColor("#888888"))
        for dx in (-6, 0, 6):
            painter.drawLine(mid_x + dx, mid_y - 1, mid_x + dx, mid_y + 1)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start_y = event.globalPos().y()
            self._drag_start_height = self.target.height()

    def mouseMoveEvent(self, event):
        if self._drag_start_y is not None:
            delta = event.globalPos().y() - self._drag_start_y
            new_height = max(self.min_height, self._drag_start_height + delta)
            self.target.setFixedHeight(new_height)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start_y = None
            self._drag_start_height = None


class CharacterPromptWidget(QFrame):
    """캐릭터 프롬프트를 입력하고 관리하는 위젯"""

    deleted = pyqtSignal(object)  # 삭제 시그널
    moved = pyqtSignal(object, int)  # 이동 시그널 (위젯, 방향)

    def __init__(self, parent=None, index=0):
        super().__init__(parent)
        self.parent = parent
        self.index = index
        self.position = None  # 캐릭터 위치 (None = AI 선택)

        # 설정 객체
        self.settings = QSettings("dcp_arca", "nag_gui")

        # 스타일 설정
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)
        self.setStyleSheet("background-color: #e6e6e6; border: 1px solid #cccccc; border-radius: 5px; padding: 3px;")

        self.setup_ui()

        # 가로로 꽉 채우고 세로는 고정 (드래그 핸들로 변경 가능)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(135)
    
    def update_title(self):
        """타이틀 업데이트"""
        try:
            self.title_label.setText(tr('ui.character_n', self.index + 1))
        except Exception as e:
            logger.error(f"타이틀 업데이트 중 오류: {e}")
    
    def setup_ui(self):
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(4, 4, 4, 4)
        self.layout.setSpacing(2)
        self.setLayout(self.layout)

        # 탭 위젯 (Prompt / Negative / Position) — 헤더를 탭바 코너에 통합
        self.prompt_tab = QTabWidget()
        self.prompt_tab.setTabPosition(QTabWidget.North)

        # 왼쪽 코너: 캐릭터 타이틀
        self.title_label = QLabel(tr('ui.character_n', self.index + 1))
        self.title_label.setStyleSheet("font-weight: bold; color: black; padding: 0px 4px;")
        self.prompt_tab.setCornerWidget(self.title_label, Qt.TopLeftCorner)

        # 오른쪽 코너: 이동/삭제 버튼
        corner_widget = QWidget()
        corner_layout = QHBoxLayout(corner_widget)
        corner_layout.setContentsMargins(0, 0, 2, 0)
        corner_layout.setSpacing(1)

        move_up_btn = QPushButton("▲")
        move_up_btn.setFixedSize(22, 20)
        move_up_btn.setStyleSheet("padding: 0px;")
        move_up_btn.clicked.connect(lambda: self.moved.emit(self, -1))

        move_down_btn = QPushButton("▼")
        move_down_btn.setFixedSize(22, 20)
        move_down_btn.setStyleSheet("padding: 0px;")
        move_down_btn.clicked.connect(lambda: self.moved.emit(self, 1))

        delete_btn = QPushButton("✕")
        delete_btn.setFixedSize(22, 20)
        delete_btn.setStyleSheet("padding: 0px;")
        delete_btn.clicked.connect(lambda: self.deleted.emit(self))

        corner_layout.addWidget(move_up_btn)
        corner_layout.addWidget(move_down_btn)
        corner_layout.addWidget(delete_btn)

        self.prompt_tab.setCornerWidget(corner_widget, Qt.TopRightCorner)

        # Tab 0: 메인 프롬프트
        self.prompt_edit = CompletionTextEdit(enable_image_drop=False)
        self.prompt_edit.setPlaceholderText(tr('ui.char_prompt_placeholder'))
        self.prompt_edit.setMinimumHeight(60)
        self.prompt_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.prompt_edit.setStyleSheet("background-color: white; color: black; border: 1px solid #bbbbbb;")
        self.prompt_tab.addTab(self.prompt_edit, tr('ui.prompt'))

        # Tab 1: 네거티브 프롬프트
        self.neg_prompt_edit = CompletionTextEdit(enable_image_drop=False)
        self.neg_prompt_edit.setPlaceholderText(tr('ui.char_negative_placeholder'))
        self.neg_prompt_edit.setMinimumHeight(60)
        self.neg_prompt_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.neg_prompt_edit.setStyleSheet("background-color: white; color: black; border: 1px solid #bbbbbb;")
        self.prompt_tab.addTab(self.neg_prompt_edit, tr('ui.negative_tab'))

        # Tab 2: 위치 선택 (인라인 그리드)
        self.position_widget = PositionSelectorWidget()
        self.position_widget.position_changed.connect(self._on_position_changed)
        self.prompt_tab.addTab(self.position_widget, tr('ui.position'))

        # 탭 레이블에 문자 수 업데이트 연결
        self.prompt_edit.textChanged.connect(self._update_prompt_tab_label)
        self.neg_prompt_edit.textChanged.connect(self._update_neg_tab_label)
        # 위치 탭 선택 시 높이 자동 확장
        self.prompt_tab.currentChanged.connect(self._on_tab_changed)

        self.layout.addWidget(self.prompt_tab, 1)

        # 높이 조절 핸들
        self.resize_handle = ResizeHandle(self, min_height=120)
        self.layout.addWidget(self.resize_handle)

    def _update_prompt_tab_label(self):
        count = len(self.prompt_edit.toPlainText())
        label = tr('ui.prompt') if count == 0 else f"{tr('ui.prompt')} ({count})"
        self.prompt_tab.setTabText(0, label)

    def _update_neg_tab_label(self):
        count = len(self.neg_prompt_edit.toPlainText())
        label = tr('ui.negative_tab') if count == 0 else f"{tr('ui.negative_tab')} ({count})"
        self.prompt_tab.setTabText(1, label)

    def _on_position_changed(self, position):
        self.position = position
        if position:
            pct_x = int(position[0] * 100)
            pct_y = int(position[1] * 100)
            self.prompt_tab.setTabText(2, f"{tr('ui.position')} ●")
            self.prompt_tab.setTabToolTip(2, f"{pct_x}%, {pct_y}%")
        else:
            self.prompt_tab.setTabText(2, tr('ui.position'))
            self.prompt_tab.setTabToolTip(2, "")

    # 위치 탭 선택 시 그리드(5×5, 버튼 40px)가 ~320px 필요 → 자동 확장
    _POSITION_TAB_MIN_HEIGHT = 320

    def _on_tab_changed(self, index):
        if index == 2:  # 위치 탭
            if self.height() < self._POSITION_TAB_MIN_HEIGHT:
                self._height_before_position = self.height()
                self.setFixedHeight(self._POSITION_TAB_MIN_HEIGHT)
        else:
            if hasattr(self, '_height_before_position'):
                self.setFixedHeight(self._height_before_position)
                del self._height_before_position

    def get_data(self):
        """캐릭터 프롬프트 데이터 반환"""
        neg_text = self.neg_prompt_edit.toPlainText()
        data = {
            "prompt": self.prompt_edit.toPlainText(),
            "negative_prompt": neg_text,
            "position": self.position,
            "show_negative": bool(neg_text),
        }
        logger.debug(f"캐릭터 {self.index + 1} 데이터: position={data['position']}")
        return data

    def set_data(self, data):
        """캐릭터 프롬프트 데이터 설정"""
        if "prompt" in data:
            self.prompt_edit.setPlainText(data["prompt"])

        if "negative_prompt" in data and data["negative_prompt"]:
            self.neg_prompt_edit.setPlainText(data["negative_prompt"])

        if "position" in data:
            self.position = data["position"]
            self.position_widget.set_position(data["position"])
            if data["position"]:
                pct_x = int(data["position"][0] * 100)
                pct_y = int(data["position"][1] * 100)
                self.prompt_tab.setTabText(2, f"{tr('ui.position')} ●")
                self.prompt_tab.setTabToolTip(2, f"{pct_x}%, {pct_y}%")


class CharacterPromptsContainer(QWidget):
    """캐릭터 프롬프트 컨테이너 위젯"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.character_widgets = []
        self.use_ai_positions = True
        self.settings = QSettings("dcp_arca", "nag_gui")
        self.setup_ui()
    
    def setup_ui(self):
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(4, 4, 4, 4)  # 여백 축소
        self.main_layout.setSpacing(4)  # 간격 축소
        self.setLayout(self.main_layout)
        
        # 전체 컨테이너 스타일 설정
        self.setStyleSheet("QLabel { color: black; } QCheckBox { color: black; }")
        
        # AI 위치 선택 여부 체크박스
        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(0, 0, 0, 0)  # 여백 제거
        self.ai_position_checkbox = QCheckBox(tr('ui.ai_position'))
        self.ai_position_checkbox.setChecked(True)
        self.ai_position_checkbox.stateChanged.connect(self.toggle_ai_positions)
        controls_layout.addWidget(self.ai_position_checkbox)
        
        # 캐릭터 추가 버튼
        self.add_button = QPushButton(tr('ui.add_character'))
        self.add_button.clicked.connect(self.add_character)
        controls_layout.addWidget(self.add_button)
        
        # 모두 삭제 버튼
        self.clear_button = QPushButton(tr('ui.clear_all'))
        self.clear_button.clicked.connect(self.clear_characters)
        controls_layout.addWidget(self.clear_button)
        
        self.main_layout.addLayout(controls_layout)

        # 수직 스크롤 영역
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # 캐릭터 위젯들을 수직으로 배치할 컨테이너
        self.characters_container = QWidget()
        self.characters_layout = QVBoxLayout(self.characters_container)
        self.characters_layout.setContentsMargins(0, 0, 0, 0)
        self.characters_layout.setSpacing(8)
        self.characters_layout.addStretch()  # 아래쪽 끝에 빈 공간 추가

        self.scroll_area.setWidget(self.characters_container)

        self.scroll_area.setMinimumHeight(150)
        self.scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.main_layout.addWidget(self.scroll_area, 1)
    
    def toggle_ai_positions(self, state):
        """AI 위치 선택 여부 토글"""
        try:
            self.use_ai_positions = state == Qt.Checked
            logger.error(f"AI 위치 선택 상태 변경: {self.use_ai_positions}")

            # AI 위치 선택 시 Position 탭 비활성화 (탭은 유지하되 입력 불가)
            for widget in self.character_widgets:
                pos_tab_index = 2  # Position 탭은 항상 인덱스 2
                widget.prompt_tab.setTabEnabled(pos_tab_index, not self.use_ai_positions)
        except Exception as e:
            logger.error(f"AI 위치 토글 오류: {e}")
            import traceback
            traceback.print_exc()
    
    def add_character(self):
        """새 캐릭터 프롬프트 추가"""
        if len(self.character_widgets) >= 6:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, tr('dialogs.warning'), tr('ui.char_max_warning'))
            return
        
        widget = CharacterPromptWidget(self, len(self.character_widgets))
        widget.deleted.connect(self.remove_character)
        widget.moved.connect(self.move_character)
        widget.prompt_tab.setTabEnabled(2, not self.use_ai_positions)
        
        # 태그 자동 완성 적용 (태그 목록이 있는 경우)
        if hasattr(self, 'tag_list') and self.tag_list:
            if hasattr(widget.prompt_edit, 'start_complete_mode'):
                widget.prompt_edit.start_complete_mode(self.tag_list)
            if hasattr(widget.neg_prompt_edit, 'start_complete_mode'):
                widget.neg_prompt_edit.start_complete_mode(self.tag_list)
        
        # stretch 아이템 앞에 위젯 삽입
        self.characters_layout.insertWidget(self.characters_layout.count() - 1, widget)
        self.character_widgets.append(widget)
        
        # 인덱스 업데이트
        self.update_indices()
    
    def remove_character(self, widget):
        """캐릭터 프롬프트 삭제"""
        if widget in self.character_widgets:
            self.characters_layout.removeWidget(widget)
            self.character_widgets.remove(widget)
            widget.deleteLater()
            
            # 인덱스 업데이트
            self.update_indices()
    
    def move_character(self, widget, direction):
        """캐릭터 프롬프트 순서 이동"""
        if widget not in self.character_widgets:
            return
        
        index = self.character_widgets.index(widget)
        new_index = index + direction
        
        if 0 <= new_index < len(self.character_widgets):
            # 위젯 순서 변경
            self.character_widgets.pop(index)
            self.character_widgets.insert(new_index, widget)
            
            # 레이아웃에서 제거 후 재배치
            for i, w in enumerate(self.character_widgets):
                self.characters_layout.removeWidget(w)
            
            # stretch 아이템 제거
            stretch_item = self.characters_layout.takeAt(self.characters_layout.count() - 1)
            
            # 위젯 추가
            for i, w in enumerate(self.character_widgets):
                self.characters_layout.addWidget(w)
            
            # stretch 아이템 다시 추가
            self.characters_layout.addStretch()
            
            # 인덱스 업데이트
            self.update_indices()
    
    def update_indices(self):
        """캐릭터 인덱스 업데이트"""
        for i, widget in enumerate(self.character_widgets):
            widget.index = i
            try:
                widget.update_title()
            except AttributeError:
                # 예전 방식으로도 시도
                try:
                    header_layout = widget.layout.itemAt(0).layout()
                    if header_layout:
                        title_label = header_layout.itemAt(0).widget()
                        if title_label:
                            title_label.setText(f"캐릭터 {i + 1}")
                except Exception as e:
                    logger.warning(f"캐릭터 제목 업데이트 실패 (index={i}): {e}")
    
    def clear_characters(self):
        """모든 캐릭터 프롬프트 삭제"""
        for widget in self.character_widgets[:]:
            self.remove_character(widget)
    
    def get_data(self):
        """모든 캐릭터 프롬프트 데이터 반환"""
        # 와일드카드 처리기 참조 확인
        if hasattr(self, 'parent') and hasattr(self.parent, 'apply_wildcards'):
            apply_wildcards_func = self.parent.apply_wildcards
        else:
            apply_wildcards_func = lambda x: x  # 기본 함수 (변경 없음)
        
        characters_data = []
        for widget in self.character_widgets:
            char_data = widget.get_data()
            characters_data.append(char_data)
            
        result = {
            "use_ai_positions": self.use_ai_positions,
            "characters": characters_data
        }
        
        logger.debug(f"캐릭터 프롬프트 컨테이너 데이터:")
        logger.debug(f"  AI 위치 선택: {self.use_ai_positions}")
        logger.debug(f"  캐릭터 수: {len(characters_data)}")
        for i, char in enumerate(characters_data):
            logger.debug(f"  캐릭터 {i+1} 위치: {char.get('position', 'None')}")
        
        return result
    
    def set_data(self, data):
        """캐릭터 프롬프트 데이터 설정"""
        self.clear_characters()
        
        if "use_ai_positions" in data:
            self.use_ai_positions = data["use_ai_positions"]
            self.ai_position_checkbox.setChecked(self.use_ai_positions)
        
        if "characters" in data:
            for char_data in data["characters"]:
                self.add_character()
                self.character_widgets[-1].set_data(char_data)
    
    def set_tag_completion(self, tag_list):
        """
        모든 캐릭터 프롬프트 에디터에 태그 자동 완성 설정
        """
        if not tag_list:
            return
            
        # 기존 캐릭터들에 자동 완성 적용
        for widget in self.character_widgets:
            if hasattr(widget.prompt_edit, 'start_complete_mode'):
                widget.prompt_edit.start_complete_mode(tag_list)
            if hasattr(widget.neg_prompt_edit, 'start_complete_mode'):
                widget.neg_prompt_edit.start_complete_mode(tag_list)
                
        # 이후 새로 추가되는 캐릭터에도 적용하기 위해 태그 목록 저장
        self.tag_list = tag_list

    def resizeEvent(self, event):
        """창 크기 변경 시 처리"""
        super().resizeEvent(event)

        # 반응형 동작: 높이 저장 제거 (자동으로 창 크기에 맞춰 조절됨)
        # if self.scroll_area.height() > 0:
        #     self.settings.setValue("character_scroll_height", self.scroll_area.height())