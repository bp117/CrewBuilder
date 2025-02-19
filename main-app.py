import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import sys
import platform
from PIL import Image
import pystray
import threading
from pathlib import Path
from datetime import datetime
import subprocess
from recorder import CrossPlatformScreenRecorder
from gcpintegrations import GCPIntegrations

class JsonTreeView(ttk.Treeview):
    """Custom TreeView widget for displaying JSON data hierarchically"""
    def __init__(self, parent):
        super().__init__(parent)
        
        # Configure the treeview
        self.column("#0", width=300)
        self.heading("#0", text="Workflow Structure")
        
        # Add scrollbars
        self.vsb = ttk.Scrollbar(parent, orient="vertical", command=self.yview)
        self.hsb = ttk.Scrollbar(parent, orient="horizontal", command=self.xview)
        self.configure(yscrollcommand=self.vsb.set, xscrollcommand=self.hsb.set)
        
        # Grid layout
        self.grid(row=0, column=0, sticky="nsew")
        self.vsb.grid(row=0, column=1, sticky="ns")
        self.hsb.grid(row=1, column=0, sticky="ew")
        
    def load_json(self, json_data):
        """Load JSON data into the tree view"""
        # Clear existing items
        for item in self.get_children():
            self.delete(item)
            
        # Insert the JSON data
        self._insert_json("", json_data)
        
    def _insert_json(self, parent, data):
        """Recursively insert JSON data into the tree"""
        if isinstance(data, dict):
            for key, value in data.items():
                item = self.insert(parent, "end", text=str(key))
                self._insert_json(item, value)
        elif isinstance(data, list):
            for i, value in enumerate(data):
                item = self.insert(parent, "end", text=f"[{i}]")
                self._insert_json(item, value)
        else:
            self.insert(parent, "end", text=str(data))

class JsonViewer(ttk.Frame):
    """Text widget for displaying raw JSON data"""
    def __init__(self, parent):
        super().__init__(parent)
        
        # Create text widget with scrollbars
        self.text = tk.Text(self, wrap=tk.NONE, font=('Courier', 10))
        self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.text.yview)
        self.hsb = ttk.Scrollbar(self, orient="horizontal", command=self.text.xview)
        self.text.configure(yscrollcommand=self.vsb.set, xscrollcommand=self.hsb.set)
        
        # Grid layout
        self.text.grid(row=0, column=0, sticky="nsew")
        self.vsb.grid(row=0, column=1, sticky="ns")
        self.hsb.grid(row=1, column=0, sticky="ew")
        
        # Configure grid weights
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
    def load_json(self, json_data):
        """Display formatted JSON data"""
        self.text.delete('1.0', tk.END)
        self.text.insert('1.0', json.dumps(json_data, indent=2))
        self.text.config(state='disabled')

class FlowDesigner:
    """Main designer component with split view for JSON visualization"""
    def __init__(self, parent):
        self.parent = parent
        self.setup_ui()
        
    def setup_ui(self):
        # Configure grid weights for the parent
        self.parent.grid_rowconfigure(0, weight=1)
        self.parent.grid_columnconfigure(0, weight=1)
        
        # Create main paned window
        self.paned = ttk.PanedWindow(self.parent, orient=tk.HORIZONTAL)
        self.paned.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        # Create frames for tree and json views
        self.tree_frame = ttk.Frame(self.paned)
        self.json_frame = ttk.Frame(self.paned)
        
        # Configure grid weights for frames
        self.tree_frame.grid_rowconfigure(0, weight=1)
        self.tree_frame.grid_columnconfigure(0, weight=1)
        self.json_frame.grid_rowconfigure(0, weight=1)
        self.json_frame.grid_columnconfigure(0, weight=1)
        
        # Create views
        self.tree = JsonTreeView(self.tree_frame)
        self.json_viewer = JsonViewer(self.json_frame)
        
        # Add to paned window
        self.paned.add(self.tree_frame, weight=1)
        self.paned.add(self.json_frame, weight=1)
        
    def load_workflow_data(self, json_data):
        """Load workflow data into both views"""
        self.tree.load_json(json_data)
        self.json_viewer.load_json(json_data)
        
    def clear(self):
        """Clear both views"""
        self.tree.delete(*self.tree.get_children())
        self.json_viewer.text.delete('1.0', tk.END)

