#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <ArduinoJson.h>
#include "esp_camera.h"
#include "soc/soc.h"
#include "soc/rtc_cntl_reg.h"
#include <Arduino.h>
#include <HTTPClient.h>

// WiFi credentials
const char* ssid = "Treasure";
const char* password = "54697df560";

// Define camera model (adjust if using a different model)
#define CAMERA_MODEL_XIAO_ESP32S3 // Has PSRAM
#include "camera_pins.h"

// Server URL for uploading images and receiving text
// const char* serverUrl = "https://nathang2022--readbuddy-backend-endpoint.modal.run/uploadS3";
const char* serverUrl = "http://192.168.86.36:8000/process_image";

void setup() {
  Serial.begin(115200);
  Serial.setDebugOutput(true);
  Serial.println();

  // Camera configuration based on the successful example
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.frame_size = FRAMESIZE_UXGA;
  config.pixel_format = PIXFORMAT_JPEG;  // for streaming
  //config.pixel_format = PIXFORMAT_RGB565; // for face detection/recognition
  config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
  config.fb_location = CAMERA_FB_IN_PSRAM;
  config.jpeg_quality = 12;
  config.fb_count = 1;

  // if PSRAM IC present, init with UXGA resolution and higher JPEG quality
  //                      for larger pre-allocated frame buffer.
  if (config.pixel_format == PIXFORMAT_JPEG) {
    if (psramFound()) {
      config.jpeg_quality = 10;
      config.fb_count = 2;
      config.grab_mode = CAMERA_GRAB_LATEST;
    } else {
      // Limit the frame size when PSRAM is not available
      config.frame_size = FRAMESIZE_SVGA;
      config.fb_location = CAMERA_FB_IN_DRAM;
    }
  } else {
    // Best option for face detection/recognition
    config.frame_size = FRAMESIZE_240X240;
#if CONFIG_IDF_TARGET_ESP32S3
    config.fb_count = 2;
#endif
  }

#if defined(CAMERA_MODEL_ESP_EYE)
  pinMode(13, INPUT_PULLUP);
  pinMode(14, INPUT_PULLUP);
#endif

  // camera init
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x", err);
    return;
  }

  sensor_t *s = esp_camera_sensor_get();
  // initial sensors are flipped vertically and colors are a bit saturated
  if (s->id.PID == OV3660_PID) {
    s->set_vflip(s, 1);        // flip it back
    s->set_brightness(s, 1);   // up the brightness just a bit
    s->set_saturation(s, -2);  // lower the saturation
  }
  // drop down frame size for higher initial frame rate
  if (config.pixel_format == PIXFORMAT_JPEG) {
    s->set_framesize(s, FRAMESIZE_QVGA);
  }

#if defined(CAMERA_MODEL_M5STACK_WIDE) || defined(CAMERA_MODEL_M5STACK_ESP32CAM)
  s->set_vflip(s, 1);
  s->set_hmirror(s, 1);
#endif

#if defined(CAMERA_MODEL_ESP32S3_EYE)
  s->set_vflip(s, 1);
#endif

  // Connect to WiFi
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  Serial.println("Connecting to WiFi...");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nConnected to WiFi");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());
}

String generateFileName() {
  unsigned long timestamp = millis();  // Use millis() for a simple timestamp
  return "image_" + String(timestamp) + ".jpg";  // Generate the filename dynamically
}

void loop() {
  String detectedText = captureAndUploadImage();
  if (detectedText.length() > 0) {
    Serial.println("Detected text: " + detectedText);
  } else {
    Serial.println("Please keep the device at least 15 cm above the text.");
  }
  delay(30000); // Wait 30 seconds before capturing again
}

String captureAndUploadImage() {
  camera_fb_t *fb = esp_camera_fb_get();  // Capture the image
  if (!fb) {
    Serial.println("Failed to capture image");
    return "";
  }

  String fileName = generateFileName();

  Serial.printf("Captured image of size: %u bytes\n", fb->len);

  HTTPClient http;
  http.begin(serverUrl);  // Initialize the HTTP request
  http.setTimeout(15000);  // Set timeout for the request

  String boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW";
  String contentType = "multipart/form-data; boundary=" + boundary;
  http.addHeader("Content-Type", contentType);

  String bodyStart = "--" + boundary + "\r\n";
  bodyStart += "Content-Disposition: form-data; name=\"file\"; filename=\"" + fileName + "\"\r\n";
  bodyStart += "Content-Type: image/jpeg\r\n\r\n";

  String bodyEnd = "\r\n--" + boundary + "--\r\n";

  size_t bodySize = bodyStart.length();
  size_t bodyEndSize = bodyEnd.length();
  size_t totalSize = bodySize + fb->len + bodyEndSize;

  uint8_t* bodyBuffer = (uint8_t*)malloc(totalSize);
  if (bodyBuffer == NULL) {
    Serial.println("Failed to allocate memory for body buffer");
    esp_camera_fb_return(fb);
    return "";
  }

  // Copy data into the buffer
  memcpy(bodyBuffer, bodyStart.c_str(), bodySize);
  memcpy(bodyBuffer + bodySize, fb->buf, fb->len);  // Add the image data
  memcpy(bodyBuffer + bodySize + fb->len, bodyEnd.c_str(), bodyEndSize);

  int httpResponseCode = http.sendRequest("POST", bodyBuffer, totalSize);  // Send the POST request
  String response = "";
  if (httpResponseCode > 0) {
    response = http.getString();  // Get the server response
    Serial.println("Image uploaded successfully");
  } else {
    Serial.printf("Error on HTTP request: %s\n", http.errorToString(httpResponseCode).c_str());
  }

  free(bodyBuffer);  // Free allocated memory
  http.end();  // Close the connection
  esp_camera_fb_return(fb);  // Release the frame buffer

  return response;  // Return the response from the server
}