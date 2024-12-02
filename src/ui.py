import sys
import numpy as np
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QVBoxLayout,
    QWidget,
    QPushButton,
    QLineEdit,
    QLabel,
)
from PyQt5.QtGui import QImage, QPixmap
from hypha_rpc.sync import connect_to_server, login
from microscope import SharedImage, register_shared_image_codec


class SnapImageApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()

        # Initialize QTimer for updating the snapped image
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_snap_image)

        # Variables for server and service connection
        self.server = None
        self.microscope_service = None
        # self.analysis_service = None

    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Microscope Control")
        self.setGeometry(100, 100, 600, 600)

        layout = QVBoxLayout()

        # Input for stage movement
        self.x_input = QLineEdit(self)
        self.x_input.setPlaceholderText("X Offset")
        self.x_input.setText("0.0")
        layout.addWidget(self.x_input)

        self.y_input = QLineEdit(self)
        self.y_input.setPlaceholderText("Y Offset")
        self.y_input.setText("0.0")
        layout.addWidget(self.y_input)

        move_button = QPushButton("Move Stage", self)
        move_button.clicked.connect(self.move_stage)
        layout.addWidget(move_button)

        # Input for exposure time
        self.exposure_input = QLineEdit(self)
        self.exposure_input.setPlaceholderText("Exposure Time (ms)")
        self.exposure_input.setText("100")
        layout.addWidget(self.exposure_input)

        # Buttons to control snapping images
        start_button = QPushButton("Start Snapping", self)
        start_button.clicked.connect(self.start_display)
        layout.addWidget(start_button)

        stop_button = QPushButton("Stop Snapping", self)
        stop_button.clicked.connect(self.stop_display)
        layout.addWidget(stop_button)

        # Image display label
        self.image_label = QLabel(self)
        self.image_label.setText("Snapped Image will appear here.")
        layout.addWidget(self.image_label)

        # Status label
        self.status_label = QLabel("Status: Not connected", self)
        layout.addWidget(self.status_label)

        # Set the layout
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def connect_to_server(self):
        """Connect to the Hypha server and initialize the microscope service."""
        try:
            server_url = "http://127.0.0.1:9527"
            token = login({"server_url": server_url})
            self.server = connect_to_server({"server_url": server_url, "token": token, "sync_max_workers": 1})

            # Register the shared image codec
            register_shared_image_codec(self.server)

            # Get the microscope service
            self.microscope_service = self.server.get_service("microscope-control")
            # self.analysis_service = self.server.get_service("image-analysis")
            
            self.status_label.setText("Status: Connected to the server.")
        except Exception as e:
            self.status_label.setText(f"Error connecting to server: {e}")

    def start_display(self):
        """Start snapping images."""
        if self.microscope_service is None:
            self.status_label.setText("Error: Not connected to the server.")
            return

        self.timer.start(30)  # Update every 30 milliseconds
        self.status_label.setText("Status: Snapping")

    def stop_display(self):
        """Stop snapping images."""
        self.timer.stop()
        self.status_label.setText("Status: Snapping Stopped")

    def move_stage(self):
        """Move the microscope stage."""
        try:
            x = float(self.x_input.text())
            y = float(self.y_input.text())
            result = self.microscope_service.move_stage(x=x, y=y)
            self.status_label.setText(f"Stage moved to: x={x}, y={y} - {result}")
        except Exception as e:
            self.status_label.setText(f"Error: {e}")

    def update_snap_image(self):
        """Snap an image and display it."""
        try:
            # Get exposure time from input
            exposure = float(self.exposure_input.text())
            # Call snap_image from the microscope service
            result = self.microscope_service.snap_image(exposure=exposure, return_shared=False)
            # if self.analysis_service:
            #     result = self.analysis_service.convolve_image(image=result, kernel_size=3)
            if isinstance(result, SharedImage):
                # Restore numpy array from shared memory
                image_data = result.to_numpy()
                result.close()
            else:
                image_data = result

            # Convert numpy array to QImage
            height, width = image_data.shape
            bytes_per_line = width  # Grayscale images have 1 byte per pixel
            qimage = QImage(image_data, width, height, bytes_per_line, QImage.Format_Grayscale8)

            # Convert QImage to QPixmap and display it
            pixmap = QPixmap.fromImage(qimage)
            self.image_label.setPixmap(pixmap)

        except Exception as e:
            self.status_label.setText(f"Error: {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SnapImageApp()
    window.connect_to_server()
    window.show()
    sys.exit(app.exec_())
