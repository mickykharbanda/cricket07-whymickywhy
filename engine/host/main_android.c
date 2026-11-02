/* Android entry point. SDLActivity starts a thread and calls SDL_main on it, so unlike the desktop
 * build there is no process main(): host/main.c's main() is compiled out on Android and its boot
 * sequence is reached through rc_boot() instead.
 *
 * The game folder arrives as argv[1], which the Activity supplies by overriding
 * SDLActivity.getArguments(). With no argument we fall back to <external storage>/cricket07/game,
 * where the app's downloader puts the 1.17 GB of game data.
 *
 * Everything else — the window, the renderer, audio, input — is the same code the desktop build
 * runs; see host/window_android.c for the ANativeWindow the Vulkan surface is made from. */
#include "win32.h"

#include <SDL2/SDL.h>
#include <SDL2/SDL_main.h>
#include <android/log.h>
#include <fcntl.h>
#include <pthread.h>
#include <unistd.h>

int rc_boot(const char *game);   /* host/main.c */

/* stderr/stdout are discarded on Android, so mirror the engine's logging into logcat. */
static int log_pipe[2];
static void *log_pump(void *arg) {
    (void)arg;
    char line[512];
    ssize_t n;
    size_t used = 0;
    while ((n = read(log_pipe[0], line + used, sizeof line - used - 1)) > 0) {
        used += (size_t)n;
        line[used] = 0;
        char *start = line, *nl;
        while ((nl = strchr(start, '\n'))) {
            *nl = 0;
            __android_log_write(ANDROID_LOG_INFO, "cricket07", start);
            start = nl + 1;
        }
        used = strlen(start);
        memmove(line, start, used);
    }
    return NULL;
}
static void redirect_output_to_logcat(void) {
    setvbuf(stdout, NULL, _IOLBF, 0);
    setvbuf(stderr, NULL, _IONBF, 0);
    if (pipe(log_pipe)) return;
    dup2(log_pipe[1], STDOUT_FILENO);
    dup2(log_pipe[1], STDERR_FILENO);
    pthread_t t;
    if (!pthread_create(&t, NULL, log_pump, NULL)) pthread_detach(t);
}

/* The launcher reads this out of getFilesDir() after a failed launch. One short token, overwritten
 * each time: the file is truncated first so a longer token cannot leave a tail of the previous one.
 * No stdio anywhere in here -- a buffered byte that never reaches the disk is the whole failure we
 * are trying to avoid. Repeats are dropped, so the per-frame call at the end costs one fsync once. */
static char g_rung_path[1024];

void rc_rung(const char *token) {
    static char last[32];
    if (!g_rung_path[0] || !strcmp(last, token)) return;
    snprintf(last, sizeof last, "%s", token);
    int fd = open(g_rung_path, O_WRONLY | O_CREAT | O_TRUNC, 0600);
    if (fd < 0) return;
    size_t n = strlen(token);
    if (write(fd, token, n) == (ssize_t)n) fsync(fd);
    close(fd);
}

int SDL_main(int argc, char *argv[]) {
    redirect_output_to_logcat();

    const char *internal = SDL_AndroidGetInternalStoragePath();
    if (internal) snprintf(g_rung_path, sizeof g_rung_path, "%s/engine-progress.txt", internal);

    char fallback[1024];
    const char *game = argc > 1 ? argv[1] : NULL;
    if (!game) {
        const char *base = SDL_AndroidGetExternalStoragePath();
        if (!base) base = SDL_AndroidGetInternalStoragePath();
        if (!base) { fprintf(stderr, "no storage path from SDL\n"); return 1; }
        snprintf(fallback, sizeof fallback, "%s/cricket07/game", base);
        game = fallback;
    }
    fprintf(stderr, "game folder: %s\n", game);
    return rc_boot(game);
}
