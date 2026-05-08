"""
gui_settings_io.py - 설정 저장/로드 관련 Mixin

NAIAutoGeneratorWindow에 mix-in되는 설정 파일 I/O 메서드들.
UI 데이터 수집, QSettings 저장/로드, 설정 파일(.txt) 내보내기/가져오기를 담당합니다.
"""

import json
import os

from PyQt5.QtWidgets import QFileDialog, QMessageBox

from gui_utils import pickedit_lessthan_str, create_folder_if_not_exists, MAX_COUNT_FOR_WHILE
from consts import DEFAULT_PARAMS, DEFAULT_PATH
from logger import get_logger
logger = get_logger()


class SettingsIOMixin:
    """NAIAutoGeneratorWindow에 mix-in되는 설정 저장/로드 관련 메서드.
    
    이 Mixin은 다음을 전제합니다:
    - self.settings: QSettings 인스턴스
    - self.dict_ui_settings: UI 위젯 딕셔너리
    - self.character_prompts_container: CharacterPromptsContainer 인스턴스
    - self.apply_wildcards(): 와일드카드 적용 메서드
    """

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
                logger.debug(f"Missing key in data_dict: {key}")
        
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
                logger.error(f"Error saving settings: {e}")
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
                logger.debug(f"설정 파일 메타데이터: {json_obj['metadata']}")
                
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
            logger.error(f"Error loading settings from file: {e}")

        return False
