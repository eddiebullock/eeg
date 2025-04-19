# EEG Monitor

A real-time EEG visualization and analysis application for displaying, processing, and recording EEG data from USB serial devices.

## Features

- Real-time waveform display with adjustable speed and sensitivity
- Frequency analysis with real-time spectrogram
- Adjustable filters (highpass, lowpass, notch)
- Data recording capabilities
- Save spectrograms as images

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/eeg-monitor.git
   cd eeg-monitor
   ```

2. Create a virtual environment (optional but recommended):
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

Run the application with:
```
python main.py
```

### Hardware Setup

This application expects to receive EEG data from a USB serial device with the following specifications:

- Data format: 16-bit signed integers
- Sampling rate: 500 Hz
- Baud rate: 115200
- Data is sent continuously as a stream of bytes

### Application Controls

- **Port Selection**: Choose the serial port your EEG device is connected to
- **Connect/Disconnect**: Establish or close the serial connection
- **Recording**: Save raw data to a file for later analysis
- **Filters**: Adjust highpass, lowpass, and notch filters
- **Sensitivity**: Change display amplitude scaling
- **Speed**: Adjust display speed (mm/s)

## Project Structure

- `main.py` - Main entry point
- `config/` - Configuration settings
- `acquisition/` - Serial data acquisition
- `signal_processing/` - Signal processing and filtering
- `data/` - Data storage and management
- `ui/` - User interface components

## Dependencies

- PyQt5 - GUI framework
- pyqtgraph - Fast data visualization
- NumPy - Numerical processing
- SciPy - Signal processing
- pyserial - Serial communication
- matplotlib - For saving spectrograms as images

## License

[MIT License](LICENSE)