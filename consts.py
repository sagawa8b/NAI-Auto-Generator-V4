import json

COLOR = type('COLOR', (), {
    'BUTTON_CUSTOM': '#559977',
    'BUTTON_AUTOGENERATE': '#D37493',
    'LABEL_SUCCESS': '#559977',
    'LABEL_FAILED': '#D37493',
})

# RESOLUTION_FAMILIY_MASK와 RESOLUTION_FAMILIY 업데이트
RESOLUTION_FAMILIY_MASK = [0, 0, 0, 0, -1]

RESOLUTION_FAMILIY = {
    0: ["Square (1024x1024)", "Portrait (832x1216)", "Landscape (1216x832)"],  # 기본 해상도 모음 (HD 먼저)
    1: ["Square (1472x1472)", "Portrait (1024x1536)", "Landscape (1536x1024)"],  # 더 높은 해상도
    2: ["Portrait (1088x1920)", "Landscape (1920x1088)"],  # 와이드 해상도
    3: ["Square (640x640)", "Portrait (512x768)", "Landscape (768x512)"],  # 작은 해상도
    4: []  # 커스텀을 위한 빈 항목
}

# consts.py 파일에서
DEFAULT_TAGCOMPLETION_PATH = "./danbooru_tags_post_count.csv"  # 상대 경로로 설정


def prettify_naidict(d, additional_dict=None):
    """NovelAI 이미지 메타데이터를 보기 좋게 정렬하여 표시"""
    try:
        # 간략 정보 (Simplified) - NovelAI inspect 페이지와 유사하게
        result = (
            "Simplified\n\n"
            f"Prompt: {d.get('prompt', '')}\n"
            f"Undesired Content: {d.get('negative_prompt', '')}\n"
            f"Resolution: {d.get('width', 0)}x{d.get('height', 0)}\n"
            f"Seed: {d.get('seed', 0)}\n"
            f"Steps: {d.get('steps', 0)}\n"
            f"Sampler: {d.get('sampler', '')} ({d.get('noise_schedule', 'karras')})\n"
            f"Prompt Guidance: {d.get('scale', 0)}\n"
            f"Prompt Guidance Rescale: {d.get('cfg_rescale', 0)}\n"
            f"Undesired Content Strength: {d.get('uncond_scale', 0)}\n"
        )
        
        # 모델 정보 결정
        model_id = d.get('model', 'nai-diffusion-4-5-curated')
        model_display_name = "NAI Diffusion V4 Full"
        
        if model_id == "nai-diffusion-4-5-curated":
            model_display_name = "NAI Diffusion V4.5 Curated"
        elif model_id == "nai-diffusion-4-full":
            model_display_name = "NAI Diffusion V4 Full"
        
        # 기본 정보
        result += (
            "\nGeneration Information\n\n"
            f"Software: NovelAI\n"
            f"Source: {model_display_name}\n"
            f"Request Type: {'Image to Image' if d.get('image') else 'Text to Image'}\n"
            f"Model Preset: {d.get('v4_model_preset', 'Artistic')}\n"
            f"Legacy Mode: {'Enabled' if d.get('legacy', False) else 'Disabled'}\n"
        )
        
        # 고급 설정 - 웹 UI에서 제공되는 설정
        result += (
            "\nWeb UI Settings\n"
            f"Noise Schedule: {d.get('noise_schedule', 'karras')}\n"
        )
        
        # 내부 설정 - API 전용 설정 (웹 UI에 없음)
        result += (
            "\nInternal API Settings\n"
            f"(※ 웹 UI에 표시되지 않는 설정으로, 실제 효과는 제한될 수 있습니다.)\n"
            f"Auto SMEA: {'On' if d.get('autoSmea', False) or d.get('sm', False) else 'Off'} (※)\n"
            f"Dynamic SMEA: {'On' if d.get('sm_dyn', False) else 'Off'} (※)\n"
            f"Dynamic Thresholding: {'On' if d.get('dynamic_thresholding', False) else 'Off'} (※)\n"
            f"Quality Toggle: {'On' if d.get('quality_toggle', True) else 'Off'} (※)\n"
            f"Prefer Brownian Motion: {'On' if d.get('prefer_brownian', True) else 'Off'} (※)\n"
            f"Euler Ancestral Bug: {'On' if d.get('deliberate_euler_ancestral_bug', True) else 'Off'} (※)\n"
            
        )
        
        # 캐릭터 프롬프트가 있는 경우 추가 정보
        if 'characterPrompts' in d and d['characterPrompts']:
            result += "\nCharacter Prompts\n\n"
            for i, char in enumerate(d['characterPrompts']):
                if isinstance(char, dict):
                    result += f"Character {i+1}: {char.get('prompt', 'No information')}\n"
                    if 'negative_prompt' in char and char['negative_prompt'].strip():
                        result += f"  Negative: {char['negative_prompt']}\n"
                    if 'position' in char:
                        result += f"  Position: ({char['position'][0]:.2f}, {char['position'][1]:.2f})\n"
        
        # 이미지/레퍼런스 이미지가 있는 경우 추가 정보
        if 'image' in d and d['image']:
            result += "\nImage to Image Settings\n\n"
            result += f"Image Path: {additional_dict.get('image_src', 'Unknown') if additional_dict else 'Unknown'}\n"
            result += f"Strength: {d.get('strength', 0.7)}\n"
            result += f"Noise: {d.get('noise', 0.0)}\n"
            if additional_dict and 'image_tag' in additional_dict:
                result += f"Image Tags: {additional_dict['image_tag']}\n"

        if 'reference_image' in d and d['reference_image']:
            result += "\nReference Image Settings\n\n"
            result += f"Reference Path: {additional_dict.get('reference_image_src', 'Unknown') if additional_dict else 'Unknown'}\n"
            result += f"Strength: {d.get('reference_strength', 0.6)}\n"
            result += f"Information Extracted: {d.get('reference_information_extracted', 1.0)}\n"
            if additional_dict and 'reference_image_tag' in additional_dict:
                result += f"Reference Tags: {additional_dict['reference_image_tag']}\n"
        
    except Exception as e:
        result = f"Error processing metadata: {e}"
        
    return result

