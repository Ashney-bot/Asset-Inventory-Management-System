import os
import sys

_ADMIN_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ADMIN_DIR not in sys.path:
    sys.path.insert(0, _ADMIN_DIR)


from dashboard import *


class LogsTabMixin:
    def render_logs(self):
        top_header_frame = tk.Frame(self.content_frame, bg=THEME["bg_main"])
        top_header_frame.pack(fill="x", padx=30, pady=(15, 10))

        tk.Label(
            top_header_frame, text="Audit & Activity History", font=FONTS["title"], 
            bg=THEME["bg_main"], fg=THEME["text_dark"]
        ).pack(anchor="nw", pady=(0, 2))

        tk.Label(
            top_header_frame, text="System-wide log of user actions, asset updates, and security events.", 
            font=("Arial", 11, "italic"), bg=THEME["bg_main"], fg=THEME["text_muted"]
        ).pack(anchor="nw")

        filter_box = tk.Frame(
            self.content_frame, bg=THEME["form_container"], 
            highlightbackground=THEME["border"], highlightthickness=1
        )
        filter_box.pack(fill="x", padx=30, pady=(10, 15))

        filter_inner = tk.Frame(filter_box, bg=THEME["form_container"])
        filter_inner.pack(fill="x", padx=15, pady=12)

        search_frame = tk.Frame(filter_inner, bg="white", highlightbackground=THEME["border"], highlightthickness=1)
        search_frame.pack(side="left", ipady=2)
        tk.Label(search_frame, text="🔍", bg="white", fg=THEME["text_muted"], font=("Arial", 11)).pack(side="left", padx=5)

        self.log_search_entry = tk.Entry(search_frame, bd=0, bg="white", font=("Arial", 11), width=35)
        self.log_search_entry.pack(side="left", ipady=4, padx=(0, 5))
        self.log_search_entry.insert(0, "Search logs...")

        action_options = ["All", "CREATE", "READ", "UPDATE", "DELETE"]
        self.log_action_combo = ttk.Combobox(filter_inner, values=action_options, state="readonly", font=("Arial", 10), width=12)
        self.log_action_combo.set("All")
        self.log_action_combo.pack(side="right", padx=(5, 0), ipady=4)
        tk.Label(filter_inner, text="Action:", font=("Arial", 10, "bold"), bg=THEME["form_container"], fg=THEME["text_light"]).pack(side="right", padx=(15, 2))

        user_options = ["All", "Admin", "Staff"]
        self.log_user_combo = ttk.Combobox(filter_inner, values=user_options, state="readonly", font=("Arial", 10), width=12)
        self.log_user_combo.set("All")
        self.log_user_combo.pack(side="right", padx=(5, 0), ipady=4)
        tk.Label(filter_inner, text="User:", font=("Arial", 10, "bold"), bg=THEME["form_container"], fg=THEME["text_light"]).pack(side="right", padx=(10, 2))

        table_frame = tk.Frame(
            self.content_frame, bg=THEME["bg_main"], 
            highlightbackground=THEME["border"], highlightthickness=1
        )
        table_frame.pack(fill="both", expand=True, padx=30, pady=(0, 20))

        columns = ("timestamp", "user", "role", "action")
        self.logs_tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="extended")

        scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.logs_tree.yview)
        self.logs_tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.logs_tree.pack(side="left", fill="both", expand=True)

        self.logs_tree.heading("timestamp", text="TIMESTAMP")
        self.logs_tree.heading("user", text="USER")
        self.logs_tree.heading("role", text="ROLE")
        self.logs_tree.heading("action", text="ACTION")

        self.logs_tree.column("timestamp", width=220, anchor="center")
        self.logs_tree.column("user", width=200, anchor="w")
        self.logs_tree.column("role", width=160, anchor="center")
        self.logs_tree.column("action", width=420, anchor="w")

        try:
            connection = mysql.connector.connect(**DB_CONFIG)
            cursor = connection.cursor(dictionary=True)
            cursor.execute(
                """
                SELECT created_at, username, role, CONCAT(action, ': ', description) AS action
                FROM activity_logs
                ORDER BY log_id DESC
                LIMIT 500
                """
            )
            self.logs_data = [
                (
                    row["created_at"].strftime("%Y-%m-%d %H:%M:%S")
                    if hasattr(row["created_at"], "strftime") else str(row["created_at"]),
                    row["username"],
                    row["role"],
                    row["action"],
                )
                for row in cursor.fetchall()
            ]
        except Error as exc:
            messagebox.showerror("Database Error", f"Could not load logs.\n{exc}")
        finally:
            if "cursor" in locals():
                cursor.close()
            if "connection" in locals():
                connection.close()

        for log in self.logs_data:
            self.logs_tree.insert("", "end", values=log)


if __name__ == "__main__":
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from dashboard import AssetManagementApp
    app = AssetManagementApp()
    app.after(0, lambda: app.switch_tab('Logs'))
    app.mainloop()
