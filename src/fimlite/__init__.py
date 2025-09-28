import sys
from pathlib import Path
sys.path.append('src')
from fimlite.config import load_config
cfg = load_config(Path('configs/example.yml'))
print(cfg)  # shows dataclass with your values
