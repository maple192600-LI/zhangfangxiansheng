"""测试共享 fixtures — agents 模块"""
import os
import sys
import pytest

# 确保项目根目录在 sys.path 中
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
