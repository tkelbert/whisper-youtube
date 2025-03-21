import os
import subprocess
import tkinter as tk
from tkinter import messagebox
from threading import Thread
import whisper

def update_status(msg):
    status_text.set(msg)
    root.update()

def download_video(url, output_dir):
    tools = ["yt-dlp", "youtube-dl"]
    for tool in tools:
        try:
            update_status(f"Trying {tool}...")
            filename_template = os.path.join(output_dir, "%(title)s.%(ext)s")
            command = [tool, "-x", "--audio-format", "mp3", "-o", filename_template, url]
            subprocess.run(command, check=True)
            files = [f for f in os.listdir(output_dir) if f.endswith(".mp3")]
            if files:
                return os.path.join(output_dir, files[-1])
        except Exception:
            continue
    raise Exception("All downloaders failed.")

def transcribe_audio(file_path, model_size, task, translate_to):
    update_status(f"Loading Whisper model '{model_size}'...")
    model = whisper.load_model(model_size)

    args = {"fp16": False, "task": task}
    if task == "translate" and translate_to:
        args["language"] = "en"

    update_status("Transcribing...")
    result = model.transcribe(file_path, **args)

    output_path = file_path + ".txt"
    with open(output_path, "w") as f:
        f.write(result["text"])

    update_status(f"Saved to {output_path}")
    messagebox.showinfo("Done", f"Transcription saved to:\n{output_path}")

def start_process():
    url = url_entry.get()
    if not url:
        messagebox.showerror("Error", "You must enter a YouTube URL.")
        return

    model_size = model_entry.get() or "tiny"
    task = task_var.get()
    translate_to = translate_to_entry.get() if task == "translate" else None

    def thread_target():
        try:
            file_path = download_video(url, output_dir)
            update_status(f"Downloaded to {file_path}")
            transcribe_audio(file_path, model_size, task, translate_to)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    Thread(target=thread_target).start()

# GUI Setup
root = tk.Tk()
root.title("Whisper YouTube Transcriber")

output_dir = os.path.expanduser("~/whisper_audio")
os.makedirs(output_dir, exist_ok=True)

tk.Label(root, text="YouTube URL:").pack()
url_entry = tk.Entry(root, width=60)
url_entry.pack()

tk.Label(root, text="Whisper model (default: tiny):").pack()
model_entry = tk.Entry(root, width=20)
model_entry.pack()

tk.Label(root, text="Task:").pack()
task_var = tk.StringVar(value="transcribe")
tk.Radiobutton(root, text="Transcribe", variable=task_var, value="transcribe").pack(anchor="w")
tk.Radiobutton(root, text="Translate", variable=task_var, value="translate").pack(anchor="w")

tk.Label(root, text="Translate to (if translating):").pack()
translate_to_entry = tk.Entry(root, width=10)
translate_to_entry.pack()

tk.Button(root, text="Start", command=start_process).pack(pady=10)

status_text = tk.StringVar()
tk.Label(root, textvariable=status_text, fg="blue").pack()

root.mainloop()

