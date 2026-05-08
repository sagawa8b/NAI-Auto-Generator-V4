"""
gui_generation.py - 이미지 생성 로직 Mixin

NAIAutoGeneratorWindow에 mix-in되는 이미지 생성 관련 메서드들.
데이터 준비, 프롬프트 전처리, 생성 실행, 결과 처리, 와일드카드 적용 등을 담당합니다.
"""

import os
import io
import random
import base64

import numpy as np

from PIL import Image
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QDialog, QApplication

from i18n_manager import tr
from gui_utils import pickedit_lessthan_str, create_folder_if_not_exists, get_filename_only, inject_imagetag, MAX_COUNT_FOR_WHILE, validate_generation_params
from gui_workers import GenerateThread, AutoGenerateThread
from gui_dialog import GenerateDialog
from consts import COLOR, DEFAULT_PATH
from logger import get_logger
logger = get_logger()


class GenerationMixin:
    """NAIAutoGeneratorWindow에 mix-in되는 이미지 생성 관련 메서드.
    
    이 Mixin은 다음을 전제합니다:
    - self.nai: NAIGenerator 인스턴스
    - self.session_manager: NAISessionManager 인스턴스
    - self.settings: QSettings 인스턴스
    - self.dict_ui_settings: UI 위젯 딕셔너리
    - self.wcapplier: WildcardApplier 인스턴스
    - self.character_prompts_container: CharacterPromptsContainer 인스턴스
    - 관련 UI 위젯들 (buttons, labels)
    """

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

            # Character Reference 파라미터 초기화 (stale parameter 방지)
            data["reference_image_multiple"] = None
            data["reference_information_extracted_multiple"] = None
            data["reference_strength_multiple"] = None
            data["reference_fidelity_multiple"] = None

            # Image Enhance 설정 (최우선 처리)
            if hasattr(self, 'enhance_image') and self.enhance_image and self.enhance_path:
                try:
                    logger.info("Enhance mode activated")

                    # Enhancement는 반드시 메타데이터가 있어야 함
                    if not hasattr(self, 'enhance_metadata') or not self.enhance_metadata:
                        logger.error("Enhancement mode requires metadata but none found - aborting")
                        raise ValueError("Enhancement image metadata is required but not available")

                    # Enhancement 이미지 메타데이터 설정 사용
                    if self.enhance_metadata:
                        logger.info("Applying settings from enhancement image metadata")

                        # 프롬프트 설정 (메타데이터에서)
                        if "prompt" in self.enhance_metadata:
                            data["prompt"] = self.enhance_metadata["prompt"]
                            logger.debug(f"Using metadata prompt: {data['prompt'][:100]}...")

                        if "negative_prompt" in self.enhance_metadata:
                            data["negative_prompt"] = self.enhance_metadata["negative_prompt"]
                            logger.debug(f"Using metadata negative_prompt: {data['negative_prompt'][:100]}...")

                        # 기타 설정 (메타데이터에서)
                        metadata_params = ["scale", "sampler", "steps", "sm", "sm_dyn"]
                        for param in metadata_params:
                            if param in self.enhance_metadata:
                                data[param] = self.enhance_metadata[param]
                                logger.debug(f"Using metadata {param}: {data[param]}")

                    # 이미지를 업스케일
                    from danbooru_tagger import convert_src_to_imagedata

                    # 원본 이미지 크기 가져오기
                    orig_width, orig_height = self.enhance_image.size

                    # NovelAI Enhancement 해상도 매핑 사용 (ratio 무시)
                    new_width, new_height = self._get_enhanced_resolution(orig_width, orig_height)

                    # 이미지 업스케일
                    upscaled_image = self.enhance_image.resize((new_width, new_height), Image.LANCZOS)

                    # 업스케일된 이미지를 임시 저장하여 base64로 변환
                    img_byte_arr = io.BytesIO()
                    upscaled_image.save(img_byte_arr, format='PNG')
                    img_byte_arr.seek(0)
                    imgdata_enhance = base64.b64encode(img_byte_arr.read()).decode('utf-8')

                    if imgdata_enhance:
                        data["image"] = imgdata_enhance
                        data['autoSmea'] = False

                        # Strength와 Noise 직접 사용 (GUI 설정 사용)
                        data["strength"] = self.enhance_strength
                        data["noise"] = self.enhance_noise

                        # 업스케일된 크기로 width/height 설정
                        data["width"] = new_width
                        data["height"] = new_height

                        # extra_noise_seed 설정 (seed - 1)
                        data["extra_noise_seed"] = data["seed"] - 1

                        # skip_cfg_above_sigma 조정
                        # 기본값에서 약간 증가 (19 -> 약 29 정도)
                        base_sigma = data.get("skip_cfg_above_sigma", 19) if data.get("skip_cfg_above_sigma") else 19
                        data["skip_cfg_above_sigma"] = base_sigma * 1.5

                        # 프롬프트에 업스케일 아티팩트 방지 추가
                        if data.get("prompt"):
                            data["prompt"] = data["prompt"] + ", -2::upscaled, blurry::,"

                        # img2img 관련 추가 파라미터
                        data["legacy"] = False
                        data["color_correct"] = False

                        logger.info(f"Enhance enabled: strength={self.enhance_strength}, noise={self.enhance_noise}, size={orig_width}x{orig_height} -> {new_width}x{new_height}")
                    else:
                        logger.error("Failed to encode enhance image")
                        self.remove_enhance_image()
                except Exception as e:
                    logger.error(f"Enhance 설정 중 오류: {e}")

            # img2img 설정 (새 위젯 사용) - Enhance가 없을 때만
            elif hasattr(self, 'img2img_image') and self.img2img_image and self.img2img_path:
                try:
                    # 이미지를 base64로 인코딩
                    from danbooru_tagger import convert_src_to_imagedata
                    imgdata_i2i = convert_src_to_imagedata(self.img2img_path)
                    if imgdata_i2i:
                        data["image"] = imgdata_i2i
                        # 만약 i2i가 켜져있다면 autoSmea 설정을 반드시 꺼야함
                        data['autoSmea'] = False

                        # strength와 noise 파라미터 설정
                        data["strength"] = self.img2img_strength
                        data["noise"] = self.img2img_noise

                        # Inpainting 마스크 설정
                        if self.inpaint_mode and self.inpaint_mask:
                            try:
                                # Grayscale 마스크 처리 (inpaint dialog에서 이미 grayscale 'L' mode로 생성됨)
                                # NovelAI API는 grayscale mask를 기대: white=inpaint, black=preserve

                                # Handle grayscale 'L' mode mask (primary case)
                                if self.inpaint_mask.mode == 'L':
                                    # Mask is already grayscale, just ensure it's binary
                                    mask_array = np.array(self.inpaint_mask)

                                    # Check for non-binary values BEFORE thresholding
                                    unique_values_before = np.unique(mask_array)
                                    logger.info(f"🔍 Mask unique values BEFORE threshold: {unique_values_before[:10]}... (total: {len(unique_values_before)})")

                                    # Apply strict binary threshold (should already be binary from grid painting)
                                    mask_binary = np.where(mask_array > 127, 255, 0).astype(np.uint8)

                                    # Verify mask is now perfectly binary
                                    unique_values_after = np.unique(mask_binary)
                                    logger.info(f"🔍 Mask unique values AFTER threshold: {unique_values_after}")

                                    if len(unique_values_after) > 2 or not all(v in [0, 255] for v in unique_values_after):
                                        logger.error(f"⚠️ WARNING: Mask is not perfectly binary! Values: {unique_values_after}")
                                    else:
                                        logger.info("✓ Mask is perfectly binary (only 0 and 255)")

                                    # Convert to grayscale image (already 'L' mode, just ensure clean)
                                    mask_grayscale = Image.fromarray(mask_binary).convert('L')
                                    logger.info("✓ Processed grayscale mask to binary (grid-based painting)")
                                else:
                                    # Fallback: convert any other format to grayscale and threshold
                                    mask_array = np.array(self.inpaint_mask.convert('L'))
                                    mask_binary = np.where(mask_array > 127, 255, 0).astype(np.uint8)
                                    mask_grayscale = Image.fromarray(mask_binary).convert('L')
                                    logger.warning(f"⚠ Mask in unexpected format ({self.inpaint_mask.mode}), converting to binary grayscale")

                                # Mask is now guaranteed to be pure binary (0 or 255 only)
                                logger.info("✓ Pure binary mask ready for API (0=preserve, 255=inpaint)")

                                # Send mask at FULL RESOLUTION (matching DCP-arca implementation)
                                # Note: Grid-based painting already ensures perfect 8×8 grid alignment
                                # No downsampling needed - DCP-arca's working implementation sends full-res masks
                                mask_final = mask_grayscale
                                logger.info(f"✓ Mask at full resolution: {mask_final.size}, mode: {mask_final.mode}")

                                # Encode mask to base64 PNG
                                mask_byte_arr = io.BytesIO()
                                mask_final.save(mask_byte_arr, format='PNG')
                                mask_byte_arr.seek(0)
                                mask_base64 = base64.b64encode(mask_byte_arr.read()).decode('utf-8')

                                data["mask"] = mask_base64
                                logger.info(f"✓ Inpainting mask enabled - mask size: {len(mask_base64)} bytes")
                                logger.info(f"✓ Mask dimensions: {mask_final.size}, mode: {mask_final.mode}")
                            except Exception as e:
                                logger.error(f"✗ Failed to encode mask: {e}")
                                import traceback
                                traceback.print_exc()
                        elif self.inpaint_mode and not self.inpaint_mask:
                            logger.warning("⚠ Inpaint mode is ON but no mask painted!")
                        elif not self.inpaint_mode and self.inpaint_mask:
                            logger.info("ℹ Mask exists but inpaint mode is OFF - ignoring mask")

                        logger.info(f"img2img enabled: strength={self.img2img_strength}, noise={self.img2img_noise}, inpaint={self.inpaint_mode}")
                    else:
                        logger.error("Failed to encode img2img image")
                        self.remove_img2img_image()
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
            data["deliberate_euler_ancestral_bug"] = False  # WebUI uses corrected sampler (changed from True)
            data["controlnet_strength"] = 1  # WebUI default for img2img
            data["dynamic_thresholding"] = False
            data["sm_dyn"] = False
            data["quality_toggle"] = True
            
            # autoSmea 값 선택적 적용 (샘플러가 ddim_v3일 때 비활성화)
            if data.get('sampler') == 'ddim_v3':
                data['autoSmea'] = False
            elif "autoSmea" not in data and hasattr(self, 'dict_ui_settings') and 'autoSmea' in self.dict_ui_settings:
                data['autoSmea'] = bool(self.dict_ui_settings["autoSmea"].isChecked())
                        
            # 캐릭터 프롬프트 데이터 가져오기
            # Enhancement 모드일 때는 Enhancement 이미지의 메타데이터 사용
            if hasattr(self, 'enhance_image') and self.enhance_image and hasattr(self, 'enhance_metadata') and self.enhance_metadata:
                try:
                    # Enhancement 이미지의 메타데이터에서 캐릭터 프롬프트 가져오기
                    if "characterPrompts" in self.enhance_metadata:
                        logger.info("Using character prompts from enhancement image metadata")
                        data["characterPrompts"] = self.enhance_metadata["characterPrompts"]

                        # use_character_coords도 메타데이터에서 가져오기
                        if "use_character_coords" in self.enhance_metadata:
                            data["use_character_coords"] = self.enhance_metadata["use_character_coords"]
                            logger.debug(f"🔍 Enhancement metadata use_character_coords: {data['use_character_coords']}")
                        else:
                            # 메타데이터에 없으면 위치 정보가 있는지 확인
                            has_positions = any(
                                char.get("position") is not None
                                for char in data["characterPrompts"]
                            )
                            data["use_character_coords"] = has_positions
                            logger.debug(f"🔍 Inferred use_character_coords from positions: {has_positions}")
                    else:
                        # 캐릭터 프롬프트가 없으면 빈 배열
                        data["characterPrompts"] = []
                        data["use_character_coords"] = False
                        logger.info("No character prompts in enhancement image metadata")
                except Exception as e:
                    logger.error(f"Enhancement 메타데이터 캐릭터 프롬프트 처리 중 오류: {e}")
                    data["characterPrompts"] = []
            # 일반 모드일 때는 GUI에서 가져오기
            elif hasattr(self, 'character_prompts_container'):
                if hasattr(self, 'wcapplier'):
                    self.wcapplier.create_index_snapshot()
                try:
                    char_data = self.character_prompts_container.get_data()
                    logger.debug(f"🔍 캐릭터 컨테이너 원본 데이터: {char_data}")

                    data["characterPrompts"] = []

                    # use_character_coords 설정
                    use_ai_positions = char_data.get("use_ai_positions", True)
                    data["use_character_coords"] = not use_ai_positions

                    logger.debug(f"🔍 use_ai_positions: {use_ai_positions}")
                    logger.debug(f"🔍 use_character_coords: {data['use_character_coords']}")

                    if "characters" in char_data:
                        for i, char in enumerate(char_data["characters"]):
                            # 프롬프트 전처리
                            raw_prompt = char.get("prompt", "")
                            raw_negative_prompt = char.get("negative_prompt", "") if char.get("negative_prompt") else ""

                            prompt = self._preprocess_character_prompt(raw_prompt)
                            negative_prompt = self._preprocess_character_prompt(raw_negative_prompt)

                            char_prompt = {
                                "prompt": prompt,
                                "negative_prompt": negative_prompt
                            }

                            # 위치 정보 처리 (한 번만)
                            if not use_ai_positions and char.get("position") and isinstance(char["position"], (list, tuple)) and len(char["position"]) == 2:
                                char_prompt["position"] = [float(char["position"][0]), float(char["position"][1])]
                                logger.debug(f"캐릭터 {i+1} 커스텀 위치: {char_prompt['position']}")
                            else:
                                logger.debug(f"캐릭터 {i+1}: AI's choice 모드 - 위치 정보 미포함")

                            data["characterPrompts"].append(char_prompt)

                    # 인덱스 진행
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
            
            # Character Reference 데이터 추가            
            if self.character_reference_image is not None:
                # 이미지를 권장 해상도로 조정
                processed_image = self._prepare_character_reference_image(self.character_reference_image)
                
                # 이미지를 Base64로 인코딩
                img_byte_arr = io.BytesIO()
                processed_image.save(img_byte_arr, format='PNG')
                img_byte_arr.seek(0)
                image_base64 = base64.b64encode(img_byte_arr.read()).decode('utf-8')
                
                data["reference_image_multiple"] = [image_base64]
                data["reference_information_extracted_multiple"] = [1 if self.character_reference_style_aware else 0]
                data["reference_strength_multiple"] = [1]
                data["reference_fidelity_multiple"] = [self.character_reference_fidelity]  # Fidelity 추가
                
                logger.debug(f"Character Reference added - Style Aware: {self.character_reference_style_aware}, Fidelity: {self.character_reference_fidelity}")
                logger.debug(f"Processed image size: {processed_image.size}")
            else:
                # Character Reference 이미지가 없을 때는 초기화된 None 값 유지
                # (이미 lines 2083-2086에서 None으로 초기화됨)
                logger.debug("Character Reference not applied - parameters remain None")

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
                "deliberate_euler_ancestral_bug": False,  # Match WebUI behavior
                "controlnet_strength": 1,  # Match WebUI default
                "quality_toggle": True
            }
        
    def _prepare_character_reference_image(self, image):
        """
        Character Reference 이미지를 NovelAI 권장 해상도로 조정
        권장 해상도: 1024x1536 (세로), 1472x1472 (정사각형), 1536x1024 (가로)
        """
        from PIL import Image
        
        # 원본 이미지 크기
        orig_width, orig_height = image.size
        aspect_ratio = orig_width / orig_height
        
        # 종횡비에 따라 가장 적합한 해상도 선택
        if aspect_ratio < 0.9:  # 세로가 긴 이미지
            target_size = (1024, 1536)
        elif aspect_ratio > 1.1:  # 가로가 긴 이미지
            target_size = (1536, 1024)
        else:  # 정사각형에 가까운 이미지
            target_size = (1472, 1472)
        
        # 새 이미지 생성 (검은색 배경)
        new_image = Image.new('RGB', target_size, (0, 0, 0))
        
        # 종횡비를 유지하면서 리사이즈
        image_copy = image.copy()
        if image_copy.mode == 'RGBA':
            # RGBA 이미지는 RGB로 변환 (투명도는 검은색으로 처리)
            background = Image.new('RGB', image_copy.size, (0, 0, 0))
            background.paste(image_copy, mask=image_copy.split()[3])
            image_copy = background
        elif image_copy.mode != 'RGB':
            image_copy = image_copy.convert('RGB')
        
        # 타겟 크기에 맞게 리사이즈 (종횡비 유지)
        image_copy.thumbnail(target_size, Image.LANCZOS)
        
        # 중앙에 배치
        paste_x = (target_size[0] - image_copy.width) // 2
        paste_y = (target_size[1] - image_copy.height) // 2
        new_image.paste(image_copy, (paste_x, paste_y))
        
        logger.info(f"Character Reference 이미지 처리: {orig_width}x{orig_height} -> {target_size[0]}x{target_size[1]}")
        
        return new_image


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
        if getattr(self, '_is_generating', False):
            return
        self._is_generating = True
        try:
            # 입력 검증
            raw_data = self.get_data(False)
            validation_errors = validate_generation_params(raw_data)
            if validation_errors:
                QMessageBox.warning(self, tr('validation.title'), "\n".join(validation_errors))
                return

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

            self.set_statusbar_text("GENERATING")
            self.set_disable_button(True)
            self._show_progress_bar(-1, -1)  # indeterminate
            self.generate_thread = generate_thread
        
        except Exception as e:
            # 로깅 추가
            logger.error(f"Generate once error: {e}", exc_info=True)
            # 사용자에게 오류 표시
            QMessageBox.critical(self, tr('errors.generation_error'), tr('errors.generation_error_detail').format(e))
            # 버튼 상태 복원
            self.set_disable_button(False)
        finally:
            self._is_generating = False

    def _build_flat_metadata_from_naidict(self, actual_metadata):
        """naidict 형식의 메타데이터를 flat dict로 변환하고 characterPrompts를 재구성"""
        flat_metadata = {
            "prompt": actual_metadata.get("prompt", ""),
            "negative_prompt": actual_metadata.get("negative_prompt", "")
        }
        if "option" in actual_metadata and isinstance(actual_metadata["option"], dict):
            flat_metadata.update(actual_metadata["option"])
        if "etc" in actual_metadata and isinstance(actual_metadata["etc"], dict):
            flat_metadata.update(actual_metadata["etc"])

        # v4_prompt에서 characterPrompts 재구성 (표시용)
        if "v4_prompt" in flat_metadata and "caption" in flat_metadata["v4_prompt"]:
            if "characterPrompts" not in flat_metadata:
                try:
                    char_captions = flat_metadata["v4_prompt"]["caption"].get("char_captions", [])
                    v4_neg_prompt = flat_metadata.get("v4_negative_prompt", {})
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
                        flat_metadata["characterPrompts"] = character_prompts
                        logger.debug(f"Reconstructed {len(character_prompts)} character prompts from v4_prompt")
                except Exception as e:
                    logger.error(f"Failed to reconstruct characterPrompts from v4_prompt: {e}")

        return flat_metadata

    def _on_result_generate(self, error_code, result_str):
        """세션 추적이 포함된 생성 결과 처리"""
        try:
            if error_code == 0:
                # 성공적인 생성 - 이미지 결과 설정
                self.image_result.set_custom_pixmap(result_str)
                self.set_statusbar_text("IDLE")

                # 생성된 이미지를 last_generated_image에 저장 (Enhance 기능용)
                try:
                    if os.path.isfile(result_str):
                        self.last_generated_image = Image.open(result_str).copy()
                        logger.debug("Last generated image saved for enhance feature")
                except Exception as e:
                    logger.error(f"Failed to save last generated image: {e}")

                # 실제 PNG 메타데이터를 읽어서 결과 프롬프트 업데이트
                try:
                    import naiinfo_getter
                    actual_metadata, errcode = naiinfo_getter.get_naidict_from_file(result_str)
                    if errcode == 3 and actual_metadata:
                        # 성공적으로 메타데이터를 읽었을 경우
                        flat_metadata = self._build_flat_metadata_from_naidict(actual_metadata)

                        # 결과 프롬프트 업데이트
                        self.set_result_text(flat_metadata)
                        logger.info("Result prompt updated with actual PNG metadata")
                    else:
                        logger.warning(f"Could not read PNG metadata (error code: {errcode}), using local parameters")
                except Exception as e:
                    logger.error(f"Failed to read PNG metadata: {e}")

                # 세션 모니터링 업데이트
                if hasattr(self, 'session_manager'):
                    self.session_manager.increment_image_count()

                # Anlas 실시간 업데이트 추가 (서버 업데이트 대기 시간 고려)
                QTimer.singleShot(1000, self.refresh_anlas)  # 1초 후 Anlas 새로고침

                # 벌크 Enhancement 모드인 경우 다음 이미지 처리
                if self.enhance_bulk_mode and self.enhance_image_list:
                    self.enhance_current_index += 1
                    logger.info(f"Bulk enhancement: moving to next image (index {self.enhance_current_index}) after 3s delay")

                    # API 스로틀링 방지를 위한 대기 메시지 표시
                    if self.enhance_current_index < len(self.enhance_image_list):
                        self.enhance_progress_label.setText(
                            tr('enhance.waiting_next').format(
                                self.enhance_current_index + 1, len(self.enhance_image_list)
                            )
                        )

                    # 다음 이미지 처리 (3초 딜레이로 API 스로틀링 방지)
                    QTimer.singleShot(3000, self.process_next_enhance_image)

            else:
                # 오류 케이스 - 인증 문제인지 확인
                if error_code == 401 or "authentication" in result_str.lower():
                    # 인증 오류 - 갱신 시도
                    if hasattr(self, 'nai') and self.nai:
                        success = self.nai.refresh_token()
                        if not success:
                            # 갱신 실패 - 로그인 대화상자 표시
                            QMessageBox.critical(self, tr('errors.auth_error'), tr('errors.auth_session_expired'))
                            self.show_login_dialog()
                else:
                    # 다른 오류 처리
                    error_messages = {
                        1: tr('errors.gen_err_1'),
                        2: tr('errors.gen_err_2'),
                        3: tr('errors.gen_err_3'),
                        4: tr('errors.gen_err_4'),
                    }
                    error_msg = error_messages.get(error_code, tr('errors.gen_err_unknown'))

                    logger.error(f"Generation error {error_code}: {error_msg}")
                    QMessageBox.critical(self, tr('errors.generation_error'), f"{error_msg}\n{result_str}")
        
        except Exception as e:
            logger.error(f"Result processing error: {e}", exc_info=True)
        
        finally:
            self._is_generating = False
            self._hide_progress_bar()
            self.set_disable_button(False)
            self.set_statusbar_text("IDLE")

    def show_api_error_dialog(self, error_code, error_message):
        """API 오류를 사용자 친화적으로 표시"""
        title = tr('errors.api_error')

        # 오류 코드별 사용자 친화적 메시지
        friendly_messages = {
            401: tr('errors.api_err_401'),
            402: tr('errors.api_err_402'),
            429: tr('errors.api_err_429'),
            500: tr('errors.api_err_500'),
            503: tr('errors.api_err_503'),
        }

        # 사용자 친화적 메시지
        if error_code in friendly_messages:
            message = tr('errors.api_err_detail').format(friendly_messages[error_code], error_message)
        else:
            message = tr('errors.api_err_generic').format(error_message)

        QMessageBox.critical(self, title, message)

    def show_error_dialog(self, title, message):
        """일반 오류 메시지 표시"""
        QMessageBox.critical(self, title, message)

    def on_click_generate_sett(self):
        path_list, _ = QFileDialog().getOpenFileNames(self,
                                                      caption=tr('errors.settings_load_caption'),
                                                      filter="Txt File (*.txt)")
        if path_list:
            if len(path_list) < 2:
                QMessageBox.information(
                    self, tr('errors.warning'), tr('errors.settings_select_min_two'))
                return

            for path in path_list:
                if not path.endswith(".txt") or not os.path.isfile(path):
                    QMessageBox.information(
                        self, tr('errors.warning'), tr('errors.settings_txt_only'))
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

    def on_click_generate_auto(self, setting_batch_target=None):
        if not self.autogenerate_thread:
            raw_data = self.get_data(False)
            validation_errors = validate_generation_params(raw_data)
            if validation_errors:
                QMessageBox.warning(self, tr('validation.title'), "\n".join(validation_errors))
                return

            d = GenerateDialog(self)
            if d.exec_() == QDialog.Accepted:
                self.list_settings_batch_target = setting_batch_target
                if setting_batch_target:
                    self.index_settings_batch_target = -1
                    is_success = self.proceed_settings_batch()
                    if not is_success:
                        QMessageBox.information(
                            self, tr('errors.warning'), tr('errors.settings_load_failed'))
                        return

                agt = AutoGenerateThread(
                    self, d.count, d.delay, d.ignore_error)
                agt.on_data_created.connect(
                    self._on_after_create_data_apply_gui)
                agt.on_error.connect(self._on_error_autogenerate)
                agt.on_end.connect(self._on_end_autogenerate)
                agt.on_statusbar_change.connect(self.set_statusbar_text)
                agt.on_success.connect(self._on_success_autogenerate)
                agt.on_progress.connect(self._on_autogenerate_progress)
                agt.start()

                self.set_autogenerate_mode(True)
                self.autogenerate_thread = agt
        else:
            self._on_end_autogenerate()

    def _on_error_autogenerate(self, error_code, result):
        QMessageBox.information(
            self, tr('errors.warning'), tr('errors.autogenerate_error').format(str(result)))
        self._on_end_autogenerate()

    def _on_end_autogenerate(self):
        self.autogenerate_thread.stop()
        self.autogenerate_thread = None
        self.set_autogenerate_mode(False)
        self._hide_progress_bar()
        self.set_statusbar_text("IDLE")
        self.refresh_anlas()

    def _on_success_autogenerate(self, result_str):
        self._on_refresh_anlas(self.nai.get_anlas() or -1)

        self.image_result.set_custom_pixmap(result_str)

        # 생성된 이미지를 last_generated_image에 저장 (Enhance 기능용)
        try:
            if os.path.isfile(result_str):
                self.last_generated_image = Image.open(result_str).copy()
                logger.debug("Last generated image saved for enhance feature")
        except Exception as e:
            logger.error(f"Failed to save last generated image: {e}")

        # 실제 PNG 메타데이터를 읽어서 결과 프롬프트 업데이트
        try:
            import naiinfo_getter
            actual_metadata, errcode = naiinfo_getter.get_naidict_from_file(result_str)
            if errcode == 3 and actual_metadata:
                flat_metadata = self._build_flat_metadata_from_naidict(actual_metadata)

                # 결과 프롬프트 업데이트
                self.set_result_text(flat_metadata)
                logger.info("Auto-generate result prompt updated with actual PNG metadata")
            else:
                logger.warning(f"Could not read PNG metadata (error code: {errcode}), using local parameters")
        except Exception as e:
            logger.error(f"Failed to read PNG metadata: {e}")

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
            tr('generate.stop') if is_autogenrate else tr('generate.auto'))
        self.button_generate_auto.setDisabled(False)

        if hasattr(self, 'button_pause_auto'):
            if is_autogenrate:
                self.button_pause_auto.setText(tr('generate.pause'))
                self.button_pause_auto.show()
            else:
                self.button_pause_auto.hide()

    def on_click_pause_autogenerate(self):
        if not self.autogenerate_thread:
            return
        if self.autogenerate_thread.is_paused:
            self.autogenerate_thread.resume()
            self.button_pause_auto.setText(tr('generate.pause'))
        else:
            self.autogenerate_thread.pause()
            self.button_pause_auto.setText(tr('generate.resume'))

    def _show_progress_bar(self, current: int, total: int):
        """Progress bar를 표시한다. total=-1이면 indeterminate 모드."""
        if not hasattr(self, 'progress_bar'):
            return
        if total <= 0:
            self.progress_bar.setMaximum(0)
        else:
            self.progress_bar.setMaximum(total)
            self.progress_bar.setValue(current)
        self.progress_bar.show()

    def _hide_progress_bar(self):
        if hasattr(self, 'progress_bar'):
            self.progress_bar.hide()
            self.progress_bar.setMaximum(100)

    def _on_autogenerate_progress(self, current: int, total: int):
        self._show_progress_bar(current, total)

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

        logger.debug("=== 루프카드 디버깅 시작 ===")

        # 1. 와일드카드 로딩 확인
        self.wcapplier.load_wildcards()
        wildcards = self.wcapplier._wildcards_dict

        logger.debug(f"로드된 와일드카드 수: {len(wildcards)}")
        logger.debug("사용 가능한 키들:")
        for key in wildcards.keys():
            logger.debug(f"  - '{key}': {len(wildcards[key])}개 라인")

        # 2. 특정 키 확인
        test_key = "1_chara"
        logger.debug(f"\n키 '{test_key}' 확인:")
        if test_key in wildcards:
            logger.debug(f"✅ 발견! 내용: {wildcards[test_key]}")
        else:
            logger.debug(f"❌ 없음")

        # 3. 루프카드 테스트
        test_prompt = "##1_chara##"
        logger.debug(f"\n루프카드 테스트: {test_prompt}")

        for i in range(3):
            result = self.wcapplier.apply_wildcards(test_prompt)
            logger.debug(f"시도 {i+1}: {result}")

        logger.debug("=== 루프카드 디버깅 완료 ===")
                
                