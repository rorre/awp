import json
import sys
from typing import List, Tuple
from siak_awp_python.config import load_config

output: List[Tuple[str, List[int]]] = []
cfg = load_config(sys.argv[1])
for matkul in cfg["selections"]:
    name = f"c[{matkul['code']}_{matkul['curriculum']}]"
    output.append((name, matkul["preference"]))

print(cfg["username"])
print(cfg["password"])
print(f"window.irsfill({json.dumps(output)})\n")
