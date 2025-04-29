import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import threading
import time
import google.generativeai as genai
import language_tool_python
from PIL import Image
import base64
import mimetypes
import cv2
import numpy as np
import io

# ---------------------------
# CONFIGURATIONS
# ---------------------------

# Gemini API Key
genai.configure(api_key="AIzaSyCOlsVZ2HZcZZmFtQ_WqGXPfXiT5OyeoxA")  # <-- Replace with your key
model = genai.GenerativeModel('gemini-1.5-pro')

# Language Tool for auto-correction
tool = language_tool_python.LanguageTool('en-US')

# Fonts
BIG_FONT = ("Helvetica", 26, "bold")
MEDIUM_FONT = ("Helvetica", 20, "bold")
NORMAL_FONT = ("Helvetica", 16)
RESULT_FONT = ("Helvetica", 16, "italic")

# ---------------------------
# HELPER FUNCTIONS
# ---------------------------

def auto_correct_text(text):
    matches = tool.check(text)
    corrected_text = language_tool_python.utils.correct(text, matches)
    return corrected_text

def ai_call(prompt):
    try:
        print(f"Sending prompt: {prompt}")  # Debugging: print the prompt being sent to the AI
        response = model.generate_content(prompt)
        print(f"Received response: {response}")  # Debugging: print the response from AI
        return response.text
    except Exception as e:
        print(f"Error occurred: {str(e)}")  # Log the error for debugging
        return f"⚠️ Error contacting AI service: {str(e)}"

def animated_loading(label, stop_event):
    loading_phases = ["Thinking", "Thinking.", "Thinking..", "Thinking..."]
    while not stop_event.is_set():
        for phase in loading_phases:
            if stop_event.is_set():
                break
            label.config(text=phase)
            time.sleep(0.25)

def threaded_ai_call(func, args, label):
    threading.Thread(target=lambda: run_ai_call(func, args, label)).start()

def run_ai_call(func, args, label):
    stop_event = threading.Event()
    threading.Thread(target=animated_loading, args=(label, stop_event), daemon=True).start()
    result = func(*args)
    stop_event.set()
    label.config(text=result)

# ---------------------------
# FEATURE FUNCTIONS
# ---------------------------

def check_sms():
    sms = sms_text.get("1.0", tk.END).strip()
    if not sms:
        messagebox.showerror("Error", "Please enter SMS text.")
        return
    fixed = auto_correct_text(sms)
    prompt = f"Check this SMS for phishing or spam:\n{fixed}\nReply Safe / Suspicious with a short reason."
    threaded_ai_call(ai_call, (prompt,), sms_result)

def check_news():
    news = news_text.get("1.0", tk.END).strip()
    if not news:
        messagebox.showerror("Error", "Please enter news text.")
        return
    fixed = auto_correct_text(news)
    prompt = f"Fact check this news:\n{fixed}\nReply Likely True / Likely Fake with a short reason."
    threaded_ai_call(ai_call, (prompt,), news_result)

def check_email():
    email = email_entry.get().strip()
    if not email:
        messagebox.showerror("Error", "Please enter an email address.")
        return
    prompt = f"Check if this email address '{email}' is suspicious. Answer Safe / Suspicious with reason."
    threaded_ai_call(ai_call, (prompt,), email_result)

def check_url():
    url = url_entry.get().strip()
    if not url:
        messagebox.showerror("Error", "Please enter a URL link.")
        return
    prompt = f"Check if the website URL '{url}' is safe or a phishing link. Answer Safe / Unsafe with reason."
    threaded_ai_call(ai_call, (prompt,), url_result)

def check_deepfake():
    filepath = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.jpeg *.png")])
    if not filepath:
        return
    try:
        loading = ttk.Progressbar(deepfake_tab, mode='indeterminate')
        loading.pack(pady=10)
        loading.start()

        image = Image.open(filepath)
        max_size = (1024, 1024)
        image.thumbnail(max_size)

        img_byte_array = io.BytesIO()
        image.save(img_byte_array, format="JPEG")
        img_bytes = img_byte_array.getvalue()

        mime_type, _ = mimetypes.guess_type(filepath)
        encoded_img = base64.b64encode(img_bytes).decode('utf-8')

        response = model.generate_content(
            contents=[
                {
                    "role": "user",
                    "parts": [
                        {"text": "Detect if this uploaded image is Real or Deepfake."},
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": encoded_img
                            }
                        },
                    ]
                }
            ]
        )

        loading.stop()
        loading.destroy()

        image_result.config(text=response.text)

    except Exception as e:
        loading.stop()
        loading.destroy()
        image_result.config(text=f"⚠️ Error analyzing image: {str(e)}")

