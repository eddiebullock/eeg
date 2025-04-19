#!/usr/bin/env python3
"""
EEG Monitor - Main Entry Point
A real-time EEG visualization and analysis application.
"""

import sys
import os
from pathlib import Path

# Add the project directory to sys.path
sys.path.insert(0, str(Path(__file__).parent))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer

# Import the main application window
from ui.main_window import EEGMonitorWindow 
from config.settings import Settings

def main():
    """Main entry point for the EEG Monitor application"""
    print("Starting real-time EEG monitor...")
    print(f"Python path: {sys.path}")
    
    # Create QApplication instance
    app = QApplication(sys.argv)
    
    # Load settings
    settings = Settings()
    
    # Create main window
    main_window = EEGMonitorWindow(settings)
    
    # Show the main window
    main_window.show()
    
    # Attempt auto-connect to EEG device after startup
    # This gives the GUI time to fully initialize before connecting
    QTimer.singleShot(1000, lambda: auto_connect(main_window))
    
    # Start application event loop
    sys.exit(app.exec_())

def auto_connect(window):
    """Automatically attempt to connect to EEG device after startup"""
    # Get list of available ports
    ports = window.serial_reader.get_available_ports()
    
    # Look for the Bluetooth EEG device
    for port in ports:
        if window.settings.bluetooth_device_name in port["device"]:
            print(f"Found EEG device at {port['device']}. Attempting to connect...")
            success, message = window.serial_reader.connect(port["device"])
            if success:
                print(f"Successfully connected to EEG device: {message}")
            else:
                print(f"Failed to connect to EEG device: {message}")
            return
    
    print("No EEG device found. Please connect manually through the interface.")

if __name__ == "__main__":
    main()