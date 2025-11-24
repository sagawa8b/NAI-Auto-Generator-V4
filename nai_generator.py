from hashlib import blake2b
import argon2
from base64 import urlsafe_b64encode
import requests
import random
import json
import io
import time
import zipfile
import logging
from enum import Enum
from PIL import Image
import base64

from logger import get_logger
logger = get_logger()  # 기존 setup_logger() 대신 통일된 로거 사용

BASE_URL_DEPRE = "https://api.novelai.net"
BASE_URL = "https://image.novelai.net"


class NAISessionManager:
    def __init__(self, nai_generator, check_interval=1800, keepalive_interval=600):
        logger.info("NAISessionManager 초기화")
        self.nai = nai_generator
        self.base_check_interval = check_interval  # 기본 간격
        self.base_keepalive_interval = keepalive_interval  # 기본 유지 간격
        
        # 적응형 간격 관리
        self.check_interval = check_interval
        self.keepalive_interval = keepalive_interval
        
        self.last_check_time = time.time()
        self.last_keepalive_time = time.time()
        self.last_activity_time = time.time()
        
        # 이미지 생성 세션 관리
        self.image_count_since_login = 0
        self.max_images_per_session = 450
        
        # 오류 추적
        self.consecutive_errors = 0
        self.last_error_time = 0
        self.error_types = {}
        self.network_available = True  # 네트워크 상태 플래그 추가
        self.last_network_check = time.time()
        self.network_check_interval = 60  # 1분마다 네트워크 상태 확인
        
        # 세션 상태
        self.session_health = 1.0  # 1.0 = 완전 건강, 0.0 = 실패
        
        # 최적 갱신 주기 학습
        self.successful_session_durations = []
        self._estimated_token_lifetime = 24 * 3600  # 초기 예상: 24시간
        
        # 로깅 설정
        self.logger = logging.getLogger('nai_session_manager')
        self.logger.setLevel(logging.INFO)
    
    def update(self):
        """정기적으로 호출할 통합 세션 관리 함수 - 적응형 간격 적용"""
        current_time = time.time()
        
        # 네트워크 상태 정기적 확인 추가
        if current_time - self.last_network_check > self.network_check_interval:
            self.check_network_availability()
            self.last_network_check = current_time
            
        # 네트워크 불가 상태면 세션 확인 생략
        if not self.network_available:
            logger.warning("네트워크 연결 없음 - 세션 업데이트 건너뜀")
            return self.session_health
            
        # 활동 감지 기반 간격 조정
        idle_time = current_time - self.last_activity_time
        if idle_time > 3600:  # 1시간 이상 비활성
            # 비활성 시 절전 모드: 간격 확장
            adjusted_check = min(self.base_check_interval * 2, 7200)  # 최대 2시간
            adjusted_keepalive = min(self.base_keepalive_interval * 2, 1800)  # 최대 30분
        else:
            # 활성 상태: 정상 또는 짧은 간격
            adjusted_check = max(self.base_check_interval / (1 + self.consecutive_errors * 0.5), 600)  # 최소 10분
            adjusted_keepalive = self.base_keepalive_interval
        
        # 전체 세션 확인
        if current_time - self.last_check_time > adjusted_check:
            self.perform_session_check()
            self.last_check_time = current_time
            
        # 경량 keepalive
        elif current_time - self.last_keepalive_time > adjusted_keepalive:
            self.perform_keepalive()
            self.last_keepalive_time = current_time
            
        # 이미지 수 임계값 확인 - 거의 도달했을 때 미리 갱신
        images_threshold = self.max_images_per_session * 0.9  # 90%에 도달하면 갱신
        if self.image_count_since_login >= images_threshold:
            self.logger.info(f"세션당 이미지 임계값({images_threshold:.0f}/{self.max_images_per_session})에 도달, 사전 로그인 갱신")
            self.force_refresh()
            self.image_count_since_login = 0
            
        # 세션 상태 업데이트 및 UI 반영
        self._update_session_health()
        return self.session_health
    
    def check_network_availability(self):
        """네트워크 연결 가능 여부 확인 (추가)"""
        try:
            # DNS 서버 체크 - 가볍게 확인
            import socket
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            
            if not self.network_available:
                logger.info("네트워크 연결 복구 감지")
                self.network_available = True
                # 연결 복구 후 세션 검증
                self.force_refresh()
            return True
        except (socket.timeout, socket.error):
            if self.network_available:
                logger.error("네트워크 연결 끊김 감지")
                self.network_available = False
            return False
    
    def _update_session_health(self):
        """세션 건강도 점수 계산"""
        # 오류 횟수 기반 감소
        error_factor = max(0, 1 - (self.consecutive_errors * 0.2))
        
        # 이미지 카운트 기반 감소
        count_factor = max(0, 1 - (self.image_count_since_login / self.max_images_per_session))
        
        # 시간 경과 기반 감소
        time_elapsed = time.time() - self.last_check_time
        time_factor = max(0, 1 - (time_elapsed / self._estimated_token_lifetime))
        
        # 종합 건강도 계산
        self.session_health = min(1.0, (error_factor * 0.4) + (count_factor * 0.4) + (time_factor * 0.2))
    
    def perform_session_check(self):
        """전체 세션 유효성 확인 - 오류 처리 강화"""
        try:
            if not self.nai.check_logged_in():
                self.logger.warning("세션 만료 감지됨")
                success = self.nai.refresh_token()
                
                if success:
                    self.consecutive_errors = 0
                    self.logger.info("세션 갱신 성공")
                    
                    # 성공적인 세션 지속 시간 추적하여 학습
                    if hasattr(self.nai, '_last_successful_login'):
                        duration = time.time() - self.nai._last_successful_login
                        if duration > 600:  # 10분 이상 지속된 세션만 고려
                            self.successful_session_durations.append(duration)
                            # 최근 5개 세션 기준으로 평균 계산
                            if len(self.successful_session_durations) > 5:
                                self.successful_session_durations = self.successful_session_durations[-5:]
                            self._estimated_token_lifetime = sum(self.successful_session_durations) / len(self.successful_session_durations)
                    
                    # 새 로그인 시간 기록
                    self.nai._last_successful_login = time.time()
                else:
                    self.consecutive_errors += 1
                    self.logger.error(f"세션 갱신 실패 (연속 오류: {self.consecutive_errors})")
                
                # 이미지 카운트 리셋
                self.image_count_since_login = 0
                
                return success
            else:
                return True
        except requests.exceptions.ConnectionError as e:
            self.consecutive_errors += 1
            self.last_error_time = time.time()
            self.error_types.setdefault('connection', 0)
            self.error_types['connection'] += 1
            self.logger.error(f"세션 확인 중 연결 오류: {e}")
            return False
        except Exception as e:
            self.consecutive_errors += 1
            self.last_error_time = time.time()
            self.error_types.setdefault('unknown', 0)
            self.error_types['unknown'] += 1
            self.logger.error(f"세션 확인 오류: {e}")
            return False
    
    def perform_keepalive(self):
        """경량 keepalive 호출 - 오류 처리 개선"""
        try:
            # API 요청 부하를 최소화하는 가장 경량 호출
            result = self.nai.get_anlas()
            if result is not None:  # 성공적인 응답
                self.logger.debug("Keepalive 성공")
                return True
            else:
                self.logger.warning("Keepalive 응답 없음")
                # 응답이 없으면 세션 체크 시도
                return self.perform_session_check()
        except requests.exceptions.Timeout:
            self.logger.warning("Keepalive 시간 초과")
            # 시간 초과는 치명적이지 않음 - 다음 체크에서 재시도
            return False
        except Exception as e:
            self.consecutive_errors += 1
            self.logger.warning(f"Keepalive 실패: {e}")
            
            # 특정 오류 패턴에 따라 즉시 세션 체크
            if "401" in str(e) or "unauthorized" in str(e).lower():
                self.logger.info("인증 오류 감지, 즉시 세션 검사 실행")
                return self.perform_session_check()
            return False
            
    def force_refresh(self):
        """타이밍과 관계없이 강제 토큰 갱신 - 재시도 로직 추가"""
        max_attempts = 3
        backoff_factor = 1.5
        delay = 2
        
        for attempt in range(max_attempts):
            try:
                success = self.nai.refresh_token()
                if success:
                    self.consecutive_errors = 0
                    self.image_count_since_login = 0
                    self.logger.info(f"강제 토큰 갱신 성공 (시도: {attempt+1})")
                    return True
                else:
                    self.logger.warning(f"강제 토큰 갱신 실패 (시도: {attempt+1})")
            except Exception as e:
                self.logger.error(f"강제 갱신 오류 (시도: {attempt+1}): {e}")
            
            # 마지막 시도가 아니면 지수 백오프로 대기
            if attempt < max_attempts - 1:
                wait_time = delay * (backoff_factor ** attempt)
                self.logger.info(f"{wait_time:.1f}초 후 재시도...")
                time.sleep(wait_time)
        
        self.consecutive_errors += 1
        return False
            
    def increment_image_count(self):
        """각 이미지 생성 후 호출 - 활동 기록"""
        self.image_count_since_login += 1
        self.last_activity_time = time.time()
        
        # 경계값 접근 시 경고 로그
        if self.image_count_since_login >= self.max_images_per_session * 0.8:
            self.logger.warning(f"세션 이미지 카운트 경고: {self.image_count_since_login}/{self.max_images_per_session}")
        
        return self.image_count_since_login

    def get_status_info(self):
        """UI에 표시할 세션 상태 정보"""
        return {
            "health": self.session_health,
            "image_count": self.image_count_since_login,
            "max_images": self.max_images_per_session,
            "errors": self.consecutive_errors,
            "estimated_lifetime": self._estimated_token_lifetime
        }



