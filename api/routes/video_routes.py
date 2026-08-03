"""
Video API Routes (Flask)
Video artık client-side'da local asset ile oluşturuluyor.
Fal AI kullanılmıyor.
"""

from flask import Blueprint, jsonify
import time

video_bp = Blueprint('video', __name__)


@video_bp.route('/generate-video', methods=['POST'])
def generate_video():
    """
    POST /api/video/generate-video
    
    Video artık client-side'da local asset loop ile oluşturuluyor.
    Bu endpoint artık kullanılmıyor.
    """
    return jsonify({
        'video_url': None,
        'video_id': f"local_{int(time.time())}",
        'status': 'deprecated',
        'message': 'Video generation is now handled client-side using local asset loop. No Fal AI request needed.',
    }), 200


@video_bp.route('/health', methods=['GET'])
def health_check():
    """
    GET /api/video/health
    
    Video servisi sağlık kontrolü
    """
    return jsonify({
        'status': 'healthy',
        'service': 'video_generation',
        'mode': 'local_asset_loop',
        'message': 'Video is created client-side by looping local asset video',
    }), 200
