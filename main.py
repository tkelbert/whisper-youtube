import os
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import yt_dlp
import whisper
import re

AUDIO_DIR = os.path.expanduser("~/whisper_audio")

def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "", name)

def get_downloaded_filename(info_dict):
    title = sanitize_filename(info_dict.get('title', 'audio'))
    return os.path.join(AUDIO_DIR, f"{title}.mp3")

def download_audio(url, output_dir=AUDIO_DIR):
    downloaded_file = None

    def progress_hook(d):
        nonlocal downloaded_file
        if d['status'] == 'finished':
            downloaded_file = d['filename']

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
        }],
        'progress_hooks': [progress_hook],
        'quiet': True,
        'noplaylist': True
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        if not downloaded_file:
            downloaded_file = get_downloaded_filename(info)
        return downloaded_file

def remove_timestamps(text):
    return re.sub(r'\[\d{2}:\d{2}\.\d{3} --> \d{2}:\d{2}\.\d{3}\]\s+', '', text)

def transcribe_audio(model_name, language, audio_path, translate, translate_to, remove_ts, dual_output):
    model = whisper.load_model(model_name)
    options = {"fp16": False}
    if language:
        options["language"] = language

    result = model.transcribe(audio_path, **options)
    original_text = result['text']

    if remove_ts:
        segments = result['segments']
        original_text = '\n'.join([s['text'].strip() for s in segments])

    if translate and result.get("language") == "en" and translate_to:
        translated_result = model.transcribe(audio_path, task="translate", language="en")
        translated_text = translated_result['text']
        if dual_output:
            side_by_side = f"{'English':<50} | {translate_to.upper()}\n" + "-" * 100 + "\n"
            eng_lines = original_text.splitlines()
            trans_lines = translated_text.splitlines()
            for i in range(max(len(eng_lines), len(trans_lines))):
                left = eng_lines[i] if i < len(eng_lines) else ""
                right = trans_lines[i] if i < len(trans_lines) else ""
                side_by_side += f"{left:<50} | {right}\n"
            return side_by_side
        return translated_text

    return original_text

class WhisperApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("🎤 Whisper YouTube Transcriber")
        self.geometry("900x700")

        self.url_var = tk.StringVar()
        self.model_var = tk.StringVar(value="tiny")
        self.lang_var = tk.StringVar()
        self.translate_var = tk.BooleanVar()
        self.translate_to_var = tk.StringVar()
        self.remove_ts_var = tk.BooleanVar()
        self.dual_output_var = tk.BooleanVar()

        self.create_widgets()

    def create_widgets(self):
        padding = {'padx': 10, 'pady': 5}

        button_frame = tk.Frame(self)
        button_frame.pack(**padding)
        tk.Button(button_frame, text="Tiny Auto", command=lambda: self.quick_run("tiny", ""), width=12).grid(row=0, column=0)
        tk.Button(button_frame, text="Tiny English", command=lambda: self.quick_run("tiny", "en"), width=12).grid(row=0, column=1)
        tk.Button(button_frame, text="Tiny Spanish", command=lambda: self.quick_run("tiny", "es"), width=12).grid(row=0, column=2)

        tk.Label(self, text="YouTube URL:").pack(**padding)
        tk.Entry(self, textvariable=self.url_var, width=90).pack(**padding)

        frame = tk.Frame(self)
        frame.pack(**padding)

        tk.Label(frame, text="Model:").grid(row=0, column=0)
        ttk.Combobox(frame, textvariable=self.model_var, values=["tiny", "base", "small", "medium", "large"], width=10).grid(row=0, column=1)

        tk.Label(frame, text="Language (blank to detect):").grid(row=0, column=2)
        tk.Entry(frame, textvariable=self.lang_var, width=10).grid(row=0, column=3)

        tk.Checkbutton(self, text="Translate", variable=self.translate_var, command=self.toggle_translate).pack()

        self.translate_frame = tk.Frame(self)
        self.translate_to_label = tk.Label(self.translate_frame, text="Translate to:")
        self.translate_to_entry = tk.Entry(self.translate_frame, textvariable=self.translate_to_var, width=10)
        self.translate_to_label.pack(side=tk.LEFT)
        self.translate_to_entry.pack(side=tk.LEFT)

        tk.Checkbutton(self, text="Dual Output", variable=self.dual_output_var).pack()
        tk.Checkbutton(self, text="Remove Timestamps", variable=self.remove_ts_var).pack()

        self.translate_frame.pack()
        self.translate_frame.forget()

        tk.Button(self, text="Run", command=self.run_process).pack(pady=10)

        self.status = tk.Label(self, text="Status: Idle", anchor="w")
        self.status.pack(fill="x", padx=10, pady=5)

        self.output = tk.Text(self, wrap="word")
        self.output.pack(fill="both", expand=True, padx=10, pady=5)

    def toggle_translate(self):
        if self.translate_var.get():
            self.translate_frame.pack()
        else:
            self.translate_frame.forget()

    def quick_run(self, model, lang):
        self.model_var.set(model)
        self.lang_var.set(lang)
        self.run_process()

    def run_process(self):
        threading.Thread(target=self._run).start()

    def set_status(self, message):
        self.status.config(text=f"Status: {message}")
        self.update()

    def _run(self):
        url = self.url_var.get().strip()
        model = self.model_var.get().strip() or "tiny"
        lang = self.lang_var.get().strip() or None
        translate = self.translate_var.get()
        translate_to = self.translate_to_var.get().strip()
        remove_ts = self.remove_ts_var.get()
        dual_output = self.dual_output_var.get()

        if not url:
            messagebox.showerror("Error", "You must enter a YouTube URL.")
            return

        self.set_status("Downloading audio...")
        try:
            if not os.path.exists(AUDIO_DIR):
                os.makedirs(AUDIO_DIR)
            audio_path = download_audio(url)
        except Exception as e:
            self.set_status("Download failed.")
            messagebox.showerror("Download Error", str(e))
            return

        self.set_status("Transcribing audio...")
        try:
            text = transcribe_audio(model, lang, audio_path, translate, translate_to, remove_ts, dual_output)
            self.output.delete("1.0", tk.END)
            self.output.insert(tk.END, text)
            self.set_status("Done.")
        except Exception as e:
            self.set_status("Error during transcription")
            messagebox.showerror("Transcription Error", str(e))

if __name__ == "__main__":
    app = WhisperApp()
    app.mainloop()

