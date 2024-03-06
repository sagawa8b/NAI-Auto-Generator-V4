import os
import sys
from PyQt5.QtWidgets import QApplication, QWidget, QFrame, QFileDialog, QLabel, QLineEdit, QCheckBox, QGridLayout, QVBoxLayout, QHBoxLayout, QPushButton, QDialog, QMessageBox, QFileSystemModel, QListView, QSizePolicy
from PyQt5.QtGui import QImage, QPainter
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QEvent, QRectF, QSize

from consts import DEFAULT_PATH


def create_empty(minimum_width=1, minimum_height=1, fixed_height=0):
    w = QWidget()
    w.setMinimumWidth(minimum_width)
    w.setMinimumHeight(minimum_height)
    w.setStyleSheet("background-color:#00000000")
    if fixed_height != 0:
        w.setFixedHeight(fixed_height)
    return w


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path).replace("\\", "/")


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


class BackgroundFrame(QFrame):
    def __init__(self, parent):
        super(BackgroundFrame, self).__init__(parent)
        self.image = QImage()

    def set_background_image(self, image_path):
        self.image.load(image_path)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        scaled_image = self.image.scaled(
            self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        target_rect = QRectF(
            (self.width() - scaled_image.width()) / 2,
            (self.height() - scaled_image.height()) / 2,
            scaled_image.width(),
            scaled_image.height())
        painter.setOpacity(0.5)
        painter.drawImage(target_rect, scaled_image)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Resize:
            self.update()
            return True
        return super(BackgroundFrame, self).eventFilter(obj, event)


class LoginThread(QThread):
    login_result = pyqtSignal(int)

    def __init__(self, parent, nai, username, password):
        super(LoginThread, self).__init__(parent)
        self.nai = nai
        self.username = username
        self.password = password

    def run(self):
        if not self.username or not self.password:
            self.login_result.emit(1)
            return

        is_login_success = self.nai.try_login(
            self.username, self.password)

        self.login_result.emit(0 if is_login_success else 2)


class LoginDialog(QDialog):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.initUI()
        self.check_already_login()
        super().exec_()

    def initUI(self):
        parent_pos = self.parent.pos()

        self.setWindowTitle('로그인')
        self.move(parent_pos.x() + 50, parent_pos.y() + 50)
        self.resize(400, 150)

        layout = QVBoxLayout()

        hbox_username = QHBoxLayout()
        username_label = QLabel('Username:')
        username_edit = QLineEdit(self)
        self.username_edit = username_edit
        hbox_username.addWidget(username_label)
        hbox_username.addWidget(username_edit)

        hbox_password = QHBoxLayout()
        password_label = QLabel('Password:')
        password_edit = QLineEdit(self)
        password_edit.setEchoMode(QLineEdit.Password)  # 비밀번호 입력시 마스킹 처리
        self.password_edit = password_edit
        hbox_password.addWidget(password_label)
        hbox_password.addWidget(password_edit)

        vbox_button = QGridLayout()
        autologin_check = QCheckBox("자동 로그인")
        self.autologin_check = autologin_check
        autologin_check.setChecked(True)
        login_button = QPushButton('Login')
        login_button.clicked.connect(self.try_login)
        self.login_button = login_button
        logout_button = QPushButton('Logout')
        logout_button.setDisabled(True)
        logout_button.clicked.connect(self.logout)
        self.logout_button = logout_button
        vbox_button.addWidget(autologin_check, 0, 0)
        vbox_button.addWidget(login_button, 0, 1)
        vbox_button.addWidget(logout_button, 1, 1)

        instruct_label = QLabel('Novel AI 계정을 입력해주세요.')
        instruct_label.setAlignment(Qt.AlignRight)
        self.instruct_label = instruct_label

        layout.addLayout(hbox_username)
        layout.addLayout(hbox_password)
        layout.addLayout(vbox_button)
        layout.addWidget(instruct_label)

        self.setLayout(layout)

    def set_login_result_ui(self, is_login_success):
        self.username_edit.setDisabled(is_login_success)
        self.password_edit.setDisabled(is_login_success)

        self.login_button.setDisabled(is_login_success)
        self.logout_button.setDisabled(not is_login_success)

        self.instruct_label.setText(
            "로그인 성공! 창을 닫아도 됩니다." if is_login_success else 'Novel AI 계정을 입력해주세요.')

    def check_already_login(self):
        if self.parent.trying_auto_login:
            self.username_edit.setDisabled(True)
            self.password_edit.setDisabled(True)

            self.login_button.setDisabled(True)
            self.logout_button.setDisabled(True)

            self.instruct_label.setText("자동로그인 시도중입니다. 창을 꺼주세요.")
        else:  # 오토 로그인 중이 아니라면 자동 로그인
            nai = self.parent.nai
            if nai.access_token:  # 자동로그인 성공
                self.username_edit.setText(nai.username)
                self.password_edit.setText(nai.password)

                self.set_login_result_ui(True)
            else:  # 자동로그인 실패
                self.set_login_result_ui(False)

    def try_login(self):
        username = self.username_edit.text()
        password = self.password_edit.text()

        self.instruct_label.setText("로그인 시도 중... 창을 닫지 마세요.")
        self.parent.set_statusbar_text("LOGGINGIN")
        self.login_button.setDisabled(True)
        self.logout_button.setDisabled(True)

        login_thread = LoginThread(self, self.parent.nai, username, password)
        login_thread.login_result.connect(self.on_login_result)
        login_thread.login_result.connect(self.parent.on_login_result)
        login_thread.start()
        self.login_thread = login_thread

    def logout(self):
        self.parent.on_logout()
        self.set_login_result_ui(False)

    def on_login_result(self, error_code):
        if error_code == 0:
            self.set_login_result_ui(True)

            if self.autologin_check.isChecked():
                self.parent.set_auto_login(True)
        elif error_code == 1:
            self.set_login_result_ui(False)
            self.instruct_label.setText("잘못된 아이디 또는 비번입니다.")
        elif error_code == 2:
            self.set_login_result_ui(False)
            self.instruct_label.setText("로그인에 실패했습니다.")


class GenerateDialog(QDialog):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.initUI()

    def initUI(self):
        parent_pos = self.parent.pos()

        self.setWindowTitle('자동 생성')
        self.move(parent_pos.x() + 50, parent_pos.y() + 50)
        self.setFixedSize(400, 200)

        layout = QVBoxLayout()
        self.setLayout(layout)

        layout_count = QHBoxLayout()
        layout.addLayout(layout_count)

        label_count = QLabel("생성 횟수(빈칸시 무한) : ", self)
        layout_count.addWidget(label_count, 1)
        lineedit_count = QLineEdit("")
        lineedit_count.setMaximumWidth(40)
        self.lineedit_count = lineedit_count
        layout_count.addWidget(lineedit_count, 1)

        layout_delay = QHBoxLayout()
        layout.addLayout(layout_delay)

        label_delay = QLabel("지연 시간(매 생성시, 에러시 대기시간) : ", self)
        layout_delay.addWidget(label_delay, 1)
        lineedit_delay = QLineEdit("3")
        lineedit_delay.setMaximumWidth(40)
        self.lineedit_delay = lineedit_delay
        layout_delay.addWidget(lineedit_delay, 1)

        checkbox_ignoreerror = QCheckBox("에러 발생 시에도 계속 하기")
        checkbox_ignoreerror.setChecked(True)
        self.checkbox_ignoreerror = checkbox_ignoreerror
        layout.addWidget(checkbox_ignoreerror, 1)

        layout_buttons = QHBoxLayout()
        layout.addLayout(layout_buttons)

        start_button = QPushButton("시작")
        start_button.clicked.connect(self.on_start_button_clicked)
        layout_buttons.addWidget(start_button)
        self.start_button = start_button

        close_button = QPushButton("닫기")
        close_button.clicked.connect(self.on_close_button_clicked)
        layout_buttons.addWidget(close_button)
        self.close_button = close_button

    def on_start_button_clicked(self):
        self.count = self.lineedit_count.text()
        self.delay = self.lineedit_delay.text()
        self.ignore_error = self.checkbox_ignoreerror.isChecked()
        self.accept()

    def on_close_button_clicked(self):
        self.reject()


class OptionDialog(QDialog):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.initUI()
        super().exec_()

    def initUI(self):
        parent_pos = self.parent.pos()

        self.setWindowTitle('옵션')
        self.move(parent_pos.x() + 50, parent_pos.y() + 50)
        self.resize(600, 200)
        layout = QVBoxLayout()

        self.dict_label_loc = {}

        def add_item(layout, code, text):
            hbox_item = QHBoxLayout()
            layout.addLayout(hbox_item)

            label_title = QLabel(text)
            hbox_item.addWidget(label_title)

            path = self.parent.settings.value(
                code, DEFAULT_PATH[code])
            label_loc = QLabel(os.path.abspath(path))
            label_loc.setStyleSheet("font-size: 14px")
            self.dict_label_loc[code] = label_loc
            hbox_item.addWidget(label_loc, stretch=999)

            button_select_loc = QPushButton("위치 변경")
            button_select_loc.setSizePolicy(
                QSizePolicy.Minimum, QSizePolicy.Minimum)
            button_select_loc.clicked.connect(
                lambda: self.on_click_select_button(code))
            hbox_item.addWidget(button_select_loc)

            button_reset_loc = QPushButton("리셋")
            button_reset_loc.setSizePolicy(
                QSizePolicy.Minimum, QSizePolicy.Minimum)
            button_reset_loc.clicked.connect(
                lambda: self.on_click_reset_button(code))
            hbox_item.addWidget(button_reset_loc)

        add_item(layout, "path_results", "생성이미지 저장 위치 : ")
        add_item(layout, "path_wildcards", "와일드카드 저장 위치 : ")
        add_item(layout, "path_settings", "세팅 파일 저장 위치 : ")
        add_item(layout, "path_models", "태거 모델 저장 위치 : ")

        layout.addWidget(create_empty(minimum_height=6))

        checkbox_savepname = QCheckBox("파일 생성시 이름에 프롬프트 넣기")
        checkbox_savepname.setChecked(strtobool(
            self.parent.settings.value("will_savename_prompt", True)))
        self.checkbox_savepname = checkbox_savepname
        layout.addWidget(checkbox_savepname)

        button_close = QPushButton("닫기")
        button_close.clicked.connect(self.on_click_close_button)
        self.button_close = button_close

        layout.addStretch(2)

        qhl_close = QHBoxLayout()
        qhl_close.addStretch(4)
        qhl_close.addWidget(self.button_close, 2)
        layout.addLayout(qhl_close)

        self.setLayout(layout)

    def on_click_select_button(self, code):
        select_dialog = QFileDialog()
        save_loc = select_dialog.getExistingDirectory(
            self, '저장할 위치를 골라주세요.')

        if save_loc:
            self.parent.change_path(code, save_loc)

            self.refresh_label(code)

    def on_click_reset_button(self, code):
        self.parent.change_path(code, DEFAULT_PATH[code])

        self.refresh_label(code)

    def refresh_label(self, code):
        path = self.parent.settings.value(code, DEFAULT_PATH[code])
        self.dict_label_loc[code].setText(path)

    def on_click_close_button(self):
        self.parent.settings.setValue(
            "will_savename_prompt", self.checkbox_savepname.isChecked())
        self.reject()


class LoadingWorker(QThread):
    finished = pyqtSignal(bool)

    def __init__(self, func):
        super().__init__()
        self.func = func

    def run(self):
        try:
            self.finished.emit(self.func())
        except Exception as e:
            print(e)
            self.finished.emit(False)


class FileIODialog(QDialog):
    def __init__(self, text, func):
        super().__init__()
        self.text = text
        self.func = func
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("로딩 중")

        layout = QVBoxLayout()
        self.progress_label = QLabel(self.text)
        layout.addWidget(self.progress_label)

        self.setLayout(layout)

        self.resize(200, 100)
        self.setWindowFlag(Qt.WindowCloseButtonHint, False)

    def showEvent(self, event):
        self.worker_thread = LoadingWorker(self.func)
        self.worker_thread.finished.connect(self.on_finished)
        self.worker_thread.start()
        super().showEvent(event)

    def on_finished(self, df):
        self.result = df
        self.accept()


class MiniUtilDialog(QDialog):
    def __init__(self, parent, mode):
        super(MiniUtilDialog, self).__init__(parent)
        self.mode = mode
        self.setWindowTitle("태거" if self.mode == "tagger" else "인포 게터")

        # 레이아웃 설정
        layout = QVBoxLayout()
        frame = BackgroundFrame(self)
        frame.set_background_image(self.mode + ".png")
        self.parent().installEventFilter(frame)
        frame.setFixedSize(QSize(512, 512))
        layout.addWidget(frame)
        self.setLayout(layout)


if __name__ == '__main__':
    app = QApplication(sys.argv)

    DEBUG_MODE = MiniUtilDialog

    if DEBUG_MODE == MiniUtilDialog:
        from PyQt5.QtWidgets import QMainWindow
        qw = QMainWindow()
        loading_dialog = MiniUtilDialog(qw, "getter")
        if loading_dialog.exec_() == QDialog.Accepted:
            print(len(loading_dialog.result))
