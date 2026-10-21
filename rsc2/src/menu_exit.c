/* Native front-end / pause choices. Assets append action 7 / 13 without
 * changing existing actions. Only the matching controller vtable is hooked.
 * Confirmation uses the title's message box and A/B handling, not a host UI. */
#include "recomp/gen/recomp_types.h"
#include <stdio.h>
#include <stdlib.h>
#if defined(_WIN32)
#include <windows.h>
#endif

extern void sub_002B8140(void), sub_00165110(void);
extern void sub_002B85F0(void), sub_00164D60(void);
extern void sub_001DB210(void), sub_001DAFB0(void);
extern void sub_002B7C20(void), sub_002B7F10(void);
static uint32_t pending_owner;

static int enabled(void)
{
    const char *v = getenv("RSC2_NATIVE_EXIT");
    return !v || v[0] != '0';
}

static uint32_t choice_action(uint32_t choice)
{
    recomp_func_t fn = recomp_lookup(MEM32(MEM32(choice) + 0x74));
    uint32_t saved_sp = g_esp, saved_cx = g_ecx;
    if (!fn) return UINT32_MAX;
    g_ecx = choice;
    PUSH32(g_esp, 0x002B815A);
    fn();
    uint32_t action = g_eax;
    g_esp = saved_sp;
    g_ecx = saved_cx;
    return action;
}

static uint32_t vcall(uint32_t object, uint32_t slot, int argc,
                      uint32_t arg0, uint32_t arg1)
{
    recomp_func_t fn = recomp_lookup(MEM32(MEM32(object) + slot));
    if (!fn) return 0;
    g_ecx = object;
    if (argc > 1) PUSH32(g_esp, arg1);
    if (argc > 0) PUSH32(g_esp, arg0);
    PUSH32(g_esp, 0x0016470D);
    fn();
    return g_eax;
}

/* The stock front-end animation only has backgrounds for actions 0..6.
 * Keep the last valid background instead of using an invalid lookup on 7. */
static void main_tick(void)
{
    uint32_t owner=g_ecx, saved_sp=g_esp;
    uint32_t selected=vcall(MEM32(owner+0x1C),0xCC,1,UINT32_MAX,0);
    int quit=selected && choice_action(selected)==7;
    g_ecx=owner;g_esp=saved_sp;
    if (enabled() && quit) { g_eax=1;g_esp+=12;return; }
    sub_002B7C20();
}

static void main_changed(void)
{
    uint32_t owner=g_ecx,saved_sp=g_esp;
    if (enabled() && choice_action(MEM32(saved_sp+4))==7) {
        MEMF(owner+0x14)=0;
        uint32_t title=MEM32(MEM32(owner+8)+0x14);
        if(title)vcall(title,0xC0,1,0xF000,0);
        g_eax=1;g_esp=saved_sp+8;return;
    }
    g_ecx=owner;g_esp=saved_sp;sub_002B7F10();
}

static void choice_made(int pause)
{
    uint32_t owner = g_ecx, saved_sp = g_esp;
    uint32_t saved_bx = g_ebx, saved_si = g_esi, saved_di = g_edi;
    uint32_t saved_bp = g_ebp, saved_seh = g_seh_ebp;
    uint32_t menu = MEM32(owner + 4);
    /* Modal choices must stay with their original handler. */
    if (!enabled() || MEM8(menu + 0x236)
            || choice_action(MEM32(saved_sp + 4)) != (pause ? 13u : 7u)) {
        g_esp = saved_sp; g_ecx = owner;
        if (pause) sub_00165110(); else sub_002B8140();
        return;
    }
    pending_owner = owner;
    fprintf(stderr, "[MENU EXIT] confirm %s\n", pause ? "pause" : "main");
    uint32_t buttons=MEM32(MEM32(owner+8)+0x18);
    if(buttons) {
        vcall(buttons,0xC0,1,3,0);
        vcall(buttons,0xC8,2,0,0x14E); /* A: Yes */
        vcall(buttons,0xC8,2,1,0x140); /* B: Cancel */
    }
    /* show_message(message id, heading id, enabled buttons, screen index).
     * Native results are A=0, B=1. No host dialog or extra navigation. */
    g_edi = menu;
    PUSH32(g_esp, MEM32(owner + 0xC));
    PUSH32(g_esp, 3);
    PUSH32(g_esp, 0xF000);
    PUSH32(g_esp, 0xF001);
    PUSH32(g_esp, 0x0016470D);
    sub_001DB210();
    g_ebx = saved_bx; g_esi = saved_si; g_edi = saved_di;
    g_ebp = saved_bp; g_seh_ebp = saved_seh;
    g_esp = saved_sp + 8; g_eax = 1;
}

static void response(int pause)
{
    uint32_t owner = g_ecx;
    if (!pending_owner || pending_owner != owner) {
        if (pause) sub_00164D60(); else sub_002B85F0();
        return;
    }
    uint32_t result = MEM32(g_esp + 4);
    pending_owner = 0;
    fprintf(stderr, "[MENU EXIT] response %u\n", result);
    if (result == 0) {
        fflush(NULL);
#if defined(_WIN32)
        ExitProcess(0);
#else
        _Exit(0);
#endif
    }
    /* Restore the native button hints and dismiss the native message box. */
    uint32_t saved_sp = g_esp, saved_si = g_esi, saved_di = g_edi;
    uint32_t saved_bx = g_ebx, saved_bp = g_ebp, saved_seh = g_seh_ebp;
    g_esi = MEM32(owner + 4);
    PUSH32(g_esp, 0x002B8FB9);
    sub_001DAFB0();
    /* The pause controller does not rebuild its button row every frame as
     * the front end does. Restore its root-menu hints after the popup hides. */
    uint32_t buttons=MEM32(MEM32(owner+8)+0x18);
    if(buttons) {
        vcall(buttons,0xC0,1,3,0);
        vcall(buttons,0xC8,2,0,0x12C);
        vcall(buttons,0xC8,2,1,pause ? 0x162 : 0x12D);
    }
    g_esi = saved_si; g_edi = saved_di; g_ebx = saved_bx;
    g_ebp = saved_bp; g_seh_ebp = saved_seh;
    g_esp = saved_sp + 8; g_eax = 1;
}

static void main_choice(void) { choice_made(0); }
static void pause_choice(void) { choice_made(1); }
static void main_response(void) { response(0); }
static void pause_response(void) { response(1); }

recomp_func_t rsc2_menu_exit_lookup(uint32_t va)
{
    switch (va) {
    case 0x002B7C20: return main_tick;
    case 0x002B7F10: return main_changed;
    case 0x002B8140: return main_choice;
    case 0x00165110: return pause_choice;
    case 0x002B85F0: return main_response;
    case 0x00164D60: return pause_response;
    default: return NULL;
    }
}
