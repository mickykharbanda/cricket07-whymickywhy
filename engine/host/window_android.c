/* The host window on Android (SDL2) and input: runs on the thread SDLActivity calls SDL_main on.
 *
 * The renderer needs an ANativeWindow for VK_KHR_android_surface, which SDL hands us through
 * SDL_GetWindowWMInfo. Keyboard events become DirectInput scan codes (g_dik), Windows virtual-key
 * state (g_keys) and WM_KEYDOWN/WM_KEYUP messages, exactly as on the desktop: host/input.c keys off
 * USB HID usage IDs, and SDL scancodes are those usage IDs.
 *
 * On-screen controls are a Java overlay View on top of SDL's SurfaceView (the same arrangement the
 * browser build uses, where a DOM overlay sits over the canvas). It injects keys through
 * Java_com_micky_games_CricketActivity_nativeKey below, so the engine needs no touch-specific code.
 * That class is app code and lives with the app that loads this library (game-room-public,
 * com.micky.games.CricketActivity); only the symbol name below is a contract with it.
 *
 * The pad handling mirrors host/window.c; it is duplicated rather than shared so that the macOS
 * backend (Metal, Objective-C App Nap opt-out) stays untouched. */
#include "win32.h"

#include <SDL2/SDL.h>
#include <SDL2/SDL_syswm.h>
#include <jni.h>

void *g_android_window;                    /* ANativeWindow * the renderer draws into */
int g_window_w = 1280, g_window_h = 720;   /* drawable size in pixels; replaced at create time */
static SDL_Window *g_window;

void input_key_hid(int usage, int down);   /* input.c */
void input_mouse_button(int b, int down);
void dinput_mouse_move(int dx, int dy);
void input_gamepad(int idx, int connected, uint32_t buttons, int lx, int ly, int rx, int ry);

/* Game controllers (bluetooth pads are common on Android). Pads SDL has a GameController mapping for
   are read in that layout (= the W3C standard layout input_gamepad() takes); others are read as raw
   joysticks, as DirectInput presented them and as the game's controltypes.csv expects. */
#define PAD_SLOTS 4
static SDL_GameController *g_pad[PAD_SLOTS];
static SDL_Joystick *g_joy[PAD_SLOTS];

/* raw button n -> standard-layout bit that host/dinput.c turns back into DirectInput button n */
static const int g_std_for_raw[12] = { 2, 0, 1, 3, 4, 5, 6, 7, 9, 8, 10, 11 };

/* The shoulder buttons are the loft modifier, matching the on-screen LOFT button and Shift on a
   keyboard. Cricket takes a lofted shot from Shift and the pad layout has no button of its own for
   it, so L1 and L2 are mirrored onto the key; the game's own Controller Reassign screen still maps
   every pad button as before, this only adds the modifier on top.

   Held per slot so two pads cannot cancel each other, and sent only when the combined state
   changes -- otherwise every poll while L2 is held would re-send the key. */
static uint32_t g_loft_pads;
static void pad_loft(int slot, int down) {
    uint32_t before = g_loft_pads;
    if (down) g_loft_pads |= 1u << slot; else g_loft_pads &= ~(1u << slot);
    if (!before != !g_loft_pads) input_key_hid(225 /* USB HID usage: Left Shift */, g_loft_pads != 0);
}

/* Standard-gamepad bits (see input.c): 4 = LB / L1, 6 = LT / L2. */
#define PAD_LOFT_BITS ((1u << 4) | (1u << 6))

