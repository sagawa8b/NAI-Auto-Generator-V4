from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, 
                             QLabel, QLineEdit, QPushButton, QPlainTextEdit, 
                             QTextBrowser, QComboBox, QSplitter, QCheckBox, 
                             QRadioButton, QButtonGroup, QSizePolicy, QMessageBox, 
                             QFileDialog, QApplication, QCompleter, QFrame)
from PyQt5.QtCore import Qt, pyqtSignal, QSettings, QSize
from PyQt5.QtGui import QPixmap, QImage, QPainter, QPen, QColor, QMouseEvent, QBrush, QPalette
from consts import RESOLUTION_FAMILIY
from completer import CompletionTextEdit
from character_prompts_ui import CharacterPromptsContainer
import random
import os
from logger import get_logger

from i18n_manager import tr

logger = get_logger()

def init_advanced_prompt_group(parent):
    """고급 반응형 프롬프트 그룹 초기화"""
    prompt_group = QGroupBox(tr('ui.prompt_group', 'Prompt'))
    prompt_layout = QVBoxLayout()
    prompt_group.setLayout(prompt_layout)

    # 스플리터 추가
    splitter = QSplitter(Qt.Vertical)
    
    # 프롬프트 위젯
    prompt_widget = QWidget()
    prompt_widget_layout = QVBoxLayout(prompt_widget)
    prompt_widget_layout.setContentsMargins(0, 0, 0, 0)
    
    prompt_label = QLabel(tr('ui.prompt'))
    parent.dict_ui_settings["prompt"] = CompletionTextEdit()
    parent.dict_ui_settings["prompt"].setPlaceholderText(tr('ui.prompt_placeholder'))
    
    prompt_widget_layout.addWidget(prompt_label)
    prompt_widget_layout.addWidget(parent.dict_ui_settings["prompt"])
    
    # 네거티브 프롬프트 위젯
    neg_prompt_widget = QWidget()
    neg_prompt_widget_layout = QVBoxLayout(neg_prompt_widget)
    neg_prompt_widget_layout.setContentsMargins(0, 0, 0, 0)
    
    neg_prompt_label = QLabel(tr('ui.negative_prompt'))
    parent.dict_ui_settings["negative_prompt"] = CompletionTextEdit()
    parent.dict_ui_settings["negative_prompt"].setPlaceholderText("이미지에서 제외할 내용을 입력하세요...")
    
    neg_prompt_widget_layout.addWidget(neg_prompt_label)
    neg_prompt_widget_layout.addWidget(parent.dict_ui_settings["negative_prompt"])
    
    # 스플리터에 위젯 추가
    splitter.addWidget(prompt_widget)
    splitter.addWidget(neg_prompt_widget)
    
    # 초기 크기 비율 설정 (60:40)
    splitter.setSizes([600, 400])
    
    # 스플리터 핸들 스타일 설정
    splitter.setHandleWidth(8)
    splitter.setStyleSheet("QSplitter::handle { background-color: #cccccc; }")
    
    # 레이아웃에 스플리터 추가
    prompt_layout.addWidget(splitter)
    
    # 스플리터 저장 (나중에 접근 가능하도록)
    parent.prompt_splitter = splitter
    
    return prompt_group


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

    # 8. Character Reference 그룹 추가 (캐릭터 프롬프트 그룹 다음에)
    char_ref_group = init_character_reference_group(parent)
    left_layout.addWidget(char_ref_group)

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
    horizontal_container = QHBoxLayout()
    
    # 이미지 옵션 그룹
    img_option_group = QGroupBox("Image Options")
    img_option_layout = QVBoxLayout()
    img_option_group.setLayout(img_option_layout)

    # 이미지 크기 설정
    hbox_size = QHBoxLayout()
    combo_resolution = QComboBox()
    parent.combo_resolution = combo_resolution

    # 그룹 제목과 해상도 추가
    # Normal 그룹
    combo_resolution.addItem("--- Normal ---")
    combo_resolution.setItemData(0, 0, Qt.UserRole - 1)  # 선택 불가능하게 설정
    
    for resolution in RESOLUTION_FAMILIY[0]:
        combo_resolution.addItem(resolution)
    
    # Large 그룹
    combo_resolution.addItem("--- Large ---")
    large_idx = combo_resolution.count() - 1
    combo_resolution.setItemData(large_idx, 0, Qt.UserRole - 1)  # 선택 불가능하게 설정
    
    for resolution in RESOLUTION_FAMILIY[1]:
        combo_resolution.addItem(resolution)
    
    # Wallpaper 그룹
    combo_resolution.addItem("--- Wallpaper ---")
    wallpaper_idx = combo_resolution.count() - 1
    combo_resolution.setItemData(wallpaper_idx, 0, Qt.UserRole - 1)  # 선택 불가능하게 설정
    
    for resolution in RESOLUTION_FAMILIY[2]:
        combo_resolution.addItem(resolution)
    
    # Low Resolution 그룹
    combo_resolution.addItem("--- Low Resolution ---")
    low_res_idx = combo_resolution.count() - 1
    combo_resolution.setItemData(low_res_idx, 0, Qt.UserRole - 1)  # 선택 불가능하게 설정
    
    for resolution in RESOLUTION_FAMILIY[3]:
        combo_resolution.addItem(resolution)
    
    combo_resolution.addItem("Custom (직접 입력)")
    
    # Square (1024x1024) 항목을 기본으로 선택
    hd_index = -1
    for i in range(combo_resolution.count()):
        if "Square (1024x1024)" in combo_resolution.itemText(i):
            hd_index = i
            break
    
    if hd_index >= 0:
        combo_resolution.setCurrentIndex(hd_index)
    
    hbox_size.addWidget(QLabel("Size:"))
    hbox_size.addWidget(combo_resolution, 1)

    # 직접 입력 필드
    hbox_custom_size = QHBoxLayout()
    hbox_custom_size.addWidget(QLabel("W:"))
    parent.dict_ui_settings["width"] = QLineEdit()
    parent.dict_ui_settings["width"].setAlignment(Qt.AlignRight)
    hbox_custom_size.addWidget(parent.dict_ui_settings["width"])

    hbox_custom_size.addWidget(QLabel("H:"))
    parent.dict_ui_settings["height"] = QLineEdit()
    parent.dict_ui_settings["height"].setAlignment(Qt.AlignRight)
    hbox_custom_size.addWidget(parent.dict_ui_settings["height"])

    # 체크박스 설정 불러오는 부분
    checkbox_random_resolution = QCheckBox("Random")
    checkbox_random_resolution.stateChanged.connect(
        parent.on_random_resolution_checked)

    # 먼저 객체를 속성에 할당
    parent.checkbox_random_resolution = checkbox_random_resolution

    # 명시적으로 bool 타입으로 변환
    random_checked = parent.settings.value("image_random_checkbox", False, type=bool)
    parent.checkbox_random_resolution.setChecked(random_checked)

    # 레이아웃에 체크박스 추가 - 이 줄이 누락되었습니다
    hbox_custom_size.addWidget(parent.checkbox_random_resolution)
    

    img_option_layout.addLayout(hbox_size)
    img_option_layout.addLayout(hbox_custom_size)

    # 샘플러 설정
    hbox_sampler = QHBoxLayout()
    hbox_sampler.addWidget(QLabel("Sampler:"))
    parent.dict_ui_settings["sampler"] = QComboBox()

    # UI 표시용 샘플러 이름과 API 값 매핑 - 딕셔너리를 클래스 변수로 저장
    parent.sampler_mapping = {
        "Euler": "k_euler",
        "Euler Ancestral": "k_euler_ancestral",
        "DPM++ 2S Ancestral": "k_dpmpp_2s_ancestral",
        "DPM++ 2M": "k_dpmpp_2m",
        "DPM++ 2M SDE": "k_dpmpp_sde", 
        "DPM++ SDE": "k_dpmpp_sde"  # 추가된 샘플러
    }

    # UI에 표시할 이름만 추가
    parent.dict_ui_settings["sampler"].addItems(list(parent.sampler_mapping.keys()))

    # 샘플러 선택 시 이벤트 핸들러 추가
    parent.dict_ui_settings["sampler"].currentTextChanged.connect(lambda text: on_sampler_changed(parent, text))

    hbox_sampler.addWidget(parent.dict_ui_settings["sampler"])
    img_option_layout.addLayout(hbox_sampler)

    # 샘플러 선택 이벤트 핸들러 함수
    def on_sampler_changed(parent, ui_name):
        # UI 이름에서 API 값으로 변환
        api_value = parent.sampler_mapping.get(ui_name, ui_name)
        # 디버깅용 로그
        logger.debug(f"Sampler changed: UI={ui_name}, API={api_value}")

    # 스텝 설정
    hbox_steps = QHBoxLayout()
    hbox_steps.addWidget(QLabel("Steps:"))
    parent.dict_ui_settings["steps"] = QLineEdit()
    parent.dict_ui_settings["steps"].setAlignment(Qt.AlignRight)
    hbox_steps.addWidget(parent.dict_ui_settings["steps"])
    img_option_layout.addLayout(hbox_steps)

    # 시드 설정
    hbox_seed = QHBoxLayout()
    hbox_seed.addWidget(QLabel("Seed:"))
    parent.dict_ui_settings["seed"] = QLineEdit()
    parent.dict_ui_settings["seed"].setAlignment(Qt.AlignRight)
    hbox_seed.addWidget(parent.dict_ui_settings["seed"])
    parent.dict_ui_settings["seed_fix_checkbox"] = QCheckBox("Fix")
    hbox_seed.addWidget(parent.dict_ui_settings["seed_fix_checkbox"])
    seed_random_button = QPushButton("Random")
    seed_random_button.clicked.connect(
        lambda: parent.dict_ui_settings["seed"].setText(str(random.randint(0, 2**32-1))))
    hbox_seed.addWidget(seed_random_button)
    img_option_layout.addLayout(hbox_seed)

    # 레이아웃 여백과 간격 조정
    img_option_layout.setContentsMargins(5, 5, 5, 5)
    img_option_layout.setSpacing(3)

    # 고급 설정 그룹 초기화
    advanced_group = init_advanced_group(parent)
    
    
    # ========== Character Reference 그룹 추가 ==========
    char_ref_group = QGroupBox("Character Reference (V4.5 전용)")
    char_ref_layout = QVBoxLayout()
    char_ref_group.setLayout(char_ref_layout)
    
    # 이미지 표시 영역
    parent.char_ref_image_label = QLabel("캐릭터 이미지를 업로드하세요")
    parent.char_ref_image_label.setAlignment(Qt.AlignCenter)
    parent.char_ref_image_label.setMinimumHeight(120)
    parent.char_ref_image_label.setMaximumHeight(200)
    parent.char_ref_image_label.setStyleSheet("""
        QLabel {
            background-color: #2a2a2a;
            border: 2px dashed #666;
            border-radius: 5px;
            color: #999;
            font-size: 12px;
        }
    """)
    char_ref_layout.addWidget(parent.char_ref_image_label)
    
    # 버튼 영역
    char_ref_buttons = QHBoxLayout()
    
    parent.char_ref_load_btn = QPushButton("📁 이미지 불러오기")
    parent.char_ref_load_btn.clicked.connect(lambda: load_character_reference(parent))
    char_ref_buttons.addWidget(parent.char_ref_load_btn)
    
    parent.char_ref_remove_btn = QPushButton("🗑️ 제거")
    parent.char_ref_remove_btn.clicked.connect(lambda: remove_character_reference(parent))
    parent.char_ref_remove_btn.setEnabled(False)  # 초기에는 비활성화
    char_ref_buttons.addWidget(parent.char_ref_remove_btn)
    
    char_ref_layout.addLayout(char_ref_buttons)
    
    # Style Aware 체크박스
    parent.char_ref_style_aware = QCheckBox("Style Aware (캐릭터 스타일 정보 유지)")
    parent.char_ref_style_aware.setChecked(True)
    parent.char_ref_style_aware.setToolTip(
        "캐릭터의 특징적인 스타일 정보를 자동으로 전달합니다.\n"
        "눈이나 머리카락 같은 세부 특징이 더 정확하게 재현됩니다."
    )
    char_ref_layout.addWidget(parent.char_ref_style_aware)
    
    # 정보 라벨
    info_label = QLabel("💡 팁: 전신 샷, 중립 포즈, 단순 배경의 이미지가 가장 좋습니다")
    info_label.setWordWrap(True)
    info_label.setStyleSheet("color: #888; font-size: 10px; padding: 5px;")
    char_ref_layout.addWidget(info_label)
    
    # 경고 라벨
    warning_label = QLabel("⚠️ V4.5 모델에서만 작동 | Vibe Transfer와 동시 사용 불가")
    warning_label.setStyleSheet("color: orange; font-size: 10px; padding: 5px;")
    char_ref_layout.addWidget(warning_label)
    
    # 레이아웃에 추가
    left_layout.addWidget(char_ref_group)
    char_ref_group.setVisible(False)  # 초기에는 숨김
    parent.char_ref_group = char_ref_group  # 참조 저장 (중요!)
    
    # Character Reference 데이터 저장용 변수 초기화
    parent.char_ref_image_data = None
    parent.char_ref_image_path = None
    
    logger.info("Character Reference UI 생성 완료")
    # ========== Character Reference 그룹 추가 끝 ==========    


    # Generate 버튼 그룹
    generate_group = QGroupBox("Generate")
    generate_layout = QVBoxLayout()
    generate_group.setLayout(generate_layout)
       
    
    # 생성 버튼들 추가
    parent.button_generate_once = QPushButton("1회 생성")
    parent.button_generate_once.clicked.connect(parent.on_click_generate_once)
    generate_layout.addWidget(parent.button_generate_once)
    
    parent.button_generate_sett = QPushButton("세팅별 연속 생성")
    parent.button_generate_sett.clicked.connect(parent.on_click_generate_sett)
    generate_layout.addWidget(parent.button_generate_sett)
    
    parent.button_generate_auto = QPushButton("연속 생성 (Auto)")
    parent.button_generate_auto.clicked.connect(parent.on_click_generate_auto)
    generate_layout.addWidget(parent.button_generate_auto)
    
    # 작은 구분선 추가
    separator = QFrame()
    separator.setFrameShape(QFrame.HLine)
    separator.setFrameShadow(QFrame.Sunken)
    generate_layout.addWidget(separator)

    # 토글 버튼 추가
    parent.button_expand = QPushButton("◀▶" if parent.is_expand else "▶◀")
    parent.button_expand.setToolTip("결과 패널 확장/축소")
    parent.button_expand.clicked.connect(parent.on_click_expand)
    parent.button_expand.setStyleSheet("""
        QPushButton {
            background-color: #f0f0f0;
            border: 1px solid #ccc;
            border-radius: 4px;
            padding: 4px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #e0e0e0;
        }
        QPushButton:pressed {
            background-color: #d0d0d0;
        }
    """)
    generate_layout.addWidget(parent.button_expand)

    # 이미지 크기 리셋 버튼 추가
    parent.button_reset_size = QPushButton(tr('ui.reset_image_size'))
    parent.button_reset_size.setToolTip(tr('ui.reset_image_size_tooltip'))
    parent.button_reset_size.clicked.connect(lambda: parent.image_result.reset_to_default_size())
    parent.button_reset_size.setStyleSheet("""
        QPushButton {
            background-color: #f0f0f0;
            border: 1px solid #ccc;
            border-radius: 4px;
            padding: 4px;
        }
        QPushButton:hover {
            background-color: #e0e0e0;
        }
        QPushButton:pressed {
            background-color: #d0d0d0;
        }
    """)
    generate_layout.addWidget(parent.button_reset_size)

    # 공백 추가 (버튼 아래 여백)
    generate_layout.addStretch(1)

    # 레이아웃 여백과 간격 조정
    generate_layout.setContentsMargins(5, 5, 5, 5)
    generate_layout.setSpacing(3)

    # 좌우 균형 조정
    img_option_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
    advanced_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
    generate_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

    # 폴더 열기 그룹 생성
    folder_group = QGroupBox("Folder Open")
    folder_layout = QVBoxLayout()
    folder_group.setLayout(folder_layout)
    folder_layout.setContentsMargins(5, 5, 5, 5)
    folder_layout.setSpacing(3)

    # 결과 폴더 버튼
    results_folder_btn = QPushButton(tr('folders.results'))
    results_folder_btn.clicked.connect(lambda: parent.on_click_open_folder("path_results"))
    folder_layout.addWidget(results_folder_btn)

    # 와일드카드 폴더 버튼
    wildcards_folder_btn = QPushButton(tr('folders.wildcards'))
    wildcards_folder_btn.clicked.connect(lambda: parent.on_click_open_folder("path_wildcards"))
    folder_layout.addWidget(wildcards_folder_btn)

    # 세팅 파일 폴더 버튼
    settings_folder_btn = QPushButton(tr('folders.settings'))
    settings_folder_btn.clicked.connect(lambda: parent.on_click_open_folder("path_settings"))
    folder_layout.addWidget(settings_folder_btn)

    # 여백 추가
    folder_layout.addStretch(1)

    # 폴더 그룹 크기 정책 설정
    folder_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
    
    # 위젯들을 수평 레이아웃에 원하는 순서로 추가
    horizontal_container.addWidget(img_option_group, 4)  # Image Options (비율 4)
    horizontal_container.addWidget(advanced_group, 4)    # Advanced Settings (비율 4)
    horizontal_container.addWidget(folder_group, 2)      # Folder Open (비율 2)
    horizontal_container.addWidget(generate_group, 3)    # Generate (비율 3)
    
    
    # 수평 레이아웃을 메인 레이아웃에 추가
    left_layout.addLayout(horizontal_container)
        

    # 1.4: 이미지 옵션 (img2img, reference) 그룹 - 숨김 처리하되 객체는 생성
    image_options_group = QGroupBox("Image References")
    image_options_layout = QHBoxLayout()
    image_options_group.setLayout(image_options_layout)
    parent.image_options_layout = image_options_layout

    # Character Reference 그룹 생성
    char_ref_group = QGroupBox("Character Reference (V4.5)")
    char_ref_layout = QVBoxLayout()
    char_ref_group.setLayout(char_ref_layout)
    
    # 이미지 표시 영역
    parent.char_ref_image_label = QLabel("캐릭터 이미지를 업로드하세요")
    parent.char_ref_image_label.setAlignment(Qt.AlignCenter)
    parent.char_ref_image_label.setMinimumHeight(100)
    parent.char_ref_image_label.setStyleSheet("""
        QLabel {
            background-color: rgba(0, 0, 0, 50);
            border: 2px dashed #666;
            border-radius: 5px;
            color: #999;
        }
    """)
    char_ref_layout.addWidget(parent.char_ref_image_label)
    
    # 버튼 영역
    char_ref_buttons = QHBoxLayout()
    
    char_ref_load_btn = QPushButton("이미지 불러오기")
    char_ref_load_btn.clicked.connect(lambda: load_character_reference(parent))
    char_ref_buttons.addWidget(char_ref_load_btn)
    
    char_ref_remove_btn = QPushButton("제거")
    char_ref_remove_btn.clicked.connect(lambda: remove_character_reference(parent))
    char_ref_buttons.addWidget(char_ref_remove_btn)
    
    char_ref_layout.addLayout(char_ref_buttons)
    
    # Style Aware 체크박스
    parent.char_ref_style_aware = QCheckBox("Style Aware (캐릭터 스타일 유지)")
    parent.char_ref_style_aware.setChecked(True)
    char_ref_layout.addWidget(parent.char_ref_style_aware)
    
    # 정보 라벨
    info_label = QLabel("💡 V4.5 모델 전용 | 전신 샷 권장")
    info_label.setStyleSheet("color: #888; font-size: 10px;")
    char_ref_layout.addWidget(info_label)
    
    # 레이아웃에 추가 (left_layout에 추가해야 함)
    left_layout.addWidget(char_ref_group)
    char_ref_group.setVisible(False)  # 초기에는 숨김
    parent.char_ref_group = char_ref_group  # 참조 저장
    
    # Character Reference 데이터 저장용 변수
    parent.char_ref_image_data = None
    parent.char_ref_image_path = None


    # img2img 옵션
    parent.i2i_settings_group = ImageToImageWidget("img2img", parent)
    image_options_layout.addWidget(parent.i2i_settings_group)

    # Reference Image 옵션 (기존 - Vibe Transfer)
    parent.vibe_settings_group = ImageToImageWidget("vibe", parent)
    image_options_layout.addWidget(parent.vibe_settings_group)

    # Character Reference 옵션 (새로 추가)
    parent.char_ref_settings_group = CharacterReferenceWidget(parent)
    image_options_layout.addWidget(parent.char_ref_settings_group)

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

    # Character Reference 전용 설정 추가
    parent.char_ref_settings = QGroupBox("Character Reference Settings")
    char_ref_settings_layout = QVBoxLayout()
    parent.char_ref_settings.setLayout(char_ref_settings_layout)
    
    # Style Aware 체크박스
    parent.dict_ui_settings["character_reference_style_aware"] = QCheckBox("Style Aware")
    parent.dict_ui_settings["character_reference_style_aware"].setChecked(True)
    parent.dict_ui_settings["character_reference_style_aware"].setToolTip(
        "캐릭터 관련 스타일 정보를 자동으로 전달합니다. 캐릭터를 더 쉽게 인식할 수 있게 합니다."
    )
    char_ref_settings_layout.addWidget(parent.dict_ui_settings["character_reference_style_aware"])
    
    # V4.5 모델 전용 경고 라벨
    warning_label = QLabel("⚠️ Character Reference는 V4.5 모델에서만 사용 가능합니다")
    warning_label.setStyleSheet("color: orange; font-size: 10px;")
    char_ref_settings_layout.addWidget(warning_label)
    
    image_options_layout.addWidget(parent.char_ref_settings)
    parent.char_ref_settings.setVisible(False)


    # 그룹 표시/숨김 제어
    left_layout.addWidget(image_options_group)
    image_options_group.setVisible(False)  # 초기에는 숨김


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
    result_image_group = QGroupBox("결과 이미지 (Result Image)")
    result_image_layout = QVBoxLayout()
    result_image_group.setLayout(result_image_layout)
    
    # 이미지 보기
    parent.image_result = ResizableImageWidget()
    result_image_layout.addWidget(parent.image_result)
    
    # 크기 변경 시그널 연결
    parent.image_result.size_changed.connect(
        lambda size: adjust_group_size(result_image_group, size))
    
    # 이미지 버튼 영역
    hbox_image_buttons = QHBoxLayout()
    
    # 이미지 저장 버튼
    button_save_image = QPushButton("이미지 저장")
    button_save_image.clicked.connect(lambda: parent.image_result.save_image())
    hbox_image_buttons.addWidget(button_save_image)
    
    # 기본 크기로 복원 버튼 추가
    button_reset_size = QPushButton("이미지 창을 기본 크기로 복원")
    button_reset_size.setToolTip("이미지 창을 기본 크기(512x512)로 되돌립니다")
    button_reset_size.clicked.connect(lambda: parent.image_result.reset_to_default_size())
    hbox_image_buttons.addWidget(button_reset_size)
    
    result_image_layout.addLayout(hbox_image_buttons)
    
    right_layout.addWidget(result_image_group)
    
    # 저장된 크기 기준으로 초기 그룹 크기 설정
    initial_width = parent.image_result.width() + 30  # 여백 고려
    initial_height = parent.image_result.height() + 80  # 버튼 영역과 여백 고려
    result_image_group.setMinimumSize(initial_width, initial_height)


    # 2.2: 결과 프롬프트 그룹
    result_prompt_group = QGroupBox("결과 프롬프트 (Result Prompt)")
    result_prompt_layout = QVBoxLayout()
    result_prompt_group.setLayout(result_prompt_layout)

    parent.prompt_result = QTextBrowser()
    result_prompt_layout.addWidget(parent.prompt_result)

    right_layout.addWidget(result_prompt_group)

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
    parent.session_status_indicator.setToolTip("세션 상태")
    parent.statusBar().addPermanentWidget(parent.session_status_indicator)

