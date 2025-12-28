cmake_minimum_required(VERSION 3.25)
project(gpustat LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# FetchContent for dependencies
include(FetchContent)

FetchContent_Declare(
    cpr
    GIT_REPOSITORY https://github.com/libcpr/cpr.git
    GIT_TAG 1.11.0 # Or a later version
)
FetchContent_MakeAvailable(cpr)

FetchContent_Declare(
    json
    GIT_REPOSITORY https://github.com/nlohmann/json.git
    GIT_TAG v3.11.2
)
FetchContent_MakeAvailable(json)

add_executable(gpustat main.cpp)
target_link_libraries(gpustat PRIVATE cpr::cpr nlohmann_json::nlohmann_json)
