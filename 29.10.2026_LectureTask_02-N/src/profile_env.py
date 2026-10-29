import argparse, glob, json, os, platform, re, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from salt import get_student_params

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = os.path.join(ROOT, "results")


def run(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return ""


def parse_size(text):
    m = re.match(r"\s*(\d+)\s*([KMG]?)", text or "")
    if not m:
        return None
    return int(m.group(1)) * {"": 1, "K": 1024, "M": 1024 ** 2, "G": 1024 ** 3}[m.group(2)]


def linux_info():
    info = {}
    cpuinfo = open("/proc/cpuinfo").read()
    m = re.search(r"model name\s*:\s*(.+)", cpuinfo)
    info["model_name"] = m.group(1).strip() if m else platform.processor()
    fam = re.search(r"cpu family\s*:\s*(\d+)", cpuinfo)
    mod = re.search(r"^model\s*:\s*(\d+)", cpuinfo, re.M)
    info["microarchitecture"] = f"family {fam.group(1)} model {mod.group(1)}" if fam and mod else platform.machine()
    mhz = re.search(r"cpu MHz\s*:\s*([\d.]+)", cpuinfo)
    base = None
    lscpu = run("lscpu")
    m2 = re.search(r"CPU max MHz:\s*([\d.]+)", lscpu)
    m3 = re.search(r"@\s*([\d.]+)\s*GHz", info["model_name"])
    if m3:
        base = float(m3.group(1)) * 1000
    elif mhz:
        base = float(mhz.group(1))
    info["base_frequency_mhz"] = base
    info["max_frequency_mhz"] = float(m2.group(1)) if m2 else None
    flags = re.search(r"flags\s*:\s*(.+)", cpuinfo)
    fl = flags.group(1).split() if flags else []
    info["simd"] = [f for f in ("sse4_2", "avx", "avx2", "fma", "avx512f") if f in fl]
    pairs = set()
    for p in glob.glob("/sys/devices/system/cpu/cpu[0-9]*/topology/thread_siblings_list"):
        pairs.add(open(p).read().strip())
    logical = os.cpu_count()
    physical = len(pairs) if pairs else None
    if not physical:
        m4 = re.search(r"Core\(s\) per socket:\s*(\d+)", lscpu)
        m5 = re.search(r"Socket\(s\):\s*(\d+)", lscpu)
        if m4 and m5:
            physical = int(m4.group(1)) * int(m5.group(1))
    caches = {}
    for d in sorted(glob.glob("/sys/devices/system/cpu/cpu0/cache/index*")):
        try:
            level = open(d + "/level").read().strip()
            ctype = open(d + "/type").read().strip()
            size = parse_size(open(d + "/size").read())
            line = int(open(d + "/coherency_line_size").read().strip())
        except Exception:
            continue
        if ctype == "Instruction":
            continue
        caches[f"L{level}"] = {"size_bytes": size, "line_size_bytes": line, "type": ctype}
    return info, physical, logical, caches


def macos_info():
    def sc(key):
        v = run(f"sysctl -n {key}")
        return int(v) if v.isdigit() else None

    info = {}
    info["model_name"] = run("sysctl -n machdep.cpu.brand_string") or platform.processor()
    info["microarchitecture"] = platform.machine()
    freq = sc("hw.cpufrequency")
    info["base_frequency_mhz"] = freq / 1e6 if freq else None
    info["max_frequency_mhz"] = None
    info["simd"] = []
    physical = sc("hw.physicalcpu")
    logical = sc("hw.logicalcpu") or os.cpu_count()
    line = sc("hw.cachelinesize") or 64
    caches = {}
    l1 = sc("hw.perflevel0.l1dcachesize") or sc("hw.l1dcachesize")
    l2 = sc("hw.perflevel0.l2cachesize") or sc("hw.l2cachesize")
    l3 = sc("hw.l3cachesize")
    for level, size in (("L1", l1), ("L2", l2), ("L3", l3)):
        if size:
            caches[level] = {"size_bytes": size, "line_size_bytes": line, "type": "Data" if level == "L1" else "Unified"}
    if not caches:
        caches["L1"] = {"size_bytes": None, "line_size_bytes": line, "type": "Data"}
    return info, physical, logical, caches


def generic_info():
    info = {"model_name": platform.processor() or platform.machine(), "microarchitecture": platform.machine(),
            "base_frequency_mhz": None, "max_frequency_mhz": None, "simd": []}
    physical = logical = None
    try:
        import psutil
        physical = psutil.cpu_count(logical=False)
        logical = psutil.cpu_count(logical=True)
        f = psutil.cpu_freq()
        if f:
            info["base_frequency_mhz"] = f.current
    except Exception:
        logical = os.cpu_count()
    return info, physical, logical, {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--student-id", required=True)
    args = ap.parse_args()
    os.makedirs(RESULTS, exist_ok=True)

    system = platform.system()
    if system == "Linux":
        cpu, physical, logical, caches = linux_info()
    elif system == "Darwin":
        cpu, physical, logical, caches = macos_info()
    else:
        cpu, physical, logical, caches = generic_info()

    line = 64
    for c in caches.values():
        if c.get("line_size_bytes"):
            line = c["line_size_bytes"]
            break

    profile = {
        "cpu": cpu,
        "cores": {
            "physical": physical,
            "logical": logical,
            "smt_enabled": bool(physical and logical and logical > physical),
        },
        "cache": {
            "L1d_bytes": caches.get("L1", {}).get("size_bytes"),
            "L2_bytes": caches.get("L2", {}).get("size_bytes"),
            "L3_bytes": caches.get("L3", {}).get("size_bytes"),
            "line_size_bytes": line,
        },
        "os": {
            "system": system,
            "kernel": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
        },
        "python": {
            "implementation": platform.python_implementation(),
            "version": platform.python_version(),
            "compiler": platform.python_compiler(),
        },
    }
    with open(os.path.join(RESULTS, "host_profile.json"), "w") as f:
        json.dump(profile, f, indent=2)
    with open(os.path.join(RESULTS, "salted_params.json"), "w") as f:
        json.dump(get_student_params(args.student_id), f, indent=2)
    print(json.dumps(profile, indent=2))
    print(json.dumps(get_student_params(args.student_id), indent=2))


if __name__ == "__main__":
    main()