# video_player.py
import cv2
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import threading
import time

class VideoPlayer:
    def __init__(self, parent):
        self.parent = parent
        self.setup_ui()
        self.playing = False
        self.current_frame = 0
        
    def setup_ui(self):
        # Video display
        self.canvas = tk.Canvas(self.parent)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Controls
        self.controls = ttk.Frame(self.parent)
        self.controls.pack(fill=tk.X, padx=5, pady=5)
        
        self.play_btn = ttk.Button(self.controls, text="Play", command=self.toggle_play)
        self.play_btn.pack(side=tk.LEFT, padx=5)
        
        self.progress = ttk.Scale(self.controls, from_=0, to=100, orient=tk.HORIZONTAL)
        self.progress.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
    def load_video(self, video_path):
        self.video_path = video_path
        self.cap = cv2.VideoCapture(video_path)
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.progress.config(to=self.total_frames)
        self.show_frame(0)
        
    def show_frame(self, frame_no):
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = cv2.resize(frame, (800, 600))
            img = Image.fromarray(frame)
            img_tk = ImageTk.PhotoImage(image=img)
            self.canvas.create_image(0, 0, anchor=tk.NW, image=img_tk)
            self.canvas.image = img_tk
            
    def toggle_play(self):
        self.playing = not self.playing
        if self.playing:
            self.play_btn.config(text="Pause")
            threading.Thread(target=self.play_video, daemon=True).start()
        else:
            self.play_btn.config(text="Play")
            
    def play_video(self):
        while self.playing and self.current_frame < self.total_frames:
            self.show_frame(self.current_frame)
            self.progress.set(self.current_frame)
            self.current_frame += 1
            time.sleep(1/self.fps)

# flow_designer.py
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
        
        # Add scrollbars
        self.vsb = ttk.Scrollbar(self.parent, orient="vertical", command=self.canvas.yview)
        self.hsb = ttk.Scrollbar(self.parent, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=self.vsb.set, xscrollcommand=self.hsb.set)
        
        # Grid layout
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
        # Create node rectangle
        node = self.canvas.create_rectangle(x, y, x+150, y+60, fill='lightblue', outline='navy')
        
        # Add text
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
        
        # Draw arrow
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
        # Move associated text
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

# analyzer.py
class InteractionAnalyzer:
    def __init__(self):
        self.workflow_steps = []
        
    def analyze_interactions(self, interactions_path):
        with open(interactions_path, 'r') as f:
            data = json.load(f)
            
        interactions = data["recording_data"]["interactions"]
        
        for interaction in interactions:
            if interaction["type"] == "click":
                self.workflow_steps.append({
                    "type": "action",
                    "details": {
                        "action_type": "click",
                        "target": interaction["element"]["text"] if "text" in interaction["element"] else "Unknown",
                        "position": interaction["position"]
                    }
                })
            elif interaction["type"] == "scroll":
                self.workflow_steps.append({
                    "type": "action",
                    "details": {
                        "action_type": "scroll",
                        "direction": interaction["direction"]
                    }
                })
                
        return {"steps": self.workflow_steps}
