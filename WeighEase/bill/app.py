import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pymongo import MongoClient
import pandas as pd
from datetime import datetime, timedelta
from tkcalendar import DateEntry
import os
import subprocess
import tempfile
import platform

class WeightbridgeBillingSystem:
    def __init__(self, root):
        self.root = root
        self.root.geometry("1200x800+0+40")
        self.root.title("Weightbridge Billing System")
        
        # Define colors for styling
        self.primary_color = "#2c3e50"
        self.secondary_color = "#3498db"
        self.success_color = "#27ae60"
        self.danger_color = "#e74c3c"
        
        self.root.configure(bg="#f5f6fa")
        self.style = ttk.Style()
        self.set_style()
        
        # ----- MongoDB Connection -----
        try:
            MONGO_URI = "mongodb+srv://subhasmily1984:guru%40mongo@cluster0.79xnc.mongodb.net/weightbridge_to_factory"
            self.client = MongoClient(MONGO_URI)
            self.db = self.client["weightbridge_to_factory"]
            self.collection = self.db["entries"]
        except Exception as e:
            messagebox.showerror("Database Error", f"Could not connect to the database:\n{str(e)}")
            self.root.destroy()
            return

        # Build main interface
        self.create_interface()
        self.load_all_data()

    @staticmethod
    def safe_float(value, default=0.0):
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def set_style(self):
        base_font = ("Segoe UI", 14)
        heading_font = ("Segoe UI Semibold", 16)
        button_font = ("Segoe UI", 14)
        
        self.style.theme_use("clam")
        self.style.configure(".", font=base_font)
        self.style.configure("TFrame", background="#f5f6fa")
        self.style.configure("TLabel", background="#f5f6fa", foreground=self.primary_color, font=base_font)
        self.style.configure("TButton", background=self.secondary_color, foreground="white", font=button_font,
                            borderwidth=1, focusthickness=3, focuscolor=self.secondary_color)
        self.style.map("TButton",
                      background=[("active", self.primary_color), ("disabled", "#bdc3c7")],
                      foreground=[("disabled", "#7f8c8d")])
        self.style.configure("Treeview", font=base_font, rowheight=30)
        self.style.configure("Treeview.Heading", font=heading_font, background=self.primary_color, 
                            foreground="white", relief="flat")
        self.style.map("Treeview.Heading",
                      background=[("active", self.secondary_color)])
        self.style.configure("Accent.TButton", background=self.success_color, foreground="white", font=button_font)

    def create_interface(self):
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # Create filter and controls
        self.create_filters_frame(main_frame)
        
        # Create data table
        self.create_data_table(main_frame)
        
        # Create billing panel
        self.create_billing_panel(main_frame)
        
        # Status bar
        self.status = ttk.Label(self.root, text="Ready", background=self.primary_color, 
                               foreground="white", anchor=tk.W, padding=10, font=("Segoe UI", 14))
        self.status.pack(side=tk.BOTTOM, fill=tk.X)

    def create_filters_frame(self, parent):
        filters_frame = ttk.LabelFrame(parent, text="Filters & Controls", padding=10)
        filters_frame.pack(fill=tk.X, pady=5, padx=10)
        
        # Date filters
        date_frame = ttk.Frame(filters_frame)
        date_frame.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(date_frame, text="From:").pack(side=tk.LEFT)
        self.from_date_entry = DateEntry(date_frame, width=12, date_pattern='yyyy-mm-dd')
        self.from_date_entry.set_date(datetime.now() - timedelta(days=30))
        self.from_date_entry.pack(side=tk.LEFT, padx=5)
        # Bind the date change event to apply filters automatically
        self.from_date_entry.bind("<<DateEntrySelected>>", lambda e: self.apply_filters())
        
        ttk.Label(date_frame, text="To:").pack(side=tk.LEFT)
        self.to_date_entry = DateEntry(date_frame, width=12, date_pattern='yyyy-mm-dd')
        self.to_date_entry.set_date(datetime.now())
        self.to_date_entry.pack(side=tk.LEFT, padx=5)
        # Bind the date change event to apply filters automatically
        self.to_date_entry.bind("<<DateEntrySelected>>", lambda e: self.apply_filters())
        
        # Party filter
        party_frame = ttk.Frame(filters_frame)
        party_frame.pack(side=tk.LEFT, padx=10)
        
        ttk.Label(party_frame, text="Party:").pack(side=tk.LEFT)
        self.party_var = tk.StringVar()
        self.party_entry = ttk.Entry(party_frame, textvariable=self.party_var, width=20)
        self.party_entry.pack(side=tk.LEFT, padx=5)
        # Bind key release event to apply filters automatically with a delay
        self.party_entry.bind("<KeyRelease>", self.schedule_filter)
        
        # Buttons (only Reset and Export, no Apply button)
        btn_frame = ttk.Frame(filters_frame)
        btn_frame.pack(side=tk.RIGHT)
        
        ttk.Button(btn_frame, text="Reset", command=self.load_all_data).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Export", command=lambda: self.export_data("xlsx")).pack(side=tk.LEFT, padx=5)
        
        # Variable to track if a filter application is scheduled
        self.filter_scheduled = False

    def schedule_filter(self, event=None):
        """Schedule filter application with a small delay to avoid rapid filtering during typing"""
        if self.filter_scheduled:
            self.root.after_cancel(self.filter_scheduled)
        
        # Schedule the filter to be applied after 500ms
        self.filter_scheduled = self.root.after(500, self.apply_filters)

    def create_data_table(self, parent):
        table_frame = ttk.LabelFrame(parent, text="Weightbridge Records", padding=(20, 15))
        table_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        # Added Date column
        columns = ("S.No", "Date", "Party Name", "Net Weight", "Rate", "Total Amount")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")
        
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        # Adjusted column widths to accommodate the Date column
        col_widths = [80, 120, 230, 150, 150, 150]
        for col, width in zip(columns, col_widths):
            self.tree.heading(col, text=col, anchor=tk.CENTER,
                             command=lambda c=col: self.sort_column(c, False))
            self.tree.column(col, width=width, anchor=tk.CENTER, minwidth=50)

        self.tree.tag_configure('evenrow', background='#f8f9fa')
        self.tree.tag_configure('oddrow', background='white')

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)
        
        # Bind select event
        self.tree.bind('<<TreeviewSelect>>', self.on_record_select)

    def create_billing_panel(self, parent):
        billing_frame = ttk.LabelFrame(parent, text="Billing Information", padding=(20, 15))
        billing_frame.pack(fill=tk.X, pady=10)
        
        # Left column - Bill details
        details_frame = ttk.Frame(billing_frame)
        details_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # S.No
        ttk.Label(details_frame, text="S.No:").grid(row=0, column=0, padx=10, pady=5, sticky=tk.W)
        self.sno_var = tk.StringVar()
        ttk.Entry(details_frame, textvariable=self.sno_var, width=10, state="readonly").grid(row=0, column=1, padx=10, pady=5, sticky=tk.W)
        
        # Date
        ttk.Label(details_frame, text="Date:").grid(row=1, column=0, padx=10, pady=5, sticky=tk.W)
        self.bill_date_var = tk.StringVar()
        ttk.Entry(details_frame, textvariable=self.bill_date_var, width=15, state="readonly").grid(row=1, column=1, padx=10, pady=5, sticky=tk.W)
        
        # Party Name
        ttk.Label(details_frame, text="Party Name:").grid(row=2, column=0, padx=10, pady=5, sticky=tk.W)
        self.bill_party_var = tk.StringVar()
        ttk.Entry(details_frame, textvariable=self.bill_party_var, width=30, state="readonly").grid(row=2, column=1, padx=10, pady=5, sticky=tk.W)
        
        # Net Weight
        ttk.Label(details_frame, text="Net Weight (kg):").grid(row=3, column=0, padx=10, pady=5, sticky=tk.W)
        self.net_weight_var = tk.StringVar()
        ttk.Entry(details_frame, textvariable=self.net_weight_var, width=15, state="readonly").grid(row=3, column=1, padx=10, pady=5, sticky=tk.W)
        
        # Right column - Rate and total calculation
        calc_frame = ttk.Frame(billing_frame)
        calc_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Rate per kg
        ttk.Label(calc_frame, text="Rate per kg (Rs):").grid(row=0, column=0, padx=10, pady=5, sticky=tk.W)
        self.rate_var = tk.StringVar()
        ttk.Entry(calc_frame, textvariable=self.rate_var, width=15).grid(row=0, column=1, padx=10, pady=5, sticky=tk.W)
        
        # Calculate button
        ttk.Button(calc_frame, text="Calculate", command=self.calculate_total, style="Accent.TButton").grid(row=0, column=2, padx=10, pady=5)
        
        # Total Amount
        ttk.Label(calc_frame, text="Total Amount (Rs):").grid(row=1, column=0, padx=10, pady=5, sticky=tk.W)
        self.total_var = tk.StringVar()
        ttk.Entry(calc_frame, textvariable=self.total_var, width=15, state="readonly").grid(row=1, column=1, padx=10, pady=5, sticky=tk.W)
        
        # Add a frame for bill actions
        actions_frame = ttk.Frame(billing_frame)
        actions_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)
        
        # Print and Download Buttons
        ttk.Button(actions_frame, text="Print Bill", command=self.print_bill, style="TButton").pack(side=tk.LEFT, padx=10)
        ttk.Button(actions_frame, text="Send to Printer", command=self.send_to_printer, style="TButton").pack(side=tk.LEFT, padx=10)
        ttk.Button(actions_frame, text="Download PDF", command=self.download_pdf, style="TButton").pack(side=tk.LEFT, padx=10)

    def load_all_data(self):
        """Reset filters and load all data"""
        # Clear the filter fields
        self.party_var.set("")
        self.from_date_entry.set_date(datetime.now() - timedelta(days=30))
        self.to_date_entry.set_date(datetime.now())
        
        self.status.config(text="Loading data...", foreground=self.primary_color)
        self.tree.delete(*self.tree.get_children())
        try:
            for i, doc in enumerate(self.collection.find({}, {"sno": 1, "party_name": 1, "net_weight": 1, "date": 1}).sort("sno", -1)):
                tag = 'evenrow' if i % 2 == 0 else 'oddrow'
                net_weight = self.safe_float(doc.get("net_weight"))
                
                # Format date or use a default
                date_str = doc.get("date", "")
                if not date_str:
                    # If no date in DB, use current date as fallback
                    date_str = datetime.now().strftime("%Y-%m-%d")
                elif isinstance(date_str, datetime):
                    # If date is already a datetime object
                    date_str = date_str.strftime("%Y-%m-%d")
                
                self.tree.insert("", "end", values=(
                    doc.get("sno"),
                    date_str,
                    doc.get("party_name"),
                    f'{net_weight:.2f}',
                    "",  # Rate column (empty initially)
                    ""   # Total Amount column (empty initially)
                ), tags=(tag,))
            self.status.config(text=f"Loaded {len(self.tree.get_children())} records", foreground=self.primary_color)
        except Exception as e:
            messagebox.showerror("Data Error", f"Error fetching data: {str(e)}")
            self.status.config(text="Error loading data", foreground=self.danger_color)

    def apply_filters(self):
        """Apply filters to the data - called automatically when filter controls change"""
        query = {}
        
        # Date filter
        try:
            from_date = self.from_date_entry.get_date()
            to_date = self.to_date_entry.get_date() + timedelta(days=1)
            query["date"] = {"$gte": from_date.strftime("%Y-%m-%d"), "$lt": to_date.strftime("%Y-%m-%d")}
        except:
            pass  # Skip date filter if there's an error
        
        # Party name filter
        if self.party_var.get():
            query['party_name'] = {'$regex': self.party_var.get(), '$options': 'i'}
        
        self.load_filtered_data(query)

    def load_filtered_data(self, query):
        self.status.config(text="Applying filters...", foreground=self.primary_color)
        self.tree.delete(*self.tree.get_children())
        try:
            for i, doc in enumerate(self.collection.find(query, {"sno": 1, "party_name": 1, "net_weight": 1, "date": 1}).sort("sno", -1)):
                tag = 'evenrow' if i % 2 == 0 else 'oddrow'
                net_weight = self.safe_float(doc.get("net_weight"))
                
                # Format date or use a default
                date_str = doc.get("date", "")
                if not date_str:
                    # If no date in DB, use current date as fallback
                    date_str = datetime.now().strftime("%Y-%m-%d")
                elif isinstance(date_str, datetime):
                    # If date is already a datetime object
                    date_str = date_str.strftime("%Y-%m-%d")
                
                self.tree.insert("", "end", values=(
                    doc.get("sno"),
                    date_str,
                    doc.get("party_name"),
                    f'{net_weight:.2f}',
                    "",  # Rate column (empty initially)
                    ""   # Total Amount column (empty initially)
                ), tags=(tag,))
            self.status.config(text=f"Loaded {len(self.tree.get_children())} filtered records", foreground=self.primary_color)
        except Exception as e:
            messagebox.showerror("Filter Error", f"Error applying filters: {str(e)}")
            self.status.config(text="Error applying filters", foreground=self.danger_color)

    def on_record_select(self, event):
        selected_item = self.tree.selection()
        if not selected_item:
            return
            
        # Get values from the selected row
        values = self.tree.item(selected_item[0], 'values')
        if len(values) >= 4:  # Updated to account for the date column
            self.sno_var.set(values[0])
            self.bill_date_var.set(values[1])  # Set the date value
            self.bill_party_var.set(values[2])
            self.net_weight_var.set(values[3])
            
            # Clear rate and total
            self.rate_var.set("")
            self.total_var.set("")

    def calculate_total(self):
        rate_str = self.rate_var.get().strip()
        if not rate_str:
            messagebox.showwarning("Rate Error", "Please enter a rate per kg.")
            return

        try:
            rate = float(rate_str)
        except ValueError:
            messagebox.showerror("Rate Error", "Invalid rate. Please enter a numeric value.")
            return
            
        net_weight_str = self.net_weight_var.get().strip()
        if not net_weight_str:
            messagebox.showwarning("Selection Error", "Please select a record first.")
            return
            
        try:
            net_weight = self.safe_float(net_weight_str)
            total_amount = rate * net_weight
            
            # Update the UI
            self.total_var.set(f"{total_amount:,.2f}")
            
            # Update the treeview
            selected_item = self.tree.selection()
            if selected_item:
                current_values = list(self.tree.item(selected_item[0], 'values'))
                current_values[4] = f"{rate:.2f}"  # Updated index for rate
                current_values[5] = f"{total_amount:,.2f}"  # Updated index for total amount
                self.tree.item(selected_item[0], values=current_values)
                
            self.status.config(
                text=f"Calculated Amount: Rs.{total_amount:,.2f} | Rate: Rs.{rate}/kg | Net Weight: {net_weight} kg", 
                foreground=self.primary_color
            )
        except Exception as e:
            messagebox.showerror("Calculation Error", f"Error in calculation: {str(e)}")

    def generate_bill_content(self):
        """Generate bill content as a string, replacing ₹ with Rs."""
        if not self.sno_var.get() or not self.total_var.get():
            messagebox.showwarning("Bill Error", "Please select a record and calculate the total amount first.")
            return None
            
        if not self.rate_var.get():
            messagebox.showwarning("Bill Error", "Please calculate the total amount first.")
            return None
            
        # Get bill details
        sno = self.sno_var.get()
        date = self.bill_date_var.get()
        party_name = self.bill_party_var.get()
        net_weight = self.net_weight_var.get()
        rate = self.rate_var.get()
        total = self.total_var.get()
        
        # Create bill content using "Rs." instead of ₹ symbol
        bill_content = f"""
=========================================
            WEIGHTBRIDGE BILL
=========================================

Bill No: {sno}                Date: {datetime.now().strftime('%d-%m-%Y')}
Record Date: {date}

Party Name: {party_name}

Net Weight: {net_weight} kg
Rate per kg: Rs.{rate}

Total Amount: Rs.{total}

=========================================
            Thank You
=========================================
"""
        return bill_content, sno

    def print_bill(self):
        """Save bill as a text file"""
        bill_data = self.generate_bill_content()
        if not bill_data:
            return
            
        bill_content, sno = bill_data
        
        try:
            # Ask for save location
            file_path = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
                initialfile=f"Bill_{sno}_{datetime.now().strftime('%Y%m%d')}"
            )
            
            if file_path:
                # Use UTF-8 encoding to avoid character encoding issues
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(bill_content)
                
                self.status.config(
                    text=f"Bill saved successfully to {file_path}",
                    foreground=self.success_color
                )
                messagebox.showinfo("Save Successful", f"Bill successfully saved to:\n{file_path}")
                
                # Open the file
                self.open_file(file_path)
                
        except Exception as e:
            messagebox.showerror("Save Error", f"Could not save bill:\n{str(e)}")
            self.status.config(text="Bill saving failed", foreground=self.danger_color)

    def send_to_printer(self):
        """Send bill directly to printer"""
        bill_data = self.generate_bill_content()
        if not bill_data:
            return
            
        bill_content, sno = bill_data
        
        try:
            # Create a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.txt', mode='w', encoding='utf-8') as temp_file:
                temp_file.write(bill_content)
                temp_file_path = temp_file.name
            
            # Print the file
            if platform.system() == 'Windows':
                os.startfile(temp_file_path, 'print')
                self.status.config(text="Bill sent to printer", foreground=self.success_color)
                messagebox.showinfo("Print", "Bill has been sent to the default printer")
            else:
                # For Unix/Linux/MacOS
                subprocess.run(['lpr', temp_file_path])
                self.status.config(text="Bill sent to printer", foreground=self.success_color)
                messagebox.showinfo("Print", "Bill has been sent to the default printer")
            
            # Schedule file deletion after printing (might not work reliably on Windows)
            self.root.after(10000, lambda: os.unlink(temp_file_path) if os.path.exists(temp_file_path) else None)
            
        except Exception as e:
            messagebox.showerror("Print Error", f"Could not print bill:\n{str(e)}")
            self.status.config(text="Bill printing failed", foreground=self.danger_color)

    def download_pdf(self):
        """Generate and download a PDF version of the bill"""
        try:
            # First check if we have the required modules
            try:
                from reportlab.lib.pagesizes import letter
                from reportlab.pdfgen import canvas
                from reportlab.lib.units import inch
            except ImportError:
                messagebox.showinfo("Module Required", 
                    "The ReportLab module is required for PDF generation.\n"
                    "Please install it using: pip install reportlab")
                return
                
            bill_data = self.generate_bill_content()
            if not bill_data:
                return
                
            bill_content, sno = bill_data
            
            # Ask for save location
            file_path = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF Files", "*.pdf"), ("All Files", "*.*")],
                initialfile=f"Bill_{sno}_{datetime.now().strftime('%Y%m%d')}"
            )
            
            if not file_path:
                return
                
            # Create PDF
            c = canvas.Canvas(file_path, pagesize=letter)
            width, height = letter
            
            # Set font and size
            c.setFont("Helvetica-Bold", 16)
            c.drawCentredString(width/2, height - 1*inch, "WEIGHTBRIDGE BILL")
            
            c.setFont("Helvetica", 12)
            # Draw horizontal line
            c.line(1*inch, height - 1.2*inch, width - 1*inch, height - 1.2*inch)
            
            # Bill details
            y_position = height - 1.5*inch
            lines = bill_content.strip().split('\n')
            
            # Skip the title and separator lines
            start_line = 3  # Skip the first 3 lines (empty, title, separator)
            
            c.setFont("Helvetica", 12)
            for line in lines[start_line:]:
                if "========" not in line:  # Skip separator lines
                    if "Bill No:" in line or "Party Name:" in line or "Total Amount:" in line or "Record Date:" in line:
                        c.setFont("Helvetica-Bold", 12)
                    else:
                        c.setFont("Helvetica", 12)
                        
                    if line.strip():  # Only draw non-empty lines
                        c.drawString(1*inch, y_position, line)
                        y_position -= 0.3*inch
            
            # Draw horizontal line at the bottom
            c.line(1*inch, 1.5*inch, width - 1*inch, 1.5*inch)
            
            # Thank you note
            c.setFont("Helvetica-Bold", 12)
            c.drawCentredString(width/2, 1.2*inch, "Thank You")
            
            c.save()
            
            self.status.config(
                text=f"PDF generated successfully at {file_path}",
                foreground=self.success_color
            )
            messagebox.showinfo("PDF Created", f"PDF bill has been created at:\n{file_path}")
            
            # Open the PDF
            self.open_file(file_path)
            
        except Exception as e:
            messagebox.showerror("PDF Error", f"Could not create PDF:\n{str(e)}")
            self.status.config(text="PDF creation failed", foreground=self.danger_color)

    def open_file(self, file_path):
        """Open a file with the default application"""
        try:
            if platform.system() == 'Windows':
                os.startfile(file_path)
            elif platform.system() == 'Darwin':  # macOS
                subprocess.run(['open', file_path])
            else:  # Linux and other Unix-like
                subprocess.run(['xdg-open', file_path])
        except Exception as e:
            messagebox.showinfo("File Saved", f"File has been saved at:\n{file_path}")

    def sort_column(self, col, reverse):
        try:
            l = [(self.tree.set(k, col), k) for k in self.tree.get_children('')]
            try:
                l.sort(key=lambda t: float(t[0]), reverse=reverse)
            except ValueError:
                l.sort(key=lambda t: t[0], reverse=reverse)
            for index, (val, k) in enumerate(l):
                self.tree.move(k, '', index)
            self.tree.heading(col, command=lambda: self.sort_column(col, not reverse))
        except Exception as e:
            messagebox.showerror("Sort Error", f"Error sorting column '{col}': {str(e)}")

    def export_data(self, format_type):
        try:
            data = []
            for item_id in self.tree.get_children():
                values = self.tree.item(item_id, 'values')
                data.append({
                    "S.No": values[0],
                    "Date": values[1],       # Added Date field
                    "Party Name": values[2],
                    "Net Weight": values[3],
                    "Rate": values[4] if len(values) > 4 and values[4] else "",
                    "Total Amount": values[5] if len(values) > 5 and values[5] else ""
                })
                
            if not data:
                messagebox.showinfo("No Data", "No records available to export.")
                return

            df = pd.DataFrame(data)
            
            file_path = filedialog.asksaveasfilename(
                defaultextension=f".{format_type}",
                filetypes=[("Excel Files", "*.xlsx")]
            )

            if file_path:
                df.to_excel(file_path, index=False)
                self.status.config(
                    text=f"Data exported successfully to {file_path}",
                    foreground=self.success_color
                )
                messagebox.showinfo("Export Successful", f"Data successfully exported to:\n{file_path}")

        except Exception as e:
            messagebox.showerror("Export Error", f"Could not export data:\n{str(e)}")
            self.status.config(text="Export failed", foreground=self.danger_color)

def main():
    root = tk.Tk()
    app = WeightbridgeBillingSystem(root)
    root.mainloop()

if __name__ == "__main__":
    main()