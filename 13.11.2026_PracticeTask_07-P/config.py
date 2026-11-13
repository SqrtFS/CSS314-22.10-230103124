import os

STUDENT_ID = int(os.environ.get("LAB_ID", 230103124))
P_PHYS = int(os.environ.get("LAB_PPHYS", 8))
P_BOUNDARY = 4
CACHE_LINE = 128
L1D_BYTES = 65536
L2_BYTES = 4194304
L3_BYTES = 0
QUICK = os.environ.get("LAB_QUICK") == "1"
