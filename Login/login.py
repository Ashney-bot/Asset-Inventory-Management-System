import tkinter as tk
from tkinter import messagebox
import os
import ctypes
import subprocess
import sys
from PIL import Image, ImageTk
import hashlib
import mysql.connector
from mysql.connector import Error


DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "asset inventory management system",
}


def create_pending_user(username, email, password):
    connection = mysql.connector.connect(**DB_CONFIG)
    cursor = connection.cursor()
    try:
        password_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
        cursor.execute(
            """
            INSERT INTO users
                (username, email, password_hash, role, access_status)
            VALUES (%s, %s, %s, 'Staff', 'Pending')
            """,
            (username, email, password_hash),
        )
        connection.commit()
    finally:
        cursor.close()
        connection.close()


def authenticate_user(email, password):
    connection = mysql.connector.connect(**DB_CONFIG)
    cursor = connection.cursor(dictionary=True)
    try:
        password_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
        cursor.execute(
            """
            SELECT user_id, username, email, role, access_status
            FROM users
            WHERE email = %s
              AND password_hash = %s
              AND access_status = 'Active'
            """,
            (email, password_hash),
        )
        return cursor.fetchone()
    finally:
        cursor.close()
        connection.close()

# authentication logic
def handle_login():
    email = email_entry.get().strip()
    password = pass_entry.get()
    if email == "Enter your email..." or password == "Enter your password...":
        messagebox.showerror("Login Error", "Enter your email and password.", parent=root)
        return

    try:
        user = authenticate_user(email, password)
        if not user:
            messagebox.showerror("Login Failed", "Invalid credentials or your account has not been approved.", parent=root)
            return
        messagebox.showinfo("Login Successful", f"Welcome, {user['username']}!", parent=root)

        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        role = str(user["role"]).lower()
        if role == "admin":
            dashboard_script = os.path.join(project_root, "Admin", "dashboard.py")
        elif role == "staff":
            dashboard_script = os.path.join(project_root, "Staff", "staff.py")
        else:
            messagebox.showerror("Login Error", f"Unknown account role: {user['role']}", parent=root)
            return

        subprocess.Popen(
            [sys.executable, dashboard_script, "--username", user["username"]],
            cwd=os.path.dirname(dashboard_script),
        )
        root.destroy()
    except Error as exc:
        messagebox.showerror("Database Error", f"Could not connect to MySQL.\n{exc}", parent=root)

# placeholder focus handlers
def on_email_focus_in(event):
    if email_entry.get() == "Enter your email...":
        email_entry.delete(0, tk.END)
        email_entry.config(fg="#333333")

def on_email_focus_out(event):
    if not email_entry.get():
        email_entry.insert(0, "Enter your email...")
        email_entry.config(fg="#888888")

def on_pass_focus_in(event):
    if pass_entry.get() == "Enter your password...":
        pass_entry.delete(0, tk.END)
        pass_entry.config(fg="#333333", show="•")

def on_pass_focus_out(event):
    if not pass_entry.get():
        pass_entry.config(show="")
        pass_entry.insert(0, "Enter your password...")
        pass_entry.config(fg="#888888")

