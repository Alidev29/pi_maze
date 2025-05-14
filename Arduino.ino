
#include <NewPing.h>

// Motor control pins
#define RIGHT_MOTOR_PIN1 9
#define RIGHT_MOTOR_PIN2 10
#define LEFT_MOTOR_PIN1 11
#define LEFT_MOTOR_PIN2 12
#define RIGHT_MOTOR_ENABLE 5  // PWM pin for right motor speed
#define LEFT_MOTOR_ENABLE 6  // PWM pin for left motor speed

// Ultrasonic sensor pins (Trigger, Echo)
#define FRONT_TRIG_PIN  14   // PC0
#define FRONT_ECHO_PIN  15   // PC1

#define RIGHT_TRIG_PIN  16   // PC2
#define RIGHT_ECHO_PIN  17   // PC3

#define LEFT_TRIG_PIN   18   // PC4
#define LEFT_ECHO_PIN   19   // PC5

#define BACK_TRIG_PIN   8
#define BACK_ECHO_PIN   7

// No IR sensors used in this implementation

// Constants
#define MAX_DISTANCE 200     // Maximum distance for ultrasonic sensors (cm)
#define BASE_SPEED 180       // Base motor speed (0-255)
#define TURN_SPEED 110       // Speed during turns
#define BLOCK_SIZE 25        // Size of maze blocks in cm
#define CAR_WIDTH 15         // Width of the car in cm
#define EXPECTED_SIDE_DISTANCE 5  // Expected side distance when centered ((25-15)/2 = 5cm)
#define SIDE_TOLERANCE 2     // Acceptable variation in side distance (cm)
#define FRONT_SAFETY_MARGIN 8     // Safety distance for front obstacle detection (cm)
#define COMMAND_BUFFER_SIZE 100  // Maximum number of movement commands

// Create ultrasonic sensor objects
NewPing frontSonar(FRONT_TRIG_PIN, FRONT_ECHO_PIN, MAX_DISTANCE);
NewPing rightSonar(RIGHT_TRIG_PIN, RIGHT_ECHO_PIN, MAX_DISTANCE);
NewPing leftSonar(LEFT_TRIG_PIN, LEFT_ECHO_PIN, MAX_DISTANCE);
NewPing backSonar(BACK_TRIG_PIN, BACK_ECHO_PIN, MAX_DISTANCE);

// Variables for path execution
char commandBuffer[COMMAND_BUFFER_SIZE];
int commandLength = 0;
int currentCommand = 0;
bool isExecuting = false;
bool isStopped = true;

// Car position in maze (row, column)
int currentRow = 0;
int currentCol = 0;

// Current orientation (0=North, 1=East, 2=South, 3=West)
int currentOrientation = 0;

// Timing variables
unsigned long lastSensorUpdate = 0;
unsigned long lastCommandTime = 0;
const int sensorUpdateInterval = 500;  // Update sensors every 500ms
const int commandTimeout = 5000;       // Max 5 seconds per command

// Function prototypes
void executeCommand(char cmd);
void moveForward();
void moveBackward();
void turnLeft();
void turnRight();
void stopMotors();
void updateSensors();
void sendPosition();
void adjustPosition();
bool isAligned();

void setup() {
  // Initialize serial communication
  Serial.begin(115200);
  Serial.println("Arduino Maze Solver Car initialized");
  
  // Set motor control pins as outputs
  pinMode(RIGHT_MOTOR_PIN1, OUTPUT);
  pinMode(RIGHT_MOTOR_PIN2, OUTPUT);
  pinMode(LEFT_MOTOR_PIN1, OUTPUT);
  pinMode(LEFT_MOTOR_PIN2, OUTPUT);
  pinMode(RIGHT_MOTOR_ENABLE, OUTPUT);
  pinMode(LEFT_MOTOR_ENABLE, OUTPUT);
  
  // No IR sensor initialization
  
  // Stop motors initially
  stopMotors();
  
  // Initial sensor reading
  updateSensors();
}

