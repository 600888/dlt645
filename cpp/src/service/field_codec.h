#pragma once

#include "dlt645/model/data_item.h"
#include <algorithm>
#include <cctype>
#include <cstdint>
#include <string>
#include <vector>

namespace dlt645::service::detail {

    inline size_t fieldDigits(const std::string& format)
    {
        return static_cast<size_t>(
            std::count_if(format.begin(), format.end(), [](unsigned char c) { return std::isalnum(c) != 0; }));
    }

    inline bool encodePart(const std::string& format, const std::string& value, std::vector<uint8_t>& out)
    {
        const size_t digits = fieldDigits(format);
        if (digits == 0 || value.size() != digits
            || !std::all_of(value.begin(), value.end(), [](unsigned char c) { return std::isdigit(c) != 0; }))
            return false;
        const std::string padded = (digits % 2 ? "0" : "") + value;
        for (size_t i = padded.size(); i > 0; i -= 2) {
            out.push_back(static_cast<uint8_t>(((padded[i - 2] - '0') << 4) | (padded[i - 1] - '0')));
        }
        return true;
    }

    inline bool decodePart(const std::string& format, const std::vector<uint8_t>& data, size_t& offset, std::string& value)
    {
        const size_t digits = fieldDigits(format);
        const size_t bytes = (digits + 1) / 2;
        if (digits == 0 || offset + bytes > data.size())
            return false;
        value.clear();
        for (size_t i = offset + bytes; i > offset; --i) {
            const auto byte = data[i - 1];
            if ((byte >> 4) > 9 || (byte & 0x0f) > 9)
                return false;
            value.push_back(static_cast<char>('0' + (byte >> 4)));
            value.push_back(static_cast<char>('0' + (byte & 0x0f)));
        }
        if (digits % 2)
            value.erase(value.begin());
        offset += bytes;
        return true;
    }

    inline bool encodeFields(const std::vector<model::DataField>& fields, std::vector<uint8_t>& out)
    {
        for (const auto& field : fields) {
            const auto comma = field.dataFormat.find(',');
            if (comma == std::string::npos) {
                const auto value = field.value.empty() ? std::string(fieldDigits(field.dataFormat), '0') : field.value;
                if (!encodePart(field.dataFormat, value, out))
                    return false;
            } else {
                const auto value = field.value.empty() ? std::string(fieldDigits(field.dataFormat.substr(0, comma)), '0') + ","
                        + std::string(fieldDigits(field.dataFormat.substr(comma + 1)), '0')
                                                       : field.value;
                const auto valueComma = value.find(',');
                if (valueComma == std::string::npos)
                    return false;
                // Python writes paired event values in reverse order on the wire.
                if (!encodePart(field.dataFormat.substr(comma + 1), value.substr(valueComma + 1), out)
                    || !encodePart(field.dataFormat.substr(0, comma), value.substr(0, valueComma), out))
                    return false;
            }
        }
        return true;
    }

    inline bool decodeFields(std::vector<model::DataField>& fields, const std::vector<uint8_t>& data, size_t offset)
    {
        for (auto& field : fields) {
            const auto comma = field.dataFormat.find(',');
            if (comma == std::string::npos) {
                if (!decodePart(field.dataFormat, data, offset, field.value))
                    return false;
            } else {
                std::string second, first;
                if (!decodePart(field.dataFormat.substr(comma + 1), data, offset, second)
                    || !decodePart(field.dataFormat.substr(0, comma), data, offset, first))
                    return false;
                field.value = first + "," + second;
            }
        }
        return offset == data.size();
    }

} // namespace dlt645::service::detail
