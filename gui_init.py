from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
                             QLabel, QLineEdit, QPushButton, QPlainTextEdit,
                             QTextBrowser, QComboBox, QSplitter, QCheckBox,
                             QRadioButton, QButtonGroup, QSizePolicy, QMessageBox,
                             QFileDialog, QApplication, QCompleter, QFrame, QSlider,
                             QTabWidget)
from PyQt5.QtCore import Qt, pyqtSignal, QSettings, QSize
from PyQt5.QtGui import QPixmap, QImage, QPainter, QPen, QColor, QMouseEvent, QBrush, QPalette, QDrag
from consts import RESOLUTION_FAMILIY, COLOR, DEFAULT_CUSTOM_RESOLUTIONS
from completer import CompletionTextEdit
from character_prompts_ui import CharacterPromptsContainer
import random
import os
from logger import get_logger

from i18n_manager import tr

logger = get_logger()


def _populate_resolution_combo(parent, combo_resolution):
    """Populate resolution combo box based on settings (Large/Wallpaper enable and custom resolutions)"""
    combo_resolution.clear()

    # Get settings
    large_enabled = parent.settings.value("resolution_family_large_enabled",
                                          DEFAULT_CUSTOM_RESOLUTIONS["resolution_family_large_enabled"], type=bool)
    wallpaper_enabled = parent.settings.value("resolution_family_wallpaper_enabled",
                                              DEFAULT_CUSTOM_RESOLUTIONS["resolution_family_wallpaper_enabled"], type=bool)

    # Normal 그룹 (always enabled)
    combo_resolution.addItem("--- Normal ---")
    combo_resolution.setItemData(combo_resolution.count() - 1, 0, Qt.UserRole - 1)
    for resolution in RESOLUTION_FAMILIY[0]:
        combo_resolution.addItem(resolution)

    # Large 그룹 (conditional)
    if large_enabled:
        combo_resolution.addItem("--- Large ---")
        combo_resolution.setItemData(combo_resolution.count() - 1, 0, Qt.UserRole - 1)
        for resolution in RESOLUTION_FAMILIY[1]:
            combo_resolution.addItem(resolution)

    # Wallpaper 그룹 (conditional)
    if wallpaper_enabled:
        combo_resolution.addItem("--- Wallpaper ---")
        combo_resolution.setItemData(combo_resolution.count() - 1, 0, Qt.UserRole - 1)
        for resolution in RESOLUTION_FAMILIY[2]:
            combo_resolution.addItem(resolution)

    # Low Resolution 그룹 (always enabled)
    combo_resolution.addItem("--- Low Resolution ---")
    combo_resolution.setItemData(combo_resolution.count() - 1, 0, Qt.UserRole - 1)
    for resolution in RESOLUTION_FAMILIY[3]:
        combo_resolution.addItem(resolution)

    # Custom resolutions
    custom_resolutions = []
    for i in range(1, 7):  # Support up to 6 custom resolutions
        enabled = parent.settings.value(f"custom_resolution_{i}_enabled",
                                        DEFAULT_CUSTOM_RESOLUTIONS.get(f"custom_resolution_{i}_enabled", False), type=bool)
        if enabled:
            width = parent.settings.value(f"custom_resolution_{i}_width",
                                          DEFAULT_CUSTOM_RESOLUTIONS.get(f"custom_resolution_{i}_width", "1024"))
            height = parent.settings.value(f"custom_resolution_{i}_height",
                                           DEFAULT_CUSTOM_RESOLUTIONS.get(f"custom_resolution_{i}_height", "1024"))
            try:
                w = int(width)
                h = int(height)
                if w > 0 and h > 0:
                    custom_resolutions.append(f"Custom {i} ({w}x{h})")
            except (ValueError, TypeError):
                pass

    # Add Custom section with separator
    combo_resolution.addItem("--- Custom ---")
    combo_resolution.setItemData(combo_resolution.count() - 1, 0, Qt.UserRole - 1)

    if custom_resolutions:
        # Add enabled custom resolutions
        for res in custom_resolutions:
            combo_resolution.addItem(res)
    else:
        # Only show manual input option when no custom resolutions are enabled
        combo_resolution.addItem(tr('ui.custom_resolution'))


