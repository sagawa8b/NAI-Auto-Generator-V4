"""
gui_credentials.py - 인증 정보 보안 저장/로드

OS Keyring을 우선 사용하고, 사용 불가 시 QSettings로 fallback.
"""

from logger import get_logger
logger = get_logger()

_SERVICE = "NAI-Auto-Generator"

try:
    import keyring
    import keyring.errors
    _KEYRING_OK = True
except Exception:
    _KEYRING_OK = False
    logger.warning("keyring 모듈 없음 - QSettings fallback 사용")


def save_credential(key: str, value: str | None, settings=None) -> None:
    """민감 정보를 OS Keyring에 저장한다. 실패 시 QSettings에 fallback."""
    if not value:
        delete_credential(key, settings)
        return
    if _KEYRING_OK:
        try:
            keyring.set_password(_SERVICE, key, value)
            if settings is not None:
                settings.remove(key)
            return
        except Exception as e:
            logger.warning(f"keyring 저장 실패 ({key}): {e} - QSettings fallback")
    if settings is not None:
        settings.setValue(key, value)


def load_credential(key: str, settings=None) -> str:
    """OS Keyring에서 민감 정보를 읽는다. 없으면 QSettings fallback."""
    if _KEYRING_OK:
        try:
            val = keyring.get_password(_SERVICE, key)
            if val is not None:
                return val
        except Exception as e:
            logger.warning(f"keyring 읽기 실패 ({key}): {e} - QSettings fallback")
    if settings is not None:
        return settings.value(key, "") or ""
    return ""


def delete_credential(key: str, settings=None) -> None:
    """저장된 인증 정보를 삭제한다."""
    if _KEYRING_OK:
        try:
            keyring.delete_password(_SERVICE, key)
        except Exception:
            pass
    if settings is not None:
        settings.remove(key)