class NAIAction(Enum):
    generate = "generate",
    img2img = "img2img",
    infill = "infill"


class NAIParam(Enum):
    # 기본 파라미터
    prompt = 1
    negative_prompt = 2
    width = 3
    height = 4
    steps = 5
    cfg_rescale = 8
    sampler = 11
    seed = 12
    extra_noise_seed = 13
    scale = 14
    uncond_scale = 15
    reference_image = 16
    reference_information_extracted = 17
    reference_strength = 18
    image = 19
    noise = 20
    strength = 21
    mask = 22
    
    
    # V4 전용 파라미터
    autoSmea = 23
    v4_model_preset = 24
    anti_artifacts = 25
    add_original_image = 26
    params_version = 27
    legacy = 28
    prefer_brownian = 29
    ucPreset = 30
    dynamic_thresholding = 31
    quality_toggle = 32
    characterPrompts = 33
    skip_cfg_above_sigma = 34  # 새로운 파라미터 번호 추가
    
    # Character Reference 파라미터 추가
    reference_image_multiple = 35
    reference_information_extracted_multiple = 36
    reference_strength_multiple = 37
    


TYPE_NAIPARAM_DICT = {
    NAIParam.prompt: str,
    NAIParam.negative_prompt: str,
    NAIParam.width: int,
    NAIParam.height: int,
    NAIParam.steps: int,
    NAIParam.cfg_rescale: float,
    NAIParam.sampler: str,
    NAIParam.seed: int,
    NAIParam.extra_noise_seed: int,
    NAIParam.scale: float,
    NAIParam.uncond_scale: float,
    NAIParam.reference_image: str,
    NAIParam.reference_information_extracted: float,
    NAIParam.reference_strength: float,
    NAIParam.image: str,
    NAIParam.noise: float,
    NAIParam.strength: float,
    NAIParam.mask: str,
    
    # V4 파라미터 타입
    NAIParam.autoSmea: bool,
    NAIParam.v4_model_preset: str,
    NAIParam.anti_artifacts: float,
    NAIParam.add_original_image: bool,
    NAIParam.params_version: int,
    NAIParam.legacy: bool,
    NAIParam.prefer_brownian: bool,
    NAIParam.ucPreset: int,
    NAIParam.dynamic_thresholding: bool,
    NAIParam.quality_toggle: bool,
    NAIParam.characterPrompts: list,
    NAIParam.skip_cfg_above_sigma: (int, type(None)),  # int 또는 None 타입 허용
    
    # Character Reference 타입 추가
    NAIParam.reference_image_multiple: list,
    NAIParam.reference_information_extracted_multiple: list,
    NAIParam.reference_strength_multiple: list,
    
    
}


