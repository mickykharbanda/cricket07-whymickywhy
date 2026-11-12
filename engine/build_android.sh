#!/bin/sh
# Android build: compiles the recompiled code (translator output from build.sh), the runtime and the
# Windows API layer to a native shared library for the Micky's Games app.
#   ./build_android.sh                   -> build_android/lib/arm64-v8a/libcricket.so
#   ABI=armeabi-v7a ./build_android.sh   -> build_android/lib/armeabi-v7a/libcricket.so
#
# Unlike build.sh this produces no executable: SDLActivity loads libcricket.so and calls SDL_main
# (host/main_android.c). Only changed files are recompiled.
#
# NDK, SDL2 and WGPU override the toolchain and library locations. PROFILE=path/to/profile.h picks
# the game profile, as for build.sh. SDL2/WGPU default to a per-ABI folder so the two ABIs' libraries
# never get mixed up: third_party/sdl2-android[-armeabi-v7a], third_party/wgpu-android[-armeabi-v7a].
set -e
R=$(cd "$(dirname "$0")" && pwd)
NDK=${NDK:?set NDK to your Android NDK folder (r27+)}
ABI=${ABI:-arm64-v8a}
API=${API:-26}                                   # matches the app's --min-sdk-version

# Per-ABI toolchain target and default library folders. armeabi-v7a is for the 32-bit phones (and the
# 64-bit phones shipped with a 32-bit Android), which find no engine at all in an arm64-only build.
case "$ABI" in
arm64-v8a)
    TRIPLE=aarch64-linux-android
    CLANG_TARGET=aarch64-linux-android$API
    SUFFIX=
    ;;
armeabi-v7a)
    TRIPLE=arm-linux-androideabi
    CLANG_TARGET=armv7a-linux-androideabi$API
    SUFFIX=-armeabi-v7a
    ;;
*)
    echo "unsupported ABI '$ABI' (arm64-v8a or armeabi-v7a)"; exit 1 ;;
esac
SDL2=${SDL2:-$R/third_party/sdl2-android$SUFFIX}   # include/ + lib/libSDL2.so for this ABI
WGPU=${WGPU:-$R/third_party/wgpu-android$SUFFIX}   # include/ + lib/libwgpu_native.a for this ABI

HOST=$(ls "$NDK/toolchains/llvm/prebuilt" | head -1)
CC="$NDK/toolchains/llvm/prebuilt/$HOST/bin/clang"
[ -x "$CC" ] || { echo "no clang at $CC"; exit 1; }
TARGET="--target=$CLANG_TARGET"

PFLAG=; [ -n "$PROFILE" ] && PFLAG="-DRC_PROFILE=\"$(cd "$(dirname "$PROFILE")" && pwd)/$(basename "$PROFILE")\""
OPT=${OPT:--O2}
# -frounding-math: the x87 rounding mode is mirrored into the host FPU at runtime, as on the desktop.
# -ffp-contract=off: aarch64 would otherwise fuse a*b+c into a single FMADD (one rounding). Neither
# x86-64 baseline SSE2 nor wasm can do that, so leaving it on makes this build's floating point
# disagree with every other target -- which breaks lockstep netplay against a desktop or browser peer.
FPFLAGS="-frounding-math -ffp-contract=off"
# clang has no -frounding-math for 32-bit ARM ("overriding currently unsupported rounding mode"), so
# passing it only prints a warning on every one of the 120 generated files. fesetround() still works,
# so the run-time mirroring in fpu_sync_rounding() is unaffected and the game plays correctly on its
# own; what is lost is the promise that the compiler folds no FP constant under the wrong rounding
# mode. Treat an armeabi-v7a build as offline-only for lockstep netplay against another target.
[ "$ABI" = armeabi-v7a ] && FPFLAGS="-ffp-contract=off"
OUT=out_all
B="$R/build_android"
# Objects are per-ABI: the two ABIs' .o files are not interchangeable, and a shared folder would make
# each build throw away the other's work (the hash covers CFLAGS, so every file would recompile).
OBJ="$B/obj/$ABI"
HOSTOBJ="$B/host/$ABI"
mkdir -p "$OBJ" "$HOSTOBJ" "$B/lib/$ABI"
cd "$R"
[ -d "$OUT" ] || { echo "run build.sh (or the translator) first: it generates $OUT/"; exit 1; }
[ -f "$SDL2/lib/libSDL2.so" ] || { echo "no $SDL2/lib/libSDL2.so -- build SDL2 for $ABI first"; exit 1; }
[ -f "$WGPU/lib/libwgpu_native.a" ] || { echo "no $WGPU/lib/libwgpu_native.a -- fetch wgpu-native for $ABI first"; exit 1; }
CFLAGS="$TARGET $OPT $FPFLAGS -fPIC -w"
export CC CFLAGS OUT OBJ

