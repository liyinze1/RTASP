# RTASP

### 1. Define your own ```sensor```
You own sensor must inherit from ```RTASP.sensor```, and you must re-write the ```get_data()``` function. When a session starts, ```RTASP``` will automatically call ```get_data()```

### 2. 