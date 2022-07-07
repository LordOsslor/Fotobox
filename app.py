import os
import sys

from urllib.parse import urljoin
from time import time
from secrets import token_urlsafe
from enum import Enum, auto
from typing import List
from zipfile import ZipFile

from PyQt5 import QtCore, QtGui, QtWidgets
from qrcode import QRCode
from PIL.ImageQt import ImageQt

from window import Ui_MainWindow
from dialog import Ui_Dialog


class States(Enum):
    Stopped = auto()
    Started = auto()
    Sharing = auto()


timerInterval = 250


class Program:

    # consts:
    url_root: str = "http://192.168.178.100/q/"
    image_root: str = "fotos"
    zip_root: str = "zips"
    zip_name: str = "09.07. - Bilder_vom_Gemeinderat"
    state: States = States.Stopped
    known_images: List[str] = []

    ui: Ui_MainWindow
    main_timer: QtCore.QTimer
    start_time: float
    end_time: float
    tick_count: int
    current_id: str

    def __init__(
        self,
        ui: Ui_MainWindow,
        dialog: QtWidgets.QDialog,
        image_root: str = "",
        zip_root: str = "",
    ) -> None:

        if image_root:
            self.image_root = image_root
        if zip_root:
            self.zip_root = zip_root

        if not os.path.exists(self.image_root):
            os.mkdir(self.image_root)
        if not os.path.exists(self.zip_root):
            os.mkdir(self.zip_root)

        self.ui = ui
        self.dialog = dialog

        # initialize timer
        self.main_timer = QtCore.QTimer()
        self.main_timer.setInterval(timerInterval)
        self.main_timer.timeout.connect(self.timer_tick)

        # preview:
        self.ui.image_list.currentTextChanged.connect(self.selected_item_change)

        # button event:
        self.ui.ss_btn.clicked.connect(self.ss_click)

    def gen_qr_code(self) -> QtGui.QPixmap:
        qr = QRCode()
        qr.add_data(urljoin(self.url_root, f"{self.current_id}/{self.zip_name}.zip"))
        qr.make()
        p_img = qr.make_image(fill_color="black", back_color="white")
        return QtGui.QPixmap.fromImage(ImageQt(p_img))

    def update_time(self):
        passed_seconds = int(time() - self.start_time)

        def two_digit_string(i: int | float):
            if isinstance(i, float):
                i = int(i)

            return f"0{i}" if i < 10 else str(i)

        time_string = f"{two_digit_string(passed_seconds / 60)}:{two_digit_string(passed_seconds % 60)}"
        self.ui.time.setText(time_string)

    def timer_tick(self) -> None:
        self.ui.image_list.addItems(self.get_new_images())
        self.update_time()

    def set_image(self, pmap: QtGui.QPixmap):
        item = QtWidgets.QGraphicsPixmapItem(pmap)
        scene = QtWidgets.QGraphicsScene()
        scene.addItem(item)

        self.ui.preview.setScene(scene)
        self.ui.preview.fitInView(
            scene.sceneRect(), QtCore.Qt.AspectRatioMode.KeepAspectRatio
        )

    def get_new_images(self) -> list[str]:
        image_paths = os.listdir(self.image_root)
        et = self.end_time if self.end_time > 0 else time()

        fitting_paths = []
        for image_path in image_paths:
            abs_image_path = os.path.join(self.image_root, image_path)
            ctime = os.path.getctime(abs_image_path)
            if self.start_time < ctime < et and image_path not in self.known_images:
                fitting_paths.append(image_path)
                self.known_images.append(image_path)
        count = len(self.known_images)
        self.ui.counter.setProperty("intValue", count)
        if count == 0:
            self.ui.ss_btn.setEnabled(False)
        else:
            self.ui.ss_btn.setEnabled(True)

        return fitting_paths

    def selected_item_change(self, s: str):
        self.set_image(QtGui.QPixmap(os.path.join(self.image_root, s)))

    def start(self):
        self.state = States.Started
        self.start_time = time()
        self.end_time = -1
        self.main_timer.start()
        self.ui.ss_btn.setText("Teilen")
        self.tick_count = 0
        self.current_id = token_urlsafe(16)
        self.ui.image_list.currentTextChanged.connect(self.selected_item_change)
        self.ui.ss_btn.setEnabled(False)

    def share(self):
        self.state = States.Sharing
        self.end_time = time()
        self.main_timer.stop()
        self.ui.ss_btn.setText("Fertig")
        self.ui.image_list.currentTextChanged.disconnect()
        self.ui.image_list.setEnabled(False)
        self.ui.preview_label.setText("QR-Code:")
        self.set_image(self.gen_qr_code())
        zip_path = os.path.join(self.zip_root, self.current_id)
        os.mkdir(zip_path)
        with ZipFile(os.path.join(zip_path, f"{self.zip_name}.zip"), "w") as zip:
            for image in self.known_images:
                zip.write(os.path.join(self.image_root, image), image)

    def stop(self):
        if not self.dialog.exec():
            return
        self.state = States.Stopped
        self.ui.ss_btn.setText("Start")
        self.ui.image_list.clear()
        self.ui.preview.setScene(QtWidgets.QGraphicsScene())
        self.ui.time.setText("00:00")
        self.known_images = []
        self.ui.counter.setProperty("intValue", 0)
        self.ui.image_list.setEnabled(True)
        self.ui.preview_label.setText("Vorschau:")

    def ss_click(self):
        match self.state:
            case States.Stopped:
                self.start()
            case States.Started:
                self.share()
            case States.Sharing:
                self.stop()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    mainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(mainWindow)
    dialog = QtWidgets.QDialog(mainWindow)
    dialog_ui = Ui_Dialog()
    dialog_ui.setupUi(dialog)
    # print(dialog.exec())

    x = Program(ui, dialog)

    # x = Program(ui, dialog, image_root="/run/user/1000/d2fa8138b23971ac/DCIM_Camera")

    if "nfs" in sys.argv[1:]:
        mainWindow.show()
    else:
        mainWindow.showFullScreen()

    # stop exit
    sys.exit(app.exec_())