# generated code: one object per translator output file, rebuilt when the source or flags change
ls $OUT/*.c | while read f; do
    b=$(basename "$f" .c)
    h=$( (cat "$f"; echo "$CFLAGS") | shasum | cut -c1-40)
    if [ ! -f "$OBJ/$b.o" ] || [ "$(cat "$OBJ/$b.hash" 2>/dev/null)" != "$h" ]; then echo "$f $b $h"; fi
done | xargs -r -P 10 -L 1 sh -c '"$CC" $CFLAGS -Iruntime -I"$OUT" -c "$0" -o "$OBJ/$1.o" && echo "$2" > "$OBJ/$1.hash" && echo "  compiled $1"'
for o in "$OBJ"/*.o; do [ -f "$OUT/$(basename "$o" .o).c" ] || rm -f "$o" "${o%.o}.hash"; done

# runtime
"$CC" $CFLAGS -Iruntime -c runtime/runtime.c -o "$HOSTOBJ/runtime.o"
"$CC" $CFLAGS -Iruntime -c runtime/interp.c  -o "$HOSTOBJ/interp.o"

# Windows API layer. window.c (Metal/Objective-C) and watch.c (mach exception ports) are macOS-only;
# window_android.c and main_android.c replace them. main.c still provides rc_boot().
for f in host/*.c; do
    case "$(basename "$f")" in window.c|watch.c|web.c) continue ;; esac
    "$CC" $TARGET $OPT $FPFLAGS -fPIC -Wall -Wno-unused-function -Wno-misleading-indentation \
        -c -Iruntime -Ihost $PFLAG -I"$WGPU/include" -I"$SDL2/include" "$f" \
        -o "$HOSTOBJ/$(basename "$f" .c).o" || exit 1
done

# One shared library: SDLActivity dlopens it and calls SDL_main. -latomic: 32-bit ARM has no
# instruction for the 64-bit atomics the generated code uses, so libclang_rt supplies them.
EXTRA=; [ "$ABI" = armeabi-v7a ] && EXTRA=-latomic
"$CC" $TARGET -shared -o "$B/lib/$ABI/libcricket.so.tmp" \
    "$HOSTOBJ"/*.o "$OBJ"/*.o \
    "$WGPU/lib/libwgpu_native.a" -L"$SDL2/lib" -lSDL2 \
    -lm -lz -landroid -llog -lvulkan -ldl $EXTRA \
    -Wl,--build-id=sha1 -Wl,-z,max-page-size=16384
mv -f "$B/lib/$ABI/libcricket.so.tmp" "$B/lib/$ABI/libcricket.so"
echo "built build_android/lib/$ABI/libcricket.so ($(du -h "$B/lib/$ABI/libcricket.so" | cut -f1))"

# A stripped copy is what ships; keep the unstripped one for symbolising crashes.
"$NDK/toolchains/llvm/prebuilt/$HOST/bin/llvm-strip" --strip-unneeded \
    -o "$B/lib/$ABI/libcricket.stripped.so" "$B/lib/$ABI/libcricket.so"
echo "stripped: $(du -h "$B/lib/$ABI/libcricket.stripped.so" | cut -f1)"
