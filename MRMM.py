import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox
import json
import re
import subprocess
import glob
import difflib

def select_folder(entry):
    folder = filedialog.askdirectory()
    if folder:
        entry.delete(0, tk.END)
        entry.insert(0, folder)
        update_file_list()

SETTINGS_FILE = "settings.json"

def load_settings():
    """Load settings from the settings file."""
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    return {"auto_load_config": False, "last_config_file": None}

def save_settings():
    """Save current settings to the settings file."""
    settings = {
        "auto_load_config": auto_load_var.get(),
        "last_config_file": last_config_file.get()
    }
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f)

def find_steam_library():
    steam_path = os.path.join(os.getenv("ProgramFiles(x86)"), "Steam", "steamapps", "libraryfolders.vdf")
    if not os.path.exists(steam_path):
        return []

    libraries = []
    with open(steam_path, "r") as f:
        for line in f:
            match = re.search(r'"path"\s+"(.+)"', line)
            if match:
                libraries.append(match.group(1))

    return libraries

def find_epic_game_folder(): # Gonna be honest, I don't have the Epic version but from my research this should work
    epic_manifest_path = os.path.join(os.getenv("ProgramData"), "Epic", "EpicGamesLauncher", "Data", "Manifests")
    if not os.path.exists(epic_manifest_path):
        return None  # Epic Games manifest folder not found

    for manifest_file in glob.glob(os.path.join(epic_manifest_path, "*.item")):
        try:
            with open(manifest_file, "r") as f:
                manifest_data = json.load(f)
                install_location = manifest_data.get("InstallLocation", "")
                game_path = os.path.join(install_location, "MarvelGame", "Marvel", "Content", "Paks")
                if os.path.exists(game_path):
                    return game_path
        except (json.JSONDecodeError, KeyError):
            continue  # Skip invalid or non-target manifest files
    return None

def find_game_folder():
    # Check Steam installation first
    libraries = find_steam_library()
    for library in libraries:
        game_path = os.path.join(library, "steamapps", "common", "MarvelRivals", "MarvelGame", "Marvel", "Content", "Paks")
        if os.path.exists(game_path):
            return game_path

    # Fallback to Epic Games installation
    game_path = find_epic_game_folder()
    if game_path:
        return game_path

    return None  # Game folder not found

def set_folder2_to_mods():
    game_path = find_game_folder()
    if game_path:
        mods_path = os.path.join(game_path, "~mods")
        if not os.path.exists(mods_path):
            os.makedirs(mods_path)  # Create the ~mods folder if it doesn't exist
        folder2_entry.delete(0, tk.END)
        folder2_entry.insert(0, mods_path)

        # Automatically add/remove files based on the checkboxes
        update_files_based_on_selection(mods_path)
    else:
        messagebox.showinfo("Game Path Not Found", "Could not find the game folder automatically. Please select it manually.")
        select_manual_folder2()

def update_files_based_on_selection(folder_2):
    folder_1 = folder1_entry.get()
    if not os.path.exists(folder_1):
        return

    for file, var in checkbox_vars.items():
        file_path_1 = os.path.join(folder_1, file)
        file_path_2 = os.path.join(folder_2, file)

        if var.get():  # If the file is checked
            if not os.path.exists(file_path_2):
                shutil.copy2(file_path_1, file_path_2)  # Copy the file
        else:  # If the file is unchecked
            if os.path.exists(file_path_2):
                os.remove(file_path_2)  # Remove the file


def select_manual_folder2():
    path = filedialog.askdirectory()
    if path:
        folder2_entry.delete(0, tk.END)
        folder2_entry.insert(0, path)

        # Automatically add/remove files based on the checkboxes
        update_files_based_on_selection(path)


def select_folder1():
    path = filedialog.askdirectory()
    if path:
        folder1_entry.delete(0, tk.END)
        folder1_entry.insert(0, path)
        update_file_list()

