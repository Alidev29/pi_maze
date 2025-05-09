#!/usr/bin/env python3
import tkinter as tk
from tkinter import messagebox, StringVar, simpledialog, filedialog
from collections import deque
import io
from PIL import Image

class MazeSolverGUI:
    def __init__(self, master):
        self.master = master
        master.title("Maze Solver")
        master.geometry("1000x700")

        # Prompt for maze dimensions
        self.R = simpledialog.askinteger("Rows", "Enter number of rows:", parent=self.master, minvalue=1, maxvalue=50)
        self.C = simpledialog.askinteger("Columns", "Enter number of columns:", parent=self.master, minvalue=1, maxvalue=50)
        if not self.R or not self.C:
            messagebox.showerror("Error", "Invalid maze size. Exiting.")
            master.destroy()
            return

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
        # Canvas
        self.canvas = tk.Canvas(self.master, width=self.canvas_width, height=self.canvas_height, bg="white")
        self.canvas.pack(side=tk.LEFT, padx=10, pady=10)
        self.canvas.bind("<Button-1>", self._on_click)

        # Controls frame
        ctrl = tk.Frame(self.master)
        ctrl.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10)

        tk.Label(ctrl, text="Mode:").pack(anchor=tk.W)
        for val, txt in [("wall", "Toggle Walls"), ("start", "Start"), ("end", "End")]:
            tk.Radiobutton(ctrl, text=txt, variable=self.mode, value=val).pack(anchor=tk.W)

        tk.Button(ctrl, text="Solve", command=self.solve).pack(fill=tk.X, pady=5)
        tk.Button(ctrl, text="Clear", command=self._reset).pack(fill=tk.X, pady=5)
        tk.Button(ctrl, text="Export Path", command=self._export_path).pack(fill=tk.X, pady=5)
        tk.Button(ctrl, text="Save Image", command=self._export_image).pack(fill=tk.X, pady=5)

        self.status = StringVar(master=self.master, value="Click to set start/end or toggle walls")
        tk.Label(ctrl, textvariable=self.status, wraplength=150, fg="blue").pack(pady=10)

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
        with open("maze_solution.txt","w") as f:
            for i,cell in enumerate(path,1): f.write(f"Step {i}: {cell}\n")
        messagebox.showinfo("Exported","Saved maze_solution.txt")

    def _export_image(self):
        # Ask for filename
        file = filedialog.asksaveasfilename(defaultextension='.png', filetypes=[('PNG','*.png')])
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
