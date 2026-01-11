# RS485 Desktop Application

![Python App Screenshot](/assets/pythonAPP.png)

## Overview
This is a custom Python desktop application for the [Lamp Controller Testing Project](https://github.com/amblackpearl/lamp-controller-testing). The application receives serial data via RS485 USB to TTL from an ESP32 microcontroller. Data fetching begins when the "Send 'rs'" button is pressed, retrieving the following measurements from the ESP32:

- Voltage
- Current
- Power
- Classification Result

## Technology Stack
- **Language**: Python 3.x
- **GUI Framework**: [PySide6](https://pypi.org/project/PySide6/) (Qt for Python)
- **Serial Communication**: Python `serial` library
- **Protocol**: RS485 Serial Communication
- **Hardware Interface**: USB to TTL Converter

## Features
- Real-time serial data reception from ESP32 via RS485
- Graphical user interface for monitoring electrical parameters
- Interactive controls to initiate data fetching
- Display of voltage, current, power, and classification results

## Dependencies
- PySide6
- pyserial
- Python 3.x

## Hardware Requirements
- ESP32 microcontroller programmed to send sensor data
- RS485 to USB TTL converter module
- Appropriate power supply connections for measurement

## Usage
1. Connect the ESP32 to your computer via the RS485 USB to TTL converter
2. Launch the application
3. Press the "Send 'rs'" button to begin receiving data
4. Monitor the real-time values displayed in the application