# 기본 프롬프트 그룹 수정
def init_responsive_prompt_group(parent):
    """반응형 프롬프트 그룹 초기화"""
    prompt_group = QGroupBox("Prompt")
    prompt_layout = QVBoxLayout()
    prompt_group.setLayout(prompt_layout)

    # 프롬프트 입력 영역
    prompt_label = QLabel("프롬프트(Prompt):")
    parent.dict_ui_settings["prompt"] = CompletionTextEdit()
    parent.dict_ui_settings["prompt"].setPlaceholderText("이미지에 포함할 내용을 입력하세요...")
    
    # 프롬프트 에디터에 대한 최소 높이 설정 (화면 크기에 따라 조정됨)
    parent.dict_ui_settings["prompt"].setMinimumHeight(100)
    
    # 네거티브 프롬프트 입력 영역
    neg_prompt_label = QLabel("네거티브 프롬프트(Negative Prompt):")
    parent.dict_ui_settings["negative_prompt"] = CompletionTextEdit()
    parent.dict_ui_settings["negative_prompt"].setPlaceholderText("이미지에서 제외할 내용을 입력하세요...")
    
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


def init_character_reference_group(parent):
    """Character Reference UI 그룹 초기화"""
    from PyQt5.QtWidgets import (QGroupBox, QVBoxLayout, QHBoxLayout, QPushButton, 
                                QLabel, QCheckBox, QSizePolicy, QFrame)
    from PyQt5.QtCore import Qt
    from PyQt5.QtGui import QPixmap
    from i18n_manager import tr
    
    # Character Reference 그룹 박스
    char_ref_group = QGroupBox("Character Reference (V4.5 전용)")
    char_ref_group.setVisible(False)  # 초기에는 숨김
    char_ref_layout = QVBoxLayout()
    char_ref_layout.setContentsMargins(8, 8, 8, 8)
    char_ref_layout.setSpacing(6)
    char_ref_group.setLayout(char_ref_layout)
    
    # 안내 메시지
    info_label = QLabel("📷 캐릭터의 일관된 외형을 위한 레퍼런스 이미지를 설정하세요.")
    info_label.setStyleSheet("color: #666666; font-size: 11px; padding: 4px;")
    info_label.setWordWrap(True)
    char_ref_layout.addWidget(info_label)
    
    # 이미지 로드 영역
    image_container = QFrame()
    image_container.setFrameStyle(QFrame.StyledPanel)
    image_container.setStyleSheet("QFrame { background-color: #f8f8f8; border: 2px dashed #cccccc; }")
    image_container.setMinimumHeight(120)
    image_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    
    image_layout = QVBoxLayout()
    image_layout.setContentsMargins(10, 10, 10, 10)
    image_container.setLayout(image_layout)
    
    # 이미지 미리보기 라벨
    char_ref_preview = QLabel("이미지를 선택해주세요")
    char_ref_preview.setAlignment(Qt.AlignCenter)
    char_ref_preview.setStyleSheet("color: #999999; font-size: 12px;")
    char_ref_preview.setMinimumSize(100, 80)
    char_ref_preview.setScaledContents(True)
    image_layout.addWidget(char_ref_preview)
    
    char_ref_layout.addWidget(image_container)
    
    # 버튼 영역
    button_layout = QHBoxLayout()
    button_layout.setSpacing(8)
    
    # 이미지 로드 버튼
    load_image_btn = QPushButton("📁 이미지 선택")
    load_image_btn.setStyleSheet("""
        QPushButton {
            background-color: #4CAF50;
            color: white;
            border: none;
            padding: 8px 16px;
            font-weight: bold;
            border-radius: 4px;
        }
        QPushButton:hover {
            background-color: #45a049;
        }
        QPushButton:pressed {
            background-color: #3d8b40;
        }
    """)
    
    # 이미지 제거 버튼
    remove_image_btn = QPushButton("🗑️ 제거")
    remove_image_btn.setStyleSheet("""
        QPushButton {
            background-color: #f44336;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
        }
        QPushButton:hover {
            background-color: #da190b;
        }
        QPushButton:pressed {
            background-color: #be1e0c;
        }
    """)
    remove_image_btn.setEnabled(False)  # 초기에는 비활성화
    
    button_layout.addWidget(load_image_btn)
    button_layout.addWidget(remove_image_btn)
    button_layout.addStretch()
    
    char_ref_layout.addLayout(button_layout)
    
    # Style Aware 옵션
    style_aware_layout = QHBoxLayout()
    style_aware_checkbox = QCheckBox("Style Aware (캐릭터 고유 스타일 반영)")
    style_aware_checkbox.setChecked(True)  # 기본값 True
    style_aware_checkbox.setStyleSheet("color: #333333; font-size: 11px;")
    
    style_aware_layout.addWidget(style_aware_checkbox)
    style_aware_layout.addStretch()
    char_ref_layout.addLayout(style_aware_layout)
    
    # 주의사항 라벨
    warning_label = QLabel("⚠️ Vibe Transfer와 동시 사용 불가 | V4.5 모델 전용")
    warning_label.setStyleSheet("color: #ff6b35; font-size: 10px; font-weight: bold;")
    warning_label.setWordWrap(True)
    char_ref_layout.addWidget(warning_label)
    
    # 부모 객체에 참조 저장
    parent.char_ref_group = char_ref_group
    parent.char_ref_preview = char_ref_preview
    parent.char_ref_load_btn = load_image_btn
    parent.char_ref_remove_btn = remove_image_btn
    parent.char_ref_style_aware = style_aware_checkbox
    parent.char_ref_image_data = None  # base64 이미지 데이터 저장용
    
    # 이벤트 핸들러 연결을 위한 헬퍼 함수들 정의
    def load_character_reference():
        """Character Reference 이미지 로드"""
        from PyQt5.QtWidgets import QFileDialog, QMessageBox
        from PyQt5.QtGui import QPixmap
        import base64
        
        file_path, _ = QFileDialog.getOpenFileName(
            parent,
            "Character Reference 이미지 선택",
            "",
            "Image Files (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        
        if file_path:
            try:
                # 이미지 파일을 base64로 인코딩
                with open(file_path, "rb") as image_file:
                    encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                
                # 미리보기 업데이트
                pixmap = QPixmap(file_path)
                if not pixmap.isNull():
                    scaled_pixmap = pixmap.scaled(100, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    char_ref_preview.setPixmap(scaled_pixmap)
                    char_ref_preview.setText("")
                    
                    # 데이터 저장
                    parent.char_ref_image_data = encoded_string
                    
                    # 버튼 상태 업데이트
                    remove_image_btn.setEnabled(True)
                    
                    # 이미지 컨테이너 스타일 변경
                    image_container.setStyleSheet("QFrame { background-color: #e8f5e8; border: 2px solid #4CAF50; }")
                    
                else:
                    QMessageBox.warning(parent, "오류", "유효하지 않은 이미지 파일입니다.")
                    
            except Exception as e:
                QMessageBox.critical(parent, "오류", f"이미지 로드 실패:\n{str(e)}")
    
    def remove_character_reference():
        """Character Reference 이미지 제거"""
        # 미리보기 초기화
        char_ref_preview.clear()
        char_ref_preview.setText("이미지를 선택해주세요")
        char_ref_preview.setStyleSheet("color: #999999; font-size: 12px;")
        
        # 데이터 초기화
        parent.char_ref_image_data = None
        
        # 버튼 상태 업데이트
        remove_image_btn.setEnabled(False)
        
        # 이미지 컨테이너 스타일 초기화
        image_container.setStyleSheet("QFrame { background-color: #f8f8f8; border: 2px dashed #cccccc; }")
    
    # 이벤트 연결
    load_image_btn.clicked.connect(load_character_reference)
    remove_image_btn.clicked.connect(remove_character_reference)
    
    return char_ref_group



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
    
    ok_button = QPushButton("확인")
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
    if text == "Custom (직접 입력)":
        return

    try:
        res_text = text.split("(")[1].split(")")[0]
        width, height = res_text.split("x")

        parent.dict_ui_settings["width"].setText(width)
        parent.dict_ui_settings["height"].setText(height)
    except Exception as e:
        print(e)

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
    parent.dict_ui_settings["variety_plus"].setToolTip("이미지 초기 생성 단계에서 CFG를 스킵하여 더 다양한 결과 생성")
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
        self.state_label = QLabel("로그인 필요")
        self.state_label.setStyleSheet("color:red;")
        layout.addWidget(self.state_label)
        self.setLayout(layout)

    def set_logged_in(self, is_logged_in):
        if is_logged_in:
            self.state_label.setText("로그인 됨")
            self.state_label.setStyleSheet("color:green;")
        else:
            self.state_label.setText("로그인 필요")
            self.state_label.setStyleSheet("color:red;")


class ImageToImageWidget(QGroupBox):
    is_active_changed = pyqtSignal(bool)

    def __init__(self, mode, parent):
        title = "이미지 to 이미지" if mode == "img2img" else "레퍼런스 이미지"
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
        self.image_label = QLabel("업로드된 이미지 없음")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.image_label.setStyleSheet("background-color: rgba(0, 0, 0, 128);")
        layout.addWidget(self.image_label)

        # 버튼 부분
        button_layout = QHBoxLayout()

        # 왼쪽 버튼 부분
        left_button_layout = QHBoxLayout()

        self.upload_button = QPushButton("불러오기")
        self.upload_button.clicked.connect(
            lambda: self.parent.show_file_dialog(self.mode))
        left_button_layout.addWidget(self.upload_button)

        self.open_folder_button = QPushButton("폴더")
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
            self.image_label.setText("업로드된 이미지 없음")
            self.image_label.setPixmap(QPixmap())

        self.is_active_changed.emit(bool(src))

    def on_click_removebutton(self):
        self.src = None
        self.mask = None
        self.is_maskmode = False
        if hasattr(self, 'mask_checkbox'):
            self.mask_checkbox.setChecked(False)
        self.image_label.setText("업로드된 이미지 없음")
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
        # 기본값 선택
        parent.dict_ui_settings["sampler"].setCurrentIndex(0)
    

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
        self.image_label.setText("결과 이미지가 없습니다")
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
        print(f"이미지 크기 기본값으로 재설정: {self.DEFAULT_WIDTH}x{self.DEFAULT_HEIGHT}")
    
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
            print(e)
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

class CharacterReferenceWidget(QGroupBox):
    """Character Reference 전용 위젯"""
    is_active_changed = pyqtSignal(bool)
    
    def __init__(self, parent):
        super().__init__("Character Reference (V4.5)")
        self.parent = parent
        self.src = None
        self.image_data = None
        
        self.setMinimumHeight(150)
        self.setMaximumWidth(300)  # 너비 제한
        self.init_ui()
        
        logger.debug("CharacterReferenceWidget 생성됨")
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(5)
        
        # 이미지 표시 라벨
        self.image_label = QLabel("캐릭터 이미지 없음")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.image_label.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 0, 0, 128);
                border: 2px dashed #666;
                border-radius: 5px;
                color: #999;
                font-size: 11px;
            }
        """)
        self.image_label.setMinimumHeight(100)
        layout.addWidget(self.image_label)
        
        # 버튼 레이아웃
        button_layout = QHBoxLayout()
        button_layout.setSpacing(5)
        
        # 업로드 버튼
        self.upload_button = QPushButton("📁 불러오기")
        self.upload_button.clicked.connect(self.load_character_image)
        button_layout.addWidget(self.upload_button)
        
        # 제거 버튼
        self.remove_button = QPushButton("🗑️ 제거")
        self.remove_button.clicked.connect(self.remove_image)
        self.remove_button.setEnabled(False)
        button_layout.addWidget(self.remove_button)
        
        layout.addLayout(button_layout)
        
        # 정보 라벨
        info_label = QLabel("💡 전신, 중립 포즈, 단순 배경 권장")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("font-size: 10px; color: #888;")
        layout.addWidget(info_label)
        
        self.setLayout(layout)
    
    def load_character_image(self):
        """캐릭터 이미지 불러오기"""
        logger.debug("Character Reference 이미지 선택 대화상자 열기")
        
        filename, _ = QFileDialog.getOpenFileName(
            self, "Character Reference 이미지 선택", "", 
            "이미지 파일 (*.png *.jpg *.jpeg *.webp)"
        )
        
        if filename:
            logger.info(f"Character Reference 이미지 선택됨: {filename}")
            self.set_image(filename)
    
    def set_image(self, src):
        """이미지 설정"""
        self.src = src
        
        if src and os.path.exists(src):
            try:
                # 이미지 로드 및 표시
                pixmap = QPixmap(src)
                if not pixmap.isNull():
                    scaled_pixmap = pixmap.scaledToHeight(100, Qt.SmoothTransformation)
                    self.image_label.setPixmap(scaled_pixmap)
                    
                    # Base64 인코딩
                    with open(src, 'rb') as f:
                        self.image_data = base64.b64encode(f.read()).decode('utf-8')
                    
                    self.remove_button.setEnabled(True)
                    
                    # Vibe Transfer 충돌 체크
                    if hasattr(self.parent, 'vibe_settings_group') and self.parent.vibe_settings_group.src:
                        reply = QMessageBox.question(
                            self, "경고", 
                            "Character Reference와 Vibe Transfer는 동시 사용 불가합니다.\n"
                            "Character Reference를 사용하시겠습니까?",
                            QMessageBox.Yes | QMessageBox.No
                        )
                        if reply == QMessageBox.Yes:
                            self.parent.vibe_settings_group.on_click_removebutton()
                        else:
                            self.remove_image()
                            return
                    
                    logger.info("Character Reference 이미지 설정 완료")
                    self.is_active_changed.emit(True)
                else:
                    logger.error("이미지 로드 실패")
                    QMessageBox.warning(self, "오류", "이미지를 로드할 수 없습니다.")
                    
            except Exception as e:
                logger.error(f"Character Reference 이미지 설정 오류: {e}")
                QMessageBox.critical(self, "오류", f"이미지 처리 실패: {str(e)}")
        else:
            self.remove_image()
    
    def remove_image(self):
        """이미지 제거"""
        logger.debug("Character Reference 이미지 제거")
        
        self.src = None
        self.image_data = None
        self.image_label.setText("캐릭터 이미지 없음")
        self.image_label.setPixmap(QPixmap())
        self.remove_button.setEnabled(False)
        
        self.is_active_changed.emit(False)
    
    def get_image_data(self):
        """Base64 인코딩된 이미지 데이터 반환"""
        return self.image_data

class CharacterReferenceWidget(QGroupBox):
    """Character Reference 전용 위젯"""
    is_active_changed = pyqtSignal(bool)
    
    def __init__(self, parent):
        super().__init__("Character Reference")
        self.parent = parent
        self.src = None
        self.image_data = None
        
        self.setMinimumHeight(150)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 이미지 표시 라벨
        self.image_label = QLabel("Character Reference 이미지 없음")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.image_label.setStyleSheet("background-color: rgba(0, 0, 0, 128);")
        self.image_label.setAcceptDrops(True)
        layout.addWidget(self.image_label)
        
        # 버튼 레이아웃
        button_layout = QHBoxLayout()
        
        # 업로드 버튼
        self.upload_button = QPushButton("캐릭터 이미지 불러오기")
        self.upload_button.clicked.connect(self.load_character_image)
        button_layout.addWidget(self.upload_button)
        
        # 제거 버튼
        self.remove_button = QPushButton("제거")
        self.remove_button.clicked.connect(self.remove_image)
        button_layout.addWidget(self.remove_button)
        
        layout.addLayout(button_layout)
        
        # 정보 라벨
        info_label = QLabel("💡 전신 샷, 중립 포즈, 단순 배경의 이미지가 가장 좋습니다")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("font-size: 10px; color: gray;")
        layout.addWidget(info_label)
        
        self.setLayout(layout)
    
    def load_character_image(self):
        """캐릭터 이미지 불러오기"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Character Reference 이미지 선택", "", 
            "이미지 파일 (*.png *.jpg *.jpeg *.webp)"
        )
        
        if filename:
            self.set_image(filename)
    
    def set_image(self, src):
        """이미지 설정"""
        self.src = src
        
        if src:
            # 이미지 로드 및 표시
            pixmap = QPixmap(src)
            scaled_pixmap = pixmap.scaledToHeight(128, Qt.SmoothTransformation)
            self.image_label.setPixmap(scaled_pixmap)
            
            # Base64 인코딩
            import base64
            with open(src, 'rb') as f:
                self.image_data = base64.b64encode(f.read()).decode('utf-8')
            
            # 부모 위젯에 표시 상태 변경 알림
            self.parent.char_ref_settings.setVisible(True)
            self.parent.image_options_group.setVisible(True)
            
            # Vibe Transfer와 충돌 체크
            if self.parent.vibe_settings_group.src:
                reply = QMessageBox.question(
                    self, "경고", 
                    "Character Reference와 Vibe Transfer는 동시에 사용할 수 없습니다.\n"
                    "Character Reference를 사용하시겠습니까?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    self.parent.vibe_settings_group.on_click_removebutton()
                else:
                    self.remove_image()
                    return
        else:
            self.image_label.setText("Character Reference 이미지 없음")
            self.image_label.setPixmap(QPixmap())
            self.image_data = None
        
        self.is_active_changed.emit(bool(src))
    
    def remove_image(self):
        """이미지 제거"""
        self.src = None
        self.image_data = None
        self.image_label.setText("Character Reference 이미지 없음")
        self.image_label.setPixmap(QPixmap())
        self.parent.char_ref_settings.setVisible(False)
        
        # 다른 이미지 참조가 없으면 전체 그룹 숨김
        if not self.parent.i2i_settings_group.src and not self.parent.vibe_settings_group.src:
            self.parent.image_options_group.setVisible(False)
        
        self.is_active_changed.emit(False)
    
    def get_image_data(self):
        """Base64 인코딩된 이미지 데이터 반환"""
        return self.image_data

def load_character_reference(parent):
    """Character Reference 이미지 로드"""
    from PyQt5.QtWidgets import QFileDialog, QMessageBox
    from PyQt5.QtGui import QPixmap
    from PyQt5.QtCore import Qt
    import base64
    import os
    
    logger.info("Character Reference 이미지 선택 대화상자 열기")
    
    filename, _ = QFileDialog.getOpenFileName(
        parent, "Character Reference 이미지 선택", "", 
        "이미지 파일 (*.png *.jpg *.jpeg *.webp)"
    )
    
    if filename and os.path.exists(filename):
        try:
            # 이미지 표시
            pixmap = QPixmap(filename)
            if not pixmap.isNull():
                # 이미지 크기 조정하여 표시
                scaled = pixmap.scaled(
                    parent.char_ref_image_label.width() - 10,
                    parent.char_ref_image_label.height() - 10,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                parent.char_ref_image_label.setPixmap(scaled)
                
                # Base64 인코딩
                with open(filename, 'rb') as f:
                    parent.char_ref_image_data = base64.b64encode(f.read()).decode('utf-8')
                parent.char_ref_image_path = filename
                
                # 버튼 상태 업데이트
                parent.char_ref_remove_btn.setEnabled(True)
                
                logger.info(f"Character Reference 이미지 로드 성공: {filename}")
                
                # Vibe Transfer와 충돌 체크
                if hasattr(parent, 'vibe_settings_group') and parent.vibe_settings_group.src:
                    reply = QMessageBox.question(
                        parent, "경고", 
                        "Character Reference와 Vibe Transfer는 동시 사용이 불가능합니다.\n"
                        "Character Reference를 사용하시겠습니까?",
                        QMessageBox.Yes | QMessageBox.No
                    )
                    if reply == QMessageBox.Yes:
                        parent.vibe_settings_group.on_click_removebutton()
                        logger.info("Vibe Transfer 비활성화됨")
                    else:
                        # Character Reference 취소
                        remove_character_reference(parent)
                        return
            else:
                raise Exception("이미지를 읽을 수 없습니다")
                
        except Exception as e:
            logger.error(f"Character Reference 이미지 로드 실패: {e}")
            QMessageBox.critical(parent, "오류", f"이미지 로드 실패:\n{str(e)}")

def remove_character_reference(parent):
    """Character Reference 이미지 제거"""
    from PyQt5.QtGui import QPixmap
    
    parent.char_ref_image_label.setText("캐릭터 이미지를 업로드하세요")
    parent.char_ref_image_label.setPixmap(QPixmap())
    parent.char_ref_image_data = None
    parent.char_ref_image_path = None
    parent.char_ref_remove_btn.setEnabled(False)
    
    logger.info("Character Reference 이미지 제거됨")