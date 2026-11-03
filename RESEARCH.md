# Cricket 07 Browser Port — Deep Technical Research & Architecture

Cloned from `https://cricket07.dhaiwat.com/` into `/Users/micky/Desktop/OYT/cricket07-recomp/`.

## 1. Quick Start (Run Locally)

All web assets, the 42 MB WebAssembly binary (`build/cricket07.wasm`), and all 36 original game files (~1.17 GB in `game/`) have been downloaded and verified locally.

```bash
cd /Users/micky/Desktop/OYT/cricket07-recomp
python3 serve.py 8080
```
Then open `http://localhost:8080/` in Chrome, Edge, or Safari (requires WebGPU and `SharedArrayBuffer` via the COOP/COEP headers set by `serve.py`).

---

## 2. High-Level Overview: Static x86 Recompilation (Not Full-System Emulation)

Instead of running an x86 virtual machine + Windows XP inside the browser, this project uses **Ahead-of-Time (AOT) Static Binary Recompilation** of the 32-bit Windows PE executable `Cricket07.cracked.exe` (`ImageBase: 0x00400000`, `EntryPoint: 0x0074b71c`):

1. **Disassembly & Lifting (`.text` $\rightarrow$ C $\rightarrow$ Wasm)**:
   - Every function in the `.text` section (`0x00401000` .. `0x00784ff6`, ~3.68 MB of x86 machine code) is lifted into a standalone C function named `f_<hex_va>(CPU* cpu)` — **31,547 recompiled functions** in total (`f_00401000` through `f_00784fe0`).
   - All 31,547 lifted C functions are compiled alongside a custom C host runtime (~680 host functions) via **Emscripten** (`-sMODULARIZE -sPROXY_TO_PTHREAD -sWASMFS -sUSE_WEBGPU`) into `build/cricket07.wasm` (42.0 MB, unstripped `name` section included).
2. **Custom Win32 & DirectX 8 Host Runtime in C**:
   - Instead of Wine or Windows DLLs, the binary links directly against a clean-room C implementation of the exact Win32, COM, Direct3D 8, DirectSound, DirectInput, and WinMM APIs that *Cricket 07* imports.

---

## 3. Recompiler ABI & `CPU` Struct Layout (Reverse-Engineered from Bytecode)

Every recompiled x86 function (`f_00401000` .. `f_00784fe0`) and every Win32 import shim (`w_CreateFileA`, `w_Direct3DCreate8`, etc.) shares the identical WebAssembly signature:
```c
void f_XXXXXXXX(CPU *cpu); // Wasm signature: (i32) -> ()
```

### Guest Memory Model
- A global pointer `guest_mem_base` (stored at Wasm linear memory address `0x00220224`) points to a contiguous flat allocation representing the 32-bit Windows virtual address space.
- Any x86 memory access to virtual address `addr` translates directly to `*(T*)(guest_mem_base + addr)`.
- At startup, `load_image()` maps `Cricket07.cracked.exe` into `guest_mem_base + 0x00400000` (`.text`, `.rdata`, `.data`, `.data1`, `.rsrc`) and populates the Import Address Table (IAT) with synthetic thunk addresses (`0x80000000+`) that dispatch to host `w_*` C functions.

### `CPU` Struct Offsets (verified from `f_00401000` & `f_00401010` Wasm disassembly)
| Offset | Type | Field | Description |
| :--- | :--- | :--- | :--- |
| `0x00` | `uint32_t` | `eax` | General-purpose register `EAX` |
| `0x04` | `uint32_t` | `ecx` | General-purpose register `ECX` |
| `0x08` | `uint32_t` | `edx` | General-purpose register `EDX` |
| `0x0C` | `uint32_t` | `ebx` | General-purpose register `EBX` |
| `0x10` | `uint32_t` | `esp` | Stack pointer `ESP` (`ret` adds `4` or `N+4` to `cpu->esp`) |
| `0x14` | `uint32_t` | `ebp` | Base pointer `EBP` |
| `0x18` | `uint32_t` | `esi` | Source index `ESI` |
| `0x1C` | `uint32_t` | `edi` | Destination index `EDI` |
| `0x20` | `uint8_t` | `cf` | Carry Flag (`CF`) |
| `0x21` | `uint8_t` | `zf` | Zero Flag (`ZF`) |
| `0x22` | `uint8_t` | `sf` | Sign Flag (`SF`) |
| `0x23` | `uint8_t` | `of` | Overflow Flag (`OF`) |
| `0x24` | `uint8_t` | `pf` | Parity Flag (`PF`) |
| `0x25` | `uint8_t` | `df` | Direction Flag (`DF`) |
| `0x26` | `uint8_t` | `af` | Auxiliary Carry Flag (`AF`) |
| `0x30..0xE8` | `double[8]` / FPU | `st[0..7]` | x87 FPU register stack + 80-bit helpers (`RF80`, `WF80`, `fpu_round`) |
| `0x138` | `uint32_t` | `ticks` | Deterministic basic-block/function counter; triggers `guest_preempt(cpu)` at `100,000` |

