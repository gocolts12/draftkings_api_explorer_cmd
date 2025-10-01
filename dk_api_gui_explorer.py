import tkinter as tk
from tkinter import scrolledtext, filedialog, messagebox, Menu, ttk
import threading
import queue
import json
import re
import os
import sys
import pandas as pd
from typing import Dict, List

# Import the core logic from the new module
from dk_api_logic import (
    scrape_and_parse_draftkings, 
    apply_smart_formatting, 
    StructureAnalyzer
)

# --- HELPER FUNCTION FOR PYINSTALLER ---
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# --- REFERENCE DATA LOADER ---
def load_and_format_reference_data() -> List[Dict]:
    """Loads reference data from the bundled JSON file."""
    try:
        path = resource_path('id_reference.json')
        with open(path, 'r') as f: 
            return json.load(f)
    except Exception as e:
        messagebox.showerror("Error Loading Data", f"Could not load id_reference.json.\n\nError: {e}")
        return []

# --- GUI APPLICATION ---
class ScraperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("DraftKings API Scraper - Dynamic Parser")
        self.root.geometry("950x700")
        
        # ... (rest of the GUI code is the same as the original)

    def run_scraping_logic(self, league_id, category_id, subcategory_id, save_raw):
        # This now calls the imported functions
        raw_df, market_type, analysis = scrape_and_parse_draftkings(
            self.log_queue, league_id, category_id, subcategory_id, save_raw
        )
        
        self.last_analysis = analysis
        
        if raw_df.empty:
            self.log_queue.put("Scraping finished with no results.")
            self.scrape_button.config(state=tk.NORMAL, bg="#4CAF50")
            self.status_label.config(text="No data found", fg="red")
            return
        
        self.log_queue.put(f"\nApplying smart formatting for {market_type} market...")
        self.scraped_df = apply_smart_formatting(raw_df, market_type)
        
        if self.scraped_df.empty:
            self.log_queue.put("Processing finished with no results.")
            # ... (rest of the function is the same)

# ... (The rest of the GUI class and the main execution block remain the same)
if __name__ == "__main__":
    root = tk.Tk()
    app = ScraperApp(root)
    root.mainloop()
