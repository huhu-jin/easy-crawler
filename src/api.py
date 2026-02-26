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
        获取指定日期的所有 Markdown 文件列表
        
        Query Parameters:
            date: 日期，格式 YYYY-MM-DD，默认为今天
        
        Returns:
            JSON: {"date": "YYYY-MM-DD", "files": ["file1.md", "file2.md"]}
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
        
        # 获取文件列表
        files = storage_service.get_files_by_date(date)
        
        return jsonify({
            'date': date.strftime('%Y-%m-%d'),
            'count': len(files),
            'files': files
        })
    
    @app.route('/api/content', methods=['GET'])
    def get_content():
        """
        获取指定文件的内容
        
        Query Parameters:
            date: 日期，格式 YYYY-MM-DD，默认为今天
            filename: 文件名
        
        Returns:
            JSON: {"date": "YYYY-MM-DD", "filename": "xxx.md", "content": "..."}
        """
        date_str = request.args.get('date')
        filename = request.args.get('filename')
        
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
        content = storage_service.get_file_content(date, filename)
        
        if content is None:
            return jsonify({
                'error': '文件不存在'
            }), 404
        
        return jsonify({
            'date': date.strftime('%Y-%m-%d'),
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
