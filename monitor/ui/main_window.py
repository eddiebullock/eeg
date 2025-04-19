"""
Main window for the EEG Monitor application.
"""

import sys
import os
from pathlib import Path

# Get the absolute path to the project directory and ui directory
project_dir = str(Path(__file__).parent.parent.absolute())
ui_dir = str(Path(__file__).parent.absolute())

# Add both directories to Python's path
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)
if ui_dir not in sys.path:
    sys.path.insert(0, ui_dir)

from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout
from PyQt5.QtCore import QTimer

# Import directly using absolute paths
from ui.eeg_plot import EEGPlot
from ui.spectrogram_plot import SpectrogramPlot
from ui.controls import ControlPanel
from acquisition.serial_reader import SerialReader
from signal_processing.filters import SignalProcessor
from data.data_manager import DataManager

class EEGMonitorWindow(QMainWindow):
    """Main window for the EEG Monitor application"""
    
    def __init__(self, settings):
        super().__init__()
        
        # Store settings
        self.settings = settings
        
        # Initialize components
        self.setup_components()
        
        # Set up UI
        self.init_ui()
        
        # Setup timers
        self.setup_timers()
    
    def setup_components(self):
        """Initialize application components"""
        # Data acquisition
        self.serial_reader = SerialReader(self.settings)
        
        # Signal processing
        self.signal_processor = SignalProcessor(self.settings)
        
        # Data management
        self.data_manager = DataManager(self.settings)
        
        # Connect signals
        self.serial_reader.data_updated.connect(self.update_plots)
        self.serial_reader.connection_changed.connect(self.handle_connection_change)
    
    def init_ui(self):
        """Initialize the user interface"""
        # Set window properties
        self.setWindowTitle("Real-Time EEG Monitor")
        self.resize(1200, 800)
        
        # Create central widget and layout
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Create plots
        self.eeg_plot = EEGPlot(self.settings)
        self.spectrogram_plot = SpectrogramPlot(self.settings)
        
        # Create control panel
        self.control_panel = ControlPanel(
            self.settings, 
            self.serial_reader,
            self.signal_processor,
            self.data_manager
        )
        
        # Connect control panel signals
        self.control_panel.filter_changed.connect(self.update_plots)
        self.control_panel.display_changed.connect(self.handle_display_change)
        
        # Add widgets to layout
        main_layout.addWidget(self.eeg_plot, stretch=2)
        main_layout.addWidget(self.spectrogram_plot, stretch=2)
        main_layout.addWidget(self.control_panel, stretch=1)
    
    # Rest of your code remains the same
    def setup_timers(self):
        """Set up periodic update timers"""
        # Timer for updating the EEG display
        self.display_timer = QTimer(self)
        self.display_timer.timeout.connect(self.update_eeg_display)
        self.display_timer.start(self.settings.update_interval)
        
        # Timer for updating the spectrogram
        self.spec_timer = QTimer(self)
        self.spec_timer.timeout.connect(self.update_spectrogram)
        self.spec_timer.start(self.settings.spectrogram_update)
        
        # Timer for checking connection status
        self.conn_timer = QTimer(self)
        self.conn_timer.timeout.connect(self.check_connection)
        self.conn_timer.start(5000)  # Check connection every 5 seconds
    
    def update_plots(self):
        """Signal handler for when new data is available"""
        # Just trigger the display update
        self.update_eeg_display()
        
    def update_eeg_display(self):
        """Update the EEG plot with the latest data"""
        # Get the data from the serial reader
        eeg_data, time_data = self.serial_reader.get_data()
        
        if len(eeg_data) < 10:
            return
            
        # Apply filters
        filtered_data = self.signal_processor.apply_filters(eeg_data)
        
        # Scale the data by sensitivity
        scaled_data = filtered_data * self.settings.display_settings['sensitivity']
        
        # Update the plot
        self.eeg_plot.update_plot(time_data, scaled_data)
    
    def update_spectrogram(self):
        """Update the spectrogram plot"""
        # Get the data from the serial reader
        eeg_data, _ = self.serial_reader.get_data()
        
        if len(eeg_data) < self.settings.sampling_rate:
            return
            
        # Apply filters
        filtered_data = self.signal_processor.apply_filters(eeg_data)
        
        # Calculate spectrogram
        freqs, times, power, min_freq, max_freq = self.signal_processor.calculate_spectrogram(filtered_data)
        
        if freqs is None:
            return
            
        # Update the plot
        self.spectrogram_plot.update_plot(freqs, times, power, min_freq, max_freq)
    
    def check_connection(self):
        """Check and update the connection status"""
        status, message = self.serial_reader.get_connection_status()
        self.control_panel.update_connection_status(status, message)
    
    def handle_connection_change(self, connected, message):
        """Handle connection status changes"""
        self.control_panel.update_connection_status(connected, message)
    
    def handle_display_change(self):
        """Handle changes to display settings"""
        # Update the buffer sizes
        self.settings.update_display_buffer_size()
        
        # Update plot configurations
        self.eeg_plot.update_display_settings()
        self.spectrogram_plot.update_display_settings()
    
    def closeEvent(self, event):
        """Handle window close event"""
        # Clean up resources
        if hasattr(self, 'serial_reader'):
            self.serial_reader.disconnect()
        super().closeEvent(event)