### Concrete Translation Example (`f_00401000`)
Original x86 bytes at `0x00401000` in `Cricket07.cracked.exe`:
```asm
00401000: a1 30 3d 9e 00    mov eax, dword ptr [0x009e3d30]
00401005: c3                ret
```
Lifted C code compiled into `f_00401000` (`[687]` in `cricket07.wasm`):
```c
void f_00401000(CPU *cpu) {
    if (g_deterministic) {
        if (++cpu->ticks >= 100000) {
            guest_preempt(cpu);
        }
    }
    cpu->eax = *(uint32_t *)(guest_mem_base + 0x009e3d30);
    cpu->esp += 4; // pop return address
}
```

### Indirect Calls, COM Dispatch, and Dynamic Code Fallback
- **Direct calls (`call 0x0040XXXX`)**: Push the return VA onto `cpu->esp` in guest memory and directly invoke `f_0040XXXX(cpu)` in Wasm.
- **Indirect calls (`call reg` / `call [mem]`)**: Handled by `call_indirect(cpu, target_va)` (`[106]`) and `jump_indirect(cpu, target_va, from_va)` (`[109]`):
  1. Looks up `target_va` in a fast open-addressed hash table (`lookup_function` / `register_function` using golden-ratio multiplicative hash `0x9e3779b1`) mapping guest x86 VAs to Wasm function table indices (`__indirect_function_table`).
  2. If `target_va` is in the synthetic import/COM range (`>= 0x80000000`), dispatches to the registered Win32 import handler (`find_import_handler`) or COM vtable slot (`com_dispatch`).
  3. If `target_va` points to runtime-generated code in heap/stack memory (`dyncode_contains` via `VirtualProtect(..., PAGE_EXECUTE_*)`), falls back to a built-in **x86 interpreter** (`interp_call`, `decode_modrm`, `alu8`, `alu32`).

---

## 4. Graphics Pipeline: Direct3D 8 $\rightarrow$ WebGPU

*Cricket 07* is a Direct3D 8.1 title (`D3D8.DLL!Direct3DCreate8`). The C host implements all `IDirect3D8`, `IDirect3DDevice8`, `IDirect3DTexture8`, `IDirect3DCubeTexture8`, `IDirect3DSurface8`, `IDirect3DVertexBuffer8`, and `IDirect3DIndexBuffer8` COM interfaces:

1. **Command Recording Across Threads (`rec_*`)**:
   - Because the game runs on a background pthread (`PROXY_TO_PTHREAD`) while WebGPU canvas presentation lives on the main browser thread, `dev_Clear`, `dev_DrawPrimitive`, `dev_DrawIndexedPrimitive`, `dev_Present`, and surface uploads record into a command stream (`rec_clear`, `rec_draw`, `rec_present`, `rec_upload_surface`, `web_queue_chunk`).
   - On the main JS thread, `requestAnimationFrame` calls `M._c07_gpu_pump(1)` to replay the queued draw commands onto the WebGPU device and present the frame, while a `1 ms` `setInterval(() => M._c07_gpu_pump(0), 1)` services mid-frame render-target readbacks (`rec_readback` / `on_rb_mapped`).
2. **Vertex Shaders (`vs_run`)**:
   - D3D8 vertex shader bytecode (`vs.1.1` tokens passed to `dev_CreateVertexShader`) is decoded and executed by a fast CPU-side SIMD/vector VM (`vs_run`), outputting pre-transformed clip-space vertices (`u.flags.x == 2u`) to the WebGPU vertex buffer, while fixed-function T&L vertices use `u.mvp * vec4<f32>(v.pos.xyz, 1.0)` in the WebGPU vertex shader.
