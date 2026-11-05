import os
import sys

_ADMIN_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ADMIN_DIR not in sys.path:
    sys.path.insert(0, _ADMIN_DIR)


from dashboard import *


class BinTabMixin:
    def render_bin(self):
        tk.Label(
            self.content_frame, text="Recycle Bin", 
            font=FONTS["title"], bg=THEME["bg_main"], fg=THEME["bg_header"]
        ).pack(pady=(20, 15), padx=30, anchor="nw")

        controls_frame = tk.Frame(self.content_frame, bg=THEME["bg_main"])
        controls_frame.pack(fill="x", padx=30, pady=(0, 15))

        tk.Label(
            controls_frame, text="Deleted assets are stored here. You can restore them to inventory or delete them permanently.",
            font=("Arial", 10, "italic"), bg=THEME["bg_main"], fg=THEME["text_muted"]
        ).pack(side="left")

        delete_perm_btn = tk.Button(
            controls_frame, text="Delete Permanently", font=("Arial", 10, "bold"), 
            bg=THEME["accent_danger"], fg="white", bd=0, padx=15, pady=5,
            command=self.delete_permanently
        )
        delete_perm_btn.pack(side="right")

        restore_btn = tk.Button(
            controls_frame, text="Restore Asset", font=("Arial", 10, "bold"), 
            bg=THEME["accent_success"], fg="white", bd=0, padx=15, pady=5,
            command=self.restore_asset
        )
        restore_btn.pack(side="right", padx=(0, 10))

        table_frame = tk.Frame(self.content_frame, bg=THEME["bg_main"], highlightbackground=THEME["border"], highlightthickness=1)
        table_frame.pack(fill="both", expand=True, padx=30, pady=(0, 20))

        columns = ("id", "name", "category", "status", "qty", "deleted_at")
        self.bin_tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="extended")

        scroll_y = ttk.Scrollbar(table_frame, orient="vertical", command=self.bin_tree.yview)
        scroll_x = ttk.Scrollbar(table_frame, orient="horizontal", command=self.bin_tree.xview)
        self.bin_tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        scroll_y.pack(side="right", fill="y")
        scroll_x.pack(side="bottom", fill="x")
        self.bin_tree.pack(side="left", fill="both", expand=True)

        self.bin_tree.heading("id", text="ID")
        self.bin_tree.heading("name", text="Asset Name")
        self.bin_tree.heading("category", text="Category")
        self.bin_tree.heading("status", text="Status")
        self.bin_tree.heading("qty", text="Quantity")
        self.bin_tree.heading("deleted_at", text="Deleted On")

        self.bin_tree.column("id", width=80, anchor="center")
        self.bin_tree.column("name", width=220, anchor="w")
        self.bin_tree.column("category", width=180, anchor="center")
        self.bin_tree.column("status", width=120, anchor="center")
        self.bin_tree.column("qty", width=80, anchor="center")
        self.bin_tree.column("deleted_at", width=180, anchor="center")

        self.load_bin_items()


if __name__ == "__main__":
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from dashboard import AssetManagementApp
    app = AssetManagementApp()
    app.after(0, lambda: app.switch_tab('Bin'))
    app.mainloop()
