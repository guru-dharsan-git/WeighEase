import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pymongo import MongoClient
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import seaborn as sns
from tkcalendar import DateEntry

# Set seaborn style for better looking plots
sns.set(style="whitegrid", palette="pastel")

# ----- Custom Menu Bar as a Frame -----
class CustomMenuBar(tk.Frame):
    def __init__(self, master, controller, **kwargs):
        # Use the primary color for background (hardcoded here)
        super().__init__(master, bg="#2c3e50", **kwargs)
        self.controller = controller
        
        # File Menubutton (left aligned)
        self.file_mb = tk.Menubutton(
            self, text="File", font=("Segoe UI", 16, "bold"),
            fg="white", bg="#2c3e50", activebackground="#3498db",
            activeforeground="white", bd=0, relief="flat"
        )
        self.file_menu = tk.Menu(self.file_mb, tearoff=0, font=("Segoe UI", 14))
        self.file_menu.add_command(label="Export as CSV", command=lambda: controller.export_data("csv"))
        self.file_menu.add_command(label="Export as XLSX", command=lambda: controller.export_data("xlsx"))
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=controller.root.quit)
        self.file_mb.config(menu=self.file_menu)
        self.file_mb.pack(side="left", padx=15, pady=5)
        
        # Spacer
        spacer = tk.Label(self, text="", bg="#2c3e50")
        spacer.pack(side="left", expand=True)
        
        # Help Menubutton (right aligned)
        self.help_mb = tk.Menubutton(
            self, text="Help", font=("Segoe UI", 16, "bold"),
            fg="white", bg="#2c3e50", activebackground="#3498db",
            activeforeground="white", bd=0, relief="flat"
        )
        self.help_menu = tk.Menu(self.help_mb, tearoff=0, font=("Segoe UI", 14))
        self.help_menu.add_command(label="About", command=controller.show_about)
        self.help_mb.config(menu=self.help_menu)
        self.help_mb.pack(side="right", padx=15, pady=5)