# --- REGISTRATION WINDOW ---
def open_register(parent):
    reg_dialog = tk.Toplevel(parent)
    reg_dialog.title("Register Account")
    reg_dialog.geometry("400x620")
    reg_dialog.configure(bg="white")
    reg_dialog.transient(parent)
    reg_dialog.grab_set()

    reg_dialog.resizable(False, False)

    try:
        reg_dialog.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(reg_dialog.winfo_id())
        GWL_STYLE = -16
        WS_MINIMIZEBOX = 0x00020000
        WS_MAXIMIZEBOX = 0x00010000

        try:
            GetWindowLong = ctypes.windll.user32.GetWindowLongPtrW
            SetWindowLong = ctypes.windll.user32.SetWindowLongPtrW
        except AttributeError:
            GetWindowLong = ctypes.windll.user32.GetWindowLongW
            SetWindowLong = ctypes.windll.user32.SetWindowLongW

        style = GetWindowLong(hwnd, GWL_STYLE)
        style = style & ~WS_MINIMIZEBOX
        style = style & ~WS_MAXIMIZEBOX
        SetWindowLong(hwnd, GWL_STYLE, style)
    except Exception:
        pass

    script_dir = os.path.dirname(os.path.abspath(__file__))
    logo_path = os.path.join(script_dir, "logo.png")

    try:
        original_img = Image.open(logo_path)
        resized_img = original_img.resize((90, 90), Image.Resampling.LANCZOS)
        logo_img = ImageTk.PhotoImage(resized_img)
        
        logo_label = tk.Label(reg_dialog, image=logo_img, bg="white")
        logo_label.image = logo_img
        logo_label.place(relx=0.5, y=60, anchor="center")
    except Exception:
        logo_label = tk.Label(reg_dialog, text="[Logo]", bg="white", font=("Arial", 10, "italic"), fg="#888888")
        logo_label.place(relx=0.5, y=60, anchor="center")

    title_lbl = tk.Label(
        reg_dialog, text="Create an Account", bg="white", fg="#3A6080", font=("Arial", 14, "bold")
    )
    title_lbl.place(relx=0.5, y=125, anchor="center")

    # --- USERNAME FIELD ---
    uname_label = tk.Label(reg_dialog, text="Username", bg="white", fg="#333333", font=("Arial", 9, "bold"))
    uname_label.place(x=40, y=160, anchor="sw")

    uname_frame = tk.Frame(reg_dialog, bg="white", highlightthickness=1, highlightbackground="#D0D0D0")
    uname_frame.place(relx=0.5, y=190, anchor="center", width=320, height=38)

    uname_entry = tk.Entry(uname_frame, bg="white", bd=0, font=("Arial", 10), fg="#333333")
    uname_entry.place(x=10, y=8, width=300)

    # --- EMAIL FIELD ---
    email_label = tk.Label(reg_dialog, text="Email", bg="white", fg="#333333", font=("Arial", 9, "bold"))
    email_label.place(x=40, y=225, anchor="sw")

    email_frame = tk.Frame(reg_dialog, bg="white", highlightthickness=1, highlightbackground="#D0D0D0")
    email_frame.place(relx=0.5, y=255, anchor="center", width=320, height=38)

    email_entry_reg = tk.Entry(email_frame, bg="white", bd=0, font=("Arial", 10), fg="#333333")
    email_entry_reg.place(x=10, y=8, width=300)

    # --- PASSWORD FIELD ---
    pass_label = tk.Label(reg_dialog, text="Password", bg="white", fg="#333333", font=("Arial", 9, "bold"))
    pass_label.place(x=40, y=290, anchor="sw")

    pass_frame = tk.Frame(reg_dialog, bg="white", highlightthickness=1, highlightbackground="#D0D0D0")
    pass_frame.place(relx=0.5, y=320, anchor="center", width=320, height=38)

    pass_entry_reg = tk.Entry(pass_frame, bg="white", bd=0, font=("Arial", 10), fg="#333333", show="•")
    pass_entry_reg.place(x=10, y=8, width=300)

    # --- CONFIRM PASSWORD FIELD ---
    conf_pass_label = tk.Label(reg_dialog, text="Confirm Password", bg="white", fg="#333333", font=("Arial", 9, "bold"))
    conf_pass_label.place(x=40, y=355, anchor="sw")

    conf_pass_frame = tk.Frame(reg_dialog, bg="white", highlightthickness=1, highlightbackground="#D0D0D0")
    conf_pass_frame.place(relx=0.5, y=385, anchor="center", width=320, height=38)

    conf_pass_entry = tk.Entry(conf_pass_frame, bg="white", bd=0, font=("Arial", 10), fg="#333333", show="•")
    conf_pass_entry.place(x=10, y=8, width=300)

    def handle_register():
        username = uname_entry.get().strip()
        email = email_entry_reg.get().strip()
        pwd = pass_entry_reg.get().strip()
        conf_pwd = conf_pass_entry.get().strip()

        if not username or not email or not pwd or not conf_pwd:
            messagebox.showerror("Error", "All fields are required!", parent=reg_dialog)
            return

        if pwd != conf_pwd:
            messagebox.showerror("Error", "Passwords do not match!", parent=reg_dialog)
            return

        if len(pwd) < 6:
            messagebox.showerror("Error", "Password must be at least 6 characters.", parent=reg_dialog)
            return

        try:
            create_pending_user(username, email, pwd)
        except Error as exc:
            if getattr(exc, "errno", None) == 1062:
                messagebox.showerror("Registration Failed", "Username or email is already registered.", parent=reg_dialog)
            else:
                messagebox.showerror("Database Error", f"Could not save the account.\n{exc}", parent=reg_dialog)
            return

        messagebox.showinfo("Registration Successful", "Your account has been created successfully!\n\nYour access status is 'Pending'. Please wait for an Admin to approve your account before logging in.", parent=reg_dialog)
        reg_dialog.destroy()

    # --- REGISTER BUTTON ---
    submit_btn = tk.Button(
        reg_dialog, text="Register", font=("Arial", 11, "bold"), 
        bg="#27AE60", fg="white", bd=0, activebackground="#1E8449", 
        activeforeground="white", cursor="hand2", command=handle_register
    )
    submit_btn.place(relx=0.5, y=455, anchor="center", width=320, height=42)

    # --- BACK TO LOGIN BUTTON ---
    back_btn = tk.Button(
        reg_dialog, text="Back to Login", font=("Arial", 10, "bold"), 
        bg="#95A5A6", fg="white", bd=0, activebackground="#7F8C8D", 
        activeforeground="white", cursor="hand2", command=reg_dialog.destroy
    )
    back_btn.place(relx=0.5, y=510, anchor="center", width=320, height=40)

