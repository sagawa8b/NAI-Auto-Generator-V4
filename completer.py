import re
from PyQt5.QtWidgets import QCompleter, QTextEdit
from PyQt5.QtGui import QTextCursor, QTextCharFormat, QFont, QColor
from PyQt5.QtCore import Qt, QStringListModel
import string

from logger import get_logger
logger = get_logger()

# complete_target_stringset = string.ascii_letters + string.digits + "~!#$%^&*_+?.-="


class CustomCompleter(QCompleter):
    def __init__(self, words, parent=None):
        logger.debug(f"CustomCompleter 초기화: {len(words)}개 단어")
        super().__init__(words, parent)
        self.words = words
        self.setCaseSensitivity(Qt.CaseInsensitive)
        self.setFilterMode(Qt.MatchContains)
        self.model = QStringListModel(words, self)
        self.setModel(self.model)

    def setCompletionPrefix(self, prefix):
        self.prefix = prefix
        
        # 최소 2글자 이상부터 검색 (성능 향상)
        if len(prefix) < 2:
            self.model.setStringList([])
            super().setCompletionPrefix(prefix)
            return
            
        is_add_mode = len(self.prefix) > 3
        prefix_lower = self.prefix.lower()
        filtered_words = []
        contains_matches = []

        # 전체 태그 검색 (조기 중단 최적화로 성능 보장)
        for i in range(len(self.words)):
            word = self.words[i]
            word_lower = word.lower()
            if word_lower.startswith(prefix_lower):
                filtered_words.append(word)
                # 시작 일치 항목이 일정 수 이상이면 중단
                if len(filtered_words) > 50:
                    break
            elif is_add_mode and prefix_lower in word_lower:
                contains_matches.append(word)
                # 포함 일치 항목이 일정 수 이상이면 중단
                if len(contains_matches) > 50:
                    break

        # 최대 표시 항목 제한
        if is_add_mode:
            filtered_words.extend(sorted(contains_matches)[:50])
        
        # 목록 업데이트
        self.model.setStringList(filtered_words)
        super().setCompletionPrefix(prefix)
        self.complete()


