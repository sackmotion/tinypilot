import flask

import db.settings
import debug_logs
import hostname
import json_response
import local_system
import request_parsers.errors
import request_parsers.hostname
import request_parsers.video_settings
import update.launcher
import update.settings
import update.status
import version
import video_settings

api_blueprint = flask.Blueprint('api', __name__, url_prefix='/api')


@api_blueprint.route('/debugLogs', methods=['GET'])
def debug_logs_get():
    """Returns the TinyPilot debug log as a plaintext HTTP response.

    Returns:
        A text/plain response with the content of the logs in the response body.
    """
    try:
        return flask.Response(debug_logs.collect(), mimetype='text/plain')
    except debug_logs.Error as e:
        return flask.Response(f'Failed to retrieve debug logs: {e}', status=500)


@api_blueprint.route('/shutdown', methods=['POST'])
def shutdown_post():
    """Triggers shutdown of the system.

    Returns:
        Empty response on success, error object otherwise.
    """
    try:
        local_system.shutdown()
        return json_response.success()
    except local_system.Error as e:
        return json_response.error(e), 500


@api_blueprint.route('/restart', methods=['POST'])
def restart_post():
    """Triggers restart of the system.

    For backwards compatibility, we must include the now deprecated `success`
    and `error` properties in the response. This is needed for when TinyPilot
    updates from a version before our migration to using conventional HTTP
    status codes. Issue: https://github.com/tiny-pilot/tinypilot/issues/506

    Returns:
        No additional properties on success.

        success: true for backwards compatibility.
        error: null for backwards compatibility.

        Returns error object otherwise.
    """
    try:
        local_system.restart()
        return json_response.success({'success': True, 'error': None})
    except local_system.Error as e:
        return json_response.error(e), 500


@api_blueprint.route('/update', methods=['GET'])
def update_get():
    """Fetches the state of the latest update job.

    For backwards compatibility, we must include the now deprecated `success`
    and `error` properties in the response. This is needed for when TinyPilot
    updates from a version before our migration to using conventional HTTP
    status codes. Issue: https://github.com/tiny-pilot/tinypilot/issues/506

    Returns:
        On success, a JSON data structure with the following properties:
        status: str describing the status of the job. Can be one of
                ["NOT_RUNNING", "DONE", "IN_PROGRESS"].
        updateError: str of the error that occured while updating. If no error
                     occured, then this will be null.
        success: true for backwards compatibility.
        error: null for backwards compatibility.

        Example:
        {
            "status": "NOT_RUNNING",
            "updateError": null,
            "success": true,
            "error": null
        }
    """

    status, error = update.status.get()
    return json_response.success({
        'status': str(status),
        'updateError': error,
        'success': True,
        'error': None
    })


@api_blueprint.route('/update', methods=['PUT'])
def update_put():
    """Initiates job to update TinyPilot to the latest version available.

    This endpoint asynchronously starts a job to update TinyPilot to the latest
    version.  API clients can then query the status of the job with GET
    /api/update to see the status of the update.

    Returns:
        Empty response on success, error object otherwise.
    """
    try:
        update.launcher.start_async()
    except update.launcher.AlreadyInProgressError:
        # If an update is already in progress, treat it as success.
        pass
    except update.launcher.Error as e:
        return json_response.error(e), 500
    return json_response.success()


@api_blueprint.route('/version', methods=['GET'])
def version_get():
    """Retrieves the current installed version of TinyPilot.

    Returns:
        On success, a JSON data structure with the following properties:
        version: str.

        Example:
        {
            "version": "bf07bfe",
        }

        Returns error object on failure.
    """
    try:
        return json_response.success({'version': version.local_version()})
    except version.Error as e:
        return json_response.error(e), 500


@api_blueprint.route('/latestRelease', methods=['GET'])
def latest_release_get():
    """Retrieves the latest version of TinyPilot.

    Returns:
        On success, a JSON data structure with the following properties:
        version: str.

        Example:
        {
            "version": "bf07bfe72941457cf068ca0a44c6b0d62dd9ef05",
        }

        Returns error object on failure.
    """
    try:
        return json_response.success({'version': version.latest_version()})
    except version.Error as e:
        return json_response.error(e), 500


@api_blueprint.route('/hostname', methods=['GET'])
def hostname_get():
    """Determines the hostname of the machine.

    Returns:
        On success, a JSON data structure with the following properties:
        hostname: string.

        Example:
        {
            "hostname": "tinypilot"
        }

        Returns an error object on failure.
    """
    try:
        return json_response.success({'hostname': hostname.determine()})
    except hostname.Error as e:
        return json_response.error(e), 500


