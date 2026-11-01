#!/bin/sh
# Android build: compiles the recompiled code (translator output from build.sh), the runtime and the
# Windows API layer to a native arm64 shared library for the Micky's Games app.
#   ./build_android.sh   -> build_android/lib/arm64-v8a/libcricket.so
#
# Unlike build.sh this produces no executable: SDLActivity loads libcricket.so and calls SDL_main
# (host/main_android.c). Only changed files are recompiled.
#
# NDK, SDL2 and WGPU override the toolchain and library locations. PROFILE=path/to/profile.h picks
# the game profile, as for build.sh.
set -e
R=$(cd "$(dirname "$0")" && pwd)
NDK=${NDK:?set NDK to your Android NDK folder (r27+)}
SDL2=${SDL2:-$R/third_party/sdl2-android}        # include/ + lib/libSDL2.so for arm64-v8a
WGPU=${WGPU:-$R/third_party/wgpu-android}        # include/ + lib/libwgpu_native.a for arm64
API=${API:-26}                                   # matches the app's --min-sdk-version
ABI=arm64-v8a
TRIPLE=aarch64-linux-android

HOST=$(ls "$NDK/toolchains/llvm/prebuilt" | head -1)
CC="$NDK/toolchains/llvm/prebuilt/$HOST/bin/clang"
[ -x "$CC" ] || { echo "no clang at $CC"; exit 1; }
TARGET="--target=$TRIPLE$API"

PFLAG=; [ -n "$PROFILE" ] && PFLAG="-DRC_PROFILE=\"$(cd "$(dirname "$PROFILE")" && pwd)/$(basename "$PROFILE")\""
OPT=${OPT:--O2}
# -frounding-math: the x87 rounding mode is mirrored into the host FPU at runtime, as on the desktop.
# -ffp-contract=off: aarch64 would otherwise fuse a*b+c into a single FMADD (one rounding). Neither
# x86-64 baseline SSE2 nor wasm can do that, so leaving it on makes this build's floating point
# disagree with every other target -- which breaks lockstep netplay against a desktop or browser peer.
FPFLAGS="-frounding-math -ffp-contract=off"
OUT=out_all
B="$R/build_android"
mkdir -p "$B/obj" "$B/host" "$B/lib/$ABI"
cd "$R"
[ -d "$OUT" ] || { echo "run build.sh (or the translator) first: it generates $OUT/"; exit 1; }
CFLAGS="$TARGET $OPT $FPFLAGS -fPIC -w"
export CC CFLAGS OUT B

# generated code: one object per translator output file, rebuilt when the source or flags change
ls $OUT/*.c | while read f; do
    b=$(basename "$f" .c)
    h=$( (cat "$f"; echo "$CFLAGS") | shasum | cut -c1-40)
    if [ ! -f "$B/obj/$b.o" ] || [ "$(cat "$B/obj/$b.hash" 2>/dev/null)" != "$h" ]; then echo "$f $b $h"; fi
done | xargs -r -P 10 -L 1 sh -c '"$CC" $CFLAGS -Iruntime -I"$OUT" -c "$0" -o "$B/obj/$1.o" && echo "$2" > "$B/obj/$1.hash" && echo "  compiled $1"'
for o in "$B"/obj/*.o; do [ -f "$OUT/$(basename "$o" .o).c" ] || rm -f "$o" "${o%.o}.hash"; done

# runtime
"$CC" $CFLAGS -Iruntime -c runtime/runtime.c -o "$B/runtime.o"
"$CC" $CFLAGS -Iruntime -c runtime/interp.c  -o "$B/interp.o"

# Windows API layer. window.c (Metal/Objective-C) and watch.c (mach exception ports) are macOS-only;
# window_android.c and main_android.c replace them. main.c still provides rc_boot().
for f in host/*.c; do
    case "$(basename "$f")" in window.c|watch.c|web.c) continue ;; esac
    "$CC" $TARGET $OPT $FPFLAGS -fPIC -Wall -Wno-unused-function -Wno-misleading-indentation \
        -c -Iruntime -Ihost $PFLAG -I"$WGPU/include" -I"$SDL2/include" "$f" \
        -o "$B/host/$(basename "$f" .c).o" || exit 1
done

# One shared library: SDLActivity dlopens it and calls SDL_main.
"$CC" $TARGET -shared -o "$B/lib/$ABI/libcricket.so.tmp" \
    "$B"/runtime.o "$B"/interp.o "$B"/host/*.o "$B"/obj/*.o \
    "$WGPU/lib/libwgpu_native.a" -L"$SDL2/lib" -lSDL2 \
    -lm -lz -landroid -llog -lvulkan -ldl \
    -Wl,--build-id=sha1 -Wl,-z,max-page-size=16384
mv -f "$B/lib/$ABI/libcricket.so.tmp" "$B/lib/$ABI/libcricket.so"
echo "built build_android/lib/$ABI/libcricket.so ($(du -h "$B/lib/$ABI/libcricket.so" | cut -f1))"

# A stripped copy is what ships; keep the unstripped one for symbolising crashes.
"$NDK/toolchains/llvm/prebuilt/$HOST/bin/llvm-strip" --strip-unneeded \
    -o "$B/lib/$ABI/libcricket.stripped.so" "$B/lib/$ABI/libcricket.so"
echo "stripped: $(du -h "$B/lib/$ABI/libcricket.stripped.so" | cut -f1)"
