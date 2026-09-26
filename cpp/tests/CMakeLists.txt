add_executable(dlt645_core_test core_test.cpp)
target_link_libraries(dlt645_core_test PRIVATE dlt645)
add_test(NAME dlt645_core_test COMMAND dlt645_core_test)

add_executable(dlt645_service_test service_test.cpp)
target_link_libraries(dlt645_service_test PRIVATE dlt645::dlt645)
add_test(NAME dlt645_service_test COMMAND dlt645_service_test)

add_executable(dlt645_transport_test transport_test.cpp)
target_link_libraries(dlt645_transport_test PRIVATE dlt645::dlt645)
add_test(NAME dlt645_transport_test COMMAND dlt645_transport_test)
