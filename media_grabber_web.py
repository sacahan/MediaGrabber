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
import threading
import uuid

# In-memory store for download progress state
PROGRESS_STATE = {}

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


def do_download(job_id: str, url: str, source: str):
    """
    Background download task updating PROGRESS_STATE[job_id].
    """
    tmpdir = tempfile.mkdtemp()
    state = PROGRESS_STATE.get(job_id, {})
    def hook(d):
        status = d.get('status')
        if status == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            downloaded = d.get('downloaded_bytes', 0)
            if total:
                state['progress'] = int(downloaded / total * 100)
        elif status == 'finished':
            state['progress'] = 100
    try:
        if source == 'youtube':
            download_and_extract_audio(url, Path(tmpdir), progress_hook=hook)
            pattern = '*.mp3'
            mimetype = 'audio/mpeg'
        else:
            info = YoutubeDL({'quiet': True, 'no_warnings': True, 'noplaylist': True})
            info_dict = info.extract_info(url, download=False)
            size = info_dict.get('filesize') or info_dict.get('filesize_approx', 0)
            if size and size > 50*1024*1024:
                shutil.rmtree(tmpdir)
                state.update(status='error', error='Video size exceeds 50MB limit')
                return
            download_video_file(url, Path(tmpdir), progress_hook=hook)
            pattern = '*.mp4'
            mimetype = 'video/mp4'
        files = list(Path(tmpdir).glob(pattern))
        if not files:
            shutil.rmtree(tmpdir)
            state.update(status='error', error=f'{pattern} file not found')
            return
        file_path = files[0]
        state.update(
            status='done',
            file_path=str(file_path),
            tmpdir=tmpdir,
            filename=file_path.name,
            mimetype=mimetype,
        )
    except Exception as e:
        shutil.rmtree(tmpdir)
        state.update(status='error', error=str(e))

@app.route('/download_start', methods=['POST'])
def download_start():
    data = request.get_json() or {}
    url = data.get('url', '').strip()
    if not url:
        return jsonify({'error': 'The URL is required'}), 400
    source = data.get('source', 'youtube')
    job_id = uuid.uuid4().hex
    PROGRESS_STATE[job_id] = {'progress': 0, 'status': 'in_progress'}
    threading.Thread(target=do_download, args=(job_id, url, source), daemon=True).start()
    return jsonify({'job_id': job_id})

@app.route('/progress/<job_id>', methods=['GET'])
def download_progress(job_id):
    state = PROGRESS_STATE.get(job_id)
    if not state:
        return jsonify({'error': 'Job not found'}), 404
    resp = {'progress': state.get('progress', 0), 'status': state.get('status')}
    if state.get('status') == 'error':
        resp['error'] = state.get('error')
    return jsonify(resp)

@app.route('/download_file/<job_id>', methods=['GET'])
def download_file(job_id):
    state = PROGRESS_STATE.get(job_id)
    if not state or state.get('status') != 'done' or not state.get('file_path'):
        return jsonify({'error': 'File not ready'}), 404
    file_path = state['file_path']
    tmpdir = state['tmpdir']
    filename = state['filename']
    mimetype = state['mimetype']
    def generate():
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                yield chunk
        shutil.rmtree(tmpdir)
        PROGRESS_STATE.pop(job_id, None)
    headers = {
        'Content-Disposition': f"attachment; filename*=UTF-8''{quote(filename)}",
        'Content-Length': str(Path(file_path).stat().st_size)
    }
    return Response(stream_with_context(generate()), mimetype=mimetype, headers=headers)



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080, use_reloader=False)