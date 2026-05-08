"""
gui_image_handlers.py - 이미지 입력 관련 Mixin

NAIAutoGeneratorWindow에 mix-in되는 Image-to-Image 및 Character Reference 관련 메서드들.
이미지 선택, 제거, 슬라이더 핸들링, 인페인팅 마스크 등을 담당합니다.
"""

import io

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QDialog

from i18n_manager import tr
from logger import get_logger
logger = get_logger()


class ImageHandlersMixin:
    """NAIAutoGeneratorWindow에 mix-in되는 img2img + Character Reference 관련 메서드.
    
    이 Mixin은 다음을 전제합니다:
    - self.character_reference_visible, self.character_reference_image 등 관련 변수
    - self.img2img_visible, self.img2img_image 등 관련 변수
    - self.inpaint_mode, self.inpaint_mask
    - 관련 UI 위젯들 (labels, buttons, sliders)
    """

    def toggle_character_reference(self):
        """Character Reference 섹션 토글"""
        self.character_reference_visible = not self.character_reference_visible

        if hasattr(self, 'character_reference_widget'):
            if self.character_reference_visible:
                self.character_reference_widget.show()
            else:
                self.character_reference_widget.hide()

    def toggle_img2img(self):
        """Image to Image 섹션 토글"""
        self.img2img_visible = not self.img2img_visible

        if hasattr(self, 'img2img_widget'):
            if self.img2img_visible:
                self.img2img_widget.show()
            else:
                self.img2img_widget.hide()

    def select_character_reference_image(self):
        """Character Reference 이미지 선택"""
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(
            self, 
            'Select Character Reference Image', 
            '', 
            'Image Files (*.png *.jpg *.jpeg *.webp)'
        )
        
        if file_path:
            try:
                # 이미지 로드
                from PIL import Image
                self.character_reference_image = Image.open(file_path)
                self.character_reference_path = file_path
                
                # 미리보기 업데이트
                thumbnail = self.character_reference_image.copy()
                thumbnail.thumbnail((164, 198), Image.LANCZOS)
                
                # PIL Image를 QPixmap으로 변환
                img_byte_arr = io.BytesIO()
                thumbnail.save(img_byte_arr, format='PNG')
                img_byte_arr.seek(0)
                
                from PyQt5.QtGui import QPixmap
                pixmap = QPixmap()
                pixmap.loadFromData(img_byte_arr.read())
                
                self.character_image_label.setPixmap(pixmap)
                self.btn_remove_character_image.setEnabled(True)
                
                logger.info(f"Character Reference image loaded: {file_path}")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load image: {str(e)}")
                logger.error(f"Failed to load character reference image: {e}")

    def remove_character_reference_image(self):
        """Character Reference 이미지 제거"""
        self.character_reference_image = None
        self.character_reference_path = None
        self.character_image_label.clear()
        self.character_image_label.setText("No Image")
        self.btn_remove_character_image.setEnabled(False)
        logger.info("Character Reference image removed")

    def on_style_aware_changed(self, state):
        """Style Aware 체크박스 상태 변경"""
        self.character_reference_style_aware = (state == Qt.Checked)
        logger.debug(f"Style Aware changed: {self.character_reference_style_aware}")

    def on_fidelity_changed(self, value):
        """Fidelity 슬라이더 값 변경 이벤트"""
        # 슬라이더 값(0-20)을 실제 값(0.00-1.00)으로 변환
        self.character_reference_fidelity = value * 0.05
        self.character_fidelity_value_label.setText(f"{self.character_reference_fidelity:.2f}")
        logger.debug(f"Fidelity changed: {self.character_reference_fidelity}")

    def load_img2img_image_from_path(self, file_path):
        """Image to Image 이미지를 경로에서 로드 (드래그 앤 드롭 및 버튼 클릭 모두 지원)"""
        if not file_path:
            return

        try:
            # 이미지 로드
            from PIL import Image
            self.img2img_image = Image.open(file_path)
            self.img2img_path = file_path

            # 미리보기 업데이트
            thumbnail = self.img2img_image.copy()
            thumbnail.thumbnail((164, 198), Image.LANCZOS)

            # PIL Image를 QPixmap으로 변환
            img_byte_arr = io.BytesIO()
            thumbnail.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)

            from PyQt5.QtGui import QPixmap
            pixmap = QPixmap()
            pixmap.loadFromData(img_byte_arr.read())

            self.img2img_image_label.setPixmap(pixmap)
            self.img2img_image_label.setStyleSheet("background-color: rgba(0, 0, 0, 128); border: 2px solid #559977;")
            self.btn_remove_img2img_image.setEnabled(True)

            # Paint Mask 버튼 활성화 (inpaint 모드가 활성화된 경우)
            if self.inpaint_mode:
                self.btn_paint_mask.setEnabled(True)

            logger.info(f"Image to Image source loaded: {file_path}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load image: {str(e)}")
            logger.error(f"Failed to load img2img image: {e}")

    def select_img2img_image(self):
        """Image to Image 이미지 선택 (파일 다이얼로그)"""
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(
            self,
            'Select Image to Image Source',
            '',
            'Image Files (*.png *.jpg *.jpeg *.webp)'
        )

        if file_path:
            self.load_img2img_image_from_path(file_path)

    def remove_img2img_image(self):
        """Image to Image 이미지 제거"""
        self.img2img_image = None
        self.img2img_path = None
        self.img2img_image_label.clear()
        self.img2img_image_label.setText("No Image\n(Drag & Drop)")
        self.img2img_image_label.setStyleSheet("background-color: rgba(0, 0, 0, 128); color: white; border: 2px dashed #666;")
        self.btn_remove_img2img_image.setEnabled(False)

        # Paint Mask 버튼 비활성화 및 마스크 초기화
        self.btn_paint_mask.setEnabled(False)
        self.inpaint_mask = None
        self.mask_status_label.setText("No mask painted")
        self.mask_status_label.setStyleSheet("font-size: 9pt; color: #888; font-style: italic;")

        logger.info("Image to Image source removed")

    def on_img2img_strength_slider_changed(self, value):
        """Image to Image Strength 슬라이더 값 변경 이벤트"""
        # 슬라이더 값(0-100)을 실제 값(0.00-1.00)으로 변환
        self.img2img_strength = value / 100.0
        # 입력 필드도 업데이트
        self.img2img_strength_input.setText(f"{self.img2img_strength:.2f}")
        logger.debug(f"img2img strength changed (slider): {self.img2img_strength}")

    def on_img2img_strength_input_changed(self):
        """Image to Image Strength 입력 필드 값 변경 이벤트"""
        try:
            value = float(self.img2img_strength_input.text())
            # 0.0~1.0 범위로 제한
            value = max(0.0, min(1.0, value))
            self.img2img_strength = value
            self.img2img_strength_input.setText(f"{value:.2f}")
            # 슬라이더도 업데이트
            self.img2img_strength_slider.setValue(int(value * 100))
            logger.debug(f"img2img strength changed (input): {self.img2img_strength}")
        except ValueError:
            # 잘못된 입력일 경우 기본값으로 복원
            self.img2img_strength_input.setText(f"{self.img2img_strength:.2f}")
            logger.warning("Invalid img2img strength input")

    def on_img2img_noise_slider_changed(self, value):
        """Image to Image Noise 슬라이더 값 변경 이벤트"""
        # 슬라이더 값(0-100)을 실제 값(0.00-1.00)으로 변환
        self.img2img_noise = value / 100.0
        # 입력 필드도 업데이트
        self.img2img_noise_input.setText(f"{self.img2img_noise:.2f}")
        logger.debug(f"img2img noise changed (slider): {self.img2img_noise}")

    def on_img2img_noise_input_changed(self):
        """Image to Image Noise 입력 필드 값 변경 이벤트"""
        try:
            value = float(self.img2img_noise_input.text())
            # 0.0~1.0 범위로 제한
            value = max(0.0, min(1.0, value))
            self.img2img_noise = value
            self.img2img_noise_input.setText(f"{value:.2f}")
            # 슬라이더도 업데이트
            self.img2img_noise_slider.setValue(int(value * 100))
            logger.debug(f"img2img noise changed (input): {self.img2img_noise}")
        except ValueError:
            # 잘못된 입력일 경우 기본값으로 복원
            self.img2img_noise_input.setText(f"{self.img2img_noise:.2f}")
            logger.warning("Invalid img2img noise input")

    def on_inpaint_mode_changed(self, state):
        """Inpainting 모드 체크박스 변경 이벤트"""
        self.inpaint_mode = (state == Qt.Checked)

        # Paint Mask 버튼 활성화/비활성화
        if self.inpaint_mode and self.img2img_image is not None:
            self.btn_paint_mask.setEnabled(True)
        else:
            self.btn_paint_mask.setEnabled(False)

        # 모드 변경 시 마스크 초기화 여부 확인
        if not self.inpaint_mode and self.inpaint_mask is not None:
            self.inpaint_mask = None
            self.mask_status_label.setText("No mask painted")
            self.mask_status_label.setStyleSheet("font-size: 9pt; color: #888; font-style: italic;")

        logger.info(f"Inpainting mode: {self.inpaint_mode}")

    def open_mask_paint_dialog(self):
        """마스크 페인팅 다이얼로그 열기"""
        if self.img2img_image is None:
            QMessageBox.warning(
                self,
                tr('dialogs.warning'),
                "Please select an image first before painting mask."
            )
            return

        from gui_dialog import MaskPaintDialog

        # 다이얼로그 열기 (기존 마스크가 있으면 전달)
        dialog = MaskPaintDialog(self, self.img2img_image, existing_mask=self.inpaint_mask)
        if dialog.exec_() == QDialog.Accepted:
            # 마스크 가져오기
            self.inpaint_mask = dialog.get_mask()

            if self.inpaint_mask:
                # 마스크 상태 업데이트
                self.mask_status_label.setText("✓ Mask painted successfully")
                self.mask_status_label.setStyleSheet("font-size: 9pt; color: #559977; font-weight: bold;")
                logger.info("Inpainting mask painted successfully")
            else:
                self.mask_status_label.setText("No mask painted")
                self.mask_status_label.setStyleSheet("font-size: 9pt; color: #888; font-style: italic;")
                logger.warning("Mask painting cancelled or empty")