static void pad_report(int slot) {
    SDL_GameController *gc = g_pad[slot];
    SDL_Joystick *js = g_joy[slot];
    if (!js) { pad_loft(slot, 0); input_gamepad(slot, 0, 0, 0, 0, 0, 0); return; }
    uint32_t b = 0;
    if (!gc) {
        int nb = SDL_JoystickNumButtons(js), na = SDL_JoystickNumAxes(js);
        for (int i = 0; i < nb && i < 12; i++)
            if (SDL_JoystickGetButton(js, i)) b |= 1u << g_std_for_raw[i];
        for (int h = 0; h < SDL_JoystickNumHats(js); h++) {
            Uint8 v = SDL_JoystickGetHat(js, h);
            if (v & SDL_HAT_UP) b |= 1u << 12;
            if (v & SDL_HAT_DOWN) b |= 1u << 13;
            if (v & SDL_HAT_LEFT) b |= 1u << 14;
            if (v & SDL_HAT_RIGHT) b |= 1u << 15;
        }
        int ax[4] = { 0, 0, 0, 0 };
        for (int i = 0; i < na && i < 4; i++) ax[i] = SDL_JoystickGetAxis(js, i);
        pad_loft(slot, (b & PAD_LOFT_BITS) != 0);
        input_gamepad(slot, 1, b, ax[0], ax[1], ax[2], ax[3]);
        return;
    }
    static const SDL_GameControllerButton order[17] = {
        SDL_CONTROLLER_BUTTON_A, SDL_CONTROLLER_BUTTON_B, SDL_CONTROLLER_BUTTON_X, SDL_CONTROLLER_BUTTON_Y,
        SDL_CONTROLLER_BUTTON_LEFTSHOULDER, SDL_CONTROLLER_BUTTON_RIGHTSHOULDER, SDL_CONTROLLER_BUTTON_INVALID,
        SDL_CONTROLLER_BUTTON_INVALID, SDL_CONTROLLER_BUTTON_BACK, SDL_CONTROLLER_BUTTON_START,
        SDL_CONTROLLER_BUTTON_LEFTSTICK, SDL_CONTROLLER_BUTTON_RIGHTSTICK, SDL_CONTROLLER_BUTTON_DPAD_UP,
        SDL_CONTROLLER_BUTTON_DPAD_DOWN, SDL_CONTROLLER_BUTTON_DPAD_LEFT, SDL_CONTROLLER_BUTTON_DPAD_RIGHT,
        SDL_CONTROLLER_BUTTON_GUIDE,
    };
    for (int i = 0; i < 17; i++)
        if (order[i] != SDL_CONTROLLER_BUTTON_INVALID && SDL_GameControllerGetButton(gc, order[i])) b |= 1u << i;
    if (SDL_GameControllerGetAxis(gc, SDL_CONTROLLER_AXIS_TRIGGERLEFT) > 10000) b |= 1u << 6;
    if (SDL_GameControllerGetAxis(gc, SDL_CONTROLLER_AXIS_TRIGGERRIGHT) > 10000) b |= 1u << 7;
    pad_loft(slot, (b & PAD_LOFT_BITS) != 0);
    input_gamepad(slot, 1, b, SDL_GameControllerGetAxis(gc, SDL_CONTROLLER_AXIS_LEFTX),
                  SDL_GameControllerGetAxis(gc, SDL_CONTROLLER_AXIS_LEFTY),
                  SDL_GameControllerGetAxis(gc, SDL_CONTROLLER_AXIS_RIGHTX),
                  SDL_GameControllerGetAxis(gc, SDL_CONTROLLER_AXIS_RIGHTY));
}
static int pad_slot_of(SDL_JoystickID id) {
    for (int i = 0; i < PAD_SLOTS; i++)
        if (g_joy[i] && SDL_JoystickInstanceID(g_joy[i]) == id) return i;
    return -1;
}
static void pad_added(int device_index) {
    if (pad_slot_of(SDL_JoystickGetDeviceInstanceID(device_index)) >= 0) return;
    for (int i = 0; i < PAD_SLOTS; i++)
        if (!g_joy[i]) {
            if (SDL_IsGameController(device_index)) {
                g_pad[i] = SDL_GameControllerOpen(device_index);
                g_joy[i] = g_pad[i] ? SDL_GameControllerGetJoystick(g_pad[i]) : NULL;
            } else {
                g_joy[i] = SDL_JoystickOpen(device_index);
            }
            if (!g_joy[i]) { fprintf(stderr, "controller: open failed: %s\n", SDL_GetError()); return; }
            fprintf(stderr, "controller %d: %s (%s, %d buttons, %d axes, %d hats)\n", i, SDL_JoystickName(g_joy[i]),
                    g_pad[i] ? "mapped" : "raw joystick", SDL_JoystickNumButtons(g_joy[i]),
                    SDL_JoystickNumAxes(g_joy[i]), SDL_JoystickNumHats(g_joy[i]));
            pad_report(i);
            return;
        }
}
static void pad_removed(SDL_JoystickID id) {
    int i = pad_slot_of(id);
    if (i < 0) return;
    if (g_pad[i]) SDL_GameControllerClose(g_pad[i]); else SDL_JoystickClose(g_joy[i]);
    g_pad[i] = NULL;
    g_joy[i] = NULL;
    fprintf(stderr, "controller %d disconnected\n", i);
    pad_report(i);
}

