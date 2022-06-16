import shutil
import subprocess as sp
import os
import sys
import logging
import requests
import datetime
from dateutil.parser import parse as parsedate
import hashlib

log_format = "%(asctime)s - %(name)s - %(lineno)d - %(levelname)s - %(message)s"

__version__ = '0.0.1'

_log = logging.getLogger(__name__)


def mkdir(dirpath):
    if not os.path.exists(dirpath):
        os.makedirs(dirpath)


def execute(cmd, retcodes=(0,), stdout=sys.stdout, stderr=sys.stderr):
    cmd = cmd.strip()
    # exec_mode = exec_mode if exec_mode else os.environ.get("SNDG_EXEC_MODE", DEFAULT_SNDG_EXEC_MODE)
    try:
        _log.debug(cmd)
        process = sp.Popen(cmd, shell=True, stdout=stdout, stderr=stderr)
        process.communicate()
        return process.returncode
    except CalledProcessError as ex:
        if ex.returncode not in retcodes:
            raise
    return ex.returncode


def init_log(log_file_path=None, rootloglevel=logging.DEBUG):
    default_formatter = logging.Formatter(log_format)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(default_formatter)
    root = logging.getLogger()

    if log_file_path:
        fh = logging.FileHandler(log_file_path)
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(default_formatter)
        root.addHandler(fh)

    root.addHandler(console_handler)
    root.setLevel(rootloglevel)


def dl(src, dst_dir, dst_file, retry=4, timeout=30, ifnewer=True):
    originalfilename =   src.split("/")[-1]
    execute(
        f'wget {"-N" if ifnewer else ""} --timeout={timeout} -P {dst_dir} --waitretry=1 --retry-connrefused --tries={retry} "{src}"')
    dst = dst_dir + os.path.sep + dst_file
    dst_org = dst_dir + os.path.sep + originalfilename

    if dst != dst_org:
        if os.path.exists(dst):
            os.remove(dst)
        execute(f'ln "{dst_org}" "{dst}"')


def is_new(src, dstFile):
    r = requests.head(src)
    lastmodified = 'last-modified'
    if lastmodified not in r.headers:
        lastmodified = 'Last-Modified'
        if lastmodified not in r.headers:
            raise AttributeError(f"last-modified not found for resource {src}")

    url_time = r.headers[lastmodified]
    url_date = parsedate(url_time)
    file_time = datetime.datetime.fromtimestamp(os.path.getmtime(dstFile))
    return url_date > file_time


def execute_template(dst_path, dst_dir, **kwargs):
    # ["makeblastdb",
    #  {
    #      "package": "BioDbs",
    #      "function": "execute",
    #      "name": "pro",
    #      "template": "zcat {dst} | makeblastdb -in - -title {name}  -out {basedir}{name}"
    #  }]
    cmd = kwargs["template"].format(dst=dst_path, basedir=dst_dir, **kwargs)
    execute(cmd)  # , retcodes=(0,), stdout=sys.stdout, stderr=sys.stderr)

def md5(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()