import datetime
import logging
import os.path
import shutil

from BioDbs import init_log, execute, dl, mkdir, is_new,md5

_log = logging.getLogger(__name__)


def postprocessing(postparams, dst_filename, dst_dir):
    mod = __import__(postparams["package"])
    func = getattr(mod, postparams["function"])
    del postparams["package"]
    del postparams["function"]
    func(dst_filename, dst_dir, **postparams)


def process_datafile(datafile, basedir, params, dataparams):
    originalfilename = dataparams["url"].split("/")[-1]
    dst_filename = (dataparams["url"].split("/")[-1]
                    if dataparams["dst"].endswith("/")
                    else os.path.basename(dataparams["dst"]))

    if dataparams["dst"].endswith("/"):
        dst_path = basedir + os.path.sep + dataparams["dst"] + dst_filename
    else:
        dst_path = basedir + os.path.sep + dataparams["dst"]

    dst_dir = os.path.sep.join(dst_path.split(os.path.sep)[:-1]) + os.path.sep

    mkdir(dst_dir)
    assert os.path.exists(dst_dir), f'"{dst_dir}" could not be created'

    last_file_timestamp = None
    if params["CreateBK"]:
        if os.path.exists(dst_path):
            last_file_timestamp = datetime.datetime.fromtimestamp(os.path.getmtime(dst_path))
            if os.path.exists(dst_path + ".bk"):
                os.remove(dst_path + ".bk")
            execute(f"ln {dst_path} {dst_path}.bk")
    dl(dataparams["url"], dst_dir, dst_filename, ifnewer=params["DownloadIfNew"])
    assert os.path.exists(dst_dir + dst_filename), f"'{ dst_dir + dst_filename}' could not be created "
    # if new file is older proceed
    if last_file_timestamp and (last_file_timestamp < datetime.datetime.fromtimestamp(os.path.getmtime(dst_path))):
        if "checksum" in dataparams:
            chksum = datafile + "_checksum"
            dl(dataparams["checksum"], dst_dir, chksum)
            with open(dst_dir + chksum) as h:
                lines = h.readlines()
                md5s = {x.strip().split()[1]: x.strip().split()[0] for x in lines}
                if md5(dst_path) != md5s[originalfilename]:
                    _log.error(f"md5 for {datafile} does not match...")
                    raise AssertionError(f"md5 for {datafile} does not match...")
        if "postprocessing":
            for poststepname, postparams in dataparams.get("postprocessing",[]):
                _log.debug(f"postprocessing '{poststepname}' for '{datafile}'")
                postprocessing(postparams, dst_path, dst_dir)


def process_section(basedir, params, section_config):
    # "download?": "BioDbs.pfam.download",
    for datafile, dataparams in section_config.items():
        _log.info(f"processing {datafile}")
        try:
            process_datafile(datafile, basedir, params, dataparams)
        except Exception as ex:
            _log.info(ex, exc_info=True)


if __name__ == "__main__":

    import argparse
    import json

    parser = argparse.ArgumentParser(description='Detects active site from PDB of a given ligand')
    parser.add_argument('config', action='store', help="json config file")
    parser.add_argument('basedir', action='store', help="dir where everything is downloaded")

    parser.add_argument('-v', '--verbose', action="store_true")
    parser.add_argument('-s', '--silent', action="store_true")

    # parser.add_argument("-to", '--table_output', action='store', type=str)
    # parser.add_argument("-po",'--pdb_output', type=str, default="active_site.pdb")
    # parser.add_argument("-bo",'--pdb_output_hbond', type=str, default=None)

    args = parser.parse_args()

    init_log(rootloglevel=logging.DEBUG if args.verbose else logging.INFO)
    if args.silent:
        _log.disabled = True

    assert os.path.exists(args.config), f"'{args.config}' does not exist"

    with open(args.config) as h:
        tasks = json.load(h)

    params = tasks["config"]
    del tasks["config"]

    _log.info(f"processing {len(tasks)} sections...")
    for section, section_config in tasks.items():
        try:
            _log.info(f"processing section: {section}")
            process_section(args.basedir, params, section_config)
        except Exception as ex:
            _log.error(ex, exc_info=True)
