import tkinter as tk
from tkinter import ttk, messagebox
from pymongo import MongoClient
from datetime import datetime
import re

# MongoDB Connection
MONGO_URI = "mongodb+srv://subhasmily1984:guru%40mongo@cluster0.79xnc.mongodb.net/weightbridge_to_factory"
client = MongoClient(MONGO_URI)
db = client["weightbridge_to_factory"]
collection = db["entries"]

def validate_input(value, field_type='string'):
    """
    Validate input based on field type
    """
    if not value or str(value).strip() == '':
        return False
    
    if field_type == 'string':
        return len(str(value).strip()) > 0
    
    elif field_type == 'numeric':
        try:
            float(value)
            return True
        except ValueError:
            return False
    
    elif field_type == 'truck_number':
        # Truck number validation (example format: KA01AB1234)
        truck_pattern = r'^[A-Z]{2}\d{2}[A-Z]{1,2}\d{4}$'
        return bool(re.match(truck_pattern, str(value).strip().upper()))
    
    return True

def calculate_net_weight():
    """Calculate net weight automatically with validation"""
    try:
        gross = gross_entry.get().strip()
        empty = empty_entry.get().strip()
        
        if not gross or not empty:
            net_entry.config(state="normal")
            net_entry.delete(0, tk.END)
            net_entry.config(state="readonly")
            return
        
        gross_val = float(gross)
        empty_val = float(empty)
        net = gross_val - empty_val
        
        net_entry.config(state="normal")
        net_entry.delete(0, tk.END)
        net_entry.insert(0, f"{net:.2f}")
        net_entry.config(state="readonly")
    except ValueError:
        messagebox.showerror("Invalid Input", "Please enter valid numeric values for weights")

def toggle_drying_weight():
    """Toggle the state of drying weight entry based on checkbox"""
    if drying_var.get():
        drying_weight_entry.config(state="normal")
        drying_weight_label.config(fg="black")
    else:
        drying_weight_entry.config(state="disabled")
        drying_weight_entry.delete(0, tk.END)
        drying_weight_label.config(fg="gray")

def create_enter_binding(current_entry, next_entry):
    """Create Enter key binding to move focus to next entry"""
    def on_enter(event):
        next_entry.focus_set()
        next_entry.select_range(0, tk.END)
    current_entry.bind('<Return>', on_enter)

def submit_data():
    """Insert data into MongoDB with comprehensive validation"""
    # Validate all fields
    validation_checks = [
        (sno_entry, 'string', "Serial Number"),
        (party_entry, 'string', "Party Name"),
        (truck_entry, 'truck_number', "Truck Number"),
        (bags_entry, 'numeric', "Number of Bags"),
        (gross_entry, 'numeric', "Gross Weight"),
        (empty_entry, 'numeric', "Truck Empty Weight"),
        (net_entry, 'numeric', "Net Weight")
    ]
    
    # Check for validation errors
    errors = []
    for entry, validation_type, field_name in validation_checks:
        value = entry.get().strip()
        if not validate_input(value, validation_type):
            errors.append(f"Invalid {field_name}")
    
    # Additional validation for drying weight if checkbox is checked
    if drying_var.get():
        drying_weight = drying_weight_entry.get().strip()
        if not validate_input(drying_weight, 'numeric'):
            errors.append("Invalid Drying Weight")
    
    # If there are errors, show message and return
    if errors:
        messagebox.showerror("Validation Error", "\n".join(errors))
        return
    
    try:
        data = {
            "sno": sno_entry.get().strip(),
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "party_name": party_entry.get().strip(),
            "truck_number": truck_entry.get().strip().upper(),
            "num_of_bags": bags_entry.get().strip(),
            "gross_weight": gross_entry.get().strip(),
            "truck_empty_weight": empty_entry.get().strip(),
            "net_weight": net_entry.get().strip(),
            "is_drying": drying_var.get(),
            "drying_weight": drying_weight_entry.get().strip() if drying_var.get() else None
        }
        
        collection.insert_one(data)
        messagebox.showinfo("Success", "Data added successfully!")
        
        # Clear entries after successful submission
        for entry in [sno_entry, party_entry, truck_entry, bags_entry, gross_entry, empty_entry, net_entry, drying_weight_entry]:
            entry.delete(0, tk.END)
        
        # Reset checkbox
        drying_var.set(False)
        toggle_drying_weight()
        
        # Set focus back to first entry
        sno_entry.focus_set()
        
        refresh_table()
    except Exception as e:
        messagebox.showerror("Error", str(e))

def refresh_table():
    """Fetch data from MongoDB and display in the table"""
    for row in tree.get_children():
        tree.delete(row)
    
    for doc in collection.find().sort("date", -1):  # Sort by most recent first
        drying_status = "Yes" if doc.get("is_drying") else "No"
        drying_weight = doc.get("drying_weight", "N/A")
        
        tree.insert("", "end", values=(
            doc.get("sno"), doc.get("date"), doc.get("party_name"), 
            doc.get("truck_number"), doc.get("num_of_bags"),
            doc.get("gross_weight"), doc.get("truck_empty_weight"), 
            doc.get("net_weight"), drying_status, drying_weight
        ))

