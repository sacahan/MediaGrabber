#!/usr/bin/env python3
"""
MediaGrabber Web GUI using Flask (YouTube MP3, Facebook/Instagram MP4).
"""

from pathlib import Path
import tempfile, shutil
from flask import Flask, request, Response, stream_with_context, jsonify
from flask_cors import CORS # Import Flask-CORS

from media_grabber import download_and_extract_audio, download_video_file

from urllib.parse import quote
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError, ExtractorError, GeoRestrictedError
import logging
from logging.handlers import RotatingFileHandler
import threading
import uuid

# Ensure the log directory exists
log_dir = Path(__file__).parent / "log"
log_dir.mkdir(parents=True, exist_ok=True)

# Configure logging for the web application.
# This helps in debugging and monitoring the server's activity.
log_file = log_dir / "flask.log"
handler = RotatingFileHandler(log_file, maxBytes=10000, backupCount=1)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

app = Flask(__name__)
app.logger.setLevel(logging.INFO)
app.logger.addHandler(handler)
CORS(app) # Enable CORS for all routes. This is crucial for frontend-backend separation.

# Dictionary to store the progress and status of each download job.
# Key: job_id (string), Value: dictionary containing 'progress', 'status', 'stage', etc.
PROGRESS_STATE = {}


# Removed the / route as it will be handled by the Svelte frontend.
# @app.route('/', methods=['GET'])
# def index():
#     """Renders the main HTML page for the web GUI."""
#     return render_template('index.html')