def update_file_list():
    folder_1 = folder1_entry.get()
    folder_2 = folder2_entry.get()
    if not os.path.exists(folder_1):
        return

    # Destroy any existing checkbuttons to update the list
    for widget in file_frame.winfo_children():
        widget.destroy()

    # Add checkboxes for each file in folder 1
    for file in os.listdir(folder_1):
        file_path = os.path.join(folder_1, file)
        if os.path.isfile(file_path):
            # Initialize the variable for this checkbox based on the selected files set
            var = tk.BooleanVar(value=(file in selected_files))  # Set the initial checked state
            cb = tk.Checkbutton(
                file_frame, text=file, variable=var,
                command=lambda f=file, v=var: toggle_file(f, v.get()),
                bg="#32324C", fg="#FFFFFF",
                selectcolor="Black",  # Changes background color when checked
                activebackground="#F4D12B",  # Changes background color when clicked
            )
            cb.pack(anchor="w", padx=5, pady=2)
            checkbox_vars[file] = var  # Store the variable for later use

            # Ensure the checkbox is updated to reflect the current state (checked/unchecked)
            var.set(file in selected_files)
            cb.deselect() if not var.get() else cb.select()  # Manually set the visual state

def toggle_file(file, is_checked):
    folder_1 = folder1_entry.get()
    folder_2 = folder2_entry.get()

    file_path_1 = os.path.join(folder_1, file)
    file_path_2 = os.path.join(folder_2, file)

    if is_checked:
        if not os.path.exists(folder_2):
            os.makedirs(folder_2)
        shutil.copy2(file_path_1, file_path_2)
        selected_files.add(file)
    else:
        if os.path.exists(file_path_2):
            os.remove(file_path_2)
        selected_files.discard(file)

    # Check for compatibility issues
    check_for_compatibility_issues()

def save_config():
    config_file = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
    if not config_file:
        return

    config_data = {
        "folder1": folder1_entry.get(),
        "folder2": folder2_entry.get(),
        "selected_files": list(selected_files)
    }

    with open(config_file, "w") as f:
        json.dump(config_data, f)
    last_config_file.set(config_file)
    save_settings()
    messagebox.showinfo("Configuration Saved", "Configuration saved successfully!")

def launch_game():
    """Launch the game using Steam protocol and show a popup."""
    try:
        subprocess.run(["cmd", "/c", "start", "steam://rungameid/2767030"], shell=True)  # Launch game via Steam
        messagebox.showinfo("Game Launched", "Game Launched. Have Fun <3")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to launch game: {e}")
        
def load_config():
    config_file = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
    if not config_file:
        return

    if not os.path.exists(config_file):
        messagebox.showerror("Error", "Configuration file does not exist!")
        return

    with open(config_file, "r") as f:
        config_data = json.load(f)

    folder1_entry.delete(0, tk.END)
    folder1_entry.insert(0, config_data.get("folder1", ""))
    folder2_entry.delete(0, tk.END)
    folder2_entry.insert(0, config_data.get("folder2", ""))

    global selected_files
    selected_files = set(config_data.get("selected_files", []))

    # After loading the config, update the file list
    update_file_list()

    # Ensure ~mods folder exists and files are copied or deleted as per the config
    folder_1 = folder1_entry.get()
    folder_2 = folder2_entry.get()

    if not os.path.exists(folder_2):
        os.makedirs(folder_2)  # Ensure the target folder exists (especially ~mods folder)

    for file in os.listdir(folder_1):
        file_path_1 = os.path.join(folder_1, file)
        file_path_2 = os.path.join(folder_2, file)

        if file in selected_files:
            if not os.path.exists(file_path_2):
                shutil.copy2(file_path_1, file_path_2)  # Copy the file if missing
        else:
            if os.path.exists(file_path_2):
                os.remove(file_path_2)  # Delete the file if unchecked

    last_config_file.set(config_file)
    save_settings()