class CompletionTextEdit(QTextEdit):
    def __init__(self, enable_image_drop=True):
        logger.debug("CompletionTextEdit 초기화")
        super().__init__()
        self.completer = None
        # 중요: textChanged 시그널이 highlightSyntax에 연결되어야 함 (highlightBrackets 대신)
        self.textChanged.connect(self.highlightSyntax)

        # 가중치 하이라이트 설정
        self.highlight_emphasis = True
        self.emphasis_colors = {
            "high": QColor(100, 149, 237),  # 강조(>1.0) - 진한 파란색
            "normal": QColor(0, 0, 0),      # 일반 텍스트 - 검정색
            "low": QColor(169, 169, 169),   # 약화(<1.0) - 회색
            "bracket_unmatched": QColor(255, 0, 0)  # 매치되지 않은 괄호 - 빨간색
        }

        # 이미지 드래그 앤 드롭 설정
        self.enable_image_drop = enable_image_drop
        # 이미지 드롭이 비활성화된 경우 드래그 앤 드롭 비활성화
        self.setAcceptDrops(enable_image_drop)

    def dragEnterEvent(self, event):
        """드래그 진입 이벤트 - 이미지 파일을 수락"""
        # 이미지 드롭이 비활성화된 경우 기본 동작만 수행
        if not self.enable_image_drop:
            super().dragEnterEvent(event)
            return

        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if len(urls) == 1:
                file_path = urls[0].toLocalFile()
                # NovelAI 이미지 파일만 수락 (PNG, WebP)
                if file_path.lower().endswith(('.png', '.webp')):
                    event.acceptProposedAction()
                    logger.debug(f"Drag enter accepted for: {file_path}")
                    return
        # 이미지가 아니면 기본 텍스트 드래그 앤 드롭 처리
        super().dragEnterEvent(event)

    def dropEvent(self, event):
        """드롭 이벤트 - NovelAI 이미지의 메타데이터를 읽어서 적용"""
        # 이미지 드롭이 비활성화된 경우 기본 동작만 수행
        if not self.enable_image_drop:
            super().dropEvent(event)
            return

        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if len(urls) == 1:
                file_path = urls[0].toLocalFile()
                # NovelAI 이미지 파일 처리
                if file_path.lower().endswith(('.png', '.webp')):
                    logger.info(f"Image dropped on prompt input: {file_path}")
                    # 상위 윈도우 찾기 (NAIAutoGeneratorWindow)
                    parent = self.parent()
                    while parent is not None:
                        # NAIAutoGeneratorWindow를 찾을 때까지 상위로 올라감
                        if hasattr(parent, 'get_image_info_bysrc'):
                            logger.debug("Found parent window with get_image_info_bysrc method")
                            parent.get_image_info_bysrc(file_path)
                            event.acceptProposedAction()
                            return
                        parent = parent.parent()

                    logger.warning("Could not find parent window to load image metadata")
                    # 상위 윈도우를 찾지 못한 경우 파일 경로만 삽입
                    cursor = self.textCursor()
                    cursor.insertText(file_path)
                    event.acceptProposedAction()
                    return

        # 이미지가 아니면 기본 텍스트 드래그 앤 드롭 처리
        super().dropEvent(event)

    def insertFromMimeData(self, source):
        """클립보드에서 붙여넣기할 때 서식 없는 텍스트만 삽입"""
        if source.hasText():
            # 서식 없는 일반 텍스트만 가져와서 현재 커서 위치에 삽입
            cursor = self.textCursor()
            cursor.insertText(source.text())
        else:
            # 기본 처리 방식 사용 (텍스트가 없는 다른 형식의 데이터인 경우)
            super().insertFromMimeData(source)
    
    def highlightSyntax(self):
        """통합된 구문 강조 기능 - 괄호와 가중치 강조 모두 처리"""
        text = self.toPlainText()
        
        # 구문 강조를 위한 ExtraSelection 목록
        selections = []
        
        # 1. 괄호 강조
        selections.extend(self.findBracketHighlights(text))
        
        # 2. 가중치 구문 강조
        if self.highlight_emphasis:
            selections.extend(self.findNumericEmphasisHighlights(text))
        
        # 모든 강조 적용
        self.setExtraSelections(selections)
    
    def findBracketHighlights(self, text):
        """괄호 강조를 위한 ExtraSelection 목록 반환"""
        selections = []
        
        # Stack to keep track of open brackets
        stack = []
        bracket_pairs = {'(': ')', '{': '}', '[': ']', '<': '>'}
        open_brackets = bracket_pairs.keys()
        close_brackets = bracket_pairs.values()

        # Dictionary to keep track of bracket positions
        bracket_positions = {}
        for i, char in enumerate(text):
            if char in open_brackets:
                stack.append((char, i))
                bracket_positions[i] = -1  # 기본 값으로 -1 설정
            elif char in close_brackets:
                if stack and bracket_pairs[stack[-1][0]] == char:
                    open_bracket, open_pos = stack.pop()
                    bracket_positions[open_pos] = i
                    bracket_positions[i] = open_pos
                else:
                    bracket_positions[i] = -1

        # Highlight unmatched brackets
        unmatched_format = QTextCharFormat()
        unmatched_format.setFontWeight(QFont.Bold)
        unmatched_format.setForeground(self.emphasis_colors["bracket_unmatched"])

        for pos, matching_pos in bracket_positions.items():
            if matching_pos == -1:
                selection = QTextEdit.ExtraSelection()
                selection.format = unmatched_format
                cursor = self.textCursor()
                cursor.setPosition(pos)
                cursor.movePosition(QTextCursor.NextCharacter, QTextCursor.KeepAnchor)
                selection.cursor = cursor
                selections.append(selection)
        
        return selections
    
    def findNumericEmphasisHighlights(self, text):
        """가중치 구문 강조를 위한 ExtraSelection 목록 반환 - 개선된 버전"""
        selections = []

        # 1. 숫자 다음에 ::가 오는 패턴: "1.5::텍스트::" or "-2::텍스트::" (artist:name 같은 단일 콜론 포함)
        # (?:[^:]|:(?!:))* = 단일 콜론은 허용하지만 이중 콜론에서는 중단
        number_pattern = r"(-?\d+(?:\.\d+)?)::((?:[^:]|:(?!:))*)(?:::)?"

        # 2. ::로 시작하는 패턴: "::텍스트::" (artist:name 같은 단일 콜론 포함)
        prefix_pattern = r"::((?:[^:]|:(?!:))*)(?:::)?"

        # Track positions covered by number patterns to avoid duplicate highlighting
        covered_positions = set()

        # 숫자+:: 패턴 처리
        for match in re.finditer(number_pattern, text):
            # Mark all positions in this match as covered
            for pos in range(match.start(), match.end()):
                covered_positions.add(pos)
            # 가중치 값과 강조 텍스트 가져오기
            weight_str = match.group(1)
            emphasized_text = match.group(2)
            
            try:
                # 가중치 값 파싱
                weight = float(weight_str)
                
                # 강조 수준에 따른 서식 설정
                format = QTextCharFormat()
                
                if weight > 1.0:
                    # 강조(>1.0)
                    format.setForeground(self.emphasis_colors["high"])
                    # 가중치에 비례하여 폰트 굵기 증가
                    bold_level = min(QFont.Black, int(QFont.Normal + (weight - 1.0) * 3))
                    format.setFontWeight(bold_level)
                elif weight < 1.0:
                    # 약화(<1.0)
                    format.setForeground(self.emphasis_colors["low"])
                else:
                    # 일반(=1.0)
                    format.setForeground(self.emphasis_colors["normal"])
                
                # 강조 텍스트 부분만 강조
                emphasis_start = match.start(2)  # 가중치 다음 시작 위치
                emphasis_end = match.start(2) + len(emphasized_text)
                
                # 텍스트 선택 및 강조 추가
                selection = QTextEdit.ExtraSelection()
                selection.format = format
                cursor = self.textCursor()
                cursor.setPosition(emphasis_start)
                cursor.setPosition(emphasis_end, QTextCursor.KeepAnchor)
                selection.cursor = cursor
                selections.append(selection)
                
                # 가중치 숫자와 '::' 부분을 다른 색으로 강조
                weight_format = QTextCharFormat()
                weight_format.setForeground(QColor(128, 0, 128))  # 보라색
                weight_format.setFontWeight(QFont.Bold)
                
                weight_selection = QTextEdit.ExtraSelection()
                weight_selection.format = weight_format
                cursor = self.textCursor()
                cursor.setPosition(match.start(1))
                cursor.setPosition(match.start(2), QTextCursor.KeepAnchor)
                weight_selection.cursor = cursor
                selections.append(weight_selection)
                
            except ValueError:
                # 가중치가 유효한 숫자가 아닌 경우 무시
                pass
        
        # ::로 시작하는 패턴 처리 (기본값 1.0으로 간주)
        for match in re.finditer(prefix_pattern, text):
            # 시작 위치가 숫자+:: 패턴의 일부인지 확인 (중복 방지)
            emphasis_text = match.group(1)
            start_pos = match.start()

            # Check if this match overlaps with any number pattern match
            if start_pos in covered_positions:
                continue  # Skip this match as it's part of a number pattern

            if emphasis_text:
                # 기본 강조 서식 (가중치 1.0으로 처리)
                format = QTextCharFormat()
                format.setForeground(self.emphasis_colors["high"])  # 강조 색상 사용
                
                # 강조 텍스트 부분 선택
                emphasis_start = match.start(1)
                emphasis_end = match.start(1) + len(emphasis_text)
                
                selection = QTextEdit.ExtraSelection()
                selection.format = format
                cursor = self.textCursor()
                cursor.setPosition(emphasis_start)
                cursor.setPosition(emphasis_end, QTextCursor.KeepAnchor)
                selection.cursor = cursor
                selections.append(selection)
                
                # '::' 마커 강조
                marker_format = QTextCharFormat()
                marker_format.setForeground(QColor(128, 0, 128))  # 보라색
                marker_format.setFontWeight(QFont.Bold)
                
                marker_selection = QTextEdit.ExtraSelection()
                marker_selection.format = marker_format
                cursor = self.textCursor()
                cursor.setPosition(match.start())
                cursor.setPosition(match.start() + 2, QTextCursor.KeepAnchor)  # '::'만 선택
                marker_selection.cursor = cursor
                selections.append(marker_selection)
        
        return selections
    
    # 아래는 기존 자동 완성 기능 메서드들
    def start_complete_mode(self, tag_list):
        logger.debug(f"start_complete_mode 호출: {len(tag_list)}개 태그")
        if not tag_list:
            logger.warning("태그 목록이 비어 있어 자동 완성을 설정하지 않습니다.")
            return

        try:
            completer = CustomCompleter(tag_list)
            self.setCompleter(completer)
            logger.info("자동 완성 설정 완료")
        except Exception as e:
            logger.error(f"자동 완성 설정 중 오류 발생: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def setCompleter(self, completer):
        if self.completer:
            try:
                self.disconnect(self.completer, self.insertCompletion)
            except:
                pass  # 이전 연결이 없을 수 있으므로 예외 무시
        self.completer = completer
        if not self.completer:
            return
        self.completer.setWidget(self)
        self.completer.setCompletionMode(QCompleter.PopupCompletion)
        self.completer.setCaseSensitivity(False)
        try:
            self.completer.activated.connect(self.insertCompletion)
        except:
            logger.error("자동완성 신호 연결 실패")

    def insertCompletion(self, completion):
        # CSV 형식 처리 (태그[숫자] => 태그)
        actual_text = completion.split('[')[0] if '[' in completion else completion
        actual_text = actual_text.replace("_", " ")
        
        tc = self.textCursor()
        extra = len(actual_text) - len(self.completer.completionPrefix())
        tc.movePosition(QTextCursor.Left)
        tc.movePosition(QTextCursor.EndOfWord)
        tc.insertText(actual_text[-extra:])
        self.setTextCursor(tc)

    def textUnderCursor(self):
        tc = self.textCursor()
        tc.select(QTextCursor.WordUnderCursor)
        return tc.selectedText()

    def keyPressEvent(self, event):
        if self.completer:
            if self.completer and self.completer.popup().isVisible():
                if event.key() in (Qt.Key_Enter, Qt.Key_Return, Qt.Key_Escape, Qt.Key_Tab, Qt.Key_Backtab):
                    event.ignore()
                    return

            super().keyPressEvent(event)

            ctrlOrShift = event.modifiers() & (Qt.ControlModifier | Qt.ShiftModifier)
            if ctrlOrShift and event.text() == '':
                return

            if event.text():
                # eow = "~!@#$%^&*()_+{}|:\"<>?,./;'[]\\-="
                eow = "{},<>|@"
                hasModifier = (event.modifiers() !=
                               Qt.NoModifier) and not ctrlOrShift
                completionPrefix = self.textUnderCursor()

                if not self.completer or (hasModifier and event.text() == '') or len(completionPrefix) < 1 or event.text()[-1] in eow:
                    self.completer.popup().hide()
                    return

                if completionPrefix != self.completer.completionPrefix():
                    self.completer.setCompletionPrefix(completionPrefix)
                    self.completer.popup().setCurrentIndex(
                        self.completer.completionModel().index(0, 0))

                cr = self.cursorRect()
                cr.setWidth(self.completer.popup().sizeHintForColumn(
                    0) + self.completer.popup().verticalScrollBar().sizeHint().width())
                self.completer.complete(cr)
        else:
            super().keyPressEvent(event)
    
    # 가중치 하이라이트 설정 메서드
    def setEmphasisHighlighting(self, enabled):
        """가중치 하이라이트 활성화/비활성화"""
        self.highlight_emphasis = enabled
        self.highlightSyntax()  # 즉시 적용
    
    def setEmphasisColors(self, color_dict):
        """가중치 하이라이트 색상 설정"""
        for key, color in color_dict.items():
            if key in self.emphasis_colors:
                self.emphasis_colors[key] = color
        self.highlightSyntax()  # 즉시 적용
