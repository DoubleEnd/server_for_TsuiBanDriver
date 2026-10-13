import os
import subprocess
import sys

block_cipher = None


def write_version(root):
    """构建时把版本号文本化固定到 utils/_version.py：1.[已并入主干的远程分支数].[提交次数]"""

    def git(args):
        return subprocess.check_output(
            ["git", *args], cwd=root, stderr=subprocess.DEVNULL
        ).decode().strip()

    try:
        merged_branches = [
            line.strip()
            for line in git(["branch", "-r", "--merged", "main"]).splitlines()
            if line.strip()
            and "->" not in line
            and not line.strip().endswith(("/main", "/master"))
        ]
        version = f"1.{len(merged_branches)}.{git(['rev-list', '--count', 'HEAD'])}"
    except Exception:
        print("[build] 无法从 git 计算版本号，保留 utils/_version.py 的现有内容")
        return

    with open(os.path.join(root, "utils", "_version.py"), "w", encoding="utf-8") as f:
        f.write("# 由 build.spec 在构建时自动生成，请勿手动修改\n")
        f.write(f'VERSION = "{version}"\n')
    print(f"[build] 版本号已固定为 {version}")


write_version(SPECPATH)

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'flask',
        'flask_cors',
        'requests',
        'lxml',
        'bs4',
        'fake_useragent',
        'urllib3',
        'charset_normalizer',
        'certifi',
        'idna',
        'cryptography',
        'cffi',
        'pycparser',
        'click',
        'blinker',
        'itsdangerous',
        'jinja2',
        'markupsafe',
        'werkzeug',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='server_for_TsuiBanDriver',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)