def auto_load_last_config():
    if auto_load_var.get() and last_config_file.get():
        if os.path.exists(last_config_file.get()):
            with open(last_config_file.get(), "r") as f:
                config_data = json.load(f)
            folder1_entry.delete(0, tk.END)
            folder1_entry.insert(0, config_data.get("folder1", ""))
            folder2_entry.delete(0, tk.END)
            folder2_entry.insert(0, config_data.get("folder2", ""))
            global selected_files
            selected_files = set(config_data.get("selected_files", []))
            update_file_list()

            # Ensure ~mods folder exists and files are copied or deleted as per the config
            folder_1 = folder1_entry.get()
            folder_2 = folder2_entry.get()

            if not os.path.exists(folder_2):
                os.makedirs(folder_2)  # Ensure the target folder exists (especially ~mods folder)

            for file in os.listdir(folder_1):
                file_path_1 = os.path.join(folder_1, file)
                file_path_2 = os.path.join(folder_2, file)

                if file in selected_files:
                    if not os.path.exists(file_path_2):
                        shutil.copy2(file_path_1, file_path_2)  # Copy the file if missing
                else:
                    if os.path.exists(file_path_2):
                        os.remove(file_path_2)  # Delete the file if unchecked

def filter_files(*args):
    """Filter the files displayed based on the search query."""
    query = search_var.get().lower()
    for widget in file_frame.winfo_children():
        widget.destroy()
    
    for file in os.listdir(folder1_entry.get()):
        file_path = os.path.join(folder1_entry.get(), file)
        if os.path.isfile(file_path) and query in file.lower():
            var = checkbox_vars.get(file, tk.BooleanVar(value=(file in selected_files)))
            cb = tk.Checkbutton(
                file_frame, text=file, variable=var,
                command=lambda f=file, v=var: toggle_file(f, v.get()),
                bg="#32324C", fg="#FFFFFF"
            )
            cb.pack(anchor="w")
            checkbox_vars[file] = var

def check_for_compatibility_issues():
    selected_files_list = list(selected_files)
    for i in range(len(selected_files_list)):
        for j in range(i + 1, len(selected_files_list)):
            file1 = selected_files_list[i]
            file2 = selected_files_list[j]
            # Use SequenceMatcher to check similarity
            similarity = difflib.SequenceMatcher(None, file1.lower(), file2.lower()).ratio()
            if similarity > 0.7:  # Adjust threshold as needed
                warning_label.config(text="Potential compatibility issue detected!")
                return
    warning_label.config(text="")  # Clear the warning if no issues are found


# Main UI
root = tk.Tk()
root.title("MRMM")

settings = load_settings()
last_config_file = tk.StringVar(value=settings.get("last_config_file"))
auto_load_var = tk.BooleanVar(value=settings.get("auto_load_config"))

selected_files = set()
checkbox_vars = {}

# Folder selection frame
folder_frame = tk.Frame(root, bg="#32324C")
folder_frame.pack(pady=10)

# Folder 1
tk.Label(folder_frame, text="Mod Location:", bg="#32324C", fg="#FFFFFF").grid(row=0, column=0, padx=5)
folder1_entry = tk.Entry(folder_frame, width=50)
folder1_entry.grid(row=0, column=1, padx=5)
tk.Button(folder_frame, text="Browse", command=select_folder1, bg="#F4D12B", fg="#32324C").grid(row=0, column=2, padx=5)

# Folder 2
tk.Label(folder_frame, text="Mod Folder:", bg="#32324C", fg="#FFFFFF").grid(row=1, column=0, padx=5)
folder2_entry = tk.Entry(folder_frame, width=50)
folder2_entry.grid(row=1, column=1, padx=5)
tk.Button(folder_frame, text="Auto", command=set_folder2_to_mods, bg="#F4D12B", fg="#32324C").grid(row=1, column=2, padx=5)
tk.Button(folder_frame, text="Browse", command=select_manual_folder2, bg="#F4D12B", fg="#32324C").grid(row=1, column=3, padx=5)

# Config buttons
config_frame = tk.Frame(root, bg="#32324C")
config_frame.pack(pady=10)

tk.Button(config_frame, text="Save Config", command=save_config, bg="#F4D12B", fg="#32324C").pack(side="left", padx=5)
tk.Button(config_frame, text="Load Config", command=load_config, bg="#F4D12B", fg="#32324C").pack(side="left", padx=5)

# Search bar frame
search_frame = tk.Frame(root, bg="#32324C")
search_frame.pack(pady=5, fill=tk.X)

