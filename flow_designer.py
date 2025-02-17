import tkinter as tk
from tkinter import ttk
import json

class FlowDesigner:
    def __init__(self, parent):
        self.parent = parent
        self.setup_canvas()
        self.nodes = []
        self.connections = []
        
    def setup_canvas(self):
        self.canvas = tk.Canvas(self.parent, bg='white')
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        
        self.vsb = ttk.Scrollbar(self.parent, orient="vertical", command=self.canvas.yview)
        self.hsb = ttk.Scrollbar(self.parent, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=self.vsb.set, xscrollcommand=self.hsb.set)
        
        
        self.vsb.pack(side="right", fill="y")
        self.hsb.pack(side="bottom", fill="x")
        
    def create_flow_from_json(self, flow_json):
        self.clear_canvas()
        x, y = 50, 50
        prev_node = None
        
        for step in flow_json["steps"]:
            node = self.create_node(x, y, step)
            if prev_node:
                self.create_connection(prev_node, node)
            prev_node = node
            y += 100
            
    def create_node(self, x, y, data):
        
        node = self.canvas.create_rectangle(x, y, x+150, y+60, fill='lightblue', outline='navy')
        
        
        text = f"{data['type']}\n{data['details']['action_type']}"
        text_id = self.canvas.create_text(x+75, y+30, text=text, width=140)
        
        self.nodes.append({
            'id': node,
            'text_id': text_id,
            'data': data,
            'x': x,
            'y': y
        })
        return node
        
    def create_connection(self, from_node, to_node):
        coords_from = self.canvas.coords(from_node)
        coords_to = self.canvas.coords(to_node)
        
        
        connection = self.canvas.create_line(
            coords_from[0] + 75, coords_from[3],
            coords_to[0] + 75, coords_to[1],
            arrow=tk.LAST, fill='navy'
        )
        self.connections.append(connection)
        
    def clear_canvas(self):
        self.canvas.delete("all")
        self.nodes = []
        self.connections = []
        
    def enable_editing(self):
        self.canvas.bind("<Button-1>", self.on_node_click)
        self.canvas.bind("<B1-Motion>", self.on_node_drag)
        
    def on_node_click(self, event):
        self.selected = self.canvas.find_closest(event.x, event.y)
        self.start_x = event.x
        self.start_y = event.y
        
    def on_node_drag(self, event):
        dx = event.x - self.start_x
        dy = event.y - self.start_y
        
        self.canvas.move(self.selected[0], dx, dy)
        
        for node in self.nodes:
            if node['id'] == self.selected[0]:
                self.canvas.move(node['text_id'], dx, dy)
                break
                
        self.start_x = event.x
        self.start_y = event.y
        self.update_connections()
        
    def update_connections(self):
        for conn in self.connections:
            self.canvas.delete(conn)
        self.connections = []
        
        for i in range(len(self.nodes)-1):
            self.create_connection(self.nodes[i]['id'], self.nodes[i+1]['id'])
            
    def export_configuration(self):
        config = {
            "steps": [node['data'] for node in self.nodes],
            "layout": {
                "nodes": [{
                    "id": node['id'],
                    "position": {
                        "x": self.canvas.coords(node['id'])[0],
                        "y": self.canvas.coords(node['id'])[1]
                    }
                } for node in self.nodes]
            }
        }
        return config