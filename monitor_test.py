import pytest

import monitor


@pytest.fixture()
def prelude_text():
    """This stuff gets stripped away by `monitor.parse_output`"""
    prelude = """Processes: 309 total, 2 running, 307 sleeping, 1421 threads 
2021/01/12 16:25:38
Load Avg: 2.78, 2.23, 2.18 
CPU usage: 12.50% user, 25.0% sys, 62.50% idle 
SharedLibs: 196M resident, 67M data, 23M linkedit.
MemRegions: 48071 total, 3085M resident, 177M private, 980M shared.
PhysMem: 7613M used (1204M wired), 578M unused.
VM: 1437G vsize, 1993M framework vsize, 0(0) swapins, 0(0) swapouts.
Networks: packets: 1185129/1586M in, 512344/41M out.
Disks: 165710/2809M read, 115455/2177M written.

COMMAND          %CPU MEM  
top              0.0  1740K
top              0.0  1792K
mdworker_shared  0.0  4024K
ocspd            0.0  592K 
transparencyd    0.0  3788K
mdworker_shared  0.0  5716K
mdworker_shared  0.0  3224K
MTLCompilerServi 0.0  10M  
MTLCompilerServi 0.0  3384K
com.apple.Perfor 0.0  1504K
Processes: 309 total, 2 running, 307 sleeping, 1404 threads 
2021/01/12 16:25:43
Load Avg: 2.64, 2.21, 2.18 
CPU usage: 8.17% user, 5.80% sys, 86.2% idle 
SharedLibs: 196M resident, 67M data, 23M linkedit.
MemRegions: 48071 total, 3085M resident, 177M private, 980M shared.
PhysMem: 7607M used (1215M wired), 584M unused.
VM: 1437G vsize, 1993M framework vsize, 0(0) swapins, 0(0) swapouts.
Networks: packets: 1185140/1586M in, 512349/41M out.
Disks: 165710/2809M read, 115455/2177M written.

COMMAND          %CPU MEM   
firefox          21.2 889M- 
WindowServer     15.4 324M+ 
plugin-container 4.5  130M  
top              3.0  1792K+
kernel_task      2.9  171M+ 
plugin-container 1.5  82M+  
Terminal         0.9  45M-  
top              0.5  1804K+
pycharm          0.3  811M- 
plugin-container 0.3  65M   
Processes: 308 total, 3 running, 305 sleeping, 1402 threads 
2021/01/12 16:25:48
Load Avg: 2.67, 2.23, 2.18 
CPU usage: 8.64% user, 6.85% sys, 84.49% idle 
SharedLibs: 196M resident, 67M data, 23M linkedit.
MemRegions: 48009 total, 3082M resident, 177M private, 980M shared.
PhysMem: 7603M used (1203M wired), 588M unused.
VM: 1432G vsize, 1993M framework vsize, 0(0) swapins, 0(0) swapouts.
Networks: packets: 1185161/1586M in, 512350/41M out.
Disks: 165710/2809M read, 115456/2177M written.

COMMAND          %CPU MEM   
"""
    return prelude


class TestParser(object):
    def test_cpu_requires_floats(self, prelude_text, caplog):
        record = "firefox          21.2ERR 889M-\n"
        text = prelude_text + record
        monitor.parse_output(text)
        assert caplog.records[0].message.startswith("could not convert string to float")

    def test_mem_suffix_not_in_lookup_map(self, prelude_text, caplog):
        record = "firefox          21.2 889P-\n"
        text = prelude_text + record
        monitor.parse_output(text)
        assert caplog.records[0].message.startswith("'P'")

    def test_mem_requires_int(self, prelude_text, caplog):
        record = "firefox          21.2 889ERRM-\n"
        text = prelude_text + record
        monitor.parse_output(text)
        assert caplog.records[0].message.startswith("invalid literal for int() with base 10: '889ERR000'")

    def test_combines_identical_command_names(self, prelude_text):
        record = "firefox          21.2 9M-\nfirefox          21.2 9M-\n"
        text = prelude_text + record
        parsed = monitor.parse_output(text)
        assert parsed[0][2] == 42.4
        assert parsed[0][3] == 18000