# Tkinter UI Setup
root = tk.Tk()
root.title("Weightbridge Management System")
root.geometry("1400x800")

# Configure global font
FONT_FAMILY = "Segoe UI"
FONT_SIZE = 11
ENTRY_FONT = (FONT_FAMILY, FONT_SIZE)
HEADER_FONT = (FONT_FAMILY, 16, "bold")

# Main container
main_frame = tk.Frame(root, bg='white')
main_frame.pack(padx=20, pady=20, fill=tk.BOTH, expand=True)

# Header Section
header_frame = tk.Frame(main_frame, bg='navy')
header_frame.pack(fill=tk.X, pady=(0, 20))

header_label = tk.Label(header_frame, 
    text="Weightbridge Data Management", 
    font=HEADER_FONT, 
    fg="white", 
    bg='navy', 
    padx=20, 
    pady=10
)
header_label.pack()

# Content Frame
content_frame = tk.Frame(main_frame, bg='white')
content_frame.pack(padx=20, pady=10, fill=tk.BOTH, expand=True)

# Field definitions with labels and entries
fields = [
    ("S.No", sno_entry := ttk.Entry(content_frame, font=ENTRY_FONT)),
    ("Party Name", party_entry := ttk.Entry(content_frame, font=ENTRY_FONT)),
    ("Truck Number", truck_entry := ttk.Entry(content_frame, font=ENTRY_FONT)),
    ("No. of Bags", bags_entry := ttk.Entry(content_frame, font=ENTRY_FONT)),
    ("Gross Weight", gross_entry := ttk.Entry(content_frame, font=ENTRY_FONT)),
    ("Truck Empty Weight", empty_entry := ttk.Entry(content_frame, font=ENTRY_FONT)),
    ("Net Weight", net_entry := ttk.Entry(content_frame, state="readonly", font=ENTRY_FONT))
]

# Create grid layout
for i, (label_text, entry) in enumerate(fields):
    # Use consistent font for labels
    label = ttk.Label(content_frame, text=label_text, font=(FONT_FAMILY, FONT_SIZE, "bold"))
    label.grid(row=i, column=0, padx=10, pady=5, sticky="w")
    entry.grid(row=i, column=1, padx=10, pady=5, ipadx=10, ipady=3)

# Set up Enter key bindings for navigation
entry_list = [sno_entry, party_entry, truck_entry, bags_entry, gross_entry, empty_entry]
for i in range(len(entry_list) - 1):
    create_enter_binding(entry_list[i], entry_list[i+1])

# Bind final entry to trigger net weight calculation
empty_entry.bind('<Return>', lambda event: calculate_net_weight())

# Bind net weight calculation
gross_entry.bind("<KeyRelease>", lambda event: calculate_net_weight())
empty_entry.bind("<KeyRelease>", lambda event: calculate_net_weight())

# Drying status checkbox and weight entry
drying_var = tk.BooleanVar()
drying_checkbox = ttk.Checkbutton(content_frame, text="Load Gone for Drying", variable=drying_var, command=toggle_drying_weight)
drying_checkbox.grid(row=len(fields), column=0, columnspan=2, pady=10, sticky="w")

# Drying weight label and entry
drying_weight_label = tk.Label(content_frame, text="Drying Weight:", bg='white', fg="gray", font=(FONT_FAMILY, FONT_SIZE, "bold"))
drying_weight_label.grid(row=len(fields)+1, column=0, padx=10, pady=5, sticky="w")
drying_weight_entry = ttk.Entry(content_frame, state="disabled", font=ENTRY_FONT)
drying_weight_entry.grid(row=len(fields)+1, column=1, padx=10, pady=5, ipadx=10, ipady=3)

# Submit button
submit_btn = ttk.Button(content_frame, text="Submit", command=submit_data, style='Submit.TButton')
submit_btn.grid(row=len(fields)+2, column=0, columnspan=2, pady=20, ipadx=20, ipady=5)

# Table View
table_frame = tk.Frame(main_frame, bg='white')
table_frame.pack(padx=20, pady=10, fill=tk.BOTH, expand=True)

tree = ttk.Treeview(table_frame, 
    columns=("S.No", "Date", "Party Name", "Truck Number", "No. of Bags", 
             "Gross Weight", "Truck Empty Weight", "Net Weight", "Drying", "Drying Weight"), 
    show="headings"
)

# Configure Treeview columns
for col in tree["columns"]:
    tree.heading(col, text=col, anchor="center")
    tree.column(col, width=120, anchor="center")

tree.pack(expand=True, fill='both')

# Style the submit button
style = ttk.Style()
style.configure('Submit.TButton', font=(FONT_FAMILY, FONT_SIZE, 'bold'))

# Initial table refresh
refresh_table()

# Set initial focus
sno_entry.focus_set()

# Start the application
root.mainloop()