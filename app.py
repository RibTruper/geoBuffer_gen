import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import json

conversion_map = {}

with open("conversion_map.json") as f:
    data = json.load(f)

for entry in data:
    for id_val in entry["ids"]:
        conversion_map[id_val] = tuple(entry["to"])


PRESET_GEOBUFFER0 = [
    (0,0,100),(1,0,20),(2,0,15),(3,0,12),(4,0,5),(5,0,10),(6,0,80),(7,0,15),(8,0,10),(9,0,15),
    (10,0,45),(11,0,30),(12,0,90),(13,0,70),(14,0,120),(30,4,10),(44,4,20),(62,4,5),(64,4,10),
    (70,2,10),(71,2,2),(72,2,10),(73,2,15),(77,5,40),(78,5,50),(80,9,60),(81,9,60),
    (82,9,45),(83,9,45),(84,9,20),(85,9,20),(86,9,60),(87,9,40),(88,9,10),(89,9,40),(90,9,40),
    (91,9,40),(92,9,40),(93,9,40),(94,9,40),(95,9,40),(96,9,40),(97,9,40),(98,9,40),
    (99,9,40),(100,9,40),(101,8,650),(103,10,1),(104,10,2),(105,6,1),(107,10,1),
    (108,6,1),(109,6,1),(112,1,60),(114,10,50),(217,6,10),(218,6,3),(233,9,40),(364,10,1)
]

# ===== Processing Functions =====

def parse_level_file(filepath):
    """
    Reads the level file and returns a list of rows (each a list of ints)
    representing the level data. The grid width is fixed at 5.
    
    If a line starting with "data=" is found, data reading starts after that line.
    Otherwise, every nonempty CSV line is processed.
    """
    with open(filepath, 'r', encoding='utf-8') as infile:
        lines = infile.readlines()

    data_started = False
    level_rows = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.lower().startswith("data="):
            data_started = True
            continue
        if data_started or ("," in stripped):
            parts = [p for p in stripped.rstrip(',').split(',') if p != '']
            if len(parts) != 5:
                continue
            try:
                row = [int(val) for val in parts]
            except ValueError:
                continue
            level_rows.append(row)
    return level_rows

def analyze_chunks(level_rows, chunk_size, conv_map):
    """
    Uses a sliding-window approach over the level rows.
    For each possible contiguous block of 'chunk_size' rows,
    counts the occurrences of each level item (if in conv_map),
    and records the maximum count found across all windows.
    
    Returns a dict: {level_item_id: max_count}
    """
    max_counts = {item_id: 0 for item_id in conv_map}
    total_rows = len(level_rows)
    # Slide the window one row at a time.
    for start in range(0, total_rows - chunk_size + 1):
        window = level_rows[start:start+chunk_size]
        freq = {}
        for row in window:
            for item in row:
                if item in conv_map:
                    freq[item] = freq.get(item, 0) + 1
        for item_id, count in freq.items():
            if count > max_counts[item_id]:
                max_counts[item_id] = count
    return max_counts

def generate_geobuffer_list(conv_map, max_counts):
    """
    For each level item id in conv_map that appears (max count > 0),
    uses the conversion mapping (x, y) and the maximum count (z) to build
    a list of geoBuffer tuples (x, y, z). If multiple level IDs convert to the same (x, y),
    their z values are summed.
    """
    geo_dict = {}
    for level_id, (x, y) in conv_map.items():
        count = max_counts.get(level_id, 0)
        if count > 0:
            geo_dict[(x, y)] = geo_dict.get((x, y), 0) + count
    geobuffers = [(x, y, z) for (x, y), z in geo_dict.items()]
    geobuffers.sort(key=lambda tup: tup[0])
    return geobuffers

def write_output(filepath, geobuffer_list):
    """
    Writes the geoBuffer list to a text file.
    Each line is formatted as: x,y,z
    """
    try:
        with open(filepath, 'w', encoding='utf-8') as outfile:
            for x, y, z in geobuffer_list:
                outfile.write(f"{x},{y},{z}\n")
        return True
    except Exception as e:
        messagebox.showerror("Error", f"Error writing output file: {e}")
        return False

# ===== GUI Functions =====

def select_input_file():
    filename = filedialog.askopenfilename(
        title="Select Level Data File",
        filetypes=(("Text Files", "*.txt"), ("All Files", "*.*"))
    )
    if filename:
        input_file_var.set(filename)

def select_output_file():
    filename = filedialog.asksaveasfilename(
        title="Save GeoBuffer Output As",
        defaultextension=".txt",
        filetypes=(("Text Files", "*.txt"), ("All Files", "*.*"))
    )
    if filename:
        output_file_var.set(filename)