# ----- Main Application Class -----
class WeightbridgeDashboard:
    # Define show_about early in the class so it exists before being called
    def show_about(self):
        about_text = (
            "Weightbridge Management Dashboard\n\n"
            "Version 2.1\n"
            "Developed by Gurudharsan T\n\n"
            "Features:\n"
            "- Real-time Data Monitoring\n"
            "- Advanced Analytics\n"
            "- Export Capabilities\n"
            "- Intelligent Filters"
        )
        messagebox.showinfo("About", about_text)
        
    def __init__(self, root):
        self.root = root
        # Set window geometry with an offset
        self.root.geometry("1600x900+0+40")
        self.root.title("Weightbridge Management Dashboard")
        
        # Define colors for consistent styling
        self.primary_color = "#2c3e50"
        self.secondary_color = "#3498db"
        self.success_color = "#27ae60"
        self.warning_color = "#f1c40f"
        self.danger_color = "#e74c3c"
        
        self.root.configure(bg="#f5f6fa")
        self.style = ttk.Style()
        self.set_style()
        
        # Use a custom menu bar and pass self as controller
        self.custom_menu = CustomMenuBar(self.root, controller=self)
        self.custom_menu.pack(fill="x", side="top")
        
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

        # Build main dashboard
        self.create_dashboard()
        self.load_all_data()

    @staticmethod
    def safe_float(value, default=0.0):
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def set_style(self):
        base_font = ("Segoe UI", 16)
        heading_font = ("Segoe UI Semibold", 18)
        button_font = ("Segoe UI", 16)
        
        self.style.theme_use("clam")
        self.style.configure(".", font=base_font)
        self.style.configure("TFrame", background="#f5f6fa")
        self.style.configure("TLabel", background="#f5f6fa", foreground=self.primary_color, font=base_font)
        self.style.configure("TButton", background=self.secondary_color, foreground="white", font=button_font,
                             borderwidth=1, focusthickness=3, focuscolor=self.secondary_color)
        self.style.map("TButton",
                       background=[("active", self.primary_color), ("disabled", "#bdc3c7")],
                       foreground=[("disabled", "#7f8c8d")])
        self.style.configure("Treeview", font=base_font, rowheight=35)
        self.style.configure("Treeview.Heading", font=heading_font, background=self.primary_color, 
                             foreground="white", relief="flat")
        self.style.map("Treeview.Heading",
                       background=[("active", self.secondary_color)])
        self.style.configure("Accent.TButton", background=self.success_color, foreground="white", font=button_font)

    def create_dashboard(self):
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        self.create_filters_frame(main_frame)

        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=10)

        self.create_data_table_view()
        self.create_analytics_view()

        self.status = ttk.Label(self.root, text="Ready", background=self.primary_color, 
                                  foreground="white", anchor=tk.W, padding=10, font=("Segoe UI", 16))
        self.status.pack(side=tk.BOTTOM, fill=tk.X)

    def create_filters_frame(self, parent):
        filters_frame = ttk.LabelFrame(parent, text="Filters & Controls", padding=(20, 15))
        filters_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(filters_frame, text="Date Range:", font=("Segoe UI", 16)).grid(row=0, column=0, padx=10, pady=5, sticky=tk.W)
        self.start_date_entry = DateEntry(filters_frame, width=14, date_pattern='yyyy-mm-dd',
                                          background='darkblue', foreground='white', 
                                          bordercolor=self.primary_color, font=("Segoe UI", 16))
        self.start_date_entry.set_date(datetime.now() - timedelta(days=30))
        self.start_date_entry.grid(row=0, column=1, padx=10, pady=5)
        ttk.Label(filters_frame, text="to", font=("Segoe UI", 16)).grid(row=0, column=2, padx=10, pady=5, sticky=tk.W)
        self.end_date_entry = DateEntry(filters_frame, width=14, date_pattern='yyyy-mm-dd',
                                        background='darkblue', foreground='white', 
                                        bordercolor=self.primary_color, font=("Segoe UI", 16))
        self.end_date_entry.set_date(datetime.now())
        self.end_date_entry.grid(row=0, column=3, padx=10, pady=5)

        ttk.Label(filters_frame, text="Party Name:", font=("Segoe UI", 16)).grid(row=0, column=4, padx=10, pady=5, sticky=tk.W)
        self.party_var = tk.StringVar()
        party_entry = ttk.Entry(filters_frame, textvariable=self.party_var, width=30, font=("Segoe UI", 16))
        party_entry.grid(row=0, column=5, padx=10, pady=5)
        party_entry.bind("<KeyRelease>", lambda e: self.apply_filters())

        ttk.Label(filters_frame, text="Rate/Kg:", font=("Segoe UI", 16)).grid(row=0, column=6, padx=10, pady=5, sticky=tk.W)
        self.rate_var = tk.StringVar()
        rate_entry = ttk.Entry(filters_frame, textvariable=self.rate_var, width=12, font=("Segoe UI", 16))
        rate_entry.grid(row=0, column=7, padx=10, pady=5)
        ttk.Button(filters_frame, text="Calculate", command=self.calculate_rate, style="Accent.TButton")\
            .grid(row=0, column=8, padx=10, pady=5)

        ttk.Button(filters_frame, text="Apply Filters", command=self.apply_filters, style="Accent.TButton")\
            .grid(row=0, column=9, padx=10, pady=5)
        ttk.Button(filters_frame, text="Reset", command=self.load_all_data, style="TButton")\
            .grid(row=0, column=10, padx=10, pady=5)

        for i in range(11):
            filters_frame.columnconfigure(i, weight=1)

    def create_data_table_view(self):
        data_frame = ttk.Frame(self.notebook)
        self.notebook.add(data_frame, text="Data Records")

        columns = ("S.No", "Date", "Party Name", "Truck Number", "No. of Bags",
                   "Gross Weight", "Truck Empty Weight", "Net Weight", "Drying", "Drying Weight")
        self.tree = ttk.Treeview(data_frame, columns=columns, show="headings", selectmode="browse")
        
        vsb = ttk.Scrollbar(data_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(data_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        col_widths = [70, 120, 180, 140, 90, 120, 140, 120, 90, 120]
        for col, width in zip(columns, col_widths):
            self.tree.heading(col, text=col, anchor=tk.CENTER,
                              command=lambda c=col: self.sort_column(c, False))
            self.tree.column(col, width=width, anchor=tk.CENTER, minwidth=50)

        self.tree.tag_configure('evenrow', background='#f8f9fa')
        self.tree.tag_configure('oddrow', background='white')
        self.tree.tag_configure('drying', background='#fff3cd')

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        data_frame.rowconfigure(0, weight=1)
        data_frame.columnconfigure(0, weight=1)

    def create_analytics_view(self):
        self.analytics_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.analytics_frame, text="Data Analytics")
        
        self.canvas_frame = ttk.Frame(self.analytics_frame)
        self.canvas_frame.pack(fill=tk.BOTH, expand=True)

        self.fig, (self.ax1, self.ax2) = plt.subplots(1, 2, figsize=(16, 6))
        self.fig.patch.set_facecolor('#f5f6fa')
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.canvas_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def load_all_data(self):
        self.status.config(text="Loading data...", foreground=self.primary_color)
        self.tree.delete(*self.tree.get_children())
        try:
            for i, doc in enumerate(self.collection.find().sort("date", -1)):
                tag = 'drying' if doc.get("is_drying") else 'evenrow' if i % 2 == 0 else 'oddrow'
                values = (
                    doc.get("sno"),
                    doc.get("date"),
                    doc.get("party_name"),
                    doc.get("truck_number"),
                    doc.get("num_of_bags"),
                    f'{self.safe_float(doc.get("gross_weight")):.2f}',
                    f'{self.safe_float(doc.get("truck_empty_weight")):.2f}',
                    f'{self.safe_float(doc.get("net_weight")):.2f}',
                    "Yes" if doc.get("is_drying") else "No",
                    f'{self.safe_float(doc.get("drying_weight", 0)):.2f}' if doc.get("is_drying") else "N/A"
                )
                self.tree.insert("", "end", values=values, tags=(tag,))
            self.status.config(text=f"Loaded {len(self.tree.get_children())} records", foreground=self.primary_color)
            self.update_analytics({})
        except Exception as e:
            messagebox.showerror("Data Error", f"Error fetching data: {str(e)}")
            self.status.config(text="Error loading data", foreground=self.danger_color)

    def apply_filters(self):
        query = {}
        try:
            start_date = self.start_date_entry.get_date()
            end_date = self.end_date_entry.get_date() + timedelta(days=1)
            query['date'] = {
                '$gte': start_date.strftime("%Y-%m-%d"),
                '$lt': end_date.strftime("%Y-%m-%d")
            }
        except Exception as e:
            messagebox.showerror("Date Error", "Invalid date selection. Please try again.")
            return

        if self.party_var.get():
            query['party_name'] = {'$regex': self.party_var.get(), '$options': 'i'}

        self.load_filtered_data(query)

    def load_filtered_data(self, query):
        self.status.config(text="Applying filters...", foreground=self.primary_color)
        self.tree.delete(*self.tree.get_children())
        try:
            for i, doc in enumerate(self.collection.find(query).sort("date", -1)):
                tag = 'drying' if doc.get("is_drying") else 'evenrow' if i % 2 == 0 else 'oddrow'
                values = (
                    doc.get("sno"),
                    doc.get("date"),
                    doc.get("party_name"),
                    doc.get("truck_number"),
                    doc.get("num_of_bags"),
                    f'{self.safe_float(doc.get("gross_weight")):.2f}',
                    f'{self.safe_float(doc.get("truck_empty_weight")):.2f}',
                    f'{self.safe_float(doc.get("net_weight")):.2f}',
                    "Yes" if doc.get("is_drying") else "No",
                    f'{self.safe_float(doc.get("drying_weight", 0)):.2f}' if doc.get("is_drying") else "N/A"
                )
                self.tree.insert("", "end", values=values, tags=(tag,))
            self.status.config(text=f"Loaded {len(self.tree.get_children())} filtered records", foreground=self.primary_color)
            self.update_analytics(query)
        except Exception as e:
            messagebox.showerror("Filter Error", f"Error applying filters: {str(e)}")
            self.status.config(text="Error applying filters", foreground=self.danger_color)

    def update_analytics(self, query):
        try:
            plt.close(self.fig)
            self.fig, (self.ax1, self.ax2) = plt.subplots(1, 2, figsize=(16, 6))
            self.fig.patch.set_facecolor('#f5f6fa')
            
            data_list = list(self.collection.find(query))
            df = pd.DataFrame(data_list)
            
            if df.empty:
                self.ax1.text(0.5, 0.5, "No data available", ha='center', va='center', fontsize=16, color=self.primary_color)
                self.ax2.text(0.5, 0.5, "No data available", ha='center', va='center', fontsize=16, color=self.primary_color)
            else:
                numeric_cols = ['net_weight', 'gross_weight', 'truck_empty_weight']
                for col in numeric_cols:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                
                party_net = df.groupby('party_name')['net_weight'].sum().nlargest(10)
                party_net.sort_values().plot(kind='barh', ax=self.ax1, color=self.secondary_color)
                self.ax1.set_title('Top 10 Parties by Net Weight', fontsize=16)
                self.ax1.set_xlabel('Total Net Weight (kg)', fontsize=14)
                self.ax1.grid(True, linestyle='--', alpha=0.6)
                
                if 'is_drying' in df.columns:
                    drying_data = df['is_drying'].value_counts()
                    drying_data = drying_data.reindex([True, False], fill_value=0)
                    colors = [self.warning_color, self.success_color]
                    explode = (0.1, 0)
                    labels = {True: 'Drying', False: 'No Drying'}
                    self.ax2.pie(drying_data, 
                                 labels=[labels[k] for k in drying_data.index],
                                 autopct='%1.1f%%', 
                                 startangle=90, 
                                 colors=colors, 
                                 explode=explode,
                                 textprops={'color': self.primary_color, 'fontsize': 14})
                    self.ax2.set_title('Drying Status Distribution', fontsize=16)
                else:
                    self.ax2.text(0.5, 0.5, "Drying data unavailable", ha='center', va='center', fontsize=16, color=self.primary_color)

            self.fig.suptitle("Analytics Dashboard", fontsize=16, y=1.02)
            self.fig.tight_layout(pad=3.0)
            
            for widget in self.canvas_frame.winfo_children():
                widget.destroy()
            self.canvas = FigureCanvasTkAgg(self.fig, master=self.canvas_frame)
            self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            self.canvas.draw()
            
            self.status.config(text="Analytics updated", foreground=self.primary_color)
        except Exception as e:
            self.status.config(text=f"Analytics error: {str(e)}", foreground=self.danger_color)

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

    def calculate_rate(self):
        rate_str = self.rate_var.get().strip()
        if not rate_str:
            messagebox.showwarning("Rate Error", "Please enter a rate per kg.")
            return

        try:
            rate = float(rate_str)
        except ValueError:
            messagebox.showerror("Rate Error", "Invalid rate. Please enter a numeric value.")
            return

        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("Selection Error", "Please select a row from the table.")
            return

        try:
            net_weight_str = self.tree.item(selected_item[0], 'values')[7]
            net_weight = self.safe_float(net_weight_str)
            total_amount = rate * net_weight
            
            result_message = (
                f"Calculation Details:\n\n"
                f"Rate: ₹{rate:.2f}/kg\n"
                f"Net Weight: {net_weight:.2f} kg\n"
                f"Total Amount: ₹{total_amount:,.2f}"
            )
            messagebox.showinfo("Rate Calculation", result_message)
            self.status.config(
                text=f"Calculated Amount: ₹{total_amount:,.2f} | Rate: ₹{rate}/kg | Net Weight: {net_weight} kg", 
                foreground=self.primary_color
            )
        except Exception as e:
            messagebox.showerror("Calculation Error", f"Error in calculation: {str(e)}")

    def export_data(self, format_type):
        query = {}
        try:
            start_date = self.start_date_entry.get_date()
            end_date = self.end_date_entry.get_date() + timedelta(days=1)
            query['date'] = {
                '$gte': start_date.strftime("%Y-%m-%d"),
                '$lt': end_date.strftime("%Y-%m-%d")
            }
        except Exception as e:
            messagebox.showerror("Date Error", "Invalid date selection. Please try again.")
            return

        if self.party_var.get():
            query['party_name'] = {'$regex': self.party_var.get(), '$options': 'i'}

        try:
            df = pd.DataFrame(list(self.collection.find(query)))
            if df.empty:
                messagebox.showinfo("No Data", "No records available for the selected filters.")
                return

            file_types = {
                "csv": ("CSV Files", "*.csv"),
                "xlsx": ("Excel Files", "*.xlsx")
            }

            if format_type not in file_types:
                messagebox.showerror("Export Error", "Unsupported file type selected.")
                return

            file_path = filedialog.asksaveasfilename(
                defaultextension=f".{format_type}",
                filetypes=[file_types[format_type]]
            )

            if file_path:
                if format_type == "csv":
                    df.to_csv(file_path, index=False)
                else:
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
    app = WeightbridgeDashboard(root)
    root.mainloop()

if __name__ == "__main__":
    main()
