#!/usr/bin/env bash
# P4-LUAC - build a project-local lua + luac whose output uses the SSBU chunk
# format (Lua 5.3, little-endian, 4-byte lua_Number / 8-byte lua_Integer).
#
# Nothing is installed anywhere. Sources stay unpacked and unmodified under
# src/lua-5.3.6/ (see README.md for the upstream hash). Every artefact of the
# build - executables AND object files - is written under bin/ only.
#
# Usage (from anywhere; paths resolve against this script's own directory):
#   ./build.sh              # game-format build + both negative controls
#   ./build.sh game         # only bin/lua.exe and bin/luac.exe
#   CC=gcc ./build.sh       # pick the compiler (default: clang from llvm-mingw)
#
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$HERE/src/lua-5.3.6/src"
BIN="$HERE/bin"
OBJ="$HERE/bin/obj"
INFO="$HERE/bin/build-info.txt"

CC="${CC:-clang}"

# Upstream Makefile defaults, kept so the build stays comparable with the
# reference build (src/lua-5.3.6/src/Makefile:10-14).
CFLAGS="-O2 -Wall -Wextra -std=gnu99 -DLUA_COMPAT_5_2"

# ---------------------------------------------------------------------------
# The one configuration setting that matters.
#
# The three game chunks record, in their 29-byte header (lundump.c LoadHeader,
# via lua53-inspect `header`):
#     sizeof int = 4   sizeof size_t = 8   sizeof Instruction = 4
#     sizeof lua_Integer = 8              sizeof lua_Number = 4  (float32)
#
# On this x86_64 target int/size_t/Instruction/lua_Integer already match the
# defaults, so the only field that needs a non-default configuration is
# lua_Number:
#   * luaconf.h:146-148 - without a define, LUA_FLOAT_TYPE is LUA_FLOAT_DOUBLE
#   * luaconf.h:455-470 - with LUA_FLOAT_TYPE == LUA_FLOAT_FLOAT, LUA_NUMBER is
#     float, LUAI_UACNUMBER stays double and LUA_NUMBER_FMT is "%.7g"
# lua_Integer is left at its default LUA_INT_LONGLONG (luaconf.h:142-144,
# luaconf.h:558-560), which is 8 bytes here.
# The define is passed on the command line, so src/ stays byte-identical to
# the upstream tarball (verified: see research/P4-LUAC.md).
# ---------------------------------------------------------------------------
GAME_DEFS="-DLUA_FLOAT_TYPE=LUA_FLOAT_FLOAT"

CORE="lapi lcode lctype ldebug ldo ldump lfunc lgc llex lmem lobject lopcodes
      lparser lstate lstring ltable ltm lundump lvm lzio"
AUXLIB="lauxlib"
LIBS="lbaselib lbitlib lcorolib ldblib liolib lmathlib loslib lstrlib ltablib
      lutf8lib loadlib linit"

want="${1:-all}"

# compile <objectdir> <flags> <file>... ; aborts on the first error
compile_into() {
    local outdir="$1" flags="$2"; shift 2
    local f
    for f in "$@"; do
        # shellcheck disable=SC2086
        $CC $CFLAGS $flags -c "$SRC/$f.c" -o "$outdir/$f.o"
    done
}

