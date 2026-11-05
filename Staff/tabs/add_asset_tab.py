import os
import sys

_ADMIN_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ADMIN_DIR not in sys.path:
    sys.path.insert(0, _ADMIN_DIR)


from staff import *


class AddAssetTabMixin:
    def render_add_asset(self):
        top_header_frame = tk.Frame(self.content_frame, bg=THEME["bg_main"])
        top_header_frame.pack(fill="x", padx=30, pady=(15, 10))

        badge_lbl = tk.Label(
            top_header_frame, text="Add New Asset", font=("Arial", 11, "bold"),
            bg="#A0C4DF", fg="#2C3A61", padx=12, relief="flat"
        )
        badge_lbl.pack(anchor="nw", pady=(0, 5))

        tk.Label(
            top_header_frame, text="Enter Warehouse Physical Stock Details", 
            font=("Arial", 11, "italic"), bg=THEME["bg_main"], fg=THEME["text_muted"]
        ).pack(anchor="nw")

        outer_box = tk.Frame(
            self.content_frame, bg=THEME["form_container"], 
            highlightbackground=THEME["border"], highlightthickness=1
        )
        outer_box.pack(fill="both", expand=True, padx=30, pady=(5, 25))

        container = tk.Frame(outer_box, bg=THEME["form_container"])
        container.pack(fill="both", expand=True, padx=25, pady=15)

        self.asset_entries = {}

        # --- SECTION 1: Core Details ---
        tk.Label(
            container, text="Core Details:", font=FONTS["section_label"], 
            bg=THEME["form_container"], fg=THEME["text_light"]
        ).pack(anchor="nw", pady=(0, 4))

        card1 = tk.Frame(container, bg=THEME["sub_card"], highlightbackground=THEME["border"], highlightthickness=1)
        card1.pack(fill="both", expand=True, pady=(0, 12))

        card1_inner = tk.Frame(card1, bg=THEME["sub_card"])
        card1_inner.pack(fill="both", expand=True, padx=20, pady=12)

        r1 = tk.Frame(card1_inner, bg=THEME["sub_card"])
        r1.pack(fill="x", pady=(0, 10))

        f_name = tk.Frame(r1, bg=THEME["sub_card"])
        f_name.pack(side="left", expand=True, fill="x", padx=(0, 15))
        tk.Label(f_name, text="Asset Name*", font=FONTS["field_label"], bg=THEME["sub_card"], fg=THEME["text_dark"]).pack(anchor="nw")
        self.asset_entries["name"] = tk.Entry(f_name, font=("Arial", 10), bg="white", bd=1, relief="solid")
        self.asset_entries["name"].pack(fill="x", ipady=4, pady=(3, 0))

        f_brand = tk.Frame(r1, bg=THEME["sub_card"])
        f_brand.pack(side="left", expand=True, fill="x", padx=(0, 15))
        tk.Label(f_brand, text="Brand*", font=FONTS["field_label"], bg=THEME["sub_card"], fg=THEME["text_dark"]).pack(anchor="nw")
        self.asset_entries["brand"] = tk.Entry(f_brand, font=("Arial", 10), bg="white", bd=1, relief="solid")
        self.asset_entries["brand"].pack(fill="x", ipady=4, pady=(3, 0))

        f_cat = tk.Frame(r1, bg=THEME["sub_card"])
        f_cat.pack(side="left", expand=True, fill="x")
        tk.Label(f_cat, text="Category*", font=FONTS["field_label"], bg=THEME["sub_card"], fg=THEME["text_dark"]).pack(anchor="nw")
        cat_options = ["IT hardware", "Networking & Infrastructures", "Peripherals & Accesories", "AV & Media"]
        self.asset_entries["category"] = ttk.Combobox(f_cat, values=cat_options, state="readonly", font=("Arial", 10))
        self.asset_entries["category"].set("Select Category")
        self.asset_entries["category"].pack(fill="x", ipady=3, pady=(3, 0))

        r2 = tk.Frame(card1_inner, bg=THEME["sub_card"])
        r2.pack(fill="x")

        tk.Frame(r2, bg=THEME["sub_card"]).pack(side="left", expand=True, fill="x", padx=(0, 15))
        tk.Frame(r2, bg=THEME["sub_card"]).pack(side="left", expand=True, fill="x")

        # --- SECTION 2: Stock & Valuation ---
        tk.Label(
            container, text="Stock & Valuation", font=FONTS["section_label"], 
            bg=THEME["form_container"], fg=THEME["text_light"]
        ).pack(anchor="nw", pady=(0, 4))

        card2 = tk.Frame(container, bg=THEME["sub_card"], highlightbackground=THEME["border"], highlightthickness=1)
        card2.pack(fill="both", expand=True, pady=(0, 12))

        card2_inner = tk.Frame(card2, bg=THEME["sub_card"])
        card2_inner.pack(fill="both", expand=True, padx=20, pady=12)

        r3 = tk.Frame(card2_inner, bg=THEME["sub_card"])
        r3.pack(fill="x")

        f_qty = tk.Frame(r3, bg=THEME["sub_card"])
        f_qty.pack(side="left", expand=False, fill="y", padx=(0, 40))
        tk.Label(f_qty, text="Quantity*", font=FONTS["field_label"], bg=THEME["sub_card"], fg=THEME["text_dark"]).pack(anchor="nw")

        qty_sub = tk.Frame(f_qty, bg=THEME["sub_card"])
        qty_sub.pack(fill="x", pady=(3, 0))

        self.asset_entries["qty"] = tk.Entry(
            qty_sub, font=("Arial", 10), bg="white", bd=1, relief="solid", 
            width=8, validate="key", validatecommand=self.vcmd_qty
        )
        self.asset_entries["qty"].insert(0, "1")
        self.asset_entries["qty"].pack(side="left", ipady=4, padx=(0, 6))
        self.asset_entries["qty"].bind("<KeyRelease>", self.update_total_value) 

        tk.Button(qty_sub, text="+", font=("Arial", 9, "bold"), width=2, command=self.increment_qty).pack(side="left", padx=2)
        tk.Button(qty_sub, text="-", font=("Arial", 9, "bold"), width=2, command=self.decrement_qty).pack(side="left", padx=2)

        f_price = tk.Frame(r3, bg=THEME["sub_card"])
        f_price.pack(side="left", expand=True, fill="x", padx=(0, 15))
        tk.Label(f_price, text="Unit Price*", font=FONTS["field_label"], bg=THEME["sub_card"], fg=THEME["text_dark"]).pack(anchor="nw")

        self.price_var = tk.StringVar()
        self.price_var.trace_add("write", self.format_price_and_total)
        self.asset_entries["price"] = tk.Entry(f_price, textvariable=self.price_var, font=("Arial", 10), bg="white", bd=1, relief="solid")
        self.asset_entries["price"].pack(fill="x", ipady=4, pady=(3, 0))

        f_total = tk.Frame(r3, bg=THEME["sub_card"])
        f_total.pack(side="left", expand=True, fill="x")
        tk.Label(f_total, text="Total Estimated Value", font=FONTS["field_label"], bg=THEME["sub_card"], fg=THEME["text_dark"]).pack(anchor="nw")
        self.val_total_est = tk.StringVar(value="$0.00")
        tk.Label(f_total, textvariable=self.val_total_est, font=("Arial", 10, "bold"), bg="#D0D4DC", fg=THEME["text_dark"], anchor="w", padx=10, relief="solid", bd=1).pack(fill="x", ipady=5, pady=(3, 0))

        # --- SECTION 3: Acquisition & Location ---
        tk.Label(
            container, text="Acquisition & Location", font=FONTS["section_label"], 
            bg=THEME["form_container"], fg=THEME["text_light"]
        ).pack(anchor="nw", pady=(0, 4))

        card3 = tk.Frame(container, bg=THEME["sub_card"], highlightbackground=THEME["border"], highlightthickness=1)
        card3.pack(fill="both", expand=True, pady=(0, 12))

        card3_inner = tk.Frame(card3, bg=THEME["sub_card"])
        card3_inner.pack(fill="both", expand=True, padx=20, pady=12)

        r4 = tk.Frame(card3_inner, bg=THEME["sub_card"])
        r4.pack(fill="x", pady=(0, 10))

        f_date = tk.Frame(r4, bg=THEME["sub_card"])
        f_date.pack(side="left", expand=True, fill="x", padx=(0, 15))
        tk.Label(f_date, text="Purchase Date", font=FONTS["field_label"], bg=THEME["sub_card"], fg=THEME["text_dark"]).pack(anchor="nw")

        date_sub = tk.Frame(f_date, bg=THEME["sub_card"])
        date_sub.pack(fill="x", pady=(3, 0))

        self.date_var = tk.StringVar(value="YYYY/MM/DD")
        self.date_var.trace_add("write", self.format_date_input)
        self.asset_entries["date"] = tk.Entry(date_sub, textvariable=self.date_var, font=("Arial", 10), bg="white", bd=1, relief="solid")
        self.asset_entries["date"].pack(side="left", fill="x", expand=True, ipady=4, padx=(0, 4))

        tk.Button(date_sub, text="ðŸ“…", font=("Arial", 9), bg=THEME["bg_header"], fg="white", command=self.open_calendar_popup).pack(side="left")

        f_warranty = tk.Frame(r4, bg=THEME["sub_card"])
        f_warranty.pack(side="left", expand=True, fill="x")
        tk.Label(f_warranty, text="Warranty Duration", font=FONTS["field_label"], bg=THEME["sub_card"], fg=THEME["text_dark"]).pack(anchor="nw")

        warranty_options = ["1 Year", "5 Years", "10 Years", "Custom"]
        self.warranty_combo = ttk.Combobox(f_warranty, values=warranty_options, state="readonly", font=("Arial", 10))
        self.warranty_combo.set("1 Year")
        self.warranty_combo.pack(fill="x", ipady=3, pady=(3, 0))
        self.warranty_combo.bind("<<ComboboxSelected>>", self.toggle_custom_warranty)

        self.f_custom_warranty = tk.Frame(f_warranty, bg=THEME["sub_card"])
        self.asset_entries["custom_warranty"] = tk.Entry(self.f_custom_warranty, font=("Arial", 10), bg="white", bd=1, relief="solid")
        self.asset_entries["custom_warranty"].pack(fill="x", ipady=3, pady=(3, 0))

        r5 = tk.Frame(card3_inner, bg=THEME["sub_card"])
        r5.pack(fill="x")

        f_supplier = tk.Frame(r5, bg=THEME["sub_card"])
        f_supplier.pack(side="left", expand=True, fill="x", padx=(0, 15))
        tk.Label(f_supplier, text="Supplier", font=FONTS["field_label"], bg=THEME["sub_card"], fg=THEME["text_dark"]).pack(anchor="nw")

        sup_sub = tk.Frame(f_supplier, bg=THEME["sub_card"])
        sup_sub.pack(fill="x", pady=(3, 0))
        self.supplier_combo = ttk.Combobox(sup_sub, values=self.supplier_options_list, state="readonly", font=("Arial", 10))
        self.supplier_combo.set("No Supplier Added" if not self.supplier_options_list else self.supplier_options_list[0])
        self.supplier_combo.pack(side="left", fill="x", expand=True, ipady=3)

        tk.Button(sup_sub, text="+", font=("Arial", 9, "bold"), bg=THEME["bg_header"], fg="white", width=2, command=self.open_add_supplier_dialog).pack(side="left", padx=(4, 2))
        tk.Button(sup_sub, text="-", font=("Arial", 9, "bold"), bg=THEME["accent_danger"], fg="white", width=2, command=self.open_delete_supplier_dialog).pack(side="left")
        self.asset_entries["supplier"] = self.supplier_combo

        f_loc = tk.Frame(r5, bg=THEME["sub_card"])
        f_loc.pack(side="left", expand=True, fill="x")
        tk.Label(f_loc, text="Warehouse Location / Shelf", font=FONTS["field_label"], bg=THEME["sub_card"], fg=THEME["text_dark"]).pack(anchor="nw")

        loc_sub = tk.Frame(f_loc, bg=THEME["sub_card"])
        loc_sub.pack(fill="x", pady=(3, 0))
        self.location_combo = ttk.Combobox(loc_sub, values=self.location_options_list, state="readonly", font=("Arial", 10))
        if self.location_options_list:
            self.location_combo.set(self.location_options_list[0])
        else:
            self.location_combo.set("No Location Added")
        self.location_combo.pack(side="left", fill="x", expand=True, ipady=3)

        tk.Button(loc_sub, text="+", font=("Arial", 9, "bold"), bg=THEME["bg_header"], fg="white", width=2, command=self.open_add_location_dialog).pack(side="left", padx=(4, 2))
        tk.Button(loc_sub, text="-", font=("Arial", 9, "bold"), bg=THEME["accent_danger"], fg="white", width=2, command=self.open_delete_location_dialog).pack(side="left")
        self.asset_entries["location"] = self.location_combo

        # --- SECTION 4: Action Buttons ---
        btn_action_frame = tk.Frame(container, bg=THEME["form_container"])
        btn_action_frame.pack(fill="x", pady=(5, 0))

        clear_btn = tk.Button(
            btn_action_frame, text="Clear Form", font=("Arial", 10, "bold"), 
            bg="#95A5A6", fg="white", bd=0, padx=22, pady=7,
            command=self.clear_form
        )
        clear_btn.pack(side="right")

        save_btn = tk.Button(
            btn_action_frame, text="Save Asset", font=("Arial", 10, "bold"), 
            bg=THEME["bg_header"], fg="white", bd=0, padx=22, pady=7,
            command=self.validate_and_save_asset
        )
        save_btn.pack(side="right", padx=(0, 12))


if __name__ == "__main__":
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from staff import StaffAssetManagementApp
    app = StaffAssetManagementApp(username="Staff")
    app.after(0, lambda: app.switch_tab('Add Asset'))
    app.mainloop()

