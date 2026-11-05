import os
import sys

_ADMIN_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ADMIN_DIR not in sys.path:
    sys.path.insert(0, _ADMIN_DIR)


from staff import *


class DashboardTabMixin:
    def render_dashboard(self):
        dashboard_wrapper = tk.Frame(self.content_frame, bg=THEME["bg_main"])
        dashboard_wrapper.pack(fill="both", expand=True, padx=30, pady=(35, 35))

        tk.Label(
            dashboard_wrapper, text="Staff Dashboard Overview", 
            font=FONTS["title"], bg=THEME["bg_main"], fg=THEME["bg_header"]
        ).pack(pady=(0, 15), anchor="nw")

        row1 = tk.Frame(dashboard_wrapper, bg=THEME["bg_main"])
        row1.pack(fill="x", pady=(0, 5))

        self._create_metric_card(row1, "Total Stored Asset", self.val_total_stored, THEME["bg_header"])
        self._create_metric_card(row1, "Low Stock / Critical Items", self.val_low_stock, THEME["accent_danger"])

        row2 = tk.Frame(dashboard_wrapper, bg=THEME["bg_main"])
        row2.pack(fill="x", pady=(5, 0))

        pie_frame = tk.Frame(row2, bg=THEME["bg_card"], highlightbackground=THEME["border"], highlightthickness=1)
        pie_frame.pack(side="left", fill="both", expand=True, padx=5)

        tk.Label(pie_frame, text="Stock Categories", font=("Arial", 12, "bold"), bg=THEME["bg_card"], fg=THEME["text_dark"]).pack(anchor="nw", padx=15, pady=(15, 5))

        pie_wrapper = tk.Frame(pie_frame, bg=THEME["bg_card"])
        pie_wrapper.pack(anchor="center", pady=(15, 20))

        self.pie_canvas = tk.Canvas(pie_wrapper, bg=THEME["bg_card"], highlightthickness=0, width=160, height=160)
        self.pie_canvas.pack(side="left", padx=5, pady=5)

        legend_frame = tk.Frame(pie_wrapper, bg=THEME["bg_card"])
        legend_frame.pack(side="left", padx=(10, 15), pady=10, anchor="w")
        tk.Label(legend_frame, text="â–  Hardware", font=("Arial", 9), bg=THEME["bg_card"], fg="#3A6080").pack(anchor="w", pady=4)
        tk.Label(legend_frame, text="â–  Peripherals", font=("Arial", 9), bg=THEME["bg_card"], fg="#5A80A0").pack(anchor="w", pady=4)
        tk.Label(legend_frame, text="â–  Networking", font=("Arial", 9), bg=THEME["bg_card"], fg="#E74C3C").pack(anchor="w", pady=4)

        self.update_pie_chart({"Hardware": 0, "Peripherals": 0, "Networking": 0})

        activity_frame = tk.Frame(row2, bg=THEME["bg_card"], highlightbackground=THEME["border"], highlightthickness=1)
        activity_frame.pack(side="left", fill="both", expand=True, padx=5)
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


if __name__ == "__main__":
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from staff import StaffAssetManagementApp
    app = StaffAssetManagementApp(username="Staff")
    app.after(0, lambda: app.switch_tab('Dashboard'))
    app.mainloop()

