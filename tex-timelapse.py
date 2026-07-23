#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'src'))
from tex_timelapse.cli import main
main()
