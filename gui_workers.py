"""
gui_workers.py - 백그라운드 워커 스레드 모음

gui.py에서 분리된 QThread 서브클래스들.
이미지 생성, 태그 로딩, 토큰 검증, Anlas 조회 등의 백그라운드 작업을 담당합니다.
"""

import os
import io
import time
import threading
import zipfile
import datetime

from PIL import Image

from PyQt5.QtCore import QThread, pyqtSignal

from gui_utils import resource_path, create_folder_if_not_exists, get_filename_only
from consts import DEFAULT_PATH, DEFAULT_TAGCOMPLETION_PATH
from nai_generator import NAIAction
from completer import parse_tag_line, format_tag_display
from i18n_manager import tr
from logger import get_logger
logger = get_logger()


class CompletionTagLoadThread(QThread):
    on_load_completiontag_sucess = pyqtSignal(list)

    def __init__(self, parent, force_reload=False):
        super(CompletionTagLoadThread, self).__init__(parent)
        self.parent = parent
        self.force_reload = force_reload
        
        # 태그 목록을 캐시하는 클래스 변수 추가 (모든 인스턴스가 공유)
        if not hasattr(CompletionTagLoadThread, 'cached_tags'):
            CompletionTagLoadThread.cached_tags = None

    def run(self):
        # 이미 캐시된 태그가 있고, 강제 새로고침이 아니면 재사용
        if CompletionTagLoadThread.cached_tags is not None and not self.force_reload:
            logger.debug("캐시된 태그 사용 (다시 로드하지 않음)")
            self.on_load_completiontag_sucess.emit(CompletionTagLoadThread.cached_tags)
            return

        try:
            logger.info("----- 태그 자동 완성 로딩 시작 -----")
            # 경로 변환 - 리소스 경로 사용
            default_path = self.parent.settings.value("path_tag_completion", DEFAULT_TAGCOMPLETION_PATH)
            logger.error(f"기본 태그 파일 경로: {default_path}")
            tag_path = resource_path(default_path)
            logger.error(f"변환된 태그 파일 경로: {tag_path}")
            logger.error(f"파일 존재 여부: {os.path.exists(tag_path)}")
            
            # 파일이 존재하는지 확인
            if not os.path.exists(tag_path):
                logger.warning("기본 경로에 파일이 없습니다. 대체 경로 시도...")
                # 대체 경로 시도
                alt_paths = [
                    resource_path("danbooru_tags_post_count.csv"),
                    resource_path("./danbooru_tags_post_count.csv"),
                    os.path.join(os.path.dirname(os.path.abspath(__file__)), "danbooru_tags_post_count.csv"),
                    os.path.join(os.getcwd(), "danbooru_tags_post_count.csv")
                ]
                
                for alt_path in alt_paths:
                    logger.error(f"대체 경로 시도: {alt_path}")
                    if os.path.exists(alt_path):
                        tag_path = alt_path
                        logger.error(f"대체 경로 발견: {tag_path}")
                        break
                    else:
                        logger.error(f"  - 파일 없음")
            
            # 태그 파일 다운로드 URL (만약 파일이 없다면)
            download_url = "https://raw.githubusercontent.com/DCP-arca/NAI-Auto-Generator/main/danbooru_tags_post_count.csv"
            
            tag_list = []
            
            # 파일이 없으면 다운로드 시도
            if not os.path.exists(tag_path):
                logger.error(f"태그 파일을 찾을 수 없어 다운로드를 시도합니다: {download_url}")
                try:
                    import requests
                    response = requests.get(download_url)
                    if response.status_code == 200:
                        # 다운로드 성공, 파일 저장
                        save_path = os.path.join(os.getcwd(), "danbooru_tags_post_count.csv")
                        with open(save_path, "wb") as f:
                            f.write(response.content)
                        logger.error(f"태그 파일 다운로드 성공: {save_path}")
                        tag_path = save_path
                    else:
                        logger.error(f"태그 파일 다운로드 실패: {response.status_code}")
                except Exception as e:
                    logger.error(f"다운로드 중 오류 발생: {str(e)}")
            
            # CSV 파일 처리
            if os.path.exists(tag_path):
                logger.error(f"태그 파일 로딩 중: {tag_path}")
                tags = []
                with open(tag_path, "r", encoding='utf8') as f:
                    for line in f:
                        parsed = parse_tag_line(line)
                        if parsed is not None:
                            tags.append(parsed)
                tags = sorted(tags, key=lambda t: t.post_count, reverse=True)
                tag_list = [format_tag_display(t) for t in tags]
                        
                logger.info(f"태그 로딩 완료: {len(tag_list)}개 태그")
                
                # 첫 10개 태그 샘플 출력
            if len(tag_list) > 0:
                CompletionTagLoadThread.cached_tags = tag_list
                
                self.on_load_completiontag_sucess.emit(tag_list)
        except Exception as e:
            logger.error(f"태그 로딩 실패: {str(e)}")
            import traceback
            traceback.print_exc()
            self.on_load_completiontag_sucess.emit([])

        logger.info("----- 태그 자동 완성 로딩 종료 -----")


