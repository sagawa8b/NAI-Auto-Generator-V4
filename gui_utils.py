"""
gui_utils.py - GUI 유틸리티 함수 모음

gui.py에서 분리된 독립적인 헬퍼 함수들.
파일 경로 처리, 문자열 변환, 이미지 변환 등을 담당합니다.
"""

import json
import sys
import os
import io
import random
import base64
from PIL import Image

from PyQt5.QtCore import QBuffer
from PyQt5.QtGui import QImage

from logger import get_logger
logger = get_logger()


MAX_COUNT_FOR_WHILE = 10


def resource_path(relative_path):
    """실행 파일 또는 Python 스크립트에서 리소스 경로 가져오기"""
    try:
        # PyInstaller 번들 실행 시
        base_path = sys._MEIPASS
    except AttributeError:
        # 일반 Python 실행 시
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def create_folder_if_not_exists(foldersrc):
    if not os.path.exists(foldersrc):
        os.makedirs(foldersrc)


def prettify_dict(d):
    return json.dumps(d, sort_keys=True, indent=4)


def get_imgcount_from_foldersrc(foldersrc):
    return len([file for file in os.listdir(foldersrc) if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp'))])


def pick_imgsrc_from_foldersrc(foldersrc, index, sort_order):
    files = [file for file in os.listdir(foldersrc) if file.lower(
    ).endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp'))]

    is_reset = False
    if index != 0 and index % len(files) == 0:
        is_reset = True

    # 파일들을 정렬
    if sort_order == '오름차순':
        files.sort()
    elif sort_order == '내림차순':
        files.sort(reverse=True)
    elif sort_order == '랜덤':
        random.seed(random.randint(0, 1000000))
        random.shuffle(files)
        is_reset = False

    # 인덱스가 파일 개수를 초과하는 경우
    while index >= len(files):
        index -= len(files)

    # 정렬된 파일 리스트에서 인덱스에 해당하는 파일의 주소 반환
    return os.path.join(foldersrc, files[index]), is_reset


def strtobool(val):
    """Convert a string representation of truth to true (1) or false (0).
    True values are 'y', 'yes', 't', 'true', 'on', and '1'; false values
    are 'n', 'no', 'f', 'false', 'off', and '0'.  Raises ValueError if
    'val' is anything else.
    """
    if isinstance(val, bool):
        return val

    val = val.lower()
    if val in ('y', 'yes', 't', 'true', 'on', '1'):
        return True
    elif val in ('n', 'no', 'f', 'false', 'off', '0'):
        return False
    else:
        raise ValueError("invalid truth value %r" % (val,))


def pickedit_lessthan_str(original_str):
    try_count = 0

    edited_str = original_str
    while try_count < MAX_COUNT_FOR_WHILE:
        try_count += 1

        before_edit_str = edited_str
        pos_prev = 0
        while True:
            pos_r = edited_str.find(">", pos_prev + 1)
            if pos_r == -1:
                break

            pos_l = edited_str.rfind("<", pos_prev, pos_r)
            if pos_l != -1:
                left = edited_str[0:pos_l]
                center = edited_str[pos_l + 1:pos_r]
                right = edited_str[pos_r + 1:len(edited_str)]

                center_splited = center.split("|")
                center_picked = center_splited[random.randrange(
                    0, len(center_splited))]

                result_left = left + center_picked
                pos_prev = len(result_left)
                edited_str = result_left + right
            else:
                pos_prev = pos_r

        if before_edit_str == edited_str:
            break

    return edited_str


def create_windows_filepath(base_path, filename, extension, max_length=150):
    # 파일 이름으로 사용할 수 없는 문자 제거
    cleaned_filename = filename.replace("\n", "")
    cleaned_filename = cleaned_filename.replace("\\", "")

    invalid_chars = r'<>:"/\|?*'
    cleaned_filename = ''.join(
        char for char in cleaned_filename if char not in invalid_chars)

    # 파일 이름의 최대 길이 제한 (확장자 길이 고려)
    max_filename_length = max_length - len(base_path) - len(extension) - 1
    if max_filename_length < 5:
        return None
    cleaned_filename = cleaned_filename[:max_filename_length]

    # 경로, 파일 이름, 확장자 합치기
    filepath = os.path.join(base_path, cleaned_filename + extension)

    return filepath


def inject_imagetag(original_str, tagname, additional_str):
    result_str = original_str[:]

    tag_str_left = "@@" + tagname
    left_pos = original_str.find(tag_str_left)
    if left_pos != -1:
        right_pos = original_str.find("@@", left_pos + 1)
        except_tag_list = [x.strip() for x in original_str[left_pos +
                                                           len(tag_str_left) + 1:right_pos].split(",")]
        original_tag_list = [x.strip() for x in additional_str.split(',')]
        target_tag_list = [
            x for x in original_tag_list if x not in except_tag_list]

        result_str = original_str[0:left_pos] + ", ".join(target_tag_list) + \
            original_str[right_pos + 2:len(original_str)]

    return result_str


def get_filename_only(path):
    filename, _ = os.path.splitext(os.path.basename(path))
    return filename


def validate_generation_params(data: dict) -> list[str]:
    """생성 파라미터를 검증하고 번역된 오류 메시지 목록을 반환한다.

    Returns:
        list[str]: 번역된 오류 문자열 목록. 빈 리스트이면 검증 통과.
    """
    from validation import validate_generation_params as _validate
    from validation import translate_validation_errors
    return translate_validation_errors(_validate(data))


def convert_qimage_to_imagedata(qimage):
    try:
        buf = QBuffer()
        buf.open(QBuffer.ReadWrite)
        qimage.save(buf, "PNG")
        pil_im = Image.open(io.BytesIO(buf.data()))

        buf = io.BytesIO()
        pil_im.save(buf, format='png', quality=100)
        return base64.b64encode(buf.getvalue()).decode("utf-8")
    except Exception as e:
        return ""

def validate_generation_params(data: dict) -> list[str]:
    """생성 파라미터를 검증하고 범위 외 오류 메시지 목록을 반환한다.

    Returns:
        list[str]: 범위 외 오류 문자열 목록. 빈 리스트이면 검증 통과.
    """
    from validation import validate_generation_params as _validate
    from validation import translate_validation_errors
    return translate_validation_errors(_validate(data))