void loop() {
  // Check for serial commands
  if (Serial.available() > 0) {
    String input = Serial.readStringUntil('\n');
    
    // Process different command types
    if (input.startsWith("CMD:")) {
      // Single movement command
      char cmd = input.charAt(4);
      executeCommand(cmd);
      
    } else if (input.startsWith("PATH:")) {
      // Store path for execution
      commandLength = min(input.length() - 5, COMMAND_BUFFER_SIZE - 1);
      for (int i = 0; i < commandLength; i++) {
        commandBuffer[i] = input.charAt(i + 5);
      }
      commandBuffer[commandLength] = '\0';  // Null-terminate
      
      currentCommand = 0;
      isExecuting = false;
      
      Serial.print("STATUS:Path received (");
      Serial.print(commandLength);
      Serial.println(" commands)");
      
    } else if (input.startsWith("EXEC")) {
      // Start executing the stored path
      if (commandLength > 0) {
        isExecuting = true;
        isStopped = false;
        currentCommand = 0;
        Serial.println("STATUS:Executing path");
      } else {
        Serial.println("STATUS:No path to execute");
      }
      
    } else if (input.startsWith("STOP")) {
      // Stop execution
      isExecuting = false;
      isStopped = true;
      stopMotors();
      Serial.println("STATUS:Stopped");
    }
  }
  
  // Execute path if active
  if (isExecuting && !isStopped && commandLength > 0) {
    // Check if we need to start a new command
    if (currentCommand < commandLength) {
      char cmd = commandBuffer[currentCommand];
      
      // Send step information
      Serial.print("STEP:");
      Serial.println(currentCommand);
      
      // Execute the command
      executeCommand(cmd);
      
      // Move to next command
      currentCommand++;
      lastCommandTime = millis();
      
      // If done, send completion
      if (currentCommand >= commandLength) {
        isExecuting = false;
        Serial.println("STATUS:Completed");
        sendPosition();
      }
    }
  }
  
  // Update sensor readings periodically
  if (millis() - lastSensorUpdate > sensorUpdateInterval) {
    updateSensors();
    lastSensorUpdate = millis();
  }
}

void executeCommand(char cmd) {
  // Execute a single movement command
  switch (cmd) {
    case 'F':
      Serial.println("STATUS:Moving Forward");
      moveForward();
      break;
    case 'B':
      Serial.println("STATUS:Moving Backward");
      moveBackward();
      break;
    case 'L':
      Serial.println("STATUS:Turning Left");
      turnLeft();
      break;
    case 'R':
      Serial.println("STATUS:Turning Right");
      turnRight();
      break;
    case 'S':
      Serial.println("STATUS:Stopping");
      stopMotors();
      break;
    default:
      // Ignore unknown commands
      break;
  }
}

void moveForward() {
  // Move forward one block (25cm)
  // Start motors
  digitalWrite(RIGHT_MOTOR_PIN1, HIGH);
  digitalWrite(RIGHT_MOTOR_PIN2, LOW);
  digitalWrite(LEFT_MOTOR_PIN1, HIGH);
  digitalWrite(LEFT_MOTOR_PIN2, LOW);
  analogWrite(RIGHT_MOTOR_ENABLE, BASE_SPEED);
  analogWrite(LEFT_MOTOR_ENABLE, BASE_SPEED+20);
  
  // Wait for block completion with alignment adjustments
  unsigned long startTime = millis();
  int targetDistance = BLOCK_SIZE;
  
  // Use front sensor to measure distance moved
  int initialDistance = frontSonar.ping_cm();
  
  while (millis() - startTime < 3000) {  // Timeout after 3 seconds
    // Check if we've moved approximately one block
    int currentDist = frontSonar.ping_cm();
    
    // If we're approaching a wall, we've moved enough
    // Use a safety margin to prevent collisions
    if (currentDist > 0 && currentDist <= FRONT_SAFETY_MARGIN) {
      break;
    }
    
    // Adjust position if needed
    adjustPosition();
    
    delay(50);  // Small delay between readings
  }
  
  // Stop motors
  stopMotors();
  delay(500);  // Pause briefly
  
  // Update position based on orientation
  switch (currentOrientation) {
    case 0:  // North
      currentRow--;
      break;
    case 1:  // East
      currentCol++;
      break;
    case 2:  // South
      currentRow++;
      break;
    case 3:  // West
      currentCol--;
      break;
  }
  
  // Send updated position
  sendPosition();
}

