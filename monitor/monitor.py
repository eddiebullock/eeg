import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore
from collections import deque
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
import sys
from scipy.signal import spectrogram
import time
import os

class SimulatedEEGMonitor:
    def __init__(self):
        # Configuration parameters
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
        
        # Simulation parameters
        self.simulation_freq = [3, 10, 30]  # Hz - simulate alpha, beta, theta waves
        self.simulation_amp = [10, 5, 2]    # Amplitudes
        self.noise_level = 2                # Background noise level
        self.sample_counter = 0             # Counter for generating samples
        
        # Initialize GUI
        self.init_gui()
        
        # Initial buffer fill with simulated data
        print("Generating initial data...")
        self.generate_initial_data()
        print("Done generating initial data.")
    
    def init_gui(self):
        # Create application and main window
        self.app = QApplication(sys.argv)
        self.main_window = QWidget()
        self.main_window.setWindowTitle("Simulated EEG Monitor (20-second updates)")
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
        self.time_plot.setTitle('Simulated EEG Signal (Last 20 seconds)')
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
        self.status_label = QLabel("Status: Generating simulated EEG data")
        control_layout.addWidget(self.status_label)
        
        # Create record button
        self.record_button = QPushButton("Start Recording")
        self.record_button.clicked.connect(self.toggle_recording)
        control_layout.addWidget(self.record_button)
        
        # Create save spectrogram button
        self.save_button = QPushButton("Save Spectrogram")
        self.save_button.clicked.connect(self.save_spectrogram)
        control_layout.addWidget(self.save_button)
        
        # Add frequency adjustment buttons
        self.alpha_button = QPushButton("More Alpha (8-13 Hz)")
        self.alpha_button.clicked.connect(self.increase_alpha)
        control_layout.addWidget(self.alpha_button)
        
        self.beta_button = QPushButton("More Beta (13-30 Hz)")
        self.beta_button.clicked.connect(self.increase_beta)
        control_layout.addWidget(self.beta_button)
        
        # Setup update timer
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(int(self.UPDATE_INTERVAL * 1000))  # Convert to milliseconds
        
        # Also add a faster timer for continuous data generation
        self.data_timer = QtCore.QTimer()
        self.data_timer.timeout.connect(self.generate_data)
        self.data_timer.start(50)  # Generate data every 50ms
        
        # Show the window
        self.main_window.show()
    
    def increase_alpha(self):
        self.simulation_amp[0] += 5
        self.status_label.setText(f"Status: Increased alpha waves (8-13 Hz)")
    
    def increase_beta(self):
        self.simulation_amp[1] += 5
        self.status_label.setText(f"Status: Increased beta waves (13-30 Hz)")
    
    def generate_sample(self):
        # Generate a sample based on simulated brain waves
        t = self.sample_counter / self.SAMPLING_RATE
        
        # Create signals for different brain wave bands
        sample = 0
        for freq, amp in zip(self.simulation_freq, self.simulation_amp):
            sample += amp * np.sin(2 * np.pi * freq * t)
        
        # Add random noise
        sample += np.random.normal(0, self.noise_level)
        
        # Add occasional artifacts
        if np.random.random() < 0.001:  # 0.1% chance of artifact
            sample += np.random.normal(0, 50)  # Big spike
        
        self.sample_counter += 1
        return int(sample)
    
    def generate_initial_data(self):
        # Generate a full buffer of data
        for _ in range(self.spectrogram_buffer_size):
            sample = self.generate_sample()
            self.eeg_buffer.append(sample)
    
    def generate_data(self):
        # Generate a few new samples each time this is called
        num_samples = 20  # Generate 20 samples (about 40ms of data at 500Hz)
        for _ in range(num_samples):
            sample = self.generate_sample()
            self.eeg_buffer.append(sample)
            
            # Save to file if recording
            if self.recording and self.output_file:
                value_bytes = sample.to_bytes(2, byteorder='little', signed=True)
                self.output_file.write(value_bytes)
    
    def toggle_recording(self):
        if not self.recording:
            # Start recording
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            self.output_filename = f"SIMULATED_EEG_{timestamp}.dat"
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
                spec_filename = f"SIMULATED_EEG_SPEC_{timestamp}.png"
                
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
                plt.title(f'Simulated EEG Spectrogram - {timestamp}')
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
    
    def update(self):
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
        if self.recording and self.output_file:
            self.output_file.close()

# Run the application
if __name__ == "__main__":
    print("Starting simulated EEG monitor...")
    monitor = SimulatedEEGMonitor()
    monitor.run()