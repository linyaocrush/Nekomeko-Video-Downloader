import webbrowser

import customtkinter as ctk

from ..core import constants as _c


class StatsWindow(ctk.CTkToplevel):
    def __init__(self, parent, db):
        super().__init__(parent)
        self.title("📊 喵喵的大数据")
        self.geometry("1050x750")
        self.minsize(900, 650)
        self.db = db
        self.transient(parent)
        self.configure(fg_color=_c.CURRENT_THEME["main_bg"])
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        title_frame = ctk.CTkFrame(self, fg_color="transparent")
        title_frame.grid(row=0, column=0, pady=(15, 5))
        ctk.CTkLabel(title_frame, text="📅 记忆回廊 & 全域统计", font=("微软雅黑", 20, "bold"), text_color=_c.CURRENT_THEME["accent"]).pack()

        self.tabview = ctk.CTkTabview(self, segmented_button_selected_color=_c.CURRENT_THEME["accent"])
        self.tabview.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="nsew")
        self.tab_stats = self.tabview.add("📊 详细战报")
        self.tab_history = self.tabview.add("📜 历史清单")
        for t in [self.tab_stats, self.tab_history]:
            t.grid_columnconfigure(0, weight=1)
        self.tab_stats.grid_rowconfigure(0, weight=1)
        self.tab_history.grid_rowconfigure(2, weight=1)
        self.build_stats_tab()
        self.build_history_tab()

    def build_stats_tab(self):
        data = self.db.get_full_stats()
        main_frame = ctk.CTkFrame(self.tab_stats, fg_color="transparent")
        main_frame.grid(row=0, column=0, sticky="nsew")
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_rowconfigure(1, weight=1)
        main_frame.grid_rowconfigure(2, weight=4)

        card_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        card_frame.grid(row=0, column=0, sticky="nsew", pady=5)
        for i in range(4):
            card_frame.grid_columnconfigure(i, weight=1)

        t_gb = data["total_size"] / (1024 ** 3)
        spd = (data["total_size"] / data["total_time"] / (1024 ** 2)) if data["total_time"] > 0 else 0
        hrs = data["total_time"] / 3600
        c_bg = _c.CURRENT_THEME["panel_bg"]
        self.mk_card(card_frame, 0, "📦 总搬运量", f"{t_gb:.2f} GB", c_bg, "#1E90FF")
        self.mk_card(card_frame, 1, "⚡ 平均速度", f"{spd:.1f} MB/s", c_bg, "#00CB82")
        self.mk_card(card_frame, 2, "⏳ 抓老鼠耗时", f"{hrs:.1f} 小时", c_bg, "#FF8C00")
        self.mk_card(card_frame, 3, "🎬 视频总数", f"{data['total_count']} 个", c_bg, _c.CURRENT_THEME["accent"])

        p_frame = ctk.CTkFrame(main_frame, fg_color=_c.CURRENT_THEME["secondary"], corner_radius=10)
        p_frame.grid(row=1, column=0, sticky="nsew", pady=5)
        p_frame.grid_columnconfigure((0, 1, 2), weight=1)
        self.mk_period(p_frame, 0, "📅 今日", data['today_count'], data['today_size'])
        self.mk_period(p_frame, 1, "📅 本周", data['week_count'], data['week_size'])
        self.mk_period(p_frame, 2, "📅 本月", data['month_count'], data['month_size'])

        charts = ctk.CTkFrame(main_frame, fg_color="transparent")
        charts.grid(row=2, column=0, sticky="nsew", pady=5)
        charts.grid_columnconfigure((0, 1), weight=1)
        charts.grid_rowconfigure((0, 1), weight=1)
        self.mk_chart_box(charts, 0, 0, "🕒 活跃时段", lambda p: self.draw_bar(p, data["hours"]))
        self.mk_chart_box(charts, 0, 1, "🌍 平台分布", lambda p: self.draw_list(p, data["platforms"]))
        d_map = {
            "短 (<5m)": data["durations"]["short"],
            "中 (5-30m)": data["durations"]["medium"],
            "长 (>30m)": data["durations"]["long"],
        }
        self.mk_chart_box(charts, 1, 0, "📏 时长分布", lambda p: self.draw_list(p, d_map))
        ranks = self.db.get_top_uploaders()
        tup = {n: c for n, c in ranks}
        self.mk_chart_box(charts, 1, 1, "🏆 Top UP主", lambda p: self.draw_list(p, tup))

    def mk_card(self, p, c, t, v, bg, fg):
        f = ctk.CTkFrame(p, fg_color=bg, corner_radius=10)
        f.grid(row=0, column=c, sticky="nsew", padx=3)
        f.grid_columnconfigure(0, weight=1)
        f.grid_rowconfigure((0, 3), weight=1)
        ctk.CTkLabel(f, text=t, font=("微软雅黑", 11), text_color="#666").grid(row=1, column=0)
        ctk.CTkLabel(f, text=v, font=("Arial", 18, "bold"), text_color=fg).grid(row=2, column=0)

    def mk_period(self, p, c, t, count, size):
        f = ctk.CTkFrame(p, fg_color="transparent")
        f.grid(row=0, column=c, sticky="ns", padx=10, pady=5)
        ctk.CTkLabel(f, text=t, font=("微软雅黑", 12, "bold"), text_color="gray").pack()
        ctk.CTkLabel(f, text=f"{count}个", font=("Arial", 18, "bold"), text_color=_c.CURRENT_THEME["accent"]).pack()
        ctk.CTkLabel(f, text=f"({size // 1048576} MB)", font=("Arial", 10), text_color="#888").pack()

    def mk_chart_box(self, p, r, c, t, func):
        f = ctk.CTkFrame(p, fg_color=_c.CURRENT_THEME["secondary"], corner_radius=10)
        f.grid(row=r, column=c, sticky="nsew", padx=4, pady=4)
        f.grid_rowconfigure(1, weight=1)
        f.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(f, text=t, font=("微软雅黑", 11, "bold"), text_color="#888", anchor="w").grid(row=0, column=0, sticky="w", padx=10, pady=5)
        c_frame = ctk.CTkFrame(f, fg_color="transparent")
        c_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        func(c_frame)

    def draw_bar(self, p, cnt):
        periods = [("深夜", range(0, 6)), ("早晨", range(6, 12)), ("午后", range(12, 18)), ("夜晚", range(18, 24))]
        sums = [sum(cnt[h] for h in rng) for _, rng in periods]
        mx = max(sums) if sums and max(sums) > 0 else 1
        for i, (n, _) in enumerate(periods):
            p.grid_rowconfigure(i, weight=1)
            p.grid_columnconfigure(1, weight=1)
            ctk.CTkLabel(p, text=n, width=35, font=("微软雅黑", 10), text_color=_c.CURRENT_THEME["text"], anchor="w").grid(row=i, column=0)
            pb = ctk.CTkProgressBar(p, height=10, progress_color=_c.CURRENT_THEME["accent"])
            pb.grid(row=i, column=1, sticky="ew", padx=5)
            pb.set(sums[i] / mx)
            ctk.CTkLabel(p, text=str(sums[i]), width=25, font=("Arial", 10), text_color=_c.CURRENT_THEME["text"], anchor="e").grid(row=i, column=2)

    def draw_list(self, p, d):
        items = sorted(d.items(), key=lambda x: x[1], reverse=True)[:5]
        if not items:
            ctk.CTkLabel(p, text="无数据", text_color="#ccc").pack(expand=True)
            return
        mx = items[0][1] if items[0][1] > 0 else 1
        for i, (k, v) in enumerate(items):
            p.grid_rowconfigure(i, weight=1)
            p.grid_columnconfigure(1, weight=1)
            ctk.CTkLabel(p, text=k[:12], width=80, font=("微软雅黑", 10), text_color=_c.CURRENT_THEME["text"], anchor="w").grid(row=i, column=0)
            pb = ctk.CTkProgressBar(p, height=10, progress_color="#87CEEB")
            pb.grid(row=i, column=1, sticky="ew", padx=5)
            pb.set(v / mx)
            ctk.CTkLabel(p, text=str(v), width=25, font=("Arial", 10), text_color=_c.CURRENT_THEME["text"], anchor="e").grid(row=i, column=2)

    def build_history_tab(self):
        import tkinter as tk

        c = ctk.CTkFrame(self.tab_history, fg_color="transparent")
        c.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *a: self.refresh_history_delayed())
        ctk.CTkEntry(c, textvariable=self.search_var, width=250, text_color=_c.CURRENT_THEME["text"], fg_color=_c.CURRENT_THEME["panel_bg"]).pack(side="left", padx=5)
        self.filter_visible = False
        self.btn_toggle_filter = ctk.CTkButton(c, text="🌪️ 筛选", width=60, fg_color="#9370DB", command=self.toggle_filters)
        self.btn_toggle_filter.pack(side="left", padx=5)
        ctk.CTkButton(c, text="🔄", width=40, fg_color="gray", command=self.refresh_history).pack(side="right", padx=5)

        self.filter_frame = ctk.CTkFrame(self.tab_history, fg_color=_c.CURRENT_THEME["panel_bg"], corner_radius=6)
        all_ups = ["全部"] + self.db.get_all_uploaders()
        plats = ["全部", "B站 (Bilibili)", "油管 (YouTube)", "抖音 (Douyin)", "推特 (X)"]
        ctk.CTkLabel(self.filter_frame, text="平台:", text_color=_c.CURRENT_THEME["text"]).pack(side="left", padx=5)
        self.c_plat_filter = ctk.CTkComboBox(self.filter_frame, values=plats, width=120, command=lambda x: self.refresh_history(), text_color=_c.CURRENT_THEME["text"], fg_color=_c.CURRENT_THEME["main_bg"])
        self.c_plat_filter.pack(side="left")
        ctk.CTkLabel(self.filter_frame, text="UP主:", text_color=_c.CURRENT_THEME["text"]).pack(side="left", padx=5)
        self.c_up_filter = ctk.CTkComboBox(self.filter_frame, values=all_ups, width=150, command=lambda x: self.refresh_history(), text_color=_c.CURRENT_THEME["text"], fg_color=_c.CURRENT_THEME["main_bg"])
        self.c_up_filter.pack(side="left")
        ctk.CTkButton(self.filter_frame, text="重置", width=50, fg_color="#CD5C5C", command=self.reset_filters).pack(side="left", padx=10)

        self.hist_scroll = ctk.CTkScrollableFrame(self.tab_history, fg_color="transparent")
        self.hist_scroll.grid(row=2, column=0, sticky="nsew", padx=5, pady=5)
        self.refresh_history()

    def toggle_filters(self):
        if self.filter_visible:
            self.filter_frame.grid_forget()
            self.filter_visible = False
            self.btn_toggle_filter.configure(fg_color="#9370DB")
        else:
            self.filter_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
            self.filter_visible = True
            self.btn_toggle_filter.configure(fg_color=_c.CURRENT_THEME["accent"])

    def reset_filters(self):
        self.c_plat_filter.set("全部")
        self.c_up_filter.set("全部")
        self.search_var.set("")
        self.refresh_history()

    def refresh_history_delayed(self):
        if hasattr(self, '_after_id'):
            self.after_cancel(self._after_id)
        self._after_id = self.after(500, self.refresh_history)

    def refresh_history(self):
        for w in self.hist_scroll.winfo_children():
            w.destroy()
        recs = self.db.search_history(
            self.search_var.get().strip(),
            self.c_up_filter.get(),
            self.c_plat_filter.get(),
        )
        if not recs:
            ctk.CTkLabel(self.hist_scroll, text="🔍 无结果", text_color=_c.CURRENT_THEME["text"]).pack(pady=20)
            return
        for r in recs:
            item = ctk.CTkFrame(self.hist_scroll, fg_color=_c.CURRENT_THEME["secondary"], corner_radius=6)
            item.pack(fill="x", pady=2, padx=5)
            f = ctk.CTkFrame(item, fg_color="transparent")
            f.pack(side="left", fill="x", expand=True, padx=8, pady=4)
            ctk.CTkLabel(f, text=r.title, font=("微软雅黑", 12, "bold"), text_color=_c.CURRENT_THEME["text"], anchor="w").pack(fill="x")
            ctk.CTkLabel(f, text=f"{r.uploader} | {r.download_date} | {r.size_mb:.1f}MB | ⏱ {r.duration}s", font=("微软雅黑", 10), text_color="gray", anchor="w").pack(fill="x")
            act = ctk.CTkFrame(item, fg_color="transparent")
            act.pack(side="right", padx=5)
            if r.webpage_url:
                ctk.CTkButton(act, text="📺", width=30, height=24, fg_color="#87CEEB", command=lambda u=r.webpage_url: webbrowser.open(u)).pack(side="left", padx=1)
            if r.uploader_url:
                ctk.CTkButton(act, text="🏠", width=30, height=24, fg_color="#DDA0DD", command=lambda u=r.uploader_url: webbrowser.open(u)).pack(side="left", padx=1)
