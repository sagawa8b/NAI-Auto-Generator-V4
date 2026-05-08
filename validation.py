"""
validation.py - 생성 파라미터 입력 검증 (GUI 의존성 없음)

gui_utils.py 및 테스트 코드에서 import 가능
"""


def validate_generation_params(data: dict) -> list[str]:
    """생성 파라미터를 검증하고 범위 외 목록을 반환한다.

    Returns:
        list[str]: 오류 범위 외 목록. 빈 리스트이면 검증 통과.
    """
    errors: list[str] = []

    # width
    try:
        w = int(data.get("width", 0))
        if not (64 <= w <= 2048):
            errors.append("validation.width_invalid")
    except (ValueError, TypeError):
        errors.append("validation.width_invalid")

    # height
    try:
        h = int(data.get("height", 0))
        if not (64 <= h <= 2048):
            errors.append("validation.height_invalid")
    except (ValueError, TypeError):
        errors.append("validation.height_invalid")

    # steps
    try:
        s = int(data.get("steps", 0))
        if not (1 <= s <= 50):
            errors.append("validation.steps_invalid")
    except (ValueError, TypeError):
        errors.append("validation.steps_invalid")

    # seed: -1 = random, otherwise 0 ~ 2^32-1
    try:
        seed = int(data.get("seed", -1))
        if not (seed == -1 or 0 <= seed <= 4294967295):
            errors.append("validation.seed_invalid")
    except (ValueError, TypeError):
        errors.append("validation.seed_invalid")

    # scale (CFG)
    try:
        scale = float(data.get("scale", 0))
        if scale <= 0:
            errors.append("validation.scale_invalid")
    except (ValueError, TypeError):
        errors.append("validation.scale_invalid")

    return errors


def translate_validation_errors(error_keys: list[str]) -> list[str]:
    """범위 외 사용자 언어 문자열로 변환한다"""
    try:
        from i18n_manager import tr
        return [tr(k) for k in error_keys]
    except ImportError:
        return error_keys
