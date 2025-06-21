#!/usr/bin/env python3
"""
MediaGrabber Web GUI using Flask (YouTube MP3, Facebook/Instagram MP4).
"""

from pathlib import Path
import tempfile, shutil
from flask import Flask, render_template, request, Response, stream_with_context, jsonify

from media_grabber import download_and_extract_audio, download_video_file

from urllib.parse import quote
from yt_dlp import YoutubeDL

app = Flask(__name__)


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')


@app.route('/metadata', methods=['POST'])
def get_metadata():
    data = request.get_json() or {}
    url = data.get('url', '').strip()
    if not url:
        return jsonify({'error': 'The URL is required'}), 400
    try:
        # Ensure only single video info, ignore any playlist parameters
        ydl_opts = {'quiet': True, 'no_warnings': True, 'noplaylist': True}
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        return jsonify({'title': info.get('title'), 'thumbnail': info.get('thumbnail')})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/download', methods=['POST'])
def download_media():
    data = request.get_json() or {}
    url = data.get('url', '').strip()
    if not url:
        return jsonify({'error': 'The URL is required'}), 400
    tmpdir = tempfile.mkdtemp()
    source = data.get('source', 'youtube')
    try:
        if source == 'youtube':
            download_and_extract_audio(url, Path(tmpdir))
            pattern = '*.mp3'
            mimetype = 'audio/mpeg'
        else:
            # Enforce 50MB max limit for Facebook/Instagram video downloads
            info = YoutubeDL({'quiet': True, 'no_warnings': True, 'noplaylist': True})
            info_dict = info.extract_info(url, download=False)
            size = info_dict.get('filesize') or info_dict.get('filesize_approx', 0)
            if size and size > 50*1024*1024:
                shutil.rmtree(tmpdir)
                return jsonify({'error': 'Video size exceeds 50MB limit'}), 400
            download_video_file(url, Path(tmpdir))
            pattern = '*.mp4'
            mimetype = 'video/mp4'
        files = list(Path(tmpdir).glob(pattern))
        if not files:
            shutil.rmtree(tmpdir)
            return jsonify({'error': f'{pattern} file not found'}), 500
        file_path = files[0]
        def generate():
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    yield chunk
            shutil.rmtree(tmpdir)
        # Prepare response headers: RFC5987 filename* and Content-Length for progress
        quoted_name = quote(file_path.name)
        file_size = file_path.stat().st_size
        headers = {
            'Content-Disposition': f"attachment; filename*=UTF-8''{quoted_name}",
            'Content-Length': str(file_size)
        }
        return Response(stream_with_context(generate()), mimetype=mimetype, headers=headers)
    except Exception as e:
        shutil.rmtree(tmpdir)
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080, use_reloader=False)
