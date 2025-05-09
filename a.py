#!/usr/bin/env python3
import tkinter as tk
from tkinter import messagebox, StringVar, simpledialog
from collections import deque

class MazeSolverGUI:
    def __init__(self, master):
        self.master = master
        master.title("Maze Solver")
        master.geometry("900x700")

        # Ask user for maze size
        self.R = simpledialog.askinteger("Rows", "Enter number of rows:", parent=self.master, minvalue=1, maxvalue=50)
        self.C = simpledialog.askinteger("Columns", "Enter number of columns:", parent=self.master, minvalue=1, maxvalue=50)
        if not self.R or not self.C:
            messagebox.showerror("Error", "Invalid maze size. Exiting.")
            master.destroy()
            return

        self.SW = 600 // max(self.C, self.R)  # cell size to fit canvas
        # wall arrays: 1 = wall present
        self.hw = [[0] * self.C for _ in range(self.R+1)]
        self.vw = [[0] * (self.C+1) for _ in range(self.R)]
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
        self.canvas = tk.Canvas(
            self.master,
            width=self.C*self.SW,
            height=self.R*self.SW,
            bg="white"
        )
        self.canvas.pack(side=tk.LEFT, padx=10, pady=10)
        self.canvas.bind("<Button-1>", self._on_click)

        # Controls
        ctrl = tk.Frame(self.master)
        ctrl.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10)

        tk.Label(ctrl, text="Mode:").pack(anchor=tk.W)
        for val, txt in [("wall", "Toggle Walls"), ("start", "Start"), ("end", "End")]:
            tk.Radiobutton(ctrl, text=txt, variable=self.mode, value=val).pack(anchor=tk.W)

        tk.Button(ctrl, text="Solve",  command=self.solve).pack(fill=tk.X, pady=5)
        tk.Button(ctrl, text="Clear",  command=self._reset).pack(fill=tk.X, pady=5)
        tk.Button(ctrl, text="Export", command=self._export).pack(fill=tk.X, pady=5)

        # Status label
        self.status = StringVar(master=self.master, value="Click to set start/end or toggle walls")
        tk.Label(ctrl, textvariable=self.status, wraplength=150, fg="blue").pack(pady=10)

    def _draw(self, path=None):
        self.canvas.delete("all")
        # draw cells
        for r in range(self.R):
            for c in range(self.C):
                x, y = c*self.SW, r*self.SW
                fill = "white"
                if (r, c) == self.start: fill = "green"
                elif (r, c) == self.end: fill = "red"
                elif path and (r, c) in path: fill = "lightblue"
                self.canvas.create_rectangle(x, y, x+self.SW, y+self.SW,
                                             fill=fill, outline="black")
        # draw horizontal walls
        for r in range(self.R+1):
            for c in range(self.C):
                if self.hw[r][c]:
                    x1, y1 = c*self.SW, r*self.SW
                    self.canvas.create_line(x1, y1, x1+self.SW, y1, width=4)
        # draw vertical walls
        for r in range(self.R):
            for c in range(self.C+1):
                if self.vw[r][c]:
                    x1, y1 = c*self.SW, r*self.SW
                    self.canvas.create_line(x1, y1, x1, y1+self.SW, width=4)

    def _on_click(self, ev):
        c, r = ev.x // self.SW, ev.y // self.SW
        if not (0 <= r < self.R and 0 <= c < self.C): return

        mode = self.mode.get()
        if mode == "start":
            self.start = (r, c)
            self.status.set(f"Start = {self.start}")
        elif mode == "end":
            self.end = (r, c)
            self.status.set(f"End = {self.end}")
        else:  # toggle walls around cell
            # horizontal walls above/below
            self.hw[r][c]   ^= 1
            self.hw[r+1][c] ^= 1
            # vertical walls left/right
            self.vw[r][c]   ^= 1
            self.vw[r][c+1] ^= 1
            self.status.set(f"Toggled walls around {(r,c)}")

        self._draw()

    def solve(self):
        if not self.start or not self.end:
            messagebox.showwarning("Need start+end", "Please set both start and end")
            return

        prev = {self.start: None}
        dq = deque([self.start])
        while dq:
            u = dq.popleft()
            if u == self.end:
                break
            r, c = u
            for dr, dc in [(1,0),(-1,0),(0,1),(0,-1)]:
                nr, nc = r+dr, c+dc
                if 0 <= nr < self.R and 0 <= nc < self.C and (nr,nc) not in prev:
                    # check wall
                    if dr and self.hw[min(r,nr)+ (dr<0)][c]:   continue
                    if dc and self.vw[r][min(c,nc)+ (dc<0)]:   continue
                    prev[(nr,nc)] = u
                    dq.append((nr,nc))

        if self.end not in prev:
            messagebox.showinfo("No path", "Cannot reach end")
            self.status.set("No path found")
            return

        # reconstruct path
        path, cur = [], self.end
        while cur:
            path.append(cur); cur = prev[cur]
        path.reverse()

        self._draw(path)
        self.status.set(f"Path found ({len(path)} steps)")

    def _reset(self):
        self.hw = [[0] * self.C for _ in range(self.R+1)]
        self.vw = [[0] * (self.C+1) for _ in range(self.R)]
        self._set_border_walls()
        self.start = self.end = None
        self.status.set("Cleared")
        self._draw()

    def _export(self):
        if not self.start or not self.end:
            messagebox.showwarning("Nothing to export", "Solve the maze first")
            return

        # re-run BFS to rebuild path
        prev = {self.start: None}
        dq = deque([self.start])
        while dq:
            u = dq.popleft()
            if u == self.end:
                break
            r, c = u
            for dr, dc in [(1,0),(-1,0),(0,1),(0,-1)]:
                nr, nc = r+dr, c+dc
                if 0 <= nr < self.R and 0 <= nc < self.C and (nr,nc) not in prev:
                    if dr and self.hw[min(r,nr)+ (dr<0)][c]:   continue
                    if dc and self.vw[r][min(c<nc)+ (dc<0)]:   continue
                    prev[(nr,nc)] = u
                    dq.append((nr,nc))

        if self.end not in prev:
            messagebox.showinfo("No path", "Nothing to export")
            return

        path, cur = [], self.end
        while cur:
            path.append(cur); cur = prev[cur]
        path.reverse()

        with open("maze_solution.txt", "w") as f:
            for i, cell in enumerate(path, 1):
                f.write(f"Step {i}: {cell}\n")

        messagebox.showinfo("Exported", "Saved maze_solution.txt")

if __name__ == "__main__":
    root = tk.Tk()
    app = MazeSolverGUI(root)
    root.mainloop()