# --- FORGOT PASSWORD WINDOW ---
def open_forgot_password(parent):
    forgot_dialog = tk.Toplevel(parent)
    forgot_dialog.title("Forgot Password")
    forgot_dialog.geometry("400x620")
    forgot_dialog.configure(bg="white")
    forgot_dialog.transient(parent)
    forgot_dialog.grab_set()

    forgot_dialog.resizable(False, False)

    try:
        forgot_dialog.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(forgot_dialog.winfo_id())
        GWL_STYLE = -16
        WS_MINIMIZEBOX = 0x00020000
        WS_MAXIMIZEBOX = 0x00010000

        try:
            GetWindowLong = ctypes.windll.user32.GetWindowLongPtrW
            SetWindowLong = ctypes.windll.user32.SetWindowLongPtrW
        except AttributeError:
            GetWindowLong = ctypes.windll.user32.GetWindowLongW
            SetWindowLong = ctypes.windll.user32.SetWindowLongW

        style = GetWindowLong(hwnd, GWL_STYLE)
        style = style & ~WS_MINIMIZEBOX
        style = style & ~WS_MAXIMIZEBOX
        SetWindowLong(hwnd, GWL_STYLE, style)
    except Exception:
        pass

    script_dir = os.path.dirname(os.path.abspath(__file__))
    logo_path = os.path.join(script_dir, "logo.png")

    try:
        original_img = Image.open(logo_path)
        resized_img = original_img.resize((90, 90), Image.Resampling.LANCZOS)
        logo_img = ImageTk.PhotoImage(resized_img)
        
        logo_label = tk.Label(forgot_dialog, image=logo_img, bg="white")
        logo_label.image = logo_img
        logo_label.place(relx=0.5, y=60, anchor="center")
    except Exception:
        logo_label = tk.Label(forgot_dialog, text="[Logo]", bg="white", font=("Arial", 10, "italic"), fg="#888888")
        logo_label.place(relx=0.5, y=60, anchor="center")

    title_lbl = tk.Label(
        forgot_dialog, text="Reset Your Password", bg="white", fg="#3A6080", font=("Arial", 14, "bold")
    )
    title_lbl.place(relx=0.5, y=125, anchor="center")

    email_label = tk.Label(forgot_dialog, text="Email", bg="white", fg="#333333", font=("Arial", 9, "bold"))
    email_label.place(x=40, y=160, anchor="sw")

    email_frame = tk.Frame(forgot_dialog, bg="white", highlightthickness=1, highlightbackground="#D0D0D0")
    email_frame.place(relx=0.5, y=190, anchor="center", width=320, height=38)

    email_entry_fp = tk.Entry(email_frame, bg="white", bd=0, font=("Arial", 10), fg="#333333")
    email_entry_fp.place(x=10, y=8, width=300)

    new_pass_label = tk.Label(forgot_dialog, text="New Password", bg="white", fg="#333333", font=("Arial", 9, "bold"))
    new_pass_label.place(x=40, y=225, anchor="sw")

    new_pass_frame = tk.Frame(forgot_dialog, bg="white", highlightthickness=1, highlightbackground="#D0D0D0")
    new_pass_frame.place(relx=0.5, y=255, anchor="center", width=320, height=38)

    new_pass_entry = tk.Entry(new_pass_frame, bg="white", bd=0, font=("Arial", 10), fg="#333333", show="•")
    new_pass_entry.place(x=10, y=8, width=300)

    conf_pass_label = tk.Label(forgot_dialog, text="Confirm Password", bg="white", fg="#333333", font=("Arial", 9, "bold"))
    conf_pass_label.place(x=40, y=290, anchor="sw")

    conf_pass_frame = tk.Frame(forgot_dialog, bg="white", highlightthickness=1, highlightbackground="#D0D0D0")
    conf_pass_frame.place(relx=0.5, y=320, anchor="center", width=320, height=38)

    conf_pass_entry = tk.Entry(conf_pass_frame, bg="white", bd=0, font=("Arial", 10), fg="#333333", show="•")
    conf_pass_entry.place(x=10, y=8, width=300)

    def handle_reset():
        email = email_entry_fp.get().strip()
        new_pass = new_pass_entry.get().strip()
        conf_pass = conf_pass_entry.get().strip()

        if not email or not new_pass or not conf_pass:
            messagebox.showerror("Error", "All fields are required!", parent=forgot_dialog)
            return

        if new_pass != conf_pass:
            messagebox.showerror("Error", "New passwords do not match!", parent=forgot_dialog)
            return

        connection = None
        cursor = None
        try:
            connection = mysql.connector.connect(**DB_CONFIG)
            cursor = connection.cursor(dictionary=True)
            cursor.execute(
                """
                SELECT user_id, username, email, role
                FROM users
                WHERE LOWER(email) = LOWER(%s)
                LIMIT 1
                """,
                (email,),
            )
            user = cursor.fetchone()
            if not user:
                messagebox.showerror(
                    "Email Not Found",
                    "No account is registered with that email address.",
                    parent=forgot_dialog,
                )
                return

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS password_reset_requests (
                    request_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                    user_id INT UNSIGNED NOT NULL,
                    status ENUM('Pending', 'Approved', 'Denied') NOT NULL DEFAULT 'Pending',
                    requested_password_hash VARCHAR(64) NULL,
                    requested_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    resolved_at TIMESTAMP NULL,
                    PRIMARY KEY (request_id),
                    KEY idx_password_reset_user (user_id),
                    CONSTRAINT fk_reset_user
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                        ON UPDATE CASCADE ON DELETE CASCADE
                ) ENGINE=InnoDB
                """
            )

            cursor.execute(
                """
                SELECT request_id
                FROM password_reset_requests
                WHERE user_id = %s AND status = 'Pending'
                LIMIT 1
                """,
                (user["user_id"],),
            )
            if cursor.fetchone():
                messagebox.showwarning(
                    "Request Pending",
                    "A password reset request is already pending for this account.",
                    parent=forgot_dialog,
                )
                return

            cursor.execute(
                """
                SHOW COLUMNS FROM password_reset_requests
                LIKE 'requested_password_hash'
                """
            )
            if not cursor.fetchone():
                cursor.execute(
                    """
                    ALTER TABLE password_reset_requests
                    ADD COLUMN requested_password_hash VARCHAR(64) NULL
                    """
                )

            cursor.execute(
                """
                INSERT INTO password_reset_requests
                    (user_id, status, requested_password_hash)
                VALUES (%s, 'Pending', %s)
                """,
                (user["user_id"], hashlib.sha256(new_pass.encode("utf-8")).hexdigest()),
            )

            cursor.execute(
                """
                INSERT INTO activity_logs (user_id, username, role, action, description)
                VALUES (%s, %s, 'System', 'CREATE', %s)
                """,
                (
                    user["user_id"],
                    user["username"],
                    f"Password reset requested for '{user['email']}'",
                ),
            )
            connection.commit()
            messagebox.showinfo(
                "Success",
                "Password reset request sent successfully!",
                parent=forgot_dialog,
            )
            forgot_dialog.destroy()
        except Error as exc:
            if connection is not None:
                connection.rollback()
            messagebox.showerror(
                "Database Error",
                f"Could not verify the email or submit the reset request.\n{exc}",
                parent=forgot_dialog,
            )
        finally:
            if cursor is not None:
                cursor.close()
            if connection is not None and connection.is_connected():
                connection.close()

    submit_btn = tk.Button(
        forgot_dialog, text="Send Reset Request", font=("Arial", 11, "bold"), 
        bg="#3A6080", fg="white", bd=0, activebackground="#2A4863", 
        activeforeground="white", cursor="hand2", command=handle_reset
    )
    submit_btn.place(relx=0.5, y=390, anchor="center", width=320, height=42)

    back_btn = tk.Button(
        forgot_dialog, text="Back to Login", font=("Arial", 10, "bold"), 
        bg="#95A5A6", fg="white", bd=0, activebackground="#7F8C8D", 
        activeforeground="white", cursor="hand2", command=forgot_dialog.destroy
    )
    back_btn.place(relx=0.5, y=510, anchor="center", width=320, height=40)

# --- MAIN LOGIN WINDOW ---
root = tk.Tk()
root.title("Login")
root.geometry("400x620")
root.configure(bg="white")

root.resizable(False, False)

root.update_idletasks()
try:
    hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
    GWL_STYLE = -16
    WS_MINIMIZEBOX = 0x00020000
    WS_MAXIMIZEBOX = 0x00010000

    try:
        GetWindowLong = ctypes.windll.user32.GetWindowLongPtrW
        SetWindowLong = ctypes.windll.user32.SetWindowLongPtrW
    except AttributeError:
        GetWindowLong = ctypes.windll.user32.GetWindowLongW
        SetWindowLong = ctypes.windll.user32.SetWindowLongW

    style = GetWindowLong(hwnd, GWL_STYLE)
    style = style & ~WS_MINIMIZEBOX
    style = style & ~WS_MAXIMIZEBOX
    SetWindowLong(hwnd, GWL_STYLE, style)
except Exception:
    pass

script_dir = os.path.dirname(os.path.abspath(__file__))
logo_path = os.path.join(script_dir, "logo.png")

try:
    original_img = Image.open(logo_path)
    resized_img = original_img.resize((140, 140), Image.Resampling.LANCZOS)
    logo_img = ImageTk.PhotoImage(resized_img)
    
    logo_label = tk.Label(root, image=logo_img, bg="white")
    logo_label.image = logo_img
    logo_label.place(relx=0.5, y=110, anchor="center")
except Exception as e:
    logo_label = tk.Label(root, text="[logo.png missing]", bg="white", font=("Arial", 10, "italic"), fg="#888888")
    logo_label.place(relx=0.5, y=110, anchor="center")

# --- EMAIL SECTION ---
email_label = tk.Label(root, text="Email", bg="white", fg="#333333", font=("Arial", 9, "bold"))
email_label.place(x=40, y=210, anchor="sw")

email_frame = tk.Frame(root, bg="white", highlightthickness=1, highlightbackground="#D0D0D0")
email_frame.place(relx=0.5, y=240, anchor="center", width=320, height=42)

email_entry = tk.Entry(email_frame, bg="white", bd=0, font=("Arial", 11), fg="#888888")
email_entry.insert(0, "Enter your email...")
email_entry.place(x=12, y=10, width=296)
email_entry.bind("<FocusIn>", on_email_focus_in)
email_entry.bind("<FocusOut>", on_email_focus_out)

# --- PASSWORD SECTION ---
pass_label = tk.Label(root, text="Password", bg="white", fg="#333333", font=("Arial", 9, "bold"))
pass_label.place(x=40, y=295, anchor="sw")

pass_frame = tk.Frame(root, bg="white", highlightthickness=1, highlightbackground="#D0D0D0")
pass_frame.place(relx=0.5, y=325, anchor="center", width=320, height=42)

pass_entry = tk.Entry(pass_frame, bg="white", bd=0, font=("Arial", 11), fg="#888888")
pass_entry.insert(0, "Enter your password...")
pass_entry.place(x=12, y=10, width=296)
pass_entry.bind("<FocusIn>", on_pass_focus_in)
pass_entry.bind("<FocusOut>", on_pass_focus_out)

forgot_lbl = tk.Label(root, text="Forgot Password?", bg="white", fg="#3A6080", font=("Arial", 9, "underline"), cursor="hand2")
forgot_lbl.place(x=360, y=355, anchor="ne")
forgot_lbl.bind("<Button-1>", lambda e: open_forgot_password(root))

login_btn = tk.Button(
    root, text="Login", font=("Arial", 11, "bold"), 
    bg="#3A6080", fg="white", bd=0, activebackground="#2A4863", 
    activeforeground="white", cursor="hand2", command=handle_login
)
login_btn.place(relx=0.5, y=435, anchor="center", width=320, height=45)

divider = tk.Frame(root, bg="#E5E5E5")
divider.place(relx=0.5, y=510, anchor="center", width=320, height=1)

# register link
register_lbl = tk.Label(
    root, text="Don't have an account yet? Register here", bg="white", fg="#3A6080", font=("Arial", 9), cursor="hand2"
)
register_lbl.place(relx=0.5, y=550, anchor="center")
register_lbl.bind("<Button-1>", lambda e: open_register(root))

root.mainloop()