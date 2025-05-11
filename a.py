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
    def __init__(self, master):
        self.master = master
        master.title("Maze Solver with Arduino Control")
        master.geometry("1200x700")
        
        # Serial communication variables
        self.serial_port = None
        self.is_connected = False
        self.stop_monitor_thread = threading.Event()
        self.monitor_thread = None
        
        # Arduino feedback data
        # self.sensor_data = {} # This was commented out in the original, keeping it so
        self.current_step = 0
        self.execution_status = "Not started"
        
        # Path conversion (from cells to movement commands)
        # self.direction_map = { # This was commented out in the original, keeping it so
        #     (1, 0): 'F',  # Down = Forward
        #     (-1, 0): 'B', # Up = Backward
        #     (0, 1): 'R',  # Right = Right
        #     (0, -1): 'L'  # Left = Left
        # }
        
        # Car's current orientation (0=North, 1=East, 2=South, 3=West)
        self.car_orientation = 0 # This is used in _generate_movement_commands, but initialized here
        
        # Motion sequence (relative to car's current orientation)
        # *** THIS IS THE MODIFIED SECTION ***
        self.orientation_commands = {
            # target_orientation: (current_orientation: command_sequence)
            0: {0: '', 1: 'L', 2: 'LL', 3: 'R'},  # Face North (from South, turn Left twice)
            1: {0: 'R', 1: '', 2: 'L', 3: 'LL'},  # Face East (from West, turn Left twice)
            2: {0: 'LL', 1: 'R', 2: '', 3: 'L'},  # Face South (from North, turn Left twice)
            3: {0: 'L', 1: 'LL', 2: 'R', 3: ''}   # Face West (from East, turn Left twice)
        }
        # *** END OF MODIFIED SECTION ***
        
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
        self.sensor_data = {} # Re-initialize sensor data here as it's used in _process_feedback

        # Remove old widgets if they exist
        if hasattr(self, 'main_frame'):
            for widget in self.main_frame.winfo_children():
                widget.destroy()
            self.main_frame.destroy()


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
        
        self.test_buttons = []
        for cmd_char in ('F', 'B', 'L', 'R', 'S'):
            btn = tk.Button(test_frame, text=cmd_char, command=lambda c=cmd_char: self._send_test_command(c), width=3, state=tk.DISABLED)
            btn.pack(side=tk.LEFT, padx=2)
            self.test_buttons.append(btn)

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
                elif path and (r,c) in path and (r,c) != self.car_location : fill = "lightblue" # Show path not yet traversed
                
                # Car location always takes precedence for fill color
                if (r,c) == self.car_location: fill = "orange"

                self.canvas.create_rectangle(x, y, x+self.SW, y+self.SW, fill=fill, outline="gray") # Lighter outline for cells
        # Horizontal walls
        for r_idx in range(self.R+1):
            for c_idx in range(self.C):
                if self.hw[r_idx][c_idx]:
                    x1, y1 = c_idx*self.SW, r_idx*self.SW
                    self.canvas.create_line(x1, y1, x1+self.SW, y1, width=4, fill="black") # Walls are black
        # Vertical walls
        for r_idx in range(self.R):
            for c_idx in range(self.C+1):
                if self.vw[r_idx][c_idx]:
                    x1, y1 = c_idx*self.SW, r_idx*self.SW
                    self.canvas.create_line(x1, y1, x1, y1+self.SW, width=4, fill="black") # Walls are black

    def _on_click(self, ev):
        x, y = ev.x, ev.y
        mode = self.mode.get()
        c, r = x // self.SW, y // self.SW

        if 0 <= r < self.R and 0 <= c < self.C: # Click is within maze bounds
            if mode in ("start", "end"):
                setattr(self, mode, (r,c))
                self.status.set(f"{mode.capitalize()} = {(r,c)}")
                
                # If setting start, also set as car location and reset path
                if mode == "start":
                    self.car_location = (r, c)
                    self.path = [] # Clear old path if start changes
                    self.movement_commands = []
                    if self.is_connected:
                        self.send_path_button.config(state=tk.DISABLED)
                        self.execute_path_button.config(state=tk.DISABLED)

                self._draw(self.path) # Redraw with new start/end/car
                return

            # Toggle specific wall edges (mode == "wall")
            cell_x_offset = x - c*self.SW
            cell_y_offset = y - r*self.SW
            edge_threshold = self.SW * 0.2 # 20% of cell width/height as threshold

            toggled = False
            # Check horizontal walls (top or bottom edge of cell (r,c))
            if cell_y_offset < edge_threshold and r < self.R: # Top edge of cell (r,c) -> hw[r][c]
                self.hw[r][c] ^= 1
                toggled = True
            elif cell_y_offset > self.SW - edge_threshold and r < self.R : # Bottom edge of cell (r,c) -> hw[r+1][c]
                self.hw[r+1][c] ^= 1
                toggled = True
            # Check vertical walls (left or right edge of cell (r,c))
            elif cell_x_offset < edge_threshold and c < self.C: # Left edge of cell (r,c) -> vw[r][c]
                self.vw[r][c] ^= 1
                toggled = True
            elif cell_x_offset > self.SW - edge_threshold and c < self.C: # Right edge of cell (r,c) -> vw[r][c+1]
                self.vw[r][c+1] ^= 1
                toggled = True
            
            if toggled:
                self.status.set(f"Toggled wall near {(r,c)}")
                self.path = [] # Clear path if walls change
                self.movement_commands = []
                if self.is_connected:
                    self.send_path_button.config(state=tk.DISABLED)
                    self.execute_path_button.config(state=tk.DISABLED)
                self._draw()
        else: # Click is outside maze bounds (e.g. on border walls directly)
            # More precise border wall toggling
            # Check horizontal border walls
            if r == 0 and 0 <= c < self.C and abs(y) < self.SW * 0.2: # Top border hw[0][c]
                self.hw[0][c] ^= 1
            elif r == self.R-1 and 0 <= c < self.C and abs(y - self.R*self.SW) < self.SW * 0.2 : # Bottom border hw[R][c]
                 self.hw[self.R][c] ^= 1
            # Check vertical border walls
            elif c == 0 and 0 <= r < self.R and abs(x) < self.SW * 0.2: # Left border vw[r][0]
                self.vw[r][0] ^= 1
            elif c == self.C-1 and 0 <= r < self.R and abs(x - self.C*self.SW) < self.SW * 0.2 : # Right border vw[r][C]
                 self.vw[r][self.C] ^= 1
            self._draw()


    def can_move(self, r, c, dr, dc):
        if dr == 1: return self.hw[r+1][c] == 0 # Moving Down
        if dr == -1: return self.hw[r][c] == 0  # Moving Up
        if dc == 1: return self.vw[r][c+1] == 0 # Moving Right
        if dc == -1: return self.vw[r][c] == 0  # Moving Left
        return False

    def solve(self):
        if not self.start or not self.end:
            messagebox.showwarning("Need start+end", "Please set both start and end")
            return
        prev = {self.start: None}
        dq = deque([self.start])
        path_found = False
        while dq:
            r, c = dq.popleft()
            if (r,c) == self.end:
                path_found = True
                break
            # Order of neighbors: S, N, E, W (to match typical maze generation preferences if any)
            # (dr, dc, direction_name)
            # For BFS, order doesn't strictly matter for finding *a* path, but can affect which path is found if multiple exist
            for dr, dc in [(1,0),(-1,0),(0,1),(0,-1)]: # Down, Up, Right, Left
                nr, nc = r+dr, c+dc
                if 0<=nr<self.R and 0<=nc<self.C and (nr,nc) not in prev and self.can_move(r,c,dr,dc):
                    prev[(nr,nc)] = (r,c); dq.append((nr,nc))
        
        if not path_found or self.end not in prev:
            messagebox.showinfo("No path", "Cannot reach end")
            self.status.set("No path found")
            self.path = []
            self.movement_commands = []
            if self.is_connected:
                self.send_path_button.config(state=tk.DISABLED)
            self._draw() # Redraw to clear any old path
            return

        path_coords, cur = [], self.end
        while cur:
            path_coords.append(cur); cur = prev[cur]
        path_coords.reverse()
        self.path = path_coords  # Store the path for later use
        self._draw(self.path)
        self.status.set(f"Path found ({len(self.path)} steps)")
        
        # Generate movement commands
        self._generate_movement_commands()
        
        # Enable sending path to car if connected
        if self.is_connected and self.movement_commands:
            self.send_path_button.config(state=tk.NORMAL)
        else:
            self.send_path_button.config(state=tk.DISABLED)

    def _reset(self):
        # Re-initialize wall arrays
        self.hw = [[0]*self.C for _ in range(self.R+1)]
        self.vw = [[0]*(self.C+1) for _ in range(self.R)]
        self._set_border_walls() # Set outer border walls

        self.start = self.end = None
        self.car_location = None
        self.path = []
        self.movement_commands = []
        self.status.set("Cleared. Set start/end or walls.")
        self.mode.set("wall") # Reset mode to wall
        
        # Reset Arduino control states
        if self.is_connected:
            self.send_path_button.config(state=tk.DISABLED)
            self.execute_path_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.DISABLED) # Should be enabled only during execution
        
        self.step_var.set("Step: 0/0")
        self.status_var.set("Status: Not started")

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
            
        # Generate movement commands if they don't exist (should be generated by solve)
        if not self.movement_commands and self.path:
            self._generate_movement_commands()
            
        try:
            with open(file_path, 'w') as f:
                f.write(f"Maze Dimensions: {self.R} Rows, {self.C} Columns\n")
                f.write(f"Start: {self.start}, End: {self.end}\n\n")
                
                # Write path cells
                f.write("Path (row, col):\n")
                for r, c in self.path:
                    f.write(f"({r}, {c})\n")
                    
                # Write movement commands
                f.write("\nMovement Commands (Assumed start North):\n")
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
            'end': self.end,
            'car_location': self.car_location # Save car location too
        }
        
        try:
            with open(file_path, 'w') as f:
                json.dump(maze_data, f, indent=2) # Added indent for readability
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
            
            # Basic validation
            if not all(k in maze_data for k in ['rows', 'cols', 'horizontal_walls', 'vertical_walls']):
                messagebox.showerror("Load Error", "Invalid maze file format.")
                return

            # Store old dimensions for widget re-creation check
            old_R, old_C = self.R, self.C

            self.R = maze_data['rows']
            self.C = maze_data['cols']
            self.hw = maze_data['horizontal_walls']
            self.vw = maze_data['vertical_walls']
            
            # Handle potential None for start/end from older saves or manual edits
            self.start = tuple(maze_data['start']) if maze_data.get('start') else None
            self.end = tuple(maze_data['end']) if maze_data.get('end') else None
            self.car_location = tuple(maze_data['car_location']) if maze_data.get('car_location') else self.start

            # Clear path and commands
            self.path = []
            self.movement_commands = []
            
            # If dimensions changed, we need to rebuild UI parts related to canvas size
            if self.R != old_R or self.C != old_C:
                # Recompute canvas dimensions
                canvas_size = 500 # Or get from a more dynamic source if UI allows resizing
                self.SW = canvas_size // max(self.C, self.R, 1) # Avoid division by zero if C/R is 0
                self.canvas_width = self.C * self.SW
                self.canvas_height = self.R * self.SW
                self.canvas.config(width=self.canvas_width, height=self.canvas_height)

            self._draw() # Redraw with loaded maze data
            self.status.set(f"Maze loaded from {file_path}")
            
            # Reset Arduino control states
            if self.is_connected:
                self.send_path_button.config(state=tk.DISABLED)
                self.execute_path_button.config(state=tk.DISABLED)
                self.stop_button.config(state=tk.DISABLED)


        except json.JSONDecodeError:
            messagebox.showerror("Load Error", "Invalid JSON file.")
        except Exception as e:
            messagebox.showerror("Load error", f"An unexpected error occurred: {str(e)}")

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
            messagebox.showerror("Export error", f"Error saving image: {str(e)}")

    def _refresh_ports(self):
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_combo['values'] = ports
        if ports:
            self.port_combo.current(0)
        else:
            self.port_var.set("") # Clear if no ports

    def _toggle_connection(self):
        if not self.is_connected:
            port = self.port_var.get()
            if not port:
                messagebox.showwarning("No Port", "Please select a serial port")
                return
                
            try:
                # Connect to Arduino with a 115200 baud rate
                self.serial_port = serial.Serial(port, 115200, timeout=1)
                self._log(f"Attempting to connect to {port}...")
                # Arduino Uno/Nano with CH340 might take a moment to be ready after DTR toggle
                time.sleep(2)  # Wait for Arduino to reset and initialize
                
                # Send a simple handshake or check if Arduino is responsive
                # self.serial_port.write(b"PING\n") # Example, Arduino would need to respond
                # response = self.serial_port.readline().decode('utf-8').strip()
                # if "initialized" in response or "PONG" in response: # Check for expected Arduino startup message

                # For now, assume connection if no exception after open and sleep
                init_line = self.serial_port.readline().decode('utf-8').strip() # Read initial message
                if "Arduino Maze Solver Car initialized" in init_line:
                    self._log(f"← {init_line}") # Log the init message
                    self.is_connected = True
                    self.connect_button.config(text="Disconnect")
                    self.status.set(f"Connected to {port}")
                    self._log(f"Successfully connected to {port}")
                    
                    # Start monitoring thread
                    self.stop_monitor_thread.clear()
                    self.monitor_thread = threading.Thread(target=self._monitor_serial, daemon=True)
                    # self.monitor_thread.daemon = True # Set daemon before start
                    self.monitor_thread.start()
                    
                    # Enable control buttons
                    if self.path and self.movement_commands: # Path exists and commands generated
                        self.send_path_button.config(state=tk.NORMAL)
                    
                    for btn in self.test_buttons:
                        btn.config(state=tk.NORMAL)
                else:
                    self._log(f"Arduino did not send expected initialization message. Received: '{init_line}'")
                    self.serial_port.close()
                    messagebox.showerror("Connection Error", "Arduino did not respond as expected. Check sketch and reset Arduino.")

            except serial.SerialException as e:
                messagebox.showerror("Connection Error", f"Could not open port {port}: {str(e)}")
                self._log(f"SerialException: {str(e)}")
            except Exception as e:
                messagebox.showerror("Connection Error", f"An unexpected error occurred: {str(e)}")
                self._log(f"Error: {str(e)}")
        else:
            # Disconnect
            self.stop_monitor_thread.set() # Signal thread to stop
            if self.monitor_thread and self.monitor_thread.is_alive():
                self.monitor_thread.join(timeout=2) # Wait for thread to finish
            
            if self.serial_port and self.serial_port.is_open:
                try:
                    self.serial_port.close()
                except Exception as e:
                    self._log(f"Error closing serial port: {e}")
            
            self.is_connected = False
            self.serial_port = None # Clear the serial port object
            self.connect_button.config(text="Connect")
            self.send_path_button.config(state=tk.DISABLED)
            self.execute_path_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.DISABLED)
            for btn in self.test_buttons:
                btn.config(state=tk.DISABLED)

            self.status.set("Disconnected")
            self._log("Disconnected")

    def _monitor_serial(self):
        """Thread function to monitor serial data from Arduino"""
        self._log("Serial monitor thread started.")
        while not self.stop_monitor_thread.is_set():
            if self.serial_port and self.serial_port.is_open:
                try:
                    if self.serial_port.in_waiting > 0:
                        # Read line by line
                        line = self.serial_port.readline().decode('utf-8', errors='replace').strip()
                        if line: # Process only if line is not empty
                            self._log(f"← {line}")
                            # Schedule GUI updates on the main thread
                            self.master.after(0, self._process_feedback, line)
                except serial.SerialException as e:
                    self._log(f"SerialException in monitor: {str(e)}. Disconnecting.")
                    self.master.after(0, self._handle_serial_error) # Handle error in main thread
                    break # Exit thread
                except UnicodeDecodeError as e:
                    self._log(f"UnicodeDecodeError in monitor: {str(e)}. Raw: {self.serial_port.read(self.serial_port.in_waiting)}")
                except Exception as e:
                    # Log other unexpected errors
                    self._log(f"Error reading from serial: {str(e)}")
                    # Consider whether to break or continue based on error type
                    # For robustness, might try to continue unless it's a fatal serial error
                    time.sleep(0.1) # Small delay to prevent busy-looping on persistent error
            else:
                # Serial port not open or not set, small delay and check stop flag
                time.sleep(0.1)
                if self.stop_monitor_thread.is_set():
                    break
        self._log("Serial monitor thread stopped.")

    def _handle_serial_error(self):
        """Handles serial errors encountered in the monitor thread, run in main thread."""
        if self.is_connected: # If was connected, perform disconnect operations
            messagebox.showerror("Serial Error", "Lost connection to Arduino or serial error.")
            self._toggle_connection() # This will attempt to disconnect cleanly

    def _process_feedback(self, data):
        """Process feedback data from Arduino. Called by master.after()"""
        try:
            # Parse data format: "DATA:sensor:value"
            if data.startswith("DATA:"):
                parts = data.split(":")
                if len(parts) >= 3:
                    sensor = parts[1].lower()
                    value = parts[2]
                    
                    # Update sensor data dictionary (make sure self.sensor_data is initialized)
                    if not hasattr(self, 'sensor_data'): self.sensor_data = {}
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
            
            # Process execution status update
            elif data.startswith("STEP:"):
                try:
                    step = int(data.split(":")[1])
                    self.current_step = step
                    total_commands = len(self.movement_commands) if self.movement_commands else 0
                    self.step_var.set(f"Step: {step+1}/{total_commands}") # Display 1-indexed step
                    
                    # Update car location in maze (use step+1 because path includes start)
                    self._update_car_location_from_command_index(step) # Use command index
                except (ValueError, IndexError) as e:
                    self._log(f"Error parsing STEP data: {data} - {e}")
            
            elif data.startswith("STATUS:"):
                status_msg = data.split(":", 1)[1]
                self.execution_status = status_msg
                self.status_var.set(f"Status: {status_msg}")
                
                # Handle completion or stop
                if status_msg.lower() == "completed" or status_msg.lower() == "stopped":
                    self.execute_path_button.config(state=tk.NORMAL if self.movement_commands else tk.DISABLED)
                    self.stop_button.config(state=tk.DISABLED)
                    if status_msg.lower() == "completed" and self.path:
                        self.car_location = self.path[-1] # Ensure car is at the end
                        self._draw(self.path)

            # Update car location if position received
            elif data.startswith("POS:"):
                try:
                    parts = data.split(":")
                    if len(parts) == 3:
                        row = int(parts[1])
                        col = int(parts[2])
                        self.car_location = (row, col)
                        self._draw(self.path) # Redraw with new car position
                except (ValueError, IndexError) as e:
                    self._log(f"Error parsing POS data: {data} - {e}")
        except Exception as e:
            self._log(f"Error processing feedback '{data}': {str(e)}")
    
    def _update_car_location_from_command_index(self, command_idx):
        """Update car location based on the current command being executed."""
        if not self.path or not self.movement_commands:
            return

        # This logic needs to trace the path based on commands executed
        # It's simpler to rely on Arduino sending POS updates after each F/B move.
        # If Arduino sends POS:r:c after each moveForward/Backward, that's the most reliable.
        # For now, let's assume Arduino's POS updates are the source of truth for car_location.
        # This function could be enhanced to predict location based on commands if POS is infrequent.

        # A simple approximation: if the command at command_idx was 'F' or 'B',
        # then the car should be at path[k] where k is the number of F/B commands up to command_idx.
        # This is complex to track perfectly here without knowing the Arduino's internal state.
        # Relying on POS:r:c from Arduino is better.
        pass # Let POS:r:c handle the update from Arduino.

    def _send_test_command(self, command):
        """Send a single test movement command to Arduino"""
        if not self.is_connected or not self.serial_port or not self.serial_port.is_open:
            messagebox.showwarning("Not Connected", "Please connect to Arduino first")
            return
            
        try:
            # Format: "CMD:X" where X is F, B, L, R, or S
            cmd_to_send = f"CMD:{command}\n"
            self.serial_port.write(cmd_to_send.encode('utf-8'))
            self._log(f"→ {cmd_to_send.strip()}")
        except serial.SerialTimeoutException:
            self._log(f"Timeout sending command: {command}")
            messagebox.showerror("Send Error", "Timeout sending command to Arduino.")
        except Exception as e:
            self._log(f"Error sending command '{command}': {str(e)}")
            messagebox.showerror("Send Error", f"Error sending command: {str(e)}")

    def _generate_movement_commands(self):
        """Convert path cells to movement commands for the car"""
        if not self.path or len(self.path) < 2:
            self.movement_commands = []
            self.car_orientation = 0 # Reset orientation if no path
            return "" # Return empty string for consistency
            
        # Initialize with start position and north orientation (0)
        # self.car_orientation should reflect the car's actual orientation at the start of the path.
        # For a fresh solve, it's 0 (North). If continuing, it might be different.
        # For now, assume it's always calculated from a fresh start (North = 0).
        current_r, current_c = self.path[0]
        # `self.car_orientation` is a class member, use it directly. Let's assume it's 0 (North) at the start of a new path.
        # Or, if the car has a known orientation, that should be used.
        # For now, let's make it explicit that we are starting assuming North.
        current_orientation_at_path_start = 0 # 0=N, 1=E, 2=S, 3=W
        
        # If self.start is defined, we can assume the car is at self.start
        # and its initial orientation is North (0) relative to the maze.
        # The Arduino also starts with currentOrientation = 0.
        
        # Reset or ensure car_orientation is 0 before generating a new full path
        self.car_orientation = 0 # Start facing North (0) for path generation

        generated_commands = []
        
        for i in range(len(self.path) - 1):
            current_pos = self.path[i]
            next_pos = self.path[i+1]
            
            # Calculate direction vector
            dr = next_pos[0] - current_pos[0]
            dc = next_pos[1] - current_pos[1]
            
            # Determine target orientation based on movement direction
            target_orientation_for_move = -1 # Invalid default
            if (dr, dc) == (-1, 0):   # Moving Up (North)
                target_orientation_for_move = 0
            elif (dr, dc) == (0, 1):  # Moving Right (East)
                target_orientation_for_move = 1
            elif (dr, dc) == (1, 0):   # Moving Down (South)
                target_orientation_for_move = 2
            elif (dr, dc) == (0, -1): # Moving Left (West)
                target_orientation_for_move = 3
                
            # Get turning commands to face the right direction
            if target_orientation_for_move != -1:
                # Ensure current_orientation for lookup is correct (0-3)
                # self.car_orientation is updated after each turn sequence
                turn_cmds_needed = self.orientation_commands[target_orientation_for_move][self.car_orientation]
                
                if turn_cmds_needed: # If any turns are needed
                    generated_commands.append(turn_cmds_needed)
                
                # Update car's orientation after turning
                self.car_orientation = target_orientation_for_move
                
                # Add forward command to move to next cell
                generated_commands.append('F') # Always move Forward after orienting
            else:
                self._log(f"Warning: Could not determine target orientation for move from {current_pos} to {next_pos}")

        self.movement_commands = ''.join(generated_commands)
        self._log(f"Generated movement commands: {self.movement_commands}")
        return self.movement_commands


    def _send_path_to_car(self):
        """Send the computed path to Arduino"""
        if not self.is_connected or not self.serial_port or not self.serial_port.is_open:
            messagebox.showwarning("Not Connected", "Please connect to Arduino first")
            return
            
        if not self.movement_commands:
            if not self.path:
                messagebox.showwarning("No Path", "Please solve the maze first, then generate commands.")
                return
            # Attempt to generate commands if path exists but commands don't
            self._generate_movement_commands()
            if not self.movement_commands: # Still no commands
                 messagebox.showwarning("No Commands", "Path exists but could not generate movement commands.")
                 return
            
        try:
            # Format for Arduino: "PATH:commands"
            cmd_to_send = f"PATH:{self.movement_commands}\n"
            self.serial_port.write(cmd_to_send.encode('utf-8'))
            self._log(f"→ Path sent: {self.movement_commands}")
            
            # Enable execute button, disable send path button until new path or clear
            self.execute_path_button.config(state=tk.NORMAL)
            self.send_path_button.config(state=tk.DISABLED) # Path sent, disable re-sending same path
            self.current_step = 0 # Reset step counter for new path
            self.step_var.set(f"Step: 0/{len(self.movement_commands)}")

        except serial.SerialTimeoutException:
            self._log(f"Timeout sending path.")
            messagebox.showerror("Send Error", "Timeout sending path to Arduino.")
        except Exception as e:
            self._log(f"Error sending path: {str(e)}")
            messagebox.showerror("Send Error", str(e))

    def _execute_path(self):
        """Tell Arduino to start executing the path"""
        if not self.is_connected or not self.serial_port or not self.serial_port.is_open:
            messagebox.showwarning("Not Connected", "Please connect to Arduino first")
            return
        
        if not self.movement_commands:
            messagebox.showwarning("No Path Sent", "No path has been sent to the Arduino to execute.")
            return

        try:
            # Send execute command
            cmd_to_send = "EXEC\n"
            self.serial_port.write(cmd_to_send.encode('utf-8'))
            self._log("→ Execute command sent")
            
            # Update UI
            self.execute_path_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.status_var.set("Status: Executing...") # Update status immediately
            self.current_step = 0 # Reset for display
            self.step_var.set(f"Step: 0/{len(self.movement_commands)}")

            # Car should start at self.start if a path is being executed
            if self.start:
                self.car_location = self.start
            self._draw(self.path)

        except serial.SerialTimeoutException:
            self._log(f"Timeout sending EXEC command.")
            messagebox.showerror("Execute Error", "Timeout sending EXEC command to Arduino.")
            # Re-enable execute button if EXEC failed to send
            self.execute_path_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
        except Exception as e:
            self._log(f"Error executing path: {str(e)}")
            messagebox.showerror("Execute Error", str(e))
            self.execute_path_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)

    def _stop_execution(self):
        """Send stop command to Arduino"""
        if not self.is_connected or not self.serial_port or not self.serial_port.is_open:
            # Silently return if not connected, or show mild warning
            # messagebox.showwarning("Not Connected", "Not connected to Arduino.")
            return
            
        try:
            # Send stop command
            cmd_to_send = "STOP\n"
            self.serial_port.write(cmd_to_send.encode('utf-8'))
            self._log("→ Stop command sent")
            
            # Update UI - Arduino will send "STATUS:Stopped" which _process_feedback will handle
            # self.execute_path_button.config(state=tk.NORMAL) # Let Arduino status confirm
            # self.stop_button.config(state=tk.DISABLED)
            # self.status_var.set("Status: Stopping...")

        except serial.SerialTimeoutException:
             self._log(f"Timeout sending STOP command.")
             messagebox.showerror("Stop Error", "Timeout sending STOP command to Arduino.")
        except Exception as e:
            self._log(f"Error stopping execution: {str(e)}")

    def _log(self, message):
        """Add message to log display with timestamp"""
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        log_entry = f"[{timestamp}] {message}\n"
        
        def append_to_log():
            # Insert at end and scroll to see it
            self.log_text.insert(tk.END, log_entry)
            self.log_text.see(tk.END)
            
            # Keep log size manageable (max 1000 lines)
            # This check can be slow if done every time.
            # Consider doing it less frequently or when log grows significantly.
            # current_lines = int(self.log_text.index('end-1c').split('.')[0])
            # if current_lines > 1000:
            #    self.log_text.delete(1.0, float(current_lines - 999)) # Delete oldest lines
        
        # Ensure UI updates are done in the main thread
        if self.master.winfo_exists(): # Check if master window still exists
            self.master.after(0, append_to_log)


# Run the application
if __name__ == "__main__":
    root = tk.Tk()
    app = MazeSolverGUI(root)
    # Handle window close gracefully
    def on_closing():
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            if app.is_connected:
                app._log("Window closing, attempting to disconnect Arduino...")
                if app.serial_port and app.serial_port.is_open:
                     app.serial_port.write(b"STOP\n") # Try to stop car if running
                app.stop_monitor_thread.set()
                if app.monitor_thread and app.monitor_thread.is_alive():
                    app.monitor_thread.join(timeout=1)
                if app.serial_port and app.serial_port.is_open:
                    app.serial_port.close()
                app._log("Disconnected on exit.")
            root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()
