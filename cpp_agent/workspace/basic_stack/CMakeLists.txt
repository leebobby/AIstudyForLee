cmake_minimum_required(VERSION 3.10)
project(basic_stack)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_library(impl_lib STATIC basic_stack.cpp)

add_executable(run_tests test_basic_stack.cpp)
target_link_libraries(run_tests impl_lib)