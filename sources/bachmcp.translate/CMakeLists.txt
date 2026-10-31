# bachmcp externals: bachmcp.translate.
#
#   cmake -S sources/bachmcp.translate -B sources/bachmcp.translate/build
#   cmake --build sources/bachmcp.translate/build
#
# makes externals/bachmcp.translate.mxo.
#
# It compiles bach's shared library (the sources of bach's own "lib_bach" target)
# from a checkout of bach, read only, and the Max SDK headers. Their places:
#   -DBACH_SOURCE=<bach>/source      default: ../../../../bach/source (next to this repository)
#   -DMAX_SDK_BASE=<max-sdk-base>    default: ../../../../max-sdk-base-main
# The bach package loaded in Max must be the same version as that checkout (0.8.3).

cmake_minimum_required(VERSION 3.20)
set(CMAKE_OSX_ARCHITECTURES "arm64;x86_64" CACHE STRING "")
set(CMAKE_OSX_DEPLOYMENT_TARGET "10.13" CACHE STRING "")
project(bachmcp_externals C CXX)

get_filename_component(GITHUB_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../../.." ABSOLUTE)
set(BACH_SOURCE "${GITHUB_DIR}/bach/source" CACHE PATH "bach's source folder")
set(MAX_SDK_BASE "${GITHUB_DIR}/max-sdk-base-main" CACHE PATH "max-sdk-base")
set(C74 "${MAX_SDK_BASE}/c74support")

if(NOT EXISTS "${BACH_SOURCE}/commons/foundation/llllobj.c")
  message(FATAL_ERROR "bach's source not found at ${BACH_SOURCE} (set -DBACH_SOURCE)")
endif()
if(NOT EXISTS "${C74}/max-includes/ext.h")
  message(FATAL_ERROR "the Max SDK not found at ${MAX_SDK_BASE} (set -DMAX_SDK_BASE)")
endif()

set(CMAKE_CXX_STANDARD 17)

# ── bach's library: the sources of its lib_bach target, as bach builds them (C as C++) ── #

set(LIB_BACH_FILES
  kiss_fft.c fftutil.c builtInFunctionWithFindFn.cpp operator.cpp jpatcher_syms.c kfc.c kiss_fastfir.c
  kiss_fftnd.c llllIterator.cpp kiss_fftndr.c bach_strparser_tab.c astNode.cpp llll_sort.cpp kiss_fftr.c
  mxml-attr.c mxml-entity.c mxml-file.c mxml-get.c mxml-index.c mxml-node.c stringparser_tab_nolines.c
  mxml-private.c mxml-search.c mxml-set.c mxml-string.c bach_codableobj.cpp notation_files.c
  collector_commons.c notation_goto.c hatom.c llll_commons.c conditional.cpp llll_commonsyms.c llll_files.c
  llll_math.c llll_modifiers.c llllobj.c comparator.cpp llll_expr_commons.c llll_maxinterface.c
  bach_inspector.c bach_math_utilities.c commonsyms.c bach_slots.c llll_commons_ext.c bach_cursors.c
  llll_settheory.c llll_linearalgebra.c llll_append.c rational.c notation_commons.c mathFunction.cpp
  notation_maxinterface.c spectral.c bach_threads.c bach_128bit.cpp builtInFunction.cpp
  llll_hatom_change.c bach_mem.c SdifCheck.c SdifConvToText.c SdifErrMess.c SdifFGet.c bach_maxutils.c
  SdifFile.c SdifFPrint.c SdifFPut.c SdifFrame.c function.cpp bach_symparser.c notation_dynamics.c
  SdifFrameType.c pvManager.cpp bach_exprparser.c bach_pitchparser.c SdifFRead.c SdifFScan.c SdifFWrite.c
  bach_symparser_tab.c bach_graphics.c SdifGlobals.c SdifHard_OS.c ownedFunction.cpp bach_pitch.cpp
  SdifHash.c SdifHighLevel.c stringparser_nolines.c SdifList.c SdifMatrix.c SdifMatrixType.c
  SdifNameValue.c SdifPreTypes.c SdifPrint.c fnMap.cpp builtInFunctionWithSortFn.cpp SdifRWLowLevel.c
  bach_strparser.c notation_pitches.c SdifSelect.c SdifSignatureTab.c SdifStreamID.c SdifString.c
  bach_alterparser.c SdifTest.c SdifTextConv.c SdifTimePosition.c bach_chkparser.c bach_ss.c
  llll_comparisons.c notation_export.c)

file(GLOB_RECURSE BACH_ALL "${BACH_SOURCE}/commons/*" "${C74}/max-includes/common/*")
set(LIB_BACH_SOURCES "")
foreach(name IN LISTS LIB_BACH_FILES)
  set(found "")
  foreach(path IN LISTS BACH_ALL)
    get_filename_component(base "${path}" NAME)
    if(base STREQUAL name)
      set(found "${path}")
      break()
    endif()
  endforeach()
  if(NOT found)
    message(FATAL_ERROR "lib_bach source ${name} not found")
  endif()
  list(APPEND LIB_BACH_SOURCES "${found}")
endforeach()

# bach finds its headers in any of its folders (Xcode: ALWAYS_SEARCH_USER_PATHS)
set(BACH_INCLUDES "${BACH_SOURCE}/commons")
foreach(path IN LISTS BACH_ALL)
  if(path MATCHES "\\.(h|hpp)$" AND NOT path MATCHES "/(doc|docs|test|tests|examples?)/")
    get_filename_component(dir "${path}" DIRECTORY)
    list(APPEND BACH_INCLUDES "${dir}")
  endif()
endforeach()
list(REMOVE_DUPLICATES BACH_INCLUDES)
set(C74_INCLUDES "${C74}/max-includes" "${C74}/msp-includes" "${C74}/jit-includes")

set(BACH_DEFINITIONS BACH_MAX "DENORM_WANT_FIX=1" CONFIGURATION_Deployment
    "BACH_VERSION=\"0.8.3.0\"" "BACH_LLLL_VERSION=\"0.8.0.0\"")

set_source_files_properties(${LIB_BACH_SOURCES} PROPERTIES LANGUAGE CXX COMPILE_OPTIONS "-xc++;-w")
# The Max SDK's own symbol table declares a few symbols twice, which only C allows.
foreach(path IN LISTS LIB_BACH_SOURCES)
  if(path MATCHES "jpatcher_syms\\.c$")
    set_source_files_properties("${path}" PROPERTIES LANGUAGE C COMPILE_OPTIONS "-w")
  endif()
endforeach()
add_library(bach_lib STATIC ${LIB_BACH_SOURCES})
target_include_directories(bach_lib PUBLIC ${BACH_INCLUDES} ${C74_INCLUDES})
target_compile_definitions(bach_lib PUBLIC ${BACH_DEFINITIONS})
target_compile_options(bach_lib PUBLIC -fvisibility=hidden)
target_link_options(bach_lib PUBLIC "-F${C74}/max-includes")

# ── bachmcp.translate ── #

set(AUTHOR_DOMAIN "com.bachmcp")
set(BUNDLE_IDENTIFIER "bachmcp.translate")
set(EXCLUDE_FROM_COLLECTIVES "no")
set(PACKAGE_VERSION "0.1.0")
set(COPYRIGHT_STRING "bach-mcp")
configure_file("${MAX_SDK_BASE}/script/Info.plist.in" "${CMAKE_CURRENT_BINARY_DIR}/Info.plist.in" @ONLY)

add_library(bachmcp.translate MODULE
  source/bachmcp.translate.cpp
  source/bachmcp.translate.convert.cpp)
target_link_libraries(bachmcp.translate PRIVATE bach_lib
  "-framework CoreServices" "-framework Accelerate" "-Wl,-undefined,dynamic_lookup")
set_target_properties(bachmcp.translate PROPERTIES
  BUNDLE TRUE
  BUNDLE_EXTENSION mxo
  PREFIX ""
  OUTPUT_NAME bachmcp.translate
  MACOSX_BUNDLE_INFO_PLIST "${CMAKE_CURRENT_BINARY_DIR}/Info.plist.in"
  LIBRARY_OUTPUT_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/../../externals")

# Apple Silicon loads only signed code: sign the whole bundle (ad hoc) after each build.
add_custom_command(TARGET bachmcp.translate POST_BUILD
  COMMAND codesign --force --sign - "${CMAKE_CURRENT_SOURCE_DIR}/../../externals/bachmcp.translate.mxo")
