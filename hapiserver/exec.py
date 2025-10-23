import os
import sys
import logging
import subprocess

logger = logging.getLogger(__name__)

def exec(script, args="", stream=False):
  if stream:
    return _stream(script, args)
  else:
    return _read(script, args)


def _read(script, args=""):

  if not os.path.exists(script):
    content = "Execution script not found"
    logger.error(f"{content}: {script}")
    return None, {"code": 1500, "message": content}

  call = [sys.executable, script, *args.split()]
  logger.info(f"Executing: {' '.join(call)}")
  try:
    kwargs = {
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "text": True,
        "check": True,
    }
    result = subprocess.run(call, **kwargs)
    return result.stdout, None
  except Exception as e:
    message = "Execution of script failed"
    error = {
      "code": 1500,
      "message": message,
      "message_console": str(getattr(e, "stderr", None)),
      "exception": e
    }
    return None, error


def _stream(script, args=""):

  if not os.path.exists(script):
    content = "Execution script not found"
    return None, {"code": 1500, "message": content}

  call = [sys.executable, script, *args.split()]
  logger.info(f"Executing: {' '.join(call)}")
  try:
    kwargs = {
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "bufsize": 1,
        "text": True,
    }
    proc = subprocess.Popen(call, **kwargs)
  except Exception as e:
    message = "Execution of script failed"
    error = {
      "code": 1500,
      "message": message,
      "message_console": str(getattr(e, "stderr", None)),
      "exception": e
    }
    return None, error

  def stream_output():
    try:
      # stream stdout lines as they arrive
      for line in proc.stdout:
        yield line
      proc.stdout.close()
      returncode = proc.wait()
      if returncode != 0:
        emsg = f"Error: {proc.stderr.read()}"
        logger.error(emsg)
        yield emsg
    finally:
      if proc.poll() is None:
        proc.kill()

  return stream_output, None
