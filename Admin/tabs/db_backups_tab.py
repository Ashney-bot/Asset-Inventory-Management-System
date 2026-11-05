import os
import sys

_ADMIN_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ADMIN_DIR not in sys.path:
    sys.path.insert(0, _ADMIN_DIR)


from dashboard import *


class DbBackupsTabMixin:
    def render_db_backups(self):
        tk.Label(
            self.content_frame, text="Database Management & Backups", 
            font=FONTS["title"], bg=THEME["bg_main"], fg=THEME["bg_header"]
        ).pack(pady=(20, 15), padx=30, anchor="nw")

        outer_box = tk.Frame(
            self.content_frame, bg=THEME["form_container"], 
            highlightbackground=THEME["border"], highlightthickness=1
        )
        outer_box.pack(fill="x", expand=False, padx=30, pady=(5, 25))

        container = tk.Frame(outer_box, bg=THEME["form_container"])
        container.pack(fill="x", padx=25, pady=15)

        tk.Label(
            container, text="Database Status & Information", font=FONTS["section_label"], 
            bg=THEME["form_container"], fg=THEME["text_light"]
        ).pack(anchor="nw", pady=(0, 10))

        card_status = tk.Frame(container, bg=THEME["sub_card"], highlightbackground=THEME["border"], highlightthickness=1)
        card_status.pack(fill="x", pady=(0, 15))

        card_inner = tk.Frame(card_status, bg=THEME["sub_card"])
        card_inner.pack(fill="x", padx=20, pady=20)

        total_records = 0
        database_size_kb = 0.0
        table_count = 0
        connection = None
        cursor = None
        try:
            connection = mysql.connector.connect(**DB_CONFIG)
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT COUNT(*) FROM information_schema.tables
                WHERE table_schema = %s
                """,
                (DB_CONFIG["database"],),
            )
            table_count = cursor.fetchone()[0]
            cursor.execute(
                """
                SELECT COALESCE(SUM(table_rows), 0),
                       COALESCE(SUM(data_length + index_length), 0)
                FROM information_schema.tables
                WHERE table_schema = %s
                """,
                (DB_CONFIG["database"],),
            )
            total_records, database_size_bytes = cursor.fetchone()
            database_size_kb = database_size_bytes / 1024
        except Error as exc:
            table_count = 0
            print(f"Could not load database status: {exc}")
        finally:
            if cursor is not None:
                cursor.close()
            if connection is not None and connection.is_connected():
                connection.close()

        metrics = [
            ("Database Tables:", f"{table_count} Tables"),
            ("Estimated Records:", f"{total_records:,} Rows"),
            ("Database Storage:", f"{database_size_kb:,.1f} KB"),
            ("Last Backup:", "None Recorded"),
            ("Daily Backup:", "Manual Export (Not Scheduled)")
        ]

        for label, val in metrics:
            row_frame = tk.Frame(card_inner, bg=THEME["sub_card"])
            row_frame.pack(fill="x", pady=6)
            tk.Label(row_frame, text=label, font=FONTS["field_label"], bg=THEME["sub_card"], fg=THEME["text_muted"], width=22, anchor="w").pack(side="left")
            tk.Label(row_frame, text=val, font=("Arial", 10, "bold"), bg=THEME["sub_card"], fg=THEME["text_dark"]).pack(side="left")

        tk.Label(
            container, text="Backup & Export Actions", font=FONTS["section_label"], 
            bg=THEME["form_container"], fg=THEME["text_light"]
        ).pack(anchor="nw", pady=(15, 10))

        card_action = tk.Frame(container, bg=THEME["sub_card"], highlightbackground=THEME["border"], highlightthickness=1)
        card_action.pack(fill="x", pady=(0, 10))

        action_inner = tk.Frame(card_action, bg=THEME["sub_card"])
        action_inner.pack(fill="x", padx=20, pady=20)

        info_frame = tk.Frame(action_inner, bg=THEME["sub_card"])
        info_frame.pack(side="left")

        tk.Label(
            info_frame, text="💾 Export SQL Database", font=("Arial", 12, "bold"), 
            bg=THEME["sub_card"], fg=THEME["text_dark"]
        ).pack(anchor="nw")

        tk.Label(
            info_frame, text="Generate and download a full SQL dump of the current database.", 
            font=("Arial", 10), bg=THEME["sub_card"], fg=THEME["text_muted"]
        ).pack(anchor="nw", pady=(5, 0))

        btn_frame = tk.Frame(action_inner, bg=THEME["sub_card"])
        btn_frame.pack(side="right", pady=5)

        tk.Button(
            btn_frame, text="Export SQL", font=("Arial", 10, "bold"), 
            bg=THEME["bg_header"], fg="white", bd=0, padx=20, pady=8,
            command=self.handle_export
        ).pack(side="left", padx=5)


if __name__ == "__main__":
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from dashboard import AssetManagementApp
    app = AssetManagementApp()
    app.after(0, lambda: app.switch_tab('DB & Backups'))
    app.mainloop()
