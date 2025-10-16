# TCP服务器示例
add_executable(tcp_server_example tcp_server_example.cpp)
target_link_libraries(tcp_server_example PRIVATE dlt645)
install(TARGETS tcp_server_example RUNTIME DESTINATION bin)

# TCP客户端示例
add_executable(tcp_client_example tcp_client_example.cpp)
target_link_libraries(tcp_client_example PRIVATE dlt645)
install(TARGETS tcp_client_example RUNTIME DESTINATION bin)

# RTU服务器示例
add_executable(rtu_server_example rtu_server_example.cpp)
target_link_libraries(rtu_server_example PRIVATE dlt645)
install(TARGETS rtu_server_example RUNTIME DESTINATION bin)

# RTU客户端示例
add_executable(rtu_client_example rtu_client_example.cpp)
target_link_libraries(rtu_client_example PRIVATE dlt645)
install(TARGETS rtu_client_example RUNTIME DESTINATION bin)

# 添加测试程序
add_executable(test_bcd_float transform/test_bcd_float.cpp)
target_link_libraries(test_bcd_float PRIVATE dlt645)
install(TARGETS test_bcd_float RUNTIME DESTINATION bin)
