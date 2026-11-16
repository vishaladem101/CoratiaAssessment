"""
Resource resolution utilities for ROV Ground Station.
Locates assets across developer source trees, package submodules, and PyInstaller standalone binaries.
"""
import os
import sys


def get_resource_path(relative_path):
    """Returns absolute path to resource, working in dev mode, modular directories, and PyInstaller bundles."""
    if hasattr(sys, '_MEIPASS'):
        bundle_dir = sys._MEIPASS
        p1 = os.path.join(bundle_dir, "assets", relative_path)
        if os.path.exists(p1):
            return p1
        p2 = os.path.join(bundle_dir, relative_path)
        if os.path.exists(p2):
            return p2
        return p1

    # Dev / source mode:
    curr_dir = os.path.dirname(os.path.abspath(__file__))
    # Step up from view/ -> src/ -> project root
    project_root = curr_dir
    while project_root and os.path.basename(project_root) in ("view", "src"):
        project_root = os.path.dirname(project_root)

    p_assets = os.path.join(project_root, "assets", relative_path)
    if os.path.exists(p_assets):
        return p_assets
    p_root = os.path.join(project_root, relative_path)
    if os.path.exists(p_root):
        return p_root
    p_curr = os.path.join(curr_dir, relative_path)
    if os.path.exists(p_curr):
        return p_curr
    return p_assets

