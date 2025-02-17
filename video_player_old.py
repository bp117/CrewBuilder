
import cv2
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import threading
import time

class VideoPlayer:
    def __init__(self, parent):
        self.parent = parent
        self.playing = False
        self.current_frame = 0
        self.total_frames = 0
        self.cap = None
        self.desired_width = 800
        self._update_pending = False
        self.setup_ui()

    def setup_ui(self):
        
        self.container = ttk.Frame(self.parent)
        self.container.pack(fill=tk.BOTH, expand=True)

        
        self.video_frame = ttk.Frame(self.container)
        self.video_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        
        self.canvas = tk.Canvas(self.video_frame, bg='black', width=800, height=600)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        
        self.controls = ttk.Frame(self.container)
        self.controls.pack(fill=tk.X, padx=5, pady=5)

        
        self.play_btn = ttk.Button(self.controls, text="Play", command=self.toggle_play)
        self.play_btn.pack(side=tk.LEFT, padx=5)

        
        self.time_label = ttk.Label(self.controls, text="0:00 / 0:00")
        self.time_label.pack(side=tk.RIGHT, padx=5)

        
        self.progress = ttk.Scale(self.controls, from_=0, to=1000, orient=tk.HORIZONTAL)
        self.progress.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.progress.bind("<ButtonRelease-1>", self.on_progress_change)

    def on_progress_change(self, event):
        if not self.playing and self.cap is not None:
            try:
                value = self.progress.get()
                frame_no = int((value / 1000.0) * self.total_frames)
                self.current_frame = frame_no
                self.display_frame(frame_no)
            except Exception as e:
                print(f"Error in progress change: {e}")

    def calculate_dimensions(self, frame_width, frame_height):
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        if canvas_width <= 1:
            canvas_width = self.desired_width
        if canvas_height <= 1:
            canvas_height = 600

        width_ratio = canvas_width / frame_width
        height_ratio = canvas_height / frame_height
        scale = min(width_ratio, height_ratio)

        new_width = int(frame_width * scale)
        new_height = int(frame_height * scale)

        return new_width & ~1, new_height & ~1  

    def load_video(self, video_path):
        if hasattr(self, 'cap') and self.cap is not None:
            self.cap.release()
            
        self.cap = cv2.VideoCapture(video_path)
        if not self.cap.isOpened():
            print("Error: Could not open video file")
            return

        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.current_frame = 0
        
        self.display_frame(0)

    def display_frame(self, frame_no):
        if self._update_pending or not hasattr(self, 'cap') or self.cap is None:
            return

        try:
            self._update_pending = True
            
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
            ret, frame = self.cap.read()
            
            if ret:
                
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                new_width, new_height = self.calculate_dimensions(frame.shape[1], frame.shape[0])
                frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)

                
                image = Image.fromarray(frame)
                photo = ImageTk.PhotoImage(image=image)

                
                self.canvas.delete("all")
                x = (self.canvas.winfo_width() - new_width) // 2
                y = (self.canvas.winfo_height() - new_height) // 2
                self.canvas.create_image(x, y, anchor=tk.NW, image=photo)
                self.canvas.image = photo  

                
                progress = int((frame_no / self.total_frames) * 1000)
                self.progress.set(progress)

                
                current_time = frame_no / self.fps
                total_time = self.total_frames / self.fps
                self.time_label.config(
                    text=f"{int(current_time//60)}:{int(current_time%60):02d} / "
                         f"{int(total_time//60)}:{int(total_time%60):02d}"
                )

        except Exception as e:
            print(f"Error displaying frame: {e}")
        finally:
            self._update_pending = False

    def toggle_play(self):
        if not hasattr(self, 'cap') or self.cap is None:
            return
            
        self.playing = not self.playing
        if self.playing:
            self.play_btn.config(text="Pause")
            threading.Thread(target=self.play_video, daemon=True).start()
        else:
            self.play_btn.config(text="Play")

    def play_video(self):
        while self.playing and self.current_frame < self.total_frames:
            start_time = time.time()
            
            if not self._update_pending:
                self.display_frame(self.current_frame)
                self.current_frame += 1

            
            elapsed = time.time() - start_time
            sleep_time = max(0, 1.0/self.fps - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)

        if self.current_frame >= self.total_frames:
            self.playing = False
            self.play_btn.config(text="Play")
            self.current_frame = 0
            self.display_frame(0)