import os
import sys

_ADMIN_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ADMIN_DIR not in sys.path:
    sys.path.insert(0, _ADMIN_DIR)


from dashboard import *


class AccountManagementTabMixin:
    def render_account_management(self):
        top_header_frame = tk.Frame(self.content_frame, bg=THEME["bg_main"])
        top_header_frame.pack(fill="x", padx=30, pady=(15, 10))

        badge_lbl = tk.Label(
            top_header_frame, text="Account Management", font=("Arial", 11, "bold"),
            bg="#A0C4DF", fg="#2C3A61", padx=12, relief="flat"
        )
        badge_lbl.pack(anchor="nw", pady=(0, 5))

        tk.Label(
            top_header_frame, text="Admin & User Account Lists and Accessibility Approvals", 
            font=("Arial", 11, "italic"), bg=THEME["bg_main"], fg=THEME["text_muted"]
        ).pack(anchor="nw")

        self.accounts_data = []
        try:
            users = get_all_users()
            self.accounts_data = [
                (
                    user["user_id"],
                    user["username"],
                    user["role"],
                    user["access_status"],
                    user["email"],
                )
                for user in users
            ]
        except Error as exc:
            messagebox.showerror(
                "Database Error",
                f"Could not load registered accounts.\n{exc}",
            )

        outer_box = tk.Frame(
            self.content_frame, bg=THEME["form_container"], 
            highlightbackground=THEME["border"], highlightthickness=1
        )
        outer_box.pack(fill="both", expand=True, padx=30, pady=(5, 25))

        container = tk.Frame(outer_box, bg=THEME["form_container"])
        container.pack(fill="both", expand=True, padx=25, pady=15)

        card_acc = tk.Frame(container, bg=THEME["sub_card"], height=330, highlightbackground=THEME["border"], highlightthickness=1)
        card_acc.pack(fill="both", pady=(0, 10))
        card_acc.pack_propagate(False)

        card_acc_inner = tk.Frame(card_acc, bg=THEME["sub_card"])
        card_acc_inner.pack(fill="both", expand=True, padx=20, pady=15)

        tk.Label(
            card_acc_inner, text="Registered Admin & User Accounts", font=FONTS["section_label"], 
            bg=THEME["sub_card"], fg=THEME["text_dark"]
        ).pack(anchor="nw", pady=(0, 10))

        account_action_toolbar = tk.Frame(card_acc_inner, bg=THEME["sub_card"])
        account_action_toolbar.pack(fill="x", pady=(0, 8))

        deny_btn = tk.Button(
            account_action_toolbar, text="Deny Access", font=("Arial", 10, "bold"),
            bg=THEME["accent_danger"], fg="white", bd=0, padx=15, pady=6,
            command=lambda: self.change_account_status("Denied")
        )
        deny_btn.pack(side="right", padx=(5, 0))

        approve_btn = tk.Button(
            account_action_toolbar, text="Approve Access", font=("Arial", 10, "bold"),
            bg=THEME["accent_success"], fg="white", bd=0, padx=15, pady=6,
            command=lambda: self.change_account_status("Active")
        )
        approve_btn.pack(side="right", padx=(5, 0))

        remove_btn = tk.Button(
            account_action_toolbar, text="Remove Account", font=("Arial", 10, "bold"),
            bg=THEME["accent_danger"], fg="white", bd=0, padx=15, pady=6,
            command=self.remove_account
        )
        remove_btn.pack(side="right", padx=(5, 0))

        table_frame = tk.Frame(card_acc_inner, bg=THEME["sub_card"])
        table_frame.pack(fill="both", expand=True, pady=(0, 10))

        columns = ("id", "username", "role", "status", "email")
        self.acc_tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")

        scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.acc_tree.yview)
        self.acc_tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.acc_tree.pack(side="left", fill="both", expand=True)

        self.acc_tree.heading("id", text="User ID")
        self.acc_tree.heading("username", text="Username")
        self.acc_tree.heading("role", text="Role")
        self.acc_tree.heading("status", text="Access Status")
        self.acc_tree.heading("email", text="Email Address")

        self.acc_tree.column("id", width=90, anchor="center")
        self.acc_tree.column("username", width=150, anchor="w")
        self.acc_tree.column("role", width=150, anchor="center")
        self.acc_tree.column("status", width=150, anchor="center")
        self.acc_tree.column("email", width=220, anchor="w")

        for account in self.accounts_data:
            self.acc_tree.insert("", "end", values=account)

        tk.Label(
            container, text="Password Reset Requests", font=FONTS["section_label"], 
            bg=THEME["form_container"], fg=THEME["text_light"]
        ).pack(anchor="nw", pady=(10, 4))

        card_reset = tk.Frame(container, bg=THEME["sub_card"], height=250, highlightbackground=THEME["border"], highlightthickness=1)
        card_reset.pack(fill="x", pady=(0, 0))
        card_reset.pack_propagate(False)

        card_reset_inner = tk.Frame(card_reset, bg=THEME["sub_card"])
        card_reset_inner.pack(fill="both", expand=True, padx=20, pady=15)

        reset_toolbar = tk.Frame(card_reset_inner, bg=THEME["sub_card"])
        reset_toolbar.pack(fill="x", pady=(0, 8))

        deny_req_btn = tk.Button(
            reset_toolbar, text="Deny Request", font=("Arial", 10, "bold"),
            bg=THEME["accent_danger"], fg="white", bd=0, padx=15, pady=6,
            command=lambda: self.change_reset_status("Denied")
        )
        deny_req_btn.pack(side="right", padx=(5, 0))

        approve_req_btn = tk.Button(
            reset_toolbar, text="Approve Request", font=("Arial", 10, "bold"),
            bg=THEME["accent_success"], fg="white", bd=0, padx=15, pady=6,
            command=lambda: self.change_reset_status("Approved")
        )
        approve_req_btn.pack(side="right", padx=(5, 0))

        reset_table_frame = tk.Frame(card_reset_inner, bg=THEME["sub_card"])
        reset_table_frame.pack(fill="both", expand=True, pady=(0, 10))

        reset_cols = ("username", "email", "status", "date")
        self.reset_tree = ttk.Treeview(reset_table_frame, columns=reset_cols, show="headings", selectmode="browse")

        scroll_reset = ttk.Scrollbar(reset_table_frame, orient="vertical", command=self.reset_tree.yview)
        self.reset_tree.configure(yscrollcommand=scroll_reset.set)
        scroll_reset.pack(side="right", fill="y")
        self.reset_tree.pack(side="left", fill="both", expand=True)

        self.reset_tree.heading("username", text="Username")
        self.reset_tree.heading("email", text="Email")
        self.reset_tree.heading("status", text="Status")
        self.reset_tree.heading("date", text="Requested Date")

        self.reset_tree.column("username", width=180, anchor="w")
        self.reset_tree.column("email", width=250, anchor="w")
        self.reset_tree.column("status", width=140, anchor="center")
        self.reset_tree.column("date", width=200, anchor="center")
        self.load_reset_requests()


if __name__ == "__main__":
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from dashboard import AssetManagementApp
    app = AssetManagementApp()
    app.after(0, lambda: app.switch_tab('Account Management'))
    app.mainloop()
