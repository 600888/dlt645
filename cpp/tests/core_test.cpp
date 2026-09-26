#include "dlt645/common/transform.h"
#include "dlt645/model/data_item.h"
#include "dlt645/protocol/protocol.h"
#include "log/log_init.hpp"
#include <array>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
void check(bool condition, const char* message)
{
    if (!condition) throw std::runtime_error(message);
}
} // namespace

int main()
{
    try {
        LogInitializer logInitializer("dlt645_core_test", LV::info, false);
        check(spdlog::get("dlt645_core_test") != nullptr, "logger without configuration file");
        using dlt645::protocol::Frame;
        const std::array<uint8_t, 6> address{{1, 2, 3, 4, 5, 6}};
        const std::vector<uint8_t> data{0x00, 0x33, 0xFE};
        const auto raw = Frame::buildFrame(address, 0x11, data);
        auto frame = Frame::deserialize(raw);
        check(frame && frame->addr == address && frame->data == data, "frame round trip");
        check(frame->serialize() == raw, "frame reserialization with preamble");
        dlt645::protocol::FrameStreamDecoder stream;
        stream.append(raw.data(), 7);
        check(!stream.nextFrame(), "fragmented frame is retained");
        stream.append(raw.data() + 7, raw.size() - 7);
        auto splitFrame = stream.nextFrame();
        check(splitFrame && splitFrame->data == data, "fragmented frame is reassembled");
        check(!stream.nextFrame(), "stream is drained after one frame");
        std::vector<uint8_t> together{0x01, 0x68, 0x02};
        together.insert(together.end(), raw.begin(), raw.end());
        together.insert(together.end(), raw.begin(), raw.end());
        stream.append(together.data(), together.size());
        check(stream.nextFrame() && stream.nextFrame() && !stream.nextFrame(),
              "noise and coalesced frames");
        auto corrupt = raw;
        corrupt[corrupt.size() - 2] ^= 1;
        check(!Frame::deserialize(corrupt), "checksum rejection");
        corrupt.insert(corrupt.end(), raw.begin(), raw.end());
        stream.append(corrupt.data(), corrupt.size());
        check(stream.nextFrame() && !stream.nextFrame(), "stream resynchronizes after checksum error");
        check(dlt645::common::bytesToHexString(Frame::buildFrame(
                  {0xAA, 0xAA, 0xAA, 0xAA, 0xAA, 0xAA}, 0x13, {}))
                  == "FE FE FE FE 68 AA AA AA AA AA AA 68 13 00 DF 16",
              "Python read-address wire vector");
        check(dlt645::common::bytesToHexString(Frame::buildFrame(
                  {0x12, 0x34, 0x56, 0x78, 0x10, 0x12}, 0x15,
                  {0x12, 0x34, 0x56, 0x78, 0x10, 0x13}))
                  == "FE FE FE FE 68 12 34 56 78 10 12 68 15 06 45 67 89 AB 43 46 8A 16",
              "Python write-address wire vector");
        check(dlt645::common::bytesToHexString(Frame::buildFrame(
                  {0x99, 0x99, 0x99, 0x99, 0x99, 0x99}, 0x08,
                  {0x25, 0x11, 0x02, 0x12, 0x34, 0x56}))
                  == "FE FE FE FE 68 99 99 99 99 99 99 68 08 06 58 44 35 45 67 89 7A 16",
              "Python time-sync wire vector");
        corrupt = raw;
        corrupt.pop_back();
        check(!Frame::deserialize(corrupt), "truncated frame rejection");
        bool oversized = false;
        try { Frame::buildFrame(address, 0x11, std::vector<uint8_t>(256)); }
        catch (const std::length_error&) { oversized = true; }
        check(oversized, "oversized data rejection");

        using namespace dlt645::common;
        const std::vector<uint8_t> bcd{0x12, 0x34, 0x56, 0x78};
        check(std::fabs(bcdToFloat(bcd, "XXXXXX.XX", false) - 123456.78f) < 0.02f, "BCD float");
        check(std::fabs(bcdToFloat(floatToBcd(-1.23f, "XXXX.XX"), "XXXX.XX", true) + 1.23f) < 0.01f,
              "negative BCD float round trip");
        check(floatToBcd(1.23f, "XXXX.XX").size() == 3, "BCD format byte count");
        check(intToBCD(1234, 4, true) == std::vector<uint8_t>({0x34, 0x12, 0x00, 0x00}), "padded little endian BCD");
        const std::array<uint8_t, 3> bytes{{0x01, 0x23, 0x45}};
        check(bytesToHexString(bytes) == "01 23 45", "array hex");
        check(bytesToIntLittleEndian<uint32_t>(bytes) == 0x452301u, "array little endian");
        check(calculateCRC(bytes) == calculateCRC(std::vector<uint8_t>(bytes.begin(), bytes.end())), "array CRC");
        check(calculateLRC(bytes) == calculateLRC(std::vector<uint8_t>(bytes.begin(), bytes.end())), "array LRC");
        const auto now = std::chrono::system_clock::from_time_t(1735689600);
        const auto timeBcd = timeToBcd(now);
        check(std::chrono::system_clock::to_time_t(bcdToTime({timeBcd.begin(), timeBcd.end()})) == 1735689600,
              "BCD time round trip");
        bool shortTime = false;
        try { bcdToTime({0x20}); }
        catch (const std::invalid_argument&) { shortTime = true; }
        check(shortTime, "short BCD time rejection");

        dlt645::model::DataItemManager manager;
        check(manager.getDataItems().size() == 20286, "static data item count");
        const auto energy = manager.getDataItem(0x00000000u);
        const auto demand = manager.getDataItem(0x01010000u);
        const auto variable = manager.getDataItem(0x02010100u);
        check(energy && energy->name == "（当前）组合有功总电能" && energy->dataFormat == "XXXXXX.XX",
              "static energy definition");
        check(demand && demand->name == "（当前）正向有功总最大需量" && demand->dataFormat == "XX.XXXX",
              "static demand definition");
        check(variable && variable->name == "A相电压" && variable->dataFormat == "XXX.X",
              "static variable definition");
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
