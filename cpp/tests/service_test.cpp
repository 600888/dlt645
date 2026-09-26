#include "dlt645/service/client_service.h"
#include "dlt645/service/server_service.h"
#include "log/log_init.hpp"
#include <array>
#include <chrono>
#include <ctime>
#include <future>
#include <iostream>
#include <stdexcept>

namespace {
    void check(bool value, const char* message)
    {
        if (!value)
            throw std::runtime_error(message);
    }

    class DummyServer : public dlt645::transport::server::Server {
    public:
        bool start() override { return true; }
        void stop() override {}
        bool isRunning() const override { return true; }
        void setConnectionHandler(std::shared_ptr<dlt645::transport::server::ConnectionHandler>) override {}
    };

    class LoopbackConnection : public dlt645::transport::client::Connection {
    public:
        explicit LoopbackConnection(std::shared_ptr<dlt645::service::ServerService> server)
            : server_(std::move(server))
        {
        }

        std::future<bool> connectAsync() override { return ready(true); }
        std::future<void> disconnectAsync() override
        {
            connected_ = false;
            std::promise<void> promise;
            promise.set_value();
            return promise.get_future();
        }
        std::future<std::vector<uint8_t>> sendRequestAsync(const std::vector<uint8_t>& raw) override
        {
            auto request = dlt645::protocol::Frame::deserialize(raw);
            check(static_cast<bool>(request), "request frame");
            lastRequest = *request;
            return ready(server_->handleRequest(*request));
        }
        std::future<bool> sendOnlyAsync(const std::vector<uint8_t>& raw) override
        {
            auto request = dlt645::protocol::Frame::deserialize(raw);
            check(static_cast<bool>(request), "broadcast frame");
            lastRequest = *request;
            check(server_->handleRequest(*request).empty(), "broadcast must not have a response");
            return ready(true);
        }
        bool isConnected() const override { return connected_; }
        void setTimeout(std::chrono::milliseconds) override {}
        dlt645::protocol::Frame lastRequest;

    private:
        template <typename T>
        static std::future<T> ready(T value)
        {
            std::promise<T> promise;
            promise.set_value(std::move(value));
            return promise.get_future();
        }
        std::shared_ptr<dlt645::service::ServerService> server_;
        bool connected_ = true;
    };
} // namespace

