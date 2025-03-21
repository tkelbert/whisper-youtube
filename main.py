import os
import tkinter as tk
from tkinter import messagebox, scrolledtext, simpledialog
from glob import glob
from subprocess import run
import subprocess
import shutil

WHISPER_AUDIO_DIR = os.path.expanduser("~/whisper_audio")
os.makedirs(WHISPER_AUDIO_DIR, exist_ok=True)

# Fallback downloaders
DOWNLOADERS = ["yt-dlp", "youtube-dl", "you-get"]

def download_audio(url):
    for downloader in DOWNLOADERS:
        if shutil.which(downloader):
            try:
                output_template = os.path.join(WHISPER_AUDIO_DIR, "%(title)s.%(ext)s")
                cmd = [
                    downloader,
                    "-x",
                    "--audio-format", "mp3",
                    "-o", output_template,
                    url
                ]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    break
            except Exception:
                continue
    else:
        raise RuntimeError("No working downloader (yt-dlp, youtube-dl, you-get) found.")

    # Return newest mp3 file in the output directory
    files = sorted(glob(os.path.join(WHISPER_AUDIO_DIR, "*.mp3")), key=os.path.getmtime, reverse=True)
    return files[0] if files else None

def transcribe_audio(filepath, model, task, language):
    cmd = ["whisper", filepath, "--model", model, "--task", task, "--fp16", "False"]
    if language:
        cmd += ["--language", language]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout + "\n" + result.stderr

def run_pipeline():
    url = simpledialog.askstring("YouTube URL", "Enter the YouTube video URL:")
    if not url:
        return

    try:
        log_output("🎬 Downloading audio...")
        audio_path = download_audio(url)
        log_output(f"✔️ Audio downloaded: {os.path.basename(audio_path)}")
    except Exception as e:
        log_output(f"❌ Failed to download audio:\n{e}")
        return

    model = simpledialog.askstring("Model", "Enter Whisper model (tiny, base, small, medium, large):", initialvalue="tiny") or "tiny"
    task = simpledialog.askstring("Task", "Enter task (transcribe or translate):", initialvalue="transcribe") or "transcribe"
    language = simpledialog.askstring("Language", "Enter language code (or leave blank to detect):", initialvalue="") or ""

    log_output("🧠 Running Whisper transcription...")
    try:
        output = transcribe_audio(audio_path, model, task, language)
        log_output("✅ Whisper completed.\n\n" + output)
    except Exception as e:
        log_output(f"❌ Whisper failed:\n{e}")

def log_output(text):
    output_box.configure(state='normal')
    output_box.insert(tk.END, text + "\n")
    output_box.see(tk.END)
    output_box.configure(state='disabled')

# GUI setup
root = tk.Tk()
root.title("Whisper YouTube Transcriber")

frame = tk.Frame(root)
frame.pack(padx=10, pady=10)

run_button = tk.Button(frame, text="Start Transcription", command=run_pipeline)
run_button.pack()

output_box = scrolledtext.ScrolledText(root, width=100, height=30, wrap=tk.WORD, state='disabled')
output_box.pack(padx=10, pady=10)

root.mainloop()

