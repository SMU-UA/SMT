import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import pandas as pd
import os
import re


class CsvSplitterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CSV Splitter by Label")
        self.root.geometry("700x500")
        self.root.resizable(True, True)

        self.csv_path = None
        self.df = None
        self.datetime_str = ""

        self._build_ui()

    def _build_ui(self):
        # --- Input file section ---
        frame_input = ttk.LabelFrame(self.root, text="1. Select CSV File", padding=10)
        frame_input.pack(fill="x", padx=10, pady=(10, 5))

        self.lbl_file = ttk.Label(frame_input, text="No file selected", anchor="w")
        self.lbl_file.pack(side="left", fill="x", expand=True)

        btn_browse = ttk.Button(frame_input, text="Browse...", command=self.browse_csv)
        btn_browse.pack(side="right")

        # --- Labels found section ---
        frame_labels = ttk.LabelFrame(self.root, text="2. Labels Found (excluding Logging...)", padding=10)
        frame_labels.pack(fill="both", expand=True, padx=10, pady=5)

        self.tree = ttk.Treeview(frame_labels, columns=("label", "rows"), show="headings", height=10)
        self.tree.heading("label", text="Label")
        self.tree.heading("rows", text="Row Count")
        self.tree.column("label", width=450)
        self.tree.column("rows", width=100, anchor="center")

        scrollbar = ttk.Scrollbar(frame_labels, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # --- Output folder section ---
        frame_output = ttk.LabelFrame(self.root, text="3. Select Output Folder", padding=10)
        frame_output.pack(fill="x", padx=10, pady=5)

        self.lbl_output = ttk.Label(frame_output, text="No folder selected", anchor="w")
        self.lbl_output.pack(side="left", fill="x", expand=True)

        btn_output = ttk.Button(frame_output, text="Browse...", command=self.browse_output)
        btn_output.pack(side="right")

        # --- Split button ---
        self.btn_split = ttk.Button(self.root, text="Split and Save", command=self.split_and_save, state="disabled")
        self.btn_split.pack(pady=10)

        # --- Status bar ---
        self.lbl_status = ttk.Label(self.root, text="", relief="sunken", anchor="w")
        self.lbl_status.pack(fill="x", side="bottom", padx=10, pady=(0, 10))

    def browse_csv(self):
        path = filedialog.askopenfilename(
            title="Select CSV file",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not path:
            return

        self.csv_path = path
        self.lbl_file.config(text=path)

        # Extract date-time from filename like HMI_DataLog_2026-02-24_16-21-24.csv
        basename = os.path.basename(path)
        match = re.search(r"(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})", basename)
        self.datetime_str = match.group(1) if match else ""

        try:
            self.df = pd.read_csv(path)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to read CSV:\n{e}")
            return

        if "Label" not in self.df.columns:
            messagebox.showerror("Error", "CSV does not contain a 'Label' column.")
            self.df = None
            return

        # Filter out Logging...
        filtered = self.df[self.df["Label"].str.strip() != "Logging..."]
        labels = filtered.groupby("Label").size().reset_index(name="count")

        # Populate treeview
        self.tree.delete(*self.tree.get_children())
        for _, row in labels.iterrows():
            self.tree.insert("", "end", values=(row["Label"], row["count"]))

        self.lbl_status.config(text=f"Loaded {len(self.df)} rows, {len(labels)} unique labels (excluding Logging...)")
        self._check_ready()

    def browse_output(self):
        folder = filedialog.askdirectory(title="Select output folder")
        if not folder:
            return
        self.output_folder = folder
        self.lbl_output.config(text=folder)
        self._check_ready()

    def _check_ready(self):
        if self.df is not None and hasattr(self, "output_folder"):
            self.btn_split.config(state="normal")
        else:
            self.btn_split.config(state="disabled")

    def split_and_save(self):
        filtered = self.df[self.df["Label"].str.strip() != "Logging..."]
        groups = filtered.groupby("Label")

        saved = 0
        for label, group_df in groups:
            # Build filename: LabelName_datetime.csv
            safe_label = str(label).strip()
            if self.datetime_str:
                filename = f"{safe_label}_{self.datetime_str}.csv"
            else:
                filename = f"{safe_label}.csv"

            out_path = os.path.join(self.output_folder, filename)
            group_df.to_csv(out_path, index=False)
            saved += 1

        self.lbl_status.config(text=f"Done! Saved {saved} files to {self.output_folder}")
        messagebox.showinfo("Success", f"Saved {saved} CSV files to:\n{self.output_folder}")


if __name__ == "__main__":
    root = tk.Tk()
    app = CsvSplitterApp(root)
    root.mainloop()
