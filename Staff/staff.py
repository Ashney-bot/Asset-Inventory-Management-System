import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import math
import os
from datetime import datetime
import calendar
import sys
import subprocess
import mysql.connector
from mysql.connector import Error

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "asset inventory management system",
}


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
            WHERE asset_name = %s AND brand = %s AND category_id = %s
              AND deleted_at IS NULL
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
                VALUES (%s, %s, %s, %s, %s, 'In Stock', %s, %s, %s, %s, %s)
                """,
                (
                    asset_data["name"], asset_data["brand"], category_id,
                    asset_data["quantity"], asset_data["unit_price"],
                    asset_data["purchase_date"], asset_data["warranty"], supplier_id, location_id, user_id,
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

class StaffAssetManagementApp(tk.Tk):
    def __init__(self, username="Staff"):
        super().__init__()
        self.username = username
        
        self.title("Asset Inventory Management - Staff Portal")
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
        
        # Load suppliers and locations from MySQL on startup
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
        self.val_low_stock = tk.StringVar(value="--")
        self.quantity_undo_stack = []
        
        self.logs_data = [] 
        self.notif_frame = None 
        self.notification_button = None
        self.latest_notification_id = 0
        self.unread_notification_count = 0
        
        self.setup_ui()
        self.switch_tab("Dashboard")
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
        self.notification_button.pack(side="left", padx=(0, 15), pady=(0, 4))
        
        tk.Label(
            right_frame, text=f"{self.username} 👤", font=FONTS["header"], 
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
            ("➕", "Add Asset")
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
            new_count = latest_id - self.latest_notification_id
            self.latest_notification_id = latest_id
            self.unread_notification_count += max(1, new_count)
            if self.notification_button:
                self.notification_button.configure(
                    text=f"🔔 {self.unread_notification_count}"
                )
                self.bell()


    # ==========================================
    # 4. STAFF DASHBOARD INTERFACE
    # ==========================================
    def refresh_dashboard_data(self):
        try:
            connection = mysql.connector.connect(**DB_CONFIG)
            cursor = connection.cursor(dictionary=True)

            cursor.execute(
                """
                SELECT COALESCE(SUM(quantity), 0) AS total_stored
                FROM assets
                WHERE deleted_at IS NULL
                """
            )
            summary = cursor.fetchone()

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
        low_stock_names = [
            f"{row['name']} ({'Critical' if row['quantity'] <= 1 else 'Low Stock'}: {row['quantity']})"
            for row in low_stock_categories
        ]
        self.val_low_stock.set("\n".join(low_stock_names) if low_stock_names else "No Low Stock")

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


    def _create_metric_card(self, parent, title, textvariable, value_color):
        card = tk.Frame(parent, bg=THEME["bg_card"], highlightbackground=THEME["border"], highlightthickness=1)
        card.pack(side="left", fill="x", expand=True, padx=5, ipady=10)
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
            cursor.execute(
                "SELECT user_id FROM users WHERE username = %s LIMIT 1",
                (self.username,),
            )
            staff = cursor.fetchone()
            staff_id = staff["user_id"] if staff else None

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
                    VALUES (%s, %s, 'Staff', 'UPDATE', %s)
                    """,
                    (
                        staff_id,
                        self.username,
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
                "SELECT user_id FROM users WHERE username = %s LIMIT 1",
                (self.username,),
            )
            staff = cursor.fetchone()
            staff_id = staff["user_id"] if staff else None

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
                    VALUES (%s, %s, 'Staff', 'UPDATE', %s)
                    """,
                    (
                        staff_id,
                        self.username,
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

    def move_selected_assets_to_bin(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Selection Warning", "Please select one or more assets to move to the bin.")
            return
        if not messagebox.askyesno("Move to Bin", f"Move {len(selected)} selected asset(s) to the Bin?"):
            return

        asset_ids = [self.tree.item(item, "values")[0] for item in selected]
        placeholders = ", ".join(["%s"] * len(asset_ids))
        try:
            connection = mysql.connector.connect(**DB_CONFIG)
            cursor = connection.cursor()
            cursor.execute(
                "SELECT user_id FROM users WHERE username = %s LIMIT 1", (self.username,)
            )
            user = cursor.fetchone()
            deleted_by = user[0] if user else None
            cursor.execute(
                f"""
                UPDATE assets
                SET deleted_at = CURRENT_TIMESTAMP, deleted_by = %s
                WHERE asset_id IN ({placeholders}) AND deleted_at IS NULL
                """,
                (deleted_by, *asset_ids),
            )
            cursor.execute(
                """
                INSERT INTO activity_logs (user_id, username, role, action, description)
                VALUES (%s, %s, 'Staff', 'DELETE', %s)
                """,
                (deleted_by, self.username, f"Moved {cursor.rowcount} asset(s) to the Bin"),
            )
            connection.commit()
        except Error as exc:
            if "connection" in locals():
                connection.rollback()
            messagebox.showerror("Database Error", f"Could not move assets to the Bin.\n{exc}")
            return
        finally:
            if "cursor" in locals():
                cursor.close()
            if "connection" in locals():
                connection.close()

        self.load_inventory()
        self.refresh_dashboard_data()
        messagebox.showinfo("Moved to Bin", "The selected asset(s) were moved to the Bin.")


    # ==========================================
    # 6. ADD ASSET INTERFACE
    # ==========================================


    # ==========================================
    # 7. FORM UTILITIES & VALIDATION
    # ==========================================
    def load_dropdown_options(self):
        """Fetches existing suppliers and locations from the database on startup."""
        try:
            connection = mysql.connector.connect(**DB_CONFIG)
            cursor = connection.cursor(dictionary=True)
            
            cursor.execute("SELECT name FROM suppliers ORDER BY name ASC")
            self.supplier_options_list = [row["name"] for row in cursor.fetchall()]
            
            cursor.execute("SELECT name FROM locations ORDER BY name ASC")
            self.location_options_list = [row["name"] for row in cursor.fetchall()]
            
        except Error as exc:
            print(f"Notice: Could not load dropdowns (tables might be empty). {exc}")
        finally:
            if "cursor" in locals():
                cursor.close()
            if "connection" in locals():
                connection.close()

    def handle_logout(self):
        if messagebox.askyesno("Confirm Logout", "Are you sure you want to log out of the staff portal?"):
            self.destroy()
            login_script = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "Login",
                "login.py",
            )
            subprocess.Popen([sys.executable, login_script], cwd=os.path.dirname(login_script))

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

    def toggle_custom_warranty(self, event=None):
        if self.warranty_combo.get() == "Custom":
            self.f_custom_warranty.pack(fill="x", pady=(2, 0))
        else:
            self.f_custom_warranty.pack_forget()
            self.asset_entries["custom_warranty"].delete(0, tk.END)

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
                conn = mysql.connector.connect(**DB_CONFIG)
                cur = conn.cursor()
                cur.execute("INSERT INTO suppliers (name) VALUES (%s)", (new_sup,))
                conn.commit()
                conn.close()
            except Error as exc:
                messagebox.showerror("Database Error", f"Failed to save supplier to database.\n{exc}", parent=dialog)
                return
            
            self.supplier_options_list.append(new_sup)
            self.supplier_options_list.sort() 
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
                    conn = mysql.connector.connect(**DB_CONFIG)
                    cur = conn.cursor()
                    cur.execute("DELETE FROM suppliers WHERE name = %s", (target,))
                    conn.commit()
                    conn.close()
                except Error as exc:
                    messagebox.showerror("Error", "Cannot delete this supplier because it is currently assigned to an existing asset.", parent=dialog)
                    return
                
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
                conn = mysql.connector.connect(**DB_CONFIG)
                cur = conn.cursor()
                cur.execute("INSERT INTO locations (name) VALUES (%s)", (new_loc,))
                conn.commit()
                conn.close()
            except Error as exc:
                messagebox.showerror("Database Error", f"Failed to save location to database.\n{exc}", parent=dialog)
                return
            
            self.location_options_list.append(new_loc)
            self.location_options_list.sort()
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
                    conn = mysql.connector.connect(**DB_CONFIG)
                    cur = conn.cursor()
                    cur.execute("DELETE FROM locations WHERE name = %s", (target,))
                    conn.commit()
                    conn.close()
                except Error as exc:
                    messagebox.showerror("Error", "Cannot delete this location because it is currently assigned to an existing asset.", parent=dialog)
                    return

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
                self.username,
                "Staff",
                description,
            )
        except Exception as exc:
            messagebox.showerror("Database Error", f"Could not save asset.\n{exc}")
            return

        self.load_inventory()
        self.refresh_dashboard_data()

        messagebox.showinfo(
            "Success", 
            f"Asset '{sanitized_name}' validated and saved successfully!\nAudit trail log recorded."
        )


    # ==========================================
    # 8. GENERAL UTILITIES
    # ==========================================
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

# ==========================================
# RUN APPLICATION
# ==========================================

# Tab mixins
from tabs.dashboard_tab import DashboardTabMixin
from tabs.inventory_tab import InventoryTabMixin
from tabs.add_asset_tab import AddAssetTabMixin

_TAB_MIXINS = (DashboardTabMixin, InventoryTabMixin, AddAssetTabMixin)
for _tab_mixin in _TAB_MIXINS:
    for _tab_name, _tab_method in vars(_tab_mixin).items():
        if not _tab_name.startswith("__") and callable(_tab_method):
            setattr(StaffAssetManagementApp, _tab_name, _tab_method)

if __name__ == "__main__":
    username = "Staff"
    if "--username" in sys.argv:
        username_index = sys.argv.index("--username") + 1
        if username_index < len(sys.argv):
            username = sys.argv[username_index]
    app = StaffAssetManagementApp(username=username)
    app.mainloop()
