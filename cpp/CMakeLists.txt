cmake_minimum_required(VERSION 3.20)
project(dlt645 VERSION 1.0.0 LANGUAGES CXX)

# 设置构建目录到cpp文件夹下
set(CMAKE_BINARY_DIR ${CMAKE_SOURCE_DIR}/build)
set(EXECUTABLE_OUTPUT_PATH ${CMAKE_BINARY_DIR}/bin)
set(LIBRARY_OUTPUT_PATH ${CMAKE_BINARY_DIR}/lib)

# 设置C++20标准
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# 设置编译选项
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU")
    add_compile_options(-Wall -Wextra -pedantic -Werror)
elseif(CMAKE_CXX_COMPILER_ID MATCHES "MSVC")
    add_compile_options(/W4 /WX)
endif()

# 设置 Boost 的路径
if(WIN32)
    set(BOOST_ROOT "E:\\boost_1_83_0")  # 设置 Boost 根路径
    set(Boost_USE_STATIC_LIBS ON)
    set(Boost_NO_SYSTEM_PATHS ON)
    set(Boost_ARCHITECTURE "-x64")
    set(Boost_INCLUDE_DIR "E:\\boost_1_83_0")  # 设置 Boost 的 include 目录
    set(Boost_LIBRARY_DIR "E:\\boost_1_83_0\\stage\\lib")  # 设置 Boost 的库目录
else()
    set(Boost_USE_STATIC_LIBS ON)
    # Linux平台让系统自动查找Boost
endif()
# 查找Boost库
find_package(Boost 1.83.0 REQUIRED)

# 包含头文件目录
include_directories(
    ${CMAKE_SOURCE_DIR}/third
    ${CMAKE_SOURCE_DIR}/include
    ${CMAKE_SOURCE_DIR}/src
    ${Boost_INCLUDE_DIRS}
)

# 自动查找所有cpp文件
file(GLOB_RECURSE SOURCES "src/*.cpp")

# 定义库
add_library(dlt645
    ${SOURCES}
)

# 添加头文件目录到目标
target_include_directories(dlt645
    PRIVATE ${CMAKE_SOURCE_DIR}/include
)

# 添加编译定义
target_compile_definitions(dlt645 PRIVATE BOOST_ASIO_NO_DEPRECATED)

# 链接库
target_link_libraries(dlt645 
    PRIVATE ${CMAKE_THREAD_LIBS_INIT}   # 链接线程库
    PRIVATE ${Boost_LIBRARIES}
)

# Windows平台需要链接的网络库
if(WIN32)
    target_link_libraries(dlt645 PRIVATE ws2_32 mswsock)
endif()

# 添加示例目录
add_subdirectory(example)

# 拷贝config文件夹
file(COPY ${CMAKE_SOURCE_DIR}/config DESTINATION ${CMAKE_BINARY_DIR})

# 安装规则
install(TARGETS dlt645
    ARCHIVE DESTINATION lib
    LIBRARY DESTINATION lib
    RUNTIME DESTINATION bin
)

install(DIRECTORY include/ DESTINATION include)