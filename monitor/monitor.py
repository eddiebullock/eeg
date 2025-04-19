import serial
import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore
from collections import deque
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
import sys
from scipy.signal import spectrogram
import time
import os

class ContinuousEEGMonitor:
    def __init__(self):
        # Configuration parameters
        self.SERIAL_PORT = 'COM4'  # Replace with your COM port
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
        self.time_axis = np.linspace(-self.DISPLAY_WINDOW, 0, self.display_buffer_size)
        
        # File saving
        self.recording = False
        self.output_file = None
        self.start_time = None
        
        # Setup serial connection
        try:
            self.ser = serial.Serial(self.SERIAL_PORT, self.BAUD_RATE)
            print(f"Connected to {self.SERIAL_PORT}")
        except Exception as e:
            print(f"Could not connect to serial port: {e}")
            sys.exit(1)
        
        # Initialize GUI
        self.init_gui()
    
    def init_gui(self):
        # Create application and main window
        self.app = QApplication(sys.argv)
        self.main_window = QWidget()
        self.main_window.setWindowTitle("Static EEG Monitor (20-second updates)")
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
        
        # Create status label
        self.status_label = QLabel("Status: Running")
        control_layout.addWidget(self.status_label)
        
        # Create record button
        self.record_button = QPushButton("Start Recording")
        self.record_button.clicked.connect(self.toggle_recording)
        control_layout.addWidget(self.record_button)
        
        # Create save spectrogram button
        self.save_button = QPushButton("Save Spectrogram")
        self.save_button.clicked.connect(self.save_spectrogram)
        control_layout.addWidget(self.save_button)
        
        # Setup update timer
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(int(self.UPDATE_INTERVAL * 1000))  # Convert to milliseconds
        
        # Show the window
        self.main_window.show()
    
    def toggle_recording(self):
        if not self.recording:
            # Start recording
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
                plt.pcolormesh(t, f_filtered, 10 * np.log10(Sxx_filtered), shading='gouraud')
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
    
    def read_serial_data(self):
        # Read all available data from serial port
        bytes_to_read = self.ser.in_waiting
        if bytes_to_read >= 2:  # Each sample is 2 bytes
            # Read data in chunks of 2 bytes
            num_samples = bytes_to_read // 2
            for _ in range(num_samples):
                data = self.ser.read(2)
                if len(data) == 2:
                    # Convert to integer (16-bit signed)
                    value = int.from_bytes(data, byteorder='little', signed=True)
                    
                    # Add to buffer
                    self.eeg_buffer.append(value)
                    
                    # Save to file if recording
                    if self.recording and self.output_file:
                        self.output_file.write(data)
    
    def update(self):
        # Read new data
        self.read_serial_data()
        
        # Check if we have enough data for a full window
        if len(self.eeg_buffer) >= self.spectrogram_buffer_size:
            # Update plots
            self.update_time_plot()
            self.update_spectrogram()
            
            # Update status to show when the display was last refreshed
            current_time = time.strftime("%H:%M:%S", time.localtime())
            self.status_label.setText(f"Status: Display updated at {current_time} (Updates every {self.UPDATE_INTERVAL} seconds)")
    
    def run(self):
        # Start the application event loop
        sys.exit(self.app.exec_())
    
    def __del__(self):
        # Clean up
        if self.ser.is_open:
            self.ser.close()
        if self.recording and self.output_file:
            self.output_file.close()

# Run the application
if __name__ == "__main__":
    monitor = ContinuousEEGMonitor()
    monitor.run()