3. **Fixed-Function Multi-Texture & Pixel Shaders (`ps_to_wgsl`)**:
   - Fixed-function D3D8 `TextureStageState` combiners (`D3DTOP_*`, `D3DTA_*`, alpha test, fog/specular) are evaluated by a unified ubershader (`stage()`, `top()`, `arg()`, `alpha_ok()`).
   - Custom D3D8 Pixel Shader `ps.1.1`–`ps.1.3` bytecode tokens passed to `dev_CreatePixelShader` are dynamically transpiled at runtime into WGSL fragment shaders by `ps_to_wgsl()` (`[584]`) — including bump-environment mapping (`texbem`, `texbeml`) and register combiners (`r0`, `r1`, `t0..t3`, `v0`, `v1`, `c0..c7`) — and compiled via `wgpuDeviceCreateShaderModule`.
   - DXT1/DXT3/DXT5 compressed textures (`format_is_dxt`) are decompressed to RGBA8 (`texture_to_rgba8`) if the WebGPU adapter does not expose BC texture compression.

---

## 5. Audio Pipeline: DirectSound8 $\rightarrow$ Lock-Free Shared Memory Ring + `AudioWorklet`

- `host/dsound.c` implements `IDirectSound8` and `IDirectSoundBuffer8` (`w_DirectSoundCreate`, `ds_CreateSoundBuffer`, `b_Lock`, `b_Unlock`, `b_Play`, `b_SetFrequency`, `b_SetVolume`, `b_SetPan`, `n_SetNotificationPositions`).
- A background mixer function (`mix_frames`) resamples and mixes all active secondary sound buffers into a lock-free ring buffer in `SharedArrayBuffer` Wasm memory (`c07_audio_ring()`), with header `{ uint32_t write_idx, read_idx, sample_rate, capacity_frames; float pcm[capacity_frames * 2]; }`.
- `audio-worklet.js` runs on the browser's real-time audio thread and reads stereo `Float32` samples directly from `M.wasmMemory.buffer` using `Atomics.load` and `Atomics.store`.

---

## 6. Deterministic Lockstep Netplay (`netplay.js` + `sched_*` + `vclock_*`)

To make a multi-threaded 2006 Windows game deterministic across two browsers for 1v1 online multiplayer without sending video streams or massive state snapshots:
- **Deterministic Virtual Clock (`vclock_*`)**: Replaces wall-clock `rdtsc`, `QueryPerformanceCounter`, `GetTickCount`, `timeGetTime`, and `GetSystemTimeAsFileTime` with a deterministic virtual clock driven by instruction preemption ticks (`C07_DET_PREEMPT_US`, `C07_DET_YIELD_US`) and frame boundaries (`vclock_frame`).
- **Deterministic Cooperative Thread Scheduler (`sched_*`)**: Replaces OS thread scheduling non-determinism by forcing all guest Win32 threads (`w_CreateThread`, `w_WaitForSingleObject`, `w_EnterCriticalSection`, `w_Sleep`) through a deterministic turn-based scheduler (`sched_enter`, `sched_yield_det`, `sched_wait`, `switch_from`).
- **State Hashing & Desync Detection (`state_hash_globals`)**: Every frame (`dev_Present`), the engine hashes guest global state (`state_hash_globals`) and exchanges 64-bit hashes (`_netplay_remote_hash`) alongside gamepad inputs (`_netplay_remote_input`) over an unordered WebRTC DataChannel (`inputs`).

---

## 7. Directory Structure of This Clone (`/Users/micky/Desktop/OYT/cricket07-recomp`)

```text
cricket07-recomp/
├── index.html              # Launcher UI, keyboard reference, and <canvas id="canvas">
├── c07.js                  # OPFS downloader, input mapper, AudioWorklet setup, WebGPU render loop
├── netplay.js              # WebSocket room signaling + WebRTC DataChannel lockstep transport
├── audio-worklet.js        # SharedArrayBuffer ring-buffer AudioWorkletProcessor
├── cricket07-logo.png      # Logo asset
├── favicon.ico             # Favicon
├── serve.py                # Local HTTP server with COOP/COEP headers for instant local play
├── download_game_files.py  # Resumable parallel downloader for all 36 files in game/manifest.json
├── RESEARCH.md             # This technical architecture & reverse-engineering document
├── build/
│   ├── cricket07.js        # Emscripten modularized loader (createC07), WasmFS + WebGPU bindings
│   └── cricket07.wasm      # 42 MB statically recompiled binary (31,547 x86 funcs + C host runtime)
└── game/
    ├── manifest.json       # List of 36 game files & byte sizes (version 599401d4a440)
    ├── Cricket07.cracked.exe # Original 4.35 MB 32-bit Windows PE binary (loaded into guest memory)
    ├── Audio/              # aems.big, ambient.big, music.big, pbp.big (~431 MB)
    └── Data/               # data.gob (341 MB), motion/script.big, motion/moai.viv, 26 *.vp6 videos
```