class AutoGenerateThread(QThread):
    on_data_created = pyqtSignal()
    on_error = pyqtSignal(int, str)
    on_success = pyqtSignal(str)
    on_end = pyqtSignal()
    on_statusbar_change = pyqtSignal(str, list)
    on_progress = pyqtSignal(int, int)  # (current, total); total=-1 means indeterminate

    def __init__(self, parent, count: int | str, delay: float | str, ignore_error: bool):
        super(AutoGenerateThread, self).__init__(parent)
        self.count = int(count or -1)
        self.delay = float(delay or 0.01)
        self.ignore_error = ignore_error
        self.is_dead = False
        self._pause_event = threading.Event()
        self._pause_event.set()  # 초기 상태: 실행 중

    def run(self):
        parent = self.parent()

        count = self.count
        delay = float(self.delay)

        temp_preserve_data_once = False
        while count != 0:
            # 일시정지 대기 (is_dead 체크도 함께)
            while not self._pause_event.is_set():
                if self.is_dead:
                    return
                time.sleep(0.2)
            if self.is_dead:
                return

            # 1. Generate

            # generate data
            if not temp_preserve_data_once:
                try:
                    data = parent._get_data_for_generate()
                    if data is None:
                        self.on_error.emit(1, tr('errors.data_generation_failed'))
                        return
                    parent.nai.set_param_dict(data)
                    self.on_data_created.emit()
                except Exception as e:
                    self.on_error.emit(1, tr('errors.data_generation_error').format(str(e)))
                    return

            # progress bar 업데이트
            if self.count <= -1:
                self.on_progress.emit(0, -1)  # indeterminate
                self.on_statusbar_change.emit("AUTO_GENERATING_INF", [])
            else:
                current = self.count - count + 1
                self.on_progress.emit(current, self.count)
                self.on_statusbar_change.emit("AUTO_GENERATING_COUNT", [
                    self.count, current])

            # before generate, if setting batch
            path = parent.settings.value(
                "path_results", DEFAULT_PATH["path_results"])
            create_folder_if_not_exists(path)
            if parent.list_settings_batch_target:
                setting_path = parent.list_settings_batch_target[parent.index_settings_batch_target]
                setting_name = get_filename_only(setting_path)
                path = path + "/" + setting_name
                create_folder_if_not_exists(path)

            # generate image
            error_code, result_str = _threadfunc_generate_image(
                self, path)
            if self.is_dead:
                return
            if error_code == 0:
                self.on_success.emit(result_str)
            else:
                if self.ignore_error:
                    for t in range(int(delay), 0, -1):
                        self.on_statusbar_change.emit("AUTO_ERROR_WAIT", [t])
                        time.sleep(1)
                        if self.is_dead:
                            return

                    temp_preserve_data_once = True
                    continue
                else:
                    self.on_error.emit(error_code, result_str)
                    return

            # 2. Wait
            count -= 1
            if count != 0:
                temp_delay = delay
                for x in range(int(delay)):
                    # 일시정지 상태면 대기 중 메시지 유지하며 블로킹
                    while not self._pause_event.is_set():
                        if self.is_dead:
                            return
                        time.sleep(0.2)
                    self.on_statusbar_change.emit("AUTO_WAIT", [temp_delay])
                    time.sleep(1)
                    if self.is_dead:
                        return
                    temp_delay -= 1

        self.on_end.emit()

    def pause(self) -> None:
        self._pause_event.clear()

    def resume(self) -> None:
        self._pause_event.set()

    @property
    def is_paused(self) -> bool:
        return not self._pause_event.is_set()

    def stop(self) -> None:
        self.is_dead = True
        self.quit()


