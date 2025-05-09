#!/usr/bin/env python3
import tkinter as tk
from tkinter import messagebox, StringVar, simpledialog, filedialog, ttk
from collections import deque
import io
import numpy as np
from PIL import Image, ImageTk, ImageOps, ImageFilter

class MazeSolverGUI:
    def __init__(self, master):
        self.master = master
        master.title("Maze Solver")
        master.geometry("1200x700")
        
        self.image_source = None
        self.processed_image = None
        
        # Default maze dimensions
        self.R = 20
        self.C = 20
        
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
        
        self.threshold_var = tk.IntVar(value=128)
        self.edge_sensitivity = tk.IntVar(value=50)

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
        
        # Image preview frame
        self.preview_frame = tk.Frame(left_frame)
        self.preview_frame.pack(fill=tk.X, pady=10)
        
        self.preview_canvas = tk.Canvas(self.preview_frame, width=300, height=200, bg="lightgray")
        self.preview_canvas.pack(side=tk.LEFT, padx=5)
        
        preview_controls = tk.Frame(self.preview_frame)
        preview_controls.pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        tk.Label(preview_controls, text="Threshold:").pack(anchor=tk.W)
        tk.Scale(preview_controls, from_=0, to=255, orient=tk.HORIZONTAL, 
                 variable=self.threshold_var, command=self._update_preview).pack(fill=tk.X)
        
        tk.Label(preview_controls, text="Edge Sensitivity:").pack(anchor=tk.W)
        tk.Scale(preview_controls, from_=0, to=100, orient=tk.HORIZONTAL, 
                variable=self.edge_sensitivity, command=self._update_preview).pack(fill=tk.X)
        
        # Controls frame
        ctrl = tk.Frame(main_frame)
        ctrl.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10)

        # Image section
        image_frame = tk.LabelFrame(ctrl, text="Image to Maze", padx=5, pady=5)
        image_frame.pack(fill=tk.X, pady=10)
        
        tk.Button(image_frame, text="Load Image", command=self._load_image).pack(fill=tk.X, pady=2)
        tk.Button(image_frame, text="Take Photo", command=self._take_photo).pack(fill=tk.X, pady=2)
        tk.Button(image_frame, text="Convert to Maze", command=self._convert_to_maze).pack(fill=tk.X, pady=2)
        
        # Maze size section
        size_frame = tk.LabelFrame(ctrl, text="Maze Size", padx=5, pady=5)
        size_frame.pack(fill=tk.X, pady=10)
        
        tk.Label(size_frame, text="Rows:").grid(row=0, column=0, sticky=tk.W)
        self.rows_var = tk.StringVar(value=str(self.R))
        tk.Entry(size_frame, textvariable=self.rows_var, width=5).grid(row=0, column=1, padx=5, pady=2)
        
        tk.Label(size_frame, text="Columns:").grid(row=1, column=0, sticky=tk.W)
        self.cols_var = tk.StringVar(value=str(self.C))
        tk.Entry(size_frame, textvariable=self.cols_var, width=5).grid(row=1, column=1, padx=5, pady=2)
        
        tk.Button(size_frame, text="Apply Size", command=self._apply_size).pack(fill=tk.X, pady=5)
        
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

        # Status bar
        self.status = StringVar(master=self.master, value="Click to set start/end or toggle walls")
        status_bar = tk.Label(self.master, textvariable=self.status, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def _apply_size(self):
        try:
            new_r = int(self.rows_var.get())
            new_c = int(self.cols_var.get())
            
            if new_r < 5 or new_c < 5 or new_r > 100 or new_c > 100:
                messagebox.showwarning("Invalid Size", "Please enter rows and columns between 5 and 100")
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
            self.status.set(f"Maze size changed to {self.R}x{self.C}")
            self._draw()
            
        except ValueError:
            messagebox.showwarning("Invalid Input", "Please enter valid numbers for rows and columns")

    def _load_image(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp *.gif"), ("All files", "*.*")]
        )
        if not file_path:
            return
            
        try:
            self.image_source = Image.open(file_path)
            self.status.set(f"Image loaded: {file_path}")
            self._update_preview()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open image: {str(e)}")

    def _take_photo(self):
        try:
            # This would normally use a camera library
            # For now, we'll simulate with a file dialog
            messagebox.showinfo("Camera Simulation", 
                                "Since we can't access your camera directly in this implementation, "
                                "please select an image file that will act as if it came from your camera.")
            self._load_image()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to take photo: {str(e)}")

    def _update_preview(self, *args):
        if not self.image_source:
            return
            
        # Process the image based on current settings
        img = self.image_source.copy()
        
        # Resize for preview
        preview_width = 300
        ratio = preview_width / img.width
        preview_height = int(img.height * ratio)
        img = img.resize((preview_width, preview_height), Image.LANCZOS)
        
        # Process based on current settings
        if self.edge_sensitivity.get() > 0:
            # Edge detection
            img = img.convert("L")
            img = img.filter(ImageFilter.FIND_EDGES)
            img = img.point(lambda x: 255 if x > self.edge_sensitivity.get() else 0)
        else:
            # Simple threshold
            img = img.convert("L")
            img = img.point(lambda x: 255 if x > self.threshold_var.get() else 0)
        
        self.processed_image = img
        
        # Display the preview
        img_tk = ImageTk.PhotoImage(img)
        self.preview_canvas.config(width=img.width, height=img.height)
        self.preview_canvas.create_image(0, 0, anchor=tk.NW, image=img_tk)
        self.preview_canvas.image = img_tk  # Keep a reference

    def _convert_to_maze(self):
        if not self.processed_image:
            messagebox.showwarning("No Image", "Please load an image first")
            return
            
        # Resize the processed image to match our maze dimensions
        img = self.processed_image.resize((self.C, self.R), Image.LANCZOS)
        img_data = np.array(img)
        
        # Reset walls
        self.hw = [[0] * self.C for _ in range(self.R + 1)]
        self.vw = [[0] * (self.C + 1) for _ in range(self.R)]
        
        # Set horizontal walls
        for r in range(self.R + 1):
            for c in range(self.C):
                # Check pixels above and below the wall
                r_above = max(0, min(r-1, self.R-1))
                r_below = min(r, self.R-1)
                
                # If there's a significant difference, set a wall
                if r == 0 or r == self.R or abs(int(img_data[r_above, c]) - int(img_data[r_below, c])) > 127:
                    self.hw[r][c] = 1
        
        # Set vertical walls
        for r in range(self.R):
            for c in range(self.C + 1):
                # Check pixels to left and right of the wall
                c_left = max(0, min(c-1, self.C-1))
                c_right = min(c, self.C-1)
                
                # If there's a significant difference, set a wall
                if c == 0 or c == self.C or abs(int(img_data[r, c_left]) - int(img_data[r, c_right])) > 127:
                    self.vw[r][c] = 1
        
        # Ensure border walls
        self._set_border_walls()
        
        # Clear start and end points
        self.start = self.end = None
        
        self.status.set("Image converted to maze")
        self._draw()

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
                setattr(self, mode, (r,c))
                self.status.set(f"{mode.capitalize()} = {(r,c)}")
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
        self.status.set("Cleared")
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
                                           filetypes=[('PNG','*.png'), ('JPEG','*.jpg')])
        if not file: return
        
        # Get postscript from canvas
        ps = self.canvas.postscript(colormode='color')
        # Convert using PIL
        img = Image.open(io.BytesIO(ps.encode('utf-8')))
        img.save(file)
        messagebox.showinfo("Image Saved", f"Maze image saved to {file}")

if __name__ == "__main__":
    root = tk.Tk()
    app = MazeSolverGUI(root)
    root.mainloop()