def check_deepfake_video():
    filepath = filedialog.askopenfilename(filetypes=[("Video files", "*.mp4 *.avi *.mov")])
    if not filepath:
        return
    try:
        loading = ttk.Progressbar(video_tab, mode='indeterminate')
        loading.pack(pady=10)
        loading.start()

        cap = cv2.VideoCapture(filepath)
        ret, frame = cap.read()
        cap.release()

        if not ret:
            video_result.config(text="⚠️ Couldn't extract frame from video.")
            return

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(frame_rgb)

        max_size = (1024, 1024)
        pil_img.thumbnail(max_size)

        img_byte_array = io.BytesIO()
        pil_img.save(img_byte_array, format="JPEG")
        img_bytes = img_byte_array.getvalue()

        mime_type = "image/jpeg"
        encoded_img = base64.b64encode(img_bytes).decode('utf-8')

        response = model.generate_content(
            contents=[
                {
                    "role": "user",
                    "parts": [
                        {"text": "Detect if this frame from video is Real or Deepfake."},
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": encoded_img
                            }
                        },
                    ]
                }
            ]
        )

        loading.stop()
        loading.destroy()

        video_result.config(text=response.text)

    except Exception as e:
        loading.stop()
        loading.destroy()
        video_result.config(text=f"⚠️ Error analyzing video: {str(e)}")

def ask_chatbot():
    question = chatbot_entry.get().strip()
    if not question:
        messagebox.showerror("Error", "Please ask a question.")
        return
    fixed = auto_correct_text(question)
    prompt = f"Answer briefly:\n{fixed}"
    threaded_ai_call(ai_call, (prompt,), chatbot_result)

# ---------------------------
# ADDITIONAL FEATURES
# ---------------------------

def show_guidelines():
    guidelines_window = tk.Toplevel()
    guidelines_window.title("Cybercrime Guidelines")
    guidelines_text = """
    1. Avoid clicking on suspicious links.
    2. Always verify news sources before believing.
    3. Report suspicious emails and messages immediately.
    4. Keep your devices and software updated.
    5. Use strong, unique passwords for each account.
    """
    guidelines_label = tk.Label(guidelines_window, text=guidelines_text, font=NORMAL_FONT, justify=tk.LEFT)
    guidelines_label.pack(padx=20, pady=20)

def show_helpline():
    helpline_window = tk.Toplevel()
    helpline_window.title("Cybercrime Helplines")
    helpline_text = """
    National Cybercrime Helpline: 155260
    Delhi Police Cyber Crime: 011-27440118
    Report Phishing Emails: reportphishing@cyber.gov.in
    """
    helpline_label = tk.Label(helpline_window, text=helpline_text, font=NORMAL_FONT, justify=tk.LEFT)
    helpline_label.pack(padx=20, pady=20)

def show_digital_arrest_helper():
    digital_arrest_window = tk.Toplevel()
    digital_arrest_window.title("Digital Arrest Helper")
    arrest_text = """
-Understand laws and regulations related to digital activities
-Know your rights and responsibilities
-Seek legal advice if necessary

    """
    arrest_label = tk.Label(digital_arrest_window, text=arrest_text, font=NORMAL_FONT, justify=tk.LEFT)
    arrest_label.pack(padx=20, pady=20)

# ---------------------------
# MAIN APP UI
# ---------------------------

app = ttk.Window(themename="superhero")
app.title("🛡️ FakeFact - Cyber Safety AI")
app.geometry("1200x900")
app.configure(bg="#222")

header = tk.Label(app, text="🛡️ FakeFact", font=("Helvetica", 40, "bold"), fg="cyan", bg="#222")
header.pack(pady=20)

subheader = tk.Label(app, text="Your Ultimate Cyber Safety Companion", font=("Helvetica", 20), fg="lightblue", bg="#222")
subheader.pack()

# Buttons for Guidelines, Helpline, Digital Arrest
ttk.Button(app, text="Guidelines", command=show_guidelines, bootstyle="info-outline", width=20).pack(pady=10)
ttk.Button(app, text="Helplines", command=show_helpline, bootstyle="warning-outline", width=20).pack(pady=10)
ttk.Button(app, text="Digital Arrest Helper", command=show_digital_arrest_helper, bootstyle="danger-outline", width=20).pack(pady=10)

