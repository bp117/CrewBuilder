import os
import platform
import subprocess
import tkinter as tk
from tkinter import ttk

class VideoPlayer:
    def __init__(self, parent):
        self.parent = parent
        self.setup_ui()

    def setup_ui(self):
        """Set up a simple interface with just a button to open the video"""
        self.container = ttk.Frame(self.parent)
        self.container.pack(fill=tk.BOTH, expand=True)

        self.label = ttk.Label(
            self.container,
            text="Recording complete! Click below to view the recording.",
            wraplength=400
        )
        self.label.pack(expand=True, padx=20, pady=(20, 0))

        self.play_btn = ttk.Button(
            self.container, 
            text="Open in Media Player",
            command=self.play_in_system_player,
            state=tk.DISABLED
        )
        self.play_btn.pack(expand=True, padx=20, pady=(0, 20))

        self.current_video = None

    def load_video(self, video_path):
        """Store the video path and enable the play button"""
        self.current_video = video_path
        if os.path.exists(video_path):
            self.play_btn.config(state=tk.NORMAL)

    def play_in_system_player(self):
        """Open the video in the system's default media player"""
        if not self.current_video or not os.path.exists(self.current_video):
            return

        try:
            if platform.system() == 'Windows':
                os.startfile(self.current_video)
            elif platform.system() == 'Darwin':  # macOS
                subprocess.run(['open', self.current_video])
            else:  # Linux
                subprocess.run(['xdg-open', self.current_video])
        except Exception as e:
            print(f"Error opening video: {e}")
