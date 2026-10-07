"""
QR Code Studio — โปรแกรมสร้าง QR Code ปรับสี / ขนาด / ใส่โลโก้ตรงกลางได้

ติดตั้ง:  pip install customtkinter "qrcode[pil]" pillow
รัน:      python qr_app.py
ทำเป็น .exe (Windows): ดับเบิลคลิก build_exe.bat
"""

import os
import tkinter as tk
import tkinter.font as tkfont
from tkinter import colorchooser, filedialog, messagebox

import customtkinter as ctk
import qrcode
from qrcode.constants import ERROR_CORRECT_H, ERROR_CORRECT_M
from qrcode.exceptions import DataOverflowError
from PIL import Image, ImageColor, ImageDraw

# ---------- ธีมสี ----------
ACCENT = "#0F766E"
ACCENT_HOVER = "#115E59"
ACCENT_SOFT = "#CCFBF1"
BG = "#EEF2F6"
CARD = "#FFFFFF"
STAGE = "#F8FAFC"
TEXT = "#0F172A"
MUTED = "#64748B"
LINE = "#E2E8F0"
WARN = "#B45309"
OK = "#15803D"

PRESETS = [  # (สีจุด, สีพื้น)
    ("#000000", "#FFFFFF"),
    ("#0F766E", "#FFFFFF"),
    ("#1E3A8A", "#F8FAFC"),
    ("#6D28D9", "#FAF5FF"),
    ("#BE123C", "#FFF1F2"),
    ("#7C2D12", "#FFF7ED"),
]

PREVIEW = 380

ctk.set_appearance_mode("light")