# Tabs
notebook = ttk.Notebook(app, bootstyle="primary")
notebook.pack(fill="both", expand=True, pady=20, padx=10)

# --- SMS CHECKER TAB ---
sms_tab = ttk.Frame(notebook)
notebook.add(sms_tab, text="📱 SMS Checker")

ttk.Label(sms_tab, text="Enter SMS Text:", font=BIG_FONT).pack(pady=10)
sms_text = tk.Text(sms_tab, height=8, width=90, font=NORMAL_FONT)
sms_text.pack(pady=10)
ttk.Button(sms_tab, text="Check SMS", command=check_sms, bootstyle="success-outline", width=20).pack(pady=10)
sms_result = ttk.Label(sms_tab, text="", font=RESULT_FONT, wraplength=800)
sms_result.pack(pady=20)

# --- NEWS CHECKER TAB ---
news_tab = ttk.Frame(notebook)
notebook.add(news_tab, text="📰 News Checker")

ttk.Label(news_tab, text="Enter News Text:", font=BIG_FONT).pack(pady=10)
news_text = tk.Text(news_tab, height=8, width=90, font=NORMAL_FONT)
news_text.pack(pady=10)
ttk.Button(news_tab, text="Check News", command=check_news, bootstyle="success-outline", width=20).pack(pady=10)
news_result = ttk.Label(news_tab, text="", font=RESULT_FONT, wraplength=800)
news_result.pack(pady=20)

# --- EMAIL CHECKER TAB ---
email_tab = ttk.Frame(notebook)
notebook.add(email_tab, text="📧 Email Checker")

ttk.Label(email_tab, text="Enter Email Address:", font=BIG_FONT).pack(pady=10)
email_entry = ttk.Entry(email_tab, font=NORMAL_FONT, width=50)
email_entry.pack(pady=10)
ttk.Button(email_tab, text="Check Email", command=check_email, bootstyle="success-outline", width=20).pack(pady=10)
email_result = ttk.Label(email_tab, text="", font=RESULT_FONT)
email_result.pack(pady=20)

# --- URL CHECKER TAB ---
url_tab = ttk.Frame(notebook)
notebook.add(url_tab, text="🔗 URL Checker")

ttk.Label(url_tab, text="Enter URL Link:", font=BIG_FONT).pack(pady=10)
url_entry = ttk.Entry(url_tab, font=NORMAL_FONT, width=50)
url_entry.pack(pady=10)
ttk.Button(url_tab, text="Check URL", command=check_url, bootstyle="success-outline", width=20).pack(pady=10)
url_result = ttk.Label(url_tab, text="", font=RESULT_FONT)
url_result.pack(pady=20)

# --- DEEPFAKE CHECKER TAB ---
deepfake_tab = ttk.Frame(notebook)
notebook.add(deepfake_tab, text="🖼️ Deepfake Checker")

ttk.Button(deepfake_tab, text="Check Image for Deepfake", command=check_deepfake, bootstyle="success-outline", width=30).pack(pady=20)
image_result = ttk.Label(deepfake_tab, text="", font=RESULT_FONT)
image_result.pack(pady=20)

# --- VIDEO DEEPFAKE CHECKER TAB ---
video_tab = ttk.Frame(notebook)
notebook.add(video_tab, text="🎬 Video Deepfake Checker")

ttk.Button(video_tab, text="Check Video Frame for Deepfake", command=check_deepfake_video, bootstyle="success-outline", width=30).pack(pady=20)
video_result = ttk.Label(video_tab, text="", font=RESULT_FONT)
video_result.pack(pady=20)

# --- CHATBOT TAB ---
chatbot_tab = ttk.Frame(notebook)
notebook.add(chatbot_tab, text="🤖 AI Chatbot")

ttk.Label(chatbot_tab, text="Ask AI Chatbot:", font=BIG_FONT).pack(pady=10)
chatbot_entry = ttk.Entry(chatbot_tab, font=NORMAL_FONT, width=80)
chatbot_entry.pack(pady=10)
ttk.Button(chatbot_tab, text="Ask", command=ask_chatbot, bootstyle="success-outline", width=20).pack(pady=10)
chatbot_result = ttk.Label(chatbot_tab, text="", font=RESULT_FONT)
chatbot_result.pack(pady=20)

# Run the app
app.mainloop()
