import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import math
import os
import sys
import subprocess
import shutil
import csv
from datetime import datetime
import calendar
import mysql.connector
from mysql.connector import Error


DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "asset inventory management system",
}


def get_all_users():
    connection = mysql.connector.connect(**DB_CONFIG)
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT user_id, username, role, access_status, email
            FROM users
            ORDER BY user_id DESC
            """
        )
        return cursor.fetchall()
    finally:
        cursor.close()
        connection.close()


def update_user_status(user_id, status):
    connection = mysql.connector.connect(**DB_CONFIG)
    cursor = connection.cursor()
    try:
        cursor.execute(
            "UPDATE users SET access_status = %s WHERE user_id = %s",
            (status, user_id),
        )
        connection.commit()
        return cursor.rowcount > 0
    finally:
        cursor.close()
        connection.close()


def delete_user(user_id):
    connection = mysql.connector.connect(**DB_CONFIG)
    cursor = connection.cursor()
    try:
        cursor.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
        connection.commit()
        return cursor.rowcount > 0
    finally:
        cursor.close()
        connection.close()


def get_or_create_lookup(cursor, table, id_column, name):
    if not name or name.startswith("No "):
        return None

    cursor.execute(f"SELECT {id_column} FROM {table} WHERE name = %s", (name,))
    row = cursor.fetchone()
    if row:
        return row[id_column]

    cursor.execute(f"INSERT INTO {table} (name) VALUES (%s)", (name,))
    return cursor.lastrowid


def save_asset_and_log(asset_data, username, role, description):
    connection = mysql.connector.connect(**DB_CONFIG)
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("SELECT user_id FROM users WHERE username = %s LIMIT 1", (username,))
        user = cursor.fetchone()
        user_id = user["user_id"] if user else None

        cursor.execute(
            "SELECT category_id FROM categories WHERE name = %s LIMIT 1",
            (asset_data["category"],),
        )
        category = cursor.fetchone()
        if not category:
            cursor.execute(
                "INSERT INTO categories (name) VALUES (%s)",
                (asset_data["category"],),
            )
            category_id = cursor.lastrowid
        else:
            category_id = category["category_id"]

        supplier_id = get_or_create_lookup(
            cursor, "suppliers", "supplier_id", asset_data["supplier"]
        )
        location_id = get_or_create_lookup(
            cursor, "locations", "location_id", asset_data["location"]
        )

        cursor.execute(
            """
            SELECT asset_id, quantity FROM assets
            WHERE asset_name = %s AND brand = %s AND category_id = %s AND deleted_at IS NULL
            LIMIT 1
            """,
            (asset_data["name"], asset_data["brand"], category_id)
        )
        existing_asset = cursor.fetchone()

        if existing_asset:
            new_qty = existing_asset["quantity"] + asset_data["quantity"]
            cursor.execute(
                """
                UPDATE assets 
                SET quantity = %s, unit_price = %s, purchase_date = %s, 
                    warranty_duration = %s, supplier_id = %s, location_id = %s
                WHERE asset_id = %s
                """,
                (new_qty, asset_data["unit_price"], asset_data["purchase_date"], 
                 asset_data["warranty"], supplier_id, location_id, existing_asset["asset_id"])
            )
            asset_id = existing_asset["asset_id"]
            action = 'UPDATE'
            log_desc = f"Updated existing asset '{asset_data['name']}' (Added Qty: {asset_data['quantity']} | New Total: {new_qty})"
        else:
            cursor.execute(
                """
                INSERT INTO assets
                    (asset_name, brand, category_id, quantity, unit_price,
                     status, purchase_date, warranty_duration, supplier_id, location_id, created_by)
                VALUES
                    (%s, %s, %s, %s, %s, 'In Stock', %s, %s, %s, %s, %s)
                """,
                (
                    asset_data["name"],
                    asset_data["brand"],
                    category_id,
                    asset_data["quantity"],
                    asset_data["unit_price"],
                    asset_data["purchase_date"],
                    asset_data["warranty"],
                    supplier_id,
                    location_id,
                    user_id,
                ),
            )
            asset_id = cursor.lastrowid
            action = 'CREATE'
            log_desc = f"Added new asset '{asset_data['name']}' (Added Qty: {asset_data['quantity']})"

        cursor.execute(
            """
            INSERT INTO activity_logs (user_id, username, role, action, description)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (user_id, username, role, action, log_desc),
        )
        connection.commit()
        return asset_id
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()

# ==========================================
# 1. CONFIGURATION & THEME
# ==========================================
THEME = {
    "bg_main": "white",
    "bg_header": "#3A6080",
    "bg_sidebar": "#2A4863",
    "bg_sidebar_active": "#1B3041",
    "bg_card": "#F4F6F9",
    "text_light": "white",
    "text_dark": "#333333",
    "text_muted": "#555555",
    "accent_danger": "#E74C3C",
    "accent_success": "#27AE60",
    "border": "#E0E0E0",
    "form_container": "#2A648F",
    "sub_card": "#E2E5E9"
}

FONTS = {
    "title": ("Arial", 16, "bold"),
    "header": ("Arial", 14, "bold"),
    "logo": ("Arial", 16, "bold"),
    "sidebar": ("Arial", 11),
    "section_label": ("Arial", 10, "bold italic"),
    "field_label": ("Arial", 9, "bold"),
    "card_title": ("Arial", 10, "bold"),     
    "card_value": ("Arial", 18, "bold")      
}

