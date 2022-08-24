## The multistep synthesis
Run [basic.py](basic.py) will conduct the three python scripts from [L1.py](L1.py) to [L3.py](L3.py) sequentially, which conduct the three different batches of experiments. 
#### Example code
```python
import os
os.system("python3 L1.py")
os.system("python3 L2.py")
os.system("python3 L3.py")
```