#include "dlt645/protocol/protocol.h"
#include "dlt645/transport/client/client_api.h"
#include "dlt645/transport/server/server_api.h"
#include "log/log_init.hpp"
#include <array>
#include <atomic>
#include <chrono>
#include <exception>
#include <iostream>
#include <stdexcept>
#include <thread>
#include <vector>

namespace {
    using boost::asio::ip::tcp;
    using dlt645::protocol::Frame;
    constexpr std::array<uint8_t, 6> address { 0x12, 0x34, 0x56, 0x78, 0x10, 0x12 };

    void check(bool value, const char* message)
    {
        if (!value)
            throw std::runtime_error(message);
    }

    class EchoHandler : public dlt645::transport::server::ConnectionHandler {
    public:
        std::vector<uint8_t> handleRequest(const Frame& frame) override
        {
            ++requests;
            return Frame::buildFrame(frame.addr, frame.ctrlCode | 0x80, frame.data);
        }
        void onConnectionClosed() override {}
        std::atomic<int> requests { 0 };
    };

    void testServerStream()
    {
        boost::asio::io_context context;
        tcp::acceptor reserve(context, tcp::endpoint(boost::asio::ip::make_address("127.0.0.1"), 0));
        const auto port = reserve.local_endpoint().port();
        reserve.close();

        dlt645::transport::server::TcpServer server;
        dlt645::transport::server::TcpServerConfig config;
        config.ip = "127.0.0.1";
        config.port = port;
        check(server.configure(config), "configure server");
        auto handler = std::make_shared<EchoHandler>();
        server.setConnectionHandler(handler);
        check(server.start(), "start server");

        tcp::socket socket(context);
        socket.connect(tcp::endpoint(boost::asio::ip::make_address("127.0.0.1"), port));
        const auto request = Frame::buildFrame(address, 0x11, { 0, 0, 0, 0 });
        boost::asio::write(socket, boost::asio::buffer(request.data(), 8));
        std::this_thread::sleep_for(std::chrono::milliseconds(20));
        std::vector<uint8_t> rest(request.begin() + 8, request.end());
        rest.insert(rest.end(), request.begin(), request.end());
        boost::asio::write(socket, boost::asio::buffer(rest));

        socket.non_blocking(true);
        dlt645::protocol::FrameStreamDecoder decoder;
        std::array<uint8_t, 256> bytes {};
        int responses = 0;
        const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(2);
        while (responses < 2 && std::chrono::steady_clock::now() < deadline) {
            boost::system::error_code error;
            const auto size = socket.read_some(boost::asio::buffer(bytes), error);
            if (!error) {
                decoder.append(bytes.data(), size);
                while (decoder.nextFrame())
                    ++responses;
            } else if (error != boost::asio::error::would_block) {
                throw boost::system::system_error(error);
            } else {
                std::this_thread::sleep_for(std::chrono::milliseconds(5));
            }
        }
        check(responses == 2 && handler->requests == 2, "server handles split and coalesced frames");
        socket.close();
        server.stop();
    }

    void testClientFragmentedResponse()
    {
        boost::asio::io_context context;
        tcp::acceptor acceptor(context, tcp::endpoint(boost::asio::ip::make_address("127.0.0.1"), 0));
        const auto port = acceptor.local_endpoint().port();
        std::exception_ptr serverError;
        std::thread peer([&] {
            try {
                tcp::socket socket(context);
                acceptor.accept(socket);
                std::array<uint8_t, 128> bytes {};
                check(socket.read_some(boost::asio::buffer(bytes)) > 0, "client request received");
                const auto response = Frame::buildFrame(address, 0x91, { 0, 0, 0, 0, 0, 0, 0, 0 });
                auto damaged = response;
                damaged[damaged.size() - 2] ^= 1;
                boost::asio::write(socket, boost::asio::buffer(damaged));
                boost::asio::write(socket, boost::asio::buffer(response.data(), 7));
                std::this_thread::sleep_for(std::chrono::milliseconds(20));
                boost::asio::write(socket, boost::asio::buffer(response.data() + 7, response.size() - 7));
            } catch (...) {
                serverError = std::current_exception();
            }
        });

        try {
            dlt645::transport::client::TcpClient client;
            dlt645::transport::client::TcpClientConfig config;
            config.ip = "127.0.0.1";
            config.port = port;
            config.timeout = std::chrono::seconds(2);
            check(client.configure(config) && client.connect(), "client connects");
            const auto request = Frame::buildFrame(address, 0x11, { 0, 0, 0, 0 });
            const auto response = client.sendRequest(request);
            check(Frame::deserialize(response) != nullptr, "client reassembles response");
            client.disconnect();
        } catch (...) {
            peer.join();
            throw;
        }
        peer.join();
        if (serverError)
            std::rethrow_exception(serverError);
    }

    void testClientTimeoutRecovery()
    {
        boost::asio::io_context context;
        tcp::acceptor acceptor(context, tcp::endpoint(boost::asio::ip::make_address("127.0.0.1"), 0));
        const auto port = acceptor.local_endpoint().port();
        std::exception_ptr serverError;
        std::thread peer([&] {
            try {
                tcp::socket socket(context);
                acceptor.accept(socket);
                std::array<uint8_t, 128> bytes {};
                check(socket.read_some(boost::asio::buffer(bytes)) > 0, "first request received");
                const auto response = Frame::buildFrame(address, 0x91, { 0, 0, 0, 0, 0, 0, 0, 0 });
                boost::asio::write(socket, boost::asio::buffer(response.data(), 7));
                std::this_thread::sleep_for(std::chrono::milliseconds(400));
                check(socket.read_some(boost::asio::buffer(bytes)) > 0, "second request received");
                boost::asio::write(socket, boost::asio::buffer(response));
            } catch (...) {
                serverError = std::current_exception();
            }
        });

        try {
            dlt645::transport::client::TcpClient client;
            dlt645::transport::client::TcpClientConfig config;
            config.ip = "127.0.0.1";
            config.port = port;
            config.timeout = std::chrono::milliseconds(300);
            check(client.configure(config) && client.connect(), "client connects for timeout test");
            const auto request = Frame::buildFrame(address, 0x11, { 0, 0, 0, 0 });
            check(client.sendRequest(request).empty(), "partial response times out");
            check(Frame::deserialize(client.sendRequest(request)) != nullptr,
                  "next request succeeds after partial response timeout");
            client.disconnect();
        } catch (...) {
            peer.join();
            throw;
        }
        peer.join();
        if (serverError)
            std::rethrow_exception(serverError);
    }
} // namespace

int main()
{
    try {
        LogInitializer logger("dlt645_transport_test", LV::info, false);
        testServerStream();
        testClientFragmentedResponse();
        testClientTimeoutRecovery();
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