class AssetManagementApp(tk.Tk):
    def __init__(self):
        super().__init__()
        
        self.title("Asset Inventory Management")
        self.geometry("1100x750")
        self.configure(bg=THEME["bg_main"])
        
        try:
            self.state('zoomed') 
        except tk.TclError:
            self.attributes('-zoomed', True) 
            
        self.system_icon = self.load_system_icon()
        if self.system_icon:
            self.iconphoto(True, self.system_icon)
            
        self.vcmd_qty = (self.register(self.validate_qty), '%P')
        
        self.supplier_options_list = []
        self.location_options_list = []
        self.load_dropdown_options()

        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure(
            "Treeview.Heading", font=("Arial", 10, "bold"), 
            background=THEME["bg_header"], foreground="white"
        )
        self.style.configure(
            "Treeview", font=("Arial", 10), rowheight=30, 
            background=THEME["bg_card"], fieldbackground=THEME["bg_card"]
        )
        self.style.map("Treeview", background=[("selected", THEME["bg_sidebar_active"])])
        
        self.val_total_stored = tk.StringVar(value="--")
        self.val_asset_value = tk.StringVar(value="--")
        self.val_low_stock = tk.StringVar(value="--")
        self.val_recent_added = tk.StringVar(value="--")
        self.val_top_suppliers = tk.StringVar(value="--")
        self.val_monthly_exp = tk.StringVar(value="--")
        self.quantity_undo_stack = []
        
        self.accounts_data = []
        self.logs_data = [] 
        self.notif_frame = None 
        self.notification_button = None
        self.latest_notification_id = 0
        self.unread_notification_count = 0
        
        self.setup_ui()
        self.switch_tab("Inventory") 
        self.start_dashboard_refresh()

    # ==========================================
    # 2. CORE LAYOUT (Header, Sidebar, Content)
    # ==========================================
    def setup_ui(self):
        self.create_header()
        
        self.body_frame = tk.Frame(self, bg=THEME["bg_main"])
        self.body_frame.pack(side="bottom", fill="both", expand=True)
        
        self.create_sidebar()
        self.create_content_area()

    def create_header(self):
        header = tk.Frame(self, bg=THEME["bg_header"], height=60)
        header.pack(side="top", fill="x")
        header.pack_propagate(False)
        
        tk.Label(
            header, text=" 📦 ASSET INVENTORY", font=FONTS["logo"], 
            bg=THEME["bg_header"], fg=THEME["text_light"]
        ).pack(side="left", padx=20)
        
        right_frame = tk.Frame(header, bg=THEME["bg_header"])
        right_frame.pack(side="right", padx=20)

        self.notification_button = tk.Button(
            right_frame, text="🔔", font=("Arial", 15),
            bg=THEME["bg_header"], fg=THEME["text_light"], bd=0,
            activebackground=THEME["bg_header"], activeforeground=THEME["text_light"],
            cursor="hand2", command=self.toggle_notifications
        )
        self.notification_button.pack(side="left", padx=(0, 15))
        
        tk.Label(
            right_frame, text="ADMIN 👤", font=FONTS["header"], 
            bg=THEME["bg_header"], fg=THEME["text_light"]
        ).pack(side="left")

    def create_sidebar(self):
        sidebar = tk.Frame(self.body_frame, bg=THEME["bg_sidebar"], width=230)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        
        tk.Frame(sidebar, bg=THEME["bg_sidebar"], height=20).pack(fill="x")
        
        tabs = [
            ("📊", "Dashboard"), 
            ("📦", "Inventory"), 
            ("➕", "Add Asset"), 
            ("👥", "Account Management"), 
            ("📝", "Logs"), 
            ("💾", "DB & Backups"),
            ("🗑️", "Bin")
        ]
        
        for icon, tab in tabs:
            btn_text = f"{icon}    {tab}"
            tk.Button(
                sidebar, text=btn_text, font=FONTS["sidebar"], 
                bg=THEME["bg_sidebar"], fg=THEME["text_light"], 
                bd=0, anchor="w", padx=20, pady=12,
                activebackground=THEME["bg_sidebar_active"], 
                activeforeground=THEME["text_light"],
                command=lambda t=tab: self.switch_tab(t)
            ).pack(fill="x")
            
        tk.Button(
            sidebar, text="🚪    Log Out", font=("Arial", 11, "bold"), 
            bg=THEME["bg_sidebar"], fg="#FF9999", 
            bd=0, anchor="w", padx=20, pady=15,
            activebackground=THEME["bg_sidebar_active"], 
            activeforeground="#FF5555",
            command=self.handle_logout
        ).pack(side="bottom", fill="x")

    def create_content_area(self):
        self.content_frame = tk.Frame(self.body_frame, bg=THEME["bg_main"])
        self.content_frame.pack(side="right", fill="both", expand=True)

    # ==========================================
    # 3. TAB NAVIGATION & NOTIFICATIONS
    # ==========================================
    def switch_tab(self, tab_name):
        if self.notif_frame and self.notif_frame.winfo_exists():
            self.notif_frame.destroy()

        for widget in self.content_frame.winfo_children():
            widget.destroy()
            
        if tab_name == "Dashboard":
            self.render_dashboard()
        elif tab_name == "Inventory":
            self.render_inventory()
        elif tab_name == "Add Asset":
            self.render_add_asset()
        elif tab_name == "Account Management":
            self.render_account_management()
        elif tab_name == "Logs":
            self.render_logs()
        elif tab_name == "DB & Backups":
            self.render_db_backups()
        elif tab_name == "Bin":
            self.render_bin()
        else:
            self.render_placeholder(tab_name)

    def toggle_notifications(self):
        if self.notif_frame and self.notif_frame.winfo_exists():
            self.notif_frame.destroy()
        else:
            self.unread_notification_count = 0
            self.notification_button.configure(text="🔔")
            self.notif_frame = tk.Frame(self, bg="white", highlightbackground=THEME["border"], highlightthickness=1)
            self.notif_frame.place(relx=1.0, x=-330, y=60, width=300, height=320)
            
            header_frm = tk.Frame(self.notif_frame, bg=THEME["bg_sidebar"])
            header_frm.pack(fill="x")
            tk.Label(header_frm, text="Notifications", font=("Arial", 10, "bold"), bg=THEME["bg_sidebar"], fg="white").pack(side="left", padx=10, pady=8)
            
            content_frm = tk.Frame(self.notif_frame, bg="white")
            content_frm.pack(fill="both", expand=True)
            try:
                connection = mysql.connector.connect(**DB_CONFIG)
                cursor = connection.cursor(dictionary=True)
                cursor.execute(
                    """
                    SELECT username, role, action, description, created_at
                    FROM activity_logs
                    WHERE action IN ('CREATE', 'UPDATE', 'DELETE')
                    ORDER BY created_at DESC, log_id DESC
                    LIMIT 3
                    """
                )
                notifications = cursor.fetchall()
            except Error as exc:
                notifications = []
                print(f"Could not load notifications: {exc}")
            finally:
                if "cursor" in locals():
                    cursor.close()
                if "connection" in locals():
                    connection.close()

            if not notifications:
                tk.Label(
                    content_frm,
                    text="No recent notifications.",
                    font=("Arial", 10),
                    bg="white",
                    fg=THEME["text_muted"],
                    wraplength=270,
                ).pack(expand=True)
                return

            for notification in notifications:
                time_text = notification["created_at"].strftime("%Y-%m-%d %H:%M")
                tk.Label(
                    content_frm,
                    text=f"{notification['username']} ({notification['role']})\n{notification['action']}: {notification['description']}\n{time_text}",
                    font=("Arial", 9),
                    bg="white",
                    fg=THEME["text_dark"],
                    justify="left",
                    anchor="w",
                    wraplength=280,
                    padx=8,
                    pady=3,
                ).pack(fill="x")

    def refresh_notification_ping(self):
        try:
            connection = mysql.connector.connect(**DB_CONFIG)
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT COALESCE(MAX(log_id), 0)
                FROM activity_logs
                WHERE action IN ('CREATE', 'UPDATE', 'DELETE')
                """
            )
            latest_id = cursor.fetchone()[0]
        except Error as exc:
            print(f"Could not check notifications: {exc}")
            return
        finally:
            if "cursor" in locals():
                cursor.close()
            if "connection" in locals():
                connection.close()

        if self.latest_notification_id == 0:
            self.latest_notification_id = latest_id
        elif latest_id > self.latest_notification_id:
            cursor_result = latest_id - self.latest_notification_id
            self.latest_notification_id = latest_id
            self.unread_notification_count += max(1, cursor_result)
            if hasattr(self, "notification_button") and self.notification_button:
                self.notification_button.configure(
                    text=f"🔔 {self.unread_notification_count}"
                )
                self.bell()

    # ==========================================
    # 4. DASHBOARD INTERFACE
    # ==========================================
    def refresh_dashboard_data(self):
        try:
            connection = mysql.connector.connect(**DB_CONFIG)
            cursor = connection.cursor(dictionary=True)

            cursor.execute(
                """
                SELECT COALESCE(SUM(quantity), 0) AS total_stored,
                       COALESCE(SUM(quantity * unit_price), 0) AS total_value
                FROM assets
                WHERE deleted_at IS NULL
                """
            )
            summary = cursor.fetchone()

            cursor.execute(
                """
                SELECT description FROM activity_logs
                WHERE created_at >= DATE_SUB(CURRENT_TIMESTAMP, INTERVAL 30 DAY)
                """
            )
            recent_added_qty = 0
            for row in cursor.fetchall():
                desc = row["description"]
                if "Added Qty:" in desc:
                    try:
                        qty_str = desc.split("Added Qty:")[1].split("|")[0].split(")")[0].strip()
                        recent_added_qty += int(qty_str)
                    except:
                        pass
                elif "Qty:" in desc:
                    try:
                        qty_str = desc.split("Qty:")[1].split(")")[0].strip()
                        recent_added_qty += int(qty_str)
                    except:
                        pass

            cursor.execute(
                """
                SELECT a.asset_name AS name, a.quantity
                FROM assets a
                WHERE a.deleted_at IS NULL AND a.quantity <= 5
                ORDER BY a.quantity ASC, a.asset_name ASC
                LIMIT 3
                """
            )
            low_stock_categories = cursor.fetchall()

            cursor.execute(
                """
                SELECT COALESCE(s.name, 'No Supplier Added') AS supplier,
                       COALESCE(SUM(a.quantity), 0) AS volume
                FROM assets a
                LEFT JOIN suppliers s ON s.supplier_id = a.supplier_id
                WHERE a.deleted_at IS NULL
                GROUP BY supplier
                ORDER BY volume DESC
                LIMIT 1
                """
            )
            top_supplier = cursor.fetchone()

            cursor.execute(
                """
                SELECT COALESCE(SUM(quantity * unit_price), 0) AS monthly_expense
                FROM assets
                WHERE created_at >= DATE_FORMAT(CURRENT_TIMESTAMP, '%Y-%m-01') AND deleted_at IS NULL
                """
            )
            monthly_expense = cursor.fetchone()

            cursor.execute(
                """
                SELECT c.name, COALESCE(SUM(a.quantity), 0) AS quantity
                FROM assets a
                JOIN categories c ON c.category_id = a.category_id
                WHERE a.deleted_at IS NULL
                GROUP BY c.category_id, c.name
                """
            )
            category_rows = cursor.fetchall()

            cursor.execute(
                """
                SELECT created_at, username, role,
                       CONCAT(action, ': ', description) AS activity
                FROM activity_logs
                ORDER BY log_id DESC
                LIMIT 5
                """
            )
            recent_logs = cursor.fetchall()
        except Error as exc:
            messagebox.showerror("Database Error", f"Could not refresh dashboard.\n{exc}")
            return
        finally:
            if "cursor" in locals():
                cursor.close()
            if "connection" in locals():
                connection.close()

        self.val_total_stored.set(str(summary["total_stored"]))
        self.val_asset_value.set(f"${summary['total_value']:,.2f}")
        low_stock_names = [
            f"{row['name']} ({'Critical' if row['quantity'] <= 1 else 'Low Stock'}: {row['quantity']})"
            for row in low_stock_categories
        ]
        self.val_low_stock.set("\n".join(low_stock_names) if low_stock_names else "No Low Stock")
        self.val_recent_added.set(str(recent_added_qty))
        self.val_top_suppliers.set(
            f"{top_supplier['supplier']} ({top_supplier['volume']})"
            if top_supplier else "None"
        )
        self.val_monthly_exp.set(f"${monthly_expense['monthly_expense']:,.2f}")

        category_counts = {"Hardware": 0, "Peripherals": 0, "Networking": 0}
        for category in category_rows:
            name = category["name"].lower()
            if "network" in name:
                category_counts["Networking"] += category["quantity"]
            elif "peripheral" in name or "av" in name or "media" in name:
                category_counts["Peripherals"] += category["quantity"]
            else:
                category_counts["Hardware"] += category["quantity"]

        if hasattr(self, "pie_canvas") and self.pie_canvas.winfo_exists():
            self.update_pie_chart(category_counts)

        if hasattr(self, "recent_activity_frame") and self.recent_activity_frame.winfo_exists():
            for widget in self.recent_activity_frame.winfo_children():
                widget.destroy()
            if not recent_logs:
                tk.Label(
                    self.recent_activity_frame, text="-- No recent activity --",
                    font=("Arial", 10, "italic"), bg=THEME["bg_card"], fg=THEME["text_muted"]
                ).pack(expand=True)
            else:
                for log in recent_logs:
                    timestamp = log["created_at"].strftime("%Y-%m-%d %H:%M")
                    tk.Label(
                        self.recent_activity_frame,
                        text=f"{timestamp}  {log['username']} - {log['activity']}",
                        font=("Arial", 9), bg=THEME["bg_card"], fg=THEME["text_dark"],
                        anchor="nw", justify="left", wraplength=360
                    ).pack(fill="x", pady=2)
                self.recent_activity_frame.update_idletasks()
                if hasattr(self, "recent_activity_canvas"):
                    self.recent_activity_canvas.configure(
                        scrollregion=self.recent_activity_canvas.bbox("all")
                    )

    def start_dashboard_refresh(self):
        def refresh_periodically():
            if self.winfo_exists():
                self.refresh_dashboard_data()
                self.refresh_notification_ping()
                self.after(5000, refresh_periodically)

        self.after(5000, refresh_periodically)

    def render_dashboard(self):
        dashboard_wrapper = tk.Frame(self.content_frame, bg=THEME["bg_main"])
        dashboard_wrapper.pack(fill="both", expand=True, padx=30, pady=(35, 35))

        tk.Label(
            dashboard_wrapper, text="Dashboard Overview", 
            font=FONTS["title"], bg=THEME["bg_main"], fg=THEME["bg_header"]
        ).pack(pady=(0, 15), anchor="nw")
        
        cards_container = tk.Frame(dashboard_wrapper, bg=THEME["bg_main"])
        cards_container.pack(fill="x", padx=0)
        
        row1 = tk.Frame(cards_container, bg=THEME["bg_main"])
        row1.pack(fill="x", pady=(0, 10))
        self._create_metric_card(row1, "Total Stored Asset", self.val_total_stored, THEME["bg_header"])
        self._create_metric_card(row1, "Total Asset Value", self.val_asset_value, THEME["bg_header"])
        self._create_metric_card(row1, "Low Stock / Critical Items", self.val_low_stock, THEME["accent_danger"])

        row2 = tk.Frame(cards_container, bg=THEME["bg_main"])
        row2.pack(fill="x", pady=(0, 10))
        self._create_metric_card(row2, "Recently Added Assets", self.val_recent_added, THEME["bg_header"])
        self._create_metric_card(row2, "Top Suppliers by Volume", self.val_top_suppliers, THEME["bg_header"])
        self._create_metric_card(row2, "Monthly Expenditure", self.val_monthly_exp, THEME["bg_header"])

        bottom_outer = tk.Frame(dashboard_wrapper, bg=THEME["bg_main"])
        bottom_outer.pack(fill="x", pady=(10, 0))

        bottom_container = tk.Frame(bottom_outer, bg=THEME["bg_main"])
        bottom_container.pack(anchor="center")

        pie_frame = tk.Frame(bottom_container, bg=THEME["bg_card"], highlightbackground=THEME["border"], highlightthickness=1)
        pie_frame.pack(side="left", fill="y", padx=(0, 15))
        
        tk.Label(pie_frame, text="Stock Categories", font=("Arial", 12, "bold"), bg=THEME["bg_card"], fg=THEME["text_dark"]).pack(anchor="nw", padx=15, pady=(15, 5))
        
        pie_wrapper = tk.Frame(pie_frame, bg=THEME["bg_card"])
        pie_wrapper.pack(side="top", anchor="nw", fill="x", padx=10, pady=5)

        self.pie_canvas = tk.Canvas(pie_wrapper, bg=THEME["bg_card"], highlightthickness=0, width=160, height=160)
        self.pie_canvas.pack(side="left", padx=5, pady=5)
        
        legend_frame = tk.Frame(pie_wrapper, bg=THEME["bg_card"])
        legend_frame.pack(side="left", padx=(10, 15), pady=10, anchor="w")
        tk.Label(legend_frame, text="■ Hardware", font=("Arial", 9), bg=THEME["bg_card"], fg="#3A6080").pack(anchor="w", pady=4)
        tk.Label(legend_frame, text="■ Peripherals", font=("Arial", 9), bg=THEME["bg_card"], fg="#5A80A0").pack(anchor="w", pady=4)
        tk.Label(legend_frame, text="■ Networking", font=("Arial", 9), bg=THEME["bg_card"], fg="#E74C3C").pack(anchor="w", pady=4)

        self.update_pie_chart({"Hardware": 0, "Peripherals": 0, "Networking": 0})

        activity_frame = tk.Frame(bottom_container, bg=THEME["bg_card"], highlightbackground=THEME["border"], highlightthickness=1, width=400)
        activity_frame.pack(side="left", fill="y")
        activity_frame.pack_propagate(False)
        
        tk.Label(activity_frame, text="Recent Activity Logs", font=("Arial", 12, "bold"), bg=THEME["bg_card"], fg=THEME["text_dark"]).pack(anchor="nw", padx=15, pady=(15, 5))
        
        act_content = tk.Frame(activity_frame, bg=THEME["bg_card"], height=160)
        act_content.pack(fill="both", expand=True, padx=(15, 0), pady=(0, 15))
        act_content.pack_propagate(False)

        self.recent_activity_canvas = tk.Canvas(
            act_content, bg=THEME["bg_card"], highlightthickness=0
        )
        activity_scroll = ttk.Scrollbar(
            act_content, orient="vertical", command=self.recent_activity_canvas.yview
        )
        self.recent_activity_canvas.configure(yscrollcommand=activity_scroll.set)
        activity_scroll.pack(side="right", fill="y")
        self.recent_activity_canvas.pack(side="left", fill="both", expand=True)
        self.recent_activity_canvas.bind(
            "<Configure>",
            lambda event: self.recent_activity_canvas.itemconfigure(
                self.recent_activity_window, width=event.width
            ),
        )

        self.recent_activity_frame = tk.Frame(
            self.recent_activity_canvas, bg=THEME["bg_card"]
        )
        self.recent_activity_window = self.recent_activity_canvas.create_window(
            (0, 0), window=self.recent_activity_frame, anchor="nw"
        )
        self.recent_activity_frame.bind(
            "<Configure>",
            lambda event: self.recent_activity_canvas.configure(
                scrollregion=self.recent_activity_canvas.bbox("all")
            ),
        )

        self.refresh_dashboard_data()

    def _create_metric_card(self, parent, title, textvariable, value_color):
        card = tk.Frame(parent, bg=THEME["bg_card"], highlightbackground=THEME["border"], highlightthickness=1)
        card.pack(side="left", fill="both", expand=True, padx=10, ipady=15)
        tk.Label(card, text=title, font=FONTS["card_title"], bg=THEME["bg_card"], fg=THEME["text_muted"]).pack(pady=(10, 0))
        tk.Label(
            card,
            textvariable=textvariable,
            font=("Arial", 11, "bold"),
            bg=THEME["bg_card"],
            fg=value_color,
            justify="center",
            wraplength=250,
        ).pack(pady=(5, 10))

    def update_pie_chart(self, category_counts):
        self.pie_canvas.delete("all")
        total = sum(category_counts.values())

        if total == 0:
            self.pie_canvas.create_oval(10, 10, 150, 150, fill="#E0E0E0", outline="#FFFFFF", width=2)
            self.pie_canvas.create_text(80, 80, text="0%", font=("Arial", 9, "bold"), fill="#888888")
            return

        colors = {"Hardware": "#3A6080", "Peripherals": "#5A80A0", "Networking": "#E74C3C"}
        start_angle = 90
        
        for category, count in category_counts.items():
            if count <= 0: continue
            
            color = colors.get(category, "#888888")
            pct = round((count / total) * 100)
            
            if count == total:
                self.pie_canvas.create_oval(10, 10, 150, 150, fill=color, outline=THEME["bg_card"], width=2)
                self.pie_canvas.create_text(80, 80, text=f"{pct}%", font=("Arial", 10, "bold"), fill="white")
                break
                
            extent = (count / total) * 360
            self.pie_canvas.create_arc(10, 10, 150, 150, start=start_angle, extent=extent, fill=color, outline=THEME["bg_card"], width=2, style=tk.PIESLICE)
            mid_angle_rad = math.radians(start_angle + (extent / 2))
            self.pie_canvas.create_text(80 + 35 * math.cos(mid_angle_rad), 80 - 35 * math.sin(mid_angle_rad), text=f"{pct}%", font=("Arial", 9, "bold"), fill="white")
            start_angle += extent

    # ==========================================
    # 5. INVENTORY INTERFACE
    # ==========================================
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

    def load_inventory(self):
        try:
            connection = mysql.connector.connect(**DB_CONFIG)
            cursor = connection.cursor(dictionary=True)
            cursor.execute(
                """
                SELECT a.asset_id, a.asset_name, c.name AS category,
                       a.status, a.quantity, a.brand
                FROM assets a
                JOIN categories c ON c.category_id = a.category_id
                WHERE a.deleted_at IS NULL
                ORDER BY a.asset_id DESC
                """
            )
            assets = cursor.fetchall()
            cursor.execute("SELECT name FROM categories ORDER BY name ASC")
            categories = [row["name"] for row in cursor.fetchall()]
        except Error as exc:
            messagebox.showerror("Database Error", f"Could not load assets.\n{exc}")
            assets = []
            categories = []
        finally:
            if "cursor" in locals():
                cursor.close()
            if "connection" in locals():
                connection.close()

        self.inventory_assets = assets
        if hasattr(self, "inventory_category_combo"):
            selected_category = self.inventory_category_combo.get()
            self.inventory_category_combo["values"] = ["All Categories", *categories]
            if selected_category in ["All Categories", *categories]:
                self.inventory_category_combo.set(selected_category)
            else:
                self.inventory_category_combo.set("All Categories")
        self.apply_inventory_filters()

    def _clear_inventory_search_placeholder(self, event=None):
        if self.inventory_search_entry.get() == "Search assets...":
            self.inventory_search_entry.delete(0, tk.END)

    def _restore_inventory_search_placeholder(self, event=None):
        if not self.inventory_search_entry.get().strip():
            self.inventory_search_entry.insert(0, "Search assets...")

    def apply_inventory_filters(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        search_text = self.inventory_search_entry.get().strip().lower()
        if search_text == "search assets...":
            search_text = ""
        category = self.inventory_category_combo.get()

        for asset in getattr(self, "inventory_assets", []):
            if category != "All Categories" and asset["category"] != category:
                continue
            searchable_values = (
                str(asset["asset_id"]),
                asset["asset_name"],
                asset["category"],
                asset["status"],
                str(asset["quantity"]),
                asset["brand"],
            )
            if search_text and not any(search_text in str(value).lower() for value in searchable_values):
                continue
            self.tree.insert(
                "", "end",
                values=(
                    asset["asset_id"], asset["asset_name"], asset["category"],
                    asset["status"], asset["quantity"],
                    asset["brand"],
                ),
            )

    def decrease_asset_quantity(self):
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning(
                "Selection Warning",
                "Please select one or more assets to decrease quantity.",
            )
            return

        decrease_by = simpledialog.askinteger(
            "Decrease Quantity",
            "Enter quantity to decrease:",
            parent=self,
            minvalue=1,
        )
        if decrease_by is None:
            return

        connection = None
        cursor = None
        try:
            connection = mysql.connector.connect(**DB_CONFIG)
            cursor = connection.cursor(dictionary=True)
            low_stock_items = []
            undo_items = []
            cursor.execute("SELECT user_id FROM users WHERE username = 'admin' LIMIT 1")
            admin = cursor.fetchone()
            admin_id = admin["user_id"] if admin else None

            for item in selected_items:
                values = self.tree.item(item, "values")
                asset_id = values[0]
                asset_name = values[1]
                cursor.execute(
                    "SELECT quantity FROM assets WHERE asset_id = %s AND deleted_at IS NULL",
                    (asset_id,),
                )
                asset = cursor.fetchone()
                if not asset:
                    continue

                current_quantity = asset["quantity"]
                if decrease_by > current_quantity:
                    raise ValueError(
                        f"Cannot decrease '{asset_name}' by {decrease_by}; "
                        f"available quantity is {current_quantity}."
                    )

                new_quantity = current_quantity - decrease_by
                cursor.execute(
                    "UPDATE assets SET quantity = %s WHERE asset_id = %s",
                    (new_quantity, asset_id),
                )
                cursor.execute(
                    """
                    INSERT INTO activity_logs (user_id, username, role, action, description)
                    VALUES (%s, 'admin', 'Admin', 'UPDATE', %s)
                    """,
                    (
                        admin_id,
                        f"Decreased quantity for asset '{asset_name}' (ID: {asset_id}; "
                        f"Removed: {decrease_by}; Previous: {current_quantity}; New: {new_quantity})",
                    ),
                )
                undo_items.append((asset_id, asset_name, decrease_by))
                if new_quantity <= 5:
                    level = "Critical" if new_quantity <= 1 else "Low Stock"
                    low_stock_items.append(f"{asset_name} ({level}: {new_quantity})")

            connection.commit()
            self.quantity_undo_stack.append(undo_items)
            self.load_inventory()
            self.refresh_dashboard_data()

            if low_stock_items:
                messagebox.showwarning(
                    "Low Stock / Critical Item",
                    "Remaining stock:\n" + "\n".join(low_stock_items),
                    parent=self,
                )
            else:
                messagebox.showinfo(
                    "Quantity Updated",
                    "Selected asset quantities were decreased.",
                    parent=self,
                )
        except ValueError as exc:
            if connection is not None:
                connection.rollback()
            messagebox.showerror("Invalid Quantity", str(exc), parent=self)
        except Error as exc:
            if connection is not None:
                connection.rollback()
            messagebox.showerror(
                "Database Error",
                f"Could not decrease asset quantity.\n{exc}",
                parent=self,
            )
        finally:
            if cursor is not None:
                cursor.close()
            if connection is not None and connection.is_connected():
                connection.close()

    def undo_last_quantity_decrease(self):
        if not self.quantity_undo_stack:
            messagebox.showinfo(
                "Nothing to Undo",
                "There is no recent quantity decrease to undo.",
                parent=self,
            )
            return

        undo_items = self.quantity_undo_stack[-1]
        if not messagebox.askyesno(
            "Confirm Undo",
            "Are you sure you want to undo the latest quantity decrease?",
            parent=self,
        ):
            return
        connection = None
        cursor = None
        try:
            connection = mysql.connector.connect(**DB_CONFIG)
            cursor = connection.cursor(dictionary=True)
            cursor.execute(
                "SELECT user_id FROM users WHERE username = 'admin' LIMIT 1"
            )
            admin = cursor.fetchone()
            admin_id = admin["user_id"] if admin else None

            for asset_id, asset_name, restored_quantity in undo_items:
                cursor.execute(
                    """
                    UPDATE assets
                    SET quantity = quantity + %s
                    WHERE asset_id = %s AND deleted_at IS NULL
                    """,
                    (restored_quantity, asset_id),
                )
                cursor.execute(
                    """
                    INSERT INTO activity_logs (user_id, username, role, action, description)
                    VALUES (%s, 'admin', 'Admin', 'UPDATE', %s)
                    """,
                    (
                        admin_id,
                        f"Undid quantity decrease for asset '{asset_name}' "
                        f"(ID: {asset_id}; Restored: {restored_quantity})",
                    ),
                )

            connection.commit()
            self.quantity_undo_stack.pop()
            self.load_inventory()
            self.refresh_dashboard_data()
            messagebox.showinfo(
                "Decrease Undone",
                "The latest quantity decrease was restored.",
                parent=self,
            )
        except Error as exc:
            if connection is not None:
                connection.rollback()
            messagebox.showerror(
                "Database Error",
                f"Could not undo the quantity decrease.\n{exc}",
                parent=self,
            )
        finally:
            if cursor is not None:
                cursor.close()
            if connection is not None and connection.is_connected():
                connection.close()

    def soft_delete_asset(self):
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("Selection Warning", "Please select one or more assets to remove.")
            return

        if not messagebox.askyesno("Confirm Remove", "Move selected asset(s) to the Bin?"):
            return

        try:
            connection = mysql.connector.connect(**DB_CONFIG)
            cursor = connection.cursor()
            
            cursor.execute("SELECT user_id FROM users WHERE username = 'admin' LIMIT 1")
            admin_row = cursor.fetchone()
            admin_id = admin_row[0] if admin_row else None

            for item in selected_items:
                values = self.tree.item(item, "values")
                asset_id = values[0]
                asset_name = values[1]

                cursor.execute(
                    "UPDATE assets SET deleted_at = CURRENT_TIMESTAMP, deleted_by = %s WHERE asset_id = %s",
                    (admin_id, asset_id)
                )
                
                cursor.execute(
                    """
                    INSERT INTO activity_logs (user_id, username, role, action, description)
                    VALUES (%s, 'admin', 'Admin', 'DELETE', %s)
                    """,
                    (admin_id, f"Moved asset '{asset_name}' (ID: {asset_id}) to the Bin")
                )

            connection.commit()
            messagebox.showinfo("Success", "Selected asset(s) moved to the Bin.")
            self.load_inventory()
            self.refresh_dashboard_data()
        except Error as exc:
            messagebox.showerror("Database Error", f"Could not move assets to bin.\n{exc}")
        finally:
            if "cursor" in locals():
                cursor.close()
            if "connection" in locals():
                connection.close()

    # ==========================================
    # 6. ADD ASSET INTERFACE
    # ==========================================
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
        
        tk.Button(date_sub, text="📅", font=("Arial", 9), bg=THEME["bg_header"], fg="white", command=self.open_calendar_popup).pack(side="left")

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

    # ==========================================
    # 7. ACCOUNT MANAGEMENT INTERFACE
    # ==========================================
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

    # ==========================================
    # 8. LOGS INTERFACE
    # ==========================================
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

    # ==========================================
    # 9. DB & BACKUPS INTERFACE
    # ==========================================
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

    # ==========================================
    # 10. BIN INTERFACE (Retrieve or Delete Permanently)
    # ==========================================
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

    def load_bin_items(self):
        try:
            connection = mysql.connector.connect(**DB_CONFIG)
            cursor = connection.cursor(dictionary=True)
            cursor.execute(
                """
                SELECT a.asset_id, a.asset_name, c.name AS category,
                       a.status, a.quantity, a.deleted_at
                FROM assets a
                JOIN categories c ON c.category_id = a.category_id
                WHERE a.deleted_at IS NOT NULL
                ORDER BY a.deleted_at DESC
                """
            )
            deleted_assets = cursor.fetchall()
        except Error as exc:
            messagebox.showerror("Database Error", f"Could not load bin items.\n{exc}")
            deleted_assets = []
        finally:
            if "cursor" in locals():
                cursor.close()
            if "connection" in locals():
                connection.close()

        for item in self.bin_tree.get_children():
            self.bin_tree.delete(item)
        for asset in deleted_assets:
            del_time = asset["deleted_at"].strftime("%Y-%m-%d %H:%M:%S") if hasattr(asset["deleted_at"], "strftime") else str(asset["deleted_at"])
            self.bin_tree.insert(
                "", "end",
                values=(
                    asset["asset_id"], asset["asset_name"], asset["category"],
                    asset["status"], asset["quantity"], del_time
                ),
            )

    def restore_asset(self):
        selected_items = self.bin_tree.selection()
        if not selected_items:
            messagebox.showwarning("Selection Warning", "Please select asset(s) to restore.")
            return

        if not messagebox.askyesno("Confirm Restore", "Restore selected asset(s) back to active inventory?"):
            return

        try:
            connection = mysql.connector.connect(**DB_CONFIG)
            cursor = connection.cursor()

            for item in selected_items:
                values = self.bin_tree.item(item, "values")
                asset_id = values[0]
                asset_name = values[1]

                cursor.execute(
                    "UPDATE assets SET deleted_at = NULL, deleted_by = NULL WHERE asset_id = %s",
                    (asset_id,)
                )
                cursor.execute(
                    """
                    INSERT INTO activity_logs (username, role, action, description)
                    VALUES ('admin', 'Admin', 'UPDATE', %s)
                    """,
                    (f"Restored asset '{asset_name}' (ID: {asset_id}) from the Bin",)
                )

            connection.commit()
            messagebox.showinfo("Success", "Selected asset(s) successfully restored.")
            self.load_bin_items()
            self.refresh_dashboard_data()
        except Error as exc:
            messagebox.showerror("Database Error", f"Could not restore assets.\n{exc}")
        finally:
            if "cursor" in locals():
                cursor.close()
            if "connection" in locals():
                connection.close()

    def delete_permanently(self):
        selected_items = self.bin_tree.selection()
        if not selected_items:
            messagebox.showwarning("Selection Warning", "Please select asset(s) to delete permanently.")
            return

        if not messagebox.askyesno("Confirm Permanent Deletion", "Are you sure you want to PERMANENTLY delete these items? This action cannot be undone."):
            return

        try:
            connection = mysql.connector.connect(**DB_CONFIG)
            cursor = connection.cursor()

            for item in selected_items:
                values = self.bin_tree.item(item, "values")
                asset_id = values[0]
                asset_name = values[1]

                cursor.execute("DELETE FROM assets WHERE asset_id = %s", (asset_id,))
                cursor.execute(
                    """
                    INSERT INTO activity_logs (username, role, action, description)
                    VALUES ('admin', 'Admin', 'DELETE', %s)
                    """,
                    (f"Permanently deleted asset '{asset_name}' (ID: {asset_id}) from the Bin",)
                )

            connection.commit()
            messagebox.showinfo("Success", "Selected asset(s) permanently deleted.")
            self.load_bin_items()
        except Error as exc:
            messagebox.showerror("Database Error", f"Could not delete assets permanently.\n{exc}")
        finally:
            if "cursor" in locals():
                cursor.close()
            if "connection" in locals():
                connection.close()

    # ==========================================
    # 11. FORM UTILITIES & VALIDATION
    # ==========================================
    def load_dropdown_options(self):
        connection = None
        cursor = None
        try:
            connection = mysql.connector.connect(**DB_CONFIG)
            cursor = connection.cursor(dictionary=True)

            cursor.execute("SELECT name FROM suppliers ORDER BY name ASC")
            self.supplier_options_list = [
                row["name"] for row in cursor.fetchall()
            ]

            cursor.execute("SELECT name FROM locations ORDER BY name ASC")
            self.location_options_list = [
                row["name"] for row in cursor.fetchall()
            ]
        except Error as exc:
            print(f"Notice: Could not load supplier and location options. {exc}")
        finally:
            if cursor is not None:
                cursor.close()
            if connection is not None and connection.is_connected():
                connection.close()

    def handle_logout(self):
        if messagebox.askyesno("Confirm Logout", "Are you sure you want to log out of the admin portal?"):
            self.destroy()
            login_script = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "Login",
                "login.py",
            )
            subprocess.Popen([sys.executable, login_script], cwd=os.path.dirname(login_script))

    def handle_export(self):
        if not messagebox.askyesno(
            "Confirm Export",
            "Export the complete asset inventory database to a SQL file?",
        ):
            return

        default_name = f"{DB_CONFIG['database']}_backup_{datetime.now():%Y%m%d_%H%M%S}.sql"
        file_path = filedialog.asksaveasfilename(
            parent=self,
            title="Save SQL Database Backup",
            initialfile=default_name.replace(" ", "_"),
            defaultextension=".sql",
            filetypes=[("SQL files", "*.sql"), ("All files", "*.*")],
        )
        if not file_path:
            return

        mysqldump = shutil.which("mysqldump")
        if mysqldump:
            try:
                command = [
                    mysqldump,
                    f"--host={DB_CONFIG['host']}",
                    f"--user={DB_CONFIG['user']}",
                    "--single-transaction",
                    "--routines",
                    "--events",
                    "--triggers",
                    "--result-file",
                    file_path,
                    DB_CONFIG["database"],
                ]
                dump_environment = os.environ.copy()
                if DB_CONFIG["password"]:
                    dump_environment["MYSQL_PWD"] = DB_CONFIG["password"]
                subprocess.run(
                    command,
                    check=True,
                    capture_output=True,
                    text=True,
                    env=dump_environment,
                )
                messagebox.showinfo(
                    "Export Complete",
                    f"SQL database backup created successfully:\n{file_path}",
                    parent=self,
                )
                return
            except (OSError, subprocess.SubprocessError) as exc:
                messagebox.showwarning(
                    "Backup Utility Error",
                    f"mysqldump failed. A SQL backup will be generated using MySQL Connector.\n{exc}",
                    parent=self,
                )

        try:
            connection = mysql.connector.connect(**DB_CONFIG)
            cursor = connection.cursor()
            cursor.execute("SHOW TABLES")
            tables = [row[0] for row in cursor.fetchall()]

            with open(file_path, "w", encoding="utf-8", newline="\n") as sql_file:
                sql_file.write(
                    "-- Asset Inventory Management System SQL Backup\n"
                    f"-- Generated: {datetime.now():%Y-%m-%d %H:%M:%S}\n\n"
                    "SET FOREIGN_KEY_CHECKS=0;\n"
                    "SET SQL_MODE='NO_AUTO_VALUE_ON_ZERO';\n\n"
                    f"CREATE DATABASE IF NOT EXISTS `{DB_CONFIG['database']}` "
                    "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;\n"
                    f"USE `{DB_CONFIG['database']}`;\n"
                )

                for table in tables:
                    cursor.execute(f"SHOW CREATE TABLE `{table}`")
                    create_statement = cursor.fetchone()[1]
                    sql_file.write(f"\nDROP TABLE IF EXISTS `{table}`;\n{create_statement};\n")

                    cursor.execute(f"SELECT * FROM `{table}`")
                    rows = cursor.fetchall()
                    if rows:
                        cursor.execute(f"SHOW COLUMNS FROM `{table}`")
                        columns = [row[0] for row in cursor.fetchall()]
                        column_sql = ", ".join(f"`{column}`" for column in columns)
                        for row in rows:
                            values = ", ".join(self.sql_dump_value(value) for value in row)
                            sql_file.write(
                                f"INSERT INTO `{table}` ({column_sql}) VALUES ({values});\n"
                            )

                sql_file.write("\nSET FOREIGN_KEY_CHECKS=1;\n")

            messagebox.showinfo(
                "Export Complete",
                f"SQL database backup created successfully:\n{file_path}",
                parent=self,
            )
        except (Error, OSError, UnicodeError) as exc:
            messagebox.showerror("Export Failed", f"Could not export SQL database.\n{exc}", parent=self)
        finally:
            if "cursor" in locals():
                cursor.close()
            if "connection" in locals() and connection.is_connected():
                connection.close()

    @staticmethod
    def sql_dump_value(value):
        if value is None:
            return "NULL"
        if isinstance(value, bytes):
            return "0x" + value.hex().upper()
        if isinstance(value, (int, float)):
            return str(value)
        escaped = str(value).replace("\\", "\\\\").replace("'", "''")
        escaped = escaped.replace("\r", "\\r").replace("\n", "\\n").replace("\t", "\\t")
        return f"'{escaped}'"

    def export_inventory_csv(self):
        if not messagebox.askyesno("Confirm Export", "Export the inventory data to CSV?"):
            return

        file_path = filedialog.asksaveasfilename(
            parent=self,
            title="Export Inventory",
            defaultextension=".csv",
            initialfile="inventory.csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not file_path:
            return

        connection = None
        cursor = None
        try:
            connection = mysql.connector.connect(**DB_CONFIG)
            cursor = connection.cursor(dictionary=True)
            cursor.execute(
                """
                SELECT a.asset_id AS `ID`, a.asset_name AS `Asset Name`,
                       c.name AS `Category`, a.status AS `Status`,
                       a.quantity AS `Quantity`, a.brand AS `Brand`
                FROM assets a
                JOIN categories c ON c.category_id = a.category_id
                WHERE a.deleted_at IS NULL
                ORDER BY a.asset_id DESC
                """
            )
            assets = cursor.fetchall()

            with open(file_path, "w", newline="", encoding="utf-8-sig") as csv_file:
                fieldnames = ["ID", "Asset Name", "Category", "Status", "Quantity", "Brand"]
                writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(assets)

            messagebox.showinfo(
                "Export Complete",
                f"Inventory exported successfully to:\n{file_path}",
                parent=self,
            )
        except (Error, OSError, csv.Error) as exc:
            messagebox.showerror("Export Failed", f"Could not export inventory.\n{exc}", parent=self)
        finally:
            if cursor is not None:
                cursor.close()
            if connection is not None and connection.is_connected():
                connection.close()

    def import_inventory_csv(self):
        file_path = filedialog.askopenfilename(
            parent=self,
            title="Import Inventory CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not file_path:
            return

        try:
            with open(file_path, "r", newline="", encoding="utf-8-sig") as csv_file:
                reader = csv.DictReader(csv_file)
                if not reader.fieldnames:
                    raise ValueError("The selected CSV file is empty.")

                normalized_headers = {
                    header.strip().lower().replace("_", " ").replace("-", " "): header
                    for header in reader.fieldnames
                }

                def get_value(row, *names):
                    for name in names:
                        key = normalized_headers.get(name.lower().replace("_", " "))
                        if key is not None and row.get(key) not in (None, ""):
                            return str(row[key]).strip()
                    return ""

                rows = list(reader)
        except (OSError, csv.Error, UnicodeError, ValueError) as exc:
            messagebox.showerror("Import Failed", f"Could not read the CSV file.\n{exc}", parent=self)
            return

        if not rows:
            messagebox.showwarning("Import Empty", "The selected CSV file has no asset rows.", parent=self)
            return
        if not messagebox.askyesno(
            "Confirm Import",
            f"Import {len(rows)} asset row(s) into inventory?",
            parent=self,
        ):
            return

        connection = None
        cursor = None
        inserted_count = 0
        updated_count = 0
        try:
            connection = mysql.connector.connect(**DB_CONFIG)
            cursor = connection.cursor(dictionary=True)

            cursor.execute("SELECT user_id FROM users WHERE username = 'admin' LIMIT 1")
            admin = cursor.fetchone()
            admin_id = admin["user_id"] if admin else None

            for row in rows:
                asset_name = get_value(row, "asset name", "name", "asset")
                category_name = get_value(row, "category") or "IT hardware"
                brand = get_value(row, "brand") or "Unknown"
                quantity_text = get_value(row, "quantity", "qty")
                status = get_value(row, "status") or "In Stock"

                if not asset_name:
                    raise ValueError("Every row must contain an Asset Name.")
                try:
                    quantity = max(0, int(quantity_text or "1"))
                except ValueError as exc:
                    raise ValueError(f"Invalid quantity for '{asset_name}'.") from exc
                if status not in ("In Stock", "Disposed"):
                    status = "In Stock"

                cursor.execute(
                    "SELECT category_id FROM categories WHERE LOWER(name) = LOWER(%s) LIMIT 1",
                    (category_name,),
                )
                category = cursor.fetchone()
                if category:
                    category_id = category["category_id"]
                else:
                    cursor.execute("INSERT INTO categories (name) VALUES (%s)", (category_name,))
                    category_id = cursor.lastrowid

                cursor.execute(
                    """
                    SELECT asset_id, quantity
                    FROM assets
                    WHERE asset_name = %s AND brand = %s AND category_id = %s
                      AND deleted_at IS NULL
                    LIMIT 1
                    """,
                    (asset_name, brand, category_id),
                )
                existing_asset = cursor.fetchone()
                if existing_asset:
                    cursor.execute(
                        """
                        UPDATE assets
                        SET quantity = quantity + %s, status = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE asset_id = %s
                        """,
                        (quantity, status, existing_asset["asset_id"]),
                    )
                    updated_count += 1
                else:
                    cursor.execute(
                        """
                        INSERT INTO assets
                            (asset_name, brand, category_id, quantity, unit_price, status, created_by)
                        VALUES (%s, %s, %s, %s, 0, %s, %s)
                        """,
                        (asset_name, brand, category_id, quantity, status, admin_id),
                    )
                    inserted_count += 1

            cursor.execute(
                """
                INSERT INTO activity_logs (user_id, username, role, action, description)
                VALUES (%s, 'admin', 'Admin', 'CREATE', %s)
                """,
                (admin_id, f"Imported {len(rows)} inventory rows from CSV ({inserted_count} added, {updated_count} updated)."),
            )
            connection.commit()
        except (Error, ValueError) as exc:
            if connection is not None:
                connection.rollback()
            messagebox.showerror("Import Failed", f"Could not import inventory.\n{exc}", parent=self)
            return
        finally:
            if cursor is not None:
                cursor.close()
            if connection is not None and connection.is_connected():
                connection.close()

        self.load_inventory()
        self.refresh_dashboard_data()
        messagebox.showinfo(
            "Import Complete",
            f"Imported inventory successfully.\nAdded: {inserted_count}\nUpdated: {updated_count}",
            parent=self,
        )

    def validate_qty(self, P):
        if P == "" or P.isdigit():
            return True
        return False

    def format_date_input(self, *args):
        raw = self.date_var.get()
        if raw == "YYYY/MM/DD":
            return
        
        clean = "".join([c for c in raw if c.isdigit()])
        if len(clean) > 8:
            clean = clean[:8]
            
        formatted = ""
        if len(clean) > 4:
            formatted = clean[:4] + "/" + clean[4:6] + ("/" + clean[6:] if len(clean) > 6 else "")
        elif len(clean) > 2:
            formatted = clean[:4] + ("/" + clean[4:] if len(clean) > 4 else "")
        else:
            formatted = clean
            
        if raw != formatted:
            self.date_var.set(formatted)
            self.asset_entries["date"].icursor(tk.END)

    def open_calendar_popup(self):
        cal_dialog = tk.Toplevel(self)
        cal_dialog.title("Select Purchase Date")
        self.center_dialog(cal_dialog, 340, 320)
        cal_dialog.configure(bg=THEME["bg_main"])
        cal_dialog.transient(self)
        cal_dialog.grab_set()

        now = datetime.now()
        curr_year = tk.IntVar(value=now.year)
        curr_month = tk.IntVar(value=now.month)

        header_frm = tk.Frame(cal_dialog, bg=THEME["bg_header"])
        header_frm.pack(fill="x")

        sel_frm = tk.Frame(header_frm, bg=THEME["bg_header"])
        sel_frm.pack(pady=10)

        month_names = list(calendar.month_name)[1:] 
        month_combo = ttk.Combobox(sel_frm, values=month_names, state="readonly", font=("Arial", 10), width=11)
        month_combo.set(calendar.month_name[curr_month.get()])
        month_combo.pack(side="left", padx=5)

        years_list = [str(y) for y in range(1995, now.year + 11)]
        year_combo = ttk.Combobox(sel_frm, values=years_list, state="readonly", font=("Arial", 10), width=7)
        year_combo.set(str(curr_year.get()))
        year_combo.pack(side="left", padx=5)

        grid_frm = tk.Frame(cal_dialog, bg=THEME["bg_main"])
        grid_frm.pack(fill="both", expand=True, padx=15, pady=10)

        def build_calendar():
            for w in grid_frm.winfo_children():
                w.destroy()
                
            y = int(year_combo.get())
            m = month_names.index(month_combo.get()) + 1
            
            days = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
            for i, d in enumerate(days):
                tk.Label(grid_frm, text=d, font=("Arial", 9, "bold"), bg=THEME["bg_main"], fg=THEME["text_muted"]).grid(row=0, column=i, padx=6, pady=2)
                
            month_matrix = calendar.monthcalendar(y, m)
            for r_idx, week in enumerate(month_matrix):
                for c_idx, day in enumerate(week):
                    if day == 0:
                        tk.Label(grid_frm, text="", bg=THEME["bg_main"]).grid(row=r_idx+1, column=c_idx, padx=6, pady=3)
                    else:
                        btn = tk.Button(
                            grid_frm, text=str(day), font=("Arial", 9), width=3, bg=THEME["bg_card"], bd=1,
                            command=lambda y_v=y, m_v=m, d_v=day: select_date(y_v, m_v, d_v)
                        )
                        btn.grid(row=r_idx+1, column=c_idx, padx=3, pady=3)

        def select_date(y, m, d):
            self.date_var.set(f"{y:04d}/{m:02d}/{d:02d}")
            cal_dialog.destroy()

        month_combo.bind("<<ComboboxSelected>>", lambda e: build_calendar())
        year_combo.bind("<<ComboboxSelected>>", lambda e: build_calendar())

        build_calendar()

    def center_dialog(self, dialog, width=340, height=180):
        self.update_idletasks()
        main_x = self.winfo_x()
        main_y = self.winfo_y()
        main_w = self.winfo_width()
        main_h = self.winfo_height()
        
        x = main_x + (main_w // 2) - (width // 2)
        y = main_y + (main_h // 2) - (height // 2)
        dialog.geometry(f"{width}x{height}+{x}+{y}")

    def open_add_supplier_dialog(self):
        dialog = tk.Toplevel(self)
        dialog.title("Add New Supplier")
        self.center_dialog(dialog, 340, 180)
        dialog.configure(bg=THEME["bg_main"])
        dialog.transient(self)
        dialog.grab_set()

        tk.Label(dialog, text="Enter New Supplier Name:", font=("Arial", 10, "bold"), bg=THEME["bg_main"], fg=THEME["text_dark"]).pack(anchor="nw", padx=20, pady=(15, 5))
        
        sup_entry = tk.Entry(dialog, font=("Arial", 10), bg="white", bd=1, relief="solid", width=32)
        sup_entry.pack(padx=20, pady=5, ipady=4)
        sup_entry.focus()

        def save_supplier():
            new_sup = sup_entry.get().strip()
            if not new_sup:
                messagebox.showerror("Error", "Supplier name cannot be empty!", parent=dialog)
                return
            if new_sup in self.supplier_options_list:
                messagebox.showerror("Error", "Supplier already exists!", parent=dialog)
                return

            try:
                connection = mysql.connector.connect(**DB_CONFIG)
                cursor = connection.cursor()
                cursor.execute(
                    "INSERT INTO suppliers (name) VALUES (%s)",
                    (new_sup,),
                )
                connection.commit()
            except Error as exc:
                if "connection" in locals():
                    connection.rollback()
                messagebox.showerror(
                    "Database Error",
                    f"Failed to save supplier to MySQL.\n{exc}",
                    parent=dialog,
                )
                return
            finally:
                if "cursor" in locals():
                    cursor.close()
                if "connection" in locals():
                    connection.close()

            self.supplier_options_list.append(new_sup)
            self.supplier_combo["values"] = self.supplier_options_list
            self.supplier_combo.set(new_sup)
            dialog.destroy()

        btn_row = tk.Frame(dialog, bg=THEME["bg_main"])
        btn_row.pack(fill="x", padx=20, pady=(15, 0))

        tk.Button(btn_row, text="Cancel", font=("Arial", 9), bg="#95A5A6", fg="white", bd=0, padx=12, pady=5, command=dialog.destroy).pack(side="right")
        tk.Button(btn_row, text="Add", font=("Arial", 9, "bold"), bg=THEME["bg_header"], fg="white", bd=0, padx=15, pady=5, command=save_supplier).pack(side="right", padx=(0, 8))

    def open_delete_supplier_dialog(self):
        if not self.supplier_options_list:
            messagebox.showwarning("Notice", "No suppliers available to delete.")
            return

        dialog = tk.Toplevel(self)
        dialog.title("Delete Supplier")
        self.center_dialog(dialog, 340, 180)
        dialog.configure(bg=THEME["bg_main"])
        dialog.transient(self)
        dialog.grab_set()

        tk.Label(dialog, text="Select Supplier to Delete:", font=("Arial", 10, "bold"), bg=THEME["bg_main"], fg=THEME["text_dark"]).pack(anchor="nw", padx=20, pady=(15, 5))
        
        del_combo = ttk.Combobox(dialog, values=self.supplier_options_list, state="readonly", font=("Arial", 10), width=28)
        del_combo.set(self.supplier_options_list[0])
        del_combo.pack(padx=20, pady=5, ipady=3)

        def delete_supplier():
            target = del_combo.get()
            if target in self.supplier_options_list:
                try:
                    connection = mysql.connector.connect(**DB_CONFIG)
                    cursor = connection.cursor()
                    cursor.execute(
                        "DELETE FROM suppliers WHERE name = %s",
                        (target,),
                    )
                    connection.commit()
                except Error as exc:
                    messagebox.showerror(
                        "Database Error",
                        f"Failed to delete supplier from MySQL.\n{exc}",
                        parent=dialog,
                    )
                    return
                finally:
                    if "cursor" in locals():
                        cursor.close()
                    if "connection" in locals():
                        connection.close()

                self.supplier_options_list.remove(target)
                self.supplier_combo["values"] = self.supplier_options_list
                if self.supplier_options_list:
                    self.supplier_combo.set(self.supplier_options_list[0])
                else:
                    self.supplier_combo.set("No Supplier Added")
                dialog.destroy()

        btn_row = tk.Frame(dialog, bg=THEME["bg_main"])
        btn_row.pack(fill="x", padx=20, pady=(15, 0))

        tk.Button(btn_row, text="Cancel", font=("Arial", 9), bg="#95A5A6", fg="white", bd=0, padx=12, pady=5, command=dialog.destroy).pack(side="right")
        tk.Button(btn_row, text="Delete", font=("Arial", 9, "bold"), bg=THEME["accent_danger"], fg="white", bd=0, padx=15, pady=5, command=delete_supplier).pack(side="right", padx=(0, 8))

    def open_add_location_dialog(self):
        dialog = tk.Toplevel(self)
        dialog.title("Add New Location")
        self.center_dialog(dialog, 360, 200)
        dialog.configure(bg=THEME["bg_main"])
        dialog.transient(self)
        dialog.grab_set()

        tk.Label(dialog, text="Enter Location (ex. W1-Shelf A-1):", font=("Arial", 10, "bold"), bg=THEME["bg_main"], fg=THEME["text_dark"]).pack(anchor="nw", padx=20, pady=(15, 5))
        
        loc_entry = tk.Entry(dialog, font=("Arial", 10), bg="white", bd=1, relief="solid", width=34)
        loc_entry.pack(padx=20, pady=5, ipady=4)
        loc_entry.focus()
        
        tk.Label(dialog, text="Format: Warehouse-Shelf-Number", font=("Arial", 8, "italic"), bg=THEME["bg_main"], fg=THEME["text_muted"]).pack(anchor="nw", padx=20, pady=(0, 5))

        def save_location():
            new_loc = loc_entry.get().strip()
            if not new_loc:
                messagebox.showerror("Error", "Location name cannot be empty!", parent=dialog)
                return
            if new_loc in self.location_options_list:
                messagebox.showerror("Error", "Location already exists!", parent=dialog)
                return

            try:
                connection = mysql.connector.connect(**DB_CONFIG)
                cursor = connection.cursor()
                cursor.execute(
                    "INSERT INTO locations (name) VALUES (%s)",
                    (new_loc,),
                )
                connection.commit()
            except Error as exc:
                if "connection" in locals():
                    connection.rollback()
                messagebox.showerror(
                    "Database Error",
                    f"Failed to save location to MySQL.\n{exc}",
                    parent=dialog,
                )
                return
            finally:
                if "cursor" in locals():
                    cursor.close()
                if "connection" in locals():
                    connection.close()

            self.location_options_list.append(new_loc)
            self.location_combo["values"] = self.location_options_list
            self.location_combo.set(new_loc)
            dialog.destroy()

        btn_row = tk.Frame(dialog, bg=THEME["bg_main"])
        btn_row.pack(fill="x", padx=20, pady=(10, 0))

        tk.Button(btn_row, text="Cancel", font=("Arial", 9), bg="#95A5A6", fg="white", bd=0, padx=12, pady=5, command=dialog.destroy).pack(side="right")
        tk.Button(btn_row, text="Add", font=("Arial", 9, "bold"), bg=THEME["bg_header"], fg="white", bd=0, padx=15, pady=5, command=save_location).pack(side="right", padx=(0, 8))

    def open_delete_location_dialog(self):
        if not self.location_options_list:
            messagebox.showwarning("Notice", "No locations available to delete.")
            return

        dialog = tk.Toplevel(self)
        dialog.title("Delete Location")
        self.center_dialog(dialog, 340, 180)
        dialog.configure(bg=THEME["bg_main"])
        dialog.transient(self)
        dialog.grab_set()

        tk.Label(dialog, text="Select Location to Delete:", font=("Arial", 10, "bold"), bg=THEME["bg_main"], fg=THEME["text_dark"]).pack(anchor="nw", padx=20, pady=(15, 5))
        
        del_combo = ttk.Combobox(dialog, values=self.location_options_list, state="readonly", font=("Arial", 10), width=28)
        del_combo.set(self.location_options_list[0])
        del_combo.pack(padx=20, pady=5, ipady=3)

        def delete_location():
            target = del_combo.get()
            if target in self.location_options_list:
                try:
                    connection = mysql.connector.connect(**DB_CONFIG)
                    cursor = connection.cursor()
                    cursor.execute(
                        "DELETE FROM locations WHERE name = %s",
                        (target,),
                    )
                    connection.commit()
                except Error as exc:
                    messagebox.showerror(
                        "Database Error",
                        f"Failed to delete location from MySQL.\n{exc}",
                        parent=dialog,
                    )
                    return
                finally:
                    if "cursor" in locals():
                        cursor.close()
                    if "connection" in locals():
                        connection.close()

                self.location_options_list.remove(target)
                self.location_combo["values"] = self.location_options_list
                if self.location_options_list:
                    self.location_combo.set(self.location_options_list[0])
                else:
                    self.location_combo.set("No Location Added")
                dialog.destroy()

        btn_row = tk.Frame(dialog, bg=THEME["bg_main"])
        btn_row.pack(fill="x", padx=20, pady=(15, 0))

        tk.Button(btn_row, text="Cancel", font=("Arial", 9), bg="#95A5A6", fg="white", bd=0, padx=12, pady=5, command=dialog.destroy).pack(side="right")
        tk.Button(btn_row, text="Delete", font=("Arial", 9, "bold"), bg=THEME["accent_danger"], fg="white", bd=0, padx=15, pady=5, command=delete_location).pack(side="right", padx=(0, 8))

    def format_price_and_total(self, *args):
        raw = self.price_var.get()
        clean = raw.replace(",", "")
        
        filtered = []
        dot_seen = False
        for char in clean:
            if char.isdigit():
                filtered.append(char)
            elif char == '.' and not dot_seen:
                filtered.append(char)
                dot_seen = True
        
        clean_str = "".join(filtered)
        
        formatted = ""
        if clean_str:
            if "." in clean_str:
                parts = clean_str.split(".")
                int_part = parts[0]
                dec_part = parts[1]
                if int_part:
                    formatted = "{:,}".format(int(int_part)) + "." + dec_part
                else:
                    formatted = "0." + dec_part
            else:
                formatted = "{:,}".format(int(clean_str))
        
        if raw != formatted:
            self.price_var.set(formatted)
            self.asset_entries["price"].icursor(tk.END)
            
        self.update_total_value()

    def update_total_value(self, event=None):
        try:
            qty_str = self.asset_entries["qty"].get().strip()
            price_str = self.asset_entries["price"].get().strip().replace(",", "")
            
            qty = int(qty_str) if qty_str else 0
            price = float(price_str) if price_str else 0.0
            
            if qty < 0 or price < 0:
                self.val_total_est.set("$0.00")
            else:
                total = qty * price
                self.val_total_est.set(f"${total:,.2f}")
        except ValueError:
            self.val_total_est.set("$0.00")

    def change_account_status(self, new_status):
        selected_item = self.acc_tree.selection()
        if not selected_item:
            messagebox.showwarning("Selection Warning", "Please select a user account from the table first.")
            return

        item_id = selected_item[0]
        current_values = self.acc_tree.item(item_id, "values")
        
        try:
            if not update_user_status(current_values[0], new_status):
                messagebox.showerror("Update Failed", "The selected account could not be found in the database.")
                return
        except Error as exc:
            messagebox.showerror("Database Error", f"Could not update account status.\n{exc}")
            return

        updated_list = []
        for row in self.accounts_data:
            if row[0] == current_values[0]:
                updated_list.append((row[0], row[1], row[2], new_status, row[4]))
            else:
                updated_list.append(row)
        self.accounts_data = updated_list

        self.acc_tree.item(item_id, values=(current_values[0], current_values[1], current_values[2], new_status, current_values[4]))
        messagebox.showinfo("Success", f"Account accessibility for '{current_values[1]}' successfully updated to: {new_status}")

    def remove_account(self):
        selected_item = self.acc_tree.selection()
        if not selected_item:
            messagebox.showwarning("Selection Warning", "Please select an account to remove.")
            return

        item_id = selected_item[0]
        account = self.acc_tree.item(item_id, "values")
        user_id = account[0]

        if str(account[2]).lower() == "admin":
            messagebox.showwarning("Cannot Remove", "Administrator accounts cannot be removed from Account Management.")
            return

        if not messagebox.askyesno(
            "Confirm Removal",
            f"Remove the account '{account[1]}' permanently from MySQL?",
        ):
            return

        try:
            if not delete_user(user_id):
                messagebox.showerror("Removal Failed", "The selected account could not be found in MySQL.")
                return
        except Error as exc:
            messagebox.showerror("Database Error", f"Could not remove account.\n{exc}")
            return

        self.acc_tree.delete(item_id)
        self.accounts_data = [row for row in self.accounts_data if row[0] != user_id]
        messagebox.showinfo("Success", f"Account '{account[1]}' was removed successfully.")

    def change_reset_status(self, new_status):
        selected_item = self.reset_tree.selection()
        if not selected_item:
            messagebox.showwarning("Selection Warning", "Please select a password reset request from the table first.")
            return

        item_id = selected_item[0]
        current_values = self.reset_tree.item(item_id, "values")

        if not messagebox.askyesno(
            "Confirm Password Reset",
            f"{new_status} the password reset request for '{current_values[0]}'? ",
        ):
            return

        connection = None
        cursor = None
        try:
            connection = mysql.connector.connect(**DB_CONFIG)
            cursor = connection.cursor(dictionary=True)

            cursor.execute(
                """
                SELECT requested_password_hash, status
                FROM password_reset_requests
                WHERE request_id = %s
                """,
                (item_id,),
            )
            request = cursor.fetchone()
            if not request:
                messagebox.showerror("Error", "The selected reset request no longer exists.")
                return
            if request["status"] != "Pending":
                messagebox.showwarning("Request Resolved", "This reset request has already been resolved.")
                self.load_reset_requests()
                return

            if new_status == "Approved":
                if not request["requested_password_hash"]:
                    messagebox.showerror(
                        "Missing Password",
                        "This request does not contain a requested password and cannot be approved.",
                    )
                    return
                cursor.execute(
                    """
                    UPDATE users
                    SET password_hash = %s
                    WHERE user_id = (
                        SELECT user_id
                        FROM password_reset_requests
                        WHERE request_id = %s
                    )
                    """,
                    (request["requested_password_hash"], item_id),
                )

            cursor.execute(
                """
                UPDATE password_reset_requests
                SET status = %s, resolved_at = CURRENT_TIMESTAMP
                WHERE request_id = %s
                """,
                (new_status, item_id),
            )
            cursor.execute(
                """
                INSERT INTO activity_logs (user_id, username, role, action, description)
                SELECT pr.user_id, u.username, 'System', 'UPDATE', %s
                FROM password_reset_requests pr
                JOIN users u ON u.user_id = pr.user_id
                WHERE pr.request_id = %s
                """,
                (
                    f"Password reset request for '{current_values[0]}' was {new_status.lower()}",
                    item_id,
                ),
            )
            connection.commit()
        except Error as exc:
            if connection is not None:
                connection.rollback()
            messagebox.showerror("Database Error", f"Could not resolve the reset request.\n{exc}")
            return
        finally:
            if cursor is not None:
                cursor.close()
            if connection is not None:
                connection.close()

        self.load_reset_requests()
        messagebox.showinfo("Success", f"Password reset request for '{current_values[0]}' marked as {new_status}.")

    def load_reset_requests(self):
        self.reset_tree.delete(*self.reset_tree.get_children())
        connection = None
        cursor = None
        try:
            connection = mysql.connector.connect(**DB_CONFIG)
            cursor = connection.cursor(dictionary=True)
            cursor.execute(
                """
                SELECT pr.request_id, u.username, u.email, pr.status,
                       DATE_FORMAT(pr.requested_at, '%Y-%m-%d %H:%i') AS requested_at
                FROM password_reset_requests pr
                JOIN users u ON u.user_id = pr.user_id
                ORDER BY pr.requested_at DESC, pr.request_id DESC
                """
            )
            for request in cursor.fetchall():
                self.reset_tree.insert(
                    "",
                    "end",
                    iid=str(request["request_id"]),
                    values=(
                        request["username"],
                        request["email"],
                        request["status"],
                        request["requested_at"],
                    ),
                )
        except Error as exc:
            messagebox.showerror(
                "Database Error",
                f"Could not load password reset requests.\n{exc}",
            )
        finally:
            if cursor is not None:
                cursor.close()
            if connection is not None:
                connection.close()

    def increment_qty(self):
        try:
            val = int(self.asset_entries["qty"].get())
            self.asset_entries["qty"].delete(0, tk.END)
            self.asset_entries["qty"].insert(0, str(val + 1))
        except ValueError:
            self.asset_entries["qty"].delete(0, tk.END)
            self.asset_entries["qty"].insert(0, "1")
        self.update_total_value()

    def decrement_qty(self):
        try:
            val = int(self.asset_entries["qty"].get())
            if val > 1:
                self.asset_entries["qty"].delete(0, tk.END)
                self.asset_entries["qty"].insert(0, str(val - 1))
        except ValueError:
            self.asset_entries["qty"].delete(0, tk.END)
            self.asset_entries["qty"].insert(0, "1")
        self.update_total_value()

    def clear_form(self):
        self.asset_entries["name"].delete(0, tk.END)
        self.asset_entries["brand"].delete(0, tk.END)
        self.asset_entries["category"].set("Select Category")
        self.asset_entries["qty"].delete(0, tk.END)
        self.asset_entries["qty"].insert(0, "1")
        self.price_var.set("")
        self.val_total_est.set("$0.00")
        self.date_var.set("YYYY/MM/DD")
        self.warranty_combo.set("1 Year")
        self.toggle_custom_warranty()
        if self.supplier_options_list:
            self.supplier_combo.set(self.supplier_options_list[0])
        else:
            self.supplier_combo.set("No Supplier Added")
        if self.location_options_list:
            self.location_combo.set(self.location_options_list[0])
        else:
            self.location_combo.set("No Location Added")

    def toggle_custom_warranty(self, event=None):
        if self.warranty_combo.get() == "Custom":
            self.f_custom_warranty.pack(fill="x", pady=(3, 0))
        else:
            self.f_custom_warranty.pack_forget()
            self.asset_entries["custom_warranty"].delete(0, tk.END)

    def validate_and_save_asset(self):
        name = self.asset_entries["name"].get().strip()
        brand = self.asset_entries["brand"].get().strip()
        category = self.asset_entries["category"].get() 
        qty_str = self.asset_entries["qty"].get().strip()
        price_str = self.asset_entries["price"].get().strip().replace(",", "")
        date_str = self.date_var.get().strip()

        if not name or not brand or not price_str:
            messagebox.showerror("Validation Error", "Asset Name, Brand, and Unit Price are required fields!")
            return

        if category == "Select Category":
            messagebox.showerror("Validation Error", "Please select a valid Category!")
            return

        try:
            qty = int(qty_str)
            if qty <= 0: raise ValueError()
        except ValueError:
            messagebox.showerror("Validation Error", "Quantity must be a valid positive integer.")
            return

        try:
            price = float(price_str)
            if price < 0: raise ValueError()
        except ValueError:
            messagebox.showerror("Validation Error", "Unit Price must be a valid positive number.")
            return

        if date_str != "YYYY/MM/DD" and date_str != "":
            try:
                datetime.strptime(date_str, "%Y/%m/%d")
            except ValueError:
                messagebox.showerror("Validation Error", "Purchase Date must match the exact format: YYYY/MM/DD")
                return

        sanitized_name = name.replace("<", "").replace(">", "")

        if not messagebox.askyesno("Confirm Add Asset", f"Are you sure you want to save the new asset '{sanitized_name}'?"):
            return

        total_val = qty * price
        self.val_total_est.set(f"${total_val:,.2f}")

        supplier = self.asset_entries["supplier"].get().strip()
        location = self.asset_entries["location"].get().strip()
        purchase_date = None if date_str in ("YYYY/MM/DD", "") else date_str.replace("/", "-")
        warranty = self.asset_entries["custom_warranty"].get().strip() if self.warranty_combo.get() == "Custom" else self.warranty_combo.get()
        description = f"Added new asset '{sanitized_name}' (Qty: {qty})"

        try:
            save_asset_and_log(
                {
                    "name": sanitized_name,
                    "brand": brand,
                    "category": category,
                    "quantity": qty,
                    "unit_price": price,
                    "purchase_date": purchase_date,
                    "warranty": warranty,
                    "supplier": supplier,
                    "location": location,
                },
                "admin",
                "Admin",
                description,
            )
        except Error as exc:
            messagebox.showerror("Database Error", f"Could not save asset.\n{exc}")
            return
        except Exception as exc:
            messagebox.showerror("Database Error", f"Could not save asset.\n{exc}")
            return

        self.load_inventory()
        self.refresh_dashboard_data()

        messagebox.showinfo(
            "Success", 
            f"Asset '{sanitized_name}' validated and saved successfully!\nAudit trail log recorded."
        )

    def render_placeholder(self, tab_name):
        tk.Label(
            self.content_frame, text=tab_name, font=FONTS["title"], 
            bg=THEME["bg_main"], fg=THEME["bg_header"]
        ).pack(pady=30, padx=30, anchor="nw")
        
        tk.Label(
            self.content_frame, text=f"This is the {tab_name} section. Content goes here.", 
            font=("Arial", 12), bg=THEME["bg_main"], fg=THEME["text_muted"]
        ).pack(padx=30, anchor="nw")

    def load_system_icon(self):
        logo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Login", "logo.png"))
        if os.path.exists(logo_path):
            try:
                return tk.PhotoImage(file=logo_path)
            except tk.TclError:
                pass
        return None

if __name__ == "__main__":
    app = AssetManagementApp()
    app.mainloop()