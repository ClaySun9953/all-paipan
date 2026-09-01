# run.py
# -*- coding: utf-8 -*-
"""
一键启动脚本：
1. 自动安装 requirements.txt 中的依赖
2. 检查必要文件是否齐全
3. 启动 Streamlit app.py
"""

import os
import subprocess
import sys
import time


def install_dependencies():
    """安装 requirements.txt 中的依赖。"""
    requirements_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "requirements.txt",
    )

    if not os.path.exists(requirements_path):
        print("❌ 找不到 requirements.txt")
        print("   请把 run.py 和 requirements.txt 放在同一目录。")
        sys.exit(1)

    print("📦 正在检查并安装依赖 ...")
    print("   （首次运行可能需要一两分钟，请稍候）\n")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "-r",
            requirements_path,
        ],
    )

    if result.returncode != 0:
        print("\n❌ 依赖安装失败")
        print("   请手动运行：")
        print(f"   {sys.executable} -m pip install -r requirements.txt")
        sys.exit(1)

    print("\n✅ 依赖安装完成\n")


def check_files():
    """检查项目文件是否齐全。"""
    required_files = [
        "app.py",
        "core_engine.py",
        "geocoder.py",
        "liuren_engine.py",
        "location_data.py",
        "ziwei_engine.py",
    ]

    base_dir = os.path.dirname(os.path.abspath(__file__))

    missing = [
        name
        for name in required_files
        if not os.path.exists(os.path.join(base_dir, name))
    ]

    if missing:
        print("❌ 以下文件缺失，请把它们放到本脚本同一目录：")
        for name in missing:
            print(f"   - {name}")
        sys.exit(1)

    print("✅ 项目文件齐全\n")


def main():
    print("=" * 50)
    print("🧿 赛博玄学 V36.2 一键启动")
    print("=" * 50)
    print()

    check_files()
    install_dependencies()

    print("🚀 正在启动 Streamlit ...")
    print("   浏览器将自动打开，如果没有，请手动访问：")
    print("   http://localhost:8501")
    print()
    print("⚠️  关闭本窗口即停止程序。")
    print()

    time.sleep(1)

    subprocess.run(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "app.py",
            "--server.headless",
            "true",
        ]
    )


if __name__ == "__main__":
    main()