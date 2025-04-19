"""
Data management for EEG Monitor.
Handles data storage, loading, and export.
"""

import os
import time
import numpy as np

class DataManager:
    """Manages data storage and retrieval for EEG data"""
    
    def __init__(self, settings):
        self.settings = settings
        
        # Ensure data directory exists
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'recordings')
        os.makedirs(self.data_dir, exist_ok=True)
    
    def generate_filename(self, prefix="EEG", extension=".dat"):
        """Generate a timestamped filename
        
        Args:
            prefix: A string to prepend to the filename
            extension: File extension
            
        Returns:
            A string containing the generated filename with path
        """
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        filename = f"{prefix}_{timestamp}{extension}"
        return os.path.join(self.data_dir, filename)
    
    def prepare_recording_file(self):
        """Prepare a file for recording EEG data
        
        Returns:
            tuple of (file_object, filename)
        """
        filename = self.generate_filename("EEG_RECORDING", ".dat")
        file_obj = open(filename, 'wb')
        return file_obj, filename
    
    def save_metadata(self, recording_file, metadata):
        """Save metadata for a recording
        
        Args:
            recording_file: Filename of the recording
            metadata: Dictionary of metadata to save
            
        Returns:
            Path to metadata file
        """
        base_name = os.path.splitext(recording_file)[0]
        metadata_file = f"{base_name}_meta.txt"
        
        with open(metadata_file, 'w') as f:
            for key, value in metadata.items():
                f.write(f"{key}: {value}\n")
        
        return metadata_file
    
    def load_recording(self, filename):
        """Load a recorded EEG session
        
        Args:
            filename: Path to the recording file
            
        Returns:
            tuple of (eeg_data, sample_rate, metadata) where eeg_data is a numpy array,
            sample_rate is an integer, and metadata is a dictionary
        """
        # Load the raw data
        with open(filename, 'rb') as f:
            raw_data = f.read()
        
        # Convert bytes to 16-bit integers
        eeg_data = np.frombuffer(raw_data, dtype=np.int16)
        
        # Try to load metadata
        metadata = {}
        metadata_file = os.path.splitext(filename)[0] + "_meta.txt"
        if os.path.exists(metadata_file):
            with open(metadata_file, 'r') as f:
                for line in f:
                    if ':' in line:
                        key, value = line.strip().split(':', 1)
                        metadata[key.strip()] = value.strip()
        
        # Get sample rate from metadata or default
        sample_rate = int(metadata.get('sample_rate', self.settings.sampling_rate))
        
        return eeg_data, sample_rate, metadata
    
    def export_csv(self, eeg_data, time_data, filename=None):
        """Export EEG data to CSV format
        
        Args:
            eeg_data: List or array of EEG values
            time_data: List or array of time values
            filename: Output filename or None to generate automatically
            
        Returns:
            tuple of (success, message) where success is a boolean and
            message is a string describing the result
        """
        if filename is None:
            filename = self.generate_filename("EEG_EXPORT", ".csv")
            
        try:
            with open(filename, 'w') as f:
                f.write("Time,EEG\n")
                for t, eeg in zip(time_data, eeg_data):
                    f.write(f"{t:.6f},{eeg}\n")
            return True, f"Exported data to {filename}"
        except Exception as e:
            return False, f"Error exporting data: {e}"