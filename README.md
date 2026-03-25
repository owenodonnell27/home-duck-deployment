# Home Duck Deployment

Sends a packet every 5 minutes that contains: counter, free memory, temperature (°F), and barometric pressure (Pa).

## Requirements List

- LilyGo T-Beam v1.2 SX1262
- Adafruit BMP180

## Wire Up

| T-Beam | BMP180 |
|---|---|
| 3V3 | VIN | 
| GND | GND | 
| GPIO 22 | SDA | 
| GPIO 21 | SCL | 

## Flashing

1. Clone this repository onto your local machine and open the root folder in VSCode.
2. Replace `MAMADUCK` with your Mama Duck's unique ID in `src/main.cpp`. 
3. Use the PlatformIO VSCode extension to flash to your Mama Duck.
