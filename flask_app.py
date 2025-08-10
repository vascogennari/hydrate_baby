from flask import Flask, request, render_template
import hydrate_core
import io, logging, warnings

app = Flask(__name__)

# Setup logging to capture logs in the string buffer
logs = io.StringIO()
logger = logging.getLogger('app_logger')
logger.setLevel(logging.INFO)

# Avoid adding multiple handlers if the code reloads multiple times
if not logger.handlers:
    log_handler = logging.StreamHandler(logs)
    logger.addHandler(log_handler)

# Capture warnings as well
def warn_to_log(message, category, filename, lineno, file=None, line=None):
    logger.warning(f'{category.__name__}: {message} ({filename}:{lineno})')
warnings.showwarning = warn_to_log

@app.route('/', methods=['GET', 'POST'])
def index():

    logs.truncate(0)
    logs.seek(0)
    result = None
    error = None

    if request.method == 'POST':
        user_input = request.form.to_dict()
        try:
            result = hydrate_core.process(user_input, logger)
        except ValueError as e:
            error = str(e)
            logger.error(f'ValueError: {e}')
        except Exception as e:
            error = str(e)
            logger.error(f'Unexpected error: {e}')

    return render_template('index.html', result=result, logs=logs.getvalue(), error=error)
