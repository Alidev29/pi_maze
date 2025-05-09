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
    def __init__(self, master):  # <-- Corrected here
        self.master = master
        self.master.title("Maze Solver")
        self.master.geometry("900x650")

        # Maze dimensions
        self.rows = 6
        self.cols = 4

        # Maze data - Matrix to store wall information
        self.horizontal_walls = np.zeros((self.rows+1, self.cols), dtype=int)
        self.vertical_walls = np.zeros((self.rows, self.cols+1), dtype=int)

        # Set outer boundary walls
        for c in range(self.cols):
            self.horizontal_walls[0][c] = 1
            self.horizontal_walls[self.rows][c] = 1
        for r in range(self.rows):
            self.vertical_walls[r][0] = 1
            self.vertical_walls[r][self.cols] = 1

        self.start_pos = None
        self.end_pos = None
        self.solution_path = []
        self.drawing_wall = False
        self.wall_start = None

        self.create_widgets()

    # --- (rest of the class methods stay the same, as in your original code) ---

    # Place all other methods here as in your original post:
    # create_widgets, draw_grid, canvas_click, canvas_drag, canvas_release,
    # clear_maze, can_move, solve_maze, bfs_solve, display_solution

    # We'll complete the export_solution() function here:
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

                dir_to_cmd = {
                    "UP": "f",
                    "DOWN": "b",
                    "LEFT": "l",
                    "RIGHT": "r"
                }

                current_direction = "UP"
                f.write("\nArduino Commands:\n")
                cmd_sequence = []

                for direction in instructions:
                    if current_direction == "UP":
                        if direction == "UP":
                            cmd_sequence.append("f")
                        elif direction == "DOWN":
                            cmd_sequence.extend(["r", "r", "f"])
                        elif direction == "LEFT":
                            cmd_sequence.extend(["l", "f"])
                        elif direction == "RIGHT":
                            cmd_sequence.extend(["r", "f"])

                    elif current_direction == "DOWN":
                        if direction == "UP":
                            cmd_sequence.extend(["r", "r", "f"])
                        elif direction == "DOWN":
                            cmd_sequence.append("f")
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
                            cmd_sequence.append("f")
                        elif direction == "RIGHT":
                            cmd_sequence.extend(["r", "r", "f"])

                    elif current_direction == "RIGHT":
                        if direction == "UP":
                            cmd_sequence.extend(["l", "f"])
                        elif direction == "DOWN":
                            cmd_sequence.extend(["r", "f"])
                        elif direction == "LEFT":
                            cmd_sequence.extend(["r", "r", "f"])
                        elif direction == "RIGHT":
                            cmd_sequence.append("f")

                    current_direction = direction

                f.write("// Arduino commands with sensor integration\n")
                f.write("// Commands: " + " ".join(cmd_sequence) + " s\n\n")

                f.write("/* Arduino implementation:\n")
                f.write("For IR sensors: Follow line/path detection\n")
                f.write("For Ultrasonic sensors: Wall detection and avoidance\n")
                f.write("Command sequence sent via Serial or executed in loop\n")
                f.write("*/\n")

            messagebox.showinfo("Exported", "Solution exported to maze_solution.txt")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to export: {e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = MazeSolverGUI(root)
    root.mainloop()
