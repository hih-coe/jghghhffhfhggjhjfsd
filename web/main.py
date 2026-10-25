# -*- coding: utf-8 -*-
# main.py - Part 1: Initialization & Audio Optimization
import sys
import os
import pygame
import random
import asyncio  # Web concurrency driver

from characters import Player, Buddy
from enemy import Enemy
from game_engine import (
    Camera, Menu3D, TiramisuCake3D, GameHUD,
    draw_detailed_house, draw_giant_tree,
    update_game_simulation
)

STATE_MENU = "MENU"
STATE_TRANSITION = "TRANSITION"
STATE_GAMEPLAY = "GAMEPLAY"
STATE_VICTORY = "VICTORY"

async def main():
    # Performance Optimization 1: Adjust mixer buffer to kill audio lag
    try: pygame.mixer.pre_init(44100, -16, 2, 2048)
    except Exception: pass
    pygame.init()
    
    sw, sh = 800, 600
    screen = pygame.display.set_mode((sw, sh))
    pygame.display.set_caption("Loki City Defense - Final")
    clock = pygame.time.Clock()

    mw, mh = 4800, 3600
    city_r = pygame.Rect(2100, 1500, 600, 600)
    sq_r = pygame.Rect(2300, 1700, 200, 200)
    
    ctx = {"MAP_SIZE": (mw, mh), "CITY_RECT": city_r, "CENTER_SQUARE_RECT": sq_r}
    menu_sys = Menu3D(sw, sh)
    cake_sys = TiramisuCake3D(sw, sh)
    hud_sys = GameHUD()
    
    curr_state = STATE_MENU
    vic_timer = 0.0
    g_config = {}
    z_targets = {1: 2.0, 2: 0.65, 3: 0.3} 
    curr_zoom = 2
# main.py - Part 2: Static Pre-rendering Map Buffers
    g_vars = {
        "current_map": "CITY", "base_hp": 100.0,
        "game_timer": 0, "enemy_spawn_timer": 0,
        "total_spawn_target": 35, "enemies_killed": 0,
        "breach_active": False, "breacher": None,
        "breach_cooldown": 0, "breach_hole_pos": None,
        "music_muted": False, "music_started": False,
        "saved_volume": 0.5, "show_enemy_hp": True
    }
    
    lilly = Player(2400, 1800, "MIKASA")  
    partners, enemies = [], []
    camera = Camera(sw, sh, mw, mh, zoom=2.0)
    trees = [(random.randint(100, mw-100), random.randint(100, mh-100)) for _ in range(50)]

    # Performance Optimization 2: Pre-render environments to offline surfaces
    city_bg_surf = pygame.Surface((mw, mh))
    city_bg_surf.fill((120, 160, 115))
    for x in range(0, mw, 64):
        for y in range(0, mh, 64):
            pygame.draw.rect(city_bg_surf, (110, 150, 105), pygame.Rect(x, y, 64, 64), 1)
    pygame.draw.rect(city_bg_surf, (145, 140, 125), city_r)
    pygame.draw.rect(city_bg_surf, (75, 75, 80), city_r, 16)
    
    # Bake houses onto cache surface
    for x in range(city_r.left + 35, city_r.right - 65, 115):
        for y in range(city_r.top + 35, city_r.bottom - 65, 115):
            h_r = pygame.Rect(x, y, 48, 54)
            if not sq_r.colliderect(h_r): draw_detailed_house(city_bg_surf, h_r)
    pygame.draw.rect(city_bg_surf, (110, 105, 95), sq_r)

    # Forest background cache
    forest_bg_surf = pygame.Surface((mw, mh))
    forest_bg_surf.fill((45, 85, 50))
    for x in range(0, mw, 64):
        for y in range(0, mh, 64):
            pygame.draw.rect(forest_bg_surf, (35, 75, 40), pygame.Rect(x, y, 64, 64), 1)

    p = "theme_song.ogg"
    if os.path.exists(p):
        try:
            pygame.mixer.music.load(p)
            pygame.mixer.music.set_volume(g_vars["saved_volume"])
        except Exception: pass

    running = True
