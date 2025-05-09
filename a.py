#!/usr/bin/env python3
import tkinter as tk
from tkinter import messagebox, StringVar
from collections import deque

class MazeSolverGUI:
    def __init__(self, master):
        self.master = master
        master.title("Maze Solver")
        master.geometry("800x600")

        self.R, self.C = 6, 4
        self.SW = 80  # cell size
        # wall arrays: 1 = wall present
        self.hw = [[0]*self.C for _ in range(self.R+1)]
        self.vw = [[0]*(self.C+1) for _ in range(self.R)]
        self._set_border_walls()

        self.start = self.end = None
        self.mode = StringVar(value="wall")

        self._build_ui()
        self._draw()

    def _set_border_walls(self):
        for c in range(self.C):
            self.hw[0][c] = self.hw[self.R][c] = 1
        for r in range(self.R):
            self.vw[r][0] = self.vw[r][self.C] = 1

    def _build_ui(self):
        self.canvas = tk.Canvas(self.master,
            width=self.C*self.SW, height=self.R*self.SW, bg="white")
        self.canvas.pack(side=tk.LEFT, padx=10, pady=10)
        self.canvas.bind("<Button-1>", self._on_click)

        ctrl = tk.Frame(self.master)
        ctrl.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10)
        for val,txt in [("wall","Toggle Walls"),("start","Start"),("end","End")]:
            tk.Radiobutton(ctrl, text=txt, variable=self.mode, value=val).pack(anchor=tk.W)
        tk.Button(ctrl, text="Solve", command=self.solve).pack(fill=tk.X, pady=5)
        tk.Button(ctrl, text="Clear", command=self._reset).pack(fill=tk.X, pady=5)
        tk.Button(ctrl, text="Export", command=self._export).pack(fill=tk.X, pady=5)

        self.status = StringVar("Click to set start/end or toggle walls")
        tk.Label(ctrl, textvariable=self.status, wraplength=150, fg="blue").pack(pady=10)

    def _draw(self, path=None):
        self.canvas.delete("all")
        # cells
        for r in range(self.R):
            for c in range(self.C):
                x,y = c*self.SW, r*self.SW
                fill = "white"
                if (r,c)==self.start: fill="green"
                elif (r,c)==self.end: fill="red"
                elif path and (r,c) in path: fill="lightblue"
                self.canvas.create_rectangle(x,y,x+self.SW,y+self.SW, fill=fill, outline="black")
        # walls
        for r in range(self.R+1):
            for c in range(self.C):
                if self.hw[r][c]:
                    x1,y1 = c*self.SW, r*self.SW
                    self.canvas.create_line(x1,y1, x1+self.SW,y1, width=4)
        for r in range(self.R):
            for c in range(self.C+1):
                if self.vw[r][c]:
                    x1,y1 = c*self.SW, r*self.SW
                    self.canvas.create_line(x1,y1, x1,y1+self.SW, width=4)

    def _on_click(self, ev):
        c, r = ev.x//self.SW, ev.y//self.SW
        if not (0<=r<self.R and 0<=c<self.C): return
        if self.mode.get()=="start":
            self.start=(r,c); self.status.set(f"Start={self.start}")
        elif self.mode.get()=="end":
            self.end=(r,c); self.status.set(f"End={self.end}")
        else:
            # toggle all 4 walls around (r,c)
            for dr,dc,arr,idx in [
                (-1,0,self.hw,r), (1,0,self.hw,r+1),
                (0,-1,self.vw,r), (0,1,self.vw,r)
            ]:
                rr,cc = r+dr, c+dc
                if 0<=rr<=self.R and 0<=cc<self.C+ (1 if arr is self.vw else 0):
                    if arr is self.hw:
                        arr[idx][c] ^= 1
                    else:
                        arr[r][c+ (0 if dr else (dc>0))] ^= 1
            self.status.set(f"Toggled walls @{(r,c)}")
        self._draw()

    def solve(self):
        if not self.start or not self.end:
            messagebox.showwarning("Need start+end","Please set both")
            return
        prev = {}
        dq = deque([self.start])
        prev[self.start]=None
        while dq:
            u = dq.popleft()
            if u==self.end: break
            r,c = u
            for dr,dc in [(1,0),(-1,0),(0,1),(0,-1)]:
                nr, nc = r+dr, c+dc
                if 0<=nr<self.R and 0<=nc<self.C:
                    # check wall between u and (nr,nc)
                    if dr and self.hw[min(r,nr)+ (dr<0)][c]: continue
                    if dc and self.vw[r][min(c,nc)+ (dc<0)]: continue
                    v = (nr,nc)
                    if v not in prev:
                        prev[v]=u
                        dq.append(v)
        if self.end not in prev:
            messagebox.showinfo("No path","Cannot reach end")
            return
        # reconstruct
        path = []
        cur = self.end
        while cur:
            path.append(cur); cur = prev[cur]
        path.reverse()
        self._draw(path)
        self.status.set(f"Found path ({len(path)} steps)")

    def _reset(self):
        self.hw = [[0]*self.C for _ in range(self.R+1)]
        self.vw = [[0]*(self.C+1) for _ in range(self.R)]
        self._set_border_walls()
        self.start = self.end = None
        self.status.set("Cleared")
        self._draw()

    def _export(self):
        if not self.start or not self.end:
            messagebox.showwarning("Nothing to export","Solve first")
            return
        prev = {}
        dq = deque([self.start]); prev[self.start]=None
        while dq:
            u=dq.popleft()
            if u==self.end: break
            r,c=u
            for dr,dc in [(1,0),(-1,0),(0,1),(0,-1)]:
                nr, nc = r+dr, c+dc
                if 0<=nr<self.R and 0<=nc<self.C:
                    if dr and self.hw[min(r,nr)+ (dr<0)][c]: continue
                    if dc and self.vw[r][min(c,nc)+ (dc<0)]: continue
                    v=(nr,nc)
                    if v not in prev:
                        prev[v]=u; dq.append(v)
        if self.end not in prev:
            messagebox.showinfo("No path","Nothing to export")
            return
        # write file
        path, cur = [], self.end
        while cur:
            path.append(cur); cur=prev[cur]
        path.reverse()
        with open("maze_solution.txt","w") as f:
            for i,cell in enumerate(path,1):
                f.write(f"{i}: {cell}\n")
        messagebox.showinfo("Exported","Saved maze_solution.txt")

if __name__=="__main__":
    root = tk.Tk()
    MazeSolverGUI(root)
    root.mainloop()
