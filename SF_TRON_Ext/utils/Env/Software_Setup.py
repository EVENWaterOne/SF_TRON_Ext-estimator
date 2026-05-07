import os, sys
# Add IsaacLab source to path so isaaclab.app is importable
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
_isaaclab_src = os.path.join(_project_root, "isaaclab_repo", "source")
if os.path.isdir(_isaaclab_src) and _isaaclab_src not in sys.path:
    sys.path.insert(0, _isaaclab_src)

from isaaclab.app import AppLauncher
import argparse

def App_Setup(device,headless):
# add argparse arguments
    parser = argparse.ArgumentParser(description="Tutorial on adding sensors on a robot.")
    # append AppLauncher cli args
    AppLauncher.add_app_launcher_args(parser)
    # parse the arguments
    args_cli, _ = parser.parse_known_args()
    args_cli.device = device  # set the device to cuda:0
    args_cli.headless = headless  # uncomment this to run in headless mode

    args_cli.enable_cameras = True  # uncomment this to enable camera rendering
    # launch omniverse app
    app_launcher = AppLauncher(args_cli)
    simulation_app = app_launcher.app
