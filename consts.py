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
        # noise_schedule는 실제 값이 있으면 표시, 없으면 표시하지 않음
        sampler_display = d.get('sampler', '')
        if 'noise_schedule' in d:
            sampler_display = f"{sampler_display} ({d['noise_schedule']})"

        separator = "="*60
        subseparator = "-"*60

        result = f"""{separator}
GENERATION RESULT
{separator}

Prompt:
{d.get('prompt', '')}

Undesired Content:
{d.get('negative_prompt', '')}
"""

        # 캐릭터 프롬프트가 있는 경우 추가 정보
        if 'characterPrompts' in d and d['characterPrompts']:
            result += f"""
{subseparator}
Character Prompts (V4)
{subseparator}

"""
            for i, char in enumerate(d['characterPrompts']):
                if isinstance(char, dict):
                    result += f"[Character {i+1}]\n"
                    result += f"  Prompt: {char.get('prompt', 'No information')}\n"
                    if 'negative_prompt' in char and char['negative_prompt'].strip():
                        result += f"  Negative: {char['negative_prompt']}\n"

                    # 위치 정보 표시 (수동 설정 또는 AI 자동)
                    if 'position' in char and isinstance(char['position'], (list, tuple)) and len(char['position']) == 2:
                        result += f"  Position: ({char['position'][0]:.2f}, {char['position'][1]:.2f}) [Manual]\n"
                    else:
                        # v4_prompt에서 실제 사용된 위치 정보 가져오기
                        if 'v4_prompt' in d and 'caption' in d['v4_prompt']:
                            char_captions = d['v4_prompt']['caption'].get('char_captions', [])
                            if i < len(char_captions) and 'centers' in char_captions[i]:
                                centers = char_captions[i]['centers'][0]
                                result += f"  Position: ({centers['x']:.2f}, {centers['y']:.2f}) [AI's choice]\n"
                            else:
                                result += f"  Position: AI's choice\n"
                        else:
                            result += f"  Position: AI's choice\n"
                    result += "\n"

        # 모델 정보 결정 - 실제 모델 ID에서 가져오기
        model_id = d.get('model', '')
        if model_id == "nai-diffusion-4-5-curated":
            model_display_name = "NAI Diffusion V4.5 Curated"
        elif model_id == "nai-diffusion-4-5-full":
            model_display_name = "NAI Diffusion V4.5 Full"
        elif model_id == "nai-diffusion-4-full":
            model_display_name = "NAI Diffusion V4 Full"
        elif model_id:
            model_display_name = model_id  # 알 수 없는 모델은 ID 그대로 표시
        else:
            model_display_name = "Unknown"

        # 기본 정보 - 모든 정보를 하나의 섹션으로 통합
        result += f"""
{subseparator}
Generation Information
{subseparator}
Resolution: {d.get('width', 0)}x{d.get('height', 0)}
Seed: {d.get('seed', 0)}
Steps: {d.get('steps', 0)}
Sampler: {sampler_display}
Prompt Guidance: {d.get('scale', 0)}
Prompt Guidance Rescale: {d.get('cfg_rescale', 0)}
Undesired Content Strength: {d.get('uncond_scale', 0)}

Software: NovelAI
Source: {model_display_name}
Request Type: {'Image to Image' if d.get('image') else 'Text to Image'}
Model Preset: {d.get('v4_model_preset', 'Artistic')}
Legacy Mode: {'Enabled' if d.get('legacy', False) else 'Disabled'}
"""

        # 고급 설정 - 웹 UI에서 제공되는 설정
        if 'noise_schedule' in d:
            result += f"""Noise Schedule: {d['noise_schedule']}
"""

        # 내부 설정 - API 전용 설정 (웹 UI에 없음)
        # 실제 메타데이터에 있는 값만 표시
        has_internal_settings = any(key in d for key in ['sm', 'autoSmea', 'sm_dyn', 'dynamic_thresholding', 'quality_toggle', 'prefer_brownian', 'deliberate_euler_ancestral_bug'])
        if has_internal_settings:
            result += f"""
{subseparator}
Internal API Settings
{subseparator}
(※ Settings not displayed in the web UI may have limited actual effects.)
"""

        # 각 설정 값이 실제로 메타데이터에 있을 때만 표시
        if 'sm' in d or 'autoSmea' in d:
            auto_smea = d.get('autoSmea', d.get('sm', False))
            result += f"Auto SMEA: {'On' if auto_smea else 'Off'} (※)\n"
        if 'sm_dyn' in d:
            result += f"Dynamic SMEA: {'On' if d['sm_dyn'] else 'Off'} (※)\n"
        if 'dynamic_thresholding' in d:
            result += f"Dynamic Thresholding: {'On' if d['dynamic_thresholding'] else 'Off'} (※)\n"
        if 'quality_toggle' in d:
            result += f"Quality Toggle: {'On' if d['quality_toggle'] else 'Off'} (※)\n"
        if 'prefer_brownian' in d:
            result += f"Prefer Brownian Motion: {'On' if d['prefer_brownian'] else 'Off'} (※)\n"
        if 'deliberate_euler_ancestral_bug' in d:
            result += f"Euler Ancestral Bug: {'On' if d['deliberate_euler_ancestral_bug'] else 'Off'} (※)\n"
        
        # 이미지/레퍼런스 이미지가 있는 경우 추가 정보
        if 'image' in d and d['image']:
            img_src = additional_dict.get('image_src', 'Unknown') if additional_dict else 'Unknown'
            img_tags = additional_dict.get('image_tag', '') if additional_dict else ''
            result += f"""
{separator}
Image to Image Settings
{separator}
Image Path: {img_src}
Strength: {d.get('strength', 0.7)}
Noise: {d.get('noise', 0.0)}
"""
            if img_tags:
                result += f"Image Tags: {img_tags}\n"

        if 'reference_image' in d and d['reference_image']:
            ref_src = additional_dict.get('reference_image_src', 'Unknown') if additional_dict else 'Unknown'
            ref_tags = additional_dict.get('reference_image_tag', '') if additional_dict else ''
            result += f"""
{separator}
Reference Image Settings
{separator}
Reference Path: {ref_src}
Strength: {d.get('reference_strength', 0.6)}
Information Extracted: {d.get('reference_information_extracted', 1.0)}
"""
            if ref_tags:
                result += f"Reference Tags: {ref_tags}\n"
        
    except Exception as e:
        result = f"Error processing metadata: {e}"
        
    return result

# 모델 목록 정의 추가
NAI_MODELS = {
    "nai-diffusion-4-full": "NAI Diffusion V4 Full",
    "nai-diffusion-4-5-curated": "NAI Diffusion V4.5 Curated",
    "nai-diffusion-4-5-full": "NAI Diffusion V4.5 Full"
}

# 기본 모델 설정
DEFAULT_MODEL = "nai-diffusion-4-5-full"  # V4.5 Full을 기본값으로 설정



def prettify_dict(d):
    return json.dumps(d, sort_keys=True, indent=4)


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
    "model": "nai-diffusion-4-5-full",  # 추가
    "v4_model_preset": "Artistic",
}

DEFAULT_PATH = {
    "path_results": "./results/",
    "path_settings": "./settings/",
    "path_wildcards": "./wildcards/",
    "path_models": "./models/",
}