class DragDropImageLabel(QLabel):
    """Drag-and-drop enabled QLabel for image import"""

    imageDropped = pyqtSignal(str)  # Signal emitted with file path when image is dropped

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        """Handle drag enter event"""
        if event.mimeData().hasUrls():
            # Check if at least one URL is an image file
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                    event.acceptProposedAction()
                    logger.debug(f"Drag enter accepted: {file_path}")
                    return
        event.ignore()

    def dragMoveEvent(self, event):
        """Handle drag move event"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        """Handle drop event"""
        if event.mimeData().hasUrls():
            # Get the first image file from dropped URLs
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                    logger.info(f"Image dropped: {file_path}")
                    self.imageDropped.emit(file_path)
                    event.acceptProposedAction()
                    return
        event.ignore()

def init_advanced_prompt_group(parent):
    """탭 형태의 프롬프트 그룹 초기화 (Prompt / Negative 탭 + 문자 수 표시)"""
    prompt_group = QGroupBox(tr('ui.prompt_group', 'Prompt'))
    prompt_layout = QVBoxLayout()
    prompt_layout.setContentsMargins(4, 4, 4, 4)
    prompt_group.setLayout(prompt_layout)

    # 탭 위젯
    tab_widget = QTabWidget()

    # Tab 0: 메인 프롬프트
    parent.dict_ui_settings["prompt"] = CompletionTextEdit()
    parent.dict_ui_settings["prompt"].setPlaceholderText(tr('ui.prompt_placeholder'))
    tab_widget.addTab(parent.dict_ui_settings["prompt"], tr('ui.base_prompt'))

    # Tab 1: 네거티브 프롬프트
    parent.dict_ui_settings["negative_prompt"] = CompletionTextEdit()
    parent.dict_ui_settings["negative_prompt"].setPlaceholderText(tr('ui.negative_prompt_placeholder'))
    tab_widget.addTab(parent.dict_ui_settings["negative_prompt"], tr('ui.negative_tab'))

    # 탭 레이블에 문자 수 업데이트
    def update_prompt_tab_label():
        count = len(parent.dict_ui_settings["prompt"].toPlainText())
        label = tr('ui.base_prompt') if count == 0 else f"{tr('ui.base_prompt')} ({count})"
        tab_widget.setTabText(0, label)

    def update_neg_tab_label():
        count = len(parent.dict_ui_settings["negative_prompt"].toPlainText())
        label = tr('ui.negative_tab') if count == 0 else f"{tr('ui.negative_tab')} ({count})"
        tab_widget.setTabText(1, label)

    parent.dict_ui_settings["prompt"].textChanged.connect(update_prompt_tab_label)
    parent.dict_ui_settings["negative_prompt"].textChanged.connect(update_neg_tab_label)

    prompt_layout.addWidget(tab_widget)

    # 참조 저장
    parent.prompt_tab_widget = tab_widget

    return prompt_group

def create_img2img_widget(parent, left_widget):
    """Image to Image UI 생성 (반응형)"""
    widget = QFrame(left_widget)
    widget.setFrameStyle(QFrame.StyledPanel)
    widget.hide()

    # 반응형 크기 정책 설정
    widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    layout = QVBoxLayout(widget)
    layout.setContentsMargins(10, 10, 10, 10)
    layout.setSpacing(8)

    # 타이틀
    title_label = QLabel("🖼️ Image to Image")
    title_label.setStyleSheet("font-size: 14pt; font-weight: bold;")
    layout.addWidget(title_label)

    # 컨텐츠 영역 (반응형)
    content_layout = QHBoxLayout()
    content_layout.setSpacing(10)

    # 왼쪽: 이미지 미리보기 (드래그 앤 드롭 지원)
    parent.img2img_image_label = DragDropImageLabel()
    parent.img2img_image_label.setFixedSize(164, 198)
    parent.img2img_image_label.setAlignment(Qt.AlignCenter)
    parent.img2img_image_label.setText("No Image\n(Drag & Drop)")
    parent.img2img_image_label.setStyleSheet("background-color: rgba(0, 0, 0, 128); color: white; border: 2px dashed #666;")
    parent.img2img_image_label.imageDropped.connect(parent.load_img2img_image_from_path)
    content_layout.addWidget(parent.img2img_image_label)

    # 오른쪽: 컨트롤 영역
    controls_container = QWidget()
    controls_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
    controls_layout = QVBoxLayout(controls_container)
    controls_layout.setContentsMargins(0, 0, 0, 0)
    controls_layout.setSpacing(8)

    # 버튼 영역 (가로 배치)
    buttons_layout = QHBoxLayout()
    buttons_layout.setSpacing(8)

    # 이미지 선택 버튼
    parent.btn_select_img2img_image = QPushButton("Select Image")
    parent.btn_select_img2img_image.clicked.connect(parent.select_img2img_image)
    parent.btn_select_img2img_image.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    buttons_layout.addWidget(parent.btn_select_img2img_image)

    # 이미지 제거 버튼
    parent.btn_remove_img2img_image = QPushButton("Remove Image")
    parent.btn_remove_img2img_image.clicked.connect(parent.remove_img2img_image)
    parent.btn_remove_img2img_image.setEnabled(False)
    parent.btn_remove_img2img_image.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    buttons_layout.addWidget(parent.btn_remove_img2img_image)

    controls_layout.addLayout(buttons_layout)

    # Strength 섹션
    strength_label = QLabel("Strength")
    strength_label.setStyleSheet("font-size: 12pt; font-weight: bold;")
    controls_layout.addWidget(strength_label)

    strength_description = QLabel("How much to transform the image (0.0 = original, 1.0 = completely new)")
    strength_description.setStyleSheet("font-size: 9pt; color: #888;")
    strength_description.setWordWrap(True)
    controls_layout.addWidget(strength_description)

    # Strength 슬라이더와 입력 필드
    strength_layout = QHBoxLayout()

    parent.img2img_strength_slider = QSlider(Qt.Horizontal)
    parent.img2img_strength_slider.setMinimum(0)
    parent.img2img_strength_slider.setMaximum(100)  # 0.00 ~ 1.00, 0.01 단위
    parent.img2img_strength_slider.setValue(50)  # 기본값 0.5
    parent.img2img_strength_slider.setTickPosition(QSlider.NoTicks)  # 눈금 제거
    parent.img2img_strength_slider.valueChanged.connect(parent.on_img2img_strength_slider_changed)
    strength_layout.addWidget(parent.img2img_strength_slider)

    parent.img2img_strength_input = QLineEdit("0.50")
    parent.img2img_strength_input.setStyleSheet("font-weight: bold;")
    parent.img2img_strength_input.setFixedWidth(60)
    parent.img2img_strength_input.setAlignment(Qt.AlignCenter)
    parent.img2img_strength_input.editingFinished.connect(parent.on_img2img_strength_input_changed)
    strength_layout.addWidget(parent.img2img_strength_input)

    controls_layout.addLayout(strength_layout)

    # Noise 섹션
    noise_label = QLabel("Noise")
    noise_label.setStyleSheet("font-size: 12pt; font-weight: bold;")
    controls_layout.addWidget(noise_label)

    noise_description = QLabel("Extra noise to add (0.0 = none, 1.0 = maximum)")
    noise_description.setStyleSheet("font-size: 9pt; color: #888;")
    noise_description.setWordWrap(True)
    controls_layout.addWidget(noise_description)

    # Noise 슬라이더와 입력 필드
    noise_layout = QHBoxLayout()

    parent.img2img_noise_slider = QSlider(Qt.Horizontal)
    parent.img2img_noise_slider.setMinimum(0)
    parent.img2img_noise_slider.setMaximum(100)  # 0.00 ~ 1.00, 0.01 단위
    parent.img2img_noise_slider.setValue(0)  # 기본값 0.0
    parent.img2img_noise_slider.setTickPosition(QSlider.NoTicks)  # 눈금 제거
    parent.img2img_noise_slider.valueChanged.connect(parent.on_img2img_noise_slider_changed)
    noise_layout.addWidget(parent.img2img_noise_slider)

    parent.img2img_noise_input = QLineEdit("0.00")
    parent.img2img_noise_input.setStyleSheet("font-weight: bold;")
    parent.img2img_noise_input.setFixedWidth(60)
    parent.img2img_noise_input.setAlignment(Qt.AlignCenter)
    parent.img2img_noise_input.editingFinished.connect(parent.on_img2img_noise_input_changed)
    noise_layout.addWidget(parent.img2img_noise_input)

    controls_layout.addLayout(noise_layout)

    # Inpainting section (separator line first)
    separator_line = QFrame()
    separator_line.setFrameShape(QFrame.HLine)
    separator_line.setFrameShadow(QFrame.Sunken)
    separator_line.setStyleSheet("color: #555;")
    controls_layout.addWidget(separator_line)

    # Inpainting checkbox
    parent.inpaint_checkbox = QCheckBox("Inpainting Mode")
    parent.inpaint_checkbox.setStyleSheet("font-size: 12pt; font-weight: bold;")
    parent.inpaint_checkbox.stateChanged.connect(parent.on_inpaint_mode_changed)
    controls_layout.addWidget(parent.inpaint_checkbox)

    inpaint_description = QLabel("Select areas to regenerate (requires mask)")
    inpaint_description.setStyleSheet("font-size: 9pt; color: #888;")
    inpaint_description.setWordWrap(True)
    controls_layout.addWidget(inpaint_description)

    # Paint mask button
    parent.btn_paint_mask = QPushButton("🖌️ Paint Mask")
    parent.btn_paint_mask.clicked.connect(parent.open_mask_paint_dialog)
    parent.btn_paint_mask.setEnabled(False)
    parent.btn_paint_mask.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    controls_layout.addWidget(parent.btn_paint_mask)

    # Mask status label
    parent.mask_status_label = QLabel("No mask painted")
    parent.mask_status_label.setStyleSheet("font-size: 9pt; color: #888; font-style: italic;")
    parent.mask_status_label.setAlignment(Qt.AlignCenter)
    controls_layout.addWidget(parent.mask_status_label)

    controls_layout.addStretch()

    content_layout.addWidget(controls_container)
    layout.addLayout(content_layout)

    return widget

def create_character_reference_widget(parent, left_widget):
    """Character Reference UI 생성 (반응형)"""
    widget = QFrame(left_widget)
    widget.setFrameStyle(QFrame.StyledPanel)
    widget.hide()

    # 반응형 크기 정책 설정
    widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    layout = QVBoxLayout(widget)
    layout.setContentsMargins(10, 10, 10, 10)
    layout.setSpacing(8)

    # 타이틀
    title_label = QLabel("📸 Character Reference")
    title_label.setStyleSheet("font-size: 14pt; font-weight: bold;")
    layout.addWidget(title_label)
    
    # 컨텐츠 영역 (반응형)
    content_layout = QHBoxLayout()
    content_layout.setSpacing(10)
    
    # 왼쪽: 이미지 미리보기
    parent.character_image_label = QLabel()
    parent.character_image_label.setFixedSize(164, 198)
    parent.character_image_label.setAlignment(Qt.AlignCenter)
    parent.character_image_label.setText("No Image")
    content_layout.addWidget(parent.character_image_label)
    
    # 오른쪽: 컨트롤 영역
    controls_container = QWidget()
    controls_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
    controls_layout = QVBoxLayout(controls_container)
    controls_layout.setContentsMargins(0, 0, 0, 0)
    controls_layout.setSpacing(8)
    
    # 버튼 영역 (가로 배치)
    buttons_layout = QHBoxLayout()
    buttons_layout.setSpacing(8)
    
    # 이미지 선택 버튼
    parent.btn_select_character_image = QPushButton("Select Image")
    parent.btn_select_character_image.clicked.connect(parent.select_character_reference_image)
    parent.btn_select_character_image.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    buttons_layout.addWidget(parent.btn_select_character_image)
    
    # 이미지 제거 버튼
    parent.btn_remove_character_image = QPushButton("Remove Image")
    parent.btn_remove_character_image.clicked.connect(parent.remove_character_reference_image)
    parent.btn_remove_character_image.setEnabled(False)
    parent.btn_remove_character_image.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    buttons_layout.addWidget(parent.btn_remove_character_image)
    
    controls_layout.addLayout(buttons_layout)
    
    # Style Aware 섹션
    style_aware_label = QLabel("Style Aware")
    style_aware_label.setStyleSheet("font-size: 12pt; font-weight: bold;")
    controls_layout.addWidget(style_aware_label)
    
    parent.character_style_aware_check = QCheckBox("Include style information from reference")
    parent.character_style_aware_check.setChecked(True)
    parent.character_style_aware_check.stateChanged.connect(parent.on_style_aware_changed)
    controls_layout.addWidget(parent.character_style_aware_check)
    
    # Fidelity 섹션 추가
    fidelity_label = QLabel("Fidelity")
    fidelity_label.setStyleSheet("font-size: 12pt; font-weight: bold;")
    controls_layout.addWidget(fidelity_label)
    
    fidelity_description = QLabel("0: Old version (flexible), 1: New version (detailed)")
    fidelity_description.setStyleSheet("font-size: 9pt; color: #888;")
    controls_layout.addWidget(fidelity_description)
    
    # Fidelity 슬라이더와 값 표시를 위한 수평 레이아웃
    fidelity_layout = QHBoxLayout()
    
    parent.character_fidelity_slider = QSlider(Qt.Horizontal)
    parent.character_fidelity_slider.setMinimum(0)
    parent.character_fidelity_slider.setMaximum(20)  # 0.00 ~ 1.00, 0.05 단위 (20 steps)
    parent.character_fidelity_slider.setValue(20)  # 기본값 1.0
    parent.character_fidelity_slider.setTickPosition(QSlider.TicksBelow)
    parent.character_fidelity_slider.setTickInterval(1)
    parent.character_fidelity_slider.valueChanged.connect(parent.on_fidelity_changed)
    fidelity_layout.addWidget(parent.character_fidelity_slider)
    
    parent.character_fidelity_value_label = QLabel("1.00")
    parent.character_fidelity_value_label.setStyleSheet("font-weight: bold; min-width: 35px;")
    parent.character_fidelity_value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    fidelity_layout.addWidget(parent.character_fidelity_value_label)
    
    controls_layout.addLayout(fidelity_layout)
    
    controls_layout.addStretch()
    
    content_layout.addWidget(controls_container)
    layout.addLayout(content_layout)
    
    return widget


def create_enhance_widget(parent, left_widget):
    """Image Enhance UI 생성 (반응형)"""
    widget = QFrame(parent)
    widget.setFrameStyle(QFrame.StyledPanel)
    widget.hide()

    # 반응형 크기 정책 설정
    widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    layout = QVBoxLayout(widget)
    layout.setContentsMargins(10, 10, 10, 10)
    layout.setSpacing(8)

    # 타이틀
    title_label = QLabel(f"✨ {tr('enhance.title', 'Image Enhance')}")
    title_label.setStyleSheet("font-size: 14pt; font-weight: bold;")
    layout.addWidget(title_label)

    # 컨텐츠 영역 (반응형)
    content_layout = QHBoxLayout()
    content_layout.setSpacing(10)

    # 왼쪽: 이미지 미리보기 (드래그 앤 드롭 지원)
    parent.enhance_image_label = DragDropImageLabel()
    parent.enhance_image_label.setFixedSize(164, 198)
    parent.enhance_image_label.setAlignment(Qt.AlignCenter)
    parent.enhance_image_label.setText(tr('enhance.no_image', 'No Image') + "\n(Drag & Drop)")
    parent.enhance_image_label.setStyleSheet("background-color: rgba(0, 0, 0, 128); color: white; border: 2px dashed #666;")
    parent.enhance_image_label.imageDropped.connect(parent.load_enhance_image_from_path)
    content_layout.addWidget(parent.enhance_image_label)

    # 오른쪽: 컨트롤 영역
    controls_container = QWidget()
    controls_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
    controls_layout = QVBoxLayout(controls_container)
    controls_layout.setContentsMargins(0, 0, 0, 0)
    controls_layout.setSpacing(8)

    # 버튼 영역 (가로 배치)
    buttons_layout = QHBoxLayout()
    buttons_layout.setSpacing(8)

    # 이미지 선택 버튼
    parent.btn_select_enhance_image = QPushButton(tr('enhance.select_image', 'Select Image'))
    parent.btn_select_enhance_image.clicked.connect(parent.select_enhance_image)
    parent.btn_select_enhance_image.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    buttons_layout.addWidget(parent.btn_select_enhance_image)

    # 이미지 제거 버튼
    parent.btn_remove_enhance_image = QPushButton(tr('enhance.remove_image', 'Remove Image'))
    parent.btn_remove_enhance_image.clicked.connect(parent.remove_enhance_image)
    parent.btn_remove_enhance_image.setEnabled(False)
    parent.btn_remove_enhance_image.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    buttons_layout.addWidget(parent.btn_remove_enhance_image)

    controls_layout.addLayout(buttons_layout)

    # 폴더 선택 및 벌크 처리 버튼
    bulk_buttons_layout = QHBoxLayout()
    bulk_buttons_layout.setSpacing(8)

    # 폴더 선택 버튼
    parent.btn_select_enhance_folder = QPushButton(tr('enhance.select_folder', 'Select Folder'))
    parent.btn_select_enhance_folder.clicked.connect(parent.select_enhance_folder)
    parent.btn_select_enhance_folder.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    bulk_buttons_layout.addWidget(parent.btn_select_enhance_folder)

    # 전용 Enhance 버튼 (단일/벌크 처리 모두 사용)
    parent.btn_enhance_create = QPushButton(tr('enhance.create_button', 'Enhance'))
    parent.btn_enhance_create.clicked.connect(parent.start_enhance_process)
    parent.btn_enhance_create.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    parent.btn_enhance_create.setStyleSheet(f"background-color: {COLOR.BUTTON_CUSTOM}; color: white; font-weight: bold;")
    parent.btn_enhance_create.setEnabled(False)
    bulk_buttons_layout.addWidget(parent.btn_enhance_create)

    # Stop 버튼 (벌크 처리 중단용)
    parent.btn_enhance_stop = QPushButton(tr('enhance.stop_button', 'Stop'))
    parent.btn_enhance_stop.clicked.connect(parent.stop_enhance_process)
    parent.btn_enhance_stop.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    parent.btn_enhance_stop.setStyleSheet(f"background-color: {COLOR.BUTTON_AUTOGENERATE}; color: white; font-weight: bold;")
    parent.btn_enhance_stop.setEnabled(False)
    parent.btn_enhance_stop.hide()  # 기본적으로 숨김
    bulk_buttons_layout.addWidget(parent.btn_enhance_stop)

    controls_layout.addLayout(bulk_buttons_layout)

    # 진행 상황 표시 레이블
    parent.enhance_progress_label = QLabel("")
    parent.enhance_progress_label.setStyleSheet("font-size: 10pt; color: #888;")
    parent.enhance_progress_label.setAlignment(Qt.AlignCenter)
    controls_layout.addWidget(parent.enhance_progress_label)

    # Upscale Ratio 섹션
    ratio_label = QLabel(tr('enhance.ratio_label', 'Upscale Ratio'))
    ratio_label.setStyleSheet("font-size: 12pt; font-weight: bold;")
    controls_layout.addWidget(ratio_label)

    # 라디오 버튼 그룹
    ratio_layout = QHBoxLayout()
    parent.enhance_ratio_group = QButtonGroup(parent)

    parent.enhance_ratio_1x = QRadioButton(tr('enhance.ratio_1x', '1x (Same size)'))
    parent.enhance_ratio_1_5x = QRadioButton(tr('enhance.ratio_1_5x', '1.5x'))
    parent.enhance_ratio_1_5x.setChecked(True)  # 기본값 1.5x

    parent.enhance_ratio_group.addButton(parent.enhance_ratio_1x, 0)
    parent.enhance_ratio_group.addButton(parent.enhance_ratio_1_5x, 1)
    parent.enhance_ratio_group.buttonClicked[int].connect(parent.on_enhance_ratio_changed)

    ratio_layout.addWidget(parent.enhance_ratio_1x)
    ratio_layout.addWidget(parent.enhance_ratio_1_5x)
    ratio_layout.addStretch()
    controls_layout.addLayout(ratio_layout)

    # Strength 섹션
    strength_label = QLabel(tr('enhance.strength_label', 'Strength'))
    strength_label.setStyleSheet("font-size: 12pt; font-weight: bold;")
    controls_layout.addWidget(strength_label)

    strength_description = QLabel(tr('enhance.strength_desc', 'Controls enhancement intensity (0.01-0.99)'))
    strength_description.setStyleSheet("font-size: 9pt; color: #888;")
    controls_layout.addWidget(strength_description)

    # Strength 슬라이더와 값 입력을 위한 수평 레이아웃
    strength_layout = QHBoxLayout()

    parent.enhance_strength_slider = QSlider(Qt.Horizontal)
    parent.enhance_strength_slider.setMinimum(1)  # 0.01
    parent.enhance_strength_slider.setMaximum(99)  # 0.99
    parent.enhance_strength_slider.setValue(40)  # 기본값 0.40
    parent.enhance_strength_slider.setTickPosition(QSlider.NoTicks)  # 눈금 숨김
    parent.enhance_strength_slider.valueChanged.connect(parent.on_enhance_strength_changed)
    strength_layout.addWidget(parent.enhance_strength_slider)

    parent.enhance_strength_value_input = QLineEdit("0.40")
    parent.enhance_strength_value_input.setStyleSheet("font-weight: bold;")
    parent.enhance_strength_value_input.setFixedWidth(50)
    parent.enhance_strength_value_input.setAlignment(Qt.AlignCenter)
    parent.enhance_strength_value_input.editingFinished.connect(parent.on_enhance_strength_input_changed)
    strength_layout.addWidget(parent.enhance_strength_value_input)

    controls_layout.addLayout(strength_layout)

    # Noise 섹션
    noise_label = QLabel(tr('enhance.noise_label', 'Noise'))
    noise_label.setStyleSheet("font-size: 12pt; font-weight: bold;")
    controls_layout.addWidget(noise_label)

    noise_description = QLabel(tr('enhance.noise_desc', 'Adds variation to the result (0.00-0.99)'))
    noise_description.setStyleSheet("font-size: 9pt; color: #888;")
    controls_layout.addWidget(noise_description)

    # Noise 슬라이더와 값 입력을 위한 수평 레이아웃
    noise_layout = QHBoxLayout()

    parent.enhance_noise_slider = QSlider(Qt.Horizontal)
    parent.enhance_noise_slider.setMinimum(0)  # 0.00
    parent.enhance_noise_slider.setMaximum(99)  # 0.99
    parent.enhance_noise_slider.setValue(0)  # 기본값 0.00
    parent.enhance_noise_slider.setTickPosition(QSlider.NoTicks)  # 눈금 숨김
    parent.enhance_noise_slider.valueChanged.connect(parent.on_enhance_noise_changed)
    noise_layout.addWidget(parent.enhance_noise_slider)

    parent.enhance_noise_value_input = QLineEdit("0.00")
    parent.enhance_noise_value_input.setStyleSheet("font-weight: bold;")
    parent.enhance_noise_value_input.setFixedWidth(50)
    parent.enhance_noise_value_input.setAlignment(Qt.AlignCenter)
    parent.enhance_noise_value_input.editingFinished.connect(parent.on_enhance_noise_input_changed)
    noise_layout.addWidget(parent.enhance_noise_value_input)

    controls_layout.addLayout(noise_layout)

    controls_layout.addStretch()

    content_layout.addWidget(controls_container)
    layout.addLayout(content_layout)

    return widget


def init_main_widget(parent):
    """메인 위젯 초기화 함수"""
    main_widget = QWidget()
    main_layout = QVBoxLayout()
    main_widget.setLayout(main_layout)
    
    # 메인 스플리터 (좌우 분할)
    parent.main_splitter = QSplitter(Qt.Horizontal)
    
    # 왼쪽 패널 (설정 부분)
    left_widget = QWidget()
    left_layout = QVBoxLayout(left_widget)
    left_layout.setContentsMargins(5, 5, 5, 5)

    # ===== 설정 그룹 섹션 =====
    
    # 프롬프트 영역과 캐릭터 프롬프트 영역을 담을 수직 스플리터 생성
    prompt_char_splitter = QSplitter(Qt.Vertical)

    # 1. 프롬프트 그룹 초기화
    prompt_group = init_advanced_prompt_group(parent)  # 스플리터를 사용한 고급 반응형 버전

    # 2. 캐릭터 프롬프트 그룹 초기화
    character_prompts_group = QGroupBox("Character Prompts (V4)")
    character_prompts_layout = QVBoxLayout()
    character_prompts_layout.setContentsMargins(5, 5, 5, 5)  # 여백 조정
    character_prompts_layout.setSpacing(5)  # 간격 조정
    character_prompts_group.setLayout(character_prompts_layout)

    # 캐릭터 프롬프트 컨테이너 생성 및 추가
    parent.character_prompts_container = CharacterPromptsContainer(parent)
    character_prompts_layout.addWidget(parent.character_prompts_container)

    # 높이 조정 가능하도록 설정
    character_prompts_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
    character_prompts_group.setMinimumHeight(120)  

    # 3. 스플리터에 두 그룹 추가
    prompt_char_splitter.addWidget(prompt_group)
    prompt_char_splitter.addWidget(character_prompts_group)

    # 4. 스플리터 핸들 설정
    prompt_char_splitter.setHandleWidth(8)
    prompt_char_splitter.setChildrenCollapsible(False)  # 영역이 완전히 접히지 않도록 설정
    prompt_char_splitter.setStyleSheet("QSplitter::handle { background-color: #cccccc; }")

    # 5. 초기 크기 비율 설정 (60:40)
    prompt_char_splitter.setSizes([600, 400])

    # 6. 스플리터 참조 저장 (나중에 크기 조정 가능하도록)
    parent.prompt_char_splitter = prompt_char_splitter

    # 7. 왼쪽 레이아웃에 스플리터 추가
    left_layout.addWidget(prompt_char_splitter)

    def adjust_group_size(group_box, size):
        """이미지 위젯 크기가 변경될 때 그룹박스 크기도 조정"""
        # 여백과 버튼 영역을 고려한 추가 공간
        padding_width = 30
        padding_height = 80
        
        # 그룹박스 크기 조정
        group_box.setMinimumSize(
            size.width() + padding_width,
            size.height() + padding_height
        )

    # 이미지 옵션, 고급 설정, 생성 버튼을 수평으로 배치할 컨테이너
    
    # ===== 전체 영역을 상하로 조정 가능하도록 큰 수직 스플리터로 묶기 =====
    main_vertical_splitter = QSplitter(Qt.Vertical)
    
    # 1. 프롬프트 영역 추가 (이미 수직 스플리터로 구성됨)
    main_vertical_splitter.addWidget(prompt_char_splitter)

    # 2. 설정 영역을 담을 컨테이너 위젯 생성
    settings_container = QWidget()
    settings_layout = QVBoxLayout(settings_container)
    settings_layout.setContentsMargins(0, 0, 0, 0)
    settings_layout.setSpacing(5)
    
    # 이미지 옵션 + 고급 설정을 통합한 그룹 (Options & Settings) — QGridLayout으로 공간 효율화
    options_settings_group = QGroupBox("Options & Settings")
    grid = QGridLayout()
    grid.setContentsMargins(5, 5, 5, 5)
    grid.setSpacing(3)
    options_settings_group.setLayout(grid)

    # 열 신축 설정: 0,2열은 레이블(고정), 1,3열은 입력(균등 신축)
    grid.setColumnStretch(1, 1)
    grid.setColumnStretch(3, 1)

    # ── Row 0: Model (전체 폭 사용) ──
    grid.addWidget(QLabel("Model:"), 0, 0)
    parent.dict_ui_settings["model"] = QComboBox()
    from consts import NAI_MODELS, DEFAULT_MODEL
    for model_id, model_name in NAI_MODELS.items():
        parent.dict_ui_settings["model"].addItem(model_name, model_id)
    for i in range(parent.dict_ui_settings["model"].count()):
        if parent.dict_ui_settings["model"].itemData(i) == DEFAULT_MODEL:
            parent.dict_ui_settings["model"].setCurrentIndex(i)
            break
    grid.addWidget(parent.dict_ui_settings["model"], 0, 1, 1, 3)

    # ── Row 1: Size (전체 폭 사용) ──
    combo_resolution = QComboBox()
    parent.combo_resolution = combo_resolution
    _populate_resolution_combo(parent, combo_resolution)
    hd_index = -1
    for i in range(combo_resolution.count()):
        if "Square (1024x1024)" in combo_resolution.itemText(i):
            hd_index = i
            break
    if hd_index >= 0:
        combo_resolution.setCurrentIndex(hd_index)
    grid.addWidget(QLabel("Size:"), 1, 0)
    grid.addWidget(combo_resolution, 1, 1, 1, 3)

    # ── Row 2: W / H / Random (전체 폭) ──
    wh_widget = QWidget()
    wh_layout = QHBoxLayout(wh_widget)
    wh_layout.setContentsMargins(0, 0, 0, 0)
    wh_layout.setSpacing(4)
    wh_layout.addWidget(QLabel("W:"))
    parent.dict_ui_settings["width"] = QLineEdit()
    parent.dict_ui_settings["width"].setAlignment(Qt.AlignRight)
    wh_layout.addWidget(parent.dict_ui_settings["width"], 1)
    wh_layout.addWidget(QLabel("H:"))
    parent.dict_ui_settings["height"] = QLineEdit()
    parent.dict_ui_settings["height"].setAlignment(Qt.AlignRight)
    wh_layout.addWidget(parent.dict_ui_settings["height"], 1)
    checkbox_random_resolution = QCheckBox("Random")
    checkbox_random_resolution.stateChanged.connect(parent.on_random_resolution_checked)
    parent.checkbox_random_resolution = checkbox_random_resolution
    random_checked = parent.settings.value("image_random_checkbox", False, type=bool)
    parent.checkbox_random_resolution.setChecked(random_checked)
    wh_layout.addWidget(parent.checkbox_random_resolution)
    grid.addWidget(wh_widget, 2, 0, 1, 4)

    # ── Row 3: Sampler | Noise Schedule ──
    grid.addWidget(QLabel("Sampler:"), 3, 0)
    parent.dict_ui_settings["sampler"] = QComboBox()
    parent.sampler_mapping = {
        "Euler": "k_euler",
        "Euler Ancestral": "k_euler_ancestral",
        "DPM++ 2S Ancestral": "k_dpmpp_2s_ancestral",
        "DPM++ 2M": "k_dpmpp_2m",
        "DPM++ 2M SDE": "k_dpmpp_sde",
        "DPM++ SDE": "k_dpmpp_sde"
    }
    parent.dict_ui_settings["sampler"].addItems(list(parent.sampler_mapping.keys()))

    def on_sampler_changed(parent, ui_name):
        api_value = parent.sampler_mapping.get(ui_name, ui_name)
        logger.debug(f"Sampler changed: UI={ui_name}, API={api_value}")

    parent.dict_ui_settings["sampler"].currentTextChanged.connect(lambda text: on_sampler_changed(parent, text))
    grid.addWidget(parent.dict_ui_settings["sampler"], 3, 1)
    grid.addWidget(QLabel("Noise:"), 3, 2)
    parent.dict_ui_settings["noise_schedule"] = QComboBox()
    parent.dict_ui_settings["noise_schedule"].addItems(["karras", "exponential", "polyexponential"])
    parent.dict_ui_settings["noise_schedule"].setCurrentText("karras")
    grid.addWidget(parent.dict_ui_settings["noise_schedule"], 3, 3)

    # ── Row 4: Steps | CFG Scale ──
    grid.addWidget(QLabel("Steps:"), 4, 0)
    parent.dict_ui_settings["steps"] = QLineEdit()
    parent.dict_ui_settings["steps"].setAlignment(Qt.AlignRight)
    grid.addWidget(parent.dict_ui_settings["steps"], 4, 1)
    grid.addWidget(QLabel("CFG Scale:"), 4, 2)
    parent.dict_ui_settings["scale"] = QLineEdit()
    parent.dict_ui_settings["scale"].setAlignment(Qt.AlignRight)
    grid.addWidget(parent.dict_ui_settings["scale"], 4, 3)

    # ── Row 5: Seed (Fix / Rnd) | CFG Rescale ──
    seed_widget = QWidget()
    seed_layout = QHBoxLayout(seed_widget)
    seed_layout.setContentsMargins(0, 0, 0, 0)
    seed_layout.setSpacing(3)
    seed_layout.addWidget(QLabel("Seed:"))
    parent.dict_ui_settings["seed"] = QLineEdit()
    parent.dict_ui_settings["seed"].setAlignment(Qt.AlignRight)
    seed_layout.addWidget(parent.dict_ui_settings["seed"], 1)
    parent.dict_ui_settings["seed_fix_checkbox"] = QCheckBox("Fix")
    seed_layout.addWidget(parent.dict_ui_settings["seed_fix_checkbox"])
    seed_random_button = QPushButton("Rnd")
    seed_random_button.clicked.connect(
        lambda: parent.dict_ui_settings["seed"].setText(str(random.randint(0, 2**32-1))))
    seed_layout.addWidget(seed_random_button)
    grid.addWidget(seed_widget, 5, 0, 1, 2)
    grid.addWidget(QLabel("CFG Rescale:"), 5, 2)
    parent.dict_ui_settings["cfg_rescale"] = QLineEdit()
    parent.dict_ui_settings["cfg_rescale"].setAlignment(Qt.AlignRight)
    grid.addWidget(parent.dict_ui_settings["cfg_rescale"], 5, 3)

    # ── Row 6: Variety+ | Legacy Mode ──
    parent.dict_ui_settings["variety_plus"] = QCheckBox("Variety+")
    parent.dict_ui_settings["variety_plus"].setToolTip(tr('advanced.variety_plus_tooltip'))
    grid.addWidget(parent.dict_ui_settings["variety_plus"], 6, 0, 1, 2)
    parent.dict_ui_settings["legacy"] = QCheckBox("Legacy Mode")
    parent.dict_ui_settings["legacy"].setChecked(False)
    grid.addWidget(parent.dict_ui_settings["legacy"], 6, 2, 1, 2)

    # Auto SMEA는 표시하지 않고 내부에서만 사용
    parent.dict_ui_settings["autoSmea"] = QCheckBox("Auto SMEA")
    parent.dict_ui_settings["autoSmea"].setChecked(True)
    parent.dict_ui_settings["autoSmea"].setVisible(False)

    # 설정 컨테이너에 추가
    settings_layout.addWidget(options_settings_group)

    # Character Reference 위젯도 설정 컨테이너에 추가
    parent.character_reference_widget = create_character_reference_widget(parent, left_widget)
    settings_layout.addWidget(parent.character_reference_widget)

    # Image to Image 위젯 추가
    parent.img2img_widget = create_img2img_widget(parent, left_widget)
    settings_layout.addWidget(parent.img2img_widget)

    # Image Enhance 위젯 추가
    parent.enhance_widget = create_enhance_widget(parent, left_widget)
    settings_layout.addWidget(parent.enhance_widget)

    # 3. 설정 컨테이너를 메인 수직 스플리터에 추가
    main_vertical_splitter.addWidget(settings_container)

    # 4. 메인 수직 스플리터 설정
    main_vertical_splitter.setHandleWidth(8)
    main_vertical_splitter.setChildrenCollapsible(False)
    main_vertical_splitter.setStyleSheet("QSplitter::handle { background-color: #cccccc; }")

    # 초기 크기 비율 설정 (프롬프트:설정 = 60:40)
    main_vertical_splitter.setSizes([600, 400])

    # 스플리터 참조 저장
    parent.main_vertical_splitter = main_vertical_splitter

    # 5. left_layout에 메인 수직 스플리터 추가
    left_layout.addWidget(main_vertical_splitter)
    
    

    # Character Reference 위젯 추가 (여기에 추가)
    parent.character_reference_widget = create_character_reference_widget(parent, left_widget)
    left_layout.addWidget(parent.character_reference_widget)        

    # 1.4: 이미지 옵션 (img2img, reference) 그룹 - 숨김 처리하되 객체는 생성
    image_options_group = QGroupBox("Image References")
    image_options_layout = QHBoxLayout()
    image_options_group.setLayout(image_options_layout)
    parent.image_options_layout = image_options_layout

    # img2img 옵션
    parent.i2i_settings_group = ImageToImageWidget("img2img", parent)
    image_options_layout.addWidget(parent.i2i_settings_group)

    # Reference Image 옵션
    parent.vibe_settings_group = ImageToImageWidget("vibe", parent)
    image_options_layout.addWidget(parent.vibe_settings_group)

    # img2img 전용 설정
    parent.i2i_settings = QGroupBox("img2img Settings")
    i2i_settings_layout = QVBoxLayout()
    parent.i2i_settings.setLayout(i2i_settings_layout)

    # strength, noise 설정
    hbox_strength = QHBoxLayout()
    hbox_strength.addWidget(QLabel("Strength:"))
    parent.dict_ui_settings["strength"] = QLineEdit()
    parent.dict_ui_settings["strength"].setAlignment(Qt.AlignRight)
    hbox_strength.addWidget(parent.dict_ui_settings["strength"])
    i2i_settings_layout.addLayout(hbox_strength)

    hbox_noise = QHBoxLayout()
    hbox_noise.addWidget(QLabel("Noise:"))
    parent.dict_ui_settings["noise"] = QLineEdit()
    parent.dict_ui_settings["noise"].setAlignment(Qt.AlignRight)
    hbox_noise.addWidget(parent.dict_ui_settings["noise"])
    i2i_settings_layout.addLayout(hbox_noise)

    image_options_layout.addWidget(parent.i2i_settings)
    parent.i2i_settings.setVisible(False)

    # Reference Image 전용 설정
    parent.vibe_settings = QGroupBox("References Settings")
    vibe_settings_layout = QVBoxLayout()
    parent.vibe_settings.setLayout(vibe_settings_layout)

    # reference image 관련 설정들
    hbox_reference_information_extracted = QHBoxLayout()
    hbox_reference_information_extracted.addWidget(
        QLabel("Reference Information Extracted:"))
    parent.dict_ui_settings["reference_information_extracted"] = QLineEdit()
    parent.dict_ui_settings["reference_information_extracted"].setAlignment(
        Qt.AlignRight)
    hbox_reference_information_extracted.addWidget(
        parent.dict_ui_settings["reference_information_extracted"])
    vibe_settings_layout.addLayout(hbox_reference_information_extracted)

    hbox_reference_strength = QHBoxLayout()
    hbox_reference_strength.addWidget(QLabel("Reference Strength:"))
    parent.dict_ui_settings["reference_strength"] = QLineEdit()
    parent.dict_ui_settings["reference_strength"].setAlignment(Qt.AlignRight)
    hbox_reference_strength.addWidget(parent.dict_ui_settings["reference_strength"])
    vibe_settings_layout.addLayout(hbox_reference_strength)

    image_options_layout.addWidget(parent.vibe_settings)
    parent.vibe_settings.setVisible(False)

    # UI에 그룹은 추가하되 숨김 처리
    left_layout.addWidget(image_options_group)
    image_options_group.setVisible(False) 


    # 1.5: 버튼 레이아웃
    button_layout = QHBoxLayout()

    # 로그인 상태
    parent.label_loginstate = LoginStateWidget()
    button_layout.addWidget(parent.label_loginstate)

    # ANLAS 표시
    parent.label_anlas = QLabel("Anlas: ?")
    button_layout.addWidget(parent.label_anlas)
    parent.statusBar().addPermanentWidget(parent.label_anlas)
    

    # 2: 오른쪽 레이아웃 - 결과
    right_widget = QWidget()
    right_layout = QVBoxLayout()
    right_widget.setLayout(right_layout)

    # 2.1: 결과 이미지 그룹
    result_image_group = QGroupBox(tr('result.image_title'))
    result_image_layout = QVBoxLayout()
    result_image_group.setLayout(result_image_layout)
    
    # 이미지 보기
    parent.image_result = ResizableImageWidget()
    result_image_layout.addWidget(parent.image_result)
    
    # 크기 변경 시그널 연결
    parent.image_result.size_changed.connect(
        lambda size: adjust_group_size(result_image_group, size))
    
    # 결과 프롬프트는 이미지 오버레이로 표시 (image_result.prompt_overlay 참조)
    parent.prompt_result = parent.image_result.prompt_overlay

    # 이미지 버튼 영역 — 왼쪽: 생성 버튼, 오른쪽: 이미지 관리 + 오버레이 토글
    hbox_image_buttons = QHBoxLayout()
    hbox_image_buttons.setSpacing(4)

    # ── 왼쪽: 생성 버튼 ──
    parent.button_generate_once = QPushButton(tr('generate.once'))
    parent.button_generate_once.clicked.connect(parent.on_click_generate_once)
    hbox_image_buttons.addWidget(parent.button_generate_once)

    parent.button_generate_auto = QPushButton(tr('generate.auto'))
    parent.button_generate_auto.clicked.connect(parent.on_click_generate_auto)
    hbox_image_buttons.addWidget(parent.button_generate_auto)

    parent.button_generate_sett = QPushButton(tr('generate.by_settings'))
    parent.button_generate_sett.clicked.connect(parent.on_click_generate_sett)
    hbox_image_buttons.addWidget(parent.button_generate_sett)

    # 구분선
    btn_separator = QFrame()
    btn_separator.setFrameShape(QFrame.VLine)
    btn_separator.setFrameShadow(QFrame.Sunken)
    hbox_image_buttons.addWidget(btn_separator)

    hbox_image_buttons.addStretch(1)

    # ── 오른쪽: 이미지 관리 버튼 ──
    button_save_image = QPushButton(tr('result.save_image'))
    button_save_image.clicked.connect(lambda: parent.image_result.save_image())
    hbox_image_buttons.addWidget(button_save_image)

    button_reset_size = QPushButton(tr('ui.reset_image_size'))
    button_reset_size.setToolTip(tr('ui.reset_image_size_tooltip'))
    button_reset_size.clicked.connect(lambda: parent.image_result.reset_to_default_size())
    hbox_image_buttons.addWidget(button_reset_size)

    # 오버레이 토글 체크박스
    parent.checkbox_overlay_toggle = QCheckBox(tr('result.overlay_toggle'))
    parent.checkbox_overlay_toggle.stateChanged.connect(
        lambda state: parent.image_result.set_overlay_visible(state == Qt.Checked))
    hbox_image_buttons.addWidget(parent.checkbox_overlay_toggle)

    result_image_layout.addLayout(hbox_image_buttons)

    # 저장된 크기 기준으로 초기 그룹 크기 설정
    initial_width = parent.image_result.width() + 30  # 여백 고려
    initial_height = parent.image_result.height() + 80  # 버튼 영역과 여백 고려
    result_image_group.setMinimumSize(initial_width, initial_height)

    # 오른쪽 레이아웃에 결과 이미지 그룹 추가
    right_layout.addWidget(result_image_group)

    # 스플리터에 좌우 레이아웃 추가
    parent.main_splitter.addWidget(left_widget)
    parent.main_splitter.addWidget(right_widget)
    
    # 스플리터 설정
    parent.main_splitter.setHandleWidth(6)
    parent.main_splitter.setChildrenCollapsible(False)
    
    # 좌측 패널 최소 너비 설정
    left_widget.setMinimumWidth(500)

    # 메인 레이아웃에 스플리터 추가
    main_layout.addWidget(parent.main_splitter)
    
    
    # 이벤트 연결
    combo_resolution.currentIndexChanged.connect(lambda idx: set_resolution(parent, idx))
    parent.i2i_settings_group.is_active_changed.connect(lambda is_active: parent.i2i_settings.setVisible(is_active))
    parent.vibe_settings_group.is_active_changed.connect(lambda is_active: parent.vibe_settings.setVisible(is_active))

    return main_widget

def init_session_status_indicator(parent):
    """세션 상태 표시기 초기화"""
    parent.session_status_indicator = QLabel("● 0%")
    parent.session_status_indicator.setStyleSheet("color: green; font-weight: bold;")
    parent.session_status_indicator.setToolTip(tr('ui.session_status'))
    parent.statusBar().addPermanentWidget(parent.session_status_indicator)

# 기본 프롬프트 그룹 수정
def init_responsive_prompt_group(parent):
    """반응형 프롬프트 그룹 초기화"""
    prompt_group = QGroupBox("Prompt")
    prompt_layout = QVBoxLayout()
    prompt_group.setLayout(prompt_layout)

    # 프롬프트 입력 영역
    prompt_label = QLabel(tr('ui.prompt'))
    parent.dict_ui_settings["prompt"] = CompletionTextEdit()
    parent.dict_ui_settings["prompt"].setPlaceholderText(tr('ui.prompt_placeholder'))
    
    # 프롬프트 에디터에 대한 최소 높이 설정 (화면 크기에 따라 조정됨)
    parent.dict_ui_settings["prompt"].setMinimumHeight(100)
    
    # 네거티브 프롬프트 입력 영역
    neg_prompt_label = QLabel(tr('ui.negative_prompt'))
    parent.dict_ui_settings["negative_prompt"] = CompletionTextEdit()
    parent.dict_ui_settings["negative_prompt"].setPlaceholderText(tr('ui.negative_prompt_placeholder'))
    
    # 네거티브 프롬프트 에디터에 대한 최소 높이 설정 (화면 크기에 따라 조정됨)
    parent.dict_ui_settings["negative_prompt"].setMinimumHeight(80)
    
    # 레이아웃에 추가
    prompt_layout.addWidget(prompt_label)
    prompt_layout.addWidget(parent.dict_ui_settings["prompt"])
    prompt_layout.addWidget(neg_prompt_label)
    prompt_layout.addWidget(parent.dict_ui_settings["negative_prompt"])
    
    # 프롬프트와 네거티브 프롬프트의 사이즈 비율 설정 (기본값: 6:4)
    prompt_layout.setStretch(1, 6)  # 프롬프트 영역: 60%
    prompt_layout.setStretch(3, 4)  # 네거티브 프롬프트 영역: 40%
    
    return prompt_group



def show_custom_message(parent, title, message, icon_type=None):
    """
    시스템 기본 스타일의 메시지 대화상자를 표시합니다.
    """
    from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
    from PyQt5.QtGui import QIcon
    from PyQt5.QtCore import Qt
    
    # 커스텀 대화상자 생성
    dialog = QDialog(parent)
    dialog.setWindowTitle(title)
    dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
    dialog.setFixedWidth(400)
    
    # 명시적으로 모든 스타일 제거
    dialog.setStyleSheet("""
        QDialog {
            background-color: #F0F0F0;
        }
        QLabel {
            color: #000000;
            background-color: transparent;
        }
        QPushButton {
            background-color: #E0E0E0;
            color: #000000;
            padding: 6px 12px;
            border: 1px solid #CCCCCC;
            min-width: 80px;
        }
        QPushButton:hover {
            background-color: #D0D0D0;
        }
    """)
    
    # 레이아웃 설정
    layout = QVBoxLayout(dialog)
    
    # 아이콘과 메시지 영역
    msg_layout = QHBoxLayout()
    
    # 아이콘 설정
    if icon_type:
        icon_label = QLabel()
        icon = QIcon.fromTheme("dialog-information")
        if icon_type == "warning":
            icon = QIcon.fromTheme("dialog-warning")
        elif icon_type == "error":
            icon = QIcon.fromTheme("dialog-error")
            
        icon_label.setPixmap(icon.pixmap(32, 32))
        icon_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        msg_layout.addWidget(icon_label)
    
    # 메시지 텍스트
    msg_label = QLabel(message)
    msg_label.setWordWrap(True)
    msg_layout.addWidget(msg_label, 1)
    
    layout.addLayout(msg_layout)
    
    # 버튼 영역
    btn_layout = QHBoxLayout()
    btn_layout.addStretch()
    
    ok_button = QPushButton(tr('dialogs.ok'))
    ok_button.setAutoDefault(True)
    ok_button.setDefault(True)
    ok_button.clicked.connect(dialog.accept)
    btn_layout.addWidget(ok_button)
    
    layout.addLayout(btn_layout)
    
    dialog.exec_()

def set_resolution(parent, idx):
    if idx < 0:
        return

    text = parent.combo_resolution.currentText()
    if text == tr('ui.custom_resolution'):
        return

    try:
        res_text = text.split("(")[1].split(")")[0]
        width, height = res_text.split("x")

        parent.dict_ui_settings["width"].setText(width)
        parent.dict_ui_settings["height"].setText(height)
    except Exception as e:
        logger.error(f"Error parsing resolution: {e}")

def init_advanced_group(parent):
    advanced_group = QGroupBox("Advanced Settings")
    advanced_layout = QVBoxLayout()
    advanced_group.setLayout(advanced_layout)

    # 모델 선택 추가
    hbox_model = QHBoxLayout()
    hbox_model.addWidget(QLabel("Model:"))
    parent.dict_ui_settings["model"] = QComboBox()
    
    # 업데이트된 모델 목록 추가
    from consts import NAI_MODELS, DEFAULT_MODEL
    for model_id, model_name in NAI_MODELS.items():
        parent.dict_ui_settings["model"].addItem(model_name, model_id)
    
    # 기본 모델을 4.5 full로 선택
    for i in range(parent.dict_ui_settings["model"].count()):
        if parent.dict_ui_settings["model"].itemData(i) == DEFAULT_MODEL:
            parent.dict_ui_settings["model"].setCurrentIndex(i)
            break
    
    hbox_model.addWidget(parent.dict_ui_settings["model"])
    advanced_layout.addLayout(hbox_model)
    
    # CFG Scale 설정
    hbox_scale = QHBoxLayout()
    hbox_scale.addWidget(QLabel("Prompt Guidance:"))
    parent.dict_ui_settings["scale"] = QLineEdit()
    parent.dict_ui_settings["scale"].setAlignment(Qt.AlignRight)
    hbox_scale.addWidget(parent.dict_ui_settings["scale"])
    advanced_layout.addLayout(hbox_scale)

    # CFG Rescale 설정
    hbox_cfgrescale = QHBoxLayout()
    hbox_cfgrescale.addWidget(QLabel("Prompt Guidance Rescale:"))
    parent.dict_ui_settings["cfg_rescale"] = QLineEdit()
    parent.dict_ui_settings["cfg_rescale"].setAlignment(Qt.AlignRight)
    hbox_cfgrescale.addWidget(parent.dict_ui_settings["cfg_rescale"])
    advanced_layout.addLayout(hbox_cfgrescale)

    # Variety+ 설정 추가
    variety_layout = QHBoxLayout()
    parent.dict_ui_settings["variety_plus"] = QCheckBox("Variety+")
    parent.dict_ui_settings["variety_plus"].setToolTip(tr('advanced.variety_plus_tooltip'))
    variety_layout.addWidget(parent.dict_ui_settings["variety_plus"])
    advanced_layout.addLayout(variety_layout)
    
    # Noise Schedule 설정
    hbox_noise_schedule = QHBoxLayout()
    
    # Noise Schedule 설정
    hbox_noise_schedule = QHBoxLayout()
    hbox_noise_schedule.addWidget(QLabel("Noise Schedule:"))
    parent.dict_ui_settings["noise_schedule"] = QComboBox()
    parent.dict_ui_settings["noise_schedule"].addItems(["karras", "exponential", "polyexponential"])
    parent.dict_ui_settings["noise_schedule"].setCurrentText("karras")
    hbox_noise_schedule.addWidget(parent.dict_ui_settings["noise_schedule"])
    advanced_layout.addLayout(hbox_noise_schedule)
    
    # Legacy Mode 설정
    parent.dict_ui_settings["legacy"] = QCheckBox("Legacy Prompt Conditioning Mode")
    parent.dict_ui_settings["legacy"].setChecked(False)
    advanced_layout.addWidget(parent.dict_ui_settings["legacy"])
    
    # Auto SMEA는 표시하지 않고 내부에서만 사용
    parent.dict_ui_settings["autoSmea"] = QCheckBox("Auto SMEA")
    parent.dict_ui_settings["autoSmea"].setChecked(True)
    parent.dict_ui_settings["autoSmea"].setVisible(False)
    
    # 레이아웃 여백과 간격 조정
    advanced_layout.setContentsMargins(5, 5, 5, 5)
    advanced_layout.setSpacing(3)
    
    return advanced_group


class LoginStateWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.state_label = QLabel(tr('misc.not_logged_in'))
        self.state_label.setStyleSheet("color:red;")
        layout.addWidget(self.state_label)
        self.setLayout(layout)

    def set_logged_in(self, is_logged_in):
        if is_logged_in:
            self.state_label.setText(tr('misc.logged_in'))
            self.state_label.setStyleSheet("color:green;")
        else:
            self.state_label.setText(tr('misc.not_logged_in'))
            self.state_label.setStyleSheet("color:red;")


class ImageToImageWidget(QGroupBox):
    is_active_changed = pyqtSignal(bool)

    def __init__(self, mode, parent):
        title = tr('ui.img2img_title') if mode == "img2img" else tr('ui.reference_image_title')
        super().__init__(title)
        self.parent = parent
        self.mode = mode
        self.src = None

        self.setMinimumHeight(150)
        self.mask = None
        self.init_ui()

        self.is_maskmode = False
        self.is_randompick = False
        self.random_index = -1

    def init_ui(self):
        layout = QVBoxLayout()

        # 이미지 부분
        self.image_label = QLabel(tr('ui.no_uploaded_image'))
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.image_label.setStyleSheet("background-color: rgba(0, 0, 0, 128);")
        layout.addWidget(self.image_label)

        # 버튼 부분
        button_layout = QHBoxLayout()

        # 왼쪽 버튼 부분
        left_button_layout = QHBoxLayout()

        self.upload_button = QPushButton(tr('ui.load_image'))
        self.upload_button.clicked.connect(
            lambda: self.parent.show_file_dialog(self.mode))
        left_button_layout.addWidget(self.upload_button)

        self.open_folder_button = QPushButton(tr('ui.select_folder'))
        self.open_folder_button.clicked.connect(
            lambda: self.parent.show_openfolder_dialog(self.mode))
        left_button_layout.addWidget(self.open_folder_button)

        button_layout.addLayout(left_button_layout)

        # 체크박스 부분
        check_layout = QHBoxLayout()
        if self.mode == "img2img":
            self.mask_checkbox = QCheckBox("마스크 그리기")
            self.mask_checkbox.stateChanged.connect(self.on_mask_checked)
            check_layout.addWidget(self.mask_checkbox)

        self.tagcheck_checkbox = QCheckBox("태그 읽기")
        self.tagcheck_checkbox.stateChanged.connect(
            lambda: self.parent.on_click_tagcheckbox(self.mode))
        check_layout.addWidget(self.tagcheck_checkbox)

        button_layout.addLayout(check_layout)

        # 오른쪽 버튼 부분
        self.remove_button = QPushButton("제거")
        self.remove_button.clicked.connect(self.on_click_removebutton)
        button_layout.addWidget(self.remove_button)

        layout.addLayout(button_layout)

        # 폴더 모드 UI
        self.folder_widget = QWidget()
        folder_layout = QHBoxLayout()
        folder_layout.setContentsMargins(0, 0, 0, 0)
        
        self.prev_button = QPushButton("이전")
        self.prev_button.clicked.connect(self.on_click_prev)
        folder_layout.addWidget(self.prev_button)
        
        self.next_button = QPushButton("다음")
        self.next_button.clicked.connect(self.on_click_next)
        folder_layout.addWidget(self.next_button)
        
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["오름차순", "내림차순", "랜덤"])
        folder_layout.addWidget(self.sort_combo)
        
        self.folder_widget.setLayout(folder_layout)
        layout.addWidget(self.folder_widget)
        self.folder_widget.setVisible(False)
        
        self.setLayout(layout)

    def get_folder_sort_mode(self):
        return self.sort_combo.currentText()

    def set_folder_mode(self, is_folder_mode):
        self.folder_widget.setVisible(is_folder_mode)

    def set_image(self, src):
        self.src = src
        if src:
            pixmap = QPixmap(src)
            scaled_pixmap = pixmap.scaledToHeight(
                128, Qt.SmoothTransformation)
            self.image_label.setPixmap(scaled_pixmap)
        else:
            self.image_label.setText(tr('ui.no_uploaded_image'))
            self.image_label.setPixmap(QPixmap())

        self.is_active_changed.emit(bool(src))

    def on_click_removebutton(self):
        self.src = None
        self.mask = None
        self.is_maskmode = False
        if hasattr(self, 'mask_checkbox'):
            self.mask_checkbox.setChecked(False)
        self.image_label.setText(tr('ui.no_uploaded_image'))
        self.image_label.setPixmap(QPixmap())
        self.image_label.setCursor(Qt.ArrowCursor)
        self.is_active_changed.emit(False)

    def on_mask_checked(self, state):
        self.is_maskmode = (state == Qt.Checked)
        if self.is_maskmode:
            if self.src:
                self.mask = QImage(QPixmap(self.src).toImage().size(), QImage.Format_ARGB32)
                self.mask.fill(Qt.black)
                self.image_label.setCursor(Qt.CrossCursor)
                self.image_label.mousePressEvent = self.mousePressEvent
                self.image_label.mouseMoveEvent = self.mouseMoveEvent
                self.image_label.mouseReleaseEvent = self.mouseReleaseEvent
                self.mousePressPos = None
        else:
            self.mask = None
            self.image_label.setCursor(Qt.ArrowCursor)
            self.image_label.mousePressEvent = None
            self.image_label.mouseMoveEvent = None
            self.image_label.mouseReleaseEvent = None

    def on_click_prev(self):
        if self.mode == "img2img":
            self.parent.dict_img_batch_target["img2img_index"] -= 2
            self.parent.proceed_image_batch("img2img")
        else:
            self.parent.dict_img_batch_target["vibe_index"] -= 2
            self.parent.proceed_image_batch("vibe")

    def on_click_next(self):
        if self.mode == "img2img":
            self.parent.proceed_image_batch("img2img")
        else:
            self.parent.proceed_image_batch("vibe")

    def mousePressEvent(self, event: QMouseEvent):
        if not self.is_maskmode or not self.src:
            return
        self.mousePressPos = event.pos()
        self.drawMask(event.pos())

    def mouseMoveEvent(self, event: QMouseEvent):
        if not self.is_maskmode or not self.mousePressPos:
            return
        self.drawMask(event.pos())

    def mouseReleaseEvent(self, event: QMouseEvent):
        if not self.is_maskmode:
            return
        self.mousePressPos = None

    def drawMask(self, pos):
        if not self.mask:
            return

        # 원본 이미지 크기와 라벨 크기 비율 계산
        pixmap = QPixmap(self.src)
        img_w, img_h = pixmap.width(), pixmap.height()
        label_w, label_h = self.image_label.width(), self.image_label.height()

        # 이미지가 라벨 내 어떻게 스케일되는지 계산
        ratio = min(label_w / img_w, label_h / img_h)
        scaled_w, scaled_h = img_w * ratio, img_h * ratio

        # 라벨 내 이미지 위치 계산
        offset_x = (label_w - scaled_w) / 2
        offset_y = (label_h - scaled_h) / 2

        # 라벨 좌표를 이미지 좌표로 변환
        x = (pos.x() - offset_x) / ratio if ratio > 0 else 0
        y = (pos.y() - offset_y) / ratio if ratio > 0 else 0

        if 0 <= x < img_w and 0 <= y < img_h:
            # 마스크에 그리기
            painter = QPainter(self.mask)
            painter.setPen(QPen(Qt.white, 10, Qt.SolidLine, Qt.RoundCap))
            
            if self.mousePressPos:
                prev_x = (self.mousePressPos.x() - offset_x) / ratio
                prev_y = (self.mousePressPos.y() - offset_y) / ratio
                painter.drawLine(prev_x, prev_y, x, y)
            else:
                painter.drawPoint(x, y)
            
            painter.end()
            self.mousePressPos = pos

            # 마스크 오버레이와 함께 이미지 표시
            self.updateMaskOverlay()

    def updateMaskOverlay(self):
        if not self.src or not self.mask:
            return

        pixmap = QPixmap(self.src)
        overlay = QImage(pixmap.size(), QImage.Format_ARGB32)
        overlay.fill(Qt.transparent)

        # 마스크를 반투명 빨간색 오버레이로 변환
        for y in range(self.mask.height()):
            for x in range(self.mask.width()):
                if self.mask.pixelColor(x, y).value() > 0:  # 마스크에 그려진 부분
                    overlay.setPixelColor(x, y, QColor(255, 0, 0, 128))

        # 원본 이미지와 오버레이 합성
        result = QPixmap(pixmap.size())
        result.fill(Qt.transparent)

        painter = QPainter(result)
        painter.drawPixmap(0, 0, pixmap)
        painter.drawImage(0, 0, overlay)
        painter.end()

        # 결과 표시
        scaled_pixmap = result.scaledToHeight(128, Qt.SmoothTransformation)
        self.image_label.setPixmap(scaled_pixmap)


def set_sampler_by_api_value(parent, api_value):
    """API 값으로 샘플러 콤보박스 설정"""
    try:
        # sampler_mapping이 초기화되었는지 확인
        if not hasattr(parent, 'sampler_mapping') or not parent.sampler_mapping:
            logger.warning(f"sampler_mapping이 초기화되지 않았습니다. 기본값을 사용합니다.")
            if hasattr(parent, 'dict_ui_settings') and "sampler" in parent.dict_ui_settings:
                parent.dict_ui_settings["sampler"].setCurrentIndex(0)
            return

        # API 값에서 UI 이름으로 역매핑
        ui_name = None
        for name, value in parent.sampler_mapping.items():
            if value == api_value:
                ui_name = name
                break

        # 매핑된 UI 이름이 있으면 선택, 없으면 기본값(첫 번째 항목) 선택
        if ui_name and ui_name in parent.sampler_mapping:
            parent.dict_ui_settings["sampler"].setCurrentText(ui_name)
        else:
            logger.warning(f"API 값 '{api_value}'에 대한 UI 매핑을 찾을 수 없습니다. 기본값을 사용합니다.")
            # 기본값 선택
            parent.dict_ui_settings["sampler"].setCurrentIndex(0)
    except Exception as e:
        logger.error(f"set_sampler_by_api_value 오류: {e}")
        # 오류 발생 시에도 기본값으로 설정
        try:
            if hasattr(parent, 'dict_ui_settings') and "sampler" in parent.dict_ui_settings:
                parent.dict_ui_settings["sampler"].setCurrentIndex(0)
        except:
            pass
    

class ResizableImageWidget(QFrame):
    """크기 조절이 가능한 이미지 결과 위젯"""
    
    # 크기 변경 시그널
    size_changed = pyqtSignal(QSize)
    
    # 기본 크기 상수 정의
    DEFAULT_WIDTH = 512
    DEFAULT_HEIGHT = 512
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Sunken)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(self.DEFAULT_WIDTH, self.DEFAULT_HEIGHT)
        
        # 설정 객체
        self.settings = QSettings("dcp_arca", "nag_gui")
        
        # 레이아웃 설정
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # 이미지 라벨
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setText(tr('result.no_image'))
        self.image_label.setStyleSheet("background-color: rgba(0, 0, 0, 128);")
        self.layout.addWidget(self.image_label)
        
        # 이미지 데이터
        self.image_path = None
        self.original_image_data = None
        
        # 리사이즈 핸들 설정
        self.setMouseTracking(True)
        self.resizing = False
        self.resize_start_pos = None
        self.original_size = None
        self.resize_margin = 10  # 가장자리 마진
        
        # 저장된 크기 불러오기
        self.load_widget_size()

        # 프롬프트 오버레이 (레이아웃에 추가하지 않고 절대 위치로 배치)
        self.prompt_overlay = QTextBrowser(self)
        self.prompt_overlay.setReadOnly(True)
        self.prompt_overlay.setStyleSheet("""
            QTextBrowser {
                background-color: rgba(0, 0, 0, 160);
                color: #ffffff;
                border: none;
                font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                font-size: 10pt;
                padding: 8px;
            }
        """)
        self.prompt_overlay.setVisible(False)
        self._overlay_visible = False

    def set_overlay_visible(self, visible):
        """오버레이 표시/비표시 전환"""
        self._overlay_visible = visible
        self.prompt_overlay.setVisible(visible)
        if visible:
            self._position_overlay()

    def _position_overlay(self):
        """오버레이를 위젯 하단 40%에 배치"""
        overlay_height = max(120, int(self.height() * 0.40))
        self.prompt_overlay.setGeometry(
            0, self.height() - overlay_height,
            self.width(), overlay_height
        )

    def apply_overlay_color(self, color_str):
        """오버레이 텍스트 색상 적용"""
        self.prompt_overlay.setStyleSheet(f"""
            QTextBrowser {{
                background-color: rgba(0, 0, 0, 160);
                color: {color_str};
                border: none;
                font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                font-size: 10pt;
                padding: 8px;
            }}
        """)

    def resizeEvent(self, event):
        """위젯 크기 변경 시 오버레이 위치 갱신"""
        super().resizeEvent(event)
        if self._overlay_visible:
            self._position_overlay()

    def load_widget_size(self):
        """저장된 위젯 크기 불러오기"""
        saved_width = self.settings.value("result_image_width", self.DEFAULT_WIDTH, type=int)
        saved_height = self.settings.value("result_image_height", self.DEFAULT_HEIGHT, type=int)
        
        # 최소 크기보다 작으면 최소 크기로 설정
        saved_width = max(saved_width, self.minimumWidth())
        saved_height = max(saved_height, self.minimumHeight())
        
        self.resize(saved_width, saved_height)
        
        # 부모 위젯에게 크기 변경 알림
        self.size_changed.emit(QSize(saved_width, saved_height))
    
    def save_widget_size(self):
        """위젯 크기 저장"""
        self.settings.setValue("result_image_width", self.width())
        self.settings.setValue("result_image_height", self.height())
    
    def reset_to_default_size(self):
        """위젯 크기를 기본값으로 리셋"""
        # 기본 크기로 설정
        self.resize(self.DEFAULT_WIDTH, self.DEFAULT_HEIGHT)
        
        # 설정 저장
        self.settings.setValue("result_image_width", self.DEFAULT_WIDTH)
        self.settings.setValue("result_image_height", self.DEFAULT_HEIGHT)
        
        # 이미지 크기 조정
        self.refresh_size()
        
        # 부모 위젯에게 크기 변경 알림
        self.size_changed.emit(QSize(self.DEFAULT_WIDTH, self.DEFAULT_HEIGHT))

        # 로그 출력
        logger.info(f"이미지 크기 기본값으로 재설정: {self.DEFAULT_WIDTH}x{self.DEFAULT_HEIGHT}")
    
    def set_custom_pixmap(self, src):
        """이미지 설정"""
        self.image_path = src
        self.original_image_data = None  # 초기화

        try:
            if isinstance(src, str):
                pixmap = QPixmap(src)
                if not pixmap.isNull():
                    # 원본 이미지 데이터 저장
                    with open(src, 'rb') as f:
                        self.original_image_data = f.read()
                    self.image_label.setPixmap(pixmap.scaled(
                        self.image_label.width(), self.image_label.height(), 
                        Qt.KeepAspectRatio, Qt.SmoothTransformation))
                else:
                    self.image_label.setText("이미지 로드 실패")
                    self.image_path = None
            else:
                # 바이트 데이터인 경우
                self.original_image_data = src  # 원본 이미지 데이터 저장
                image = QImage()
                image.loadFromData(src)
                pixmap = QPixmap.fromImage(image)
                if not pixmap.isNull():
                    self.image_label.setPixmap(pixmap.scaled(
                        self.image_label.width(), self.image_label.height(), 
                        Qt.KeepAspectRatio, Qt.SmoothTransformation))
                else:
                    self.image_label.setText("이미지 로드 실패")
                    self.image_path = None
                    self.original_image_data = None
        except Exception as e:
            logger.error(f"Error loading custom pixmap: {e}")
            self.image_label.setText("이미지 로드 오류: " + str(e))
            self.image_path = None
            self.original_image_data = None
    
    def refresh_size(self):
        """이미지 크기 새로고침"""
        if not self.image_path and not self.original_image_data:
            return  # 이미지가 없으면 아무 작업도 하지 않음
            
        try:
            if isinstance(self.image_path, str) and os.path.isfile(self.image_path):
                # 파일 경로가 있는 경우
                pixmap = QPixmap(self.image_path)
                if not pixmap.isNull():
                    self.image_label.setPixmap(pixmap.scaled(
                        self.image_label.width(), self.image_label.height(), 
                        Qt.KeepAspectRatio, Qt.SmoothTransformation))
            elif self.original_image_data:
                # 저장된 원본 데이터가 있는 경우
                image = QImage()
                image.loadFromData(self.original_image_data)
                pixmap = QPixmap.fromImage(image)
                if not pixmap.isNull():
                    self.image_label.setPixmap(pixmap.scaled(
                        self.image_label.width(), self.image_label.height(), 
                        Qt.KeepAspectRatio, Qt.SmoothTransformation))
        except Exception as e:
            logger.error(f"Error refreshing image size: {e}")
    
    def save_image(self):
        """이미지 저장 기능"""
        if not self.image_path and not self.original_image_data:
            QMessageBox.warning(self, "경고", "저장할 이미지가 없습니다.")
            return
            
        # 파일 저장 대화상자 열기
        from datetime import datetime
        default_name = f"nai_image_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        filename, _ = QFileDialog.getSaveFileName(
            self, "이미지 저장", default_name, "Images (*.png *.jpg *.jpeg)"
        )
        
        if filename:
            # 이미지 저장
            try:
                if self.image_path and os.path.isfile(self.image_path):
                    # 파일 경로가 있는 경우, 해당 파일을 복사
                    import shutil
                    shutil.copy2(self.image_path, filename)
                elif self.original_image_data:
                    # 원본 이미지 데이터가 있는 경우
                    from PIL import Image
                    import io
                    if isinstance(self.original_image_data, bytes):
                        # 바이트 데이터인 경우
                        img = Image.open(io.BytesIO(self.original_image_data))
                        img.save(filename)
                    else:
                        # pixmap에서 이미지 저장
                        pixmap = self.image_label.pixmap()
                        if pixmap and not pixmap.isNull():
                            pixmap.save(filename)
                
                # 성공 메시지 표시
                QMessageBox.information(self, "정보", f"이미지가 성공적으로 저장되었습니다.\n{filename}")
            except Exception as e:
                # 오류 메시지 표시
                QMessageBox.critical(self, "오류", f"이미지 저장 중 오류가 발생했습니다.\n{str(e)}")
    
    def mousePressEvent(self, event):
        """마우스 클릭 이벤트"""
        # 오른쪽 아래 모서리 근처에서만 리사이즈 가능
        if self.is_in_resize_area(event.pos()):
            self.resizing = True
            self.resize_start_pos = event.globalPos()
            self.original_size = self.size()
            self.setCursor(Qt.SizeFDiagCursor)
        else:
            super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """마우스 이동 이벤트"""
        if self.resizing:
            # 리사이즈 중
            diff = event.globalPos() - self.resize_start_pos
            new_width = max(self.minimumWidth(), self.original_size.width() + diff.x())
            new_height = max(self.minimumHeight(), self.original_size.height() + diff.y())
            new_size = QSize(new_width, new_height)
            
            self.resize(new_width, new_height)
            self.refresh_size()  # 이미지 크기 업데이트
            
            # 부모 위젯에게 크기 변경 알림
            self.size_changed.emit(new_size)
        elif self.is_in_resize_area(event.pos()):
            # 리사이즈 영역에 있을 때 커서 변경
            self.setCursor(Qt.SizeFDiagCursor)
        else:
            # 일반 영역
            self.setCursor(Qt.ArrowCursor)
            super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        """마우스 릴리즈 이벤트"""
        if self.resizing:
            self.resizing = False
            self.save_widget_size()  # 크기 저장
            self.setCursor(Qt.ArrowCursor)
        else:
            super().mouseReleaseEvent(event)
    
    def is_in_resize_area(self, pos):
        """리사이즈 영역인지 확인"""
        # 오른쪽 아래 모서리 근처
        return (self.width() - pos.x() < self.resize_margin and 
                self.height() - pos.y() < self.resize_margin)
    
    def paintEvent(self, event):
        """위젯 그리기 이벤트 - 리사이즈 핸들 표시"""
        super().paintEvent(event)
        
        # 리사이즈 핸들 그리기
        painter = QPainter(self)
        painter.setPen(QPen(QColor(150, 150, 150), 1))
        
        # 오른쪽 아래 모서리에 작은 삼각형 그리기
        size = 8
        painter.drawLine(self.width() - size, self.height(), self.width(), self.height() - size)
        painter.drawLine(self.width() - size * 2, self.height(), self.width(), self.height() - size * 2)
        painter.drawLine(self.width() - size * 3, self.height(), self.width(), self.height() - size * 3)