def _threadfunc_generate_image(thread_self, path: str) -> tuple[int, str]:
    """이미지 생성 스레드의 핵심 로직.
    
    Args:
        thread_self: 호출하는 QThread 인스턴스 (parent() 접근용)
        path: 이미지 저장 경로
        
    Returns:
        tuple: (error_code, result_str)
            - error_code 0: 성공, result_str은 저장된 파일 경로
            - error_code 1: API 오류
            - error_code 2: 이미지 열기 오류
            - error_code 3: 이미지 저장 오류
            - error_code 4: 예기치 못한 오류
    """
    try:
        # 중앙 로거 가져오기
        from logger import get_logger
        logger = get_logger()
        
        # 1: 이미지 생성
        parent = thread_self.parent()
        nai = parent.nai

        # action 결정 (순서 중요: mask 체크를 먼저!)
        if nai.parameters.get("mask"):
            action = NAIAction.infill
            logger.info("✓ Mask detected - using NAIAction.infill")
        elif nai.parameters.get("image"):
            action = NAIAction.img2img
            logger.info("img2img mode detected - using NAIAction.img2img")
        else:
            action = NAIAction.generate

        # 액션 타입 로깅
        logger.debug(f"Image generation action: {action}")
        
        # 이 부분 수정: 튜플 반환값 확인 및 처리
        result = nai.generate_image(action)
        
        # 튜플 반환 확인 (오류 발생 시)
        if isinstance(result, tuple) and len(result) == 2 and result[0] is None:
            error_message = result[1]
            logger.error(f"API 오류: {error_message}")
            return 1, error_message  # 오류 코드와 메시지 반환
            
        if not result:
            logger.error("서버에서 정보를 가져오는데 실패했습니다.")
            return 1, tr('errors.gen_err_1')
        
        # 2: 이미지 열기
        try:
            zipped = zipfile.ZipFile(io.BytesIO(result))
            image_bytes = zipped.read(zipped.infolist()[0])
            img = Image.open(io.BytesIO(image_bytes))
        except Exception as e:
            logger.error(f"이미지 열기 오류: {e}")
            return 2, str(e)
        
        # 3: 이미지 저장
        create_folder_if_not_exists(path)

        # 안전한 파일명 생성
        def sanitize_filename(filename):
            # 윈도우 파일명에 허용되지 않는 문자 제거
            return "".join(c for c in filename if c.isalnum() or c in (' ', '_', '-', '.')).rstrip()

        # 파일명 형식화 함수
        def format_filename(format_template, nai_params, parent_window):
            """
            파일명 템플릿을 실제 파일명으로 변환

            지원되는 플레이스홀더:
            [datetime] - 날짜+시간 (251118_11240833)
            [date] - 날짜만 (251118)
            [time] - 시간만 (11240833)
            [prompt] - 프롬프트 텍스트
            [character] - 캐릭터 프롬프트 (첫 번째)
            [seed] - 시드 값
            """
            now = datetime.datetime.now()

            # 날짜/시간 포맷
            datetime_str = now.strftime("%y%m%d_%H%M%S%f")[:-4]
            date_str = now.strftime("%y%m%d")
            time_str = now.strftime("%H%M%S%f")[:-4]

            # 프롬프트 가져오기 및 길이 제한
            prompt_limit = int(parent_window.settings.value("filename_prompt_word_limit", 50))
            prompt_text = sanitize_filename(nai_params.get("prompt", ""))[:prompt_limit]

            # 캐릭터 프롬프트 가져오기
            character_text = ""
            try:
                if hasattr(parent_window, 'character_prompts_container'):
                    char_data = parent_window.character_prompts_container.get_data()
                    if char_data and "characters" in char_data and len(char_data["characters"]) > 0:
                        first_char = char_data["characters"][0]
                        char_prompt = first_char.get("prompt", "")
                        if char_prompt:
                            character_limit = int(parent_window.settings.value("filename_character_word_limit", 30))
                            character_text = sanitize_filename(char_prompt)[:character_limit]
            except Exception as e:
                logger.debug(f"캐릭터 프롬프트 가져오기 실패: {e}")

            # 시드 가져오기
            seed = nai_params.get("seed", "")

            # 플레이스홀더 치환
            result = format_template
            result = result.replace("[datetime]", datetime_str)
            result = result.replace("[date]", date_str)
            result = result.replace("[time]", time_str)
            result = result.replace("[prompt]", prompt_text)
            result = result.replace("[character]", character_text)
            result = result.replace("[seed]", str(seed))

            # 빈 플레이스홀더로 인한 연속 구분자 제거 (예: "__" -> "_")
            while "__" in result:
                result = result.replace("__", "_")
            while "  " in result:
                result = result.replace("  ", " ")

            # 시작/끝의 구분자 제거
            result = result.strip("_- ")

            return result

        # 파일명 생성 로직
        # 사용자 정의 포맷 가져오기
        filename_format = thread_self.parent().settings.value("filename_format", "[datetime]_[prompt]")
        filename = format_filename(filename_format, nai.parameters, thread_self.parent())

        # 파일명이 비어있거나 너무 짧으면 기본 포맷 사용
        if not filename or len(filename) < 3:
            logger.warning("파일명 형식화 결과가 비어있음, 기본 포맷 사용")
            timename = datetime.datetime.now().strftime("%y%m%d_%H%M%S%f")[:-4]
            filename = timename

        # 파일 확장자 추가
        filename += ".png"
        
        # 최종 저장 경로 생성
        dst = os.path.join(path, filename)
        
        # 중복 파일명 처리
        counter = 1
        base, ext = os.path.splitext(dst)
        while os.path.exists(dst):
            dst = f"{base}_{counter}{ext}"
            counter += 1
        
        # 상세 로깅
        logger.debug(f"최종 저장 경로: {dst}")
        logger.debug(f"파일명: {filename}")
        
        try:
            img.save(dst)
            logger.info(f"이미지 성공적으로 저장: {dst}")
        except Exception as e:
            logger.error(f"이미지 저장 오류: {e}")
            return 3, str(e)
        
        return 0, dst
    
    except Exception as e:
        # 중앙 로거 사용 및 예외 정보 포함
        from logger import get_logger
        logger = get_logger()
        logger.critical(f"예기치 못한 오류: {e}", exc_info=True)
        return 4, str(e)


