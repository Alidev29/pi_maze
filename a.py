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
        master.geometry("1200x750")
        
        self.serial_port = None
        self.is_connected = False
        self.stop_monitor_thread = threading.Event()
        self.monitor_thread = None
        
        self.current_step = 0
        self.execution_status = "Not started"
        
        self.car_orientation_for_path_gen = 0 
        
        self.orientation_commands = {
            0: {0: '', 1: 'L', 2: 'LL', 3: 'R'},
            1: {0: 'R', 1: '', 2: 'L', 3: 'LL'},
            2: {0: 'LL', 1: 'R', 2: '', 3: 'L'},
            3: {0: 'L', 1: 'LL', 2: 'R', 3: ''}
        }
        
        self.path = []
        self.movement_commands = ""
        self.movement_commands_detailed_str = ""
        self.gui_path_confirmed_by_arduino = False # NEW: Tracks if current GUI path is on Arduino

        self.R = 0 
        self.C = 0
        self.hw = []
        self.vw = []
        self.start = None
        self.end = None
        self.car_location = None
        self.sensor_data = {}

        self.create_new_maze()
        self.master.protocol("WM_DELETE_WINDOW", self._on_closing)

    def create_new_maze(self):
        if self.R == 0 or self.C == 0 or (hasattr(self, 'main_frame') and self.main_frame.winfo_exists()):
            if hasattr(self, 'main_frame') and self.main_frame.winfo_exists():
                new_R = simpledialog.askinteger("Rows", "Enter number of rows:", parent=self.master, minvalue=1, maxvalue=50, initialvalue=self.R or 5)
                new_C = simpledialog.askinteger("Columns", "Enter number of columns:", parent=self.master, minvalue=1, maxvalue=50, initialvalue=self.C or 5)
                if not new_R or not new_C:
                    if self.R == 0 or self.C == 0:
                        messagebox.showerror("Error", "Valid maze size required to start.")
                        self.master.destroy()
                        return
                else:
                    self.R, self.C = new_R, new_C
            else: 
                self.R = simpledialog.askinteger("Rows", "Enter number of rows:", parent=self.master, minvalue=1, maxvalue=50, initialvalue=5)
                self.C = simpledialog.askinteger("Columns", "Enter number of columns:", parent=self.master, minvalue=1, maxvalue=50, initialvalue=5)
                if not self.R or not self.C:
                    messagebox.showerror("Error", "Invalid maze size. Exiting.")
                    self.master.destroy()
                    return
        
        canvas_size = 500
        self.SW = canvas_size // max(self.C, self.R, 1)
        self.canvas_width = self.C * self.SW
        self.canvas_height = self.R * self.SW

        self.hw = [[0] * self.C for _ in range(self.R + 1)]
        self.vw = [[0] * (self.C + 1) for _ in range(self.R)]
        self._set_border_walls()

        self.start = self.end = None
        self.car_location = None
        self.path = []
        self.movement_commands = ""
        self.movement_commands_detailed_str = ""
        self.gui_path_confirmed_by_arduino = False # Reset flag
        self.sensor_data = {}

        if hasattr(self, 'mode'):
            self.mode.set("wall")
        else:
            self.mode = StringVar(value="wall")

        if hasattr(self, 'main_frame') and self.main_frame.winfo_exists():
            for widget in self.main_frame.winfo_children():
                widget.destroy()
            self.main_frame.destroy()
        
        self._build_ui()
        self.canvas.config(width=self.canvas_width, height=self.canvas_height)
        self._draw()
        self._update_button_states() # Update buttons after UI is built/rebuilt

    def _set_border_walls(self):
        if not self.R or not self.C: return # Guard against uninitialized R/C
        for c_idx in range(self.C):
            self.hw[0][c_idx] = self.hw[self.R][c_idx] = 1
        for r_idx in range(self.R):
            self.vw[r_idx][0] = self.vw[r_idx][self.C] = 1

    def _build_ui(self):
        self.main_frame = tk.Frame(self.master)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        self.left_frame = tk.Frame(self.main_frame)
        self.left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.canvas = tk.Canvas(self.left_frame, width=self.canvas_width, height=self.canvas_height, bg="ivory")
        self.canvas.pack(expand=True)
        self.canvas.bind("<Button-1>", self._on_click)
        
        self.middle_frame = tk.Frame(self.main_frame)
        self.middle_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
        
        self.right_frame = tk.Frame(self.main_frame)
        self.right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        tk.Label(self.middle_frame, text="Mode:").pack(anchor=tk.W)
        for val, txt in [("wall", "Toggle Walls"), ("start", "Start"), ("end", "End")]:
            tk.Radiobutton(self.middle_frame, text=txt, variable=self.mode, value=val).pack(anchor=tk.W)

        tk.Button(self.middle_frame, text="Solve", command=self.solve).pack(fill=tk.X, pady=5)
        tk.Button(self.middle_frame, text="Clear Maze", command=self._reset).pack(fill=tk.X, pady=5)
        
        file_frame = tk.LabelFrame(self.middle_frame, text="File")
        file_frame.pack(fill=tk.X, pady=10)
        tk.Button(file_frame, text="New Maze", command=self.create_new_maze).pack(fill=tk.X, pady=3)
        tk.Button(file_frame, text="Save Maze", command=self._save_maze).pack(fill=tk.X, pady=3)
        tk.Button(file_frame, text="Load Maze", command=self._load_maze).pack(fill=tk.X, pady=3)
        
        export_frame = tk.LabelFrame(self.middle_frame, text="Export")
        export_frame.pack(fill=tk.X, pady=10)
        tk.Button(export_frame, text="Export Path Cmds", command=self._export_path).pack(fill=tk.X, pady=3)
        tk.Button(export_frame, text="Save Maze Image", command=self._export_image).pack(fill=tk.X, pady=3)

        self.status = StringVar(value="Set start/end or toggle walls.")
        tk.Label(self.middle_frame, textvariable=self.status, wraplength=180, fg="blue").pack(pady=10)
        
        arduino_frame = tk.LabelFrame(self.right_frame, text="Arduino Communication")
        arduino_frame.pack(fill=tk.X, pady=5)
        
        port_frame = tk.Frame(arduino_frame)
        port_frame.pack(fill=tk.X, pady=5)
        tk.Label(port_frame, text="Port:").pack(side=tk.LEFT)
        self.port_var = StringVar()
        self.port_combo = ttk.Combobox(port_frame, textvariable=self.port_var, width=15)
        self.port_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        tk.Button(port_frame, text="Refresh", command=self._refresh_ports).pack(side=tk.RIGHT)
        self._refresh_ports()
        
        self.connect_button = tk.Button(arduino_frame, text="Connect", command=self._toggle_connection)
        self.connect_button.pack(fill=tk.X, pady=5)
        
        control_frame = tk.LabelFrame(self.right_frame, text="Car Control")
        control_frame.pack(fill=tk.X, pady=10)
        
        self.send_path_button = tk.Button(control_frame, text="Send Path to Car", command=self._send_path_to_car, state=tk.DISABLED)
        self.send_path_button.pack(fill=tk.X, pady=5)
        self.execute_path_button = tk.Button(control_frame, text="Execute Path", command=self._execute_path, state=tk.DISABLED)
        self.execute_path_button.pack(fill=tk.X, pady=5)
        self.stop_button = tk.Button(control_frame, text="Stop Execution", command=self._stop_execution, state=tk.DISABLED)
        self.stop_button.pack(fill=tk.X, pady=5)
        
        test_frame = tk.LabelFrame(control_frame, text="Test Movements")
        test_frame.pack(fill=tk.X, pady=5)
        self.test_buttons = {}
        for cmd_char in ('F', 'B', 'L', 'R', 'S'):
            btn = tk.Button(test_frame, text=cmd_char, command=lambda c=cmd_char: self._send_test_command(c), width=3, state=tk.DISABLED)
            btn.pack(side=tk.LEFT, padx=2, pady=2)
            self.test_buttons[cmd_char] = btn
        
        sensor_frame = tk.LabelFrame(self.right_frame, text="Sensor Data & Status")
        sensor_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        us_frame = tk.Frame(sensor_frame)
        us_frame.pack(fill=tk.X, pady=5)
        tk.Label(us_frame, text="Ultrasonic:").grid(row=0, column=0, columnspan=4, sticky=tk.W)
        self.front_dist = StringVar(value="F: --- cm")
        self.right_dist = StringVar(value="R: --- cm")
        self.left_dist = StringVar(value="L: --- cm")
        self.back_dist = StringVar(value="B: --- cm")
        tk.Label(us_frame, textvariable=self.front_dist, width=10).grid(row=1, column=0, sticky=tk.W)
        tk.Label(us_frame, textvariable=self.left_dist, width=10).grid(row=1, column=1, sticky=tk.W)
        tk.Label(us_frame, textvariable=self.right_dist, width=10).grid(row=1, column=2, sticky=tk.W)
        tk.Label(us_frame, textvariable=self.back_dist, width=10).grid(row=1, column=3, sticky=tk.W)
        
        exec_frame = tk.Frame(sensor_frame)
        exec_frame.pack(fill=tk.X, pady=5)
        self.step_var = StringVar(value="Step: 0/0")
        self.status_var = StringVar(value="Status: Not started")
        tk.Label(exec_frame, textvariable=self.step_var).pack(side=tk.LEFT, padx=5)
        tk.Label(exec_frame, textvariable=self.status_var).pack(side=tk.LEFT, padx=5)
        
        log_frame = tk.LabelFrame(self.right_frame, text="Communication Log")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.log_text = tk.Text(log_frame, height=8, width=40, wrap=tk.WORD)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = tk.Scrollbar(log_frame, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)

    def _draw(self, current_path_to_highlight=None):
        if not hasattr(self, 'canvas') or not self.canvas.winfo_exists(): return
        self.canvas.delete("all")
        for r_idx in range(self.R):
            for c_idx in range(self.C):
                x, y = c_idx*self.SW, r_idx*self.SW
                fill_color = "ivory"
                if (r_idx,c_idx) == self.start: fill_color = "pale green"
                elif (r_idx,c_idx) == self.end: fill_color = "salmon"
                
                if current_path_to_highlight and (r_idx,c_idx) in current_path_to_highlight:
                    if (r_idx,c_idx) != self.start and (r_idx,c_idx) != self.end:
                        fill_color = "light sky blue"
                
                if (r_idx,c_idx) == self.car_location: fill_color = "orange"
                
                self.canvas.create_rectangle(x, y, x+self.SW, y+self.SW, fill=fill_color, outline="gray60")
        
        for r_idx in range(self.R+1):
            for c_idx in range(self.C):
                if self.hw[r_idx][c_idx]:
                    x1, y1 = c_idx*self.SW, r_idx*self.SW
                    self.canvas.create_line(x1, y1, x1+self.SW, y1, width=3, fill="black")
        for r_idx in range(self.R):
            for c_idx in range(self.C+1):
                if self.vw[r_idx][c_idx]:
                    x1, y1 = c_idx*self.SW, r_idx*self.SW
                    self.canvas.create_line(x1, y1, x1, y1+self.SW, width=3, fill="black")

    def _on_click(self, ev):
        x, y = ev.x, ev.y
        mode = self.mode.get()
        c, r = x // self.SW, y // self.SW

        if 0 <= r < self.R and 0 <= c < self.C:
            if mode in ("start", "end"):
                setattr(self, mode, (r,c))
                self.status.set(f"{mode.capitalize()} set to {(r,c)}")
                if mode == "start":
                    self.car_location = (r, c)
                self.path = [] 
                self.movement_commands = ""
                self.movement_commands_detailed_str = ""
                self.gui_path_confirmed_by_arduino = False # Path changed
                self._update_button_states()
                self._draw(self.path)
                return

            cell_x_offset = x - c*self.SW
            cell_y_offset = y - r*self.SW
            edge_threshold = self.SW * 0.25

            toggled = False
            if cell_y_offset < edge_threshold and r < self.R :
                self.hw[r][c] ^= 1; toggled = True
            elif cell_y_offset > self.SW - edge_threshold and r < self.R:
                self.hw[r+1][c] ^= 1; toggled = True
            elif cell_x_offset < edge_threshold and c < self.C:
                self.vw[r][c] ^= 1; toggled = True
            elif cell_x_offset > self.SW - edge_threshold and c < self.C:
                self.vw[r][c+1] ^= 1; toggled = True
            
            if toggled:
                self.status.set(f"Toggled wall near {(r,c)}")
                self.path = []
                self.movement_commands = ""
                self.movement_commands_detailed_str = ""
                self.gui_path_confirmed_by_arduino = False # Walls changed, path invalid
                self._update_button_states()
                self._draw()
        else:
            self._draw()

    def can_move(self, r, c, dr, dc):
        if dr == 1: return not self.hw[r+1][c]
        if dr == -1: return not self.hw[r][c]
        if dc == 1: return not self.vw[r][c+1]
        if dc == -1: return not self.vw[r][c]
        return False

    def solve(self):
        if not self.start or not self.end:
            messagebox.showwarning("Input Missing", "Please set both Start and End points.")
            return
        
        q = deque([(self.start, [self.start])])
        visited = {self.start}
        solved_path = []

        while q:
            (curr_r, curr_c), path_taken = q.popleft()
            if (curr_r, curr_c) == self.end:
                solved_path = path_taken
                break
            for dr, dc in [(-1,0), (0,1), (1,0), (0,-1)]:
                nr, nc = curr_r + dr, curr_c + dc
                if 0 <= nr < self.R and 0 <= nc < self.C and \
                   (nr, nc) not in visited and self.can_move(curr_r, curr_c, dr, dc):
                    visited.add((nr, nc))
                    q.append(((nr, nc), path_taken + [(nr, nc)]))
        
        self.gui_path_confirmed_by_arduino = False # New solve, path not confirmed yet
        if solved_path:
            self.path = solved_path
            self.status.set(f"Path found: {len(self.path)-1} moves.")
            self._generate_movement_commands()
        else:
            self.path = []
            self.movement_commands = ""
            self.movement_commands_detailed_str = ""
            self.status.set("No path found to the end point.")
        
        self._update_button_states()
        self._draw(self.path)

    def _reset(self):
        self.hw = [[0] * self.C for _ in range(self.R + 1)]
        self.vw = [[0] * (self.C + 1) for _ in range(self.R)]
        self._set_border_walls()
        self.start = self.end = self.car_location = None
        self.path = []
        self.movement_commands = ""
        self.movement_commands_detailed_str = ""
        self.gui_path_confirmed_by_arduino = False # Reset flag
        self.status.set("Maze cleared. Set start/end or walls.")
        self.mode.set("wall")
        self._update_button_states()
        self.step_var.set("Step: 0/0")
        self.status_var.set("Status: Not started")
        self._draw()

    def get_expected_walls(self, r, c, orientation):
        front_wall, left_wall, right_wall = 0, 0, 0
        if orientation == 0: front_wall = 1 if r == 0 or self.hw[r][c] else 0
        elif orientation == 1: front_wall = 1 if c == self.C - 1 or self.vw[r][c+1] else 0
        elif orientation == 2: front_wall = 1 if r == self.R - 1 or self.hw[r+1][c] else 0
        elif orientation == 3: front_wall = 1 if c == 0 or self.vw[r][c] else 0

        if orientation == 0: left_wall = 1 if c == 0 or self.vw[r][c] else 0
        elif orientation == 1: left_wall = 1 if r == 0 or self.hw[r][c] else 0
        elif orientation == 2: left_wall = 1 if c == self.C - 1 or self.vw[r][c+1] else 0
        elif orientation == 3: left_wall = 1 if r == self.R - 1 or self.hw[r+1][c] else 0

        if orientation == 0: right_wall = 1 if c == self.C - 1 or self.vw[r][c+1] else 0
        elif orientation == 1: right_wall = 1 if r == self.R - 1 or self.hw[r+1][c] else 0
        elif orientation == 2: right_wall = 1 if c == 0 or self.vw[r][c] else 0
        elif orientation == 3: right_wall = 1 if r == 0 or self.hw[r][c] else 0
        return front_wall, left_wall, right_wall

    def _generate_movement_commands(self):
        if not self.path or len(self.path) < 2:
            self.movement_commands = ""
            self.movement_commands_detailed_str = ""
            self.gui_path_confirmed_by_arduino = False # No path, so not confirmed
            return

        self.car_orientation_for_path_gen = 0
        temp_orientation = self.car_orientation_for_path_gen
        
        detailed_segments = []
        simple_cmds_list = []

        for i in range(len(self.path) - 1):
            current_r, current_c = self.path[i]
            next_r, next_c = self.path[i+1]

            dr, dc = next_r - current_r, next_c - current_c
            
            target_move_orientation = -1
            if (dr, dc) == (-1, 0): target_move_orientation = 0
            elif (dr, dc) == (0, 1): target_move_orientation = 1
            elif (dr, dc) == (1, 0): target_move_orientation = 2
            elif (dr, dc) == (0, -1): target_move_orientation = 3

            if target_move_orientation != -1:
                turn_sequence = self.orientation_commands[target_move_orientation][temp_orientation]
                
                for turn_char in turn_sequence:
                    simple_cmds_list.append(turn_char)
                    if turn_char == 'L': temp_orientation = (temp_orientation + 3) % 4
                    elif turn_char == 'R': temp_orientation = (temp_orientation + 1) % 4
                    ef, el, er = self.get_expected_walls(current_r, current_c, temp_orientation)
                    detailed_segments.append(f"{turn_char},{ef},{el},{er}")

                simple_cmds_list.append('F')
                ef, el, er = self.get_expected_walls(next_r, next_c, temp_orientation)
                detailed_segments.append(f"F,{ef},{el},{er}")
            else:
                self._log(f"ERR: Path gen, unknown move from ({current_r},{current_c}) to ({next_r},{next_c})")
        
        self.movement_commands = "".join(simple_cmds_list)
        self.movement_commands_detailed_str = ";".join(detailed_segments)
        if self.movement_commands_detailed_str:
            self.movement_commands_detailed_str += ";"
        
        self.gui_path_confirmed_by_arduino = False # New commands generated, not yet confirmed by Arduino
        self._log(f"Path cmds: {self.movement_commands}")
        return self.movement_commands_detailed_str

    def _send_path_to_car(self):
        if not self._check_connection("Send Path"): return
        if not self.movement_commands_detailed_str:
            messagebox.showwarning("No Path", "No path commands generated. Solve the maze first.")
            return
            
        try:
            cmd_to_send = f"PATH:{self.movement_commands_detailed_str}\n"
            if len(cmd_to_send) > 250:
                 self._log(f"WARN: Path string length {len(cmd_to_send)} may exceed Arduino buffer.")
                 if not messagebox.askyesno("Path Too Long", f"Path command string is very long ({len(cmd_to_send)} chars).\nArduino might not receive it all.\n\nContinue anyway?"):
                    return

            self.serial_port.write(cmd_to_send.encode('utf-8'))
            self._log(f"→ PATH sent ({self.movement_commands_detailed_str.count(';')} segments)")
            
            self.current_step = 0
            num_segments = self.movement_commands_detailed_str.count(';')
            self.step_var.set(f"Step: 0/{num_segments}")
            # Don't set gui_path_confirmed_by_arduino to True here yet.
            # Wait for "STATUS:Path received" from Arduino.
            # _update_button_states will be called by _process_feedback then.
            # For immediate feedback, we can assume it will be confirmed, but safer to wait.
            # Let's call it with path_just_sent_successfully=True to disable Send and enable Execute if all good.
            self._update_button_states(path_just_sent_successfully=True) # Crucial fix here
            
        except Exception as e:
            self._log(f"ERR: Sending path: {str(e)}")
            messagebox.showerror("Send Error", str(e))

    def _execute_path(self):
        if not self._check_connection("Execute Path"): return
        try:
            self.serial_port.write(b"EXEC\n")
            self._log("→ EXEC command sent")
            self.execution_status = "Executing..." # Tentative status
            self._update_button_states() # Update based on new status
            self.status_var.set("Status: Executing...")
            if self.start: self.car_location = self.start
            self._draw(self.path)
        except Exception as e:
            self._log(f"ERR: Executing path: {str(e)}")
            messagebox.showerror("Execute Error", str(e))

    def _stop_execution(self):
        if not self._check_connection("Stop Execution", silent=True): return
        try:
            self.serial_port.write(b"STOP\n")
            self._log("→ STOP command sent")
        except Exception as e:
            self._log(f"ERR: Stopping execution: {str(e)}")

    def _send_test_command(self, command_char):
        if not self._check_connection(f"Test {command_char}"): return
        try:
            cmd_to_send = f"CMD:{command_char}\n"
            self.serial_port.write(cmd_to_send.encode('utf-8'))
            self._log(f"→ {cmd_to_send.strip()}")
        except Exception as e:
            self._log(f"ERR: Sending test cmd '{command_char}': {str(e)}")

    def _toggle_connection(self):
        if not self.is_connected:
            port = self.port_var.get()
            if not port:
                messagebox.showwarning("No Port", "Please select a serial port.")
                return
            try:
                self.serial_port = serial.Serial(port, 115200, timeout=1)
                self._log(f"Attempting connection to {port}...")
                time.sleep(2)
                
                init_msg = ""
                if self.serial_port.in_waiting > 0:
                    init_msg = self.serial_port.readline().decode('utf-8', errors='replace').strip()
                
                if "Arduino Maze Solver Car initialized" in init_msg:
                    self._log(f"← {init_msg}")
                    self.is_connected = True
                    self.connect_button.config(text="Disconnect")
                    self.status.set(f"Connected to {port}")
                    self._log(f"Successfully connected to {port}")
                    
                    self.stop_monitor_thread.clear()
                    self.monitor_thread = threading.Thread(target=self._monitor_serial, daemon=True)
                    self.monitor_thread.start()
                else:
                    self._log(f"ERR: Arduino init message not received or incorrect. Got: '{init_msg}'")
                    if self.serial_port and self.serial_port.is_open: self.serial_port.close()
                    self.serial_port = None
                    messagebox.showerror("Connection Failed", "Arduino did not initialize correctly. Check sketch and port.")
            except serial.SerialException as e:
                self._log(f"ERR: SerialException on connect: {str(e)}")
                messagebox.showerror("Connection Error", f"Could not open port {port}: {str(e)}")
                self.serial_port = None
            except Exception as e:
                self._log(f"ERR: Unexpected connect error: {str(e)}")
                messagebox.showerror("Connection Error", f"An unexpected error occurred: {str(e)}")
                if self.serial_port and self.serial_port.is_open: self.serial_port.close()
                self.serial_port = None
        else: 
            self.stop_monitor_thread.set()
            if self.monitor_thread and self.monitor_thread.is_alive():
                self.monitor_thread.join(timeout=1)
            if self.serial_port and self.serial_port.is_open:
                try:
                    if self.execution_status.lower().startswith("executing"):
                         self.serial_port.write(b"STOP\n")
                         self._log("→ Sent STOP on disconnect.")
                    self.serial_port.close()
                except Exception as e:
                    self._log(f"ERR: Closing serial port: {e}")
            self.is_connected = False
            self.serial_port = None
            self.connect_button.config(text="Connect")
            self.status.set("Disconnected")
            self._log("Disconnected.")
        self._update_button_states()

    def _monitor_serial(self):
        self._log("Serial monitor thread started.")
        while not self.stop_monitor_thread.is_set():
            if not (self.serial_port and self.serial_port.is_open):
                if not self.stop_monitor_thread.is_set():
                    self._log("Serial port closed or unavailable in monitor thread.")
                    self.master.after(0, self._handle_serial_error_in_main_thread)
                break 
            try:
                if self.serial_port.in_waiting > 0:
                    line = self.serial_port.readline().decode('utf-8', errors='replace').strip()
                    if line:
                        self.master.after(0, self._process_feedback, line)
            except serial.SerialException as e:
                if not self.stop_monitor_thread.is_set():
                     self._log(f"SerialException in monitor: {e}. Stopping monitor.")
                     self.master.after(0, self._handle_serial_error_in_main_thread)
                break
            except Exception as e:
                if not self.stop_monitor_thread.is_set():
                    self._log(f"ERR: Reading serial: {e}")
                time.sleep(0.05)
            time.sleep(0.01)
        self._log("Serial monitor thread stopped.")

    def _handle_serial_error_in_main_thread(self):
        if self.is_connected:
            self._log("Connection lost. Attempting to disconnect UI.")
            self.is_connected = False
            self._toggle_connection()

    def _process_feedback(self, data):
        self._log(f"← {data}")
        try:
            if data.startswith("DATA:"):
                parts = data.split(":")
                if len(parts) >= 3:
                    sensor, value = parts[1].lower(), parts[2]
                    self.sensor_data[sensor] = value
                    if sensor == 'front': self.front_dist.set(f"F: {value} cm")
                    elif sensor == 'left': self.left_dist.set(f"L: {value} cm")
                    elif sensor == 'right': self.right_dist.set(f"R: {value} cm")
                    elif sensor == 'back': self.back_dist.set(f"B: {value} cm")
            elif data.startswith("POS:"):
                parts = data.split(":")
                if len(parts) >= 3: # POS:row:col or POS:row:col:orientation
                    r, c = int(parts[1]), int(parts[2])
                    self.car_location = (r, c)
                    # if len(parts) == 4: self.car_orientation_for_path_gen = int(parts[3]) # Update if Arduino sends it
                    self._draw(self.path)
            elif data.startswith("STEP:"):
                step_idx = int(data.split(":")[1])
                self.current_step = step_idx
                total_segments = self.movement_commands_detailed_str.count(';')
                self.step_var.set(f"Step: {step_idx + 1}/{total_segments}")
            elif data.startswith("STATUS:"):
                status_msg = data.split(":", 1)[1]
                self.execution_status = status_msg
                self.status_var.set(f"Status: {status_msg}")

                if "Path received" in status_msg:
                    self.gui_path_confirmed_by_arduino = True
                elif "Completed" in status_msg or "Stopped" in status_msg:
                    # After completion/stop, path is no longer "pending" on Arduino for a new EXEC command
                    # It might still be in Arduino's memory, but for new EXEC, we might want re-confirmation.
                    # For simplicity, let's say confirmed until new path is generated in GUI.
                    # self.gui_path_confirmed_by_arduino = False # Or keep True if re-exec is desired
                    pass 
                
                self._update_button_states() # Update based on new status
                if "Completed" in status_msg and self.path:
                    self.car_location = self.path[-1]
                    self._draw(self.path)
        except Exception as e:
            self._log(f"ERR: Processing Arduino msg '{data}': {e}")

    def _update_button_states(self, path_just_sent_successfully=False):
        is_currently_executing = self.execution_status.lower().startswith("executing")
        path_is_generated_in_gui = bool(self.path and self.movement_commands_detailed_str)

        if path_just_sent_successfully:
            self.gui_path_confirmed_by_arduino = True # Mark current GUI path as on Arduino

        # Test buttons
        for btn_widget in self.test_buttons.values():
            btn_widget.config(state=tk.NORMAL if self.is_connected and not is_currently_executing else tk.DISABLED)
        
        # Send Path Button:
        # Enabled if connected, path is generated in GUI, not executing, AND current GUI path is NOT yet confirmed on Arduino.
        can_send = self.is_connected and path_is_generated_in_gui and \
                   not is_currently_executing and not self.gui_path_confirmed_by_arduino
        self.send_path_button.config(state=tk.NORMAL if can_send else tk.DISABLED)

        # Execute Path Button:
        # Enabled if connected, path is generated in GUI, current GUI path IS confirmed on Arduino, AND not executing.
        can_execute = self.is_connected and path_is_generated_in_gui and \
                      self.gui_path_confirmed_by_arduino and not is_currently_executing
        self.execute_path_button.config(state=tk.NORMAL if can_execute else tk.DISABLED)
        
        # Stop Button
        self.stop_button.config(state=tk.NORMAL if self.is_connected and is_currently_executing else tk.DISABLED)


    def _check_connection(self, action_name="Action", silent=False):
        if not self.is_connected or not self.serial_port or not self.serial_port.is_open:
            if not silent:
                messagebox.showwarning("Not Connected", f"Cannot perform '{action_name}'. Please connect to Arduino.")
            return False
        return True

    def _refresh_ports(self):
        ports = [p.device for p in serial.tools.list_ports.comports()]
        self.port_combo['values'] = ports
        if ports:
            current_selection = self.port_var.get()
            if current_selection in ports:
                self.port_combo.set(current_selection)
            else:
                self.port_combo.current(0)
        else:
            self.port_var.set("")

    def _export_path(self):
        if not self.path: messagebox.showwarning("No Path", "Solve maze first."); return
        fp = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")])
        if not fp: return
        try:
            with open(fp, 'w') as f:
                f.write(f"Path ({len(self.path)-1} moves):\n")
                for r,c in self.path: f.write(f"({r},{c})\n")
                f.write(f"\nSimple Commands ({len(self.movement_commands)}):\n{self.movement_commands}\n")
                f.write(f"\nDetailed Commands for Arduino ({self.movement_commands_detailed_str.count(';')} segments):\n{self.movement_commands_detailed_str}\n")
            self.status.set("Path exported.")
        except Exception as e: messagebox.showerror("Export Error", str(e)); self._log(f"ERR: Export path: {e}")

    def _save_maze(self):
        fp = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if not fp: return
        data = {'R': self.R, 'C': self.C, 'hw': self.hw, 'vw': self.vw,
                'start': self.start, 'end': self.end, 'car_location': self.car_location}
        try:
            with open(fp, 'w') as f: json.dump(data, f, indent=2)
            self.status.set("Maze saved.")
        except Exception as e: messagebox.showerror("Save Error", str(e)); self._log(f"ERR: Save maze: {e}")

    def _load_maze(self):
        fp = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if not fp: return
        try:
            with open(fp, 'r') as f: data = json.load(f)
            
            old_R, old_C = self.R, self.C
            self.R = data['R']; self.C = data['C']
            self.hw = data['hw']; self.vw = data['vw']
            self.start = tuple(data['start']) if data.get('start') else None
            self.end = tuple(data['end']) if data.get('end') else None
            self.car_location = tuple(data['car_location']) if data.get('car_location') else self.start

            self.path = []
            self.movement_commands = ""
            self.movement_commands_detailed_str = ""
            self.gui_path_confirmed_by_arduino = False # Reset flag

            if self.R != old_R or self.C != old_C or not (hasattr(self, 'canvas') and self.canvas.winfo_exists()):
                canvas_size = 500
                self.SW = canvas_size // max(self.C, self.R, 1)
                self.canvas_width = self.C * self.SW
                self.canvas_height = self.R * self.SW
                if hasattr(self, 'canvas') and self.canvas.winfo_exists():
                    self.canvas.config(width=self.canvas_width, height=self.canvas_height)
                else:
                    self._build_ui() 
            
            self.status.set("Maze loaded.")
            self._draw()
            self._update_button_states()
        except Exception as e: messagebox.showerror("Load Error", str(e)); self._log(f"ERR: Load maze: {e}")

    def _export_image(self):
        fp = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG images", "*.png")])
        if not fp: return
        try:
            ps_data = self.canvas.postscript(colormode='color')
            img = Image.open(io.BytesIO(ps_data.encode('utf-8')))
            img.save(fp)
            self.status.set("Image saved.")
        except Exception as e: messagebox.showerror("Image Save Error", str(e)); self._log(f"ERR: Export image: {e}")

    def _log(self, message):
        if not hasattr(self, 'log_text') or not self.log_text.winfo_exists(): return
        timestamp = time.strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        def append_log():
            self.log_text.insert(tk.END, log_entry)
            self.log_text.see(tk.END)
            if float(self.log_text.index('end-1c')) > 500.0:
                 self.log_text.delete('1.0', '2.0')
        if self.master.winfo_exists():
             self.master.after(0, append_log)

    def _on_closing(self):
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            self.stop_monitor_thread.set()
            if self.is_connected and self.serial_port and self.serial_port.is_open:
                try:
                    if self.execution_status.lower().startswith("executing"):
                        self.serial_port.write(b"STOP\n")
                        self._log("Sent STOP on quit while executing.")
                        time.sleep(0.1)
                except Exception as e:
                    self._log(f"Exception sending STOP on quit: {e}")
            
            if self.monitor_thread and self.monitor_thread.is_alive():
                self.monitor_thread.join(timeout=0.5)
            
            if self.serial_port and self.serial_port.is_open:
                try:
                    self.serial_port.close()
                    self._log("Serial port closed on quit.")
                except Exception as e:
                    self._log(f"Exception closing serial port on quit: {e}")
            
            self.master.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = MazeSolverGUI(root)
    root.mainloop()
