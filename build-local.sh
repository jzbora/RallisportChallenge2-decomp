#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
ROOT="$PWD"
TP="$ROOT/third_party/mingw"
TC="$ROOT/xboxrecomp/cmake/mingw-w64-x86_64.cmake"
JOBS=8
mkdir -p "$TP/include" "$TP/lib" logs
cp -r /usr/include/vulkan /usr/include/vk_video "$TP/include/"
python3 rsc2/tools/mingw_vulkan_def.py "$TP/include" third_party/vulkan-1.def
x86_64-w64-mingw32-dlltool -d third_party/vulkan-1.def -l "$TP/lib/libvulkan-1.a"
cmake -S third_party/src/glslang -B third_party/build-glslang -G Ninja \
 -DCMAKE_TOOLCHAIN_FILE="$TC" -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$TP" \
 -DBUILD_SHARED_LIBS=OFF -DENABLE_OPT=OFF -DENABLE_HLSL=OFF -DGLSLANG_TESTS=OFF -DENABLE_GLSLANG_BINARIES=OFF
cmake --build third_party/build-glslang -j "$JOBS"
cmake --install third_party/build-glslang
cmake -S third_party/src/SDL2 -B third_party/build-sdl -G Ninja \
 -DCMAKE_TOOLCHAIN_FILE="$TC" -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$TP" \
 -DSDL_SHARED=OFF -DSDL_STATIC=ON -DSDL_TEST=OFF
cmake --build third_party/build-sdl -j "$JOBS"
cmake --install third_party/build-sdl
cmake -S rsc2 -B rsc2/build-win -G Ninja -DCMAKE_BUILD_TYPE=Release \
 -DCMAKE_TOOLCHAIN_FILE="$TC" -DVulkan_INCLUDE_DIR="$TP/include" -DVulkan_LIBRARY="$TP/lib/libvulkan-1.a" \
 -DXBOXRECOMP_GLSLANG_INCLUDE="$TP/include" -DXBOXRECOMP_GLSLANG_LIB="$TP/lib/libglslang.a" \
 -DXBOXRECOMP_GLSLANG_RL_LIB="$TP/lib/libglslang-default-resource-limits.a" \
 "-DXBOXRECOMP_GLSLANG_EXTRA_LIBS=$TP/lib/libSPIRV.a;$TP/lib/libMachineIndependent.a;$TP/lib/libOSDependent.a;$TP/lib/libGenericCodeGen.a;$TP/lib/libMachineIndependent.a;stdc++" \
 -DSDL2_DIR="$TP/lib/cmake/SDL2"
cmake --build rsc2/build-win -j "$JOBS"
