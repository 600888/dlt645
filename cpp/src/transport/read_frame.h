#ifndef DLT645_TRANSPORT_READ_FRAME_H
#define DLT645_TRANSPORT_READ_FRAME_H

#include <array>
#include <chrono>
#include <future>
#include <memory>
#include <vector>
#include <boost/asio.hpp>
#include "dlt645/protocol/protocol.h"

namespace dlt645::transport {

    // Keeps reading until a complete frame arrives or the request times out.
    template <typename Stream>
    class FrameReadOperation : public std::enable_shared_from_this<FrameReadOperation<Stream>> {
    public:
        FrameReadOperation(Stream& stream,
                           protocol::FrameStreamDecoder& decoder,
                           boost::asio::io_context& context,
                           std::chrono::milliseconds timeout,
                           std::shared_ptr<std::promise<std::vector<uint8_t>>> promise)
            : stream_(stream)
            , decoder_(decoder)
            , timer_(context)
            , timeout_(timeout)
            , promise_(std::move(promise))
        {
        }

        void start()
        {
            if (auto frame = decoder_.nextFrame()) {
                finish(frame->serialize());
                return;
            }
            timer_.expires_after(timeout_);
            auto self = this->shared_from_this();
            timer_.async_wait([self](const boost::system::error_code& error) {
                if (!error && !self->done_) {
                    self->decoder_.clear();
                    self->finish({});
                    boost::system::error_code ignored;
                    self->stream_.cancel(ignored);
                }
            });
            readMore();
        }

    private:
        void readMore()
        {
            auto self = this->shared_from_this();
            stream_.async_read_some(boost::asio::buffer(bytes_), [self](const boost::system::error_code& error, size_t size) {
                if (self->done_)
                    return;
                if (error) {
                    self->decoder_.clear();
                    self->finish({});
                    return;
                }
                self->decoder_.append(self->bytes_.data(), size);
                if (auto frame = self->decoder_.nextFrame()) {
                    self->finish(frame->serialize());
                } else {
                    self->readMore();
                }
            });
        }

        void finish(std::vector<uint8_t> result)
        {
            if (done_)
                return;
            done_ = true;
            timer_.cancel();
            promise_->set_value(std::move(result));
        }

        Stream& stream_;
        protocol::FrameStreamDecoder& decoder_;
        boost::asio::steady_timer timer_;
        std::chrono::milliseconds timeout_;
        std::shared_ptr<std::promise<std::vector<uint8_t>>> promise_;
        std::array<uint8_t, 1024> bytes_ {};
        bool done_ = false;
    };

} // namespace dlt645::transport

#endif
