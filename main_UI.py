import customtkinter as ctk
from tkinter import filedialog
import jmcomic
import threading
import os
import tempfile
import sys
import traceback

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class JmcomicApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("JMComic 下载器")
        self.geometry("650x550") 
        self.minsize(600, 450) 

        if getattr(sys, 'frozen', False):
            root_dir = os.path.dirname(os.path.realpath(sys.executable))
        else:
            root_dir = os.path.dirname(os.path.realpath(__file__))
            
        self.save_path = ctk.StringVar(value=root_dir)
        self.is_zip_enabled = ctk.BooleanVar(value=False) 
        self.image_format = ctk.StringVar(value="原图默认") 

        self.title_label = ctk.CTkLabel(self, text="JMComic 快捷下载工具", font=("Arial", 20, "bold"))
        self.title_label.pack(pady=20)

        self.path_frame = ctk.CTkFrame(self)
        self.path_frame.pack(pady=10, padx=20, fill="x")
        ctk.CTkLabel(self.path_frame, text="下载至:").pack(side="left", padx=10)
        self.path_display = ctk.CTkLabel(self.path_frame, textvariable=self.save_path, fg_color="gray25", corner_radius=5, anchor="w")
        self.path_display.pack(side="left", padx=10, expand=True, fill="x")
        ctk.CTkButton(self.path_frame, text="更改目录", width=80, command=self.select_folder).pack(side="left", padx=10)

        self.option_frame = ctk.CTkFrame(self)
        self.option_frame.pack(pady=10, padx=20, fill="x")
        self.zip_checkbox = ctk.CTkCheckBox(self.option_frame, text="完成后打包成 ZIP", variable=self.is_zip_enabled)
        self.zip_checkbox.pack(side="left", padx=(20, 10))
        ctk.CTkLabel(self.option_frame, text="| 格式:").pack(side="left", padx=5)
        self.format_menu = ctk.CTkOptionMenu(self.option_frame, values=["原图默认", ".jpg", ".webp", ".png"], variable=self.image_format, width=110)
        self.format_menu.pack(side="left", padx=5)

        self.input_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.input_frame.pack(pady=15)
        self.id_entry = ctk.CTkEntry(self.input_frame, placeholder_text="输入本子 ID", width=220)
        self.id_entry.pack(side="left", padx=10)
        self.download_btn = ctk.CTkButton(self.input_frame, text="准备起飞", command=self.start_download)
        self.download_btn.pack(side="left")

        self.log_textbox = ctk.CTkTextbox(self)
        self.log_textbox.pack(pady=(10, 20), padx=20, expand=True, fill="both")
        self.log_textbox.configure(state="disabled")

    def log(self, message):
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", f"{message}\n")
        self.log_textbox.see("end") 
        self.log_textbox.configure(state="disabled")

    def select_folder(self):
        current = self.save_path.get()
        initial = current if os.path.exists(current) else os.path.join(os.path.expanduser("~"), "Desktop")
        selected = filedialog.askdirectory(initialdir=initial, title="请选择下载存放文件夹")
        if selected:
            norm_path = os.path.normpath(selected)
            self.save_path.set(norm_path)
            self.log(f"[系统] 路径已更新为: {norm_path}")

    def start_download(self):
        aid = self.id_entry.get().strip()
        if not aid:
            self.log("[错误] 请先填写车号")
            return
        
        cfg = {
            "path": self.save_path.get(),
            "zip": self.is_zip_enabled.get(),
            "fmt": self.image_format.get()
        }
        
        self.download_btn.configure(state="disabled", text="正在下载...")
        threading.Thread(target=self._run_worker, args=(aid, cfg), daemon=True).start()

    def _run_worker(self, aid, cfg):
        tmp_path = None
        original_cwd = os.getcwd() 
        
        try:
            target_dir = os.path.abspath(cfg['path'])
            os.makedirs(target_dir, exist_ok=True) 
            os.chdir(target_dir)
            
            yaml_safe_path = target_dir.replace('\\', '/')
            self.log(f"[系统] 目录切换至: {target_dir}")
            
            yml_lines = [
                "dir_rule:",
                f"  base_dir: '{yaml_safe_path}'"
            ]

            if cfg['fmt'] != "原图默认":
                yml_lines.extend([
                    "download:",
                    "  image:",
                    f"    suffix: '{cfg['fmt']}'"
                ])

            if cfg['zip']:
                yml_lines.extend([
                    "plugins:",
                    "  after_album:",
                    "    - plugin: zip",
                    "      kwargs:",
                    "        level: album",
                    f"        filename_rule: '{aid}'",
                    "        delete_original_file: true"
                ])

            yml_content = "\n".join(yml_lines)

            fd, tmp_path = tempfile.mkstemp(suffix=".yml", prefix="jm_cfg_", text=True)
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write(yml_content)

            option = jmcomic.create_option(tmp_path)
            
            self.log(f"[系统] 正在下载: {aid}")
            jmcomic.download_album(aid, option)
            self.log(f"[成功] 任务处理结束，文件已保存至: {target_dir}")

        except Exception as e:
            err_details = traceback.format_exc()
            self.log(f"[失败] 发生异常，详细跟踪日志：\n{err_details}")
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try: os.remove(tmp_path)
                except: pass
            
            # 任务结束后，务必将工作目录恢复原状，防止影响下一次路径选择
            os.chdir(original_cwd)
            self.download_btn.configure(state="normal", text="开始下载")

if __name__ == "__main__":
    app = JmcomicApp()
    app.mainloop()