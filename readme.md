#  RS485 Desktop App

![python](/assets/pythonAPP.png)

It's a custom python app for the [Lamp Controller Testing Project](https://github.com/amblackpearl/lamp-controller-testing) that will recieve serial data via RS485 USB to TTL from ESP32, so it will start fetch data when the "Send 'rs'" button is pressed. This is the several data that ESP32 sent when the button pressed :

- Voltage
- Current
- Power
- Classification Result

This custom python app is build using [PySide6](https://pypi.org/project/PySide6) for the GUI.