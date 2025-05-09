#!/usr/bin/env python3
"""
Improved Maze Solver GUI Application for Raspberry Pi
Uses Tkinter for UI and NetworkX for pathfinding.
"""

import tkinter as tk
from tkinter import messagebox, StringVar
import networkx as nx

class MazeSolverGUI:
    def __init__(self, master):
        self.master = master
        master.title("Maze Solver")
        master.geometry("800x600")
        
        self.rows, self.cols = 6, 4
        self.cell_w, self.cell_h = 80, 80
        
        # Graph holds adjacency of walkable cells
        self.G = nx.grid_2d_graph(self.rows, self.cols)
        self.start = self.end = None
        
        self.mode = StringVar(value="wall")
        self._build_ui()
        self._draw_grid()
    
    def _build_ui(self):
        # Canvas
        self.canvas = tk.Canvas(self.master,
                                width=self.cols*self.cell_w,
                                height=self.rows*self.cell_h,
                                bg="white")
        self.canvas.pack(side=tk.LEFT, padx=10, pady=10)
        self.canvas.bind("<Button-1>", self._on_click)
        
        # Controls
        ctrl = tk.Frame(self.master)
        ctrl.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10)
        
        tk.Label(ctrl, text="Mode:").pack(anchor=tk.W)
        for val, txt in [("wall","Toggle Wall"), ("start","Start"), ("end","End")]:
            tk.Radiobutton(ctrl, text=txt, variable=self.mode, value=val).pack(anchor=tk.W)
        
        tk.Button(ctrl, text="Solve", command=self.solve).pack(fill=tk.X, pady=5)
        tk.Button(ctrl, text="Clear", command=self._reset).pack(fill=tk.X, pady=5)
        tk.Button(ctrl, text="Export", command=self._export).pack(fill=tk.X, pady=5)
        
        self.status = StringVar(value="Click to set start/end or toggle walls")
        tk.Label(ctrl, textvariable=self.status, wraplength=150, fg="blue").pack(pady=10)
    
    def _draw_grid(self, path=None):
        self.canvas.delete("all")
        # draw cells
        for r in range(self.rows):
            for c in range(self.cols):
                x, y = c*self.cell_w, r*self.cell_h
                fill = "white"
                if (r,c) == self.start: fill="green"
                elif (r,c) == self.end: fill="red"
                elif path and (r,c) in path: fill="light blue"
                self.canvas.create_rectangle(x,y, x+self.cell_w,y+self.cell_h,
                                             fill=fill, outline="black")
        # draw removed edges as walls
        for (u,v) in set(nx.grid_2d_graph(self.rows,self.cols).edges()) - set(self.G.edges()):
            (r1,c1),(r2,c2) = u,v
            x1,y1 = (c1+0.5)*self.cell_w,(r1+0.5)*self.cell_h
            x2,y2 = (c2+0.5)*self.cell_w,(r2+0.5)*self.cell_h
            self.canvas.create_line(x1,y1, x2,y2, width=6, fill="black")
    
    def _on_click(self, ev):
        c, r = ev.x//self.cell_w, ev.y//self.cell_h
        if not (0<=r<self.rows and 0<=c<self.cols): return
        cell = (r,c)
        m = self.mode.get()
        if m == "start":
            self.start = cell
            self.status.set(f"Start set to {cell}")
        elif m == "end":
            self.end = cell
            self.status.set(f"End set to {cell}")
        else:  # toggle wall
            # find neighbor by clicking midpoint of two cells?
            # instead, toggle all incident edges to isolate cell if clicked twice?
            # Better: right‐click neighbor cell to remove individual edge—skip here
            # For simplicity, toggle connections to all four neighbors
            for dr,dc in [(1,0),(-1,0),(0,1),(0,-1)]:
                nb = (r+dr,c+dc)
                if 0<=nb[0]<self.rows and 0<=nb[1]<self.cols:
                    if self.G.has_edge(cell, nb):
                        self.G.remove_edge(cell, nb)
                    else:
                        self.G.add_edge(cell, nb)
            self.status.set(f"Toggled walls around {cell}")
        self._draw_grid()
    
    def solve(self):
        if not self.start or not self.end:
            messagebox.showwarning("Need start/end","Set both start and end first")
            return
        try:
            path = nx.shortest_path(self.G, self.start, self.end)
            self._draw_grid(path)
            self.status.set(f"Path found ({len(path)} steps)")
        except nx.NetworkXNoPath:
            messagebox.showinfo("No Path","No route available")
            self.status.set("No path")
    
    def _reset(self):
        self.G = nx.grid_2d_graph(self.rows, self.cols)
        self.start = self.end = None
        self.status.set("Cleared")
        self._draw_grid()
    
    def _export(self):
        if not self.start or not self.end:
            messagebox.showwarning("Nothing to export","Solve first")
            return
        try:
            path = nx.shortest_path(self.G, self.start, self.end)
            with open("maze_solution.txt","w") as f:
                for i,cell in enumerate(path,1):
                    f.write(f"Step {i}: {cell}\n")
            messagebox.showinfo("Exported","Saved to maze_solution.txt")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))


if __name__=="__main__":
    root = tk.Tk()
    app = MazeSolverGUI(root)
    root.mainloop()
