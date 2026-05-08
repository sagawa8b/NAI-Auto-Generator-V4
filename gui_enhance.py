"""
gui_enhance.py - Image Enhance 기능 Mixin

NAIAutoGeneratorWindow에 mix-in되는 Image Enhancement 관련 메서드들.
이미지 업스케일, 벌크 Enhancement, 해상도 매핑 등을 담당합니다.
"""

import os
import io

from PIL import Image
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QFileDialog, QMessageBox

import naiinfo_getter
from i18n_manager import tr
from logger import get_logger
logger = get_logger()


class EnhanceMixin:
    """NAIAutoGeneratorWindow에 mix-in되는 Image Enhance 관련 메서드.
    
    이 Mixin은 다음을 전제합니다:
    - self.enhance_visible, self.enhance_image, self.enhance_path 등 관련 변수
    - self.enhance_metadata, self.enhance_strength, self.enhance_noise, self.enhance_ratio
    - self.enhance_bulk_mode, self.enhance_image_list 등 벌크 관련 변수
    - self.last_generated_image
    - 관련 UI 위젯들 (labels, buttons, sliders)
    - self.on_click_generate_once(): 생성 메서드
    """

    def toggle_enhance(self):
        """Image Enhance 섹션 토글"""
        self.enhance_visible = not self.enhance_visible

        if hasattr(self, 'enhance_widget'):
            if self.enhance_visible:
                self.enhance_widget.show()
            else:
                self.enhance_widget.hide()

        # 설정 저장
        if hasattr(self, 'settings'):
            self.settings.setValue("enhance_visible", self.enhance_visible)

    def _get_enhanced_resolution(self, orig_width, orig_height):
        """
        NovelAI Enhancement용 해상도 매핑
        원본 해상도에 따라 고정된 향상 해상도를 반환

        Args:
            orig_width (int): 원본 이미지 너비
            orig_height (int): 원본 이미지 높이

        Returns:
            tuple: (enhanced_width, enhanced_height)
        """
        # NovelAI Enhancement 해상도 매핑 테이블
        enhancement_map = {
            # Square resolutions
            (1024, 1024): (1536, 1536),

            # Portrait resolutions
            (832, 1216): (1280, 1856),

            # Landscape resolutions
            (1216, 832): (1856, 1280),
        }

        # 정확히 일치하는 해상도가 있으면 사용
        if (orig_width, orig_height) in enhancement_map:
            enhanced_width, enhanced_height = enhancement_map[(orig_width, orig_height)]
            logger.info(f"Enhancement resolution mapping: {orig_width}x{orig_height} -> {enhanced_width}x{enhanced_height}")
            return enhanced_width, enhanced_height

        # 일치하는 해상도가 없으면 1.5x 폴백 (경고 출력)
        logger.warning(f"No exact enhancement resolution mapping for {orig_width}x{orig_height}, using 1.5x fallback")
        enhanced_width = int(orig_width * 1.5)
        enhanced_height = int(orig_height * 1.5)
        return enhanced_width, enhanced_height

    def load_enhance_image_from_path(self, file_path):
        """Image Enhance 이미지를 경로에서 로드 (드래그 앤 드롭 및 버튼 클릭 모두 지원)"""
        if not file_path:
            return

        try:
            # 이미지 로드
            self.enhance_image = Image.open(file_path)
            self.enhance_path = file_path

            # 메타데이터 읽기 (Enhancement용)
            try:
                nai_dict, error_code = naiinfo_getter.get_naidict_from_file(file_path)

                if error_code == 3 and nai_dict:
                    # 메타데이터 저장
                    self.enhance_metadata = {
                        "prompt": nai_dict.get("prompt", ""),
                        "negative_prompt": nai_dict.get("negative_prompt", "")
                    }
                    self.enhance_metadata.update(nai_dict.get("option", {}))
                    self.enhance_metadata.update(nai_dict.get("etc", {}))

                    # v4_prompt에서 캐릭터 정보 추출
                    if "v4_prompt" in nai_dict.get("etc", {}) and "caption" in nai_dict["etc"]["v4_prompt"]:
                        char_captions = nai_dict["etc"]["v4_prompt"]["caption"].get("char_captions", [])
                        v4_neg_prompt = nai_dict["etc"].get("v4_negative_prompt", {})
                        neg_char_captions = []

                        if "caption" in v4_neg_prompt:
                            neg_char_captions = v4_neg_prompt["caption"].get("char_captions", [])

                        character_prompts = []
                        for i, char in enumerate(char_captions):
                            char_prompt = {
                                "prompt": char.get("char_caption", ""),
                                "negative_prompt": "",
                                "position": None
                            }
                            if "centers" in char and len(char["centers"]) > 0:
                                center = char["centers"][0]
                                char_prompt["position"] = [center.get("x", 0.5), center.get("y", 0.5)]
                            if i < len(neg_char_captions):
                                char_prompt["negative_prompt"] = neg_char_captions[i].get("char_caption", "")
                            character_prompts.append(char_prompt)

                        if character_prompts:
                            self.enhance_metadata["characterPrompts"] = character_prompts
                            use_character_coords = self.enhance_metadata.get("use_character_coords", None)
                            if use_character_coords is None and "v4_prompt" in nai_dict["etc"]:
                                v4_use_coords = nai_dict["etc"]["v4_prompt"].get("use_coords", None)
                                if v4_use_coords is not None:
                                    self.enhance_metadata["use_character_coords"] = v4_use_coords

                    logger.info(f"Enhance image metadata loaded successfully")
                    logger.debug(f"Metadata contains {len(self.enhance_metadata.get('characterPrompts', []))} character prompts")
                else:
                    self.enhance_metadata = None
                    self.enhance_image = None
                    self.enhance_path = None
                    logger.warning(f"No valid NAI metadata found in enhancement image (error_code: {error_code})")
                    QMessageBox.warning(
                        self,
                        tr('enhance.no_metadata_title', 'No NovelAI Metadata'),
                        tr('enhance.no_metadata_message',
                           'The selected image does not contain valid NovelAI metadata.\n\n'
                           'Enhancement requires metadata from the original generation to work correctly.\n\n'
                           'Please select an image generated by NovelAI with embedded metadata.')
                    )
                    return
            except Exception as e:
                logger.error(f"Error reading enhancement image metadata: {e}")
                self.enhance_metadata = None
                self.enhance_image = None
                self.enhance_path = None
                QMessageBox.critical(self, tr('error', 'Error'), f"Failed to read image metadata: {str(e)}")
                return

            # 해상도 검증
            img_width, img_height = self.enhance_image.size
            supported_resolutions = [(1024, 1024), (832, 1216), (1216, 832)]

            if (img_width, img_height) not in supported_resolutions:
                self.enhance_metadata = None
                self.enhance_image = None
                self.enhance_path = None
                supported_list = "\n".join([f"  • {w}x{h}" for w, h in supported_resolutions])
                logger.warning(f"Unsupported resolution for enhancement: {img_width}x{img_height}")
                message = tr('enhance.invalid_resolution_message',
                           'The selected image has a resolution of {width}x{height}, which is not supported for enhancement.\n\n'
                           'NovelAI Enhancement only supports Normal resolution images:\n'
                           '{supported_list}\n\n'
                           'Please select an image with one of the supported resolutions.')
                message = message.format(width=img_width, height=img_height, supported_list=supported_list)
                QMessageBox.warning(self, tr('enhance.invalid_resolution_title', 'Unsupported Resolution'), message)
                return

            # 미리보기 업데이트
            thumbnail = self.enhance_image.copy()
            thumbnail.thumbnail((164, 198), Image.LANCZOS)
            img_byte_arr = io.BytesIO()
            thumbnail.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)

            from PyQt5.QtGui import QPixmap
            pixmap = QPixmap()
            pixmap.loadFromData(img_byte_arr.read())

            self.enhance_image_label.setPixmap(pixmap)
            self.enhance_image_label.setStyleSheet("background-color: rgba(0, 0, 0, 128); border: 2px solid #559977;")
            self.btn_remove_enhance_image.setEnabled(True)
            self.update_enhance_button_state()
            logger.info(f"Enhance image loaded: {file_path}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load image: {str(e)}")
            logger.error(f"Failed to load enhance image: {e}")

    def select_enhance_image(self):
        """Image Enhance 이미지 선택 (파일 다이얼로그)"""
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(
            self, tr('enhance.select_title', 'Select Image to Enhance'), '',
            'Image Files (*.png *.jpg *.jpeg *.webp)')
        if file_path:
            self.load_enhance_image_from_path(file_path)

    def use_current_for_enhance(self):
        """현재 생성된 이미지를 Enhance용으로 사용"""
        if self.last_generated_image:
            try:
                self.enhance_image = self.last_generated_image.copy()
                self.enhance_path = "current_generated"

                try:
                    nai_dict, error_code = naiinfo_getter.get_naidict_from_img(self.last_generated_image)
                except Exception as e:
                    logger.error(f"Error reading current image metadata: {e}")
                    nai_dict = None
                    error_code = 0

                if error_code == 3 and nai_dict:
                    self.enhance_metadata = {
                        "prompt": nai_dict.get("prompt", ""),
                        "negative_prompt": nai_dict.get("negative_prompt", "")
                    }
                    self.enhance_metadata.update(nai_dict.get("option", {}))
                    self.enhance_metadata.update(nai_dict.get("etc", {}))

                    if "v4_prompt" in nai_dict.get("etc", {}) and "caption" in nai_dict["etc"]["v4_prompt"]:
                        char_captions = nai_dict["etc"]["v4_prompt"]["caption"].get("char_captions", [])
                        v4_neg_prompt = nai_dict["etc"].get("v4_negative_prompt", {})
                        neg_char_captions = []
                        if "caption" in v4_neg_prompt:
                            neg_char_captions = v4_neg_prompt["caption"].get("char_captions", [])

                        character_prompts = []
                        for i, char in enumerate(char_captions):
                            char_prompt = {"prompt": char.get("char_caption", ""), "negative_prompt": "", "position": None}
                            if "centers" in char and len(char["centers"]) > 0:
                                center = char["centers"][0]
                                char_prompt["position"] = [center.get("x", 0.5), center.get("y", 0.5)]
                            if i < len(neg_char_captions):
                                char_prompt["negative_prompt"] = neg_char_captions[i].get("char_caption", "")
                            character_prompts.append(char_prompt)

                        if character_prompts:
                            self.enhance_metadata["characterPrompts"] = character_prompts
                            use_character_coords = self.enhance_metadata.get("use_character_coords", None)
                            if use_character_coords is None and "v4_prompt" in nai_dict["etc"]:
                                v4_use_coords = nai_dict["etc"]["v4_prompt"].get("use_coords", None)
                                if v4_use_coords is not None:
                                    self.enhance_metadata["use_character_coords"] = v4_use_coords

                    logger.info("Current image metadata loaded successfully")
                else:
                    self.enhance_metadata = None
                    logger.warning(f"No valid metadata found in current image (error_code: {error_code})")

                # 미리보기 업데이트
                thumbnail = self.enhance_image.copy()
                thumbnail.thumbnail((164, 198), Image.LANCZOS)
                img_byte_arr = io.BytesIO()
                thumbnail.save(img_byte_arr, format='PNG')
                img_byte_arr.seek(0)

                from PyQt5.QtGui import QPixmap
                pixmap = QPixmap()
                pixmap.loadFromData(img_byte_arr.read())

                self.enhance_image_label.setPixmap(pixmap)
                self.btn_remove_enhance_image.setEnabled(True)
                logger.info("Using current generated image for enhance")

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to use current image: {str(e)}")
                logger.error(f"Failed to use current image for enhance: {e}")
        else:
            QMessageBox.information(self, "Info", tr('enhance.no_image_available', 'No generated image available. Please generate an image first.'))

    def remove_enhance_image(self):
        """Image Enhance 이미지 제거"""
        self.enhance_image = None
        self.enhance_path = None
        self.enhance_metadata = None
        self.enhance_image_label.clear()
        self.enhance_image_label.setText(tr('enhance.no_image', 'No Image') + "\n(Drag & Drop)")
        self.enhance_image_label.setStyleSheet("background-color: rgba(0, 0, 0, 128); color: white; border: 2px dashed #666;")
        self.btn_remove_enhance_image.setEnabled(False)
        self.update_enhance_button_state()
        logger.info("Enhance image and metadata removed")

    def on_enhance_strength_changed(self, value):
        """Enhance Strength 슬라이더 값 변경 이벤트"""
        self.enhance_strength = value / 100.0
        self.enhance_strength_value_input.setText(f"{self.enhance_strength:.2f}")
        logger.debug(f"Enhance strength changed: {self.enhance_strength}")

    def on_enhance_noise_changed(self, value):
        """Enhance Noise 슬라이더 값 변경 이벤트"""
        self.enhance_noise = value / 100.0
        self.enhance_noise_value_input.setText(f"{self.enhance_noise:.2f}")
        logger.debug(f"Enhance noise changed: {self.enhance_noise}")

    def on_enhance_strength_input_changed(self):
        """Enhance Strength 입력 필드 값 변경 이벤트"""
        try:
            value = float(self.enhance_strength_value_input.text())
            value = max(0.01, min(0.99, value))
            self.enhance_strength = value
            self.enhance_strength_slider.setValue(int(value * 100))
            self.enhance_strength_value_input.setText(f"{value:.2f}")
            logger.debug(f"Enhance strength input changed: {self.enhance_strength}")
        except ValueError:
            self.enhance_strength_value_input.setText(f"{self.enhance_strength:.2f}")
            logger.warning("Invalid strength input, reverting to current value")

    def on_enhance_noise_input_changed(self):
        """Enhance Noise 입력 필드 값 변경 이벤트"""
        try:
            value = float(self.enhance_noise_value_input.text())
            value = max(0.00, min(0.99, value))
            self.enhance_noise = value
            self.enhance_noise_slider.setValue(int(value * 100))
            self.enhance_noise_value_input.setText(f"{value:.2f}")
            logger.debug(f"Enhance noise input changed: {self.enhance_noise}")
        except ValueError:
            self.enhance_noise_value_input.setText(f"{self.enhance_noise:.2f}")
            logger.warning("Invalid noise input, reverting to current value")

    def on_enhance_ratio_changed(self, button_id):
        """Enhance Ratio 라디오 버튼 변경 이벤트"""
        if button_id == 0:
            self.enhance_ratio = 1.0
            logger.debug("Enhance ratio changed: 1x")
        else:
            self.enhance_ratio = 1.5
            logger.debug("Enhance ratio changed: 1.5x")

    def select_enhance_folder(self):
        """Bulk Enhancement를 위한 폴더 선택"""
        folder_path = QFileDialog.getExistingDirectory(
            self, tr('enhance.select_folder_title', 'Select Folder for Bulk Enhancement'), '')

        if folder_path:
            logger.info(f"Selected folder for bulk enhancement: {folder_path}")
            self.enhance_folder_path = folder_path
            valid_images = []
            supported_extensions = ['.png', '.jpg', '.jpeg', '.webp']

            try:
                for filename in os.listdir(folder_path):
                    file_path = os.path.join(folder_path, filename)
                    if os.path.isfile(file_path):
                        _, ext = os.path.splitext(filename)
                        if ext.lower() in supported_extensions:
                            try:
                                nai_dict, error_code = naiinfo_getter.get_naidict_from_file(file_path)
                                if error_code == 3 and nai_dict:
                                    valid_images.append(file_path)
                                    logger.debug(f"Valid NAI image found: {filename}")
                            except Exception as e:
                                logger.debug(f"Skipping {filename}: {e}")

                if valid_images:
                    self.enhance_image_list = valid_images
                    self.enhance_current_index = 0
                    self.enhance_bulk_mode = True
                    self.enhance_progress_label.setText(tr('enhance.images_found').format(len(valid_images)))
                    self.btn_enhance_create.setEnabled(True)
                    logger.info(f"Found {len(valid_images)} valid NAI images for bulk enhancement")
                    QMessageBox.information(self, tr('enhance.folder_selected'), tr('enhance.images_found_msg').format(len(valid_images)))
                else:
                    self.enhance_bulk_mode = False
                    self.enhance_progress_label.setText(tr('enhance.no_images_found'))
                    QMessageBox.warning(self, tr('enhance.no_images'), tr('enhance.no_images_msg'))
                    logger.warning("No valid NAI images found in selected folder")

            except Exception as e:
                logger.error(f"Error scanning folder: {e}")
                QMessageBox.critical(self, tr('error'), tr('enhance.folder_scan_error').format(str(e)))

    def start_enhance_process(self):
        """Enhancement 프로세스 시작 (단일 또는 벌크)"""
        if self.enhance_bulk_mode and self.enhance_image_list:
            self.enhance_current_index = 0
            self.enhance_bulk_stopped = False
            self.btn_enhance_stop.show()
            self.btn_enhance_stop.setEnabled(True)
            self.btn_enhance_create.setEnabled(False)
            self.process_next_enhance_image()
        elif self.enhance_image:
            logger.info("Starting single enhance process")
            self.on_click_generate_once()
        else:
            QMessageBox.warning(self, tr('enhance.no_image'), tr('enhance.no_image_loaded'))

    def process_next_enhance_image(self):
        """벌크 Enhancement에서 다음 이미지 처리"""
        if not self.enhance_bulk_mode or not self.enhance_image_list:
            return

        if self.enhance_bulk_stopped:
            logger.info("Bulk enhancement stopped by user")
            processed_count = self.enhance_current_index
            self.enhance_progress_label.setText(tr('enhance.stopped').format(processed_count, len(self.enhance_image_list)))
            self._reset_enhance_bulk_state()
            return

        if self.enhance_current_index < len(self.enhance_image_list):
            current_path = self.enhance_image_list[self.enhance_current_index]
            logger.info(f"Processing image {self.enhance_current_index + 1}/{len(self.enhance_image_list)}: {current_path}")
            self.enhance_progress_label.setText(
                tr('enhance.processing').format(self.enhance_current_index + 1, len(self.enhance_image_list)))
            self.load_enhance_image_from_path(current_path)
            QTimer.singleShot(100, self.on_click_generate_once)
        else:
            logger.info("Bulk enhancement completed")
            self.enhance_progress_label.setText(tr('enhance.completed').format(len(self.enhance_image_list)))
            QMessageBox.information(self, tr('enhance.bulk_complete'), tr('enhance.bulk_complete_msg').format(len(self.enhance_image_list)))
            self._reset_enhance_bulk_state()

    def update_enhance_button_state(self):
        """Enhance 버튼 상태 업데이트"""
        if self.enhance_image or (self.enhance_bulk_mode and self.enhance_image_list):
            self.btn_enhance_create.setEnabled(True)
        else:
            self.btn_enhance_create.setEnabled(False)

    def stop_enhance_process(self):
        """Enhancement 프로세스 중단"""
        if self.enhance_bulk_mode:
            logger.info("Stopping bulk enhancement process...")
            self.enhance_bulk_stopped = True
            self.btn_enhance_stop.setEnabled(False)

    def _reset_enhance_bulk_state(self):
        """벌크 Enhancement 상태 초기화"""
        self.enhance_bulk_mode = False
        self.enhance_image_list = []
        self.enhance_current_index = 0
        self.enhance_bulk_stopped = False
        self.btn_enhance_stop.hide()
        self.btn_enhance_stop.setEnabled(False)
        self.update_enhance_button_state()