int main()
{
    try {
        LogInitializer logger("dlt645_service_test", LV::info, false);
        const std::array<uint8_t, 6> oldAddress { 0x12, 0x34, 0x56, 0x78, 0x10, 0x12 };
        const std::array<uint8_t, 6> newAddress { 0x12, 0x34, 0x56, 0x78, 0x10, 0x13 };
        auto server = std::make_shared<dlt645::service::ServerService>(std::make_shared<DummyServer>(), oldAddress);
        auto transport = std::make_shared<LoopbackConnection>(server);
        dlt645::service::ClientService client(transport);

        check(static_cast<bool>(client.readAddress()), "read address response");
        check(transport->lastRequest.addr == std::array<uint8_t, 6> { 0xAA, 0xAA, 0xAA, 0xAA, 0xAA, 0xAA },
              "read address uses special address");
        check(static_cast<bool>(client.writeAddress(newAddress)), "write address response");
        check(transport->lastRequest.data == std::vector<uint8_t>(newAddress.begin(), newAddress.end()),
              "write address data contains only the new address");
        check(server->getAddress() == newAddress, "server address changed");
        const std::array<uint8_t, 4> originalPassword { 0, 0, 0, 0 };
        const std::array<uint8_t, 4> changedPassword { 0, 0x12, 0x34, 0x56 };
        check(client.changePassword(originalPassword, changedPassword), "change password response");
        check(transport->lastRequest.data.size() == 12 && transport->lastRequest.data[0] == 0x00
                  && transport->lastRequest.data[1] == 0x0C && server->getPassword() == changedPassword,
              "change password request includes DI and updates meter");
        check(!client.changePassword(originalPassword, changedPassword), "wrong old password rejected");
        const std::array<uint8_t, 4> freezeTime { 0x99, 0x99, 0x99, 0x99 };
        check(static_cast<bool>(client.freeze(freezeTime)), "point-to-point freeze response");
        check(server->getLastFreezeTime() == freezeTime, "freeze time stored");
        check(static_cast<bool>(client.freeze(freezeTime, true)), "broadcast freeze sent without response");
        check(transport->lastRequest.addr == std::array<uint8_t, 6> { 0x99, 0x99, 0x99, 0x99, 0x99, 0x99 },
              "broadcast freeze address");
        check(static_cast<bool>(client.changeBaudRate(19200)) && server->getBaudRate() == 19200,
              "baud rate feature acknowledged");
        check(!client.changeBaudRate(300), "unsupported baud rate rejected");

        check(server->set03(0x03110000, { "123456" }), "set single event field");
        auto event = client.read03(0x03110000);
        check(event && event->fields.size() == 1 && event->fields[0].value == "123456", "read single event field");
        check(server->set03(0x03010000, { "000001,000002", "000003,000004", "000005,000006" }), "set paired event fields");
        auto pairedEvent = client.read03(0x03010000);
        check(pairedEvent && pairedEvent->fields.size() == 3 && pairedEvent->fields[0].value == "000001,000002"
                  && pairedEvent->fields[2].value == "000005,000006",
              "read paired event fields in definition order");
        const auto pairedRead = dlt645::protocol::Frame::deserialize(server->handleRequest(*dlt645::protocol::Frame::deserialize(
            dlt645::protocol::Frame::buildFrame(newAddress, dlt645::model::CTRL_READ_DATA, { 0x00, 0x00, 0x01, 0x03 }))));
        check(pairedRead && pairedRead->data.size() >= 10
                  && std::vector<uint8_t>(pairedRead->data.begin() + 4, pairedRead->data.begin() + 10)
                      == std::vector<uint8_t>({ 0x02, 0x00, 0x00, 0x01, 0x00, 0x00 }),
              "paired event fields use Python wire order");
        check(transport->lastRequest.data.size() == 4, "event read request contains DI");

        check(server->set04(0x04000101, { "26092606" }), "set scalar parameter");
        auto parameter = client.read04(0x04000101);
        check(parameter && parameter->fields.size() == 1 && parameter->fields[0].value == "26092606", "read scalar parameter");
        check(client.write04(0x04000102, "123456"), "write scalar parameter");
        check(transport->lastRequest.data.size() == 15 && transport->lastRequest.data[12] == 0x56
                  && server->getDataItem(0x04000102)->fields[0].value == "123456",
              "write uses password, operator code and little-endian BCD");
        check(!client.write04(0x04000102, "12XX56"), "invalid parameter digits rejected");
        std::vector<std::string> periods(14, "001200");
        periods[13] = "235959";
        check(server->set04(0x04010001, periods), "set parameter period table");
        auto table = client.read04(0x04010001);
        check(table && table->fields.size() == periods.size() && table->fields[13].value == "235959",
              "read full parameter period table");
        periods[0] = "010203";
        check(client.write04(0x04010001, periods), "write parameter period table");
        check(server->getDataItem(0x04010001)->fields[0].value == "010203", "period table write updates first field");

        const auto wrongPasswordWrite = dlt645::protocol::Frame::deserialize(dlt645::protocol::Frame::buildFrame(
            newAddress, dlt645::model::CTRL_WRITE_DATA, { 0x02, 0x01, 0x00, 0x04, 0, 0, 0, 0, 0, 0, 0, 0, 0x56, 0x34, 0x12 }));
        const auto authError = dlt645::protocol::Frame::deserialize(server->handleRequest(*wrongPasswordWrite));
        check(authError && authError->ctrlCode == 0xD4 && authError->data == std::vector<uint8_t> { 0x04 },
              "parameter write checks password");
        const auto shortWrite = dlt645::protocol::Frame::deserialize(dlt645::protocol::Frame::buildFrame(
            newAddress, dlt645::model::CTRL_WRITE_DATA, { 0x02, 0x01, 0x00, 0x04, 0, 0x12, 0x34, 0x56, 0, 0, 0, 0, 0x56, 0x34 }));
        const auto lengthError = dlt645::protocol::Frame::deserialize(server->handleRequest(*shortWrite));
        check(lengthError && lengthError->ctrlCode == 0xD4 && lengthError->data == std::vector<uint8_t> { 0x02 }
                  && server->getDataItem(0x04000102)->fields[0].value == "123456",
              "short parameter write leaves stored value intact");

        std::tm local {};
        local.tm_year = 125;
        local.tm_mon = 10;
        local.tm_mday = 2;
        local.tm_hour = 12;
        local.tm_min = 34;
        local.tm_sec = 56;
        const auto time = std::chrono::system_clock::from_time_t(std::mktime(&local));
        check(client.broadcastTimeSync(time), "broadcast send");
        check(transport->lastRequest.addr == std::array<uint8_t, 6> { 0x99, 0x99, 0x99, 0x99, 0x99, 0x99 },
              "time sync uses broadcast address");
        check(transport->lastRequest.data == std::vector<uint8_t>({ 0x25, 0x11, 0x02, 0x12, 0x34, 0x56 }),
              "time sync includes seconds");
        check(server->getTime() && *server->getTime() == time, "server clock updated");

        auto secondServer = std::make_shared<dlt645::service::ServerService>(std::make_shared<DummyServer>(), oldAddress);
        check(server->set00(0x00000000, 12.5f), "first meter value");
        check(secondServer->set00(0x00000000, 37.5f), "second meter value");
        check(std::get<float>(server->getDataItem(0x00000000)->value) == 12.5f, "first meter keeps its value");
        check(std::get<float>(secondServer->getDataItem(0x00000000)->value) == 37.5f, "second meter keeps its value");
        const auto unknownRead = dlt645::protocol::Frame::deserialize(
            dlt645::protocol::Frame::buildFrame(newAddress, 0x11, { 0xFF, 0xFF, 0xFF, 0x00 }));
        const auto error = dlt645::protocol::Frame::deserialize(server->handleRequest(*unknownRead));
        check(error && error->ctrlCode == 0xD1 && error->data == std::vector<uint8_t> { 0x02 },
              "unknown DI returns protocol error frame");
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
