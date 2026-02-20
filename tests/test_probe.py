import unittest
from unittest.mock import patch
from src.libinsert.probe import SysProbe

class testpr(unittest.TestCase):
    def setUp(self):
        self.probe = SysProbe(db_path="data/drivers.json")

    @patch("subprocess.check_output")
    def testamdgpudetection(self, falselspci):
        falselspci.return_value = '03:00.0 "VGA compatible controller [0300]" "Advanced Micro Devices, Inc. [AMD/ATI] [1002]" "Navi 21 [Radeon RX 6800/6800 XT / 6900 XT] [73bf]" -rc1 -p00 "Sapphire Technology Limited [1da2]" "Device [439e]"'
        
        matches = self.probe.find_needed_packages("arch")
        self.assertTrue(len(matches) > 0)
        all_pkgs = []
        for m in matches:
            all_pkgs.extend(m["packages"])
        self.assertIn("mesa", all_pkgs)
        self.assertIn("vulkan-radeon", all_pkgs)

    @patch("subprocess.check_output")
    def testgpuinfoformatting(self, falselspci):
        falselspci.return_value = '03:00.0 "VGA compatible controller [0300]" "Advanced Micro Devices, Inc. [AMD/ATI] [1002]" "Navi 21 [Radeon RX 6800/6800 XT / 6900 XT] [73bf]" -rc1 -p00 "Sapphire Technology Limited [1da2]" "Device [439e]"'
        
        gpu_info = self.probe._get_gpu_info()
        self.assertEqual(gpu_info, "AMD/ATI Radeon RX 6800/6800 XT / 6900 XT")

    @patch("subprocess.check_output")
    def testnvidiagpudetection(self, falselspci):
        falselspci.return_value = '01:00.0 "VGA compatible controller [0300]" "NVIDIA Corporation [10de]" "GA104 [GeForce RTX 3070 LHR] [2484]" -ra1 "Gigabyte Technology Co., Ltd [1458]" "Device [4082]"'
        
        matches = self.probe.find_needed_packages("arch")
        self.assertTrue(len(matches) > 0)
        all_pkgs = []
        for m in matches:
            all_pkgs.extend(m["packages"])
        self.assertIn("nvidia", all_pkgs)

if __name__ == "__main__":
    unittest.main()
