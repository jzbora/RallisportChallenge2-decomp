#define UNICODE
#define _UNICODE
#include <windows.h>
#include <shellapi.h>
#include <wchar.h>

int WINAPI wWinMain(HINSTANCE instance, HINSTANCE previous, PWSTR args, int show) {
    WCHAR folder[32768], target[32768];
    (void)instance; (void)previous; (void)args; (void)show;
    DWORD count = GetModuleFileNameW(NULL, folder, 32768);
    if (!count || count >= 32768) return 1;
    WCHAR *last = wcsrchr(folder, L'\\');
    if (!last) return 1;
    *last = 0;
    if (wcslen(folder) + 10 >= 32768) return 1;
    wcscpy_s(target, 32768, folder);
    wcscat_s(target, 32768, L"\\rsc2.exe");
    HINSTANCE result = ShellExecuteW(NULL, L"open", target, NULL, folder, SW_SHOWNORMAL);
    if ((INT_PTR)result <= 32) {
        MessageBoxW(NULL, L"无法启动游戏。请确认 rsc2.exe 和 game 文件夹与本启动程序在同一个目录。",
                    L"RalliSport Challenge 2", MB_OK | MB_ICONERROR);
        return 1;
    }
    return 0;
}
