#!/usr/bin/env python3
import tkinter as tk
from tkinter import messagebox, StringVar, simpledialog, filedialog, ttk
from collections import deque
import io
import json
import time
import threading
import serial
import serial.tools.list_ports
from PIL import Image

class MazeSolverGUI:
    def _init_(self, master):
        self.master = master
        master.title("Maze Solver with Arduino Control")
        master.geometry("1200x700")
        
        # Serial communication variables
        self.serial_port = None
        self.is_connected = False
        self.stop_monitor_thread = threading.Event()
        self.monitor_thread = None
        
        # Arduino feedback data
        self.sensor_data = {
            'front': 0, 'right': 0, 'left': 0, 'back': 0,
            'ir1': 0, 'ir2': 0, 'ir3': 0, 'ir4': 0
        }
        self.current_step = 0
        self.execution_status = "Not started"
        
        # Path conversion (from cells to movement commands)
        self.direction_map = {
            (1, 0): 'F',  # Down = Forward
            (-1, 0): 'B', # Up = Backward
            (0, 1): 'R',  # Right = Right
            (0, -1): 'L'  # Left = Left
        }
        
        # Car's current orientation (0=North, 1=East, 2=South, 3=West)
        self.car_orientation = 0
        
        # Motion sequence (relative to car's current orientation)
        self.orientation_commands = {
            # target_orientation: (current_orientation: command)
            0: {0: '', 1: 'L', 2: 'BB', 3: 'R'},  # Face North
            1: {0: 'R', 1: '', 2: 'L', 3: 'BB'},  # Face East
            2: {0: 'BB', 1: 'R', 2: '', 3: 'L'},  # Face South
            3: {0: 'L', 1: 'BB', 2: 'R', 3: ''}   # Face West
        }
        
        # For path execution
        self.path = []
        self.movement_commands = []
        
        self.create_new_maze()

    def create_new_maze(self):
        # Prompt for maze dimensions
        self.R = simpledialog.askinteger("Rows", "Enter number of rows:", parent=self.master, minvalue=1, maxvalue=50)
        self.C = simpledialog.askinteger("Columns", "Enter number of columns:", parent=self.master, minvalue=1, maxvalue=50)
        if not self.R or not self.C:
            messagebox.showerror("Error", "Invalid maze size. Exiting.")
            self.master.destroy()
            return

        # Compute canvas and cell size
        canvas_size = 500
        self.SW = canvas_size // max(self.C, self.R)
        self.canvas_width = self.C * self.SW
        self.canvas_height = self.R * self.SW

        # Wall arrays (1=wall)
        self.hw = [[0] * self.C for _ in range(self.R + 1)]
        self.vw = [[0] * (self.C + 1) for _ in range(self.R)]
        self._set_border_walls()

        self.start = self.end = None
        self.mode = StringVar(master=self.master, value="wall")
        self.car_location = None  # Current car location in maze coordinates

        # Remove old widgets if they exist
        for widget in self.master.winfo_children():
            widget.destroy()

        self._build_ui()
        self._draw()

    def _set_border_walls(self):
        for c in range(self.C):
            self.hw[0][c] = self.hw[self.R][c] = 1
        for r in range(self.R):
            self.vw[r][0] = self.vw[r][self.C] = 1

    def _build_ui(self):
        # Main container with 3 frames
        self.main_frame = tk.Frame(self.master)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left frame for canvas
        self.left_frame = tk.Frame(self.main_frame)
        self.left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Canvas for maze
        self.canvas = tk.Canvas(self.left_frame, width=self.canvas_width, height=self.canvas_height, bg="white")
        self.canvas.pack(expand=True)
        self.canvas.bind("<Button-1>", self._on_click)
        
        # Middle frame for controls
        self.middle_frame = tk.Frame(self.main_frame)
        self.middle_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
        
        # Right frame for Arduino feedback
        self.right_frame = tk.Frame(self.main_frame)
        self.right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Middle frame contents (maze controls)
        tk.Label(self.middle_frame, text="Mode:").pack(anchor=tk.W)
        for val, txt in [("wall", "Toggle Walls"), ("start", "Start"), ("end", "End")]:
            tk.Radiobutton(self.middle_frame, text=txt, variable=self.mode, value=val).pack(anchor=tk.W)

        # Main buttons
        tk.Button(self.middle_frame, text="Solve", command=self.solve).pack(fill=tk.X, pady=5)
        tk.Button(self.middle_frame, text="Clear", command=self._reset).pack(fill=tk.X, pady=5)
        
        # File operations section
        file_frame = tk.LabelFrame(self.middle_frame, text="File Operations")
        file_frame.pack(fill=tk.X, pady=10)
        
        tk.Button(file_frame, text="Save Maze", command=self._save_maze).pack(fill=tk.X, pady=3)
        tk.Button(file_frame, text="Load Maze", command=self._load_maze).pack(fill=tk.X, pady=3)
        tk.Button(file_frame, text="New Maze", command=self.create_new_maze).pack(fill=tk.X, pady=3)
        
        # Export buttons
        export_frame = tk.LabelFrame(self.middle_frame, text="Export")
        export_frame.pack(fill=tk.X, pady=10)
        
        tk.Button(export_frame, text="Export Path", command=self._export_path).pack(fill=tk.X, pady=3)
        tk.Button(export_frame, text="Save Image", command=self._export_image).pack(fill=tk.X, pady=3)

        self.status = StringVar(master=self.master, value="Click to set start/end or toggle walls")
        tk.Label(self.middle_frame, textvariable=self.status, wraplength=150, fg="blue").pack(pady=10)
        
        # Right frame contents (Arduino control)
        arduino_frame = tk.LabelFrame(self.right_frame, text="Arduino Communication")
        arduino_frame.pack(fill=tk.X, pady=5)
        
        # Serial port selection
        port_frame = tk.Frame(arduino_frame)
        port_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(port_frame, text="Port:").pack(side=tk.LEFT)
        self.port_var = StringVar()
        self.port_combo = ttk.Combobox(port_frame, textvariable=self.port_var)
        self.port_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Get available ports
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_combo['values'] = ports
        if ports:
            self.port_combo.current(0)
            
        tk.Button(port_frame, text="Refresh", command=self._refresh_ports).pack(side=tk.RIGHT)
        
        # Connect/Disconnect button
        self.connect_button = tk.Button(arduino_frame, text="Connect", command=self._toggle_connection)
        self.connect_button.pack(fill=tk.X, pady=5)
        
        # Car control
        control_frame = tk.LabelFrame(self.right_frame, text="Car Control")
        control_frame.pack(fill=tk.X, pady=10)
        
        # Send path button
        self.send_path_button = tk.Button(control_frame, text="Send Path to Car", command=self._send_path_to_car, state=tk.DISABLED)
        self.send_path_button.pack(fill=tk.X, pady=5)
        
        # Execute path button
        self.execute_path_button = tk.Button(control_frame, text="Execute Path", command=self._execute_path, state=tk.DISABLED)
        self.execute_path_button.pack(fill=tk.X, pady=5)
        
        # Stop execution button
        self.stop_button = tk.Button(control_frame, text="Stop Execution", command=self._stop_execution, state=tk.DISABLED)
        self.stop_button.pack(fill=tk.X, pady=5)
        
        # Test movement buttons
        test_frame = tk.Frame(control_frame)
        test_frame.pack(fill=tk.X, pady=5)
        
        tk.Button(test_frame, text="F", command=lambda: self._send_test_command('F'), width=3).pack(side=tk.LEFT, padx=2)
        tk.Button(test_frame, text="B", command=lambda: self._send_test_command('B'), width=3).pack(side=tk.LEFT, padx=2)
        tk.Button(test_frame, text="L", command=lambda: self._send_test_command('L'), width=3).pack(side=tk.LEFT, padx=2)
        tk.Button(test_frame, text="R", command=lambda: self._send_test_command('R'), width=3).pack(side=tk.LEFT, padx=2)
        tk.Button(test_frame, text="S", command=lambda: self._send_test_command('S'), width=3).pack(side=tk.LEFT, padx=2)
        
        # Sensor data display
        sensor_frame = tk.LabelFrame(self.right_frame, text="Sensor Data")
        sensor_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Ultrasonic sensors
        us_frame = tk.Frame(sensor_frame)
        us_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(us_frame, text="Ultrasonic:").grid(row=0, column=0, sticky=tk.W)
        tk.Label(us_frame, text="Front:").grid(row=1, column=0, sticky=tk.W)
        tk.Label(us_frame, text="Right:").grid(row=1, column=2, sticky=tk.W)
        tk.Label(us_frame, text="Left:").grid(row=2, column=0, sticky=tk.W)
        tk.Label(us_frame, text="Back:").grid(row=2, column=2, sticky=tk.W)
        
        self.front_dist = StringVar(value="0 cm")
        self.right_dist = StringVar(value="0 cm")
        self.left_dist = StringVar(value="0 cm")
        self.back_dist = StringVar(value="0 cm")
        
        tk.Label(us_frame, textvariable=self.front_dist).grid(row=1, column=1, sticky=tk.W)
        tk.Label(us_frame, textvariable=self.right_dist).grid(row=1, column=3, sticky=tk.W)
        tk.Label(us_frame, textvariable=self.left_dist).grid(row=2, column=1, sticky=tk.W)
        tk.Label(us_frame, textvariable=self.back_dist).grid(row=2, column=3, sticky=tk.W)
        
        # IR sensors
        ir_frame = tk.Frame(sensor_frame)
        ir_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(ir_frame, text="IR Sensors:").grid(row=0, column=0, sticky=tk.W, columnspan=4)
        
        self.ir1_val = StringVar(value="0")
        self.ir2_val = StringVar(value="0")
        self.ir3_val = StringVar(value="0")
        self.ir4_val = StringVar(value="0")
        
        tk.Label(ir_frame, text="IR1:").grid(row=1, column=0, sticky=tk.W)
        tk.Label(ir_frame, textvariable=self.ir1_val).grid(row=1, column=1, sticky=tk.W)
        tk.Label(ir_frame, text="IR2:").grid(row=1, column=2, sticky=tk.W)
        tk.Label(ir_frame, textvariable=self.ir2_val).grid(row=1, column=3, sticky=tk.W)
        
        tk.Label(ir_frame, text="IR3:").grid(row=2, column=0, sticky=tk.W)
        tk.Label(ir_frame, textvariable=self.ir3_val).grid(row=2, column=1, sticky=tk.W)
        tk.Label(ir_frame, text="IR4:").grid(row=2, column=2, sticky=tk.W)
        tk.Label(ir_frame, textvariable=self.ir4_val).grid(row=2, column=3, sticky=tk.W)
        
        # Execution status
        exec_frame = tk.Frame(sensor_frame)
        exec_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(exec_frame, text="Execution:").grid(row=0, column=0, sticky=tk.W)
        self.step_var = StringVar(value="Step: 0/0")
        self.status_var = StringVar(value="Status: Not started")
        
        tk.Label(exec_frame, textvariable=self.step_var).grid(row=1, column=0, sticky=tk.W)
        tk.Label(exec_frame, textvariable=self.status_var).grid(row=2, column=0, sticky=tk.W)
        
        # Log display
        log_frame = tk.LabelFrame(self.right_frame, text="Communication Log")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.log_text = tk.Text(log_frame, height=10, width=40)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Add scrollbar to log
        scrollbar = tk.Scrollbar(self.log_text)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.log_text.yview)

    def _draw(self, path=None):
        self.canvas.delete("all")
        # Cells
        for r in range(self.R):
            for c in range(self.C):
                x, y = c*self.SW, r*self.SW
                fill = "white"
                if (r,c) == self.start: fill = "green"
                elif (r,c) == self.end: fill = "red"
                elif (r,c) == self.car_location: fill = "orange"
                elif path and (r,c) in path: fill = "lightblue"
                self.canvas.create_rectangle(x, y, x+self.SW, y+self.SW, fill=fill, outline="black")
        # Horizontal walls
        for r in range(self.R+1):
            for c in range(self.C):
                if self.hw[r][c]:
                    x1, y1 = c*self.SW, r*self.SW
                    self.canvas.create_line(x1, y1, x1+self.SW, y1, width=4)
        # Vertical walls
        for r in range(self.R):
            for c in range(self.C+1):
                if self.vw[r][c]:
                    x1, y1 = c*self.SW, r*self.SW
                    self.canvas.create_line(x1, y1, x1, y1+self.SW, width=4)

    def _on_click(self, ev):
        x, y = ev.x, ev.y
        mode = self.mode.get()
        c, r = x // self.SW, y // self.SW

        if mode in ("start", "end"):
            if 0 <= r < self.R and 0 <= c < self.C:
                setattr(self, mode, (r,c))
                self.status.set(f"{mode.capitalize()} = {(r,c)}")
                
                # If setting start, also set as car location
                if mode == "start":
                    self.car_location = (r, c)
            self._draw()
            return

        # Toggle specific wall edges
        cell_x = x - c*self.SW
        cell_y = y - r*self.SW
        th = 6
        if 0 <= r <= self.R and 0 <= c < self.C and abs(cell_y) <= th:
            self.hw[r][c] ^= 1
        elif 0 <= r < self.R and 0 <= c < self.C and abs(cell_y-self.SW) <= th:
            self.hw[r+1][c] ^= 1
        elif 0 <= r < self.R and 0 <= c <= self.C and abs(cell_x) <= th:
            self.vw[r][c] ^= 1
        elif 0 <= r < self.R and 0 <= c < self.C and abs(cell_x-self.SW) <= th:
            self.vw[r][c+1] ^= 1
        self.status.set(f"Toggled wall at {(r,c)}")
        self._draw()

    def can_move(self, r, c, dr, dc):
        if dr == 1: return self.hw[r+1][c] == 0
        if dr == -1: return self.hw[r][c] == 0
        if dc == 1: return self.vw[r][c+1] == 0
        if dc == -1: return self.vw[r][c] == 0
        return False

    def solve(self):
        if not self.start or not self.end:
            messagebox.showwarning("Need start+end", "Please set both start and end")
            return
        prev = {self.start: None}
        dq = deque([self.start])
        while dq:
            r, c = dq.popleft()
            if (r,c) == self.end: break
            for dr, dc in [(1,0),(-1,0),(0,1),(0,-1)]:
                nr, nc = r+dr, c+dc
                if 0<=nr<self.R and 0<=nc<self.C and (nr,nc) not in prev and self.can_move(r,c,dr,dc):
                    prev[(nr,nc)] = (r,c); dq.append((nr,nc))
        if self.end not in prev:
            messagebox.showinfo("No path", "Cannot reach end")
            self.status.set("No path found")
            return
        path, cur = [], self.end
        while cur:
            path.append(cur); cur = prev[cur]
        path.reverse()
        self.path = path  # Store the path for later use
        self._draw(path)
        self.status.set(f"Path found ({len(path)} steps)")
        
        # Generate movement commands
        self._generate_movement_commands()
        
        # Enable sending path to car if connected
        if self.is_connected:
            self.send_path_button.config(state=tk.NORMAL)

    def _reset(self):
        self.hw = [[0]*self.C for _ in range(self.R+1)]
        self.vw = [[0]*(self.C+1) for _ in range(self.R)]
        self._set_border_walls()
        self.start = self.end = None
        self.car_location = None
        self.path = []
        self.movement_commands = []
        self.status.set("Cleared")
        self._draw()

    def _export_path(self):
        if not self.start or not self.end or not self.path:
            messagebox.showwarning("No path", "Please solve the maze first")
            return
            
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", ".txt"), ("All files", ".*")]
        )
        if not file_path:
            return
            
        # Generate movement commands if they don't exist
        if not self.movement_commands:
            self._generate_movement_commands()
            
        try:
            with open(file_path, 'w') as f:
                # Write path cells
                f.write("Path (row, col):\n")
                for r, c in self.path:
                    f.write(f"({r}, {c})\n")
                    
                # Write movement commands
                f.write("\nMovement Commands:\n")
                f.write(''.join(self.movement_commands))
                
            self.status.set(f"Path exported to {file_path}")
        except Exception as e:
            messagebox.showerror("Export error", str(e))

    def _save_maze(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", ".json"), ("All files", ".*")]
        )
        if not file_path:
            return
            
        maze_data = {
            'rows': self.R,
            'cols': self.C,
            'horizontal_walls': self.hw,
            'vertical_walls': self.vw,
            'start': self.start,
            'end': self.end
        }
        
        try:
            with open(file_path, 'w') as f:
                json.dump(maze_data, f)
            self.status.set(f"Maze saved to {file_path}")
        except Exception as e:
            messagebox.showerror("Save error", str(e))

    def _load_maze(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("JSON files", ".json"), ("All files", ".*")]
        )
        if not file_path:
            return
            
        try:
            with open(file_path, 'r') as f:
                maze_data = json.load(f)
                
            self.R = maze_data['rows']
            self.C = maze_data['cols']
            self.hw = maze_data['horizontal_walls']
            self.vw = maze_data['vertical_walls']
            self.start = tuple(maze_data['start']) if maze_data['start'] else None
            self.end = tuple(maze_data['end']) if maze_data['end'] else None
            
            # Update car location to start
            self.car_location = self.start
            
            # Recompute canvas dimensions
            canvas_size = 500
            self.SW = canvas_size // max(self.C, self.R)
            self.canvas_width = self.C * self.SW
            self.canvas_height = self.R * self.SW
            
            # Update canvas size
            self.canvas.config(width=self.canvas_width, height=self.canvas_height)
            
            self._draw()
            self.status.set(f"Maze loaded from {file_path}")
        except Exception as e:
            messagebox.showerror("Load error", str(e))

    def _export_image(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", ".png"), ("All files", ".*")]
        )
        if not file_path:
            return
            
        try:
            # Create a temporary PostScript file
            ps_data = self.canvas.postscript(colormode='color')
            
            # Convert PostScript to image using PIL
            img = Image.open(io.BytesIO(ps_data.encode('utf-8')))
            img.save(file_path)
            
            self.status.set(f"Image saved to {file_path}")
        except Exception as e:
            messagebox.showerror("Export error", str(e))

    def _refresh_ports(self):
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_combo['values'] = ports
        if ports:
            self.port_combo.current(0)

    def _toggle_connection(self):
        if not self.is_connected:
            port = self.port_var.get()
            if not port:
                messagebox.showwarning("No Port", "Please select a serial port")
                return
                
            try:
                # Connect to Arduino with a 115200 baud rate
                self.serial_port = serial.Serial(port, 115200, timeout=1)
                time.sleep(2)  # Wait for Arduino to reset
                
                self.is_connected = True
                self.connect_button.config(text="Disconnect")
                self.status.set(f"Connected to {port}")
                self._log(f"Connected to {port}")
                
                # Start monitoring thread
                self.stop_monitor_thread.clear()
                self.monitor_thread = threading.Thread(target=self._monitor_serial)
                self.monitor_thread.daemon = True
                self.monitor_thread.start()
                
                # Enable control buttons if path exists
                if self.path:
                    self.send_path_button.config(state=tk.NORMAL)
                
                # Enable test buttons
                for child in self.master.winfo_children():
                    if isinstance(child, tk.Button) and child.cget('text') in ('F', 'B', 'L', 'R', 'S'):
                        child.config(state=tk.NORMAL)
                
            except Exception as e:
                messagebox.showerror("Connection Error", str(e))
                self._log(f"Error: {str(e)}")
        else:
            # Disconnect
            self.stop_monitor_thread.set()
            if self.monitor_thread:
                self.monitor_thread.join(timeout=1)
            
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()
            
            self.is_connected = False
            self.connect_button.config(text="Connect")
            self.send_path_button.config(state=tk.DISABLED)
            self.execute_path_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.DISABLED)
            self.status.set("Disconnected")
            self._log("Disconnected")

    def _monitor_serial(self):
        """Thread function to monitor serial data from Arduino"""
        while not self.stop_monitor_thread.is_set():
            if self.serial_port and self.serial_port.is_open:
                try:
                    if self.serial_port.in_waiting:
                        line = self.serial_port.readline().decode('utf-8').strip()
                        self._log(f"← {line}")
                        self._process_feedback(line)
                except Exception as e:
                    self._log(f"Error reading: {str(e)}")
                    break
            time.sleep(0.1)

    def _process_feedback(self, data):
        """Process feedback data from Arduino"""
        try:
            # Parse data format: "DATA:sensor:value"
            if data.startswith("DATA:"):
                parts = data.split(":")
                if len(parts) >= 3:
                    sensor = parts[1].lower()
                    value = parts[2]
                    
                    # Update sensor data dictionary
                    self.sensor_data[sensor] = value
                    
                    # Update UI elements
                    if sensor == 'front':
                        self.front_dist.set(f"{value} cm")
                    elif sensor == 'right':
                        self.right_dist.set(f"{value} cm")
                    elif sensor == 'left':
                        self.left_dist.set(f"{value} cm")
                    elif sensor == 'back':
                        self.back_dist.set(f"{value} cm")
                    elif sensor == 'ir1':
                        self.ir1_val.set(value)
                    elif sensor == 'ir2':
                        self.ir2_val.set(value)
                    elif sensor == 'ir3':
                        self.ir3_val.set(value)
                    elif sensor == 'ir4':
                        self.ir4_val.set(value)
            
            # Process execution status update
            elif data.startswith("STEP:"):
                try:
                    step = int(data.split(":")[1])
                    self.current_step = step
                    self.step_var.set(f"Step: {step}/{len(self.movement_commands)}")
                    
                    # Update car location in maze
                    self._update_car_location(step)
                except ValueError:
                    pass
            
            elif data.startswith("STATUS:"):
                status = data.split(":", 1)[1]
                self.execution_status = status
                self.status_var.set(f"Status: {status}")
                
                # Handle completion
                if status.lower() == "completed":
                    self.execute_path_button.config(state=tk.NORMAL)
                    self.stop_button.config(state=tk.DISABLED)
            
            # Update car location if position received
            elif data.startswith("POS:"):
                try:
                    parts = data.split(":")
                    row = int(parts[1])
                    col = int(parts[2])
                    self.car_location = (row, col)
                    self._draw(self.path)
                except (ValueError, IndexError):
                    pass
        except Exception as e:
            self._log(f"Error processing feedback: {str(e)}")
    
    def _update_car_location(self, step_index):
        """Update car location based on current step in path execution"""
        if not self.path or step_index >= len(self.path):
            return
        
        # Set car location to current step in path
        self.car_location = self.path[step_index]
        self._draw(self.path)
        
    def _send_test_command(self, command):
        """Send a single test movement command to Arduino"""
        if not self.is_connected or not self.serial_port:
            messagebox.showwarning("Not Connected", "Please connect to Arduino first")
            return
            
        try:
            # Format: "CMD:X" where X is F, B, L, R, or S
            cmd = f"CMD:{command}\n"
            self.serial_port.write(cmd.encode())
            self._log(f"→ {cmd.strip()}")
        except Exception as e:
            self._log(f"Error sending command: {str(e)}")

    def _generate_movement_commands(self):
        """Convert path cells to movement commands for the car"""
        if not self.path or len(self.path) < 2:
            self.movement_commands = []
            return
            
        # Initialize with start position and north orientation
        current_pos = self.path[0]
        current_orientation = 0  # Start facing North
        commands = []
        
        for next_pos in self.path[1:]:
            # Calculate direction vector
            dr = next_pos[0] - current_pos[0]
            dc = next_pos[1] - current_pos[1]
            move_dir = (dr, dc)
            
            # Determine target orientation based on movement direction
            target_orientation = None
            if move_dir == (1, 0):   # Moving down (South)
                target_orientation = 2
            elif move_dir == (-1, 0): # Moving up (North)
                target_orientation = 0
            elif move_dir == (0, 1):  # Moving right (East)
                target_orientation = 1
            elif move_dir == (0, -1): # Moving left (West)
                target_orientation = 3
                
            # Get turning commands to face the right direction
            if target_orientation is not None:
                turn_cmd = self.orientation_commands[target_orientation][current_orientation]
                commands.append(turn_cmd)
                
                # Update orientation
                current_orientation = target_orientation
                
                # Add forward command to move to next cell
                commands.append('F')
                
            # Update current position
            current_pos = next_pos
            
        # Join all commands into a single string
        self.movement_commands = ''.join(commands)
        return self.movement_commands

    def _send_path_to_car(self):
        """Send the computed path to Arduino"""
        if not self.is_connected or not self.serial_port:
            messagebox.showwarning("Not Connected", "Please connect to Arduino first")
            return
            
        if not self.movement_commands:
            if not self.path:
                messagebox.showwarning("No Path", "Please solve the maze first")
                return
            self._generate_movement_commands()
            
        try:
            # Format for Arduino: "PATH:commands"
            cmd = f"PATH:{self.movement_commands}\n"
            self.serial_port.write(cmd.encode())
            self._log(f"→ Path sent: {self.movement_commands}")
            
            # Enable execute button
            self.execute_path_button.config(state=tk.NORMAL)
            
        except Exception as e:
            self._log(f"Error sending path: {str(e)}")
            messagebox.showerror("Send Error", str(e))

    def _execute_path(self):
        """Tell Arduino to start executing the path"""
        if not self.is_connected or not self.serial_port:
            messagebox.showwarning("Not Connected", "Please connect to Arduino first")
            return
            
        try:
            # Send execute command
            cmd = "EXEC\n"
            self.serial_port.write(cmd.encode())
            self._log("→ Execute command sent")
            
            # Update UI
            self.execute_path_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.status_var.set("Status: Executing")
            
        except Exception as e:
            self._log(f"Error executing path: {str(e)}")
            messagebox.showerror("Execute Error", str(e))

    def _stop_execution(self):
        """Send stop command to Arduino"""
        if not self.is_connected or not self.serial_port:
            return
            
        try:
            # Send stop command
            cmd = "STOP\n"
            self.serial_port.write(cmd.encode())
            self._log("→ Stop command sent")
            
            # Update UI
            self.execute_path_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            
        except Exception as e:
            self._log(f"Error stopping execution: {str(e)}")

    def _log(self, message):
        """Add message to log display with timestamp"""
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        log_entry = f"[{timestamp}] {message}\n"
        
        # Insert at end and scroll to see it
        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)
        
        # Keep log size manageable (max 1000 lines)
        lines = int(self.log_text.index('end-1c').split('.')[0])
        if lines > 1000:
            self.log_text.delete(1.0, 2.0)

# Run the application
if _name_ == "_main_":
    root = tk.Tk()
    app = MazeSolverGUI(root)
    root.mainloop()
