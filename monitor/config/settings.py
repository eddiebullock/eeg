"""
Configuration settings for the EEG Monitor application.
"""

class Settings:
    """Configuration settings for the EEG Monitor application"""
    
    def __init__(self):
        # Serial connection settings
        self.serial_port = '/dev/cu.usbserial-0001'  # Default port for macOS
        self.baud_rate = 115200
        
        # Bluetooth settings
        self.use_bluetooth = True   # Prioritize Bluetooth connections
        self.bluetooth_device_name = "404-BrainNotFound"  # Name of Bluetooth EEG device
        
        # Sampling settings
        self.sampling_rate = 500  # Hz
        
        # Display settings
        self.display_duration = 10  # seconds of data to display
        self.display_speed = 25     # mm/sec - standard EEG paper speed
        self.update_interval = 20   # ms between display updates (50 Hz)
        
        # Spectrogram settings
        self.spectrogram_duration = 30  # seconds for spectrogram
        self.spectrogram_update = 500   # ms between spectrogram updates
        
        # Calculate derived values
        self.display_buffer_size = int(self.display_duration * self.sampling_rate)
        self.spectrogram_buffer_size = int(self.spectrogram_duration * self.sampling_rate)
        
        # Filter defaults
        self.filter_settings = {
            'highpass': 0.5,   # Hz
            'lowpass': 70,     # Hz
            'notch': 60,       # Hz (for power line noise)
            'enable_filter': True
        }
        
        # Display defaults
        self.display_settings = {
            'scale': 100,       # uV per division (vertical scale)
            'sensitivity': 1.0,  # Amplification factor
            'channel_count': 1   # For now, we have one channel
        }
    
    def update_display_buffer_size(self):
        """Update buffer sizes when settings change"""
        self.display_buffer_size = int(self.display_duration * self.sampling_rate)
        self.spectrogram_buffer_size = int(self.spectrogram_duration * self.sampling_rate)