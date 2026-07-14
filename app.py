import os
import threading
import time
import webbrowser
import keyring
import customtkinter as ctk
import json
import re
import tkinter as tk
from tkinter import filedialog, messagebox
from openai import OpenAI, api_key

import logging

from pathlib import Path

os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    filename="logs/sonicforge.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    encoding="utf-8"
)

######################################################
APP_NAME = "Sonic Forge"
SERVICE_NAME = "SonicForge"
USERNAME = "openai_api_key"

BASE_DIR = Path(__file__).resolve().parent
PROMPT_DIR = BASE_DIR / "prompts"


def load_prompt(filename: str) -> str:
    prompt_path = PROMPT_DIR / filename

    if not prompt_path.exists():
        raise FileNotFoundError(
            f"Prompt file not found: {prompt_path}"
        )

    content = prompt_path.read_text(encoding="utf-8")

    marker = "## Prompt"

    if marker in content:
        content = content.split(marker, 1)[1]

    return content.strip()
#######################################################

class WorkshopWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)

        self.parent_app = parent

        self.conversation_messages: list[dict[str, str]] = []

        self.system_prompt = load_prompt(
            "workshop_system.md"
        )

        self.stage_prompt = load_prompt(
            "workshop_stage_concept.md"
        )

        self.title("Sonic Forge — Guided Album Workshop")
        self.geometry("900x650")
        self.minsize(760, 540)

        self.transient(parent)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(self, text="Guided Album Workshop", font=ctk.CTkFont(size=24, weight="bold") ).grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w"  )

        self.history_box = ctk.CTkTextbox(       self,
            wrap="word",
            state="disabled"
        )
        self.history_box.grid(
            row=1,
            column=0,
            padx=20,
            pady=10,
            sticky="nsew"
        )

        input_frame = ctk.CTkFrame(self)
        input_frame.grid(
            row=2,
            column=0,
            padx=20,
            pady=(10, 20),
            sticky="ew"
        )
        input_frame.grid_columnconfigure(0, weight=1)

        self.message_box = ctk.CTkTextbox(
            input_frame,
            wrap="word",
            height=100
        )
        self.message_box.grid(
            row=0,
            column=0,
            padx=(12, 6),
            pady=12,
            sticky="ew"
        )

        self.send_button = ctk.CTkButton(
            input_frame,
            text="Discuss Album",
            width=140,
            command=self.submit_message
        )
        self.send_button.grid(
            row=0,
            column=1,
            padx=(6, 12),
            pady=12,
            sticky="ns"
        )

        self.add_message(
            "Forge",
            (
                "Welcome to the Guided Album Workshop.\n\n"
                "Describe what the album should be about, how it should "
                "feel, and anything the finished album must avoid."
            )
        )

        self.message_box.focus()

    def submit_message(self):
        message = self.message_box.get(
            "1.0",
            "end"
        ).strip()

        if not message:
            messagebox.showwarning(
                "Missing Message",
                "Enter a message first.",
                parent=self
            )
            return

        api_key = self.parent_app.api_key_entry.get().strip()

        if not api_key:
            messagebox.showwarning(
                "Missing API Key",
                "Enter your OpenAI API key in the main window first.",
                parent=self
            )
            return

        self.add_message("You", message)

        self.conversation_messages.append({
        "role": "user",
        "content": message
    })

        self.message_box.delete("1.0", "end")

        self.send_button.configure(
        state="disabled",
        text="Forge is thinking..."
    )

        thread = threading.Thread(
            target=self.request_forge_response,
            args=(api_key,),
            daemon=True
        )
        thread.start()

    def request_forge_response(self, api_key: str):
        try:
            client = OpenAI(api_key=api_key)

            instructions = (
                f"{self.system_prompt}\n\n"
                f"{self.stage_prompt}"
            )

            response = client.responses.create(
                model="gpt-5.5",
                instructions=instructions,
                input=self.conversation_messages
            )

            reply = response.output_text.strip()

            if not reply:
                raise RuntimeError(
                    "Sonic Forge returned an empty response."
                )

            self.after(
                0,
                self.finish_forge_response,
                reply
            )

        except Exception as error:
            self.after(
            0,
            self.handle_forge_error,
            str(error)
        )
            
    def finish_forge_response(self, reply: str):
        self.conversation_messages.append({
            "role": "assistant",
            "content": reply
        })

        self.add_message("Forge", reply)

        self.send_button.configure(
            state="normal",
            text="Discuss Album"
        )

        self.message_box.focus()


    def handle_forge_error(self, error_message: str):
        self.send_button.configure(
            state="normal",
            text="Discuss Album"
        )

        messagebox.showerror(
            "Workshop Error",
            error_message,
            parent=self
        )

    def add_message(self, speaker, message):
        self.history_box.configure(state="normal")

        self.history_box.insert(
            "end",
            f"{speaker}:\n{message}\n\n"
        )

        self.history_box.configure(state="disabled")
        self.history_box.see("end")

class AlbumFactoryApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(APP_NAME)
        self.geometry("980x720")
        self.minsize(900, 650)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        from pathlib import Path

        documents = Path.home() / "Documents"

        self.output_folder = os.path.join(
            documents,
            "Sonic Forge",
            "Output"
        )

        os.makedirs(self.output_folder, exist_ok=True)

        self.build_ui()
        self.load_api_key()

        self.auto_open_html = True
        self.create_menu()
        self.title(APP_NAME)

    def open_html_file(self, file_path):
        try:
            webbrowser.open(
                f"file://{os.path.abspath(file_path)}"
            )
        except Exception as e:
            messagebox.showerror(
                "Unable to Open HTML",
                str(e)
            )


    def build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=10)

        # Header
        header = ctk.CTkFrame(self, corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            header,
            text="Sonic Forge",
            font=ctk.CTkFont(size=28, weight="bold")
        )
        title.grid(row=0, column=0, padx=24, pady=(20, 4), sticky="w")

        subtitle = ctk.CTkLabel(
            header,
            text="Generate complete Suno-ready concept album packages.",
            font=ctk.CTkFont(size=14)
        )
        subtitle.grid(row=1, column=0, padx=24, pady=(0, 18), sticky="w")

        # API key row
        api_frame = ctk.CTkFrame(self)
        api_frame.grid(row=1, column=0, padx=24, pady=16, sticky="ew")
        api_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(api_frame, text="OpenAI API Key").grid(row=0, column=0, padx=16, pady=16, sticky="w")

        self.api_key_entry = ctk.CTkEntry(api_frame, show="*", placeholder_text="sk-...")
        self.api_key_entry.grid(row=0, column=1, padx=8, pady=16, sticky="ew")

        ctk.CTkButton(api_frame, text="Save Key", command=self.save_api_key, width=110).grid(row=0, column=2, padx=8)
        self.test_key_button = ctk.CTkButton(
            api_frame,
            text="Test Key",
            command=self.test_api_key,
            width=110
        )
        self.test_key_button.grid(row=0, column=3, padx=(8, 16))



        # Main content
        main = ctk.CTkFrame(self)
        main.grid(row=2, column=0, padx=24, pady=(0, 16), sticky="nsew")
        main.grid_columnconfigure(0, weight=3)
        main.grid_columnconfigure(1, weight=2)
        main.grid_rowconfigure(0, weight=1)

        # Left panel
        left = ctk.CTkFrame(main)
        left.grid(row=0, column=0, padx=16, pady=16, sticky="nsew")
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(1, weight=10, minsize=50)

        ctk.CTkLabel(
            left,
            text="Album Idea",
            font=ctk.CTkFont(size=18, weight="bold")
        ).grid(row=0, column=0, padx=16, pady=(16, 8), sticky="w")

        self.album_idea_box = ctk.CTkTextbox(left, wrap="word", height=100)
        self.album_idea_box.grid(row=1, column=0, padx=16, pady=8, sticky="nsew")

        self.album_idea_box.insert(
            "1.0",
            "Example: A dark medieval metal concept album about House Dainislaav, forge, family, oaths, undead infestations, war wizards, and victory without sorrow."
        )

        controls = ctk.CTkFrame(left)
        controls.grid(row=10, column=0, padx=16, pady=16, sticky="ew")
        controls.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(controls, text="Track Count").grid(row=0, column=0, padx=12, pady=12, sticky="w")

        self.track_count_value = 10

        self.track_slider = ctk.CTkSlider(
            controls,
            from_=1,
            to=20,
            number_of_steps=19,
            command=self.update_track_estimates
        )
        self.track_slider.set(self.track_count_value)
        self.track_slider.grid(row=0, column=1, padx=12, pady=12, sticky="ew")

        self.track_count_label = ctk.CTkLabel(
            controls,
            text="10 Tracks"
        )
        self.track_count_label.grid(row=0, column=2, padx=12, pady=12, sticky="w")

        ctk.CTkButton(
            controls,
            text="Choose Output Folder",
            command=self.choose_output_folder
        ).grid(row=0, column=3, padx=12, pady=12)

        self.output_label = ctk.CTkLabel(
            left,
            text=f"Output: {self.output_folder}",
            font=ctk.CTkFont(size=12)
        )
        self.output_label.grid(row=11, column=0, padx=16, pady=(0, 16), sticky="w")
        self.track_estimate_label = ctk.CTkLabel(
            left,
            text="Estimated Time: ~2 min | Estimated Cost: ~$0.75",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.track_estimate_label.grid(row=12, column=0, padx=16, pady=(0, 16), sticky="w")

        # Right panel
        right = ctk.CTkFrame(main)
        right.grid(row=0, column=1, padx=(0, 16), pady=16, sticky="nsew")
        right.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            right,
            text="Generation",
            font=ctk.CTkFont(size=18, weight="bold")
        ).grid(row=0, column=0, padx=16, pady=(16, 8), sticky="w")

        self.generate_button = ctk.CTkButton(
            right,
            text="Generate Album",
            height=44,
            font=ctk.CTkFont(size=16, weight="bold"),
            command=self.start_album_generation
        )

        self.generate_button.grid(row=1, column=0, padx=16, pady=12, sticky="ew")

        self.workshop_button = ctk.CTkButton(right, text="Guided Album Workshop", height=40, command=self.open_workshop_placeholder)
        self.workshop_button.grid(row=2, column=0, padx=16, pady=(0, 12), sticky="ew")

        self.progress = ctk.CTkProgressBar(right)
        self.progress.set(0)
        self.progress.grid(row=3, column=0, padx=16, pady=(12, 4), sticky="ew")

        self.progress_label = ctk.CTkLabel(right, text="Progress: 0%")
        self.progress_label.grid(row=4, column=0, padx=16, pady=(0, 16), sticky="w")

        self.status_label = ctk.CTkLabel(
            right,
            text="Status: Ready",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.status_label.grid(row=5, column=0, padx=16, pady=(8, 4), sticky="w")

        self.estimated_cost_label = ctk.CTkLabel(right, text="Estimated Cost: $0.00")
        self.estimated_cost_label.grid(row=6, column=0, padx=16, pady=4, sticky="w")

        self.actual_cost_label = ctk.CTkLabel(right, text="Actual Cost: $0.00")
        self.actual_cost_label.grid(row=7, column=0, padx=16, pady=4, sticky="w")

        ctk.CTkButton(
            right,
            text="Open Output Folder",
            command=self.open_output_folder
        ).grid(row=8, column=0, padx=16, pady=(20, 8), sticky="ew")



        # Log
        self.log("Application ready.")
        self.update_track_estimates(self.track_count_value)

    
    def open_workshop_placeholder(self):
        if (
            hasattr(self, "workshop_window")
            and self.workshop_window.winfo_exists()
        ):
            self.workshop_window.focus()
            return

        self.workshop_window = WorkshopWindow(self)
    
    
    def save_api_key(self):
        api_key = self.api_key_entry.get().strip()

        if not api_key:
            messagebox.showwarning("Missing API Key", "Enter your OpenAI API key first.")
            return

        keyring.set_password(SERVICE_NAME, USERNAME, api_key)
        self.log("API key saved securely.")
        messagebox.showinfo("Saved", "API key saved securely.")

    def load_api_key(self):
        saved_key = keyring.get_password(SERVICE_NAME, USERNAME)

        if saved_key:
            self.api_key_entry.delete(0, "end")
            self.api_key_entry.insert(0, saved_key)
            self.log("Saved API key loaded.")

    def test_api_key(self):
        api_key = self.api_key_entry.get().strip()

        if not api_key:
            messagebox.showwarning("Missing API Key", "Enter your OpenAI API key first.")
            return

        def test_button_state(self, disabled=False):
            self.test_key_button.configure(state="disabled" if disabled else "normal")
        self.log("Testing OpenAI API key...")

        thread = threading.Thread(target=self.run_api_key_test, args=(api_key,))
        thread.daemon = True
        thread.start()

    def test_button_state(self, disabled=False):
        state = "disabled" if disabled else "normal"

        for child in self.winfo_children():
            pass

    def run_api_key_test(self, api_key):
        try:
            client = OpenAI(api_key=api_key)

            response = client.responses.create(
                model="gpt-5.5",
                input="Reply with only this word: connected"
            )

            result = response.output_text.strip()

            if "connected" in result.lower():
                self.after(0, self.log, "OpenAI connection successful.")
                self.after(0, messagebox.showinfo, "Success", "OpenAI API key works.")
            else:
                self.after(0, self.log, f"OpenAI responded, but unexpectedly: {result}")
                self.after(0, messagebox.showwarning, "Unexpected Response", result)

        except Exception as e:
            self.after(0, self.log, f"OpenAI API key test failed: {e}")
            self.after(0, messagebox.showerror, "OpenAI Error", str(e))

        finally:
            self.after(0, self.test_button_state, False)

    def choose_output_folder(self):
        folder = filedialog.askdirectory()

        if folder:
            self.output_folder = folder
            self.output_label.configure(text=f"Output: {self.output_folder}")
            self.log(f"Output folder changed to: {self.output_folder}")

    def open_output_folder(self):
        os.makedirs(self.output_folder, exist_ok=True)
        webbrowser.open(self.output_folder)

    def log(self, message):
        logging.info(message)

    def set_status(self, message):
        self.status_label.configure(text=f"Status: {message}")
        self.log(message)

        if hasattr(self, "modal_status_label") and self.modal_status_label.winfo_exists():
            self.modal_status_label.configure(text=message)

    def update_progress(self, value):
        percent = int(value * 100)

        self.progress.set(value)
        self.progress_label.configure(text=f"Progress: {percent}%")

        if hasattr(self, "modal_progress") and self.modal_progress.winfo_exists():
            self.modal_progress.set(value)

        if hasattr(self, "modal_percent_label") and self.modal_percent_label.winfo_exists():
            self.modal_percent_label.configure(text=f"{percent}%")

    def start_generation_demo(self):
        album_idea = self.album_idea_box.get("1.0", "end").strip()

        if not album_idea:
            messagebox.showwarning("Missing Album Idea", "Enter an album idea first.")
            return

        self.show_generation_modal()

        self.generate_button.configure(state="disabled")
        thread = threading.Thread(target=self.generation_demo)
        thread.daemon = True
        thread.start()

    def generation_demo(self):
        try:
            steps = [
                "Parsing album idea...",
                "Generating album blueprint...",
                "Preparing track list...",
                "Generating lyrics...",
                "Generating Suno style prompts...",
                "Building HTML package...",
                "Building TXT package...",
                "Building JSON package...",
                "Complete."
            ]

            total = len(steps)

            for index, step in enumerate(steps, start=1):
                self.after(0, self.set_status, step)
                self.after(0, self.update_progress, index / total)
                time.sleep(0.5)

        finally:
            self.after(0, self.close_generation_modal)
            self.after(0, self.generate_button.configure, {"state": "normal"})

    def parse_album_idea(self, client, album_idea, track_count):
        prompt = f"""
    You are an Album Creation Assistant.

    Extract the user's album idea into clean JSON.

    Return ONLY valid JSON. No markdown. No explanation.

    Required fields:
    album_title
    album_story
    genre
    track_count
    special_notes
    final_emotion

    Use this track_count unless the prompt strongly says otherwise: {track_count}

    Analyze the following topic:

    {album_idea}
    """

        response = client.responses.create(
            model="gpt-5.5",
            input=prompt
        )

        return response.output_text



    def test_album_parser(self):
        api_key = self.api_key_entry.get().strip()
        album_idea = self.album_idea_box.get("1.0", "end").strip()
        track_count = int(self.track_count_value)

        if not api_key:
            messagebox.showwarning("Missing API Key", "Enter your OpenAI API key first.")
            return

        if not album_idea:
            messagebox.showwarning("Missing Album Idea", "Enter an album idea first.")
            return

        self.log("Testing album parser...")

        try:
            client = OpenAI(api_key=api_key)
            result = self.parse_album_idea(client, album_idea, track_count)
            self.log("Album idea parsed.")
            self.log("Generating album blueprint...")

            blueprint = self.generate_album_blueprint(client, result)

            self.log("Album blueprint generated:")
            self.log(blueprint)
            self.log(result)
            messagebox.showinfo("Album Parser", "Album parser test complete. Check the log.")

        except Exception as e:
            self.log(f"Album parser failed: {e}")
            messagebox.showerror("Parser Error", str(e))

    def start_album_generation(self):
        api_key = self.api_key_entry.get().strip()
        album_idea = self.album_idea_box.get("1.0", "end").strip()
        track_count = int(self.track_count_value)

        if not api_key:
            messagebox.showwarning("Missing API Key", "Enter your OpenAI API key first.")
            return

        if not album_idea:
            messagebox.showwarning("Missing Album Idea", "Enter an album idea first.")
            return

        self.show_generation_modal()
        self.generate_button.configure(state="disabled")
        self.update_progress(0)
        self.set_status("Starting album generation...")

        thread = threading.Thread(
            target=self.run_album_generation,
            args=(api_key, album_idea, track_count)
        )
        thread.daemon = True
        thread.start()

    def run_album_generation(self, api_key, album_idea, track_count):
        try:
            client = OpenAI(api_key=api_key)

            self.after(0, self.set_status, "Parsing album idea...")
            self.after(0, self.update_progress, 0.05)

            parsed_album_text = self.parse_album_idea(client, album_idea, track_count)
            parsed_album = json.loads(parsed_album_text)

            self.after(0, self.set_status, "Generating album blueprint...")
            self.after(0, self.update_progress, 0.15)

            blueprint_text = self.generate_album_blueprint(
                client,
                json.dumps(parsed_album, indent=2)
            )

            album_blueprint = json.loads(blueprint_text)
            tracks = album_blueprint.get("tracks", [])

            if not tracks:
                raise ValueError("No tracks were generated in the album blueprint.")

            self.after(0, self.log, f"Album created: {album_blueprint.get('album_title', 'Untitled Album')}")
            self.after(0, self.log, f"Track count: {len(tracks)}")

            generated_tracks = []
            total_tracks = len(tracks)

            for index, track in enumerate(tracks, start=1):
                track_title = track.get("track_title", f"Track {index}")

                self.after(
                    0,
                    self.set_status,
                    f"Generating lyrics for Track {index} of {total_tracks}: {track_title}"
                )

                progress = 0.15 + ((index - 1) / total_tracks) * 0.75
                self.after(0, self.update_progress, progress)

                lyrics = self.generate_track_lyrics(
                    client,
                    album_blueprint,
                    track
                )

                self.after(
                    0,
                    self.set_status,
                    f"Generating Suno style for Track {index} of {total_tracks}: {track_title}"
                )

                style_addendum = self.generate_style_addendum(client, track)

                full_style = (
                    f"{album_blueprint.get('main_style_prompt', '')}\n\n"
                    f"{style_addendum}"
                ).strip()

                generated_tracks.append({
                    **track,
                    "lyrics": lyrics,
                    "style_addendum": style_addendum,
                    "suno_style": full_style,
                    "customMode": True,
                    "instrumental": False
                })

                self.after(0, self.log, f"Finished track package: {track_title}")

                progress = 0.15 + (index / total_tracks) * 0.75
                self.after(0, self.update_progress, progress)

            album_package = {
                **album_blueprint,
                "tracks": generated_tracks
            }

            self.current_album_package = album_package

            self.after(0, self.set_status, "Building HTML package...")
            self.after(0, self.update_progress, 0.97)

            html_file = self.export_album_html(album_package)

            if self.auto_open_html:
                self.after(
                    0,
                    lambda: self.open_html_file(html_file)
                )

            self.after(0, self.log, f"HTML package created: {html_file}")

            self.after(0, self.set_status, "Lyrics generation complete.")
            self.after(0, self.update_progress, 1.0)

            self.after(
                0,
                self.log,
                json.dumps(album_package, indent=2)
            )

            self.after(
                0,
                messagebox.showinfo,
                "Generation Complete",
                f"Generated HTML package for {total_tracks} tracks."
            )

        except Exception as e:
            self.after(0, self.log, f"Album generation failed: {e}")
            self.after(0, messagebox.showerror, "Generation Error", str(e))

        finally:
            self.after(0, self.close_generation_modal)
            self.after(0, self.generate_button.configure, {"state": "normal"})

    def generate_album_blueprint(self, client, album_json):
        prompt = f"""
    You are an expert concept album architect.

    Using the album brief JSON, create a complete album blueprint.

    Return ONLY valid JSON. No markdown.

    Required output fields:
    album_title
    album_summary
    main_style_prompt
    track_count
    tracks

    Each track must include:
    track_number
    track_title
    story_purpose
    emotional_goal
    suggested_bpm
    energy_level
    notes

    Album brief JSON:
    {album_json}
    """

        response = client.responses.create(
            model="gpt-5.5",
            input=prompt
        )

        return response.output_text

    def generate_track_lyrics(self, client, album_blueprint, track):
        prompt = f"""
    You are an expert concept album songwriter.

    Write one complete song for the provided track.

    Return ONLY the lyrics. No explanation. No markdown.

    Use this structure:
    Verse 1
    Pre-Chorus
    Chorus
    Verse 2
    Pre-Chorus
    Chorus
    Bridge
    Final Chorus
    Outro

    Album Information:
    {json.dumps({
            "album_title": album_blueprint.get("album_title"),
            "album_summary": album_blueprint.get("album_summary"),
            "main_style_prompt": album_blueprint.get("main_style_prompt")
        }, indent=2)}

    Track Information:
    {json.dumps(track, indent=2)}

    Return ONLY the finished lyrics.
    """

        response = client.responses.create(
            model="gpt-5.5",
            input=prompt
        )

        return response.output_text

    def show_generation_modal(self):
        self.generation_modal = ctk.CTkToplevel(self)
        self.generation_modal.title("Generating Album")
        self.generation_modal.geometry("520x260")
        self.generation_modal.resizable(False, False)

        self.generation_modal.transient(self)
        self.generation_modal.grab_set()

        self.generation_modal.protocol("WM_DELETE_WINDOW", lambda: None)

        ctk.CTkLabel(
            self.generation_modal,
            text="Generating your album package...",
            font=ctk.CTkFont(size=22, weight="bold")
        ).pack(pady=(28, 8))

        self.modal_status_label = ctk.CTkLabel(
            self.generation_modal,
            text="Starting..."
        )
        self.modal_status_label.pack(pady=8)

        self.modal_progress = ctk.CTkProgressBar(self.generation_modal, width=420)
        self.modal_progress.set(0)
        self.modal_progress.pack(pady=16)

        self.modal_percent_label = ctk.CTkLabel(
            self.generation_modal,
            text="0%"
        )
        self.modal_percent_label.pack(pady=4)

    def close_generation_modal(self):
        if hasattr(self, "generation_modal") and self.generation_modal.winfo_exists():
            self.generation_modal.grab_release()
            self.generation_modal.destroy()

    def update_track_estimates(self, value):
        track_count = int(float(value))
        self.track_count_value = track_count

        self.track_count_label.configure(
            text=f"{track_count} Track" if track_count == 1 else f"{track_count} Tracks"
        )

        estimated_seconds = 20 + (track_count * 18)
        estimated_cost = 0.15 + (track_count * 0.06)

        if estimated_seconds < 60:
            time_text = f"~{estimated_seconds} sec"
        else:
            minutes = estimated_seconds // 60
            seconds = estimated_seconds % 60

            if seconds == 0:
                time_text = f"~{minutes} min"
            else:
                time_text = f"~{minutes} min {seconds} sec"

        self.track_estimate_label.configure(
            text=f"Estimated Time: {time_text} | Estimated Cost: ~${estimated_cost:.2f}"
        )

        self.estimated_cost_label.configure(
            text=f"Estimated Cost: ~${estimated_cost:.2f}"
        )

    def generate_style_addendum(self, client, track):
        prompt = f"""
    You are a Suno style addendum generator.

    Create a concise track-specific addendum.

    Maximum length: 250 characters.

    Include:
    - BPM
    - Vocal direction
    - Instrument emphasis
    - Emotional tone

    Do not repeat the main style prompt.

    Return plain text only.

    Track Title:
    {track.get("track_title")}

    Story Purpose:
    {track.get("story_purpose")}

    Emotional Goal:
    {track.get("emotional_goal")}

    Suggested BPM:
    {track.get("suggested_bpm")}

    Energy:
    {track.get("energy_level")}

    Notes:
    {track.get("notes")}
    """

        response = client.responses.create(
            model="gpt-5.5",
            input=prompt
        )

        return response.output_text.strip()

    def safe_filename(self, name):
        name = re.sub(r'[\\/*?:"<>|]', "", name)
        name = name.replace(" ", "_")
        return name.strip("_")

    def export_album_html(self, album_package):
        album_title = album_package.get("album_title", "Untitled Album")
        safe_title = self.safe_filename(album_title)

        html = f"""<!DOCTYPE html>
    <html>
    <head>
    
        <script>
        function copyText(id) {{
            const text = document.getElementById(id).innerText;
        
            navigator.clipboard.writeText(text)
                .then(() => {{
                    alert("Copied to clipboard!");
                }})
                .catch(err => {{
                    console.error(err);
                    alert("Unable to copy.");
                }});
        }}
        </script>

    <meta charset="UTF-8">
    <title>Sonic Forge | {album_title}</title>
    <style>
    button {{
    background: #4CAF50;
    color: white;
    border: none;
    padding: 10px 16px;
    border-radius: 6px;
    cursor: pointer;
    margin-bottom: 10px;
    font-size: 14px;
}}

button:hover {{
    background: #45a049;
}}
    body {{
        font-family: Arial, sans-serif;
        line-height: 1.6;
        padding: 40px;
        max-width: 1100px;
        margin: auto;
        background: #111;
        color: #eee;
    }}
    h1 {{
        border-bottom: 2px solid #777;
        padding-bottom: 10px;
    }}
    h2 {{
        margin-top: 50px;
        color: #fff;
    }}
    pre {{
        white-space: pre-wrap;
        background: #1f1f1f;
        padding: 18px;
        border-radius: 10px;
        border: 1px solid #333;
    }}
    .track {{
        margin-bottom: 60px;
    }}
    .meta {{
        color: #bbb;
    }}
    </style>
    </head>
    <body>
    <h1>Sonic Forge | {album_title}</h1>

    <p class="meta"><strong>Album Summary:</strong> {album_package.get("album_summary", "")}</p>

    <h2>Main Style Prompt</h2>
    <pre>{album_package.get("main_style_prompt", "")}</pre>
    """

        for track in album_package.get("tracks", []):
            title = track.get("track_title", "Untitled Track")
            style = track.get("suno_style", "")
            lyrics = track.get("lyrics", "")
            style_id = f"style_{track.get('track_number')}"
            lyrics_id = f"lyrics_{track.get('track_number')}"

            html += f"""
            <div class="track">

            <h2>{track.get("track_number", "")}. {title}</h2>

            <h3>Style</h3>

            <button onclick="copyText('{style_id}')">
            Copy Style Prompt
            </button>

            <pre id="{style_id}">{style}</pre>

            <h3>Lyrics</h3>

            <button onclick="copyText('{lyrics_id}')">
            Copy Lyrics
            </button>

            <pre id="{lyrics_id}">{lyrics}</pre>

            </div>"""

        html += """
    </body>
    </html>
    """

        os.makedirs(self.output_folder, exist_ok=True)

        file_path = os.path.join(
            self.output_folder,
            f"{safe_title}_Album_Package.html"
        )

        with open(file_path, "w", encoding="utf-8") as file:
            file.write(html)

        return file_path

    def create_menu(self):
        menubar = tk.Menu(self)

        help_menu = tk.Menu(menubar, tearoff=0)

        help_menu.add_command(
            label="User Guide",
            command=self.show_user_guide
        )

        help_menu.add_separator()

        help_menu.add_command(
            label="Open Logs Folder",
            command=self.open_logs_folder
        )

        help_menu.add_separator()

        help_menu.add_command(
            label="About Sonic Forge",
            command=self.show_about
        )

        help_menu.add_command(
            label="Getting an OpenAI API Key",
            command=self.show_api_key_help
        )

        menubar.add_cascade(
            label="Help",
            menu=help_menu
        )

        self.config(menu=menubar)

    def show_about(self):
        messagebox.showinfo(
            "About Sonic Forge",
            """
    Sonic Forge
    Version 1.0

    AI-Powered Concept Album Generator

    Generate:
    • Album Concepts
    • Track Blueprints
    • Lyrics
    • Suno Style Prompts
    • HTML Album Packages

    Built with Python, CustomTkinter, and OpenAI.
    """
        )

    def show_user_guide(self):
        messagebox.showinfo(
            "Sonic Forge User Guide",
            """
    1. Enter your OpenAI API Key.
    2. Click Save Key.
    3. Enter your album concept.
    4. Select the number of tracks.
    5. Click Generate Album.
    6. Wait while Sonic Forge creates:
       - Album Blueprint
       - Lyrics
       - Suno Prompts
       - HTML Package

    The finished package will open automatically.
    """
        )



    def show_api_key_help(self):
        help_window = ctk.CTkToplevel(self)
        help_window.title("Getting an OpenAI API Key")
        help_window.geometry("700x500")

        textbox = ctk.CTkTextbox(help_window)
        textbox.pack(fill="both", expand=True, padx=20, pady=20)

        textbox.insert(
            "1.0",
            """
    To use Sonic Forge you must have an OpenAI API key.

STEP 1
Create an OpenAI account:
https://platform.openai.com

STEP 2
Add funds to your account:

Settings
→ Billing
→ Add Payment Method

STEP 3
Purchase API credits:

Billing
→ Add Funds

(Recommended starting amount: $10)

STEP 4
Create an API Key:

Dashboard
→ API Keys
→ Create New Secret Key

STEP 5
Copy the key and paste it into Sonic Forge.

IMPORTANT:

• Your ChatGPT Plus subscription does NOT include API credits.
• API usage is billed separately.
• Keep your API key private.
• Never share your API key with anyone.

Most albums generated by Sonic Forge cost well under $1.

    """
        )

        textbox.configure(state="disabled")

    def open_logs_folder(self):
        os.makedirs("logs", exist_ok=True)
        webbrowser.open(os.path.abspath("logs"))

if __name__ == "__main__":
    app = AlbumFactoryApp()
    app.mainloop()