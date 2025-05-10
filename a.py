#!/usr/bin/env python3
import tkinter as tk
from tkinter import messagebox, StringVar, filedialog
from collections import deque
import io

class MazeSolverGUI:
    def __init__(self, master):
        self.master = master
        master.title("Maze Solver")
        master.geometry("900x700")
        
        # Default maze dimensions
        self.R = 10
        self.C = 10
        
        # Compute canvas and cell size
        canvas_size = 600
        self.SW = canvas_size // max(self.C, self.R)
        self.canvas_width = self.C * self.SW
        self.canvas_height = self.R * self.SW

        # Wall arrays (1=wall)
        self.hw = [[0] * self.C for _ in range(self.R + 1)]
        self.vw = [[0] * (self.C + 1) for _ in range(self.R)]
        self._set_border_walls()

        self.start = self.end = None
        self.mode = StringVar(master=self.master, value="wall")

        self._build_ui()
        self._draw()

    def _set_border_walls(self):
        for c in range(self.C):
            self.hw[0][c] = self.hw[self.R][c] = 1
        for r in range(self.R):
            self.vw[r][0] = self.vw[r][self.C] = 1

    def _build_ui(self):
        # Main layout frames
        main_frame = tk.Frame(self.master)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        left_frame = tk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Canvas for maze
        canvas_frame = tk.Frame(left_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(canvas_frame, width=self.canvas_width, height=self.canvas_height, bg="white")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Button-1>", self._on_click)
        
        # Controls frame
        ctrl = tk.Frame(main_frame)
        ctrl.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10)

        # Text file section
        txt_frame = tk.LabelFrame(ctrl, text="Text File Import", padx=5, pady=5)
        txt_frame.pack(fill=tk.X, pady=10)
        
        tk.Button(txt_frame, text="Load Text Maze", command=self._load_text_maze).pack(fill=tk.X, pady=2)
        
        # Example section
        example_frame = tk.LabelFrame(ctrl, text="Text Format Example", padx=5, pady=5)
        example_frame.pack(fill=tk.X, pady=10)
        
        example_text = (
            "Example format:\n"
            "###########\n"
            "#   #     #\n"
            "# # # ### #\n"
            "# #   #   #\n"
            "# ##### # #\n"
            "#     # # #\n"
            "##### # # #\n"
            "#   # # # #\n"
            "# # ### # #\n"
            "#S#     #E#\n"
            "###########\n"
            "Where:\n"
            "# = Wall\n"
            "  = Path\n"
            "S = Start\n"
            "E = End"
        )
        tk.Label(example_frame, text=example_text, justify=tk.LEFT).pack(anchor=tk.W)
        
        # Maze size section
        size_frame = tk.LabelFrame(ctrl, text="Maze Size", padx=5, pady=5)
        size_frame.pack(fill=tk.X, pady=10)
        
        tk.Label(size_frame, text="Rows:").grid(row=0, column=0, sticky=tk.W)
        self.rows_var = tk.StringVar(value=str(self.R))
        tk.Entry(size_frame, textvariable=self.rows_var, width=5).grid(row=0, column=1, padx=5, pady=2)
        
        tk.Label(size_frame, text="Columns:").grid(row=1, column=0, sticky=tk.W)
        self.cols_var = tk.StringVar(value=str(self.C))
        tk.Entry(size_frame, textvariable=self.cols_var, width=5).grid(row=1, column=1, padx=5, pady=2)
        
        tk.Button(size_frame, text="Apply Size", command=self._apply_size).grid(row=2, column=0, columnspan=2, pady=5, sticky=tk.EW)
        
        # Mode section
        mode_frame = tk.LabelFrame(ctrl, text="Edit Mode", padx=5, pady=5)
        mode_frame.pack(fill=tk.X, pady=10)
        
        for val, txt in [("wall", "Toggle Walls"), ("start", "Start Point"), ("end", "End Point")]:
            tk.Radiobutton(mode_frame, text=txt, variable=self.mode, value=val).pack(anchor=tk.W)

        # Actions section
        action_frame = tk.LabelFrame(ctrl, text="Actions", padx=5, pady=5)
        action_frame.pack(fill=tk.X, pady=10)
        
        tk.Button(action_frame, text="Solve Maze", command=self.solve).pack(fill=tk.X, pady=2)
        tk.Button(action_frame, text="Clear Maze", command=self._reset).pack(fill=tk.X, pady=2)
        tk.Button(action_frame, text="Export Path", command=self._export_path).pack(fill=tk.X, pady=2)
        tk.Button(action_frame, text="Save Image", command=self._export_image).pack(fill=tk.X, pady=2)
        tk.Button(action_frame, text="Save As Text", command=self._save_as_text).pack(fill=tk.X, pady=2)

        # Status bar
        self.status = StringVar(master=self.master, value="Ready")
        status_bar = tk.Label(self.master, textvariable=self.status, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def _load_text_maze(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if not file_path:
            return
            
        try:
            # Read the file
            with open(file_path, 'r') as f:
                lines = [line.rstrip() for line in f.readlines()]
            
            # Filter out empty lines
            lines = [line for line in lines if line]
            
            if not lines:
                messagebox.showerror("Error", "File is empty")
                return
                
            # Calculate maze dimensions
            height = len(lines)
            width = max(len(line) for line in lines)
            
            # Resize the maze
            self.R = height - 2  # Subtract borders
            self.C = width - 2   # Subtract borders
            
            if self.R < 1 or self.C < 1:
                messagebox.showerror("Error", "Invalid maze dimensions")
                return
                
            # Update UI values
            self.rows_var.set(str(self.R))
            self.cols_var.set(str(self.C))
            
            # Reinitialize maze walls
            self.hw = [[0] * self.C for _ in range(self.R + 1)]
            self.vw = [[0] * (self.C + 1) for _ in range(self.R)]
            self.start = self.end = None
            
            # Set borders
            self._set_border_walls()
            
            # Parse the text maze
            for r in range(height):
                line = lines[r].ljust(width)  # Pad line to full width
                for c in range(width):
                    if c >= len(line):
                        continue
                        
                    ch = line[c]
                    
                    if r == 0 or r == height-1 or c == 0 or c == width-1:
                        # Borders should be walls
                        continue
                        
                    # Adjust coordinates for internal grid
                    maze_r = r - 1
                    maze_c = c - 1
                    
                    if ch == '#':
                        # Add walls around this cell
                        self.hw[maze_r][maze_c] = 1      # Top wall
                        self.hw[maze_r+1][maze_c] = 1    # Bottom wall
                        self.vw[maze_r][maze_c] = 1      # Left wall
                        self.vw[maze_r][maze_c+1] = 1    # Right wall
                    elif ch == 'S' or ch == 's':
                        self.start = (maze_r, maze_c)
                    elif ch == 'E' or ch == 'e':
                        self.end = (maze_r, maze_c)
            
            # Connect adjacent empty spaces by removing shared walls
            for r in range(self.R):
                for c in range(self.C):
                    r_txt = r + 1  # Adjust back to text coordinates
                    c_txt = c + 1
                    
                    curr_ch = '#' if r_txt >= len(lines) or c_txt >= len(lines[r_txt]) else lines[r_txt][c_txt]
                    
                    if curr_ch != '#':
                        # Check right neighbor
                        if c+1 < self.C:
                            right_ch = '#' if r_txt >= len(lines) or c_txt+1 >= len(lines[r_txt]) else lines[r_txt][c_txt+1]
                            if right_ch != '#':
                                self.vw[r][c+1] = 0  # Remove wall between them
                        
                        # Check bottom neighbor
                        if r+1 < self.R:
                            bottom_ch = '#' if r_txt+1 >= len(lines) or c_txt >= len(lines[r_txt+1]) else lines[r_txt+1][c_txt]
                            if bottom_ch != '#':
                                self.hw[r+1][c] = 0  # Remove wall between them
            
            # Recalculate canvas size
            canvas_size = 600
            self.SW = canvas_size // max(self.C, self.R)
            self.canvas_width = self.C * self.SW
            self.canvas_height = self.R * self.SW
            
            # Update canvas size
            self.canvas.config(width=self.canvas_width, height=self.canvas_height)
            
            self.status.set(f"Loaded maze from {file_path}")
            self._draw()
            
        except Exception as e:
            print(f"Error loading maze: {str(e)}")
            messagebox.showerror("Error", f"Failed to load maze: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def _save_as_text(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension='.txt',
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if not file_path:
            return
            
        try:
            # Create a 2D grid representation of the maze
            # Use '#' for walls, ' ' for paths, 'S' for start, 'E' for end
            grid = [[' ' for _ in range(self.C+2)] for _ in range(self.R+2)]
            
            # Set borders
            for r in range(self.R+2):
                grid[r][0] = grid[r][self.C+1] = '#'
            for c in range(self.C+2):
                grid[0][c] = grid[self.R+1][c] = '#'
            
            # Mark walls in the grid
            for r in range(self.R):
                for c in range(self.C):
                    has_wall = False
                    
                    # Check walls around this cell
                    if self.hw[r][c] == 1 and self.hw[r+1][c] == 1 and \
                       self.vw[r][c] == 1 and self.vw[r][c+1] == 1:
                        grid[r+1][c+1] = '#'  # Cell is completely walled
                        has_wall = True
                    
                    # If this cell has start or end point, mark it
                    if (r, c) == self.start:
                        grid[r+1][c+1] = 'S'
                    elif (r, c) == self.end:
                        grid[r+1][c+1] = 'E'
            
            # Write to file
            with open(file_path, 'w') as f:
                for row in grid:
                    f.write(''.join(row) + '\n')
            
            self.status.set(f"Maze saved as text to {file_path}")
            
        except Exception as e:
            print(f"Error saving maze: {str(e)}")
            messagebox.showerror("Error", f"Failed to save maze: {str(e)}")
    
    def _apply_size(self):
        try:
            new_r = int(self.rows_var.get())
            new_c = int(self.cols_var.get())
            
            if new_r < 4 or new_c < 4 or new_r > 100 or new_c > 100:
                messagebox.showwarning("Invalid Size", "Please enter rows and columns between 4 and 100")
                return
                
            self.R = new_r
            self.C = new_c
            
            # Recalculate cell size
            canvas_size = 600
            self.SW = canvas_size // max(self.C, self.R)
            self.canvas_width = self.C * self.SW
            self.canvas_height = self.R * self.SW
            
            # Reset maze
            self.hw = [[0] * self.C for _ in range(self.R + 1)]
            self.vw = [[0] * (self.C + 1) for _ in range(self.R)]
            self._set_border_walls()
            
            self.start = self.end = None
            
            # Update canvas size
            self.canvas.config(width=self.canvas_width, height=self.canvas_height)
            
            self.status.set(f"Maze size changed to {self.R}x{self.C}")
            self._draw()
            
        except ValueError:
            messagebox.showwarning("Invalid Input", "Please enter valid numbers for rows and columns")

    def _draw(self, path=None):
        self.canvas.delete("all")
        # Cells
        for r in range(self.R):
            for c in range(self.C):
                x, y = c*self.SW, r*self.SW
                fill = "white"
                if (r,c) == self.start: fill = "green"
                elif (r,c) == self.end: fill = "red"
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
                setattr(self, mode, (r, c))
                self.status.set(f"{mode.capitalize()} = {(r, c)}")
            self._draw()
            return

        # Toggle specific wall edges
        cell_x = x - c*self.SW
        cell_y = y - r*self.SW
        th = 6
        if 0 <= r <= self.R and 0 <= c < self.C and abs(cell_y) <= th:
            self.hw[r][c] ^= 1
            self.status.set(f"Toggled horizontal wall at row {r}, column {c}")
        elif 0 <= r < self.R and 0 <= c < self.C and abs(cell_y-self.SW) <= th:
            self.hw[r+1][c] ^= 1
            self.status.set(f"Toggled horizontal wall at row {r+1}, column {c}")
        elif 0 <= r < self.R and 0 <= c <= self.C and abs(cell_x) <= th:
            self.vw[r][c] ^= 1
            self.status.set(f"Toggled vertical wall at row {r}, column {c}")
        elif 0 <= r < self.R and 0 <= c < self.C and abs(cell_x-self.SW) <= th:
            self.vw[r][c+1] ^= 1
            self.status.set(f"Toggled vertical wall at row {r}, column {c+1}")
        self._draw()

    def can_move(self, r, c, dr, dc):
        if dr == 1: return self.hw[r+1][c] == 0
        if dr == -1: return self.hw[r][c] == 0
        if dc == 1: return self.vw[r][c+1] == 0
        if dc == -1: return self.vw[r][c] == 0
        return False

    def solve(self):
        if not self.start or not self.end:
            messagebox.showwarning("Need start+end", "Please set both start and end points")
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
        self._draw(path)
        self.status.set(f"Path found ({len(path)} steps)")

    def _reset(self):
        self.hw = [[0]*self.C for _ in range(self.R+1)]
        self.vw = [[0]*(self.C+1) for _ in range(self.R)]
        self._set_border_walls()
        self.start = self.end = None
        self.status.set("Maze cleared")
        self._draw()

    def _export_path(self):
        if not self.start or not self.end:
            messagebox.showwarning("Nothing to export", "Solve the maze first")
            return
        # Reuse solve BFS to get path
        prev = {self.start: None}; dq = deque([self.start])
        while dq:
            r, c = dq.popleft()
            if (r,c) == self.end: break
            for dr, dc in [(1,0),(-1,0),(0,1),(0,-1)]:
                nr, nc = r+dr, c+dc
                if 0<=nr<self.R and 0<=nc<self.C and (nr,nc) not in prev and self.can_move(r,c,dr,dc):
                    prev[(nr,nc)] = (r,c); dq.append((nr,nc))
        if self.end not in prev:
            messagebox.showinfo("No path", "Nothing to export")
            return
        path, cur = [], self.end
        while cur:
            path.append(cur); cur = prev[cur]
        path.reverse()
        
        file = filedialog.asksaveasfilename(defaultextension='.txt', 
                                           filetypes=[('Text file','*.txt')])
        if not file:
            return
            
        with open(file, "w") as f:
            for i, cell in enumerate(path, 1): 
                f.write(f"Step {i}: {cell}\n")
        messagebox.showinfo("Exported", f"Saved path to {file}")

    def _export_image(self):
        # Ask for filename
        file = filedialog.asksaveasfilename(defaultextension='.png', 
                                           filetypes=[('PNG','*.png'), ('PostScript','*.ps')])
        if not file: return
        
        try:
            # If it's a .ps file, just save the canvas directly
            if file.lower().endswith('.ps'):
                self.canvas.postscript(file=file)
                messagebox.showinfo("Image Saved", f"Maze image saved to {file}")
                return
            
            # For other formats, try to use PIL if available
            try:
                from PIL import Image
                # Get postscript from canvas
                ps = self.canvas.postscript(colormode='color')
                # Convert using PIL
                img = Image.open(io.BytesIO(ps.encode('utf-8')))
                img.save(file)
                messagebox.showinfo("Image Saved", f"Maze image saved to {file}")
            except ImportError:
                # If PIL is not available, save as PostScript and inform user
                ps_file = file.rsplit('.', 1)[0] + '.ps'
                self.canvas.postscript(file=ps_file)
                messagebox.showinfo("Image Saved", 
                                   f"PIL not available. Saved as PostScript to {ps_file}")
        except Exception as e:
            print(f"Error saving image: {str(e)}")
            messagebox.showerror("Error", f"Failed to save image: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = MazeSolverGUI(root)
    root.mainloop()
