"""
EEG waveform plot for the EEG Monitor application.
"""

import numpy as np
import pyqtgraph as pg
from PyQt5.QtCore import Qt

class EEGPlot(pg.GraphicsLayoutWidget):
    """Widget for displaying real-time EEG waveform"""
    
    def __init__(self, settings):
        super().__init__()
        
        self.settings = settings
        self.init_plot()
    
    def init_plot(self):
        """Initialize the plot components"""
        # Create the plot
        self.plot = self.addPlot(row=0, col=0)
        self.plot.setLabel('left', 'Amplitude (μV)')
        self.plot.setLabel('bottom', 'Time (s)')
        self.plot.setTitle('Real-Time EEG')
        
        # Add grid lines to EEG plot (resembling EEG paper)
        self.plot.showGrid(x=True, y=True, alpha=0.3)
        
        # Create scrolling line for EEG
        self.curve = self.plot.plot(pen=(255, 255, 0))
        
        # Add amplitude markers (μV divisions)
        self.add_amplitude_markers()
        
        # Add time markers
        self.add_time_markers()
        
        # Set initial range
        self.update_display_settings()
        
        # Disable auto-ranging to maintain fixed scale
        self.plot.enableAutoRange(False)
        
        # Ensure x-axis doesn't auto-range
        self.plot.setXRange(0, self.settings.display_duration)
    
    def add_amplitude_markers(self):
        """Add horizontal lines marking amplitude divisions"""
        # Clear existing horizontal lines
        for item in list(self.plot.items):
            if isinstance(item, pg.InfiniteLine) and item.angle == 0:
                self.plot.removeItem(item)
        
        # Add amplitude markers (μV divisions)
        scale = self.settings.display_settings['scale']
        for i in range(-5, 6):
            if i == 0:
                # Thicker line for zero
                hLine = pg.InfiniteLine(pos=i*scale, angle=0, 
                                      pen=pg.mkPen('w', width=1))
            else:
                hLine = pg.InfiniteLine(pos=i*scale, angle=0, 
                                      pen=pg.mkPen('w', width=0.5, style=Qt.DashLine))
            self.plot.addItem(hLine)
    
    def add_time_markers(self):
        """Add vertical lines marking time divisions"""
        # Clear existing vertical lines
        for item in list(self.plot.items):
            if isinstance(item, pg.InfiniteLine) and item.angle == 90:
                self.plot.removeItem(item)
        
        # Add new time markers every second or half-second depending on display duration
        display_duration = self.settings.display_duration
        marker_interval = 0.5 if display_duration <= 5 else 1
        
        for i in np.arange(marker_interval, display_duration, marker_interval):
            vLine = pg.InfiniteLine(pos=i, angle=90, pen=pg.mkPen('w', width=0.5, style=Qt.DashLine))
            self.plot.addItem(vLine)
    
    def update_display_settings(self):
        """Update display when settings change"""
        # Update amplitude markers
        self.add_amplitude_markers()
        
        # Update time markers
        self.add_time_markers()
        
        # Update Y range to match sensitivity
        scale_factor = 5 * self.settings.display_settings['scale']
        self.plot.setYRange(-scale_factor, scale_factor)
        
        # Update X range for display duration
        self.plot.setXRange(0, self.settings.display_duration)
    
    def update_plot(self, time_data, eeg_data):
        """Update the plot with new data
        
        Args:
            time_data: List of timestamps
            eeg_data: List of EEG values
        """
        if len(time_data) < 2 or len(eeg_data) < 2:
            return
            
        # Convert to numpy arrays if they aren't already
        times = np.array(time_data)
        values = np.array(eeg_data)
        
        # Check if we received any data
        if len(times) == 0:
            return
            
        # Prepare display data - fixed window approach
        display_duration = self.settings.display_duration
        
        # Get the most recent time
        most_recent_time = times[-1]
        
        # Calculate the start time for our display window
        window_start = most_recent_time - display_duration
        
        # Filter data to only show what's in our display window
        mask = times >= window_start
        display_times = times[mask]
        display_values = values[mask]
        
        # Normalize times to display window
        normalized_times = display_times - window_start
        
        # Update the curve
        self.curve.setData(normalized_times, display_values)