class AgentFlowApplication:
    """Main application class"""
    def __init__(self, root):
        self.root = root
        self.setup_window()
        self.setup_ui()
        self.initialize_state()
        
    def setup_window(self):
        """Configure main window properties"""
        self.root.title("Agent Flow Designer")
        
        # Calculate window dimensions
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        window_width = min(int(screen_width * 0.8), 1920)
        window_height = min(int(screen_height * 0.8), 1080)
        
        window_width = max(window_width, 1400)
        window_height = max(window_height, 800)
        
        # Center the window
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.root.minsize(1400, 800)
        
        # Store initial window state
        self.initial_window_state = {
            'geometry': self.root.geometry(),
            'state': 'normal',
            'width': window_width,
            'height': window_height,
            'x': x,
            'y': y
        }
        
        # Set up close handler
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def initialize_state(self):
        """Initialize application state"""
        self.current_recording = None
        self.current_interactions_path = None
        self.recording_active = False
        self._recording_cleanup_done = False
        self.tray_icon = None
        
        # Initialize GCP integration
        self.initialize_gcp()
    def initialize_gcp(self):
        """Initialize GCP integrations with explicit credential handling"""
        try:
            # First check for credentials file in the app directory
            local_creds = os.path.join(os.path.dirname(__file__), 'service-account.json')
            
            # Then check for environment variable
            env_creds = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
            print("Creds loaded",env_creds)
            # Use local credentials if available, otherwise use environment variable
            creds_path = local_creds if os.path.exists(local_creds) else env_creds
            print("Creds loaded",creds_path)
            self.gcp = GCPIntegrations(
                project_id="woven-ceremony-836",  # Replace with your GCP project ID
                location="us-central1",
                credentials_path=creds_path
            )
            
            # Verify GCP connection by checking bucket access
            if not self.gcp.verify_bucket_access("your-bucket-name"):  # Replace with your bucket name
                raise Exception("Cannot access GCS bucket. Please verify permissions.")
                
        except Exception as e:
            error_msg = f"Error initializing GCP: {str(e)}\n\n"
            error_msg += "Please ensure:\n"
            error_msg += "1. GCP service account key file is present\n"
            error_msg += "2. GOOGLE_APPLICATION_CREDENTIALS environment variable is set\n"
            error_msg += "3. The service account has necessary permissions"
            
            print(error_msg)
            messagebox.showerror("GCP Integration Error", error_msg)
            self.gcp = None
        
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
        
        # Create toolbar buttons
        ttk.Button(self.toolbar, text="Create Agent", 
                  command=self.create_agent).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.toolbar, text="Modify Agent", 
                  command=self.modify_agent).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.toolbar, text="Export Configuration", 
                  command=self.export_config).pack(side=tk.LEFT, padx=5)
        
        self.record_btn = ttk.Button(self.toolbar, text="Start Recording",
                                   command=self.start_recording)
        self.record_btn.pack(side=tk.LEFT, padx=5)
        
        self.analyze_btn = ttk.Button(self.toolbar, text="Analyze Recording",
                                    command=self.analyze_recording, state=tk.DISABLED)
        self.analyze_btn.pack(side=tk.LEFT, padx=5)
        
        self.preview_btn = ttk.Button(self.toolbar, text="Preview Recording",
                                    command=self.preview_recording, state=tk.DISABLED)
        self.preview_btn.pack(side=tk.LEFT, padx=5)
        
    def setup_main_content(self):
        """Set up the main content area"""
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        
        self.flow_designer = FlowDesigner(self.main_frame)
        
    def create_tray_icon(self):
        """Create system tray icon for recording state"""
        try:
            icon_size = (64, 64)
            icon_image = Image.new('RGB', icon_size, color='red')
            
            def stop_recording_handler(icon, item):
                icon.stop()
                self.root.after(100, self.stop_recording_callback)
            
            menu = pystray.Menu(
                pystray.MenuItem("Stop Recording", stop_recording_handler)
            )
            
            self.tray_icon = pystray.Icon(
                "screen_recorder",
                icon_image,
                "Screen Recording in Progress",
                menu=menu
            )
            
            threading.Thread(target=self._run_tray_icon, daemon=True).start()
            self.root.after(500, self.root.withdraw)
            
        except Exception as e:
            print(f"Error creating tray icon: {e}")
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
            self.analyze_btn.config(state=tk.DISABLED)
            
            self.store_window_state()
            self.create_tray_icon()
            self.recorder.start_recording()
            
        except Exception as e:
            self.recording_active = False
            self.record_btn.config(state=tk.NORMAL)
            self.analyze_btn.config(state=tk.DISABLED)
            
            if hasattr(self, 'tray_icon') and self.tray_icon:
                try:
                    self.tray_icon.stop()
                except:
                    pass
                self.tray_icon = None
                
            messagebox.showerror("Error", f"Failed to start recording: {str(e)}")
            
    def store_window_state(self):
        """Store window state before minimizing"""
        self.initial_window_state = {
            'geometry': self.root.geometry(),
            'state': self.root.state(),
            'was_zoomed': self.root.state() == 'zoomed',
            'width': self.root.winfo_width(),
            'height': self.root.winfo_height(),
            'x': self.root.winfo_x(),
            'y': self.root.winfo_y()
        }
        
    def stop_recording_callback(self):
        """Handle recording stop event"""
        if not hasattr(self, 'recorder'):
            return
            
        try:
            print("Stopping recording...")
            self.recording_active = False
            
            self.root.config(cursor="wait")
            
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
                
                self.restore_window_state()
                
                self.preview_btn.config(state=tk.NORMAL)
                self.analyze_btn.config(state=tk.NORMAL)
                self.record_btn.config(state=tk.NORMAL)
                
                messagebox.showinfo("Recording Complete", 
                                  "Recording has been saved. Click 'Analyze Recording' to process it.")
            else:
                raise Exception("Recording files were not saved properly")
                
        except Exception as e:
            print(f"Error in stop_recording: {str(e)}")
            messagebox.showerror("Error", f"Failed to stop recording: {str(e)}")
        finally:
            self.root.config(cursor="")
            self._recording_cleanup_done = True
            
    def restore_window_state(self):
        """Restore window state after recording"""
        try:
            self.root.deiconify()
            self.root.update_idletasks()
            
            if self.initial_window_state:
                self.root.geometry(self.initial_window_state['geometry'])
                self.root.state('zoomed' if self.initial_window_state.get('was_zoomed') else 'normal')
            
            self.root.lift()
            self.root.focus_force()
            
        except Exception as e:
            print(f"Error restoring window: {e}")
            self.root.deiconify()
            self.root.state('normal')
            self.root.geometry("1400x800")
            
    def analyze_recording(self):
        """Analyze the recording using GCP services"""
        try:
            if not self.current_recording or not self.current_interactions_path:
                messagebox.showerror("Error", "No recording available to analyze")
                return
                
            if not self.gcp:
                messagebox.showerror("Error", "GCP integration not initialized")
                return
                
            # Show processing indicator
            self.root.config(cursor="wait")
            self.analyze_btn.config(state=tk.DISABLED)
            self.root.update()
            
            # Process the recording
            workflow_data = self.gcp.process_recording(
                self.current_recording,
                self.current_interactions_path,
                "flow_designer"  # Replace with your bucket name
            )
            
            if workflow_data:
                self.flow_designer.load_workflow_data(workflow_data)
                messagebox.showinfo("Analysis Complete", 
                                  "Recording has been analyzed and workflow generated.")
            else:
                messagebox.showerror("Error", "Failed to analyze recording")
                
        except Exception as e:
            print(f"Error analyzing recording: {e}")
            messagebox.showerror("Error", f"Analysis failed: {str(e)}")
        finally:
            self.root.config(cursor="")
            self.analyze_btn.config(state=tk.NORMAL)
            
    def preview_recording(self):
        """Open the recorded video in system player"""
        try:
            if self.current_recording and os.path.exists(self.current_recording):
                if platform.system() == 'Windows':
                    os.startfile(self.current_recording)
                elif platform.system() == 'Darwin':  
                    subprocess.run(['open', self.current_recording])
                else:  
                    subprocess.run(['xdg-open', self.current_recording])
        except Exception as e:
            print(f"Error opening video: {e}")
            messagebox.showerror("Error", "Failed to open video player")
            
    def create_agent(self):
        """Handle Create Agent button click"""
        try:
            self.record_btn.config(state=tk.NORMAL)
            self.flow_designer.clear()
            messagebox.showinfo("Create Agent", 
                              "Click 'Start Recording' to begin capturing your workflow.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create agent: {str(e)}")
            
    def modify_agent(self):
        """Handle Modify Agent button click"""
        try:
            messagebox.showinfo("Modify Agent", 
                              "You can now modify the flow diagram.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to enable editing: {str(e)}")
            
    def export_config(self):
        """Export flow configuration to JSON"""
        try:
            # Get the current timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Create exports directory if it doesn't exist
            export_dir = Path("exports")
            export_dir.mkdir(exist_ok=True)
            
            # Create export file path
            file_path = export_dir / f"agent_config_{timestamp}.json"
            
            # Get current workflow data from JSON viewer
            try:
                workflow_text = self.flow_designer.json_viewer.text.get('1.0', tk.END)
                workflow_data = json.loads(workflow_text)
            except:
                workflow_data = {}
            
            # Add metadata
            export_data = {
                "metadata": {
                    "exported_at": timestamp,
                    "version": "1.0"
                },
                "workflow": workflow_data
            }
            
            # Save to file
            with open(file_path, 'w') as f:
                json.dump(export_data, f, indent=2)
                
            messagebox.showinfo("Export Successful", 
                              f"Configuration exported to {file_path}")
                              
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export configuration: {str(e)}")
            
    def on_closing(self):
        """Handle window close event"""
        if self.recording_active:
            if messagebox.askyesno("Stop Recording", 
                                 "Recording is in progress. Stop recording and exit?"):
                self.stop_recording_callback()
                self.root.destroy()
        else:
            self.root.destroy()

def main():
    root = tk.Tk()
    app = AgentFlowApplication(root)
    root.mainloop()

if __name__ == "__main__":
    main()