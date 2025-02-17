import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
from recorder import CrossPlatformScreenRecorder
from video_player import VideoPlayer
import sys
import platform
from PIL import Image
import pystray
import threading

class FlowDesigner:
    def __init__(self, parent):
        self.parent = parent
        self.setup_canvas()
        
    def setup_canvas(self):
        # Create canvas with scrollbars
        self.canvas_frame = ttk.Frame(self.parent)
        self.canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(self.canvas_frame, bg='white')
        self.vscrollbar = ttk.Scrollbar(self.canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.hscrollbar = ttk.Scrollbar(self.canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        
        self.canvas.configure(xscrollcommand=self.hscrollbar.set, yscrollcommand=self.vscrollbar.set)
        
        # Grid layout
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.vscrollbar.grid(row=0, column=1, sticky="ns")
        self.hscrollbar.grid(row=1, column=0, sticky="ew")
        
        self.canvas_frame.grid_rowconfigure(0, weight=1)
        self.canvas_frame.grid_columnconfigure(0, weight=1)
        
    def clear_canvas(self):
        self.canvas.delete("all")
        
    def enable_editing(self):
        pass  # Implement editing functionality here

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
            'y': y,
            'state': 'normal'
        }
        
        self.root.minsize(1400, 800)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def initialize_state(self):
        """Initialize application state variables"""
        self.current_recording = None
        self.current_interactions_path = None
        self.recording_active = False
        self._recording_cleanup_done = False
        self.tray_icon = None
        
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
        
        self.record_btn = ttk.Button(self.toolbar, text="Start Recording",
                                   command=self.start_recording)
        self.record_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(self.toolbar, text="Stop Recording",
                                  command=self.stop_recording, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        # Add preview button (disabled by default)
        self.preview_btn = ttk.Button(self.toolbar, text="Preview Recording",
                                    command=self.preview_recording, state=tk.DISABLED)
        self.preview_btn.pack(side=tk.LEFT, padx=5)

    def preview_recording(self):
        """Open the recorded video in system player"""
        try:
            if self.current_recording and os.path.exists(self.current_recording):
                if platform.system() == 'Windows':
                    os.startfile(self.current_recording)
                elif platform.system() == 'Darwin':  # macOS
                    subprocess.run(['open', self.current_recording])
                else:  # Linux
                    subprocess.run(['xdg-open', self.current_recording])
        except Exception as e:
            print(f"Error opening video: {e}")
            messagebox.showerror("Error", "Failed to open video player")
        
    def setup_main_content(self):
        """Set up the main content area"""
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        
        # Let the flow designer occupy most of the screen
        self.flow_designer = FlowDesigner(self.main_frame)
        
    def create_tray_icon(self):
        """Create system tray icon"""
        try:
            # Create a red square icon
            icon_size = (64, 64)
            icon_image = Image.new('RGB', icon_size, color='red')
            
            def stop_recording_handler(icon, item):
                icon.stop()
                self.root.after(100, self.stop_recording)
            
            menu = pystray.Menu(
                pystray.MenuItem("Stop Recording", stop_recording_handler)
            )
            
            self.tray_icon = pystray.Icon(
                "screen_recorder",
                icon_image,
                "Screen Recording in Progress",
                menu=menu
            )
            
            # Start the tray icon in a separate thread
            threading.Thread(target=self._run_tray_icon, daemon=True).start()
            
            # Wait a bit to ensure the tray icon is showing
            self.root.after(500, self.root.withdraw)
            
        except Exception as e:
            print(f"Error creating tray icon: {e}")
            # If tray icon fails, keep window minimized but visible
            self.root.iconify()

    def _run_tray_icon(self):
        """Run the tray icon in a separate thread"""
        try:
            if self.tray_icon:
                self.tray_icon.run()
        except Exception as e:
            print(f"Error running tray icon: {e}")

    def start_recording(self):
        """Start screen recording"""
        try:
            self.recording_active = True
            self._recording_cleanup_done = False
            self.recorder = CrossPlatformScreenRecorder(self)
            self.record_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            
            # Store current window state before minimizing
            self.store_window_state()
            
            # Create and show tray icon before starting recording
            self.create_tray_icon()
            
            # Start the actual recording
            self.recorder.start_recording()
            
        except Exception as e:
            self.recording_active = False
            self.record_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            
            # Clean up tray icon if it exists
            if hasattr(self, 'tray_icon') and self.tray_icon:
                try:
                    self.tray_icon.stop()
                except:
                    pass
                self.tray_icon = None
                
            messagebox.showerror("Error", f"Failed to start recording: {str(e)}")

    def store_window_state(self):
        """Store complete window state before minimizing the window"""
        self.initial_window_state = {
            'geometry': self.root.geometry(),
            'state': self.root.state(),  # This returns 'normal' or 'zoomed'
            'was_zoomed': True if self.root.state() == 'zoomed' else False,
            'width': self.root.winfo_width(),
            'height': self.root.winfo_height(),
            'x': self.root.winfo_x(),
            'y': self.root.winfo_y()
        }
        print(f"Stored window state: {self.initial_window_state}")

    def stop_recording_from_tray(self, icon, item):
        """Handle stop recording from system tray"""
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.after(100, self.stop_recording)
        
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
            self.flow_designer.enable_editing()
            messagebox.showinfo("Modify Agent", 
                              "You can now modify the flow diagram.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to enable editing: {str(e)}")
        
    def stop_recording(self):
        """Stop screen recording"""
        if not hasattr(self, 'recorder'):
            return

        try:
            print("Stopping recording...")
            self.recording_active = False
            
            self.stop_btn.config(state=tk.DISABLED)
            self.record_btn.config(state=tk.DISABLED)
            
            self.root.config(cursor="wait")
            
            # Stop the tray icon
            if hasattr(self, 'tray_icon') and self.tray_icon:
                try:
                    self.tray_icon.stop()
                except:
                    pass
                self.tray_icon = None

            video_path, interactions_path = self.recorder.stop_recording()
            
            if video_path and os.path.exists(video_path):
                self.current_recording = video_path
                self.current_interactions_path = interactions_path
                
                # Restore window first
                self.restore_window_state()
                
                # Enable preview button
                self.preview_btn.config(state=tk.NORMAL)
                
                messagebox.showinfo("Recording Complete", 
                                  "Recording has been saved. Click 'Preview Recording' to view it.")
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

    def restore_window_state(self):
        """Restore window state after recording"""
        try:
            print("Restoring window state...")
            
            # Ensure the window is visible
            self.root.deiconify()
            self.root.update_idletasks()
            
            if self.initial_window_state:
                # Restore the window geometry
                self.root.geometry(self.initial_window_state['geometry'])
                
                # Restore state to zoomed if it was zoomed; otherwise normal
                self.root.state('zoomed' if self.initial_window_state.get('was_zoomed') else 'normal')
                print(f"Restored geometry: {self.initial_window_state['geometry']}")
            
            # Bring the window to the front
            self.root.lift()
            self.root.focus_force()
            self.root.update_idletasks()
        except Exception as e:
            print(f"Error restoring window: {e}")
            # Fallback in the event of an error
            self.root.deiconify()
            self.root.state('normal')
            self.root.geometry("1400x800")
            self.root.update()
            
    def export_config(self):
        """Export flow configuration to JSON"""
        try:
            config = {"flow": "sample_config"}  # Replace with actual flow config
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