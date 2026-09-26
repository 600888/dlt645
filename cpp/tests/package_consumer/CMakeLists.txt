cmake_minimum_required(VERSION 3.20)
project(dlt645_package_consumer LANGUAGES CXX)

find_package(dlt645 1 CONFIG REQUIRED)

add_executable(dlt645_package_consumer ../core_test.cpp)
target_link_libraries(dlt645_package_consumer PRIVATE dlt645::dlt645)
if(MSVC)
    target_compile_options(dlt645_package_consumer PRIVATE /utf-8)
endif()

if(WIN32)
    add_custom_command(TARGET dlt645_package_consumer POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy_if_different
                $<TARGET_FILE:dlt645::dlt645>
                $<TARGET_FILE_DIR:dlt645_package_consumer>
    )
endif()

enable_testing()
add_test(NAME dlt645_package_consumer COMMAND dlt645_package_consumer)
