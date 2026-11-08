import tkinter as tk
from tkinter import messagebox, filedialog
from PIL import Image, ImageTk
import subprocess
import io
import os

class CropTool:
    def __init__(self, root):
        self.root = root
        self.root.title("Bot Coords & Template Capture Tool (Color Picker)")
        self.root.geometry("1200x950")

        self.start_x = None
        self.start_y = None
        self.rect = None
        self.original_image = None 
        self.pil_image = None      
        self.tk_image = None
        self.zoom_factor = 1.0     
        
        self.current_x1 = 0
        self.current_y1 = 0
        self.current_x2 = 0
        self.current_y2 = 0
        
        self.default_save_dir = os.path.join(os.getcwd(), "Templates", "Smart_Auto_train")

        # --- THANH CÔNG CỤ TRÊN CÙNG ---
        top_frame = tk.Frame(root)
        top_frame.pack(pady=5, fill=tk.X)

        tk.Label(top_frame, text="ADB Device:", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
        self.entry_adb = tk.Entry(top_frame, width=15, font=("Consolas", 10))
        self.entry_adb.insert(0, "127.0.0.1:21503") 
        self.entry_adb.pack(side=tk.LEFT, padx=5)

        btn_capture = tk.Button(top_frame, text="📸 Chụp Màn Hình", command=self.capture_screen, bg="#FF9800", fg="white", font=("Arial", 10, "bold"))
        btn_capture.pack(side=tk.LEFT, padx=5)

        btn_zoom_in = tk.Button(top_frame, text="➕ Phóng To", command=lambda: self.zoom_image(1.2), bg="#9C27B0", fg="white")
        btn_zoom_in.pack(side=tk.LEFT, padx=2)
        btn_zoom_out = tk.Button(top_frame, text="➖ Thu Nhỏ", command=lambda: self.zoom_image(0.8), bg="#9C27B0", fg="white")
        btn_zoom_out.pack(side=tk.LEFT, padx=2)

        btn_save_crop = tk.Button(top_frame, text="💾 Lưu Ảnh Mẫu", command=self.save_crop, bg="#2196F3", fg="white", font=("Arial", 10, "bold"))
        btn_save_crop.pack(side=tk.LEFT, padx=10)

        btn_copy_xyxy = tk.Button(top_frame, text="📋 Copy XYXY", command=self.copy_xyxy, bg="#4CAF50", fg="white", font=("Arial", 10, "bold"))
        btn_copy_xyxy.pack(side=tk.LEFT, padx=2)

        btn_copy_xywh = tk.Button(top_frame, text="📋 Copy X Y W H", command=self.copy_xywh, bg="#4CAF50", fg="white", font=("Arial", 10, "bold"))
        btn_copy_xywh.pack(side=tk.LEFT, padx=2)

        # --- KHUNG CẤU HÌNH CLICK CAPTURE ---
        capture_frame = tk.LabelFrame(root, text="Click Capture (Cắt Template tự động)", font=("Arial", 10, "bold"), fg="blue")
        capture_frame.pack(pady=5, fill=tk.X, padx=10)

        tk.Label(capture_frame, text="Name:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.entry_name = tk.Entry(capture_frame, width=15)
        self.entry_name.insert(0, "wizard")
        self.entry_name.grid(row=0, column=1, padx=5, pady=5)

        tk.Label(capture_frame, text="Index:").grid(row=0, column=2, padx=5, pady=5, sticky="e")
        self.entry_index = tk.Entry(capture_frame, width=8)
        self.entry_index.insert(0, "100")
        self.entry_index.grid(row=0, column=3, padx=5, pady=5)

        tk.Label(capture_frame, text="Size (px):").grid(row=0, column=4, padx=5, pady=5, sticky="e")
        self.entry_size = tk.Entry(capture_frame, width=8)
        self.entry_size.insert(0, "40")
        self.entry_size.grid(row=0, column=5, padx=5, pady=5)

        self.click_mode_var = tk.BooleanVar(value=False)
        self.chk_click_mode = tk.Checkbutton(capture_frame, text="Bật Click Capture", variable=self.click_mode_var, font=("Arial", 10, "bold"), fg="red")
        self.chk_click_mode.grid(row=0, column=6, padx=15, pady=5)

        # --- HIỂN THỊ TỌA ĐỘ & MÀU SẮC & PREVIEW ---
        info_frame = tk.Frame(root)
        info_frame.pack(fill=tk.X, padx=10, pady=5)

        self.lbl_coords = tk.Label(info_frame, text="Bấm 'Chụp Màn Hình' để bắt đầu...\n(Chuột phải để hút màu Hex)", font=("Consolas", 11), fg="red", justify=tk.LEFT)
        self.lbl_coords.pack(side=tk.LEFT, anchor="w")

        # Label hiển thị màu vừa hút
        self.lbl_color_info = tk.Label(info_frame, text="Màu: Chưa chọn", font=("Consolas", 12, "bold"), bg="white", fg="black", width=25)
        self.lbl_color_info.pack(side=tk.LEFT, padx=20)

        self.lbl_preview = tk.Label(info_frame, text="[Preview Ảnh Cắt]", bg="gray")
        self.lbl_preview.pack(side=tk.RIGHT, padx=10)

        # --- KHUNG CHỨA CANVAS VÀ THANH CUỘN ---
        canvas_frame = tk.Frame(root)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.canvas = tk.Canvas(canvas_frame, cursor="cross", bg="gray")
        hbar = tk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        vbar = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=hbar.set, yscrollcommand=vbar.set)
        
        hbar.pack(side=tk.BOTTOM, fill=tk.X)
        vbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Bind sự kiện chuột
        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_move_press)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)
        self.canvas.bind("<MouseWheel>", self.on_mousewheel)
        self.canvas.bind("<Button-3>", self.pick_color) # Chuột phải để hút màu

    def capture_screen(self):
        device_id = self.entry_adb.get().strip()
        if not device_id:
            messagebox.showerror("Lỗi", "Vui lòng nhập địa chỉ ADB!")
            return

        self.lbl_coords.config(text="Đang chụp màn hình...", fg="blue")
        self.root.update()

        try:
            # ========================================================
            # TỰ ĐỘNG TÌM ĐƯỜNG DẪN ADB.EXE (CẬP NHẬT CHO src/adb/adb.exe)
            # ========================================================
            current_dir = os.path.dirname(os.path.abspath(__file__))
            
            possible_adb_paths = [
                os.path.join(current_dir, "adb", "adb.exe"),          # Đường dẫn mới của bạn (src/adb/adb.exe)
                os.path.join(current_dir, "adb.exe"),                 # Nếu để chung thư mục src
                os.path.join(current_dir, "COCbot", "emulator", "bin", "adb.exe"), # Cấu trúc cũ
                "adb" # Fallback
            ]
            
            adb_bin = None
            for path in possible_adb_paths:
                if path == "adb" or os.path.exists(path):
                    adb_bin = path
                    break
            
            if not adb_bin:
                from tkinter import filedialog
                adb_bin = filedialog.askopenfilename(
                    title="Không tìm thấy adb.exe. Vui lòng trỏ đến file adb.exe",
                    filetypes=[("ADB Executable", "adb.exe")]
                )
                if not adb_bin: return

            print(f"✅ Đang dùng ADB tại: {adb_bin}")
            # ========================================================

            command = [adb_bin, "-s", device_id, "exec-out", "screencap", "-p"]
            creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            result = subprocess.run(command, capture_output=True, creationflags=creationflags)
            
            if result.returncode != 0:
                messagebox.showerror("Lỗi ADB", "Không thể chụp màn hình. Kiểm tra lại kết nối giả lập.")
                return

            self.original_image = Image.open(io.BytesIO(result.stdout)).convert("RGB")
            self.zoom_factor = 1.0 
            self.update_canvas_image()
            self.lbl_coords.config(text="Chụp thành công! Kéo chuột trái để cắt, chuột phải để hút màu.", fg="green")
            self.lbl_preview.config(image="", text="[Chưa chọn vùng]")

        except Exception as e:
            messagebox.showerror("Lỗi", f"Lỗi hệ thống: {str(e)}")

    def update_canvas_image(self):
        if not self.original_image:
            return
        new_w = int(self.original_image.width * self.zoom_factor)
        new_h = int(self.original_image.height * self.zoom_factor)
        
        self.pil_image = self.original_image.resize((new_w, new_h), Image.Resampling.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(self.pil_image)
        
        self.canvas.delete("all")
        self.canvas.config(scrollregion=(0, 0, new_w, new_h))
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_image)
        
        if self.current_x2 > 0:
            draw_x1 = self.current_x1 * self.zoom_factor
            draw_y1 = self.current_y1 * self.zoom_factor
            draw_x2 = self.current_x2 * self.zoom_factor
            draw_y2 = self.current_y2 * self.zoom_factor
            self.canvas.create_rectangle(draw_x1, draw_y1, draw_x2, draw_y2, outline='red', width=2)

    def zoom_image(self, factor):
        if not self.original_image: return
        self.zoom_factor = max(0.1, min(5.0, self.zoom_factor * factor))
        self.update_canvas_image()

    def on_mousewheel(self, event):
        self.zoom_image(1.1 if event.delta > 0 else 0.9)

    # ============================================================
    # TÍNH NĂNG MỚI: HÚT MÀU (COLOR PICKER)
    # ============================================================
    def pick_color(self, event):
        if not self.original_image:
            return
            
        # Lấy tọa độ thực trên ảnh gốc
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        real_x = int(cx / self.zoom_factor)
        real_y = int(cy / self.zoom_factor)

        # Kiểm tra giới hạn ảnh
        if 0 <= real_x < self.original_image.width and 0 <= real_y < self.original_image.height:
            r, g, b = self.original_image.getpixel((real_x, real_y))
            hex_color = f"0x{r:02X}{g:02X}{b:02X}"
            
            # Copy vào clipboard
            self.root.clipboard_clear()
            self.root.clipboard_append(hex_color)
            
            # Cập nhật giao diện
            self.lbl_color_info.config(text=f"Màu: {hex_color} (Đã Copy)", bg=f"#{r:02X}{g:02X}{b:02X}", 
                                       fg="white" if (r+g+b) < 400 else "black")
            
            # Vẽ một dấu chấm nhỏ tại điểm vừa hút để dễ nhìn
            self.canvas.delete("color_pick")
            draw_x = real_x * self.zoom_factor
            draw_y = real_y * self.zoom_factor
            self.canvas.create_oval(draw_x-3, draw_y-3, draw_x+3, draw_y+3, fill="red", outline="white", tags="color_pick")

    # ============================================================

    def on_button_press(self, event):
        if not self.pil_image: return
        
        self.canvas.delete("captured_box")

        if self.click_mode_var.get():
            self.execute_click_capture(event.x, event.y)
            return 

        self.start_x = self.canvas.canvasx(event.x)
        self.start_y = self.canvas.canvasy(event.y)
        
        if self.rect:
            self.canvas.delete(self.rect)
        self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline='red', width=2)

    def execute_click_capture(self, click_x, click_y):
        try:
            size = int(self.entry_size.get())
            real_x = int(self.canvas.canvasx(click_x) / self.zoom_factor)
            real_y = int(self.canvas.canvasy(click_y) / self.zoom_factor)
            
            half_size = size // 2
            x1 = real_x - half_size
            y1 = real_y - half_size
            x2 = x1 + size
            y2 = y1 + size

            if x1 < 0: x1, x2 = 0, size
            if y1 < 0: y1, y2 = 0, size
            if x2 > self.original_image.width: x2, x1 = self.original_image.width, self.original_image.width - size
            if y2 > self.original_image.height: y2, y1 = self.original_image.height, self.original_image.height - size

            self.current_x1, self.current_y1 = max(0, x1), max(0, y1)
            self.current_x2, self.current_y2 = min(self.original_image.width, x2), min(self.original_image.height, y2)

            self.draw_selection_box()
            self.update_coords_label()
            self.update_preview()
            
            name = self.entry_name.get().strip()
            index = self.entry_index.get().strip()
            self.lbl_coords.config(text=f"Vùng chọn: {size}x{size} | Sẵn sàng lưu: {name}_{index}.png", fg="green")
            
        except ValueError:
            messagebox.showerror("Lỗi", "Size phải là số nguyên!")

    def on_move_press(self, event):
        if not self.pil_image or self.click_mode_var.get(): return
        cur_x = self.canvas.canvasx(event.x)
        cur_y = self.canvas.canvasy(event.y)
        self.canvas.coords(self.rect, self.start_x, self.start_y, cur_x, cur_y)

    def on_button_release(self, event):
        if not self.pil_image or self.click_mode_var.get(): return
        end_x = self.canvas.canvasx(event.x)
        end_y = self.canvas.canvasy(event.y)
        
        img_x1 = int(min(self.start_x, end_x) / self.zoom_factor)
        img_y1 = int(min(self.start_y, end_y) / self.zoom_factor)
        img_x2 = int(max(self.start_x, end_x) / self.zoom_factor) + 1
        img_y2 = int(max(self.start_y, end_y) / self.zoom_factor) + 1

        self.current_x1, self.current_y1 = max(0, img_x1), max(0, img_y1)
        self.current_x2, self.current_y2 = min(self.original_image.width, img_x2), min(self.original_image.height, img_y2)

        self.update_coords_label()
        self.update_preview()

    def draw_selection_box(self):
        self.canvas.delete("captured_box")
        draw_x1 = self.current_x1 * self.zoom_factor
        draw_y1 = self.current_y1 * self.zoom_factor
        draw_x2 = self.current_x2 * self.zoom_factor
        draw_y2 = self.current_y2 * self.zoom_factor
        self.canvas.create_rectangle(draw_x1, draw_y1, draw_x2, draw_y2, outline='red', width=2, tags="captured_box")

    def update_coords_label(self):
        w = self.current_x2 - self.current_x1
        h = self.current_y2 - self.current_y1
        text = f"XYXY: ({self.current_x1}, {self.current_y1}, {self.current_x2}, {self.current_y2})\n"
        text += f"X={self.current_x1}, Y={self.current_y1}, W={w}, H={h}"
        self.lbl_coords.config(text=text, fg="red")

    def update_preview(self):
        if not self.original_image or self.current_x2 <= self.current_x1:
            return
        cropped = self.original_image.crop((self.current_x1, self.current_y1, self.current_x2, self.current_y2))
        cw, ch = cropped.size
        if cw > 100 or ch > 100:
            scale = min(100/cw, 100/ch)
            cropped = cropped.resize((int(cw*scale), int(ch*scale)), Image.Resampling.LANCZOS)
        self.preview_tk = ImageTk.PhotoImage(cropped)
        self.lbl_preview.config(image=self.preview_tk, text="")

    def copy_xyxy(self):
        if self.current_x2 == 0 or self.current_x2 <= self.current_x1: 
            messagebox.showwarning("Cảnh báo", "Chưa chọn vùng nào hợp lệ!")
            return
        coord_str = f"({self.current_x1}, {self.current_y1}, {self.current_x2}, {self.current_y2})"
        self.root.clipboard_clear()
        self.root.clipboard_append(coord_str)
        self.lbl_coords.config(text=f"📋 Đã Copy XYXY: {coord_str}", fg="green")

    def copy_xywh(self):
        if self.current_x2 == 0 or self.current_x2 <= self.current_x1: 
            messagebox.showwarning("Cảnh báo", "Chưa chọn vùng nào hợp lệ!")
            return
        w = self.current_x2 - self.current_x1
        h = self.current_y2 - self.current_y1
        coord_str = f"{self.current_x1}, {self.current_y1}, {w}, {h}"
        self.root.clipboard_clear()
        self.root.clipboard_append(coord_str)
        self.lbl_coords.config(text=f"📋 Đã Copy X, Y, W, H: {coord_str}", fg="green")

    def save_crop(self):
        if not self.original_image:
            messagebox.showerror("Lỗi", "Chưa có ảnh! Hãy chụp màn hình trước.")
            return
        w = self.current_x2 - self.current_x1
        h = self.current_y2 - self.current_y1
        if w <= 0 or h <= 0:
            messagebox.showerror("Lỗi", "Vùng chọn không hợp lệ!")
            return

        cropped = self.original_image.crop((self.current_x1, self.current_y1, self.current_x2, self.current_y2))
        name = self.entry_name.get().strip() or "template"
        try: index = int(self.entry_index.get())
        except ValueError: index = 0
            
        save_path = filedialog.asksaveasfilename(
            defaultextension=".png", 
            filetypes=[("PNG files", "*.png")], 
            title="Chọn nơi lưu ảnh Template",
            initialdir=self.default_save_dir,
            initialfile=f"{name}_{index}.png"
        )
        
        if save_path:
            cropped.save(save_path)
            messagebox.showinfo("Thành công", f"Đã lưu ảnh tại:\n{save_path}")
            self.entry_index.delete(0, tk.END)
            self.entry_index.insert(0, str(index + 1))
            self.lbl_coords.config(text=f"✅ Đã lưu file: {os.path.basename(save_path)}", fg="green")

if __name__ == "__main__":
    root = tk.Tk()
    app = CropTool(root)
    root.mainloop()