# 모델 목록 정의 추가
NAI_MODELS = {
    "nai-diffusion-4-full": "NAI Diffusion V4 Full",
    "nai-diffusion-4-5-curated": "NAI Diffusion V4.5 Curated"
}

# 기본 모델 설정
DEFAULT_MODEL = "nai-diffusion-4-5-curated"  # V4.5 Curated를 기본값으로 설정



def prettify_dict(d):
    return json.dumps(d, sort_keys=True, indent=4)


class S:
    LIST_STATSUBAR_STATE = {
        "BEFORE_LOGIN": "로그인이 필요합니다.",
        "LOGINED": "로그인 완료. 이제 생성이 가능합니다.",
        "LOGGINGIN": "로그인 중...",
        "GENERATING": "이미지를 생성하는 중...",
        "IDLE": "대기 중",
        "LOAD_COMPLETE": "파일 로드 완료",
        "LOADING": "로드 중...",
        "AUTO_GENERATING_COUNT": "연속 생성 중 ({}/{})",
        "AUTO_GENERATING_INF": "연속 생성 중",
        "AUTO_WAIT": "다음 생성 대기 중... ({}초)",
        "AUTO_ERROR_WAIT": "에러 발생. {}초 후 재시도...",
    }

    ABOUT = """NAI Auto Generator v4
    version 1.5.5.12a

본진 : 
  아카라이브 AI그림 채널 https://arca.live/b/aiart
  
원 제작자 : 
  https://arca.live/b/aiart @DCP

v4 업데이트 :
 sagawa
  
크레딧 :
  https://huggingface.co/baqu2213
  https://github.com/neggles/sd-webui-stealth-pnginfo/  
  https://github.com/DCP-arca/NAI-Auto-Generator

Notice : "본 앱은 제3자가 개발한 앱으로 Novel AI 또는 Stability AI에서 개발하거나 관리하지 않으며, 이들 회사와는 무관합니다."

="This app is a third-party app that is not developed or managed by Novel AI or Stability AI and is unaffiliated with those companies."


"""


# 기본 파라미터 수정
DEFAULT_PARAMS = {
    "prompt": "",
    "negative_prompt": "",
    "width": "1024",  # 기본값을 HD로 변경
    "height": "1024",  # 기본값을 HD로 변경
    "steps": "28",
    "sampler": "k_euler_ancestral",
    "seed": "-1",
    "scale": "5.0",    
    "cfg_rescale": "0",
    "autoSmea": "True",  # 유지 (호환성)
    "noise_schedule": "karras",
    "legacy": "False",
    "quality_toggle": "True",  # 내부적으로 사용
    "strength": "0.7",
    "noise": "0.0",
    "reference_information_extracted": "1.0",
    "reference_strength": "0.6",
    "v4_model_preset": "Artistic",
    "anti_artifacts": "0.0",
    "skip_cfg_above_sigma": "null",
    "variety_plus": "False",  # 기본값 False로 설정
}

DEFAULT_PATH = {
    "path_results": "./results/",
    "path_settings": "./settings/",
    "path_wildcards": "./wildcards/",
    "path_models": "./models/",
}