# main.py - Part 3: Non-blocking Inputs & AI Simulation Engine
    while running:
        # Performance Optimization 3: Lock Wasm execution framework at 30 FPS
        clock.tick(30)
        keys = pygame.key.get_pressed()
        m_pos = pygame.mouse.get_pos()
        
        touch_points = []
        if pygame.mouse.get_pressed(): touch_points.append(m_pos)

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: running = False
            
            if curr_state == STATE_MENU:
                res = menu_sys.handle_input(ev)
                if res:
                    if res["action"] == "LETTER_OPENED" and not g_vars["music_started"]:
                        try:
                            pygame.mixer.music.play(-1)
                            g_vars["music_started"] = True
                        except Exception: pass
                    elif res["action"] == "START_CLICKED":
                        g_config = res["config"]
                        curr_state = STATE_TRANSITION
                        partners.append(Buddy(sq_r.left, sq_r.centery, "ARMIN"))
                        partners.append(Buddy(sq_r.right, sq_r.centery, "EREN"))
            
            elif curr_state == STATE_GAMEPLAY:
                if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    m_rect = pygame.Rect(sw - 50, 60, 36, 36)
                    eye_rect = pygame.Rect(sw - 95, 60, 36, 36)
                    zoom_btn_rect = pygame.Rect(8, sh - 45, 180, 32)
                    
                    if m_rect.collidepoint(ev.pos):
                        g_vars["music_muted"] = not g_vars["music_muted"]
                        v = 0.0 if g_vars["music_muted"] else g_vars["saved_volume"]
                        try: pygame.mixer.music.set_volume(v)
                        except Exception: pass
                    elif eye_rect.collidepoint(ev.pos):
                        g_vars["show_enemy_hp"] = not g_vars["show_enemy_hp"]
                    elif zoom_btn_rect.collidepoint(ev.pos):
                        curr_zoom = curr_zoom + 1 if curr_zoom < 3 else 1
                
                if not g_vars["breach_active"] and ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_k: lilly.trigger_aerial_slash(enemies)
                    elif ev.key == pygame.K_i: curr_zoom = 1 if curr_zoom == 2 else (2 if curr_zoom == 3 else 1)
                    elif ev.key == pygame.K_o: curr_zoom = 3 if curr_zoom == 2 else (2 if curr_zoom == 1 else 3)

        if curr_state in [STATE_MENU, STATE_TRANSITION]:
            if curr_state == STATE_MENU:
                g_vars["saved_volume"] = menu_sys.volume
                try:
                    if not g_vars["music_muted"]: pygame.mixer.music.set_volume(g_vars["saved_volume"])
                except Exception: pass
            if menu_sys.update_and_draw(screen): curr_state = STATE_GAMEPLAY
                
        elif curr_state == STATE_GAMEPLAY:
            camera.update(lilly.rect)
            camera.zoom += (z_targets[curr_zoom] - camera.zoom) * 0.1
            lilly.handle_rope_input(keys, touch_points, camera, sw, sh, enemies)

            sim_res = update_game_simulation(ctx, lilly, enemies, partners, g_vars, g_config)
            if sim_res == "VICTORY": curr_state = STATE_VICTORY
            elif sim_res == "RESET_TO_MENU":
                curr_state = STATE_MENU
                menu_sys = Menu3D(sw, sh)
                menu_sys.ui_state = "MAIN"
                menu_sys.volume = g_vars["saved_volume"]
                g_vars.update({
                    "base_hp": 100.0, "game_timer": 0, "enemy_spawn_timer": 0,
                    "breach_cooldown": 0, "enemies_killed": 0,
                    "breach_active": False, "breacher": None,
                    "breach_hole_pos": None, "current_map": "CITY"
                })
                partners.clear(); enemies.clear()
                lilly = Player(2400, 1800, "MIKASA"); curr_zoom = 2

            if not g_vars["breach_active"]:
                lilly.handle_input(keys, touch_points, sw, sh)
                lilly.update_swing_physics(enemies)

            for b in partners: b.update_ai_with_strategy(enemies, g_vars["base_hp"])
            for e in enemies:
                if (g_vars["current_map"] == "CITY" and not g_vars["breach_active"] and city_r.colliderect(e.rect)):
                    if g_vars["game_timer"] % 30 == 0: g_vars["base_hp"] -= (4.0 if e.variant == "COLOSSAL" else 2.0)
                    if e.rect.centerx < city_r.left + 22: e.x -= 3
                    if e.rect.centerx > city_r.right - 22: e.x += 3
                    if e.rect.centery < city_r.top + 22: e.y -= 3
                    if e.rect.centery > city_r.bottom - 22: e.y += 3
                    e.rect.x, e.rect.y = int(e.x), int(e.y)
                is_sw = (lilly.state == "SWINGING")
                g_vars["base_hp"] = e.update_ai(sq_r, lilly, g_vars["game_timer"]/1800.0, g_vars["base_hp"], g_vars["breach_active"], e == g_vars["breacher"], is_sw)
            
            ini_cnt = len(enemies)
            enemies = [e for e in enemies if not e.is_dead]
            g_vars["enemies_killed"] += (ini_cnt - len(enemies))
