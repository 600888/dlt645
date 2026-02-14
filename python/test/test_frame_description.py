
import unittest
import struct
import sys
import os
from unittest.mock import MagicMock

# Mock serial module before importing anything that might use it
sys.modules['serial'] = MagicMock()

# Ensure src is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.protocol.frame import Frame
from src.model.types.dlt645_type import CtrlCode, ErrorCode
from src.model import init_energy_def
from src.model.data.define import DIMap
# We need to make sure DIMap is populated. 
# src.model.__init__ calls init_energy_def(EnergyTypes), but we might need to trigger it.
import src.model 

class TestFrameDescription(unittest.TestCase):
    def test_read_data_request(self):
        # 0x00010000: (当前)正向有功总电能
        # DI is little endian: 00 00 01 00
        di_val = 0x00010000
        di_bytes = struct.pack("<I", di_val)
        
        frame = Frame(ctrl_code=CtrlCode.ReadData, data=bytearray(di_bytes))
        
        desc = frame.description
        print(f"Read Request Desc: {desc}")
        self.assertIn("读取", desc)
        self.assertIn("正向有功总电能", desc)
        self.assertIn("(DI=00010000)", desc) # Check format

    def test_read_data_response(self):
        di_val = 0x00010000
        di_bytes = struct.pack("<I", di_val)
        # Mocking some data return
        data = bytearray(di_bytes) + bytearray([0x12, 0x34, 0x56, 0x78]) 
        
        frame = Frame(ctrl_code=CtrlCode.ReadData | 0x80, data=data)
        desc = frame.description
        print(f"Read Response Desc: {desc}")
        self.assertIn("读取", desc)
        self.assertIn("响应", desc)
        self.assertIn("正向有功总电能", desc)
        self.assertIn("(DI=00010000)", desc)

    def test_write_data_request(self):
        di_val = 0x04000401 # Check a parameter DI
        di_bytes = struct.pack("<I", di_val)
        data = bytearray(di_bytes) + bytearray([0x11, 0x11, 0x11, 0x11]) # Password + ...
        
        frame = Frame(ctrl_code=CtrlCode.WriteData, data=data)
        desc = frame.description
        print(f"Write Request Desc: {desc}")
        self.assertIn("写入", desc)
        self.assertIn("(DI=04000401)", desc)

    def test_error_response(self):
        # CtrlCode.ReadData | 0xC0 = Error response for ReadData
        # Error bit 0x01 = Other Error? No, 0x01 is often specific.
        # ErrorCode.RequestDataEmpty = 0x01 ? Let's ignore exact match and check string.
        
        frame = Frame(ctrl_code=CtrlCode.ReadData | 0xC0, data=bytearray([0x01]))
        desc = frame.description
        print(f"Error Response Desc: {desc}")
        self.assertIn("读取数据失败响应", desc)

    def test_unknown_di(self):
        di_val = 0xFFFFFFFF
        di_bytes = struct.pack("<I", di_val)
        frame = Frame(ctrl_code=CtrlCode.ReadData, data=bytearray(di_bytes))
        desc = frame.description
        print(f"Unknown DI Desc: {desc}")
        self.assertIn("未知数据项(DI=FFFFFFFF)", desc)

if __name__ == '__main__':
    unittest.main()