class GenerateThread(QThread):
    generate_result = pyqtSignal(int, str)

    def __init__(self, parent):
        super(GenerateThread, self).__init__(parent)
        self.is_stopped = False

    def run(self):
        path = self.parent().settings.value(
            "path_results", DEFAULT_PATH["path_results"])
        error_code, result_str = _threadfunc_generate_image(self, path)
        
        if not self.is_stopped:
            self.generate_result.emit(error_code, result_str)
    
    def stop(self) -> None:
        self.is_stopped = True
        self.wait()


class TokenValidateThread(QThread):
    validation_result = pyqtSignal(int)

    def __init__(self, parent):
        super(TokenValidateThread, self).__init__(parent)
        self.parent = parent

    def run(self):
        try:
            is_login_success = self.parent.nai.check_logged_in()
            
            # 속성 존재 확인 및 초기화
            if is_login_success and not hasattr(self.parent.nai, '_estimated_token_lifetime'):
                self.parent.nai._estimated_token_lifetime = 24 * 3600
                
            self.validation_result.emit(0 if is_login_success else 1)
        except Exception as e:
            logger.error(f"토큰 검증 오류: {e}")
            self.validation_result.emit(1)  # 오류 발생 시 실패로 처리


class AnlasThread(QThread):
    anlas_result = pyqtSignal(int)

    def __init__(self, parent):
        super(AnlasThread, self).__init__(parent)

    def run(self):
        anlas = self.parent().nai.get_anlas() or -1

        self.anlas_result.emit(anlas)
