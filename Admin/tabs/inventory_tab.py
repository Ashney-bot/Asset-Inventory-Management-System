import os
import sys

_ADMIN_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ADMIN_DIR not in sys.path:
    sys.path.insert(0, _ADMIN_DIR)


from dashboard import *


class InventoryTabMixin:
    def render_inventory(self):
        tk.Label(
            self.content_frame, text="Asset Lists", 
            font=FONTS["title"], bg=THEME["bg_main"], fg=THEME["bg_header"]
        ).pack(pady=(20, 15), padx=30, anchor="nw")

        controls_frame = tk.Frame(self.content_frame, bg=THEME["bg_main"])
        controls_frame.pack(fill="x", padx=30, pady=(0, 15))

        search_frame = tk.Frame(controls_frame, bg=THEME["bg_main"], highlightbackground=THEME["border"], highlightthickness=1)
        search_frame.pack(side="left")
        tk.Label(search_frame, text="🔍", bg=THEME["bg_main"], fg=THEME["text_muted"], font=("Arial", 11)).pack(side="left", padx=5)
        self.inventory_search_entry = tk.Entry(search_frame, bd=0, bg=THEME["bg_main"], font=("Arial", 11), width=35)
        self.inventory_search_entry.pack(side="left", ipady=6, padx=(0, 5))
        self.inventory_search_entry.insert(0, "Search assets...")
        self.inventory_search_entry.bind("<FocusIn>", self._clear_inventory_search_placeholder)
        self.inventory_search_entry.bind("<FocusOut>", self._restore_inventory_search_placeholder)
        self.inventory_search_entry.bind("<KeyRelease>", lambda event: self.apply_inventory_filters())

        cat_options = ["All Categories", "IT hardware", "Networking & Infrastructures", "Peripherals & Accesories", "AV & Media"]
        self.inventory_category_combo = ttk.Combobox(controls_frame, values=cat_options, state="readonly", font=("Arial", 10), width=25)
        self.inventory_category_combo.set("All Categories")
        self.inventory_category_combo.pack(side="left", padx=(20, 10), ipady=5)
        self.inventory_category_combo.bind("<<ComboboxSelected>>", lambda event: self.apply_inventory_filters())

        remove_btn = tk.Button(
            controls_frame, text="Remove", font=("Arial", 10, "bold"), 
            bg=THEME["accent_danger"], fg="white", bd=0, padx=15, pady=5,
            command=self.soft_delete_asset
        )
        remove_btn.pack(side="right")

        decrease_btn = tk.Button(
            controls_frame, text="Decrease Quantity", font=("Arial", 10, "bold"),
            bg="#D35400", fg="white", bd=0, padx=15, pady=5,
            command=self.decrease_asset_quantity
        )
        decrease_btn.pack(side="right", padx=(0, 10))

        undo_btn = tk.Button(
            controls_frame, text="Undo Decrease", font=("Arial", 10, "bold"),
            bg="#27AE60", fg="white", bd=0, padx=15, pady=5,
            command=self.undo_last_quantity_decrease
        )
        undo_btn.pack(side="right", padx=(0, 10))

        table_frame = tk.Frame(self.content_frame, bg=THEME["bg_main"], highlightbackground=THEME["border"], highlightthickness=1)
        table_frame.pack(fill="both", expand=True, padx=30, pady=(0, 15))

        columns = ("id", "name", "category", "status", "qty", "info")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="extended")

        scroll_y = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        scroll_x = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        scroll_y.pack(side="right", fill="y")
        scroll_x.pack(side="bottom", fill="x")
        self.tree.pack(side="left", fill="both", expand=True)

        self.tree.heading("id", text="ID")
        self.tree.heading("name", text="Asset Name")
        self.tree.heading("category", text="Category")
        self.tree.heading("status", text="Status")
        self.tree.heading("qty", text="Quantity")
        self.tree.heading("info", text="Info")

        self.tree.column("id", width=80, minwidth=80, anchor="center")
        self.tree.column("name", width=200, minwidth=200, anchor="w")
        self.tree.column("category", width=180, minwidth=180, anchor="center")
        self.tree.column("status", width=120, minwidth=120, anchor="center")
        self.tree.column("qty", width=80, minwidth=80, anchor="center")
        self.tree.column("info", width=120, minwidth=120, anchor="center")

        bottom_frame = tk.Frame(self.content_frame, bg=THEME["bg_main"])
        bottom_frame.pack(fill="x", padx=30, pady=(0, 20))

        import_btn = tk.Button(
            bottom_frame, text="Import CSV", font=("Arial", 10, "bold"), 
            bg=THEME["bg_header"], fg="white", bd=0, padx=15, pady=5,
            command=self.import_inventory_csv
        )
        import_btn.pack(side="right")

        tk.Button(
            bottom_frame, text="Export CSV", font=("Arial", 10, "bold"),
            bg=THEME["bg_header"], fg="white", bd=0, padx=15, pady=5,
            command=self.export_inventory_csv
        ).pack(side="right", padx=(0, 10))
        self.load_inventory()


if __name__ == "__main__":
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from dashboard import AssetManagementApp
    app = AssetManagementApp()
    app.after(0, lambda: app.switch_tab('Inventory'))
    app.mainloop()
