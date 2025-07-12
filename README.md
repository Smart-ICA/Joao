# Arduino Power Monitoring System

A comprehensive IoT solution for real-time power monitoring using Arduino and DFRobot current sensors, with multiple visualization options through the MADS (Multi-Agent Data System) framework.

## 🔧 Hardware Requirements

- **Arduino board** (Uno, Nano, or compatible)
- **DFRobot Gravity Analog AC Current Sensors** (SKU: SEN0211) - 3 units
- **Serial connection** (USB cable)
- **Power supply** for Arduino

## 📋 Features

- **Real-time current monitoring** on 3 channels (I1, I2, I3)
- **JSON data transmission** over serial communication
- **Multiple visualization options**:
  - Terminal GUI with ASCII art display
  - Real-time plotting with Matplotlib
  - Web-based dashboard with Flask
  - Multi-sensor support (including NodeMCU sensors)
- **MADS framework integration** for distributed data processing
- **Cross-platform compatibility** (Windows, Linux, Raspberry Pi)

## 🚀 Quick Start

### 1. Arduino Setup

1. Connect the DFRobot current sensors to analog pins A0, A1, and A2
2. Upload the `Arduino/iSensor.ino` sketch to your Arduino board
3. Ensure the serial connection is established at 115200 baud rate

### 2. Python Environment Setup

```bash
# Install required dependencies
pip install pyserial matplotlib flask pyfiglet

# For MADS framework integration
# Follow MADS installation instructions from your framework documentation
```

### 3. Running the System

#### Option A: Terminal GUI Display
```bash
mads python -s tcp://mads-broker.local:9092 -n python_sink -m sink_arduino_gui
```

#### Option B: Real-time Plotting
```bash
mads python -s tcp://mads-broker.local:9092 -n python_sink -m sink_arduino_plot
```

#### Option C: Web Dashboard
```bash
mads python -s tcp://mads-broker.local:9092 -n python_sink -m sink_arduino_web
```

#### Data Source Agent
```bash
mads python -s tcp://mads-broker.local:9092 -n python_source -m source_arduino
```

## 📁 Project Structure

```
├── Arduino/
│   └── iSensor.ino              # Arduino firmware for current sensing
├── Python/
│   ├── source_arduino.py        # MADS source agent for Arduino data
│   ├── sink_arduino_gui.py      # Terminal-based GUI visualization
│   ├── sink_arduino_plot.py     # Matplotlib real-time plotting
│   ├── sink_arduino_web.py      # Flask web dashboard
│   └── sink_NodeMCU_Plot.py     # Multi-sensor visualization (NodeMCU)
└── README.md
```

## 🔌 Hardware Configuration

### Current Sensor Specifications
- **Model**: DFRobot Gravity Analog AC Current Sensor (SEN0211)
- **Range**: 5A, 10A, 20A, or 30A (configurable in code)
- **Output**: Analog voltage proportional to AC current
- **Documentation**: [DFRobot Wiki](https://wiki.dfrobot.com/Gravity_Analog_AC_Current_Sensor__SKU_SEN0211_)

### Wiring Diagram
- **Pin A0** → Current Sensor 1 (I1)
- **Pin A1** → Current Sensor 2 (I2)
- **Pin A2** → Current Sensor 3 (I3)
- **VCC** → 5V
- **GND** → Ground

## 📊 Data Format

The system transmits data in JSON format:

```json
{
  "millis": 12345,
  "data": {
    "I1": 2.45,
    "I2": 1.87,
    "I3": 3.12
  }
}
```

- `millis`: Arduino timestamp in milliseconds
- `I1`, `I2`, `I3`: Current readings in amperes

## 🖥️ Visualization Options

### 1. Terminal GUI (`sink_arduino_gui.py`)
- Large ASCII art display using PyFiglet
- Real-time current values with 2 decimal precision
- Timestamp information
- Terminal-based interface

### 2. Real-time Plotting (`sink_arduino_plot.py`)
- Matplotlib-based live plotting
- Configurable time window
- Interactive legends
- Values table display

### 3. Web Dashboard (`sink_arduino_web.py`)
- Flask-based web interface
- Auto-refreshing display (250ms intervals)
- Modern responsive UI
- Real-time data updates

### 4. Multi-sensor Support (`sink_NodeMCU_Plot.py`)
- Extended sensor support
- Temperature, humidity, sound level monitoring
- Accelerometer data (X, Y, Z axes)
- Vibration analysis

## 🔧 Troubleshooting

### Serial Connection Issues
- Verify Arduino is connected and recognized by the system
- Check serial port permissions (Linux/macOS)
- Ensure correct baud rate (115200)

### Data Reception Problems
- Verify JSON format from Arduino
- Check sensor connections and power supply
- Monitor serial output for debugging information

### Visualization Issues
- Install required Python packages
- Check display backend for Matplotlib (especially on headless systems)
- Verify Flask port availability for web dashboard

## 🤝 Contributing

This project is part of an internship at INSA Toulouse. For contributions or questions, please contact the project maintainer.

## 📝 License

This project is developed for educational and research purposes at INSA Toulouse.

## 🏫 Institution

**INSA Toulouse** - Institut National des Sciences Appliquées de Toulouse
Internship Project - Smart-ICA Laboratory

---

*For more information about the MADS framework and advanced configuration options, please refer to the MADS documentation.*