"""
Spectrogram plot for the EEG Monitor application.
"""

import pyqtgraph as pg
from PyQt5.QtCore import Qt, QRectF

class SpectrogramPlot(pg.GraphicsLayoutWidget):
    """Widget for displaying real-time EEG spectrogram"""
    
    def __init__(self, settings):
        super().__init__()
        
        self.settings = settings
        self.init_plot()
    
    def init_plot(self):
        """Initialize the plot components"""
        # Create the plot
        self.plot = self.addPlot(row=0, col=0)
        self.plot.setLabel('left', 'Frequency (Hz)')
        self.plot.setLabel('bottom', 'Time (s)')
        self.plot.setTitle('EEG Frequency Analysis (Real-time)')
        
        # Create spectrogram image item
        self.img = pg.ImageItem()
        self.plot.addItem(self.img)
        
        # Add colorbar for spectrogram
        self.colorbar = pg.ColorBarItem(values=(0, 50), colorMap='viridis')
        self.colorbar.setImageItem(self.img)
        
        # Add frequency band markers and labels
        self.add_frequency_bands()
    
    def add_frequency_bands(self):
        """Add frequency band indicators to the plot"""
        # Define frequency ranges and labels
        freq_ranges = [
            (0.5, 4, 'Delta'),
            (4, 8, 'Theta'),
            (8, 13, 'Alpha'),
            (13, 30, 'Beta'),
            (30, 70, 'Gamma')
        ]
        
        # Add horizontal lines marking frequency bands
        for low, high, band in freq_ranges:
            # Add a line at each boundary
            line = pg.InfiniteLine(pos=low, angle=0, pen=pg.mkPen('w', width=0.5, style=Qt.DashLine))
            self.plot.addItem(line)
            
            # Add a label for the band (in the middle of its range)
            mid = (low + high) / 2
            text = pg.TextItem(text=band, color=(255, 255, 255, 150), anchor=(0, 0.5))
            text.setPos(0, mid)
            self.plot.addItem(text)
        
        # Add a line at the top boundary of the highest band
        line = pg.InfiniteLine(pos=70, angle=0, pen=pg.mkPen('w', width=0.5, style=Qt.DashLine))
        self.plot.addItem(line)
    
    def update_display_settings(self):
        """Update display when settings change"""
        # No specific settings to update for spectrogram currently
        pass
    
    def update_plot(self, freqs, times, power, min_freq, max_freq):
        """Update the spectrogram with new data
        
        Args:
            freqs: Array of frequency values
            times: Array of time values
            power: 2D array of power values (freq x time)
            min_freq: Minimum frequency to display
            max_freq: Maximum frequency to display
        """
        if power is None or len(times) == 0:
            return
            
        # Transpose the image data to correctly align frequency and time
        # This ensures frequencies are plotted on the Y axis and time on the X axis
        power_transposed = power.T
        
        # Update the image
        self.img.setImage(power_transposed)
        
        # Set the correct scale for x and y axes
        duration = times[-1]  # Duration of the analyzed window in seconds
        self.img.setRect(QRectF(0, min_freq, duration, max_freq - min_freq))
        
        # Set axes limits explicitly to ensure proper scaling
        self.plot.setXRange(0, duration)
        self.plot.setYRange(min_freq, max_freq)
        
        # Update colorbar range
        self.colorbar.setLevels((power.min(), power.max()))
        
        # Make sure Greek letters and frequency band labels are visible
        if not hasattr(self, 'freq_bands_added'):
            self.freq_bands_added = True
            band_labels = [
                (4, "δ Delta"),
                (8, "θ Theta"),
                (13, "α Alpha"),
                (30, "β Beta"),
                (70, "γ Gamma")
            ]
            
            for freq, label in band_labels:
                text_item = pg.TextItem(text=label, color=(255, 255, 255), anchor=(0, 0.5))
                text_item.setPos(duration * 0.02, freq)
                self.plot.addItem(text_item)