/* ---------------------------------------------------------------- the on-screen overlay (JNI)

   The Java overlay passes USB HID usage IDs, the same numbers SDL reports as scancodes, so the
   values match the KeyboardEvent.code names the browser overlay dispatches:
     ArrowLeft/Right/Up/Down = 0x50/0x4F/0x52/0x51   KeyW/A/S/D = 0x1A/0x04/0x16/0x07
     Escape = 0x29                                   ShiftLeft  = 0xE1                        */
JNIEXPORT void JNICALL
Java_com_micky_games_CricketActivity_nativeKey(JNIEnv *env, jclass cls, jint usage, jint down) {
    (void)env; (void)cls;
    input_key_hid((int)usage, down ? 1 : 0);
}

/* ---------------------------------------------------------------- touch as mouse

   A finger on the surface itself acts as the mouse the menus expect (the overlay's own buttons are
   consumed by Java and never reach here). Two rules the first version got wrong, both of which made
   the front end activate widgets nobody touched:

     - Only the FIRST finger drives the mouse. Every finger used to press and release the same
       button and drag the cursor, so the other hand on the on-screen pad, or a thumb resting on the
       glass, clicked whatever the cursor happened to be over.
     - The click lands on LIFT, and only if the finger barely moved. Pressing on touch-down made it
       impossible to aim the cursor -- it is relative, as DirectInput reports it -- without clicking
       first: every attempt to move it was a press on the widget under the old position. A drag now
       aims, a tap clicks. The press and release go out back to back; dinput.c holds a click for
       MIN_HOLD so a frame cannot fall between them. */
#define TAP_SLOP_PX 24                     /* total motion still counted as a tap, not a drag */
static SDL_FingerID g_touch_id;
static int g_touch_down, g_touch_moved;

/* Back is trapped as a key (SDL_HINT_ANDROID_TRAP_BACK_BUTTON in window_create) and arrives as
   SDL_SCANCODE_AC_BACK -- a browser key, not a PC scancode, so host/input.c's table had nothing to
   map it onto and it did nothing at all. The game's menus go back on Escape, so that is what it
   becomes; without it the overlay's ESC button is the only way out of a menu. */
static int key_usage(SDL_Scancode sc) {
    return sc == SDL_SCANCODE_AC_BACK ? 41 /* USB HID usage: Escape */ : (int)sc;
}

/* ---------------------------------------------------------------- window */

static void read_drawable_size(void) {
    int w = 0, h = 0;
    SDL_GetWindowSize(g_window, &w, &h);   /* on Android this is already the surface size in pixels */
    if (w > 0 && h > 0) { g_window_w = w; g_window_h = h; }
}

int window_create(const char *title) {
    SDL_SetHint(SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS, "1");
    SDL_SetHint(SDL_HINT_ANDROID_TRAP_BACK_BUTTON, "1");   /* Back reaches us as a key, not a finish() */
    /* SDL presents Android's accelerometer as a joystick by default, and it enumerates first -- so
       pad 0, the only pad the game is handed (dinput.c's RC_PADS defaults to 1), was the tilt
       sensor. Two faults in one: a real Bluetooth pad opened into slot 1 where the game could never
       see it, and gravity held the left stick deflected, which this pad type reports to the game as
       a held direction for as long as the phone is in your hands. */
    SDL_SetHint(SDL_HINT_ACCELEROMETER_AS_JOYSTICK, "0");
    if (SDL_Init(SDL_INIT_VIDEO | SDL_INIT_EVENTS | SDL_INIT_GAMECONTROLLER) != 0) {
        fprintf(stderr, "SDL_Init failed: %s\n", SDL_GetError());
        return 0;
    }
    rc_rung("sdl-init");
    /* Android gives us one fullscreen surface; 0x0 means "whatever the display is".
       SDL_WINDOW_VULKAN is not optional here. With no graphics flag at all, SDL_CreateWindow adds
       SDL_WINDOW_OPENGL on Android (SDL_DefaultGraphicsBackends) and binds an EGL/GLES surface to
       the ANativeWindow -- which render_wgpu.c then hands to vkCreateAndroidSurfaceKHR as well.
       Two APIs on one surface segfaults inside the GL driver. SDL skips the EGL surface for a
       Vulkan window for exactly this reason; this is window.c's SDL_WINDOW_METAL on desktop. */
    g_window = SDL_CreateWindow(title, SDL_WINDOWPOS_UNDEFINED, SDL_WINDOWPOS_UNDEFINED, 0, 0,
                                SDL_WINDOW_VULKAN | SDL_WINDOW_FULLSCREEN | SDL_WINDOW_SHOWN);
    if (!g_window) { fprintf(stderr, "SDL_CreateWindow failed: %s\n", SDL_GetError()); return 0; }

    SDL_SysWMinfo info;
    SDL_VERSION(&info.version);
    if (!SDL_GetWindowWMInfo(g_window, &info)) {
        fprintf(stderr, "SDL_GetWindowWMInfo failed: %s\n", SDL_GetError());
        return 0;
    }
    g_android_window = info.info.android.window;
    if (!g_android_window) { fprintf(stderr, "no ANativeWindow from SDL\n"); return 0; }

    read_drawable_size();
    fprintf(stderr, "window: %dx%d drawable (ANativeWindow %p)\n", g_window_w, g_window_h, g_android_window);
    rc_rung("window-ok");
    for (int i = 0; i < SDL_NumJoysticks(); i++) pad_added(i);
    return 1;
}

