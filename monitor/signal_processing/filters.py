"""
Signal processing filters for EEG Monitor.
"""

import numpy as np
from scipy.signal import butter, filtfilt, iirnotch, welch, spectrogram

class SignalProcessor:
    """Signal processing for EEG data"""
    
    def __init__(self, settings):
        """Initialize the signal processor
        
        Args:
            settings: Application settings
        """
        self.settings = settings
    
    def apply_filters(self, eeg_data):
        """Apply filters to EEG data
        
        Args:
            eeg_data: Raw EEG data array
            
        Returns:
            Filtered EEG data
        """
        # Convert to numpy array if it's not already
        data = np.array(eeg_data)
        
        # Check if we have enough data to filter
        if len(data) < 30:  # Minimum length to avoid filtfilt errors
            return data  # Return unfiltered data
            
        # Make a copy to avoid modifying the original data
        filtered_data = data.copy()
        
        # Only apply filters if enabled in settings
        if self.settings.filter_settings['enable_filter']:
            # Apply highpass filter if frequency > 0
            highpass = self.settings.filter_settings['highpass']
            if highpass > 0:
                b, a = self._butter_highpass(highpass, self.settings.sampling_rate)
                try:
                    filtered_data = filtfilt(b, a, filtered_data)
                except ValueError:
                    # If filter fails, continue with unfiltered data for this step
                    pass
            
            # Apply lowpass filter
            lowpass = self.settings.filter_settings['lowpass']
            if lowpass < self.settings.sampling_rate / 2:
                b, a = self._butter_lowpass(lowpass, self.settings.sampling_rate)
                try:
                    filtered_data = filtfilt(b, a, filtered_data)
                except ValueError:
                    # If filter fails, continue with current data
                    pass
            
            # Apply notch filter (for power line noise)
            notch = self.settings.filter_settings['notch']
            if notch > 0:
                b, a = self._iirnotch(notch, self.settings.sampling_rate)
                try:
                    filtered_data = filtfilt(b, a, filtered_data)
                except ValueError:
                    # If filter fails, continue with current data
                    pass
                
        return filtered_data
    
    def _butter_highpass(self, cutoff, fs, order=4):
        """Design a highpass Butterworth filter
        
        Args:
            cutoff: Cutoff frequency
            fs: Sampling frequency
            order: Filter order
            
        Returns:
            b, a: Filter coefficients
        """
        nyq = 0.5 * fs
        normal_cutoff = cutoff / nyq
        b, a = butter(order, normal_cutoff, btype='high', analog=False)
        return b, a
    
    def _butter_lowpass(self, cutoff, fs, order=4):
        """Design a lowpass Butterworth filter
        
        Args:
            cutoff: Cutoff frequency
            fs: Sampling frequency
            order: Filter order
            
        Returns:
            b, a: Filter coefficients
        """
        nyq = 0.5 * fs
        normal_cutoff = cutoff / nyq
        b, a = butter(order, normal_cutoff, btype='low', analog=False)
        return b, a
        
    def _iirnotch(self, cutoff, fs, Q=30):
        """Design a notch filter
        
        Args:
            cutoff: Cutoff frequency to remove
            fs: Sampling frequency
            Q: Quality factor
            
        Returns:
            b, a: Filter coefficients
        """
        nyq = 0.5 * fs
        normal_cutoff = cutoff / nyq
        b, a = iirnotch(normal_cutoff, Q)
        return b, a
    
    def calculate_spectrogram(self, eeg_data):
        """Calculate spectrogram from EEG data
        
        Args:
            eeg_data: EEG data array
            
        Returns:
            freqs: Frequency values
            times: Time values
            power: Power values
            min_freq: Minimum frequency displayed
            max_freq: Maximum frequency displayed
        """
        # Convert to numpy array if it's not already
        data = np.array(eeg_data)
        
        # Check if we have enough data
        if len(data) < self.settings.sampling_rate:
            return None, None, None, None, None
        
        # Calculate spectrogram
        fs = self.settings.sampling_rate
        nperseg = int(fs * 2)  # 2-second segments
        noverlap = nperseg // 2  # 50% overlap
        
        try:
            freqs, times, Sxx = spectrogram(
                data, 
                fs=fs, 
                window='hanning',
                nperseg=nperseg,
                noverlap=noverlap,
                detrend='constant',
                scaling='density'
            )
            
            # Convert to dB scale (log scale is better for visualization)
            # Add small value to avoid log(0)
            Sxx_db = 10 * np.log10(Sxx + 1e-10)
            
            # Set frequency range
            min_freq = 0
            max_freq = 70  # Only show up to 70 Hz
            
            return freqs, times, Sxx_db, min_freq, max_freq
            
        except Exception as e:
            print(f"Error calculating spectrogram: {e}")
            return None, None, None, None, None
            
    def calculate_bands(self, eeg_data):
        """Calculate power in different frequency bands
        
        Args:
            eeg_data: EEG data array
            
        Returns:
            Dictionary with band powers
        """
        # Define frequency bands
        bands = {
            'delta': (0.5, 4),
            'theta': (4, 8),
            'alpha': (8, 13),
            'beta': (13, 30),
            'gamma': (30, 70)
        }
        
        # Calculate power spectrum using Welch's method
        fs = self.settings.sampling_rate
        
        # Check if we have enough data
        if len(eeg_data) < fs * 2:
            return {band: 0 for band in bands}
            
        try:
            freqs, psd = welch(eeg_data, fs, nperseg=fs*2)
            
            # Calculate power in each band
            band_powers = {}
            for band, (low, high) in bands.items():
                # Find indices of frequencies in the band
                idx_band = np.logical_and(freqs >= low, freqs <= high)
                # Calculate mean power in the band
                band_powers[band] = np.mean(psd[idx_band])
                
            return band_powers
            
        except Exception as e:
            print(f"Error calculating band powers: {e}")
            return {band: 0 for band in bands}