#!/usr/bin/env python3
"""
Improved Maze Solver GUI Application for Raspberry Pi
- Design 6x4 maze with walls between cells
- Set start and end points
- Solve maze and display path
- Generate instructions for Arduino
"""

import tkinter as tk
from tkinter import messagebox, StringVar
import numpy as np

class MazeSolverGUI:
    def __init__(self, master):
        self.master = master
        self.master.title("Maze Solver")
        self.master.geometry("900x650")
        
        # Maze dimensions
        self.rows = 6
        self.cols = 4
        
        # Maze data - Matrix to store wall information
        # horizontal_walls[r][c] represents a wall between (r,c) and (r+1,c)
        # vertical_walls[r][c] represents a wall between (r,c) and (r,c+1)
        self.horizontal_walls = np.zeros((self.rows+1, self.cols), dtype=int)
        self.vertical_walls = np.zeros((self.rows, self.cols+1), dtype=int)
        
        # Set outer boundary walls
        for c in range(self.cols):
            self.horizontal_walls[0][c] = 1  # Top boundary
            self.horizontal_walls[self.rows][c] = 1  # Bottom boundary
        for r in range(self.rows):
            self.vertical_walls[r][0] = 1  # Left boundary
            self.vertical_walls[r][self.cols] = 1  # Right boundary
        
        # Start and end coordinates
        self.start_pos = None
        self.end_pos = None
        
        # Maze solution
        self.solution_path = []
        
        # Wall drawing state
        self.drawing_wall = False
        self.wall_start = None
        
        # Create GUI elements
        self.create_widgets()
        
    def create_widgets(self):
        # Main frame
        main_frame = tk.Frame(self.master)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left frame for maze grid
        left_frame = tk.Frame(main_frame, bd=2, relief=tk.SUNKEN)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Right frame for controls
        right_frame = tk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=10)
        
        # Canvas for drawing the maze
        self.canvas_width = 500
        self.canvas_height = 400
        self.canvas = tk.Canvas(left_frame, width=self.canvas_width, height=self.canvas_height, bg="white")
        self.canvas.pack(padx=20, pady=20, fill=tk.BOTH, expand=True)
        
        # Set up canvas for wall drawing
        self.canvas.bind("<Button-1>", self.canvas_click)
        self.canvas.bind("<B1-Motion>", self.canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.canvas_release)
        
        # Calculate cell size
        self.cell_width = self.canvas_width / self.cols
        self.cell_height = self.canvas_height / self.rows
        
        # Draw initial grid
        self.draw_grid()
        
        # Status label
        status_frame = tk.Frame(left_frame)
        status_frame.pack(fill=tk.X, padx=5, pady=5)
        self.status_var = StringVar()
        self.status_var.set("Select start and end points, then create walls between cells")
        status_label = tk.Label(status_frame, textvariable=self.status_var, fg="blue")
        status_label.pack(fill=tk.X)
        
        # Control buttons
        control_label = tk.Label(right_frame, text="Controls", font=("Arial", 12, "bold"))
        control_label.pack(pady=(0, 10))
        
        # Mode selection
        self.mode_var = StringVar()
        self.mode_var.set("wall")
        
        mode_frame = tk.LabelFrame(right_frame, text="Edit Mode")
        mode_frame.pack(fill=tk.X, pady=5)
        
        wall_radio = tk.Radiobutton(mode_frame, text="Place Walls", variable=self.mode_var, value="wall")
        wall_radio.pack(anchor=tk.W)
        
        start_radio = tk.Radiobutton(mode_frame, text="Set Start", variable=self.mode_var, value="start")
        start_radio.pack(anchor=tk.W)
        
        end_radio = tk.Radiobutton(mode_frame, text="Set End", variable=self.mode_var, value="end")
        end_radio.pack(anchor=tk.W)
        
        # Action buttons
        actions_frame = tk.LabelFrame(right_frame, text="Actions")
        actions_frame.pack(fill=tk.X, pady=10)
        
        solve_button = tk.Button(actions_frame, text="Solve Maze", command=self.solve_maze)
        solve_button.pack(fill=tk.X, pady=5)
        
        clear_button = tk.Button(actions_frame, text="Clear Maze", command=self.clear_maze)
        clear_button.pack(fill=tk.X, pady=5)
        
        export_button = tk.Button(actions_frame, text="Export Solution", command=self.export_solution)
        export_button.pack(fill=tk.X, pady=5)
        
        # Solution display
        solution_frame = tk.LabelFrame(right_frame, text="Solution")
        solution_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.solution_text = tk.Text(solution_frame, height=10, width=25)
        self.solution_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Sensor info frame
        sensor_frame = tk.LabelFrame(right_frame, text="Sensor Info")
        sensor_frame.pack(fill=tk.X, pady=10)
        
        sensor_label = tk.Label(sensor_frame, text="IR Sensors: Front detection\nUltrasonic: Surrounding walls", justify=tk.LEFT)
        sensor_label.pack(anchor=tk.W, padx=5, pady=5)

    def draw_grid(self):
        self.canvas.delete("all")
        
        # Draw cells
        for row in range(self.rows):
            for col in range(self.cols):
                x1 = col * self.cell_width
                y1 = row * self.cell_height
                x2 = (col + 1) * self.cell_width
                y2 = (row + 1) * self.cell_height
                
                # Draw cell
                if (row, col) == self.start_pos:
                    self.canvas.create_rectangle(x1, y1, x2, y2, fill="green", outline="")
                elif (row, col) == self.end_pos:
                    self.canvas.create_rectangle(x1, y1, x2, y2, fill="red", outline="")
                elif self.solution_path and (row, col) in self.solution_path[0]:
                    self.canvas.create_rectangle(x1, y1, x2, y2, fill="light blue", outline="")
                else:
                    self.canvas.create_rectangle(x1, y1, x2, y2, fill="white", outline="")
        
        # Draw horizontal walls
        for row in range(self.rows + 1):
            for col in range(self.cols):
                if self.horizontal_walls[row][col] == 1:
                    x1 = col * self.cell_width
                    y1 = row * self.cell_height
                    x2 = (col + 1) * self.cell_width
                    y2 = row * self.cell_height
                    self.canvas.create_line(x1, y1, x2, y2, width=3, fill="black")
        
        # Draw vertical walls
        for row in range(self.rows):
            for col in range(self.cols + 1):
                if self.vertical_walls[row][col] == 1:
                    x1 = col * self.cell_width
                    y1 = row * self.cell_height
                    x2 = col * self.cell_width
                    y2 = (row + 1) * self.cell_height
                    self.canvas.create_line(x1, y1, x2, y2, width=3, fill="black")
    
    def canvas_click(self, event):
        mode = self.mode_var.get()
        
        # Get cell coordinates
        col = int(event.x / self.cell_width)
        row = int(event.y / self.cell_height)
        
        # Check if valid cell
        if not (0 <= row < self.rows and 0 <= col < self.cols):
            return
        
        if mode == "start":
            # Set start position
            self.start_pos = (row, col)
            self.status_var.set(f"Start position set at ({row}, {col})")
            self.draw_grid()
            
        elif mode == "end":
            # Set end position
            self.end_pos = (row, col)
            self.status_var.set(f"End position set at ({row}, {col})")
            self.draw_grid()
            
        elif mode == "wall":
            # Start wall drawing
            self.drawing_wall = True
            
            # Store click position for wall drawing
            self.wall_start = (event.x, event.y)
    
    def canvas_drag(self, event):
        if self.mode_var.get() != "wall" or not self.drawing_wall:
            return
        
        # For visual feedback during dragging
        self.canvas.delete("temp_line")
        self.canvas.create_line(self.wall_start[0], self.wall_start[1], 
                                event.x, event.y, 
                                width=3, fill="gray", tags="temp_line")
    
    def canvas_release(self, event):
        if self.mode_var.get() != "wall" or not self.drawing_wall:
            return
        
        self.drawing_wall = False
        self.canvas.delete("temp_line")
        
        # Calculate start and end cells
        start_col = int(self.wall_start[0] / self.cell_width)
        start_row = int(self.wall_start[1] / self.cell_height)
        end_col = int(event.x / self.cell_width)
        end_row = int(event.y / self.cell_height)
        
        # Check if valid cells
        if not (0 <= start_row <= self.rows and 0 <= start_col <= self.cols and
                0 <= end_row <= self.rows and 0 <= end_col <= self.cols):
            return
        
        # Only allow walls between adjacent cells (horizontal or vertical)
        if start_row == end_row and abs(start_col - end_col) == 1:
            # Vertical wall
            min_col = min(start_col, end_col)
            self.vertical_walls[start_row][min_col] = 1 - self.vertical_walls[start_row][min_col]  # Toggle wall
            self.status_var.set(f"Toggled vertical wall at row {start_row}, between columns {min_col} and {min_col+1}")
            
        elif start_col == end_col and abs(start_row - end_row) == 1:
            # Horizontal wall
            min_row = min(start_row, end_row)
            self.horizontal_walls[min_row][start_col] = 1 - self.horizontal_walls[min_row][start_col]  # Toggle wall
            self.status_var.set(f"Toggled horizontal wall at column {start_col}, between rows {min_row} and {min_row+1}")
            
        else:
            # Not a valid wall placement
            self.status_var.set("Invalid wall placement. Walls must be between adjacent cells.")
        
        # Redraw the grid
        self.draw_grid()
    
    def clear_maze(self):
        # Reset walls (keep outer boundary)
        self.horizontal_walls = np.zeros((self.rows+1, self.cols), dtype=int)
        self.vertical_walls = np.zeros((self.rows, self.cols+1), dtype=int)
        
        # Reset outer boundary walls
        for c in range(self.cols):
            self.horizontal_walls[0][c] = 1  # Top boundary
            self.horizontal_walls[self.rows][c] = 1  # Bottom boundary
        for r in range(self.rows):
            self.vertical_walls[r][0] = 1  # Left boundary
            self.vertical_walls[r][self.cols] = 1  # Right boundary
        
        # Reset start and end positions
        self.start_pos = None
        self.end_pos = None
        self.solution_path = []
        
        # Redraw grid
        self.draw_grid()
        self.solution_text.delete(1.0, tk.END)
        self.status_var.set("Maze cleared")
    
    def can_move(self, from_pos, to_pos):
        # Check if there's a wall between from_pos and to_pos
        r1, c1 = from_pos
        r2, c2 = to_pos
        
        if r1 == r2:  # Same row, horizontal movement
            if c1 < c2:  # Moving right
                return self.vertical_walls[r1][c1+1] == 0
            else:  # Moving left
                return self.vertical_walls[r1][c1] == 0
        elif c1 == c2:  # Same column, vertical movement
            if r1 < r2:  # Moving down
                return self.horizontal_walls[r1+1][c1] == 0
            else:  # Moving up
                return self.horizontal_walls[r1][c1] == 0
        
        return False  # Not adjacent
    
    def solve_maze(self):
        if not self.start_pos or not self.end_pos:
            messagebox.showwarning("Warning", "Please set start and end points first")
            return
        
        # Reset previous solution
        self.solution_path = []
        
        # Solve using BFS algorithm
        path_result = self.bfs_solve()
        
        if not path_result:
            messagebox.showinfo("No Solution", "No path exists between start and end points")
            return
        
        self.solution_path = path_result
        
        # Display solution path
        self.display_solution()
    
    def bfs_solve(self):
        # Breadth-First Search algorithm
        dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]  # Down, Up, Right, Left
        dir_names = ["DOWN", "UP", "RIGHT", "LEFT"]
        
        visited = np.zeros((self.rows, self.cols), dtype=bool)
        q = []  # Simple queue using list
        q.append(self.start_pos)
        visited[self.start_pos] = True
        
        # Keep track of previous cell for reconstructing the path
        prev = {}
        prev[self.start_pos] = None
        
        # Keep track of direction for movement instructions
        moves = {}
        
        while q:
            curr_pos = q.pop(0)  # Dequeue
            curr_row, curr_col = curr_pos
            
            # Check if we reached the end
            if curr_pos == self.end_pos:
                # Reconstruct the path
                path = []
                instructions = []
                pos = curr_pos
                
                while pos != self.start_pos:
                    path.append(pos)
                    prev_pos = prev[pos]
                    dir_idx = moves[pos]
                    instructions.append(dir_names[dir_idx])
                    pos = prev_pos
                
                path.append(self.start_pos)
                path.reverse()
                instructions.reverse()
                
                return path, instructions
            
            # Try each direction
            for i, (dr, dc) in enumerate(dirs):
                new_pos = (curr_row + dr, curr_col + dc)
                new_row, new_col = new_pos
                
                # Check if the new position is valid
                if (0 <= new_row < self.rows and 
                    0 <= new_col < self.cols and 
                    not visited[new_row, new_col] and 
                    self.can_move(curr_pos, new_pos)):
                    
                    q.append(new_pos)
                    visited[new_row, new_col] = True
                    prev[new_pos] = curr_pos
                    moves[new_pos] = i
        
        # No path found
        return None
    
    def display_solution(self):
        if not self.solution_path:
            return
        
        path, instructions = self.solution_path
        
        # Redraw the grid to show the solution
        self.draw_grid()
        
        # Display path instructions
        self.solution_text.delete(1.0, tk.END)
        self.solution_text.insert(tk.END, "Path Instructions:\n\n")
        
        for i, direction in enumerate(instructions):
            self.solution_text.insert(tk.END, f"{i+1}. {direction}\n")
        
        self.status_var.set(f"Maze solved! Path length: {len(path)}")
    
    def export_solution(self):
        if not self.solution_path:
            messagebox.showwarning("No Solution", "Please solve the maze first")
            return
            
        path, instructions = self.solution_path
        
        try:
            with open("maze_solution.txt", "w") as f:
                f.write("Maze Solution Path:\n")
                for i, (row, col) in enumerate(path):
                    f.write(f"Step {i+1}: ({row}, {col})\n")
                
                f.write("\nDirectional Instructions:\n")
                for i, direction in enumerate(instructions):
                    f.write(f"Step {i+1}: {direction}\n")
                
                # Convert to Arduino commands
                f.write("\nArduino Commands:\n")
                
                # Map direction to motor command
                dir_to_cmd = {
                    "UP": "f",     # Forward
                    "DOWN": "b",   # Backward
                    "LEFT": "l",   # Left turn
                    "RIGHT": "r"   # Right turn
                }
                
                # Build sequence of commands
                current_direction = "UP"  # Assume robot starts facing up
                f.write("Commands (f=forward, b=backward, l=left, r=right, s=stop):\n")
                
                cmd_sequence = []
                for direction in instructions:
                    # Calculate required turns based on current facing direction
                    if current_direction == "UP":
                        if direction == "UP":
                            cmd_sequence.append("f")  # No turn needed
                        elif direction == "DOWN":
                            cmd_sequence.extend(["r", "r", "f"])  # 180° turn
                        elif direction == "LEFT":
                            cmd_sequence.extend(["l", "f"])
                        elif direction == "RIGHT":
                            cmd_sequence.extend(["r", "f"])
                            
                    elif current_direction == "DOWN":
                        if direction == "UP":
                            cmd_sequence.extend(["r", "r", "f"])  # 180° turn
                        elif direction == "DOWN":
                            cmd_sequence.append("f")  # No turn needed
                        elif direction == "LEFT":
                            cmd_sequence.extend(["r", "f"])
                        elif direction == "RIGHT":
                            cmd_sequence.extend(["l", "f"])
                            
                    elif current_direction == "LEFT":
                        if direction == "UP":
                            cmd_sequence.extend(["r", "f"])
                        elif direction == "DOWN":
                            cmd_sequence.extend(["l", "f"])
                        elif direction == "LEFT":
                            cmd_sequence.append("f")  # No turn needed
                        elif direction == "RIGHT":
                            cmd_sequence.extend(["r", "r", "f"])  # 180° turn
                            
                    elif current_direction == "RIGHT":
                        if direction == "UP":
                            cmd_sequence.extend(["l", "f"])
                        elif direction == "DOWN":
                            cmd_sequence.extend(["r", "f"])
                        elif direction == "LEFT":
                            cmd_sequence.extend(["r", "r", "f"])  # 180° turn
                        elif direction == "RIGHT":
                            cmd_sequence.append("f")  # No turn needed
                    
                    # Update current direction
                    current_direction = direction
                
                # Add IR sensor and ultrasonic sensor logic for Arduino
                f.write("// Arduino commands with sensor integration\n")
                f.write("// Commands: " + " ".join(cmd_sequence) + " s\n\n")
                
                f.write("/* Arduino implementation:\n")
                f.write("For IR sensors: Follow line/path detection\n")
                f.write("For Ultrasonic sensors: Wall detection and avoidance\n")
                f.write("Use these commands as high-level navigation,\n")
                f.write("while sensors handle real-time adjustments */\n")
                
                # Write Arduino code outline
                f.write("\n// Arduino code outline:\n")
                f.write("/*\n")
                f.write("void executeCommands() {\n")
                f.write("  // Process command sequence\n")
                f.write("  for (int i = 0; i < commandLength; i++) {\n")
                f.write("    switch(commands[i]) {\n")
                f.write("      case 'f': moveForward(); break;\n")
                f.write("      case 'b': moveBackward(); break;\n")
                f.write("      case 'l': turnLeft(); break;\n")
                f.write("      case 'r': turnRight(); break;\n")
                f.write("      case 's': stopMotors(); break;\n")
                f.write("    }\n")
                f.write("    \n")
                f.write("    // Wait for movement completion\n")
                f.write("    while (isMoving()) {\n")
                f.write("      readSensors();\n")
                f.write("      adjustPathIfNeeded();\n")
                f.write("    }\n")
                f.write("  }\n")
                f.write("}\n")
                f.write("*/\n")
            
            messagebox.showinfo("Export Successful", 
                               "Solution exported to maze_solution.txt\n"
                               "File includes path coordinates, directions,\n"
                               "and Arduino command sequence.")
            self.status_var.set("Solution exported to file")
            
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export solution: {str(e)}")
        
    def get_arduino_code(self):
        """Generate Arduino code for the maze solving robot"""
        if not self.solution_path:
            return "// No solution available. Solve the maze first."
            
        path, instructions = self.solution_path
        
        # Create Arduino code
        code = """// Maze Solving Robot Code
#include <Servo.h>

// Motor pins
#define LEFT_MOTOR_PIN1 5
#define LEFT_MOTOR_PIN2 6
#define RIGHT_MOTOR_PIN1 9
#define RIGHT_MOTOR_PIN2 10

// IR Sensor pins (front sensors)
#define IR_LEFT_OUT 2
#define IR_LEFT_IN 3
#define IR_RIGHT_IN 4
#define IR_RIGHT_OUT 7

// Ultrasonic sensor pins
#define US_FRONT_TRIG 11
#define US_FRONT_ECHO 12
#define US_RIGHT_TRIG A0
#define US_RIGHT_ECHO A1
#define US_LEFT_TRIG A2
#define US_LEFT_ECHO A3
#define US_BACK_TRIG A4
#define US_BACK_ECHO A5

// Movement constants
#define FORWARD_SPEED 150
#define TURN_SPEED 120
#define TURN_TIME 650  // Time to turn 90 degrees (ms)

// Command sequence from maze solver
const char commands[] = "
"""
        
        # Add command sequence
        current_direction = "UP"  # Assume robot starts facing up
        cmd_sequence = []
        for direction in instructions:
            # Calculate required turns based on current facing direction
            if current_direction == "UP":
                if direction == "UP":
                    cmd_sequence.append("f")  # No turn needed
                elif direction == "DOWN":
                    cmd_sequence.extend(["r", "r", "f"])  # 180° turn
                elif direction == "LEFT":
                    cmd_sequence.extend(["l", "f"])
                elif direction == "RIGHT":
                    cmd_sequence.extend(["r", "f"])
                    
            elif current_direction == "DOWN":
                if direction == "UP":
                    cmd_sequence.extend(["r", "r", "f"])  # 180° turn
                elif direction == "DOWN":
                    cmd_sequence.append("f")  # No turn needed
                elif direction == "LEFT":
                    cmd_sequence.extend(["r", "f"])
                elif direction == "RIGHT":
                    cmd_sequence.extend(["l", "f"])
                    
            elif current_direction == "LEFT":
                if direction == "UP":
                    cmd_sequence.extend(["r", "f"])
                elif direction == "DOWN":
                    cmd_sequence.extend(["l", "f"])
                elif direction == "LEFT":
                    cmd_sequence.append("f")  # No turn needed
                elif direction == "RIGHT":
                    cmd_sequence.extend(["r", "r", "f"])  # 180° turn
                    
            elif current_direction == "RIGHT":
                if direction == "UP":
                    cmd_sequence.extend(["l", "f"])
                elif direction == "DOWN":
                    cmd_sequence.extend(["r", "f"])
                elif direction == "LEFT":
                    cmd_sequence.extend(["r", "r", "f"])  # 180° turn
                elif direction == "RIGHT":
                    cmd_sequence.append("f")  # No turn needed
            
            # Update current direction
            current_direction = direction
        
        cmd_sequence.append("s")  # Final stop
        code += "".join(cmd_sequence) + "\";\n\n"
        
        # Add the rest of the Arduino code
        code += """
const int commandLength = sizeof(commands) - 1;
int currentCommand = 0;
bool commandCompleted = true;

void setup() {
  // Initialize motor pins
  pinMode(LEFT_MOTOR_PIN1, OUTPUT);
  pinMode(LEFT_MOTOR_PIN2, OUTPUT);
  pinMode(RIGHT_MOTOR_PIN1, OUTPUT);
  pinMode(RIGHT_MOTOR_PIN2, OUTPUT);
  
  // Initialize IR sensor pins
  pinMode(IR_LEFT_OUT, INPUT);
  pinMode(IR_LEFT_IN, INPUT);
  pinMode(IR_RIGHT_IN, INPUT);
  pinMode(IR_RIGHT_OUT, INPUT);
  
  // Initialize ultrasonic sensor pins
  pinMode(US_FRONT_TRIG, OUTPUT);
  pinMode(US_FRONT_ECHO, INPUT);
  pinMode(US_RIGHT_TRIG, OUTPUT);
  pinMode(US_RIGHT_ECHO, INPUT);
  pinMode(US_LEFT_TRIG, OUTPUT);
  pinMode(US_LEFT_ECHO, INPUT);
  pinMode(US_BACK_TRIG, OUTPUT);
  pinMode(US_BACK_ECHO, INPUT);
  
  Serial.begin(9600);
  Serial.println("Maze Solving Robot Starting...");
  
  // Wait for initial command
  delay(2000);
}

void loop() {
  // Read sensors
  readIRSensors();
  readUltrasonicSensors();
  
  // Execute next command if previous is completed
  if (commandCompleted && currentCommand < commandLength) {
    executeCommand(commands[currentCommand]);
    currentCommand++;
    commandCompleted = false;
  }
  
  // Check if movement is complete
  if (!commandCompleted) {
    if (isMovementComplete()) {
      commandCompleted = true;
      delay(300);  // Small pause between commands
    } else {
      // Use sensors to adjust path during movement
      adjustPathWithSensors();
    }
  }
}

void executeCommand(char cmd) {
  Serial.print("Executing command: ");
  Serial.println(cmd);
  
  switch(cmd) {
    case 'f':
      moveForward();
      break;
    case 'b':
      moveBackward();
      break;
    case 'l':
      turnLeft();
      break;
    case 'r':
      turnRight();
      break;
    case 's':
      stopMotors();
      break;
    default:
      // Unknown command
      stopMotors();
  }
}

// IR sensor values
int irLeftOut, irLeftIn, irRightIn, irRightOut;

void readIRSensors() {
  irLeftOut = digitalRead(IR_LEFT_OUT);
  irLeftIn = digitalRead(IR_LEFT_IN);
  irRightIn = digitalRead(IR_RIGHT_IN);
  irRightOut = digitalRead(IR_RIGHT_OUT);
}

// Ultrasonic sensor values
float usFront, usRight, usLeft, usBack;

void readUltrasonicSensors() {
  usFront = getDistance(US_FRONT_TRIG, US_FRONT_ECHO);
  usRight = getDistance(US_RIGHT_TRIG, US_RIGHT_ECHO);
  usLeft = getDistance(US_LEFT_TRIG, US_LEFT_ECHO);
  usBack = getDistance(US_BACK_TRIG, US_BACK_ECHO);
}

float getDistance(int trigPin, int echoPin) {
  // Clear the trigger pin
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  
  // Set trigger high for 10 microseconds
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);
  
  // Read the echo pin - duration in microseconds
  long duration = pulseIn(echoPin, HIGH);
  
  // Calculate the distance in cm
  return duration * 0.034 / 2;
}

// Motor control functions
void moveForward() {
  analogWrite(LEFT_MOTOR_PIN1, FORWARD_SPEED);
  analogWrite(LEFT_MOTOR_PIN2, 0);
  analogWrite(RIGHT_MOTOR_PIN1, FORWARD_SPEED);
  analogWrite(RIGHT_MOTOR_PIN2, 0);
}

void moveBackward() {
  analogWrite(LEFT_MOTOR_PIN1, 0);
  analogWrite(LEFT_MOTOR_PIN2, FORWARD_SPEED);
  analogWrite(RIGHT_MOTOR_PIN1, 0);
  analogWrite(RIGHT_MOTOR_PIN2, FORWARD_SPEED);
}

void turnLeft() {
  analogWrite(LEFT_MOTOR_PIN1, 0);
  analogWrite(LEFT_MOTOR_PIN2, TURN_SPEED);
  analogWrite(RIGHT_MOTOR_PIN1, TURN_SPEED);
  analogWrite(RIGHT_MOTOR_PIN2, 0);
  delay(TURN_TIME);  // Wait for turn to complete
  stopMotors();
}

void turnRight() {
  analogWrite(LEFT_MOTOR_PIN1, TURN_SPEED);
  analogWrite(LEFT_MOTOR_PIN2, 0);
  analogWrite(RIGHT_MOTOR_PIN1, 0);
  analogWrite(RIGHT_MOTOR_PIN2, TURN_SPEED);
  delay(TURN_TIME);  // Wait for turn to complete
  stopMotors();
}

void stopMotors() {
  analogWrite(LEFT_MOTOR_PIN1, 0);
  analogWrite(LEFT_MOTOR_PIN2, 0);
  analogWrite(RIGHT_MOTOR_PIN1, 0);
  analogWrite(RIGHT_MOTOR_PIN2, 0);
}

// Check if current movement step is complete
unsigned long movementStartTime = 0;
unsigned long movementDuration = 800;  // Time for forward movement in ms

bool isMovementComplete() {
  // For turns, already handled in the turn functions
  // For forward movements, check time elapsed or destination reached
  char currentCmd = commands[currentCommand-1];
  
  if (currentCmd == 'f' || currentCmd == 'b') {
    // Time-based completion for forward/backward movements
    if (millis() - movementStartTime > movementDuration) {
      stopMotors();
      return true;
    }
    return false;
  }
  
  // For other commands (turns, stop), already completed
  return true;
}

// Adjust path based on sensor readings during movement
void adjustPathWithSensors() {
  // Using IR sensors for line following
  // Using ultrasonic sensors for wall detection
  
  char currentCmd = commands[currentCommand-1];
  
  if (currentCmd == 'f') {
    // Line following adjustment with IR sensors
    if (irLeftOut == LOW && irRightOut == LOW) {
      // Both outer sensors detect line - continue straight
      moveForward();
    } else if (irLeftOut == LOW) {
      // Left sensor detects line - adjust right
      analogWrite(LEFT_MOTOR_PIN1, FORWARD_SPEED*0.7);
      analogWrite(RIGHT_MOTOR_PIN1, FORWARD_SPEED);
    } else if (irRightOut == LOW) {
      // Right sensor detects line - adjust left
      analogWrite(LEFT_MOTOR_PIN1, FORWARD_SPEED);
      analogWrite(RIGHT_MOTOR_PIN1, FORWARD_SPEED*0.7);
    }
    
    // Wall avoidance with ultrasonic sensors
    if (usFront < 10) {  // Wall too close in front (10cm)
      stopMotors();
      moveBackward();
      delay(300);
      stopMotors();
    }
    
    if (usLeft < 5) {  // Wall too close on left
      // Adjust slightly right
      analogWrite(LEFT_MOTOR_PIN1, FORWARD_SPEED);
      analogWrite(RIGHT_MOTOR_PIN1, FORWARD_SPEED*0.8);
    }
    
    if (usRight < 5) {  // Wall too close on right
      // Adjust slightly left
      analogWrite(LEFT_MOTOR_PIN1, FORWARD_SPEED*0.8);
      analogWrite(RIGHT_MOTOR_PIN1, FORWARD_SPEED);
    }
  }
}

void resetMovementTimer() {
  movementStartTime = millis();
}