/* Runs forever on the thread that called window_create. */
void window_event_loop(void) {
    for (;;) {
        SDL_Event e;
        if (!SDL_WaitEventTimeout(&e, 10)) continue;
        switch (e.type) {
        case SDL_QUIT:
            fprintf(stderr, "window closed\n");
            exit(0);
        case SDL_KEYDOWN: if (!e.key.repeat) input_key_hid(key_usage(e.key.keysym.scancode), 1); break;
        case SDL_KEYUP: input_key_hid(key_usage(e.key.keysym.scancode), 0); break;
        case SDL_FINGERDOWN:
            if (g_touch_down) break;                   /* a second finger is not a second mouse */
            g_touch_id = e.tfinger.fingerId;
            g_touch_down = 1;
            g_touch_moved = 0;
            break;
        case SDL_FINGERMOTION: {
            if (!g_touch_down || e.tfinger.fingerId != g_touch_id) break;
            int dx = (int)(e.tfinger.dx * g_window_w), dy = (int)(e.tfinger.dy * g_window_h);
            g_touch_moved += (dx < 0 ? -dx : dx) + (dy < 0 ? -dy : dy);
            dinput_mouse_move(dx, dy);
            break;
        }
        case SDL_FINGERUP:
            if (!g_touch_down || e.tfinger.fingerId != g_touch_id) break;
            g_touch_down = 0;
            if (g_touch_moved <= TAP_SLOP_PX) {        /* a tap clicks; a drag only aimed */
                input_mouse_button(0, 1);
                input_mouse_button(0, 0);
            }
            break;
        case SDL_JOYDEVICEADDED: pad_added(e.jdevice.which); break;
        case SDL_JOYDEVICEREMOVED: pad_removed(e.jdevice.which); break;
        case SDL_JOYAXISMOTION: case SDL_JOYBUTTONDOWN: case SDL_JOYBUTTONUP: case SDL_JOYHATMOTION:
        case SDL_CONTROLLERAXISMOTION: case SDL_CONTROLLERBUTTONDOWN: case SDL_CONTROLLERBUTTONUP: {
            SDL_JoystickID id = e.type == SDL_JOYAXISMOTION ? e.jaxis.which : e.type == SDL_JOYHATMOTION ? e.jhat.which
                              : e.type == SDL_CONTROLLERAXISMOTION ? e.caxis.which
                              : e.type == SDL_CONTROLLERBUTTONDOWN || e.type == SDL_CONTROLLERBUTTONUP ? e.cbutton.which
                              : e.jbutton.which;
            int i = pad_slot_of(id);
            if (i >= 0) pad_report(i);
            break;
        }
        case SDL_WINDOWEVENT:
            if (e.window.event == SDL_WINDOWEVENT_SIZE_CHANGED) read_drawable_size();
            break;
        }
    }
}

/* watch.c (the write-watchpoint debugging aid d3d8.c reaches for under RC_WATCH_ARM) is built on mach
 * exception ports, so it is macOS-only. Stub it out here exactly as web.c does for the browser. */
void watch_arm(uint32_t addr) { (void)addr; }