void moveBackward() {
  // Move backward one block
  digitalWrite(RIGHT_MOTOR_PIN1, LOW);
  digitalWrite(RIGHT_MOTOR_PIN2, HIGH);
  digitalWrite(LEFT_MOTOR_PIN1, LOW);
  digitalWrite(LEFT_MOTOR_PIN2, HIGH);
  analogWrite(RIGHT_MOTOR_ENABLE, BASE_SPEED);
  analogWrite(LEFT_MOTOR_ENABLE, BASE_SPEED);
  
  // Similar to forward but using back sensor
  unsigned long startTime = millis();
  
  while (millis() - startTime < 3000) {  // Timeout after 3 seconds
    // Check if we've moved approximately one block
    int currentDist = backSonar.ping_cm();
    
    // If we're approaching a wall, we've moved enough
    if (currentDist > 0 && currentDist <= FRONT_SAFETY_MARGIN) {
      break;
    }
    
    // Adjust position if needed
    adjustPosition();
    
    delay(50);
  }
  
  // Stop motors
  stopMotors();
  delay(500);
  
  // Update position based on orientation
  switch (currentOrientation) {
    case 0:  // North
      currentRow++;
      break;
    case 1:  // East
      currentCol--;
      break;
    case 2:  // South
      currentRow--;
      break;
    case 3:  // West
      currentCol++;
      break;
  }
  
  sendPosition();
}

void turnLeft() {
  // Turn left 90 degrees
  digitalWrite(RIGHT_MOTOR_PIN1, LOW);
  digitalWrite(RIGHT_MOTOR_PIN2, HIGH);
  digitalWrite(LEFT_MOTOR_PIN1, HIGH);
  digitalWrite(LEFT_MOTOR_PIN2, LOW);
  analogWrite(RIGHT_MOTOR_ENABLE, TURN_SPEED);
  analogWrite(LEFT_MOTOR_ENABLE, TURN_SPEED);
  
  // Turn for approximately 90 degrees
  delay(680);  // Adjust this based on your car's turning speed
  
  stopMotors();
  delay(500);
  
  // Update orientation (counter-clockwise)
  currentOrientation = (currentOrientation + 3) % 4;
  
  sendPosition();
}

void turnRight() {
  // Turn right 90 degrees
  digitalWrite(RIGHT_MOTOR_PIN1, HIGH);
  digitalWrite(RIGHT_MOTOR_PIN2, LOW);
  digitalWrite(LEFT_MOTOR_PIN1, LOW);
  digitalWrite(LEFT_MOTOR_PIN2, HIGH);
  analogWrite(RIGHT_MOTOR_ENABLE, TURN_SPEED);
  analogWrite(LEFT_MOTOR_ENABLE, TURN_SPEED);
  
  // Turn for approximately 90 degrees
  delay(680);  // Adjust this based on your car's turning speed
  
  stopMotors();
  delay(500);
  
  // Update orientation (clockwise)
  currentOrientation = (currentOrientation + 1) % 4;
  
  sendPosition();
}

void stopMotors() {
  // Stop all motors
  digitalWrite(RIGHT_MOTOR_PIN1, LOW);
  digitalWrite(RIGHT_MOTOR_PIN2, LOW);
  digitalWrite(LEFT_MOTOR_PIN1, LOW);
  digitalWrite(LEFT_MOTOR_PIN2, LOW);
  analogWrite(RIGHT_MOTOR_ENABLE, 0);
  analogWrite(LEFT_MOTOR_ENABLE, 0);
}

