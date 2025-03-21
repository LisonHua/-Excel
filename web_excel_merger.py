from flask import Flask, render_template, request, send_file, jsonify
from werkzeug.utils import secure_filename
import pandas as pd
import os
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# 确保上传文件夹存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {'xlsx', 'xls'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    if 'files[]' not in request.files:
        return jsonify({'error': '没有选择文件'}), 400
    
    files = request.files.getlist('files[]')
    if not files or files[0].filename == '':
        return jsonify({'error': '没有选择文件'}), 400

    file_info = []
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # 获取Excel文件的工作表信息
            excel_file = pd.ExcelFile(filepath)
            sheet_names = excel_file.sheet_names
            columns = {}
            for sheet in sheet_names:
                df = pd.read_excel(filepath, sheet_name=sheet)
                columns[sheet] = df.columns.tolist()
            
            file_info.append({
                'filename': filename,
                'sheets': sheet_names,
                'columns': columns
            })
    
    return jsonify(file_info)

@app.route('/merge', methods=['POST'])
def merge_files():
    try:
        data = request.json
        files = data.get('files', [])
        sheets = data.get('sheets', {})
        fields = data.get('fields', [])
        
        if not files or not sheets or not fields:
            return jsonify({'error': '缺少必要参数'}), 400

        combined_df = pd.DataFrame()
        
        for file in files:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file))
            for sheet in sheets.get(file, []):
                df = pd.read_excel(filepath, sheet_name=sheet)
                df.columns = df.columns.str.lower()
                
                if set(fields).issubset(df.columns):
                    selected_df = df[fields]
                    # 将数字位数大于7位的列转换为字符串
                    for col in selected_df.select_dtypes(include=['number']).columns:
                        selected_df[col] = selected_df[col].apply(
                            lambda x: str(int(x)) if pd.notna(x) and len(str(int(x))) > 7 else x)
                    selected_df['来源文件'] = file
                    combined_df = pd.concat([combined_df, selected_df], ignore_index=True)
                else:
                    return jsonify({'error': f'文件 {file} 的工作表 {sheet} 不包含所有指定字段'}), 400

        # 生成输出文件名
        output_filename = f'merged_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)
        
        # 保存合并后的文件
        combined_df.to_excel(output_path, index=False, engine='openpyxl')
        
        return jsonify({
            'success': True,
            'filename': output_filename
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download/<filename>')
def download_file(filename):
    try:
        return send_file(
            os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(filename)),
            as_attachment=True
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 404

if __name__ == '__main__':
    app.run(debug=True) 