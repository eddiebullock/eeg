"""
Serial data acquisition for EEG Monitor.
Handles reading and parsing data from the EEG device.
"""

import time
import serial
import serial.tools.list_ports
from collections import deque
from PyQt5.QtCore import QObject, QTimer, pyqtSignal

class SerialReader(QObject):
    """Handles serial communication with the EEG device"""
    
    # Signals
    data_updated = pyqtSignal()  # Emitted when new data is available
    connection_changed = pyqtSignal(bool, str)  # Connected status, message
    
    def __init__(self, settings):
        super().__init__()
        
        # Store settings
        self.settings = settings
        
        # Data buffers - one for EEG, one for timestamps
        self.eeg_buffer = deque(maxlen=settings.spectrogram_buffer_size)
        self.time_buffer = deque(maxlen=settings.spectrogram_buffer_size)
        
        # Serial connection
        self.ser = None
        self.connected = False
        
        # Recording state
        self.recording = False
        self.output_file = None
        self.start_time = None
        self.output_filename = None
        
        # Initialize timestamp tracking
        self.last_timestamp = time.time()
        
        # Setup data reading timer
        self.data_timer = QTimer()
        self.data_timer.timeout.connect(self.read_serial_data)
        # Run at 4x the update rate to ensure smooth display
        self.data_timer.start(int(settings.update_interval / 4))
    
    def get_available_ports(self):
        """Get a list of available serial ports"""
        ports = serial.tools.list_ports.comports()
        port_list = []
        
        # Create a list of port info dictionaries
        for port in ports:
            port_info = {
                "device": port.device, 
                "description": port.description,
                "is_bluetooth": "Bluetooth" in port.description or self.settings.bluetooth_device_name in port.device
            }
            
            # Put Bluetooth EEG device at the top if it's available
            if self.settings.bluetooth_device_name in port.device:
                port_list.insert(0, port_info)
            else:
                port_list.append(port_info)
                
        return port_list
    
    def find_brain_device(self):
        """Attempt to find the EEG device"""
        ports = serial.tools.list_ports.comports()
        
        # First, try to find the Bluetooth device by name
        if self.settings.use_bluetooth:
            for port in ports:
                if self.settings.bluetooth_device_name in port.device:
                    return port.device
        
        # Otherwise use the default serial port from settings
        return self.settings.serial_port
    
    def connect(self, port=None):
        """Connect to the serial port"""
        # Auto-detect if no port specified
        if port is None or port == "auto":
            port = self.find_brain_device()
        
        # Close existing connection if open
        if self.ser and self.ser.is_open:
            self.ser.close()
            self.connected = False
        
        try:
            # Open new connection
            self.ser = serial.Serial(port, self.settings.baud_rate)
            self.settings.serial_port = port  # Save the current port
            self.connected = True
            
            # Clear buffers for fresh start
            self.eeg_buffer.clear()
            self.time_buffer.clear()
            self.last_timestamp = time.time()
            
            self.connection_changed.emit(True, f"Connected to {port}")
            return True, f"Connected to {port}"
            
        except Exception as e:
            self.connected = False
            self.connection_changed.emit(False, f"Error connecting: {str(e)}")
            return False, f"Error connecting: {str(e)}"
    
    def disconnect(self):
        """Disconnect from the serial port"""
        if self.ser and self.ser.is_open:
            # Stop recording if active
            if self.recording:
                self.stop_recording()
                
            # Close the serial port
            self.ser.close()
            self.connected = False
            self.connection_changed.emit(False, f"Disconnected from {self.settings.serial_port}")
            return True
        return False
    
    def start_recording(self):
        """Start recording data to a file"""
        if not self.connected:
            return False, "Not connected to any port. Cannot record."
            
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        self.output_filename = f"EEG_RECORDING_{timestamp}.dat"
        
        try:
            self.output_file = open(self.output_filename, 'wb')
            self.recording = True
            self.start_time = time.time()
            return True, f"Recording to {self.output_filename}"
        except Exception as e:
            return False, f"Error starting recording: {e}"
    
    def stop_recording(self):
        """Stop recording data"""
        if not self.recording:
            return False, "Not recording"
            
        if self.output_file:
            self.output_file.close()
            duration = time.time() - self.start_time
            self.output_file = None
            self.recording = False
            return True, f"Saved {self.output_filename} ({duration:.1f} sec)"
        
        self.recording = False
        return False, "Recording stopped but no file was open"
    
    def toggle_recording(self):
        """Toggle recording state"""
        if not self.recording:
            return self.start_recording()
        else:
            return self.stop_recording()
    
    def test_connection(self):
        """Test the serial connection by reading a few bytes"""
        if not self.ser or not self.ser.is_open:
            return False, "Not connected to any port."
            
        try:
            bytes_waiting = self.ser.in_waiting
            if bytes_waiting > 0:
                # Read a sample to verify data format
                sample_data = self.ser.read(min(bytes_waiting, 20))
                hex_data = ' '.join(f'{b:02x}' for b in sample_data)
                return True, f"Data received ({len(sample_data)} bytes): {hex_data}"
            else:
                return True, "No data in buffer. Verify device is sending data."
        except Exception as e:
            return False, f"Connection test error: {str(e)}"
    
    def read_serial_data(self):
        """Read data from the serial port and update the buffer"""
        # Read all available data from serial port
        if not self.ser or not self.ser.is_open:
            return
            
        try:
            # Calculate time elapsed since last read for accurate timestamps
            current_time = time.time()
            time_elapsed = current_time - self.last_timestamp
            self.last_timestamp = current_time
            
            bytes_to_read = self.ser.in_waiting
            if bytes_to_read >= 2:  # Each sample is 2 bytes
                # Read data in chunks of 2 bytes
                num_samples = bytes_to_read // 2
                
                # Create a time vector for these samples
                # (distribute samples evenly over the elapsed time)
                if len(self.time_buffer) > 0:
                    last_time = self.time_buffer[-1]
                else:
                    last_time = 0
                    
                sample_times = [
                    last_time + (time_elapsed * (i + 1) / num_samples)
                    for i in range(num_samples)
                ]
                
                data_received = False
                for i in range(num_samples):
                    data = self.ser.read(2)
                    if len(data) == 2:
                        # Convert to integer (16-bit signed)
                        try:
                            value = int.from_bytes(data, byteorder='little', signed=True)
                            
                            # Add to buffers
                            self.eeg_buffer.append(value)
                            self.time_buffer.append(sample_times[i])
                            data_received = True
                            
                            # Save to file if recording
                            if self.recording and self.output_file:
                                self.output_file.write(data)
                        except Exception as e:
                            print(f"Error processing data byte: {e}")
                
                if data_received:
                    self.data_updated.emit()
                    
        except Exception as e:
            print(f"Error reading serial data: {e}")
            self.connection_changed.emit(False, f"Error reading data: {e}")
    
    def get_data(self):
        """Return the current data buffers"""
        return list(self.eeg_buffer), list(self.time_buffer)
    
    def get_connection_status(self):
        """Get the current connection status and information"""
        if not self.ser:
            return False, "Not connected"
            
        try:
            if not self.ser.is_open:
                return False, "Port closed"
            
            bytes_waiting = self.ser.in_waiting
            return True, f"Active ({bytes_waiting} bytes waiting)"
        except:
            return False, "Connection error"
    
    def cleanup(self):
        """Clean up resources"""
        if self.ser and self.ser.is_open:
            self.ser.close()
        if self.recording and self.output_file:
            self.output_file.close()