void updateSensors() {
  // Read all sensors and send data
  
  // Ultrasonic sensors
  int frontDist = frontSonar.ping_cm();
  if (frontDist == 0) frontDist = MAX_DISTANCE;  // Convert 0 (no echo) to max distance
  
  int rightDist = rightSonar.ping_cm();
  if (rightDist == 0) rightDist = MAX_DISTANCE;
  
  int leftDist = leftSonar.ping_cm();
  if (leftDist == 0) leftDist = MAX_DISTANCE;
  
  int backDist = backSonar.ping_cm();
  if (backDist == 0) backDist = MAX_DISTANCE;
  
  // Send ultrasonic sensor data to GUI
  Serial.print("DATA:front:");
  Serial.println(frontDist);
  
  Serial.print("DATA:right:");
  Serial.println(rightDist);
  
  Serial.print("DATA:left:");
  Serial.println(leftDist);
  
  Serial.print("DATA:back:");
  Serial.println(backDist);
}

void sendPosition() {
  // Send current position in maze
  Serial.print("POS:");
  Serial.print(currentRow);
  Serial.print(":");
  Serial.println(currentCol);
}

void adjustPosition() {
  // Adjust car position to stay centered in the maze cell
  int leftDist = leftSonar.ping_cm();
  int rightDist = rightSonar.ping_cm();
  
  // Only adjust if both sensors have valid readings
  if (leftDist > 0 && rightDist > 0) {
    int diff = leftDist - rightDist;
    
    // Check if we're centered at ~5cm on each side (for 15cm car in 25cm corridor)
    if (diff > SIDE_TOLERANCE) {  // Too far to the right
      analogWrite(RIGHT_MOTOR_ENABLE, BASE_SPEED - 20);
      analogWrite(LEFT_MOTOR_ENABLE, BASE_SPEED + 20);
    } else if (diff < -SIDE_TOLERANCE) {  // Too far to the left
      analogWrite(RIGHT_MOTOR_ENABLE, BASE_SPEED + 20);
      analogWrite(LEFT_MOTOR_ENABLE, BASE_SPEED - 20);
    } else if (leftDist < (EXPECTED_SIDE_DISTANCE - SIDE_TOLERANCE) || 
               rightDist < (EXPECTED_SIDE_DISTANCE - SIDE_TOLERANCE)) {  // Too close to a wall
      // Adjust to move away from the closer wall
      if (leftDist < rightDist) {
        // Too close to left wall
        analogWrite(RIGHT_MOTOR_ENABLE, BASE_SPEED - 30);
        analogWrite(LEFT_MOTOR_ENABLE, BASE_SPEED + 30);
      } else {
        // Too close to right wall
        analogWrite(RIGHT_MOTOR_ENABLE, BASE_SPEED + 30);
        analogWrite(LEFT_MOTOR_ENABLE, BASE_SPEED - 30);
      }
    } else {  // Centered
      analogWrite(RIGHT_MOTOR_ENABLE, BASE_SPEED);
      analogWrite(LEFT_MOTOR_ENABLE, BASE_SPEED);
    }
  }
}

bool isAligned() {
  // Check if the car is aligned in the center of a cell
  int leftDist = leftSonar.ping_cm();
  int rightDist = rightSonar.ping_cm();
  
  // Car is 15cm wide, corridor is 25cm = ~5cm on each side when centered
  // Consider aligned if distance difference is small AND distances are around expected value
  return (abs(leftDist - rightDist) < SIDE_TOLERANCE) && 
         (leftDist >= (EXPECTED_SIDE_DISTANCE - SIDE_TOLERANCE)) && 
         (leftDist <= (EXPECTED_SIDE_DISTANCE + SIDE_TOLERANCE)) && 
         (rightDist >= (EXPECTED_SIDE_DISTANCE - SIDE_TOLERANCE)) && 
         (rightDist <= (EXPECTED_SIDE_DISTANCE + SIDE_TOLERANCE));
}
