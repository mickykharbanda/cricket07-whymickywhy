#ifndef RC_RUNTIME_H
#define RC_RUNTIME_H

#include "cpu.h"
#include <ctype.h>
#include <setjmp.h>

extern jmp_buf *g_trap_jmp;
extern char g_trap_msg[256];

/* Guest address-space layout. The executable sits at its preferred base (usually 0x00400000), below
   the heap. */
#define GUEST_TIB              0x00010000u
#define GUEST_STACK_TOP        0x00300000u
#define GUEST_STACK_SIZE       0x00200000u
#define GUEST_HEAP_BASE        0x10000000u
/* On a 64-bit host the guest gets a full 4 GiB reservation. Where the host's own pointers are 32 bits
   -- the browser (wasm32) and armeabi-v7a Android -- the guest cannot have an address space as large
   as the one it is living inside, so the heap and VirtualAlloc ranges are compacted to 1.25 GiB: the
   game peaks at ~125 MB of heap and ~580 MB of virtual allocations (mostly mapped archives, of which
   only what the game reads becomes resident: host/core.c, lazy file views).
   The compact layout is selected by host pointer size, not by target: a 32-bit process asking for the
   4 GiB layout would compute a size_t that has silently wrapped (0x100010000 truncates to 0x10000),
   get a 64 KiB mapping back, and fault on the first access past it. */
#if defined(__EMSCRIPTEN__) || __SIZEOF_POINTER__ == 4
#define GUEST_SPACE            0x50000000ull
#define GUEST_HEAP_HI          0x20000000u
#define GUEST_VALLOC_LO        0x20000000u
#define GUEST_VALLOC_HI        0x50000000u
#else
#define GUEST_SPACE            0x100000000ull
#define GUEST_HEAP_HI          0x60000000u
#define GUEST_VALLOC_LO        0x60000000u
#define GUEST_VALLOC_HI        0xE0000000u
#endif
#define GUEST_RETURN_SENTINEL  0xDEADBEEFu

typedef struct { const char *name; GuestFn fn; } ImportHandler;  /* name like "KERNEL32.DLL!GetTickCount" */
typedef struct { uint32_t image_base, entry, num_imports; } LoadedImage;
extern uint32_t g_image_lo, g_image_hi;   /* the loaded executable's address range */
extern uint32_t g_state_lo, g_state_hi;   /* its writable sections (global data): what determinism checks hash */

/* Entry hooks (profiles/cricket07.patches.json): hook_copy_source runs on entry to the game's memcpy and passes its source
   range to g_copy_source_hook when the host has set one (host/core.c: lazy file views). */
extern void (*g_copy_source_hook)(uint32_t src, uint32_t len);
void hook_copy_source(CPU *c);

void runtime_init(CPU *c);
void set_import_handlers(ImportHandler *h, uint32_t n);  /* call before load_image */
int load_image(const char *path, LoadedImage *out);
GuestFn lookup_function(uint32_t addr);
const char *import_name(uint32_t addr);
uint32_t add_dynamic_import(const char *name, GuestFn fn);   /* for GetProcAddress */
GuestFn find_import_handler(const char *name);
extern __thread uint32_t g_import_target;  /* address of the host slot being called (set by call_indirect) */
uint32_t guest_alloc(uint32_t size);
void guest_call(CPU *c, GuestFn fn, int nargs, const uint32_t *args);
void register_all_functions(void);  /* generated */

/* Code created at run time (e.g. sound-engine plug-ins loaded from data files): interpreted, see interp.c */
void dyncode_register(uint32_t addr, uint32_t len);
int dyncode_contains(uint32_t addr);
void interp_call(CPU *c, uint32_t eip);   /* return address already pushed */

typedef struct { uint32_t addr; uint32_t regs[8]; double st0; uint32_t top; } TraceRec;
extern TraceRec *g_trace;          /* set by a test harness to record every instruction */
extern uint32_t g_trace_len, g_trace_cap;

#endif
