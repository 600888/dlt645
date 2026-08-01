import unittest

from dlt645.model.types.dlt645_type import CtrlCode
from dlt645.protocol.frame import FRAME_END_BYTE, FRAME_START_BYTE, Frame
from dlt645.protocol.protocol import DLT645Protocol


class TestProtocolCore(unittest.TestCase):
    def test_preamble_is_not_included_in_checksum(self):
        address = bytes.fromhex("12 10 78 56 34 12")
        without_preamble = DLT645Protocol.build_frame(
            address, CtrlCode.ReadData, b"\x00\x00\x00\x00", preamble_count=0
        )
        with_preamble = DLT645Protocol.build_frame(
            address, CtrlCode.ReadData, b"\x00\x00\x00\x00", preamble_count=4
        )

        self.assertEqual(with_preamble[4:], without_preamble)
        self.assertEqual(without_preamble[-2], sum(without_preamble[:-2]) & 0xFF)

    def test_round_trip_updates_canonical_checksum_field(self):
        raw = DLT645Protocol.build_frame(
            bytes.fromhex("06 05 04 03 02 01"), CtrlCode.ReadAddress, b""
        )

        remaining, frame = DLT645Protocol.deserialize_with_remaining(raw)

        self.assertEqual(remaining, b"")
        self.assertIsNotNone(frame)
        assert frame is not None
        self.assertEqual(frame.check_sum, raw[-2])
        self.assertEqual(DLT645Protocol.serialize(frame), bytes(raw))

    def test_parser_resynchronizes_after_corrupt_frame(self):
        corrupt = DLT645Protocol.build_frame(bytes(6), CtrlCode.ReadAddress, b"")
        corrupt[-2] ^= 0x01
        valid = DLT645Protocol.build_frame(
            bytes.fromhex("06 05 04 03 02 01"), CtrlCode.ReadAddress, b""
        )

        remaining, frame = DLT645Protocol.deserialize_with_remaining(
            b"noise" + bytes(corrupt) + bytes(valid) + b"tail"
        )

        self.assertIsNotNone(frame)
        assert frame is not None
        self.assertEqual(frame.addr, bytearray.fromhex("06 05 04 03 02 01"))
        self.assertEqual(remaining, b"tail")

    def test_parser_preserves_incomplete_candidate(self):
        raw = DLT645Protocol.build_frame(bytes(6), CtrlCode.ReadAddress, b"")
        partial = b"discard" + bytes(raw[:9])

        remaining, frame = DLT645Protocol.deserialize_with_remaining(partial)

        self.assertIsNone(frame)
        self.assertEqual(remaining, bytes(raw[:9]))

    def test_frame_defaults_are_not_shared(self):
        first = Frame()
        second = Frame()
        first.addr[0] = 1
        first.data.append(2)
        first.preamble.append(0xFE)

        self.assertEqual(second.addr, bytearray(6))
        self.assertEqual(second.data, bytearray())
        self.assertEqual(second.preamble, bytearray())

    def test_serialize_rejects_invalid_frame_shape(self):
        frame = Frame(
            preamble=b"\xFE",
            start_flag=FRAME_START_BYTE,
            addr=b"short",
            data=b"",
            end_flag=FRAME_END_BYTE,
        )
        with self.assertRaises(ValueError):
            DLT645Protocol.serialize(frame)


if __name__ == "__main__":
    unittest.main()
