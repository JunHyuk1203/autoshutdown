"""Source launcher; always use the audited source rather than an embedded snapshot."""
import runpy
from pathlib import Path

if __name__ == '__main__':
    runpy.run_path(str(Path(__file__).with_name('auto_shutdown.py')), run_name='__main__')
