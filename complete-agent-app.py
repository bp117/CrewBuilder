
import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
from recorder_old import CrossPlatformScreenRecorder
from flow_designer import FlowDesigner
from analyzer import InteractionAnalyzer
from video_player_old import VideoPlayer
import sys


sys.setrecursionlimit(2000)

class AgentFlowApplication:
    def __init__(self, root):
        self.root = root
        self.setup_window()
        self.setup_ui()
        self.initialize_state()
        
    def setup_window(self):
        """Configure main window properties"""
        self.root.title("Agent Flow Designer")
        
        
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        
        window_width = min(int(screen_width * 0.8), 1920)
        window_height = min(int(screen_height * 0.8), 1080)
        
        
        window_width = max(window_width, 1400)
        window_height = max(window_height, 800)
        
        
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        
        geometry = f"{window_width}x{window_height}+{x}+{y}"
        self.root.geometry(geometry)
        
        
        self.initial_window_state = {
            'geometry': geometry,
            'width': window_width,
            'height': window_height,
            'x': x,
            'y': y
        }
        print(f"Original window size:{self.initial_window_state}")
        
        self.root.minsize(1400, 800)
        
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def initialize_state(self):
        """Initialize application state variables"""
        self.current_recording = None
        self.current_interactions_path = None
        self.recording_active = False
        self._recording_cleanup_done = False
        
    def setup_ui(self):
        """Set up the user interface"""
        
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        
        self.setup_toolbar()
        
        
        self.setup_main_content()
        
    def setup_toolbar(self):
        """Set up the top toolbar"""
        self.toolbar = ttk.Frame(self.root)
        self.toolbar.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        
        
        ttk.Button(self.toolbar, text="Create Agent", 
                  command=self.create_agent).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.toolbar, text="Modify Agent", 
                  command=self.modify_agent).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.toolbar, text="Export Configuration", 
                  command=self.export_config).pack(side=tk.LEFT, padx=5)
        
    def setup_main_content(self):
        """Set up the main content area with video and flow panels"""
        
        self.main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_paned.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        
        
        self.setup_left_panel()
        self.setup_right_panel()
        
    def setup_left_panel(self):
        """Set up the left panel with video controls and preview"""
        self.left_panel = ttk.Frame(self.main_paned)
        self.main_paned.add(self.left_panel, weight=1)
        
        
        self.setup_recording_controls()
        
        
        self.setup_video_preview()
        
    def setup_recording_controls(self):
        """Set up recording control buttons"""
        self.video_controls = ttk.LabelFrame(self.left_panel, text="Recording Controls")
        self.video_controls.pack(fill=tk.X, padx=5, pady=5)
        
        
        controls_frame = ttk.Frame(self.video_controls)
        controls_frame.pack(fill=tk.X, padx=5, pady=5)
        
        
        self.record_btn = ttk.Button(controls_frame, text="Start Recording",
                                   command=self.start_recording, width=15)
        self.record_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(controls_frame, text="Stop Recording",
                                  command=self.stop_recording, state=tk.DISABLED, width=15)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        self.analyze_btn = ttk.Button(controls_frame, text="Analyze Recording",
                                    command=self.analyze_recording, state=tk.DISABLED, width=15)
        self.analyze_btn.pack(side=tk.LEFT, padx=5)
        
    def setup_video_preview(self):
        """Set up video preview area"""
        self.video_frame = ttk.LabelFrame(self.left_panel, text="Video Preview")
        self.video_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.video_player = VideoPlayer(self.video_frame)
        
    def setup_right_panel(self):
        """Set up the right panel with flow diagram"""
        self.right_panel = ttk.Frame(self.main_paned)
        self.main_paned.add(self.right_panel, weight=1)
        
        self.flow_frame = ttk.LabelFrame(self.right_panel, text="Flow Diagram")
        self.flow_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.flow_designer = FlowDesigner(self.flow_frame)
        
    def create_agent(self):
        """Handle Create Agent button click"""
        try:
            self.record_btn.config(state=tk.NORMAL)
            self.flow_designer.clear_canvas()
            messagebox.showinfo("Create Agent", 
                              "Click 'Start Recording' to begin capturing your workflow.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create agent: {str(e)}")
        
    def modify_agent(self):
        """Handle Modify Agent button click"""
        try:
            if hasattr(self, 'flow_designer'):
                self.flow_designer.enable_editing()
                messagebox.showinfo("Modify Agent", 
                                  "You can now modify the flow diagram. Click and drag elements to reposition them.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to enable editing: {str(e)}")
        
    def start_recording(self):
        """Start screen recording"""
        try:
            self.recording_active = True
            self._recording_cleanup_done = False  
            self.recorder = CrossPlatformScreenRecorder(self)
            self.record_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            self.recorder.start_recording()
        except Exception as e:
            self.recording_active = False
            self.record_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            messagebox.showerror("Error", f"Failed to start recording: {str(e)}")

    def stop_recording(self):
        """Stop screen recording with proper cleanup"""
        if not hasattr(self, 'recorder'):
            return

        try:
            print("Stopping recording...")
            self.recording_active = False
            
            
            self.stop_btn.config(state=tk.DISABLED)
            self.record_btn.config(state=tk.DISABLED)
            self.analyze_btn.config(state=tk.DISABLED)
            
            
            self.root.config(cursor="wait")
            self.root.update()

            
            print("Waiting for recorder to stop...")
            video_path, interactions_path = self.recorder.stop_recording()
            
            print(f"Recorder stopped. Video: {video_path}, Interactions: {interactions_path}")

            if video_path and os.path.exists(video_path) and interactions_path and os.path.exists(interactions_path):
                print("Files saved successfully")
                self.current_recording = video_path
                self.current_interactions_path = interactions_path
                
                
                self.restore_window_state()
                
                
                self.root.after(500, lambda: self.load_recorded_video(video_path))
                
                
                self.analyze_btn.config(state=tk.NORMAL)
            else:
                raise Exception("Recording files were not saved properly")

        except Exception as e:
            print(f"Error in stop_recording: {str(e)}")
            messagebox.showerror("Error", f"Failed to stop recording: {str(e)}")
        finally:
            
            self.root.config(cursor="")
            self.record_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            
            
            self.restore_window_state()
            self._recording_cleanup_done = True

    def load_recorded_video(self, video_path):
        """Load the recorded video with error handling"""
        try:
            if os.path.exists(video_path):
                self.video_player.load_video(video_path)
            else:
                raise Exception("Video file not found")
        except Exception as e:
            print(f"Error loading video: {str(e)}")
            messagebox.showerror("Error", "Failed to load recorded video")



    def restore_window_state(self):
        """Restore window state after recording"""
        try:
            print("Restoring main window state...")
            
            
            self.root.deiconify()
            
            
            self.root.state('normal')
            
            
            self.root.update()
            
            
            self.root.attributes('-topmost', True)
            
            
            if hasattr(self, 'initial_window_state'):
                width = max(self.initial_window_state['width'], 1400)
                height = max(self.initial_window_state['height'], 800)
                x = self.initial_window_state['x']
                y = self.initial_window_state['y']
                
                geometry = f"{width}x{height}+{x}+{y}"
                print(f"Restoring geometry: {geometry}")
                
                self.root.geometry(geometry)
                self.root.update_idletasks()
            
            
            self.root.lift()
            self.root.focus_force()
            
            
            self.root.attributes('-topmost', False)
            
            
            self.root.update()
            
            print("Window restoration completed",geometry)
            
        except Exception as e:
            print(f"Error restoring window: {e}")
            try:
                
                self.root.deiconify()
                self.root.state('normal')
                self.root.geometry("1400x800")
                self.root.update()
            except Exception as e2:
                print(f"Fallback restoration failed: {e2}")

            
    def analyze_recording(self):
        """Analyze recorded interactions"""
        if not self.current_interactions_path:
            return
            
        try:
            analyzer = InteractionAnalyzer()
            flow_json = analyzer.analyze_interactions(self.current_interactions_path)
            self.flow_designer.create_flow_from_json(flow_json)
            self.analyze_btn.config(state=tk.DISABLED)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to analyze recording: {str(e)}")
            
    def export_config(self):
        """Export flow configuration to JSON"""
        if not hasattr(self, 'flow_designer'):
            return
            
        try:
            config = self.flow_designer.export_configuration()
            file_path = "agent_config.json"
            with open(file_path, 'w') as f:
                json.dump(config, f, indent=2)
            messagebox.showinfo("Export Successful", 
                              f"Configuration exported to {file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export configuration: {str(e)}")
            
    def on_closing(self):
        """Handle window close event"""
        if self.recording_active:
            if messagebox.askyesno("Stop Recording", 
                                 "Recording is in progress. Stop recording and exit?"):
                self.stop_recording()
                self.root.destroy()
        else:
            self.root.destroy()

def main():
    root = tk.Tk()
    app = AgentFlowApplication(root)
    root.mainloop()

if __name__ == "__main__":
    main()