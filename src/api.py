"""Flask API 模块"""
from flask import Flask, request, jsonify
from datetime import datetime
from src.storage import StorageService


def create_app(storage_service: StorageService) -> Flask:
    """
    创建 Flask 应用
    
    Args:
        storage_service: 存储服务实例
    
    Returns:
        Flask 应用实例
    """
    app = Flask(__name__)
    
    @app.route('/api/list', methods=['GET'])
    def list_files():
        """
        获取指定日期下所有 file_dir 的 Markdown 文件列表

        Query Parameters:
            date: 日期，格式 YYYY-MM-DD，默认为今天

        Returns:
            JSON 数组，每项：{"date": "YYYY-MM-DD", "file_dir": "bis1", "count": 1, "files": [...]}
        """
        date_str = request.args.get('date')

        # 解析日期
        if date_str:
            try:
                date = datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                return jsonify({
                    'error': '日期格式错误，应为 YYYY-MM-DD'
                }), 400
        else:
            date = datetime.now()

        # 按 file_dir 分组获取文件列表
        grouped = storage_service.get_files_grouped_by_dir(date)
        date_formatted = date.strftime('%Y-%m-%d')

        result = [
            {
                'date': date_formatted,
                'file_dir': item['file_dir'],
                'count': len(item['files']),
                'files': item['files']
            }
            for item in grouped
        ]

        return jsonify(result)
    
    @app.route('/api/content', methods=['GET'])
    def get_content():
        """
        获取指定文件的内容
        
        Query Parameters:
            date: 日期，格式 YYYY-MM-DD，默认为今天
            filename: 文件名
            file_dir: 网站子目录名（来自 config.json 的 file_dir 字段）
        
        Returns:
            JSON: {"date": "YYYY-MM-DD", "file_dir": "bis1", "filename": "xxx.md", "content": "..."}
        """
        date_str = request.args.get('date')
        filename = request.args.get('filename')
        file_dir = request.args.get('file_dir', '')
        
        if not filename:
            return jsonify({
                'error': '缺少 filename 参数'
            }), 400
        
        # 解析日期
        if date_str:
            try:
                date = datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                return jsonify({
                    'error': '日期格式错误，应为 YYYY-MM-DD'
                }), 400
        else:
            date = datetime.now()
        
        # 获取文件内容
        content = storage_service.get_file_content(date, filename, file_dir)
        
        if content is None:
            return jsonify({
                'error': '文件不存在'
            }), 404
        
        return jsonify({
            'date': date.strftime('%Y-%m-%d'),
            'file_dir': file_dir,
            'filename': filename,
            'content': content
        })
    
    @app.route('/api/health', methods=['GET'])
    def health():
        """健康检查接口"""
        return jsonify({
            'status': 'ok',
            'timestamp': datetime.now().isoformat()
        })
    
    return app
