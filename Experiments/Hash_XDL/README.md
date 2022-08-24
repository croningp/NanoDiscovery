# The Digital Signatures of Nanoparticles using XDL
This folder contains the XDL file of the synthesis of six nanoparticles. The corresponding code to convert them into a unique Hash representation is also shown. 
#### Example code
```python
from xdl import XDL
import hashlib
import numpy as np

def sort_reagent_name(xdl):
    """
    Sort the reagents of XDL according to their names
    Args:
        xdl:XDL objects
    Returns:
        xdl:Updated XDL obeject
    """
    xdl_json = xdl.as_json()
    indexes = np.argsort([xdl_json['reagents'][i]['name'] for i in range(len(xdl_json['reagents']))])
    xdl_json['reagents'] = [xdl_json['reagents'][index] for index in indexes]
    return XDL(xdl_json)

# Hash the initial seed
test_xdl = XDL("NP_seed.xdl")
test_xdl = sort_reagent_name(test_xdl)
xdl_str = test_xdl.as_string()
hash_value = hashlib.sha256((xdl_str+'True').encode('UTF-8')).hexdigest()
# print(xdl_str)
print(hash_value)

```