def argon_hash(email: str, password: str, size: int, domain: str) -> str:
    pre_salt = f"{password[:6]}{email}{domain}"
    # salt
    blake = blake2b(digest_size=16)
    blake.update(pre_salt.encode())
    salt = blake.digest()
    raw = argon2.low_level.hash_secret_raw(
        password.encode(),
        salt,
        2,
        int(2000000 / 1024),
        1,
        size,
        argon2.low_level.Type.ID,
    )
    hashed = urlsafe_b64encode(raw).decode()
    return hashed


class NAIGenerator():
    def __init__(self):
        self.access_token = None
        self.username = None
        self.password = None        
        # 세션 관리 관련 속성 명시적 초기화
        self._last_successful_login = None
        self._last_token_check = 0
        self._last_successful_check = 0
        self._estimated_token_lifetime = 24 * 3600  # 초기 예상: 24시간
        
        self.parameters = {
            # 기본 입력
            "prompt": "",
            "negative_prompt": "",
            
            # 이미지 설정
            "width": 1024,  # 832에서 1024로 변경
            "height": 1024, # 1216에서 1024로 변경
            "n_samples": 1,
            
            # 시드 설정
            "seed": random.randint(0, 2**32-1),
            "extra_noise_seed": -1,
            
            # 샘플링 옵션
            "sampler": "k_euler_ancestral",
            "steps": 28,
            "scale": 5.0,  # CFG 값
            "uncond_scale": 1.0,
            
            # V4 품질 관련
            "autoSmea": True,  # 스마팅 효과 활성화
            "cfg_rescale": 0,  # CFG 리스케일 (0 = 비활성화)
            "quality_toggle": True,  # 품질 향상 토글
            "dynamic_thresholding": False,  # 동적 임계처리
            
            # V4 모델 프리셋 및 기타 설정
            "v4_model_preset": "Artistic",  # Normal, Artistic, Anime 중 선택
            "anti_artifacts": 0.0,  # 아티팩트 제거 강도
            
            # V4.5에서 개선된 설정들
            "params_version": 3,
            "add_original_image": True,
            "legacy": False,
            "prefer_brownian": True,
            "noise_schedule": "karras",
            "ucPreset": 0,
            
       
            # V4.5 최적화 설정
            "v4_model_preset": "Artistic",  # Normal, Artistic, Anime 중 선택
            "model": "nai-diffusion-4-5-full",  # 기본 모델을 4.5로 설정
                   
            # 이미지 변환 설정 (img2img, inpainting)
            "image": None,
            "mask": None,
            "noise": 0.0,
            "strength": 0.7,
            
            # 참조 이미지 설정 (reference)
            "reference_image": None,
            "reference_strength": 0.6,
            "reference_information_extracted": 1.0,
            
            # 캐릭터 프롬프트
            "characterPrompts": [],
            
            # Character Reference 파라미터 추가
            "reference_image_multiple": None,
            "reference_information_extracted_multiple": None,
            "reference_strength_multiple": None,        
                        
        }
    
    def refresh_token(self):
        """토큰 갱신 최적화 - 오류 추적 및 스마트 재시도"""
        logger.debug("토큰 갱신 시도")
        current_time = time.time()
        
        # 5분 내 이미 확인했으면 스킵 (과도한 요청 방지)
        if hasattr(self, '_last_token_check') and current_time - self._last_token_check < 300:
            return True
            
        self._last_token_check = current_time
        
        # 경량 호출로 토큰 유효성 확인
        try:
            if self.check_logged_in():
                return True
        except Exception as e:
            logging.warning(f"토큰 확인 오류: {e}")
            # 계속 진행 - 확인 오류는 반드시 만료를 의미하지 않음
        
        # 자격 증명이 있고 토큰이 유효하지 않을 경우만 재로그인
        if not (self.username and self.password):
            logging.error("토큰 갱신 실패: 자격 증명 없음")
            return False
        
        # 재로그인 시도 - 지수 백오프 재시도
        max_attempts = 3
        backoff = 2
        
        for attempt in range(max_attempts):
            try:
                logging.info(f"토큰 갱신 시도 {attempt+1}/{max_attempts}...")
                success = self.try_login(self.username, self.password)
                
                if success:
                    logging.info("토큰 갱신 성공")
                    return True
                    
                logging.warning(f"토큰 갱신 실패 (시도 {attempt+1})")
                
                # 마지막 시도가 아니면 대기 후 재시도
                if attempt < max_attempts - 1:
                    wait_time = backoff ** attempt
                    logging.info(f"{wait_time}초 후 재시도...")
                    time.sleep(wait_time)
            except requests.exceptions.ConnectionError:
                logging.error(f"토큰 갱신 중 네트워크 오류 (시도 {attempt+1})")
                if attempt < max_attempts - 1:
                    wait_time = backoff ** attempt
                    time.sleep(wait_time)
            except Exception as e:
                logging.error(f"토큰 갱신 중 예외 발생: {e}")
                if attempt < max_attempts - 1:
                    wait_time = backoff ** attempt
                    time.sleep(wait_time)
        
        return False
        
        
    def try_login(self, username, password):
        # get_access_key
        access_key = argon_hash(username, password, 64, "novelai_data_access_key")[:64]
        try:
            # try login
            response = requests.post(
                f"{BASE_URL_DEPRE}/user/login", json={"key": access_key})
            self.access_token = response.json()["accessToken"]

            # if success, save id/pw in
            self.username = username
            self.password = password
            
            # 로그인 성공 시 세션 타임스탬프 업데이트
            self._last_successful_login = time.time()
            self._last_token_check = time.time()
            
            # 세션 건강도 리셋
            if hasattr(self, 'session_manager'):
                self.session_manager.consecutive_errors = 0
                self.session_manager.image_count_since_login = 0
                self.session_manager.session_health = 1.0

            return True
        except Exception as e:
            logger.error(f"로그인 실패: {e}")

        return False

    def set_param(self, param_key: NAIParam, param_value):
        # param_key type check
        assert(isinstance(param_key, NAIParam))
        # param_value type check
        if param_value is not None:
            assert(isinstance(param_value, TYPE_NAIPARAM_DICT[param_key]))

        self.parameters[param_key.name] = param_value

    def set_param_dict(self, param_dict):
        # V4 API에서만 사용하는 특별한 파라미터들
        special_params = ["legacy_v3_extend", "noise_schedule", "params_version",
                          "characterPrompts", "v4_prompt", "v4_negative_prompt", "model",
                          "deliberate_euler_ancestral_bug", "controlnet_strength"]  # WebUI 호환성을 위한 파라미터 추가

        for k, v in param_dict.items():
            if k:
                if k in special_params:
                    # 특별 파라미터는 직접 설정
                    self.parameters[k] = v
                    continue
                elif k == "use_character_coords":
                    # use_character_coords는 별도 처리
                    self.parameters[k] = v
                    continue

                try:
                    param_key = NAIParam[k]
                    self.set_param(param_key, v)
                except Exception as e:
                    logger.debug(f"파라미터 무시: {k} (원인: {e})")
                    continue

    def get_anlas(self):
        try:
            response = requests.get(BASE_URL_DEPRE + "/user/subscription", headers={
                "Authorization": f"Bearer {self.access_token}"})
            data_dict = json.loads(response.content)
            trainingStepsLeft = data_dict['trainingStepsLeft']
            anlas = int(trainingStepsLeft['fixedTrainingStepsLeft']) + \
                int(trainingStepsLeft['purchasedTrainingSteps'])

            return anlas
        except Exception as e:
            logger.error(f"Error getting ANLAS: {e}")

        return None

    def generate_image(self, action: NAIAction):
        assert(isinstance(action, NAIAction))
        
        logger.debug("=== generate_image 메서드 시작 ===")
        
        
        # 요청 추적을 위한 ID 생성
        import uuid
        request_id = str(uuid.uuid4())[:8]
        logger.info(f"Image generation request started [ID: {request_id}] - {action.name}")

        # 모델 선택 (파라미터에서 가져오기)
        model = self.parameters.get("model", "nai-diffusion-4-5-curated")
        
        # Infill 모드일 경우 모델명에 inpainting 추가
        if action == NAIAction.infill:
            # 모델 이름에서 버전 추출
            if "4-5" in model:
                model = "nai-diffusion-4-5-full-inpainting"
            else:
                model = "nai-diffusion-4-full-inpainting"
        
        logger.info(f"📍 [{request_id}] generate_image 메서드 시작")
        
        # 시드 설정
        if self.parameters["extra_noise_seed"] == -1:
            self.parameters["extra_noise_seed"] = self.parameters["seed"]

        # *** V4 구조에 맞게 파라미터 변환 ***
        logger.info(f"📍 [{request_id}] V4 파라미터 변환 호출 직전")
        self._prepare_v4_parameters()
        logger.info(f"📍 [{request_id}] V4 파라미터 변환 호출 완료")

        # *** Infill 모드일 경우 img2img 파라미터 구조화 ***
        if action == NAIAction.infill:
            logger.info(f"📍 [{request_id}] Infill 모드 - img2img 파라미터 구조화")

            # 마스크 존재 확인
            has_mask = "mask" in self.parameters and self.parameters["mask"] is not None
            if has_mask:
                mask_size = len(self.parameters["mask"]) if isinstance(self.parameters["mask"], str) else 0
                logger.info(f"✓ Mask detected in parameters - size: {mask_size} bytes")
            else:
                logger.warning(f"⚠ WARNING: Infill mode but NO MASK in parameters!")

            # Get strength value from slider for img2img and inpaintImg2ImgStrength
            img2img_strength = self.parameters.get("strength", 0.5)

            # img2img 네스트 객체 생성 (웹 UI 구조와 일치)
            img2img_params = {
                "strength": img2img_strength,
                "color_correct": True
            }

            # img2img 객체를 parameters에 추가
            self.parameters["img2img"] = img2img_params

            # 웹 UI와 동일하게 inpaintImg2ImgStrength 추가 (슬라이더 값 사용)
            self.parameters["inpaintImg2ImgStrength"] = img2img_strength

            # Top-level strength는 웹 UI와 동일하게 ALWAYS 0.7로 설정
            # 웹 UI 관찰: img2img.strength=0.5, inpaintImg2ImgStrength=0.5, strength=0.7
            # 세 가지 strength 값이 서로 다른 목적을 가짐
            self.parameters["strength"] = 0.7  # 항상 0.7 (웹 UI와 동일)

            # noise는 img2img 객체에 포함하지 않음 (웹 UI와 일치)
            if "noise" in self.parameters:
                del self.parameters["noise"]

            logger.info(f"📍 [{request_id}] img2img params: {img2img_params}")
            logger.info(f"📍 [{request_id}] inpaintImg2ImgStrength: {img2img_strength}")
            logger.info(f"📍 [{request_id}] Top-level strength: {self.parameters.get('strength')} (always 0.7 for infill)")
            logger.info(f"📍 [{request_id}] Mask still in parameters: {has_mask}")

        url = BASE_URL + f"/ai/generate-image"

        data = {
            "input": self.parameters["prompt"],
            "model": model,
            "action": action.name,
            "parameters": self.parameters,
        }
        
        # 디버깅: director_reference_* 파라미터 확인
        if "director_reference_descriptions" in self.parameters:
            logger.info(f"📍 API 전송 데이터에 director_reference_descriptions 포함됨")
            logger.info(f"📍 descriptions 내용: {self.parameters['director_reference_descriptions']}")
        if "director_reference_images" in self.parameters:
            logger.info(f"📍 API 전송 데이터에 director_reference_images 포함됨: {len(self.parameters['director_reference_images'])}개")
        
        headers = {"Authorization": f"Bearer {self.access_token}"}

        # API 전송 직전 최종 데이터 로깅 강화
        logger.info(f"📍 [{request_id}] API 전송 직전 최종 데이터 검증:")
        logger.info(f"  - 모델: {model}")
        logger.info(f"  - 액션: {action.name}")
        
        if "v4_prompt" in self.parameters:
            v4_prompt = self.parameters["v4_prompt"]
            logger.info(f"  - v4_prompt use_coords: {v4_prompt.get('use_coords', False)}")
            char_captions = v4_prompt["caption"].get("char_captions", [])
            logger.info(f"  - 캐릭터 수: {len(char_captions)}")
            
            for i, char_caption in enumerate(char_captions):
                centers = char_caption.get('centers', [])
                prompt_preview = char_caption.get('char_caption', '')[:30] + '...'
                logger.info(f"  - 캐릭터 {i+1}: '{prompt_preview}' -> {centers}")
        
        # 캐릭터 프롬프트 로깅 (기존 코드 개선)
        if "characterPrompts" in self.parameters:
            logger.debug(f"[{request_id}] 원본 characterPrompts: {len(self.parameters['characterPrompts'])}개")
        
        # 네트워크 상태 확인 추가
        if hasattr(self, 'session_manager') and not self.session_manager.network_available:
            logger.error("네트워크 연결 없음 - 이미지 생성 요청 실패")
            return None, "인터넷 연결이 없습니다. 네트워크 상태를 확인해주세요."
        
        # 재시도 메커니즘 개선
        max_retries = 3
        retry_delay = 3  # 초 단위
        dns_error_occurred = False
        
        for retry in range(max_retries):
            try:
                logger.info(f"API request attempt [ID: {request_id}] - attempt {retry+1}/{max_retries}")
                response = requests.post(url, json=data, headers=headers, timeout=60)
                
                # 상태 코드 확인
                if response.status_code == 200 or response.status_code == 201:
                    logger.info(f"API request successful [ID: {request_id}] - status code: {response.status_code}")
                    if hasattr(self, 'session_manager'):
                        self.session_manager.consecutive_errors = 0  # 오류 카운터 리셋
                    return response.content
                else:
                    # 오류 응답 분석
                    error_info = f"상태 코드: {response.status_code}"
                    try:
                        error_json = response.json()
                        error_info += f", 메시지: {error_json.get('message', '알 수 없음')}"
                    except:
                        error_info += f", 응답: {response.text[:200]}"
                    
                    logger.error(f"API error response [ID: {request_id}] - {error_info}")
                    
                    # 특정 오류에 따른 처리
                    if response.status_code == 401:
                        if self.refresh_token():  # 토큰 갱신 시도
                            logger.info(f"Token refreshed, retrying request [ID: {request_id}]")
                            continue  # 요청 재시도
                        return None, "인증 오류: 로그인이 필요합니다."
                    elif response.status_code == 402:
                        return None, "결제 필요: Anlas가 부족합니다."
                    elif response.status_code >= 500:
                        # 서버 오류는 더 긴 대기 시간으로 재시도
                        wait_time = retry_delay * (2 ** retry)
                        logger.warning(f"서버 오류, {wait_time}초 후 재시도... [ID: {request_id}]")
                        time.sleep(wait_time)
                        continue
                        
            except requests.exceptions.Timeout:
                logger.error(f"API request timeout [ID: {request_id}] - attempt {retry+1}/{max_retries}")
                wait_time = retry_delay * (2 ** retry)
                time.sleep(wait_time)
                continue
                
            except requests.exceptions.ConnectionError as e:
                logger.error(f"API request connection error [ID: {request_id}]: {str(e)}")
                
                # DNS 오류 감지 (getaddrinfo failed 포함)
                if "getaddrinfo failed" in str(e) or "NameResolutionError" in str(e):
                    dns_error_occurred = True
                    if hasattr(self, 'session_manager'):
                        self.session_manager.network_available = False
                        self.session_manager.check_network_availability()  # 즉시 네트워크 상태 확인
                    
                    logger.error(f"DNS 해석 실패 - 네트워크 연결 문제")
                    return None, "인터넷 연결 문제: 서버에 연결할 수 없습니다. 네트워크 상태를 확인해주세요."
                
                # 일반 연결 오류는 지수 백오프로 재시도
                wait_time = retry_delay * (2 ** retry)
                logger.warning(f"연결 오류, {wait_time}초 후 재시도... [ID: {request_id}]")
                time.sleep(wait_time)
                continue
                    
            except Exception as e:
                logger.error(f"API request exception [ID: {request_id}]: {str(e)}", exc_info=True)
                
                # 마지막 시도가 아니면 재시도
                if retry < max_retries - 1:
                    wait_time = retry_delay * (2 ** retry)
                    logger.warning(f"예외 발생, {wait_time}초 후 재시도... [ID: {request_id}]")
                    time.sleep(wait_time)
                    continue
                return None, f"API 요청 오류: {str(e)}"

        # DNS 오류가 발생했다면 다른 메시지 제공
        if dns_error_occurred:
            return None, "인터넷 연결 문제: 서버에 연결할 수 없습니다. 네트워크 상태를 확인해주세요."
            
        return None, "최대 재시도 횟수 초과: 서버에 연결할 수 없습니다."
    
    def _prepare_v4_parameters(self):
        """V4 API에 필요한 파라미터 구조로 변환"""
        logger.debug("=== _prepare_v4_parameters 메서드 호출됨 ===")
        logger.info("📍 _prepare_v4_parameters 메서드 시작")
        
        # 내부 파라미터 처리 - use_character_coords 값 저장 후 제거
        use_coords = self.parameters.get("use_character_coords", False)
        logger.info(f"📍 원본 use_character_coords: {use_coords}")
        if "use_character_coords" in self.parameters:
            del self.parameters["use_character_coords"]

        # Legacy 모드 확인
        legacy_mode = bool(self.parameters.get("legacy", False))
        logger.debug(f"📍 Legacy 모드: {legacy_mode}")
        
        # V4 프롬프트 형식 설정
        self.parameters["v4_prompt"] = {
            "caption": {
                "base_caption": self.parameters["prompt"],
                "char_captions": []
            },
            "use_coords": use_coords,
            "use_order": True,
            "legacy_format": legacy_mode
        }
        
        # V4 네거티브 프롬프트 형식 설정
        self.parameters["v4_negative_prompt"] = {
            "caption": {
                "base_caption": self.parameters["negative_prompt"],
                "char_captions": []
            },
            "use_coords": False,
            "use_order": False,
            "legacy_uc": legacy_mode
        }
        
        logger.debug(f"📍 v4_prompt 초기 구조 생성 완료 - use_coords: {use_coords}")
        
        # 캐릭터 프롬프트 처리
        if self.parameters.get("characterPrompts") and len(self.parameters["characterPrompts"]) > 0:
            char_prompts = self.parameters["characterPrompts"]
            logger.info(f"📍 캐릭터 프롬프트 처리 시작: {len(char_prompts)}개")
            
            for i, char in enumerate(char_prompts):
                if isinstance(char, dict) and "prompt" in char:
                    char_caption = {
                        "char_caption": char["prompt"],
                        "centers": [{"x": 0.5, "y": 0.5}]  # 기본 중앙 위치
                    }
                    
                    logger.debug(f"📍 캐릭터 {i+1} 프롬프트: '{char['prompt'][:50]}...'")
                    
                    # 위치 정보 처리
                    if use_coords and "position" in char and char["position"]:
                        position = char["position"]
                        logger.debug(f"📍 캐릭터 {i+1} 원본 위치 데이터: {position}, 타입: {type(position)}")
                        
                        if isinstance(position, (tuple, list)) and len(position) >= 2:
                            try:
                                position_x = float(position[0])
                                position_y = float(position[1])
                                char_caption["centers"] = [{"x": position_x, "y": position_y}]
                                logger.info(f"📍 캐릭터 {i+1} 커스텀 위치 적용: x={position_x}, y={position_y}")
                            except Exception as e:
                                logger.error(f"📍 캐릭터 {i+1} 위치 변환 실패: {e}")
                                logger.debug(f"📍 원본 위치 데이터 상세: {position}")
                    else:
                        logger.debug(f"📍 캐릭터 {i+1} 기본 중앙 위치 사용 (use_coords={use_coords})")
                    
                    # 캐릭터 프롬프트 추가
                    self.parameters["v4_prompt"]["caption"]["char_captions"].append(char_caption)
                    logger.debug(f"📍 캐릭터 {i+1} v4_prompt에 추가됨: {char_caption}")
                    
                    # 네거티브 프롬프트
                    neg_caption = {
                        "char_caption": char.get("negative_prompt", ""),
                        "centers": char_caption["centers"]
                    }
                    self.parameters["v4_negative_prompt"]["caption"]["char_captions"].append(neg_caption)
            
            logger.info(f"📍 캐릭터 프롬프트 처리 완료 - 총 {len(self.parameters['v4_prompt']['caption']['char_captions'])}개 변환됨")
            
            # 최종 v4_prompt 구조 로깅
            logger.debug(f"📍 최종 v4_prompt 구조:")
            logger.debug(f"  - use_coords: {self.parameters['v4_prompt']['use_coords']}")
            logger.debug(f"  - 캐릭터 수: {len(self.parameters['v4_prompt']['caption']['char_captions'])}")
            for i, char_cap in enumerate(self.parameters['v4_prompt']['caption']['char_captions']):
                logger.debug(f"  - 캐릭터 {i+1}: centers={char_cap['centers']}")
        else:
            logger.debug("📍 캐릭터 프롬프트 없음 - 기본 프롬프트만 사용")

        # Character Reference 처리 (캐릭터 프롬프트 처리 이후에 추가)
        if (self.parameters.get("reference_image_multiple") and 
            len(self.parameters["reference_image_multiple"]) > 0):
            
            logger.info("📍 Character Reference 데이터 처리 중")
            
            # *** 기존 단일 reference 파라미터 제거 (충돌 방지) ***
            if "reference_image" in self.parameters:
                del self.parameters["reference_image"]
            if "reference_strength" in self.parameters:
                del self.parameters["reference_strength"]
            if "reference_information_extracted" in self.parameters:
                del self.parameters["reference_information_extracted"]
            
            # Character Reference는 director_reference_* 파라미터 사용
            ref_images = self.parameters["reference_image_multiple"]
            ref_info_extracted_input = self.parameters.get("reference_information_extracted_multiple", [1])
            ref_strength = self.parameters.get("reference_strength_multiple", [1])
            
            # Style Aware 설정 확인 (base_caption 결정용)
            style_aware = ref_info_extracted_input[0] == 1
            
            # API 요구사항: director_reference_information_extracted는 항상 [1]이어야 함
            ref_info_extracted = [1]
            
            # Style Aware는 base_caption으로 제어
            if style_aware:
                descriptions = [{
                    "caption": {
                        "base_caption": "character&style",
                        "char_captions": []
                    },
                    "legacy_uc": False
                }]
            else:
                descriptions = [{
                    "caption": {
                        "base_caption": "character",
                        "char_captions": []
                    },
                    "legacy_uc": False
                }]
            
            # Fidelity 값 추출
            ref_fidelity = self.parameters.get("reference_fidelity_multiple", [1.0])
            
            # director_reference_* 파라미터 설정
            self.parameters["director_reference_descriptions"] = descriptions
            self.parameters["director_reference_images"] = ref_images
            self.parameters["director_reference_information_extracted"] = ref_info_extracted  # 항상 [1]
            self.parameters["director_reference_strength_values"] = ref_strength
            self.parameters["director_reference_secondary_strength_values"] = ref_fidelity  # Fidelity 추가
            
            # reference_*_multiple 파라미터는 제거 (director_reference_*와 중복 방지)
            del self.parameters["reference_image_multiple"]
            del self.parameters["reference_information_extracted_multiple"]
            del self.parameters["reference_strength_multiple"]
            if "reference_fidelity_multiple" in self.parameters:
                del self.parameters["reference_fidelity_multiple"]
            
            # 디버깅 로깅
            logger.info(f"📍 director_reference_descriptions: {descriptions}")
            logger.info(f"📍 director_reference_images 개수: {len(ref_images)}")
            logger.info(f"📍 director_reference_images[0] 길이: {len(ref_images[0]) if ref_images else 0}")
            logger.info(f"📍 director_reference_information_extracted: {ref_info_extracted}")
            logger.info(f"📍 director_reference_strength_values: {ref_strength}")
            logger.info(f"📍 director_reference_secondary_strength_values (Fidelity): {ref_fidelity}")
            logger.info(f"📍 Character Reference 적용 완료 - Style Aware: {style_aware}, Fidelity: {ref_fidelity[0]}")
        else:
            # Character Reference가 없을 때 모든 director_reference_* 파라미터 명시적으로 제거
            self.parameters.pop("director_reference_descriptions", None)
            self.parameters.pop("director_reference_images", None)
            self.parameters.pop("director_reference_information_extracted", None)
            self.parameters.pop("director_reference_strength_values", None)
            self.parameters.pop("director_reference_secondary_strength_values", None)
            
            # reference_*_multiple 파라미터도 제거
            self.parameters.pop("reference_image_multiple", None)
            self.parameters.pop("reference_information_extracted_multiple", None)
            self.parameters.pop("reference_strength_multiple", None)
            self.parameters.pop("reference_fidelity_multiple", None)
            
            logger.info("📍 Character Reference 없음 - 모든 director_reference_* 파라미터 제거됨")

        logger.info("📍 _prepare_v4_parameters 메서드 완료")
                        
    def check_logged_in(self):
        """더 나은 오류 처리를 포함한 로그인 확인"""
        if not self.access_token:
            return False
            
        try:
            response = requests.get(
                BASE_URL_DEPRE + "/user/information", 
                headers={"Authorization": f"Bearer {self.access_token}"}, 
                timeout=5
            )
            
            if response.status_code == 200:
                # 성공 - 토큰 수명 예상치 업데이트
                if hasattr(self, '_last_successful_check'):
                    elapsed = time.time() - self._last_successful_check
                    # 토큰 수명 예상치 점진적 조정
                    self._estimated_token_lifetime = (self._estimated_token_lifetime * 0.9) + (elapsed * 0.1)
                
                self._last_successful_check = time.time()
                return True
                
            elif response.status_code == 401:
                # 인증 오류 - 토큰 만료
                logging.info("토큰이 더 이상 유효하지 않음")
                return False
                
            elif response.status_code >= 500:
                # 서버 오류 - 토큰은 여전히 유효하다고 가정
                logging.warning(f"토큰 상태 확인 중 서버 오류: {response.status_code}")
                return True
                
            else:
                logging.warning(f"토큰 확인 중 예상치 못한 응답: {response.status_code}")
                return False
                
        except requests.exceptions.Timeout:
            logging.warning("로그인 상태 확인 시간 초과")
            return True  # 시간 초과 시 여전히 유효하다고 가정
            
        except requests.exceptions.ConnectionError:
            logging.error("로그인 상태 확인 중 네트워크 오류")
            return True  # 네트워크 오류 시 여전히 유효하다고 가정
            
        except Exception as e:
            logging.error(f"로그인 상태 확인 오류: {e}")
            return False

