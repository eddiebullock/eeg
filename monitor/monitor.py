import serial
import serial.tools.list_ports
import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore
from collections import deque
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
import sys
from scipy.signal import spectrogram
import time
import os

class RealEEGMonitor:
    def __init__(self):
        # Configuration parameters
        self.SERIAL_PORT = '/dev/cu.usbserial-0001'  # macOS USB serial port
        self.BAUD_RATE = 115200
        self.SAMPLING_RATE = 500  # Hz
        
        # Buffer sizes
        self.DISPLAY_WINDOW = 20  # seconds of data to display in time domain
        self.SPECTROGRAM_WINDOW = 20  # seconds of data for spectrogram
        self.UPDATE_INTERVAL = 20  # seconds between complete display updates
        
        # Derived values
        self.display_buffer_size = int(self.DISPLAY_WINDOW * self.SAMPLING_RATE)
        self.spectrogram_buffer_size = int(self.SPECTROGRAM_WINDOW * self.SAMPLING_RATE)
        
        # Data buffers
        self.eeg_buffer = deque(maxlen=self.spectrogram_buffer_size)
        
        # File saving
        self.recording = False
        self.output_file = None
        self.start_time = None
        
        # Setup serial connection
        self.ser = None
        try:
            self.ser = serial.Serial(self.SERIAL_PORT, self.BAUD_RATE)
            print(f"Connected to {self.SERIAL_PORT}")
        except Exception as e:
            print(f"Could not connect to serial port: {e}")
            print("Available ports:")
            for port in serial.tools.list_ports.comports():
                print(f"  {port.device}: {port.description}")
            # Continue with the program anyway to allow user to change port
        
        # Initialize GUI
        self.init_gui()
        
        # Data reading timer (faster than display updates)
        self.data_timer = QtCore.QTimer()
        self.data_timer.timeout.connect(self.read_serial_data)
        self.data_timer.start(10)  # Read data every 10ms
    
    def init_gui(self):
        # Create application and main window
        self.app = QApplication(sys.argv)
        self.main_window = QWidget()
        self.main_window.setWindowTitle("Real EEG Monitor (20-second updates)")
        self.main_window.resize(1200, 800)
        
        # Create main layout
        main_layout = QVBoxLayout()
        self.main_window.setLayout(main_layout)
        
        # Create graphics window for plots
        self.graph_widget = pg.GraphicsLayoutWidget()
        main_layout.addWidget(self.graph_widget)
        
        # Create time domain plot
        self.time_plot = self.graph_widget.addPlot(row=0, col=0)
        self.time_plot.setLabel('left', 'Amplitude')
        self.time_plot.setLabel('bottom', 'Time (s)')
        self.time_plot.setTitle('Raw EEG Signal (Last 20 seconds)')
        self.time_curve = self.time_plot.plot(pen='y')
        
        # Add grid to time plot for better readability
        self.time_plot.showGrid(x=True, y=True, alpha=0.3)
        
        # Create spectrogram plot
        self.graph_widget.nextRow()
        self.spec_plot = self.graph_widget.addPlot(row=1, col=0)
        self.spec_plot.setLabel('left', 'Frequency (Hz)')
        self.spec_plot.setLabel('bottom', 'Time (s)')
        self.spec_plot.setTitle('EEG Spectrogram (Last 20 seconds)')
        
        # Create spectrogram image item
        self.spec_img = pg.ImageItem()
        self.spec_plot.addItem(self.spec_img)
        
        # Add colorbar
        self.colorbar = pg.ColorBarItem(values=(0, 50), colorMap='viridis')
        self.colorbar.setImageItem(self.spec_img)
        
        # Create control panel
        control_layout = QHBoxLayout()
        main_layout.addLayout(control_layout)
        
        # Create connection status indicator
        self.connection_label = QLabel("Connection: Disconnected")
        self.connection_label.setStyleSheet("color: red")
        control_layout.addWidget(self.connection_label)
        
        # Create port selection
        self.port_label = QLabel("Port:")
        control_layout.addWidget(self.port_label)
        
        # Create port selection button
        self.port_button = QPushButton(self.SERIAL_PORT)
        self.port_button.clicked.connect(self.select_port)
        control_layout.addWidget(self.port_button)
        
        # Create connect button
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.connect_serial)
        control_layout.addWidget(self.connect_button)
        
        # Create status label
        self.status_label = QLabel("Status: Waiting for data")
        control_layout.addWidget(self.status_label)
        
        # Create record button
        self.record_button = QPushButton("Start Recording")
        self.record_button.clicked.connect(self.toggle_recording)
        control_layout.addWidget(self.record_button)
        
        # Create save spectrogram button
        self.save_button = QPushButton("Save Spectrogram")
        self.save_button.clicked.connect(self.save_spectrogram)
        control_layout.addWidget(self.save_button)
        
        # Create serial test button
        self.test_button = QPushButton("Test Connection")
        self.test_button.clicked.connect(self.test_serial_connection)
        control_layout.addWidget(self.test_button)
        
        # Update the connection status
        self.update_connection_status()
        
        # Setup update timer for display
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(int(self.UPDATE_INTERVAL * 1000))  # Convert to milliseconds
        
        # Setup connection check timer
        self.conn_timer = QtCore.QTimer()
        self.conn_timer.timeout.connect(self.check_connection)
        self.conn_timer.start(5000)  # Check connection every 5 seconds
        
        # Show the window
        self.main_window.show()
    
    def select_port(self):
        """Open a dialog to select a port"""
        from PyQt5.QtWidgets import QDialog, QComboBox, QVBoxLayout, QDialogButtonBox
        
        dialog = QDialog(self.main_window)
        dialog.setWindowTitle("Select Serial Port")
        layout = QVBoxLayout()
        
        combo = QComboBox()
        for port in serial.tools.list_ports.comports():
            combo.addItem(f"{port.device}: {port.description}", port.device)
        
        layout.addWidget(combo)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        dialog.setLayout(layout)
        
        if dialog.exec_() == QDialog.Accepted:
            selected_port = combo.currentData()
            self.SERIAL_PORT = selected_port
            self.port_button.setText(selected_port)
            # Not connecting yet, wait for user to press Connect
            self.status_label.setText(f"Selected port: {selected_port}. Press Connect to use.")
    
    def connect_serial(self):
        """Connect to the selected serial port"""
        try:
            # Close existing connection if any
            if self.ser and self.ser.is_open:
                self.ser.close()
            
            # Open new connection
            self.ser = serial.Serial(self.SERIAL_PORT, self.BAUD_RATE)
            self.update_connection_status()
            self.status_label.setText(f"Connected to {self.SERIAL_PORT}")
        except Exception as e:
            self.status_label.setText(f"Error connecting: {str(e)}")
            self.update_connection_status()
    
    def update_connection_status(self):
        """Update the connection status label"""
        if self.ser and self.ser.is_open:
            self.connection_label.setText("Connection: Connected")
            self.connection_label.setStyleSheet("color: green")
            self.connect_button.setText("Disconnect")
        else:
            self.connection_label.setText("Connection: Disconnected")
            self.connection_label.setStyleSheet("color: red")
            self.connect_button.setText("Connect")
    
    def check_connection(self):
        """Check if we're still receiving data"""
        if not self.ser:
            return
            
        try:
            # Just check if the serial port is still open
            if not self.ser.is_open:
                self.update_connection_status()
            else:
                bytes_waiting = self.ser.in_waiting
                self.connection_label.setText(f"Connection: Active ({bytes_waiting} bytes waiting)")
                self.connection_label.setStyleSheet("color: green")
        except:
            self.update_connection_status()
    
    def test_serial_connection(self):
        """Test the serial connection by reading a few bytes"""
        if not self.ser or not self.ser.is_open:
            self.status_label.setText("Connection test: Not connected to any port.")
            return
            
        try:
            bytes_waiting = self.ser.in_waiting
            if bytes_waiting > 0:
                # Read a sample to verify data format
                sample_data = self.ser.read(min(bytes_waiting, 20))
                hex_data = ' '.join(f'{b:02x}' for b in sample_data)
                self.status_label.setText(f"Connection test: Data received ({len(sample_data)} bytes): {hex_data}")
            else:
                self.status_label.setText("Connection test: No data in buffer. Verify device is sending data.")
        except Exception as e:
            self.status_label.setText(f"Connection test error: {str(e)}")
    
    def toggle_recording(self):
        if not self.recording:
            # Start recording
            if not self.ser or not self.ser.is_open:
                self.status_label.setText("Error: Not connected to any port. Cannot record.")
                return
                
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            self.output_filename = f"EEG_RECORDING_{timestamp}.dat"
            try:
                self.output_file = open(self.output_filename, 'wb')
                self.recording = True
                self.start_time = time.time()
                self.record_button.setText("Stop Recording")
                self.status_label.setText(f"Status: Recording to {self.output_filename}")
            except Exception as e:
                self.status_label.setText(f"Error starting recording: {e}")
        else:
            # Stop recording
            if self.output_file:
                self.output_file.close()
                duration = time.time() - self.start_time
                self.status_label.setText(f"Status: Saved {self.output_filename} ({duration:.1f} sec)")
                self.output_file = None
            self.recording = False
            self.record_button.setText("Start Recording")
    
    def save_spectrogram(self):
        if len(self.eeg_buffer) >= self.spectrogram_buffer_size:
            try:
                # Generate filename
                timestamp = time.strftime("%Y%m%d-%H%M%S")
                spec_filename = f"EEG_SPEC_{timestamp}.png"
                
                # Create a matplotlib figure for saving
                import matplotlib.pyplot as plt
                
                # Generate spectrogram using scipy
                data_array = np.array(list(self.eeg_buffer))
                f, t, Sxx = spectrogram(
                    data_array,
                    fs=self.SAMPLING_RATE,
                    nperseg=1024,
                    noverlap=512,
                    scaling='density',
                    detrend='constant'
                )
                
                # Filter frequencies
                freq_mask = (f >= 0.5) & (f <= 100)
                f_filtered = f[freq_mask]
                Sxx_filtered = Sxx[freq_mask, :]
                
                # Plot and save
                plt.figure(figsize=(10, 6))
                plt.pcolormesh(t, f_filtered, 10 * np.log10(Sxx_filtered + 1e-10), shading='gouraud')
                plt.colorbar(label='Power (dB)')
                plt.ylabel('Frequency (Hz)')
                plt.xlabel('Time (s)')
                plt.title(f'EEG Spectrogram - {timestamp}')
                plt.ylim(0.5, 100)
                plt.tight_layout()
                plt.savefig(spec_filename)
                plt.close()
                
                self.status_label.setText(f"Status: Saved spectrogram to {spec_filename}")
            except Exception as e:
                self.status_label.setText(f"Error saving spectrogram: {e}")
        else:
            self.status_label.setText("Error: Not enough data for spectrogram")
    
    def read_serial_data(self):
        # Read all available data from serial port
        if not self.ser or not self.ser.is_open:
            return
            
        try:
            bytes_to_read = self.ser.in_waiting
            if bytes_to_read >= 2:  # Each sample is 2 bytes
                # Read data in chunks of 2 bytes
                num_samples = bytes_to_read // 2
                for _ in range(num_samples):
                    data = self.ser.read(2)
                    if len(data) == 2:
                        # Convert to integer (16-bit signed)
                        try:
                            value = int.from_bytes(data, byteorder='little', signed=True)
                            
                            # Add to buffer
                            self.eeg_buffer.append(value)
                            
                            # Save to file if recording
                            if self.recording and self.output_file:
                                self.output_file.write(data)
                        except Exception as e:
                            print(f"Error processing data byte: {e}")
        except Exception as e:
            print(f"Error reading serial data: {e}")
            self.update_connection_status()
    
    def update_time_plot(self):
        # Get the last full window of data
        display_data = list(self.eeg_buffer)[-self.display_buffer_size:]
        
        # Pad with zeros if we don't have enough data yet
        if len(display_data) < self.display_buffer_size:
            padding = [0] * (self.display_buffer_size - len(display_data))
            display_data = padding + display_data
        
        # Create time axis from 0 to DISPLAY_WINDOW
        fixed_time_axis = np.linspace(0, self.DISPLAY_WINDOW, self.display_buffer_size)
        
        # Update time plot with fixed time axis
        self.time_curve.setData(fixed_time_axis, display_data)
        
        # Set fixed range for time axis to prevent auto-scaling
        self.time_plot.setXRange(0, self.DISPLAY_WINDOW)
    
    def update_spectrogram(self):
        # Only update spectrogram if we have enough data
        if len(self.eeg_buffer) >= self.spectrogram_buffer_size:
            # Convert deque to numpy array - take exactly one window of data
            data_array = np.array(list(self.eeg_buffer)[-self.spectrogram_buffer_size:])
            
            # Calculate spectrogram
            f, t, Sxx = spectrogram(
                data_array,
                fs=self.SAMPLING_RATE,
                nperseg=1024,
                noverlap=768,  # Higher overlap for smoother visuals
                scaling='density',
                detrend='constant'
            )
            
            # Filter frequencies
            freq_mask = (f >= 0.5) & (f <= 100)
            f_filtered = f[freq_mask]
            Sxx_filtered = Sxx[freq_mask, :]
            
            # Convert to dB
            Sxx_db = 10 * np.log10(Sxx_filtered + 1e-10)  # Add small value to avoid log(0)
            
            # Update the image
            self.spec_img.setImage(Sxx_db)
            
            # Set the correct scale for x and y axes - use fixed time range from 0 to SPECTROGRAM_WINDOW
            self.spec_img.setRect(QtCore.QRectF(0, f_filtered[0], self.SPECTROGRAM_WINDOW, f_filtered[-1] - f_filtered[0]))
            
            # Update colorbar range
            self.colorbar.setLevels((np.min(Sxx_db), np.max(Sxx_db)))
            
            # Set fixed x-range
            self.spec_plot.setXRange(0, self.SPECTROGRAM_WINDOW)
    
    def update(self):
        # Check if we have enough data for a full window
        data_collected = len(self.eeg_buffer)
        buffer_percentage = (data_collected / self.spectrogram_buffer_size) * 100
            
        # Update plots
        self.update_time_plot()
        self.update_spectrogram()
        
        # Update status to show when the display was last refreshed
        current_time = time.strftime("%H:%M:%S", time.localtime())
        
        if data_collected < self.spectrogram_buffer_size:
            self.status_label.setText(
                f"Status: Collecting data ({buffer_percentage:.1f}% complete) at {current_time}"
            )
        else:
            self.status_label.setText(
                f"Status: Display updated at {current_time} (Updates every {self.UPDATE_INTERVAL} seconds)"
            )
    
    def run(self):
        # Start the application event loop
        sys.exit(self.app.exec_())
    
    def __del__(self):
        # Clean up
        if hasattr(self, 'ser') and self.ser and self.ser.is_open:
            self.ser.close()
        if hasattr(self, 'recording') and self.recording and hasattr(self, 'output_file') and self.output_file:
            self.output_file.close()

# Run the application
if __name__ == "__main__":
    print("Starting real EEG monitor...")
    monitor = RealEEGMonitor()
    monitor.run()