@app.route('/metadata', methods=['POST'])
def get_metadata():
    """
    API endpoint to fetch video metadata (title, thumbnail) from a given URL.
    This is used by the frontend to display video information before download.
    """
    data = request.get_json() or {}
    url = data.get('url', '').strip()
    if not url:
        return jsonify({'error': 'The URL is required'}), 400
    try:
        # Configure yt-dlp to extract information without downloading the actual video.
        # 'quiet' and 'no_warnings' suppress console output from yt-dlp.
        # 'noplaylist' ensures only single video info is extracted, ignoring playlist parameters.
        ydl_opts = {'quiet': True, 'no_warnings': True, 'noplaylist': True}
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        return jsonify({'title': info.get('title'), 'thumbnail': info.get('thumbnail')})
    except ExtractorError:
        # Catch specific yt-dlp error for invalid or unsupported URLs during metadata extraction.
        return jsonify({'error': 'Could not extract video information. The URL might be invalid or unsupported.'}), 500
    except Exception as e:
        # Catch any other unexpected errors during metadata extraction.
        logging.error(f"Error fetching metadata for {url}: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


def do_download(job_id: str, url: str, source: str, format: str = 'mp3'):
    """
    Background task to perform the actual media download and update its progress state.
    This function runs in a separate thread to avoid blocking the main Flask application.
    """
    tmpdir = tempfile.mkdtemp() # Create a temporary directory for the download.
    state = PROGRESS_STATE.get(job_id, {}) # Get the current state for this job.
    state['stage'] = 'downloading' # Initialize the stage to 'downloading'.
    logging.info(f"[{job_id}] Starting download for {url} (source: {source}, format: {format})")

    def hook(d):
        """
        Progress hook for yt-dlp. This function is called by yt-dlp during the download process.
        It updates the global PROGRESS_STATE with current download progress and stage.
        """
        status = d.get('status')
        if status == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            downloaded = d.get('downloaded_bytes', 0)
            if total:
                state['progress'] = int(downloaded / total * 100)
        elif status == 'finished':
            # When yt-dlp reports 'finished', it means the download is complete,
            # but post-processing (like transcoding) might still be ongoing.
            state['progress'] = 100
            state['stage'] = 'transcoding' # Update stage to 'transcoding' to reflect post-processing.
            logging.info(f"[{job_id}] yt-dlp finished downloading. Starting post-processing.")

    try:
        # Call the appropriate download function based on the source and format.
        if source == 'youtube':
            if format == 'mp3':
                download_and_extract_audio(url, Path(tmpdir), progress_hook=hook)
                pattern = '*.mp3'
                mimetype = 'audio/mpeg'
            else:  # mp4
                download_video_file(url, Path(tmpdir), progress_hook=hook)
                pattern = '*.mp4'
                mimetype = 'video/mp4'
        else: # facebook, instagram, x, threads
            # For other sources, first check video size limit (50MB).
            # This is done by extracting info without downloading.
            info = YoutubeDL({'quiet': True, 'no_warnings': True, 'noplaylist': True})
            info_dict = info.extract_info(url, download=False)
            size = info_dict.get('filesize') or info_dict.get('filesize_approx', 0)
            if size and size > 50 * 1024 * 1024: # 50 MB limit
                shutil.rmtree(tmpdir) # Clean up temporary directory.
                logging.warning(f"[{job_id}] Video size ({size} bytes) exceeds 50MB limit.")
                state.update(status='error', error='Video size exceeds 50MB limit')
                return
            download_video_file(url, Path(tmpdir), progress_hook=hook)
            pattern = '*.mp4'
            mimetype = 'video/mp4'

        # After download and post-processing, find the resulting file.
        files = list(Path(tmpdir).glob(pattern))
        if not files:
            shutil.rmtree(tmpdir)
            logging.error(f"[{job_id}] Post-processing failed: {pattern} file not found.")
            state.update(status='error', error=f'{pattern} file not found')
            return

        file_path = files[0] # Assume only one file is generated.
        logging.info(f"[{job_id}] Download successful. File is at {file_path}")
        # Update the job state to 'done' and 'completed' stage.
        state.update(
            status='done',
            stage='completed', # Final stage indicating all processing is done.
            file_path=str(file_path),
            tmpdir=tmpdir,
            filename=file_path.name,
            mimetype=mimetype,
        )
    except GeoRestrictedError as e:
        # Handle geographical restriction errors.
        shutil.rmtree(tmpdir)
        logging.error(f"[{job_id}] Download failed: {e}")
        state.update(status='error', error='Video is not available in your region.')
    except ExtractorError as e:
        # Handle errors where video information cannot be extracted.
        shutil.rmtree(tmpdir)
        logging.error(f"[{job_id}] Download failed: {e}")
        state.update(status='error', error='Could not extract video information. The URL might be invalid or unsupported.')
    except DownloadError as e:
        # Handle general download errors from yt-dlp.
        shutil.rmtree(tmpdir)
        logging.error(f"[{job_id}] Download failed: {e}")
        state.update(status='error', error=f'Download failed: {e}')
    except Exception as e:
        # Catch any other unexpected errors during the download process.
        shutil.rmtree(tmpdir)
        logging.error(f"[{job_id}] An unexpected error occurred: {e}", exc_info=True)
        state.update(status='error', error='An unexpected error occurred. Please check the server logs.')

@app.route('/download_start', methods=['POST'])
def download_start():
    """
    API endpoint to initiate a download.
    It creates a new job_id and starts the do_download function in a separate thread.
    """
    data = request.get_json() or {}
    url = data.get('url', '').strip()
    if not url:
        return jsonify({'error': 'The URL is required'}), 400
    source = data.get('source', 'youtube')
    format = data.get('format', 'mp3')
    job_id = uuid.uuid4().hex # Generate a unique ID for this download job.
    # Initialize the job state in the global dictionary.
    PROGRESS_STATE[job_id] = {'progress': 0, 'status': 'in_progress', 'stage': 'queued'}
    logging.info(f"[{job_id}] Queuing download for {url}")
    # Start the download in a new daemon thread so it doesn't block the Flask app.
    threading.Thread(target=do_download, args=(job_id, url, source, format), daemon=True).start()
    return jsonify({'job_id': job_id})

@app.route('/progress/<job_id>', methods=['GET'])
def download_progress(job_id):
    """
    API endpoint to get the current progress of a specific download job.
    Frontend polls this endpoint to update the progress bar and status messages.
    """
    state = PROGRESS_STATE.get(job_id)
    if not state:
        return jsonify({'error': 'Job not found'}), 404
    # Return current progress, status, and stage.
    resp = {'progress': state.get('progress', 0), 'status': state.get('status'), 'stage': state.get('stage', 'unknown')}
    if state.get('status') == 'error':
        resp['error'] = state.get('error')
    return jsonify(resp)

@app.route('/download_file/<job_id>', methods=['GET'])
def download_file(job_id):
    """
    API endpoint to serve the downloaded file to the user.
    This streams the file content and cleans up the temporary directory afterwards.
    """
    state = PROGRESS_STATE.get(job_id)
    # Ensure the job exists, is done, and has a file path.
    if not state or state.get('status') != 'done' or not state.get('file_path'):
        return jsonify({'error': 'File not ready'}), 404
    file_path = state['file_path']
    tmpdir = state['tmpdir']
    filename = state['filename']
    mimetype = state['mimetype']
    def generate():
        """Generator function to stream the file in chunks."""
        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(8192) # Read file in 8KB chunks.
                if not chunk:
                    break
                yield chunk
        # Clean up temporary files and state after the file has been streamed.
        shutil.rmtree(tmpdir)
        PROGRESS_STATE.pop(job_id, None)
    headers = {
        # Set Content-Disposition to prompt download with the correct filename.
        'Content-Disposition': f"attachment; filename*=UTF-8''{quote(filename)}",
        'Content-Length': str(Path(file_path).stat().st_size) # Provide file size for progress indication.
    }
    # Stream the file as a Flask Response.
    return Response(stream_with_context(generate()), mimetype=mimetype, headers=headers)


if __name__ == '__main__':
    # Run the Flask application.
    # debug=True enables debugger and reloader (for development).
    # host='0.0.0.0' makes the server accessible from other machines on the network.
    # use_reloader=False is set to avoid issues with threading and multiple Flask instances.
    app.run(debug=True, host='0.0.0.0', port=8080, use_reloader=False)

