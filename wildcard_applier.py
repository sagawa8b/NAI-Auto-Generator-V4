import os
import random
from enum import Enum

MAX_TRY_AMOUNT = 10



class WildcardApplier():
    def __init__(self, src_wildcards_folder):
        self.src_wildcards_folder = src_wildcards_folder
        self._wildcards_dict = {}
        # 루프카드 인덱스 관리 딕셔너리 추가
        self._loopcard_indices = {}
        # 반복 카운터 추가 - 각 와일드카드별로 현재 반복 횟수 추적
        self._repeat_counters = {}  # {'wildcard_name': {'current': 0, 'target': 2}}
        self._current_snapshot = {}
        self._used_keys = set()
        
    def set_src(self, src):
        # Windows에서는 백슬래시 사용하도록 정규화
        if os.name == 'nt':
            src = os.path.normpath(src)
        self.src_wildcards_folder = src

    def load_wildcards(self):
        self._wildcards_dict.clear()
        
        # 와일드카드 폴더가 존재하는지 확인
        if not os.path.exists(self.src_wildcards_folder):
            print(f"Warning: Wildcards folder not found: {self.src_wildcards_folder}")
            return
        
        wildcard_count = 0
        
        try:
            for dirpath, dname_list, fname_list in os.walk(self.src_wildcards_folder):
                path = ""  # path for wildcards
                path = dirpath.replace(self.src_wildcards_folder, "")
                
                # Windows와 Unix 스타일 경로 모두 처리
                if os.name == 'nt':
                    path = path.replace('\\', '/')  # 내부 처리용으로는 슬래시로 통일
                else:
                    path = path.replace("\\", "/")
                    
                path = path + "/"
                path = path[1:] if path.startswith("/") else path

                for filename in fname_list:
                    if filename.endswith(".txt"):
                        src = os.path.join(dirpath, filename)
                        try:
                            with open(src, "r", encoding="utf8") as f:
                                lines = f.readlines()
                                if lines:
                                    onlyname = os.path.splitext(
                                        os.path.basename(filename))[0]
                                    key = path + onlyname
                                    # 빈 줄과 주석 제거
                                    valid_lines = [line.strip() for line in lines if line.strip() and not line.strip().startswith('#')]
                                    if valid_lines:
                                        self._wildcards_dict[key.lower()] = valid_lines
                                        wildcard_count += 1
                        except Exception as e:
                            print(f"Error loading wildcard file {src}: {e}")
            
            print(f"Loaded {wildcard_count} wildcards from {self.src_wildcards_folder}")
            
        except Exception as e:
            print(f"Error loading wildcards: {e}")

    def create_index_snapshot(self):
        """현재 루프카드 인덱스의 스냅샷 생성"""
        self._current_snapshot = self._loopcard_indices.copy()
        self._used_keys = set()

    def apply_wildcards_with_snapshot(self, target_str):
        """스냅샷된 인덱스를 사용하여 와일드카드 적용 (인덱스 증가 안함)"""
        self.load_wildcards()
        result = target_str
        
        # 루프카드 적용 (스냅샷 사용)
        index = 0
        except_list = []
        while True:
            result, applied_list = self._apply_loopcard_once_with_snapshot(result, except_list)
            except_list.extend(applied_list)
            if len(applied_list) == 0 or index > MAX_TRY_AMOUNT:
                break
            index += 1
        
        # 일반 와일드카드 적용
        index = 0
        except_list = []
        while True:
            result, applied_list = self._apply_wildcard_once(result, except_list)
            except_list.extend(applied_list)
            if len(applied_list) == 0 or index > MAX_TRY_AMOUNT:
                break
            index += 1
        
        return result
   
    def advance_loopcard_indices(self):
        """사용된 루프카드 인덱스만 다음으로 진행"""
        for key in self._used_keys:  # 실제 사용된 키만
            if key in self._wildcards_dict:
                wc_list = self._wildcards_dict[key]
                if wc_list:
                    if key not in self._loopcard_indices:
                        self._loopcard_indices[key] = 0
                    self._loopcard_indices[key] = (self._loopcard_indices[key] + 1) % len(wc_list)
        
        # 사용된 키 리셋
        self._used_keys.clear()

    def _apply_wildcard_once(self, target_str, except_list=[]):
        result = target_str

        applied_wildcard_list = []
        prev_point = 0
        
        # __ 형식으로 와일드카드 검색
        while "__" in result:
            p_left = result.find("__", prev_point)
            if p_left == -1:
                break

            p_right = result.find("__", p_left + 2)  # +2로 두 번째 __ 찾기
            if p_right == -1:
                print("Warning: A single __ exists")
                break

            str_left = result[0:p_left]
            str_center = result[p_left + 2:p_right].lower()
            str_right = result[p_right + 2:len(result)]

            if str_center in self._wildcards_dict and not (str_center in except_list):
                wc_list = self._wildcards_dict[str_center]
                if wc_list:  # 비어있지 않은지 확인
                    str_center = wc_list[random.randrange(0, len(wc_list))].strip()
                    applied_wildcard_list.append(str_center)
                else:
                    print(f"Warning: Wildcard '{str_center}' has no entries")
                    str_center = "__" + str_center + "__"
            else:
                print(f"Warning: Unknown wildcard '{str_center}'")
                str_center = "__" + str_center + "__"

            result_left = str_left + str_center
            prev_point = len(result_left)
            result = result_left + str_right

        return result, applied_wildcard_list
    
    def _apply_loopcard_once(self, target_str, except_list=[]):
        """루프카드 (순차 적용) 처리 - 순차 반복 기능 추가"""
        result = target_str
        applied_loopcard_list = []
        prev_point = 0
        
        # ## 루프카드 ## 형식 검색
        while "##" in result:
            p_left = result.find("##", prev_point)
            if p_left == -1:
                break

            p_right = result.find("##", p_left + 2)
            if p_right == -1:
                break

            str_left = result[0:p_left]
            str_center = result[p_left + 2:p_right].lower().strip()
            str_right = result[p_right + 2:len(result)]

            # 순차 반복 와일드카드 패턴 확인: wildcard_name*repeat_count
            repeat_count = 1  # 기본값
            wildcard_name = str_center
            
            # *숫자 패턴 확인
            if '*' in str_center:
                parts = str_center.split('*')
                if len(parts) == 2 and parts[0] and parts[1]:
                    try:
                        repeat_count = int(parts[1])
                        wildcard_name = parts[0]
                        if repeat_count <= 0:
                            raise ValueError("반복 횟수는 양수여야 합니다")
                    except ValueError:
                        # 잘못된 형식이면 원본 구문 그대로 유지
                        str_center = "##" + str_center + "##"
                        result_left = str_left + str_center
                        prev_point = len(result_left)
                        result = result_left + str_right
                        continue

            if wildcard_name in self._wildcards_dict and not (wildcard_name in except_list):
                wc_list = self._wildcards_dict[wildcard_name]
                if wc_list:
                    # 반복 카운터 초기화
                    counter_key = f"{wildcard_name}*{repeat_count}"
                    if counter_key not in self._repeat_counters:
                        self._repeat_counters[counter_key] = {'current': 0, 'target': repeat_count}
                    
                    # 인덱스 관리
                    if wildcard_name not in self._loopcard_indices:
                        self._loopcard_indices[wildcard_name] = 0
                    
                    idx = self._loopcard_indices[wildcard_name]
                    selected_line = wc_list[idx].strip()
                    
                    # 단일 캐릭터만 사용 (반복 없이)
                    str_center = selected_line
                    
                    # 반복 카운터 증가
                    self._repeat_counters[counter_key]['current'] += 1
                    
                    # 목표 반복 횟수에 도달하면 다음 캐릭터로 이동
                    if self._repeat_counters[counter_key]['current'] >= repeat_count:
                        self._loopcard_indices[wildcard_name] = (idx + 1) % len(wc_list)
                        self._repeat_counters[counter_key]['current'] = 0  # 카운터 리셋
                    
                    applied_loopcard_list.append(str_center)
                else:
                    str_center = "##" + str_center + "##"
            else:
                str_center = "##" + str_center + "##"

            result_left = str_left + str_center
            prev_point = len(result_left)
            result = result_left + str_right

        return result, applied_loopcard_list
        
    def _apply_loopcard_once_with_snapshot(self, target_str, except_list=[]):
        """스냅샷된 인덱스를 사용한 루프카드 처리 - 순차 반복 기능 추가"""
        result = target_str
        applied_loopcard_list = []
        prev_point = 0
        
        while "##" in result:
            p_left = result.find("##", prev_point)
            if p_left == -1:
                break
            p_right = result.find("##", p_left + 2)
            if p_right == -1:
                break

            str_left = result[0:p_left]
            str_center = result[p_left + 2:p_right].lower().strip()
            str_right = result[p_right + 2:len(result)]

            # 순차 반복 와일드카드 패턴 확인: wildcard_name*repeat_count
            repeat_count = 1  # 기본값
            wildcard_name = str_center
            
            # *숫자 패턴 확인
            if '*' in str_center:
                parts = str_center.split('*')
                if len(parts) == 2 and parts[0] and parts[1]:
                    try:
                        repeat_count = int(parts[1])
                        wildcard_name = parts[0]
                        if repeat_count <= 0:
                            raise ValueError("반복 횟수는 양수여야 합니다")
                    except ValueError:
                        # 잘못된 형식이면 원본 구문 그대로 유지
                        str_center = "##" + str_center + "##"
                        result_left = str_left + str_center
                        prev_point = len(result_left)
                        result = result_left + str_right
                        continue

            if wildcard_name in self._wildcards_dict and not (wildcard_name in except_list):
                wc_list = self._wildcards_dict[wildcard_name]
                if wc_list:
                    # 키 사용 기록
                    self._used_keys.add(wildcard_name)
                    
                    # 스냅샷에서 인덱스 가져오기
                    idx = self._current_snapshot.get(wildcard_name, 0)
                    selected_line = wc_list[idx].strip()
                    
                    # 단일 캐릭터만 사용 (스냅샷에서는 반복 없이)
                    str_center = selected_line
                    applied_loopcard_list.append(str_center)
                else:
                    str_center = "##" + str_center + "##"
            else:
                str_center = "##" + str_center + "##"

            result_left = str_left + str_center
            prev_point = len(result_left)
            result = result_left + str_right

        return result, applied_loopcard_list
    
    def apply_wildcards(self, target_str):
        """와일드카드와 루프카드 모두 적용"""
        self.load_wildcards()

        result = target_str
        
        # 1. 먼저 루프카드(순차) 적용
        index = 0
        except_list = []
        while True:
            result, applied_loopcard_list = self._apply_loopcard_once(result, except_list)
            except_list.extend(applied_loopcard_list)
            
            if len(applied_loopcard_list) == 0:
                break
                
            index += 1
            if index > MAX_TRY_AMOUNT:
                print("Warning: Too much recursion in loopcards")
                break
        
        # 2. 와일드카드(랜덤) 적용
        index = 0
        except_list = []
        while True:
            result, applied_wildcard_list = self._apply_wildcard_once(result, except_list)
            except_list.extend(applied_wildcard_list)
            
            if len(applied_wildcard_list) == 0:
                break
                
            index += 1
            if index > MAX_TRY_AMOUNT:
                print("Warning: Too much recursion in wildcards")
                break
                
        return result
    
    