@api_blueprint.route('/hostname', methods=['PUT'])
def hostname_set():
    """Changes the machine’s hostname

    Expects a JSON data structure in the request body that contains the
    new hostname as string. Example:
    {
        "hostname": "grandpilot"
    }

    Returns:
        Empty response on success, error object otherwise.
    """
    try:
        new_hostname = request_parsers.hostname.parse_hostname(flask.request)
        hostname.change(new_hostname)
        return json_response.success()
    except request_parsers.errors.Error as e:
        return json_response.error(e), 400
    except hostname.Error as e:
        return json_response.error(e), 500


@api_blueprint.route('/status', methods=['GET'])
def status_get():
    """Checks the status of TinyPilot.

    This endpoint may be called from all locations, so there is no restriction
    in regards to CORS.

    For backwards compatibility, we must include the now deprecated `success`
    and `error` properties in the response. This is needed for when TinyPilot
    updates from a version before our migration to using conventional HTTP
    status codes. Issue: https://github.com/tiny-pilot/tinypilot/issues/506

    Returns:
        No additional properties implies the server is up and running.

        success: true for backwards compatibility.
        error: null for backwards compatibility.
    """
    response = json_response.success({'success': True, 'error': None})
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response


@api_blueprint.route('/settings/video', methods=['GET'])
def settings_video_get():
    """Retrieves the current video settings.

    Returns:
        On success, a JSON data structure with the following properties:
        - streamingMode: string
        - fps: int
        - defaultFps: int
        - jpegQuality: int
        - defaultJpegQuality: int
        - h264Bitrate: int
        - defaultH264Bitrate: int

        Example of success:
        {
            "streamingMode": "MJPEG",
            "fps": 12,
            "defaultFps": 30,
            "jpegQuality": 80,
            "defaultJpegQuality": 80,
            "h264Bitrate": 450,
            "defaultH264Bitrate": 5000
        }

        Returns an error object on failure.
    """
    try:
        update_settings = update.settings.load()
    except update.settings.LoadSettingsError as e:
        return json_response.error(e), 500

    streaming_mode = db.settings.Settings().get_streaming_mode().value

    return json_response.success({
        'streamingMode': streaming_mode,
        'fps': update_settings.ustreamer_desired_fps,
        'defaultFps': video_settings.DEFAULT_FPS,
        'jpegQuality': update_settings.ustreamer_quality,
        'defaultJpegQuality': video_settings.DEFAULT_JPEG_QUALITY,
        'h264Bitrate': update_settings.ustreamer_h264_bitrate,
        'defaultH264Bitrate': video_settings.DEFAULT_H264_BITRATE
    })


@api_blueprint.route('/settings/video', methods=['PUT'])
def settings_video_put():
    """Saves new video settings.

    Note: for the new settings to come into effect, you need to make a call to
    the /settings/video/apply endpoint afterwards.

    Expects a JSON data structure in the request body that contains the
    following parameters for the video settings:
    - streamingMode: string
    - fps: int
    - jpegQuality: int
    - h264Bitrate: int

    Example of request body:
    {
        "streamingMode": "MJPEG",
        "fps": 12,
        "jpegQuality": 80,
        "h264Bitrate": 450
    }

    Returns:
        Empty response on success, error object otherwise.
    """
    try:
        streaming_mode = \
            request_parsers.video_settings.parse_streaming_mode(flask.request)
        fps = request_parsers.video_settings.parse_fps(flask.request)
        jpeg_quality = request_parsers.video_settings.parse_jpeg_quality(
            flask.request)
        h264_bitrate = request_parsers.video_settings.parse_h264_bitrate(
            flask.request)
    except request_parsers.errors.InvalidVideoSettingError as e:
        return json_response.error(e), 400

    try:
        update_settings = update.settings.load()
    except update.settings.LoadSettingsError as e:
        return json_response.error(e), 500

    update_settings.ustreamer_desired_fps = fps
    update_settings.ustreamer_quality = jpeg_quality
    update_settings.ustreamer_h264_bitrate = h264_bitrate

    # Store the new parameters. Note: we only actually persist anything if *all*
    # values have passed the validation.
    db.settings.Settings().set_streaming_mode(streaming_mode)
    try:
        update.settings.save(update_settings)
    except update.settings.SaveSettingsError as e:
        return json_response.error(e), 500

    return json_response.success()


@api_blueprint.route('/settings/video/apply', methods=['POST'])
def settings_video_apply_post():
    """Applies the current video settings found in the settings file.

    Returns:
        Empty response on success, error object otherwise.
    """
    try:
        video_settings.apply()
    except video_settings.Error as e:
        return json_response.error(e), 500
    return json_response.success()