# ---------- ส่วนสร้าง QR ----------
def build_qr(data, fill, back, size, border, logo=None, logo_ratio=0.22, rounded=True):
    """คืนค่า (ภาพ PIL RGBA, เวอร์ชัน QR)"""
    qr = qrcode.QRCode(
        error_correction=ERROR_CORRECT_H if logo is not None else ERROR_CORRECT_M,
        box_size=10,
        border=border,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color=fill, back_color=back).convert("RGBA")
    img = img.resize((size, size), Image.NEAREST)

    if logo is not None:
        lg = logo.copy()
        max_logo = int(size * logo_ratio)
        lg.thumbnail((max_logo, max_logo), Image.LANCZOS)
        lw, lh = lg.size
        pad = max(4, int(size * 0.02))
        bw, bh = lw + pad * 2, lh + pad * 2
        box = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
        d = ImageDraw.Draw(box)
        if rounded:
            d.rounded_rectangle((0, 0, bw - 1, bh - 1), radius=min(bw, bh) // 5, fill=back)
        else:
            d.rectangle((0, 0, bw - 1, bh - 1), fill=back)
        box.paste(lg, (pad, pad), lg)
        img.paste(box, ((size - bw) // 2, (size - bh) // 2), box)

    return img, qr.version


def luminance(color):
    r, g, b = ImageColor.getrgb(color)[:3]

    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4

    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def contrast(a, b):
    la, lb = luminance(a), luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


# ---------- หน้าต่างโปรแกรม ----------
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("QR Code Studio")
        self.geometry("1060x720")
        self.minsize(920, 620)
        self.configure(fg_color=BG)

        fams = set(tkfont.families())
        self.fam = next((f for f in ("Leelawadee UI", "Noto Sans Thai", "Sarabun", "Tahoma") if f in fams), None)

        self.fill = "#0F766E"
        self.back = "#FFFFFF"
        self.logo = None
        self.current = None
        self._job = None
        self._status_job = None
        self.color_widgets = {}

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build_sidebar()
        self._build_preview()
        self.schedule()

    # ----- helpers -----
    def F(self, size, bold=False):
        kw = {"size": size, "weight": "bold" if bold else "normal"}
        if self.fam:
            kw["family"] = self.fam
        return ctk.CTkFont(**kw)

    def section(self, title, first=False):
        if not first:
            ctk.CTkFrame(self.sb, height=1, fg_color=LINE).pack(fill="x", padx=18, pady=(14, 12))
        ctk.CTkLabel(self.sb, text=title, font=self.F(14, True), text_color=TEXT).pack(anchor="w", padx=18, pady=(0, 4))

    def slider_row(self, label, from_, to, steps, value, fmt):
        top = ctk.CTkFrame(self.sb, fg_color="transparent")
        top.pack(fill="x", padx=18, pady=(6, 0))
        ctk.CTkLabel(top, text=label, font=self.F(13), text_color=TEXT).pack(side="left")
        val = ctk.CTkLabel(top, text=fmt(value), font=self.F(13, True), text_color=ACCENT)
        val.pack(side="right")

        def on_change(v):
            val.configure(text=fmt(v))
            self.schedule()

        s = ctk.CTkSlider(
            self.sb, from_=from_, to=to, number_of_steps=steps,
            button_color=ACCENT, button_hover_color=ACCENT_HOVER, progress_color=ACCENT,
            fg_color=LINE, command=on_change,
        )
        s.set(value)
        s.pack(fill="x", padx=12, pady=(2, 4))
        return s

    def color_row(self, label, which):
        row = ctk.CTkFrame(self.sb, fg_color="transparent")
        row.pack(fill="x", padx=18, pady=4)
        ctk.CTkLabel(row, text=label, font=self.F(13), text_color=TEXT, width=100, anchor="w").pack(side="left")
        color = getattr(self, which)
        sw = ctk.CTkButton(
            row, text="", width=38, height=32, corner_radius=8,
            fg_color=color, hover_color=color, border_width=1, border_color="#CBD5E1",
            command=lambda: self.pick_color(which),
        )
        sw.pack(side="left", padx=(0, 8))
        var = tk.StringVar(value=color)
        ent = ctk.CTkEntry(
            row, textvariable=var, width=110, height=32, font=self.F(13),
            fg_color=STAGE, border_color=LINE, text_color=TEXT, corner_radius=8,
        )
        ent.pack(side="left")
        ent.bind("<Return>", lambda e: self.set_color(which, var.get()))
        ent.bind("<FocusOut>", lambda e: self.set_color(which, var.get()))
        self.color_widgets[which] = (sw, var)

    # ----- layout -----
    def _build_sidebar(self):
        self.sb = ctk.CTkScrollableFrame(
            self, width=360, fg_color=CARD, corner_radius=18,
            scrollbar_button_color=LINE, scrollbar_button_hover_color="#CBD5E1",
        )
        self.sb.grid(row=0, column=0, sticky="nsew", padx=(18, 9), pady=18)

        head = ctk.CTkFrame(self.sb, fg_color="transparent")
        head.pack(fill="x", padx=18, pady=(14, 10))
        badge = ctk.CTkLabel(head, text="QR", width=42, height=42, corner_radius=12,
                             fg_color=ACCENT, text_color="white", font=self.F(16, True))
        badge.pack(side="left", padx=(0, 12))
        titles = ctk.CTkFrame(head, fg_color="transparent")
        titles.pack(side="left")
        ctk.CTkLabel(titles, text="QR Code Studio", font=self.F(20, True), text_color=TEXT).pack(anchor="w")
        ctk.CTkLabel(titles, text="ปรับสี ขนาด และใส่โลโก้ได้", font=self.F(12), text_color=MUTED).pack(anchor="w")

        # ข้อความ
        self.section("ข้อความหรือลิงก์", first=True)
        self.text = ctk.CTkTextbox(
            self.sb, height=86, font=self.F(13), fg_color=STAGE, border_color=LINE,
            border_width=1, corner_radius=10, text_color=TEXT, wrap="word",
        )
        self.text.pack(fill="x", padx=18, pady=(4, 0))
        self.text.insert("1.0", "https://www.example.com")
        self.text.bind("<KeyRelease>", lambda e: self.schedule())

        # สี
        self.section("สี")
        self.color_row("สีจุด QR", "fill")
        self.color_row("สีพื้นหลัง", "back")

        ctk.CTkLabel(self.sb, text="ชุดสีสำเร็จรูป", font=self.F(12), text_color=MUTED).pack(anchor="w", padx=18, pady=(8, 2))
        chips = ctk.CTkFrame(self.sb, fg_color="transparent")
        chips.pack(fill="x", padx=18)
        for f, b in PRESETS:
            ctk.CTkButton(
                chips, text="", width=34, height=34, corner_radius=17,
                fg_color=b, hover_color=b, border_width=8, border_color=f,
                command=lambda f=f, b=b: self.apply_preset(f, b),
            ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            chips, text="⇄ สลับ", width=64, height=34, corner_radius=17, font=self.F(12),
            fg_color=STAGE, hover_color=LINE, text_color=TEXT, border_width=1, border_color=LINE,
            command=self.swap_colors,
        ).pack(side="left")

        # ขนาด
        self.section("ขนาด")
        self.size_s = self.slider_row("ขนาดภาพ", 200, 2000, 36, 800, lambda v: f"{int(v)} px")
        self.border_s = self.slider_row("ขอบรอบ QR", 0, 10, 10, 4, lambda v: f"{int(v)} ช่อง")

        # โลโก้
        self.section("โลโก้ตรงกลาง")
        lrow = ctk.CTkFrame(self.sb, fg_color="transparent")
        lrow.pack(fill="x", padx=18, pady=(4, 0))
        ctk.CTkButton(
            lrow, text="เลือกรูปโลโก้…", height=34, corner_radius=10, font=self.F(13),
            fg_color=ACCENT_SOFT, hover_color="#99F6E4", text_color=ACCENT,
            command=self.load_logo,
        ).pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.clear_btn = ctk.CTkButton(
            lrow, text="ลบ", width=60, height=34, corner_radius=10, font=self.F(13),
            fg_color=STAGE, hover_color=LINE, text_color=MUTED, border_width=1, border_color=LINE,
            command=self.clear_logo, state="disabled",
        )
        self.clear_btn.pack(side="left")
        self.logo_lbl = ctk.CTkLabel(self.sb, text="ยังไม่ได้เลือกรูป", font=self.F(12), text_color=MUTED, anchor="w")
        self.logo_lbl.pack(fill="x", padx=18, pady=(4, 0))

        self.ratio_s = self.slider_row("ขนาดโลโก้", 10, 30, 20, 22, lambda v: f"{int(v)}%")
        self.round_sw = ctk.CTkSwitch(
            self.sb, text="กรอบโลโก้มุมโค้ง", font=self.F(13), text_color=TEXT,
            progress_color=ACCENT, command=self.schedule,
        )
        self.round_sw.select()
        self.round_sw.pack(anchor="w", padx=18, pady=(8, 18))

    def _build_preview(self):
        pv = ctk.CTkFrame(self, fg_color=CARD, corner_radius=18)
        pv.grid(row=0, column=1, sticky="nsew", padx=(9, 18), pady=18)
        pv.grid_columnconfigure(0, weight=1)
        pv.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(pv, text="ตัวอย่าง", font=self.F(16, True), text_color=TEXT).grid(
            row=0, column=0, sticky="w", padx=24, pady=(20, 0))

        stage = ctk.CTkFrame(pv, fg_color=STAGE, corner_radius=14, border_width=1, border_color=LINE)
        stage.grid(row=1, column=0, sticky="nsew", padx=24, pady=14)
        # ใช้ภาพโปร่งใสแทน image=None (CustomTkinter มีบั๊กเมื่อล้างภาพออกจาก label)
        blank = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
        self._blank = ctk.CTkImage(light_image=blank, dark_image=blank, size=(1, 1))
        self.preview_lbl = ctk.CTkLabel(stage, text="", image=self._blank, font=self.F(14), text_color=MUTED)
        self.preview_lbl.place(relx=0.5, rely=0.5, anchor="center")

        self.info = ctk.CTkLabel(pv, text="", font=self.F(12), text_color=MUTED)
        self.info.grid(row=2, column=0, padx=24)
        self.warn = ctk.CTkLabel(pv, text="", font=self.F(12), text_color=WARN, wraplength=520)
        self.warn.grid(row=3, column=0, padx=24, pady=(2, 0))

        self.save_btn = ctk.CTkButton(
            pv, text="บันทึกรูป QR Code", height=46, corner_radius=12, font=self.F(15, True),
            fg_color=ACCENT, hover_color=ACCENT_HOVER, command=self.save,
        )
        self.save_btn.grid(row=4, column=0, sticky="ew", padx=24, pady=(12, 6))
        self.status = ctk.CTkLabel(pv, text="", font=self.F(12), text_color=OK)
        self.status.grid(row=5, column=0, padx=24, pady=(0, 14))

    # ----- actions -----
    def schedule(self, *_):
        if self._job:
            self.after_cancel(self._job)
        self._job = self.after(150, self.render)

    def set_color(self, which, value):
        sw, var = self.color_widgets[which]
        try:
            r, g, b = ImageColor.getrgb(value.strip())[:3]
        except ValueError:
            var.set(getattr(self, which))
            return
        hexv = f"#{r:02X}{g:02X}{b:02X}"
        setattr(self, which, hexv)
        var.set(hexv)
        sw.configure(fg_color=hexv, hover_color=hexv)
        self.schedule()

    def pick_color(self, which):
        res = colorchooser.askcolor(color=getattr(self, which), title="เลือกสี")
        if res and res[1]:
            self.set_color(which, res[1])

    def apply_preset(self, f, b):
        self.set_color("fill", f)
        self.set_color("back", b)

    def swap_colors(self):
        f, b = self.fill, self.back
        self.apply_preset(b, f)

    def load_logo(self):
        path = filedialog.askopenfilename(
            title="เลือกรูปโลโก้",
            filetypes=[("รูปภาพ", "*.png *.jpg *.jpeg *.webp *.bmp *.gif *.ico"), ("ทุกไฟล์", "*.*")],
        )
        if not path:
            return
        try:
            self.set_logo(Image.open(path).convert("RGBA"), os.path.basename(path))
        except Exception as e:
            messagebox.showerror("เปิดรูปไม่ได้", str(e))

    def set_logo(self, img, name):
        self.logo = img
        self.logo_lbl.configure(text=f"✓ {name}", text_color=ACCENT)
        self.clear_btn.configure(state="normal")
        self.schedule()

    def clear_logo(self):
        self.logo = None
        self.logo_lbl.configure(text="ยังไม่ได้เลือกรูป", text_color=MUTED)
        self.clear_btn.configure(state="disabled")
        self.schedule()

    def render(self):
        self._job = None
        data = self.text.get("1.0", "end").strip()
        warnings = []

        if not data:
            self.current = None
            self.preview_lbl.configure(image=self._blank, text="พิมพ์ข้อความหรือลิงก์ทางด้านซ้าย\nเพื่อเริ่มสร้าง QR Code")
            self.info.configure(text="")
            self.warn.configure(text="")
            self.save_btn.configure(state="disabled")
            return

        size = int(self.size_s.get())
        ratio = self.ratio_s.get() / 100
        try:
            img, version = build_qr(
                data, self.fill, self.back, size, int(self.border_s.get()),
                logo=self.logo, logo_ratio=ratio, rounded=bool(self.round_sw.get()),
            )
        except (DataOverflowError, ValueError):  # บางเวอร์ชันของ qrcode โยน ValueError เมื่อข้อมูลยาวเกิน
            self.current = None
            self.preview_lbl.configure(image=self._blank, text="ข้อความยาวเกินกว่าที่ QR Code จะรองรับได้")
            self.info.configure(text="")
            self.warn.configure(text="")
            self.save_btn.configure(state="disabled")
            return

        self.current = img
        prev = img.resize((PREVIEW, PREVIEW), Image.LANCZOS)
        self._ctkimg = ctk.CTkImage(light_image=prev, dark_image=prev, size=(PREVIEW, PREVIEW))
        self.preview_lbl.configure(image=self._ctkimg, text="")
        self.save_btn.configure(state="normal")

        level = "H (กู้ข้อมูลได้ ~30%)" if self.logo is not None else "M (กู้ข้อมูลได้ ~15%)"
        self.info.configure(text=f"{size} × {size} px   ·   QR เวอร์ชัน {version}   ·   ระดับแก้ไขข้อผิดพลาด {level}")

        if contrast(self.fill, self.back) < 3:
            warnings.append("สีจุดกับสีพื้นหลังต่างกันน้อยเกินไป อาจสแกนไม่ติด")
        elif luminance(self.fill) > luminance(self.back):
            warnings.append("เป็น QR สีกลับด้าน (จุดสว่างบนพื้นเข้ม) บางแอปอาจสแกนไม่ได้")
        if self.logo is not None and ratio > 0.25:
            warnings.append("โลโก้ใหญ่เกิน 25% อาจสแกนไม่ติด ควรลองสแกนก่อนใช้งานจริง")
        self.warn.configure(text="⚠ " + "  ·  ".join(warnings) if warnings else "")

    def save(self):
        if self.current is None:
            return
        path = filedialog.asksaveasfilename(
            title="บันทึก QR Code", defaultextension=".png", initialfile="qrcode.png",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg *.jpeg")],
        )
        if not path:
            return
        try:
            if path.lower().endswith((".jpg", ".jpeg")):
                self.current.convert("RGB").save(path, quality=95)
            else:
                self.current.save(path)
        except Exception as e:
            messagebox.showerror("บันทึกไม่สำเร็จ", str(e))
            return
        self.status.configure(text=f"✓ บันทึกแล้ว: {os.path.basename(path)}")
        if self._status_job:
            self.after_cancel(self._status_job)
        self._status_job = self.after(5000, lambda: self.status.configure(text=""))


if __name__ == "__main__":
    App().mainloop()