# build_variant <name> <cc-flags> <extra-defines> ; builds lua and luac
build_variant() {
    local name="$1" ccflags="$2" defs="$3"
    local base="$OBJ/$name" core="$OBJ/$name/core" luacdir="$OBJ/$name/luac"
    local luadir="$OBJ/$name/lua"
    local flags="$ccflags $defs"
    mkdir -p "$core" "$luacdir" "$luadir" "$BIN"

    echo "== variant $name"
    echo "   CC     : $($CC --version | head -1)"
    echo "   flags  : $CFLAGS $flags"

    # core objects are shared by both programs
    # shellcheck disable=SC2086
    compile_into "$core" "$flags" $CORE $AUXLIB

    # luac: core + lauxlib + luac.c
    compile_into "$luacdir" "$flags" luac
    # shellcheck disable=SC2086
    $CC $ccflags -o "$BIN/luac-$name.exe" "$core"/*.o "$luacdir"/*.o

    # lua: core + lauxlib + all libraries + lua.c
    # shellcheck disable=SC2086
    compile_into "$luadir" "$flags" $LIBS lua
    # shellcheck disable=SC2086
    $CC $ccflags -o "$BIN/lua-$name.exe" "$core"/*.o "$luadir"/*.o

    echo "   -> tools/luac53-game/bin/luac-$name.exe"
    echo "   -> tools/luac53-game/bin/lua-$name.exe"
}

if [ ! -d "$SRC" ]; then
    echo "sources missing: $SRC" >&2
    echo "unpack the official lua-5.3.6.tar.gz there (see README.md)" >&2
    exit 1
fi

mkdir -p "$BIN" "$OBJ"

: > "$INFO"
{
    echo "P4-LUAC build information"
    echo "date (UTC)      : $(date -u '+%Y-%m-%d %H:%M:%S')"
    echo "script          : ${BASH_SOURCE[0]} (relative: tools/luac53-game/build.sh)"
    echo "source tree     : tools/luac53-game/src/lua-5.3.6 (unmodified)"
    echo "compiler        : $($CC --version | head -3)"
    echo "compiler        : $(basename "$(command -v "$CC")"), taken from PATH"
    echo "CFLAGS          : $CFLAGS"
    echo "linker          : $(basename "$($CC -print-prog-name=ld)")"
    echo
} >> "$INFO"

# 1. the game-format build (the deliverable)
build_variant game "" "$GAME_DEFS"

if [ "$want" != "game" ]; then
    # 2. negative control A: stock configuration, 8-byte doubles.
    #    Same source, same compiler, one define missing.
    build_variant control-double "" ""

    # 3. negative control B: 32-bit target, to show the header really is
    #    ABI-sensitive (sizeof size_t becomes 4).
    build_variant control-32bit "--target=i686-w64-mingw32" "$GAME_DEFS"
fi

{
    echo "exact commands (one line per object, expanded):"
    echo "  mkdir -p \$BIN/obj/<variant>/{core,luac,lua}"
    echo "  $CC $CFLAGS <variant-ccflags> <variant-defines> -c \$SRC/<file>.c -o \$BIN/obj/<variant>/core/<file>.o"
    echo "      for each of: $(echo $CORE $AUXLIB)"
    echo "  $CC $CFLAGS <variant-ccflags> <variant-defines> -c \$SRC/luac.c -o \$BIN/obj/<variant>/luac/luac.o"
    echo "  $CC <variant-ccflags> -o \$BIN/luac-<variant>.exe \$BIN/obj/<variant>/core/*.o \$BIN/obj/<variant>/luac/*.o"
    echo "  $CC $CFLAGS <variant-ccflags> <variant-defines> -c \$SRC/<file>.c -o \$BIN/obj/<variant>/lua/<file>.o"
    echo "      for each of: $(echo $LIBS) lua"
    echo "  $CC <variant-ccflags> -o \$BIN/lua-<variant>.exe \$BIN/obj/<variant>/core/*.o \$BIN/obj/<variant>/lua/*.o"
    echo
    echo "variant definitions:"
    echo "  game          : $GAME_DEFS"
    echo "  control-double: (none - upstream default, LUA_FLOAT_DOUBLE)"
    echo "  control-32bit : $GAME_DEFS --target=i686-w64-mingw32"
    echo
    echo "binaries:"
    ( cd "$BIN" && sha256sum ./*.exe ) >> "$INFO"
} >> "$INFO"

echo
echo "build info written to tools/luac53-game/bin/build-info.txt"
ls -1 "$BIN"