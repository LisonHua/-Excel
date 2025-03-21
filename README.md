# Excel合并工具

这是一个用于合并多个Excel文件指定字段的工具，提供桌面版和网页版两种使用方式。

## 功能特点

- 支持选择多个Excel文件
- 可以选择每个文件中的特定工作表
- 支持指定要合并的字段
- 自动处理大数字（超过7位）转换为字符串
- 添加来源文件信息
- 支持全角和半角逗号作为字段分隔符

## 在线使用

访问 [Excel合并工具](https://your-username.github.io/excel-merger/) 即可在线使用。

## 本地安装

### 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

### 桌面版

1. 运行程序：
```bash
python excel_merger.py
```

2. 点击"选择文件"按钮选择要合并的Excel文件
3. 在"指定字段"输入框中输入要合并的字段名，用逗号分隔
4. 选择要合并的工作表
5. 点击"合并"按钮
6. 选择保存位置和文件名

### 网页版

1. 运行网页服务器：
```bash
python web_excel_merger.py
```

2. 在浏览器中访问 `http://localhost:5000`
3. 点击"选择文件"按钮选择要合并的Excel文件
4. 在"指定字段"输入框中输入要合并的字段名，用逗号分隔
5. 选择要合并的工作表
6. 点击"合并文件"按钮
7. 合并完成后会自动下载合并后的文件

## 部署说明

### GitHub Pages部署

1. Fork 本仓库到您的GitHub账号
2. 在仓库设置中启用GitHub Pages：
   - 进入仓库的 Settings 标签
   - 找到 Pages 选项
   - 在 Source 中选择 "GitHub Actions"
3. 推送代码到main分支，GitHub Actions会自动部署

### 本地部署

1. 安装系统依赖：
```bash
sudo apt update
sudo apt install python3-pip nginx
```

2. 克隆代码到服务器：
```bash
git clone <repository-url>
cd excel-merger
```

3. 配置Nginx：
```bash
sudo cp nginx.conf /etc/nginx/sites-available/excel-merger
sudo ln -s /etc/nginx/sites-available/excel-merger /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

4. 设置环境变量：
```bash
cp .env.example .env
# 编辑.env文件，设置必要的环境变量
```

5. 运行部署脚本：
```bash
chmod +x deploy.sh
./deploy.sh
```

## 注意事项

- 所有Excel文件必须包含指定的字段
- 字段名不区分大小写
- 合并后的文件会包含一个"来源文件"列，显示数据来源
- 网页版支持同时上传多个文件
- 网页版有文件大小限制（16MB）
- 生产环境部署时请确保修改默认的密钥
- 建议使用HTTPS协议保护数据传输安全 