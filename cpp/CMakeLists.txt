cmake_minimum_required(VERSION 3.20)
project(dlt645 VERSION 1.0.0 LANGUAGES CXX)
include(CTest)

# 输出留在调用者指定的构建目录
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/bin)
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/lib)
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/lib)

# 项目代码使用 C++17
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# 设置编译选项
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU")
    add_compile_options(-Wall -Wextra -pedantic -Werror)
elseif(CMAKE_CXX_COMPILER_ID MATCHES "MSVC")
    add_compile_options(/W4 /WX /utf-8)
endif()

# Boost 可通过 BOOST_ROOT 或 CMAKE_PREFIX_PATH 指定
find_package(Boost 1.83.0 REQUIRED)
find_package(Threads REQUIRED)

# 自动查找所有cpp文件
file(GLOB_RECURSE SOURCES CONFIGURE_DEPENDS "src/*.cpp")

# 定义库
add_library(dlt645
    ${SOURCES}
)

# 添加头文件目录到目标
target_include_directories(dlt645
    PUBLIC $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
           $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/third>
           $<INSTALL_INTERFACE:include>
    PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/src
)

# 添加编译定义
target_compile_definitions(dlt645 PRIVATE BOOST_ASIO_NO_DEPRECATED)

# 链接库
target_link_libraries(dlt645 PUBLIC Threads::Threads Boost::headers)

# Windows平台需要链接的网络库
if(WIN32)
    target_link_libraries(dlt645 PRIVATE ws2_32 mswsock)
endif()

# 添加示例目录
add_subdirectory(example)
if(BUILD_TESTING)
    add_subdirectory(tests)
endif()

# 安装规则
install(TARGETS dlt645
    ARCHIVE DESTINATION lib
    LIBRARY DESTINATION lib
    RUNTIME DESTINATION bin
)

install(DIRECTORY include/ DESTINATION include)
install(DIRECTORY third/spdlog DESTINATION include)
