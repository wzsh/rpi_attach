# L6570 Stepper Motor Library

## 1. L6470Driver.py
This library is port from SparkFun L6470 Stepper AutoDriver, sharing the same APIs.

### Usage:
  1. from WZS.L6470Driver import L6470
  2. init:   
    board = L6470(spi, RESET_PIN, BUSY_PIN)

## 2. Demo

This demo works on Raspberry Pi, and it provides users a web-based UI to control the motor which wired on board.

<img src=".\demo\arch.png" alt="System Architecture" width="90%">

<img src=".\demo\wiring.png" alt="Wiring" width="48%">
<img src=".\demo\webui.png" alt="WebUI" width="45%">