# main.py - Part 4: Dynamic Fast Blitting & Async Frame Outputs
            active_bg = city_bg_surf if g_vars["current_map"] == "CITY" else forest_bg_surf
            sub_rect = pygame.Rect(camera.x, camera.y, int(sw / camera.zoom), int(sh / camera.zoom))
            try:
                cropped_bg = active_bg.subsurface(sub_rect.clip(pygame.Rect(0, 0, mw, mh)))
                scaled_bg = pygame.transform.scale(cropped_bg, (sw, sh))
                screen.blit(scaled_bg, (0, 0))
            except Exception:
                screen.fill((120, 160, 115) if g_vars["current_map"] == "CITY" else (45, 85, 50))

            if curr_zoom == 3:
                screen.blit(*camera.apply_surface(lilly.minecraft_head, lilly.rect.topleft))
                for e in enemies: screen.blit(*camera.apply_surface(e.minecraft_head, e.rect.topleft))
            else:
                if g_vars["current_map"] == "FOREST":
                    for tx, ty in trees: draw_giant_tree(screen, camera, tx, ty)

                if g_vars["breach_hole_pos"] and g_vars["current_map"] == "CITY":
                    bh_x, bh_y = g_vars["breach_hole_pos"]
                    pygame.draw.circle(screen, (40, 35, 35), camera.apply(pygame.Rect(int(bh_x), int(bh_y), 2, 2)).center, int(35 * camera.zoom))

                for e in enemies: e.draw(screen, camera, show_hp_bar=g_vars["show_enemy_hp"])
                for b in partners: 
                    screen.blit(*camera.apply_surface(b.image, (b.rect.x - 48, b.rect.y - 48)))
                    b.draw_buddy_hp(screen, camera)
                    
                p_center = camera.apply(lilly.rect).center
                if lilly.anchor_l:
                    anc_l_c = camera.apply(pygame.Rect(int(lilly.anchor_l), int(lilly.anchor_l), 4, 4)).center
                    pygame.draw.line(screen, (240, 240, 245), p_center, anc_l_c, max(2, int(3 * camera.zoom)))
                if lilly.anchor_r:
                    anc_r_c = camera.apply(pygame.Rect(int(lilly.anchor_r), int(lilly.anchor_r), 4, 4)).center
                    pygame.draw.line(screen, (240, 240, 245), p_center, anc_r_c, max(2, int(3 * camera.zoom)))

                screen.blit(*camera.apply_surface(lilly.image, (lilly.rect.x - 48, lilly.rect.y - 48)))

            hud_sys.draw_all(screen, sw, sh, g_vars["total_spawn_target"], g_vars["enemies_killed"], g_vars["base_hp"], g_vars["current_map"], lilly.hp, partners, g_vars["music_muted"], g_vars["show_enemy_hp"], curr_zoom)
            
            # Draw semi-transparent virtual pads for mobile touchscreen overlay
            pygame.draw.circle(screen, (255, 255, 255, 45), (100, sh - 100), 55, 2)
            pygame.draw.rect(screen, (240, 245, 255, 60), (sw - 125, sh - 175, 105, 45), border_radius=6)
            screen.blit(pygame.font.Font(None, 22).render("SLASH (K)", True, (255, 255, 255)), (sw - 110, sh - 160))

        elif curr_state == STATE_VICTORY:
            vic_timer = min(1.0, vic_timer + 0.01)
            screen.fill((140, 135, 120))
            cake_sys.draw(screen, vic_timer)

        # Performance Boost: Lightweight incremental frame updates
        pygame.display.update() 
        await asyncio.sleep(0)  # Yield block timeline back to the browser sandbox
        
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    asyncio.run(main())
