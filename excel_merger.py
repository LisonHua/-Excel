import tkinter as tk
from tkinter import filedialog, messagebox
import pandas as pd
import os


class ExcelMergerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Excel Merger")

        self.files = []
        self.sheets = {}

        self.file_button = tk.Button(root, text="选择文件", command=self.select_files)
        self.file_button.pack(pady=5)

        self.canvas = tk.Canvas(root)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.scrollbar = tk.Scrollbar(root, orient="vertical", command=self.canvas.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill="y")

        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.sheet_frame = tk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.sheet_frame, anchor='nw')

        self.sheet_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        self.field_label = tk.Label(root, text="指定字段 (用逗号分隔):")
        self.field_label.pack(pady=5)

        self.field_entry = tk.Entry(root, width=50)
        self.field_entry.pack(pady=5)

        self.merge_button = tk.Button(root, text="合并", command=self.merge_files)
        self.merge_button.pack(pady=20)

    def select_files(self):
        self.files = filedialog.askopenfilenames(filetypes=[("Excel files", "*.xlsx *.xls")])
        if not self.files:
            return

        self.sheets.clear()
        for widget in self.sheet_frame.winfo_children():
            widget.destroy()

        for file in self.files:
            file_label = tk.Label(self.sheet_frame, text=os.path.basename(file), font=('Arial', 12, 'bold'))
            file_label.pack(anchor='w')

            sheet_names = pd.ExcelFile(file).sheet_names
            sheet_vars = []
            for sheet in sheet_names:
                var = tk.BooleanVar()
                var.trace_add('write',
                              lambda name, index, mode, var=var, sheet=sheet: self.update_checkboxes(sheet, var))
                chk = tk.Checkbutton(self.sheet_frame, text=sheet, variable=var)
                chk.pack(anchor='w')
                sheet_vars.append((sheet, var))
            self.sheets[file] = sheet_vars

    def update_checkboxes(self, sheet_name, var):
        if var.get():
            for file, sheet_list in self.sheets.items():
                for sheet, sheet_var in sheet_list:
                    if sheet == sheet_name and not sheet_var.get():
                        sheet_var.set(True)

    def merge_files(self):
        specified_fields = self.field_entry.get().strip()
        if not specified_fields:
            messagebox.showerror("错误", "请填写指定字段")
            return

        # 处理全角和半角逗号，并转换为小写
        fields = [field.strip().lower() for field in specified_fields.replace("，", ",").split(",")]
        combined_df = pd.DataFrame()

        for file, sheet_list in self.sheets.items():
            for sheet, var in sheet_list:
                if var.get():
                    df = pd.read_excel(file, sheet_name=sheet)
                    df.columns = df.columns.str.lower()
                    print(f"文件: {file}, 工作表: {sheet}, 列标题: {df.columns.tolist()}")
                    if set(fields).issubset(df.columns):
                        selected_df = df[fields]
                        # 将数字位数大于7位的列转换为字符串
                        for col in selected_df.select_dtypes(include=['number']).columns:
                            selected_df[col] = selected_df[col].apply(
                                lambda x: str(int(x)) if pd.notna(x) and len(str(int(x))) > 7 else x)
                        selected_df['来源文件'] = os.path.basename(file)
                        combined_df = pd.concat([combined_df, selected_df], ignore_index=True)
                    else:
                        messagebox.showerror("错误", f"{file} 中的工作表 {sheet} 不包含所有指定字段")
                        return

        save_path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel files", "*.xlsx *.xls")])
        if save_path:
            combined_df.to_excel(save_path, index=False, engine='openpyxl')
            messagebox.showinfo("成功", "文件合并完成")


if __name__ == "__main__":
    root = tk.Tk()
    app = ExcelMergerApp(root)
    root.mainloop() 