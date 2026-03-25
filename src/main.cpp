/**
 * @file MamaDuck.ino
 * @brief Implements a MamaDuck using the ClusterDuck Protocol (CDP).
 * 
 * This firmware periodically sends sensor data (BMP180 temperature
 * and pressure, plus counter and free memory) through a CDP mesh network.
 * It also relays messages that it receives from other ducks that it has not
 * seen yet.
 * 
 * @date 03-25-2026
 */

#include <string>
#include <arduino-timer.h>
#include <CDP.h>
#include <Wire.h>
#include <Adafruit_BMP085.h>

#ifdef SERIAL_PORT_USBVIRTUAL
#define Serial SERIAL_PORT_USBVIRTUAL
#endif

// Function Declarations
bool runSensor(void *);

// Global Variables
MamaDuck duck("TONEDTG5");
auto timer = timer_create_default();
int counter = 1;
bool setupOK = false;
bool bmpOK = false;

// Interval in milliseconds between runSensor calls
const int INTERVAL_MS = 300000;

// I2C pins for T-Beam
const int I2C_SDA = 21;
const int I2C_SCL = 22;

// BMP180 sensor (Adafruit_BMP085 supports both BMP085 and BMP180)
Adafruit_BMP085 bmp;

/**
 * Initializes the MamaDuck and BMP180 sensor.
 *
 * - Initializes MamaDuck using default configuration.
 * - Configures I2C and attempts to initialize the BMP180 sensor.
 * - Sets up periodic execution of sensor data transmissions.
 */
void setup() {

  if (duck.setupWithDefaults() != DUCK_ERR_NONE) {
    Serial.println("[MAMA] Failed to setup MamaDuck");
    return;
  }

  Serial2.begin(9600, SERIAL_8N1, 35, -1);

  Wire.begin(I2C_SDA, I2C_SCL);
  if (bmp.begin()) {
    bmpOK = true;
    Serial.println("[MAMA] BMP180 initialized OK");
  } else {
    Serial.println("[MAMA] BMP180 not found! Check wiring.");
  }

  timer.every(INTERVAL_MS, runSensor);

  setupOK = true;
  Serial.println("[MAMA] Setup OK!");
}

/**
 * Main loop that runs continuously.
 *
 * Executes scheduled timer tasks and maintains Duck operation.
 */
void loop() {
  if (!setupOK) {
    return;
  }

  timer.tick();
  duck.run();
}

/**
 * Gathers and sends sensor data periodically.
 *
 * Reads temperature (°F) and pressure (Pa) from the BMP180, along with
 * the counter and free memory. Formats them into a delimited string and
 * transmits via CDP.
 *
 * Message format: {"C":1,"FM":45000,"T":75.7,"P":101325}
 *
 * @param unused Unused parameter required by the timer callback signature.
 * @return true Always returns true to keep the timer running.
 */
bool runSensor(void *) {
  bool failure;

  char payload[128];

  if (bmpOK) {
    float tempF = bmp.readTemperature() * 9.0 / 5.0 + 32.0;
    int32_t pressurePa = bmp.readPressure();

    snprintf(payload, sizeof(payload),
      "{\"C\":%d,\"FM\":%d,\"T\":%.1f,\"P\":%ld}",
      counter, freeMemory(), tempF, (long)pressurePa);
  } else {
    snprintf(payload, sizeof(payload),
      "{\"C\":%d,\"FM\":%d,\"T\":null,\"P\":null}",
      counter, freeMemory());
  }

  std::string message(payload);

  Serial.print("[MAMA] sensor data: ");
  Serial.println(message.c_str());

  failure = duck.sendData(topics::health, message);
  if (!failure) {
    counter++;
    Serial.println("[MAMA] runSensor ok.");
  } else {
    Serial.println("[MAMA] runSensor failed.");
  }
  return true;
}