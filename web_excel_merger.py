from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
import pandas as pd
import os
import random
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {'xlsx', 'xls'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/lottery/upload', methods=['POST'])
def upload_lottery_file():
    if 'file' not in request.files:
        return jsonify({'error': '请先上传Excel文件'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '文件名不能为空'}), 400
    if not allowed_file(file.filename):
        return jsonify({'error': '仅支持 .xlsx 或 .xls 文件'}), 400

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    filename = f"{timestamp}_{secure_filename(file.filename)}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    try:
        df = pd.read_excel(filepath)
    except Exception as error:
        return jsonify({'error': f'读取Excel失败: {error}'}), 400

    if df.empty:
        return jsonify({'error': 'Excel文件为空，请检查内容'}), 400

    columns = [str(column) for column in df.columns]
    return jsonify({
        'filename': filename,
        'columns': columns,
        'preview': df.head(5).fillna('').astype(str).to_dict(orient='records')
    })


@app.route('/lottery/draw', methods=['POST'])
def draw_lottery():
    data = request.json or {}
    filename = data.get('filename')
    column = data.get('column')
    winner_count = data.get('winner_count')

    if not filename or not column:
        return jsonify({'error': '缺少文件或姓名列参数'}), 400

    try:
        winner_count = int(winner_count)
    except (TypeError, ValueError):
        return jsonify({'error': '中奖人数必须是整数'}), 400

    if winner_count <= 0:
        return jsonify({'error': '中奖人数必须大于0'}), 400

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(filename))
    if not os.path.exists(filepath):
        return jsonify({'error': '上传文件不存在，请重新上传'}), 400

    try:
        df = pd.read_excel(filepath)
    except Exception as error:
        return jsonify({'error': f'读取Excel失败: {error}'}), 400

    if column not in df.columns:
        return jsonify({'error': f'未找到姓名列: {column}'}), 400

    names = (
        df[column]
        .dropna()
        .astype(str)
        .map(lambda value: value.strip())
    )
    valid_names = [name for name in names if name]

    if not valid_names:
        return jsonify({'error': '姓名列没有可抽奖的数据'}), 400

    if winner_count > len(valid_names):
        return jsonify({'error': f'中奖人数不能超过总人数（{len(valid_names)}）'}), 400

    winners = random.sample(valid_names, winner_count)

    return jsonify({
        'success': True,
        'total': len(valid_names),
        'winners': winners
    })


if __name__ == '__main__':
    app.run(debug=True)
