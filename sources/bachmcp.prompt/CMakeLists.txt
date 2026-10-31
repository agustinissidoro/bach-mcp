# bachmcp.prompt: a chat-style prompt box (UI external).
#
#   cmake -S sources/bachmcp.prompt -B sources/bachmcp.prompt/build
#   cmake --build sources/bachmcp.prompt/build
#
# makes externals/bachmcp.prompt.mxo. Needs only the Max SDK headers:
#   -DMAX_SDK_BASE=<max-sdk-base>    default: ../../../../max-sdk-base-main

cmake_minimum_required(VERSION 3.20)
set(CMAKE_OSX_ARCHITECTURES "arm64;x86_64" CACHE STRING "")
set(CMAKE_OSX_DEPLOYMENT_TARGET "10.13" CACHE STRING "")
project(bachmcp_prompt C CXX OBJCXX)

get_filename_component(GITHUB_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../../.." ABSOLUTE)
set(MAX_SDK_BASE "${GITHUB_DIR}/max-sdk-base-main" CACHE PATH "max-sdk-base")
set(C74 "${MAX_SDK_BASE}/c74support")
if(NOT EXISTS "${C74}/max-includes/ext.h")
  message(FATAL_ERROR "the Max SDK not found at ${MAX_SDK_BASE} (set -DMAX_SDK_BASE)")
endif()

set(CMAKE_CXX_STANDARD 17)

set(AUTHOR_DOMAIN "com.bachmcp")
set(BUNDLE_IDENTIFIER "bachmcp.prompt")
set(EXCLUDE_FROM_COLLECTIVES "no")
set(PACKAGE_VERSION "0.1.0")
set(COPYRIGHT_STRING "bach-mcp")
configure_file("${MAX_SDK_BASE}/script/Info.plist.in" "${CMAKE_CURRENT_BINARY_DIR}/Info.plist.in" @ONLY)

add_library(bachmcp.prompt MODULE
  source/bachmcp.prompt.cpp
  source/bachmcp.prompt.clipboard.mm)
target_include_directories(bachmcp.prompt PRIVATE "${C74}/max-includes")
target_compile_options(bachmcp.prompt PRIVATE -fvisibility=hidden)
target_link_libraries(bachmcp.prompt PRIVATE
  "-framework AppKit" "-F${C74}/max-includes" "-Wl,-undefined,dynamic_lookup")
set_target_properties(bachmcp.prompt PROPERTIES
  BUNDLE TRUE
  BUNDLE_EXTENSION mxo
  PREFIX ""
  OUTPUT_NAME bachmcp.prompt
  MACOSX_BUNDLE_INFO_PLIST "${CMAKE_CURRENT_BINARY_DIR}/Info.plist.in"
  LIBRARY_OUTPUT_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/../../externals")

# Apple Silicon loads only signed code: sign the whole bundle (ad hoc) after each build.
add_custom_command(TARGET bachmcp.prompt POST_BUILD
  COMMAND codesign --force --sign - "${CMAKE_CURRENT_SOURCE_DIR}/../../externals/bachmcp.prompt.mxo")
