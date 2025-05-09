#!/usr/bin/env python3
"""
# bdddgghdghdgd
Maze Solver GUI Application for Raspberry Pi
- Design 6x4 maze
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
        self.master.geometry("800x600")
        
        # Maze dimensions
        self.rows = 6
        self.cols = 4
        
        # Maze data (0 = path, 1 = wall)
        self.maze = np.zeros((self.rows, self.cols), dtype=int)
        
        # Start and end coordinates
        self.start_pos = None
        self.end_pos = None
        
        # Maze solution
        self.solution_path = []
        
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
        
        # Frame for maze grid
        self.grid_frame = tk.Frame(left_frame)
        self.grid_frame.pack(padx=20, pady=20, fill=tk.BOTH, expand=True)
        
        # Create maze grid
        self.cell_buttons = []
        for row in range(self.rows):
            button_row = []
            for col in range(self.cols):
                cell = tk.Button(self.grid_frame, width=6, height=3, bg="white",
                                command=lambda r=row, c=col: self.toggle_cell(r, c))
                cell.grid(row=row, column=col, padx=2, pady=2)
                button_row.append(cell)
            self.cell_buttons.append(button_row)
        
        # Status label
        status_frame = tk.Frame(left_frame)
        status_frame.pack(fill=tk.X, padx=5, pady=5)
        self.status_var = StringVar()
        self.status_var.set("Select start and end points, then create walls by clicking cells")
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
    
    def toggle_cell(self, row, col):
        mode = self.mode_var.get()
        
        if mode == "wall":
            if (row, col) != self.start_pos and (row, col) != self.end_pos:
                # Toggle wall/path
                if self.maze[row, col] == 0:
                    self.maze[row, col] = 1  # Set as wall
                    self.cell_buttons[row][col].config(bg="black")
                else:
                    self.maze[row, col] = 0  # Set as path
                    self.cell_buttons[row][col].config(bg="white")
                    
        elif mode == "start":
            # Remove previous start point
            if self.start_pos:
                prev_row, prev_col = self.start_pos
                if self.maze[prev_row, prev_col] == 0:
                    self.cell_buttons[prev_row][prev_col].config(bg="white")
            
            # Set new start point if it's not a wall or end point
            if self.maze[row, col] == 0 and (row, col) != self.end_pos:
                self.start_pos = (row, col)
                self.cell_buttons[row][col].config(bg="green")
                self.status_var.set(f"Start point set at ({row}, {col})")
            
        elif mode == "end":
            # Remove previous end point
            if self.end_pos:
                prev_row, prev_col = self.end_pos
                if self.maze[prev_row, prev_col] == 0:
                    self.cell_buttons[prev_row][prev_col].config(bg="white")
            
            # Set new end point if it's not a wall or start point
            if self.maze[row, col] == 0 and (row, col) != self.start_pos:
                self.end_pos = (row, col)
                self.cell_buttons[row][col].config(bg="red")
                self.status_var.set(f"End point set at ({row}, {col})")
    
    def clear_maze(self):
        # Reset maze data
        self.maze = np.zeros((self.rows, self.cols), dtype=int)
        self.start_pos = None
        self.end_pos = None
        self.solution_path = []
        
        # Reset button colors
        for row in range(self.rows):
            for col in range(self.cols):
                self.cell_buttons[row][col].config(bg="white")
        
        # Clear solution text
        self.solution_text.delete(1.0, tk.END)
        self.status_var.set("Maze cleared")
    
    def solve_maze(self):
        if not self.start_pos or not self.end_pos:
            messagebox.showwarning("Warning", "Please set start and end points first")
            return
        
        # Reset previous solution
        self.reset_path_display()
        
        # Solve using BFS algorithm
        self.solution_path = self.bfs_solve()
        
        if not self.solution_path:
            messagebox.showinfo("No Solution", "No path exists between start and end points")
            return
        
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
            curr_row, curr_col = q.pop(0)  # Dequeue
            
            # Check if we reached the end
            if (curr_row, curr_col) == self.end_pos:
                # Reconstruct the path
                path = []
                instructions = []
                pos = (curr_row, curr_col)
                
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
                new_row, new_col = curr_row + dr, curr_col + dc
                
                # Check if the new position is valid
                if (0 <= new_row < self.rows and 
                    0 <= new_col < self.cols and 
                    not visited[new_row, new_col] and 
                    self.maze[new_row, new_col] == 0):
                    
                    q.append((new_row, new_col))
                    visited[new_row, new_col] = True
                    prev[(new_row, new_col)] = (curr_row, curr_col)
                    moves[(new_row, new_col)] = i
        
        # No path found
        return None
    
    def reset_path_display(self):
        # Reset cell colors except walls, start and end
        for row in range(self.rows):
            for col in range(self.cols):
                if self.maze[row, col] == 1:
                    self.cell_buttons[row][col].config(bg="black")  # Wall
                elif (row, col) == self.start_pos:
                    self.cell_buttons[row][col].config(bg="green")  # Start
                elif (row, col) == self.end_pos:
                    self.cell_buttons[row][col].config(bg="red")    # End
                else:
                    self.cell_buttons[row][col].config(bg="white")  # Path
        
        # Clear solution text
        self.solution_text.delete(1.0, tk.END)
    
    def display_solution(self):
        if not self.solution_path:
            return
        
        path, instructions = self.solution_path
        
        # Color the path on the grid
        for row, col in path:
            if (row, col) != self.start_pos and (row, col) != self.end_pos:
                self.cell_buttons[row][col].config(bg="light blue")
        
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
                
                for direction in instructions:
                    # Calculate required turns based on current facing direction
                    if current_direction == "UP":
                        if direction == "UP":
                            f.write("f ")  # No turn needed
                        elif direction == "DOWN":
                            f.write("r r f ")  # 180° turn
                        elif direction == "LEFT":
                            f.write("l f ")
                        elif direction == "RIGHT":
                            f.write("r f ")
                            
                    elif current_direction == "DOWN":
                        if direction == "UP":
                            f.write("r r f ")  # 180° turn
                        elif direction == "DOWN":
                            f.write("f ")  # No turn needed
                        elif direction == "LEFT":
                            f.write("r f ")
                        elif direction == "RIGHT":
                            f.write("l f ")
                            
                    elif current_direction == "LEFT":
                        if direction == "UP":
                            f.write("r f ")
                        elif direction == "DOWN":
                            f.write("l f ")
                        elif direction == "LEFT":
                            f.write("f ")  # No turn needed
                        elif direction == "RIGHT":
                            f.write("r r f ")  # 180° turn
                            
                    elif current_direction == "RIGHT":
                        if direction == "UP":
                            f.write("l f ")
                        elif direction == "DOWN":
                            f.write("r f ")
                        elif direction == "LEFT":
                            f.write("r r f ")  # 180° turn
                        elif direction == "RIGHT":
                            f.write("f ")  # No turn needed
                    
                    # Update current direction
                    current_direction = direction
                
                f.write("s")  # Final stop
            
            messagebox.showinfo("Export Successful", "Solution exported to maze_solution.txt")
            self.status_var.set("Solution exported to file")
            
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export solution: {str(e)}")

def main():
    root = tk.Tk()
    app = MazeSolverGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
