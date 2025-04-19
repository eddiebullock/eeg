"""
Control panel for the EEG Monitor application.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QSlider, QComboBox, QDialog, QDialogButtonBox
)
from PyQt5.QtCore import Qt, pyqtSignal

class ControlPanel(QWidget):
    """Control panel widget with all user controls"""
    
    # Custom signals
    filter_changed = pyqtSignal()  # Signal emitted when filter settings change
    display_changed = pyqtSignal()  # Signal emitted when display settings change
    
    def __init__(self, settings, serial_reader, signal_processor, data_manager):
        super().__init__()
        
        self.settings = settings
        self.serial_reader = serial_reader
        self.signal_processor = signal_processor
        self.data_manager = data_manager
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize user interface components"""
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # First row of controls
        controls_layout1 = QHBoxLayout()
        main_layout.addLayout(controls_layout1)
        
        # Create connection status indicator
        self.connection_label = QLabel("Connection: Disconnected")
        self.connection_label.setStyleSheet("color: red")
        controls_layout1.addWidget(self.connection_label)
        
        # Create port selection
        controls_layout1.addWidget(QLabel("Port:"))
        
        # Create port selection button
        self.port_button = QPushButton(self.settings.serial_port)
        self.port_button.clicked.connect(self.select_port)
        controls_layout1.addWidget(self.port_button)
        
        # Create connect button
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.toggle_connection)
        controls_layout1.addWidget(self.connect_button)
        
        # Create status label
        self.status_label = QLabel("Status: Waiting for data")
        controls_layout1.addWidget(self.status_label)
        
        # Create record button
        self.record_button = QPushButton("Start Recording")
        self.record_button.clicked.connect(self.toggle_recording)
        controls_layout1.addWidget(self.record_button)
        
        # Create save spectrogram button
        self.save_button = QPushButton("Save Spectrogram")
        self.save_button.clicked.connect(self.save_spectrogram)
        controls_layout1.addWidget(self.save_button)
        
        # Create serial test button
        self.test_button = QPushButton("Test Connection")
        self.test_button.clicked.connect(self.test_connection)
        controls_layout1.addWidget(self.test_button)
        
        # Second row of controls
        controls_layout2 = QHBoxLayout()
        main_layout.addLayout(controls_layout2)
        
        # Add filter controls
        controls_layout2.addWidget(QLabel("Highpass:"))
        self.highpass_combo = QComboBox()
        self.highpass_combo.addItems(["Off", "0.1 Hz", "0.5 Hz", "1.0 Hz", "5.0 Hz"])
        self.highpass_combo.setCurrentIndex(2)  # Default 0.5 Hz
        self.highpass_combo.currentIndexChanged.connect(self.update_filter_settings)
        controls_layout2.addWidget(self.highpass_combo)
        
        controls_layout2.addWidget(QLabel("Lowpass:"))
        self.lowpass_combo = QComboBox()
        self.lowpass_combo.addItems(["30 Hz", "50 Hz", "70 Hz", "100 Hz", "Off"])
        self.lowpass_combo.setCurrentIndex(2)  # Default 70 Hz
        self.lowpass_combo.currentIndexChanged.connect(self.update_filter_settings)
        controls_layout2.addWidget(self.lowpass_combo)
        
        controls_layout2.addWidget(QLabel("Notch:"))
        self.notch_combo = QComboBox()
        self.notch_combo.addItems(["Off", "50 Hz", "60 Hz"])
        self.notch_combo.setCurrentIndex(2)  # Default 60 Hz (US)
        self.notch_combo.currentIndexChanged.connect(self.update_filter_settings)
        controls_layout2.addWidget(self.notch_combo)
        
        # Add sensitivity slider
        controls_layout2.addWidget(QLabel("Sensitivity:"))
        self.sensitivity_slider = QSlider(Qt.Horizontal)
        self.sensitivity_slider.setMinimum(1)
        self.sensitivity_slider.setMaximum(10)
        self.sensitivity_slider.setValue(5)
        self.sensitivity_slider.setTickPosition(QSlider.TicksBelow)
        self.sensitivity_slider.setTickInterval(1)
        self.sensitivity_slider.valueChanged.connect(self.update_sensitivity)
        controls_layout2.addWidget(self.sensitivity_slider)
        
        # Add display speed control
        controls_layout2.addWidget(QLabel("Speed:"))
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["12.5 mm/s", "25 mm/s", "50 mm/s", "100 mm/s"])
        self.speed_combo.setCurrentIndex(1)  # Default 25 mm/s
        self.speed_combo.currentIndexChanged.connect(self.update_display_speed)
        controls_layout2.addWidget(self.speed_combo)
    
    def update_connection_status(self, connected, message=None):
        """Update the connection status display"""
        if connected:
            self.connection_label.setText(f"Connection: {message}")
            self.connection_label.setStyleSheet("color: green")
            self.connect_button.setText("Disconnect")
        else:
            self.connection_label.setText(f"Connection: Disconnected")
            self.connection_label.setStyleSheet("color: red")
            self.connect_button.setText("Connect")
        
        if message:
            self.status_label.setText(f"Status: {message}")
    
    def select_port(self):
        """Open a dialog to select a port"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Select Serial Port")
        layout = QVBoxLayout()
        
        combo = QComboBox()
        for port in self.serial_reader.get_available_ports():
            combo.addItem(f"{port['device']}: {port['description']}", port['device'])
        
        layout.addWidget(combo)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        dialog.setLayout(layout)
        
        if dialog.exec_() == QDialog.Accepted:
            selected_port = combo.currentData()
            self.port_button.setText(selected_port)
            # Not connecting yet, wait for user to press Connect
            self.status_label.setText(f"Selected port: {selected_port}. Press Connect to use.")
    
    def toggle_connection(self):
        """Connect or disconnect from the serial port"""
        # Check current state
        if self.serial_reader.connected:
            self.serial_reader.disconnect()
        else:
            self.serial_reader.connect()
    
    def toggle_recording(self):
        """Start or stop recording data"""
        success, message = self.serial_reader.toggle_recording()
        
        if success:
            if self.serial_reader.recording:
                self.record_button.setText("Stop Recording")
            else:
                self.record_button.setText("Start Recording")
        
        self.status_label.setText(f"Status: {message}")
    
    def test_connection(self):
        """Test the serial connection"""
        success, message = self.serial_reader.test_connection()
        self.status_label.setText(f"Status: {message}")
    
    def save_spectrogram(self):
        """Save a spectrogram of the current data"""
        # Get the data
        eeg_data, _ = self.serial_reader.get_data()
        
        # Apply filters
        filtered_data = self.signal_processor.apply_filters(eeg_data)
        
        # Save the spectrogram
        success, message = self.signal_processor.save_spectrogram(filtered_data)
        self.status_label.setText(f"Status: {message}")
    
    def update_filter_settings(self):
        """Update filter settings from the UI controls"""
        # Get filter values from dropdown menus
        highpass_text = self.highpass_combo.currentText()
        if highpass_text == "Off":
            self.settings.filter_settings['highpass'] = 0
        else:
            self.settings.filter_settings['highpass'] = float(highpass_text.split()[0])
        
        lowpass_text = self.lowpass_combo.currentText()
        if lowpass_text == "Off":
            self.settings.filter_settings['lowpass'] = self.settings.sampling_rate / 2
        else:
            self.settings.filter_settings['lowpass'] = float(lowpass_text.split()[0])
        
        notch_text = self.notch_combo.currentText()
        if notch_text == "Off":
            self.settings.filter_settings['notch'] = 0
        else:
            self.settings.filter_settings['notch'] = float(notch_text.split()[0])
        
        # Update status label
        self.status_label.setText(
            f"Filters updated: HP {highpass_text}, LP {lowpass_text}, Notch {notch_text}"
        )
        
        # Emit signal to update plots
        self.filter_changed.emit()
    
    def update_sensitivity(self):
        """Update sensitivity setting from slider"""
        value = self.sensitivity_slider.value()
        self.settings.display_settings['sensitivity'] = value / 5.0  # 0.2 to 2.0
        
        # Update status label
        self.status_label.setText(
            f"Sensitivity: {self.settings.display_settings['sensitivity']:.1f}x"
        )
        
        # Emit signal to update plots
        self.display_changed.emit()
    
    def update_display_speed(self):
        """Update display speed setting"""
        speed_text = self.speed_combo.currentText()
        speed = float(speed_text.split()[0])
        self.settings.display_speed = speed
        
        # Update display duration based on chosen speed to maintain consistent window width
        # Standard EEG displays are 10 seconds wide at 25 mm/s
        self.settings.display_duration = 250 / speed
        
        # Update status label
        self.status_label.setText(
            f"Display speed: {speed} mm/s, Duration: {self.settings.display_duration:.1f} s"
        )
        
        # Emit signal to update plots
        self.display_changed.emit()