def run_processing():
    input_filepath = input_file_var.get()
    output_filepath = output_file_var.get()
    if not input_filepath:
        messagebox.showwarning("Warning", "Please select an input file.")
        return
    if not output_filepath:
        messagebox.showwarning("Warning", "Please select an output file.")
        return
    try:
        chunk_size = int(chunk_size_var.get())
    except ValueError:
        messagebox.showerror("Error", "Chunk size must be an integer.")
        return

    level_rows = parse_level_file(input_filepath)
    if not level_rows:
        messagebox.showerror("Error", "No valid level data found in the file.")
        return

    max_counts = analyze_chunks(level_rows, chunk_size, conversion_map)
    geobuffer_list = generate_geobuffer_list(conversion_map, max_counts)
    
    # If the "Add GeoBuffer0" option is enabled, prepend the preset list.
    if add_geobuffer0_var.get():
        geobuffer_list = PRESET_GEOBUFFER0 + geobuffer_list

    if not geobuffer_list:
        messagebox.showinfo("Info", "No matching item IDs were found in the level data.")
        return
    if write_output(output_filepath, geobuffer_list):
        messagebox.showinfo("Success", f"GeoBuffer information written to:\n{output_filepath}")

# ===== GUI Setup =====

root = tk.Tk()
root.title("GeoBuffer Generator")

input_file_var = tk.StringVar()
output_file_var = tk.StringVar()
chunk_size_var = tk.StringVar(value="200")  # Adjust default sliding window size as needed
add_geobuffer0_var = tk.BooleanVar(value=True)

# Roller combobox mappings for specific IDs
ROLLER_IDS = [41, 42, 43, 44, 579, 580, 587, 588]

# Load roller mappings from either `roller_mappings.json` or `roller_mapping.json`.
# Expected format: { "name": "Default", "to": [24, 4] }
roller_mappings = {}
rm_filenames = ["roller_mappings.json", "roller_mapping.json"]
rm_data = None
for fname in rm_filenames:
    try:
        with open(fname, encoding="utf-8") as rf:
            rm_data = json.load(rf)
        break
    except Exception:
        rm_data = None
        continue
if rm_data:
    for entry in rm_data:
        name = entry.get("name")
        to = entry.get("to")
        if not name or not isinstance(to, (list, tuple)):
            continue
        roller_mappings[name.strip()] = (to[0], to[1])

def apply_roller_mapping(selection):
    """Update `conversion_map` for the roller IDs based on selection."""
    mapping = roller_mappings.get(selection, roller_mappings.get("Default", (24, 4)))
    for id_val in ROLLER_IDS:
        conversion_map[id_val] = mapping

# Apply default mapping initially
apply_roller_mapping("Default")

frame = tk.Frame(root, padx=10, pady=10)
frame.pack(fill="both", expand=True)

# Input file selection
tk.Label(frame, text="Input Level File:").grid(row=0, column=0, sticky="w")
tk.Entry(frame, textvariable=input_file_var, width=50).grid(row=0, column=1, padx=5, pady=5)
tk.Button(frame, text="Browse...", command=select_input_file).grid(row=0, column=2, padx=5, pady=5)

# Output file selection
tk.Label(frame, text="Output GeoBuffer File:").grid(row=1, column=0, sticky="w")
tk.Entry(frame, textvariable=output_file_var, width=50).grid(row=1, column=1, padx=5, pady=5)
tk.Button(frame, text="Browse...", command=select_output_file).grid(row=1, column=2, padx=5, pady=5)

# Chunk size input
tk.Label(frame, text="Sliding Window Size (rows) \n[RECOMENDED: 200]:").grid(row=2, column=0, sticky="w")
tk.Entry(frame, textvariable=chunk_size_var, width=10).grid(row=2, column=1, sticky="w", padx=5, pady=5)

# Roller combobox (affects only IDs: 41,42,43,44,579,580,587,588)
tk.Label(frame, text="Roller:").grid(row=3, column=0, sticky="w")
roller_var = tk.StringVar(value="Default")
roller_cb = ttk.Combobox(frame, textvariable=roller_var, values=list(roller_mappings.keys()), state="readonly", width=30)
roller_cb.grid(row=3, column=1, sticky="w", padx=5, pady=5)
roller_cb.bind('<<ComboboxSelected>>', lambda e: apply_roller_mapping(roller_var.get()))

# Checkbox to add GeoBuffer0 preset lines
tk.Checkbutton(frame, text="Add GeoBuffer0", variable=add_geobuffer0_var).grid(row=4, column=0, columnspan=2, sticky="w", padx=5, pady=5)

# Run button
tk.Button(frame, text="Generate GeoBuffer List", command=run_processing, bg="green", fg="white")\
    .grid(row=5, column=0, columnspan=3, pady=10)

root.mainloop()
