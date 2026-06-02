import os
import threading
import webbrowser
import customtkinter as ctk
from tkinter import filedialog, messagebox
from markitdown import MarkItDown
from openai import OpenAI
import ctypes

# Enable high DPI awareness for crisp text on Windows monitors
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

# Set the modern theme for the app
ctk.set_appearance_mode("System")  
ctk.set_default_color_theme("blue")

class Doc2MDProApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Doc2MD Pro")
        self.geometry("600x580")
        self.resizable(False, False)

        self.create_widgets()

    def create_widgets(self):
        # Main Padding Frame
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True, padx=40, pady=40)

        # Title
        self.title_label = ctk.CTkLabel(
            self.main_frame, 
            text="Doc2MD Pro", 
            font=ctk.CTkFont(size=28, weight="bold")
        )
        self.title_label.pack(pady=(0, 5))

        self.subtitle = ctk.CTkLabel(
            self.main_frame, 
            text="Convert documents to Markdown instantly.",
            text_color="gray",
            font=ctk.CTkFont(size=14)
        )
        self.subtitle.pack(pady=(0, 20))

        # --- MODE SELECTION CARD ---
        self.mode_frame = ctk.CTkFrame(self.main_frame)
        self.mode_frame.pack(fill="x", pady=(0, 20), ipadx=10, ipady=10)

        self.ai_var = ctk.BooleanVar(value=False)
        self.ai_checkbox = ctk.CTkSwitch(
            self.mode_frame, 
            text="Enable AI Mode (Fixes formatting & reads images)", 
            variable=self.ai_var,
            font=ctk.CTkFont(weight="bold"),
            command=self.toggle_api_entry
        )
        self.ai_checkbox.pack(pady=(10, 10), padx=15, anchor="w")

        # API Key Input
        self.api_entry = ctk.CTkEntry(
            self.mode_frame, 
            placeholder_text="Enter Free Gemini API Key", 
            show="*",
            state="disabled"
        )
        self.api_entry.pack(fill="x", padx=15, pady=(0, 5))

        # Help Link to Google AI Studio
        self.help_link = ctk.CTkLabel(
            self.mode_frame,
            text="Get a 100% Free Gemini API Key here ↗",
            text_color="#3B82F6",
            font=ctk.CTkFont(size=11, underline=True),
            cursor="hand2"
        )
        self.help_link.bind("<Button-1>", lambda e: webbrowser.open("https://aistudio.google.com/app/apikey"))
        # ---------------------------

        # Action Button
        self.select_btn = ctk.CTkButton(
            self.main_frame,
            text="Choose Files & Convert",
            font=ctk.CTkFont(size=15, weight="bold"),
            height=50,
            command=self.select_and_convert
        )
        self.select_btn.pack(fill="x", pady=(10, 20))

        # Progress Bar (Hidden initially)
        self.progress = ctk.CTkProgressBar(self.main_frame, mode="indeterminate")
        self.progress.set(0)

        # Status Label
        self.status_label = ctk.CTkLabel(self.main_frame, text="Ready for offline conversion.", text_color="gray")
        self.status_label.pack(side="bottom", pady=(10, 0))

    def toggle_api_entry(self):
        """Enables the API key box and shows the help link when switched on."""
        if self.ai_var.get():
            self.api_entry.configure(state="normal")
            self.help_link.pack(pady=(0, 10)) 
            self.status_label.configure(text="Ready for AI-enhanced conversion.")
        else:
            self.api_entry.configure(state="disabled")
            self.help_link.pack_forget() 
            self.status_label.configure(text="Ready for offline conversion.")

    def update_status(self, text, is_loading=False):
        """Safely updates UI from the background thread."""
        self.status_label.configure(text=text)
        if is_loading:
            self.progress.pack(fill="x", pady=(0, 10), before=self.status_label)
            self.progress.start()
            self.select_btn.configure(state="disabled")
            self.ai_checkbox.configure(state="disabled")
        else:
            self.progress.stop()
            self.progress.pack_forget()
            self.select_btn.configure(state="normal")
            self.ai_checkbox.configure(state="normal")

    def select_and_convert(self):
        # FIX 1: askopenfilenames (plural) allows selecting multiple files!
        file_paths = filedialog.askopenfilenames(
            title="Select Files",
            filetypes=[("All Supported", "*.pdf *.docx *.xlsx *.pptx *.jpg *.png"), ("All Files", "*.*")]
        )

        if file_paths:
            # Run in background to prevent the UI from freezing
            threading.Thread(target=self.process_conversion, args=(file_paths,), daemon=True).start()

    def process_conversion(self, file_paths):
        use_ai = self.ai_var.get()
        api_key = self.api_entry.get().strip()

        try:
            if use_ai and not api_key:
                raise ValueError("You must enter an API key to use AI Mode.")

            # Initialize AI once for all files
            if use_ai:
                client = OpenAI(
                    api_key=api_key,
                    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
                )
                # FIX 2: Updated model to Google's newest release to prevent the 404 error
                converter = MarkItDown(llm_client=client, llm_model="gemini-2.5-flash")
            else:
                converter = MarkItDown()

            # FIX 3: Loop through all selected files
            for index, file_path in enumerate(file_paths):
                base_name = os.path.basename(file_path)
                
                # Update status bar to show which file is being processed (e.g., 1/3)
                self.update_status(f"Extracting {base_name} ({index + 1}/{len(file_paths)})...", is_loading=True)
                
                result = converter.convert(file_path)
                raw_text = result.text_content

                if use_ai:
                    self.update_status(f"AI cleaning {base_name} ({index + 1}/{len(file_paths)})...", is_loading=True)
                    response = client.chat.completions.create(
                        model="gemini-2.5-flash", # FIX 2: Updated here as well
                        messages=[
                            {"role": "system", "content": "You are an expert document editor. The user will provide raw Markdown converted from a PDF/Doc. Your job is to fix broken formatting, remove odd squares or OCR garbage characters, structure the headers properly, and return ONLY the clean Markdown text. Do not add any conversational filler."},
                            {"role": "user", "content": raw_text}
                        ]
                    )
                    
                    final_text = response.choices[0].message.content
                    if final_text.startswith("```markdown"):
                        final_text = final_text[11:-3].strip()
                else:
                    final_text = raw_text

                # Save the file
                file_dir, _ = os.path.split(file_path)
                raw_name, _ = os.path.splitext(base_name)
                output_path = os.path.join(file_dir, f"{raw_name}.md")

                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(final_text)

            self.update_status("All conversions complete!")
            messagebox.showinfo("Success", f"Successfully converted {len(file_paths)} file(s)!")

        except Exception as e:
            self.update_status("Error occurred.")
            messagebox.showerror("Error", f"Failed to convert:\n{str(e)}")

if __name__ == "__main__":
    app = Doc2MDProApp()
    app.mainloop()