# Center the search bar
search_frame.grid_columnconfigure(0, weight=1)  # Add weight to center the widgets
search_frame.grid_columnconfigure(2, weight=1)  # Add weight to center the widgets

# Search label
tk.Label(search_frame, text="Search:", bg="#32324C", fg="#FFFFFF").grid(row=0, column=1, padx=5)

# Search entry
search_var = tk.StringVar()
search_var.trace_add("write", filter_files)  # Bind search to filter function

search_entry = tk.Entry(search_frame, textvariable=search_var, width=30)
search_entry.grid(row=1, column=1, padx=5)

# No longer needed, keeping for reference
#file_frame = tk.Frame(root, bd=2, relief=tk.SUNKEN, bg="#32324C")
#file_frame.pack(pady=10, fill=tk.BOTH, expand=True)

# Auto-load checkbox
auto_load_frame = tk.Frame(root, bg="#32324C")
auto_load_frame.pack(pady=10)

auto_load_checkbox = tk.Checkbutton(
    auto_load_frame, text="Auto-load last config on startup",
    variable=auto_load_var, command=save_settings, bg="#32324C"
)
auto_load_checkbox.pack(anchor="w")

# Inside the main UI section where file_frame is created
file_frame_container = tk.Frame(root, bd=2, relief=tk.SUNKEN, bg="#32324C")
file_frame_container.pack(pady=10, fill=tk.BOTH, expand=True)

# Create a canvas for scrolling
canvas = tk.Canvas(file_frame_container, bg="#32324C", highlightthickness=0)
canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

# Add a vertical scrollbar
scrollbar = tk.Scrollbar(file_frame_container, orient=tk.VERTICAL, command=canvas.yview)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

# Create an inner frame for the file list, inside the canvas
file_frame = tk.Frame(canvas, bg="#32324C")

# Attach the inner frame to the canvas
file_frame_id = canvas.create_window((0, 0), window=file_frame, anchor="nw")

# Configure the canvas to scroll with the scrollbar
canvas.configure(yscrollcommand=scrollbar.set)

# Add scrolling behavior
def on_frame_configure(event):
    canvas.configure(scrollregion=canvas.bbox("all"))

def on_canvas_resize(event):
    # Adjust the file_frame width to match the canvas width
    canvas.itemconfig(file_frame_id, width=event.width)

# Bind resizing and configure events
file_frame.bind("<Configure>", on_frame_configure)
canvas.bind("<Configure>", on_canvas_resize)

# Refresh button
refresh_button = tk.Button(root, text="Refresh", command=update_file_list, bg="#F4D12B", fg="#32324C")
refresh_button.pack(pady=5)
# Launch Game
launch_button = tk.Button(root, text="Launch Game", command=launch_game, bg="#F4D12B", fg="#32324C")
launch_button.pack(pady=5)
# Warning label for compatibility issues
warning_label = tk.Label(root, text="", bg="#32324C", fg="#FF3333", font=("Arial", 10, "bold"))
warning_label.pack(pady=5)


# Bind the mouse wheel to the canvas for scrolling
def on_mouse_wheel(event):
    if canvas.yview()[0] == 0 and event.delta > 0:
        return  # Prevent scrolling up at the top
    # Adjust the canvas scroll position
    canvas.yview_scroll(-1 * (event.delta // 120), "units")

# Bind the mouse wheel events to the canvas
canvas.bind_all("<MouseWheel>", on_mouse_wheel)  # For Windows
canvas.bind_all("<Button-4>", on_mouse_wheel)    # For Linux (scroll up)
canvas.bind_all("<Button-5>", on_mouse_wheel)    # For Linux (scroll down)

# Linux compatibility requires different bindings for mouse wheel
def on_mouse_wheel_linux(event):
    if event.num == 4:  # Scroll up
        canvas.yview_scroll(-1, "units")
    elif event.num == 5:  # Scroll down
        canvas.yview_scroll(1, "units")

root.config(bg="#32324C")
root.iconbitmap("Icon.ico")

root.geometry("600x800")

# Auto-load last config on startup
auto_load_last_config()

root.mainloop()