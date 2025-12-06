import pygame
import random
import sys
import os
from highscore import add_score, load_scores


# ----------------------------
# Helpers
# ----------------------------
def resource_path(relpath: str) -> str:
    """Return path that works for dev and for PyInstaller bundles."""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relpath)
    return os.path.join(os.path.abspath("."), relpath)

# ----------------------------
# Config
# ----------------------------
GRID_W, GRID_H = 6, 6
TILE_SIZE = 72
PADDING = 20
INFO_PANEL_H = 100
SCREEN_W = GRID_W * TILE_SIZE + PADDING * 2 + 240
SCREEN_H = GRID_H * TILE_SIZE + PADDING * 2 + INFO_PANEL_H
FPS = 60

CHICKEN_TYPES = 4

# Colors
BG = (30, 30, 40)
PANEL = (45, 50, 65)
WHITE = (240, 240, 240)
GREY = (170, 178, 189)
ACCENT = (255, 211, 126)
RED = (220, 60, 60)
GREEN = (100, 220, 140)
BTN_BG = (60, 70, 90)
BTN_HOVER = (80, 95, 120)

# ----------------------------
# Initialization
# ----------------------------
pygame.init()
try:
    pygame.mixer.init()
    # Menü-Musik
    try:
        menu_music = resource_path("assets/music.wav")
    except:
        menu_music = None
except Exception:
    print("Warnung: Mixer konnte nicht initialisiert werden (kein Sound).")


screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
pygame.display.set_caption("Sort the CHICKENS! 🐔")
clock = pygame.time.Clock()

# Fonts (try emoji-capable, fallback to default)
EMOJI_FONTS = ["Segoe UI Emoji", "Noto Color Emoji", "Apple Color Emoji", "Arial Unicode MS"]
def load_font(size=28, emoji_test_char="🐔"):
    for name in EMOJI_FONTS:
        try:
            f = pygame.font.SysFont(name, size)
            surf = f.render(emoji_test_char, True, (0,0,0))
            if surf.get_width() > 0:
                return f
        except Exception:
            pass
    return pygame.font.SysFont(None, size)

font = load_font(22)
font_big = load_font(36)
font_title = load_font(44)

# ----------------------------
# Sounds (optional, tolerant)
# ----------------------------
def try_load_sound(path):
    try:
        s = pygame.mixer.Sound(resource_path(path))
        return s
    except Exception:
        return None

sounds = {
    "place": try_load_sound("assets/place.wav"),
    "match": try_load_sound("assets/match.wav"),
    "victory": try_load_sound("assets/win.wav"),
    "gameover": try_load_sound("assets/gameover.wav"),
}

# set sane volumes if available
if sounds["place"]: sounds["place"].set_volume(0.4)
if sounds["match"]: sounds["match"].set_volume(0.25)
if sounds["victory"]: sounds["victory"].set_volume(0.6)
if sounds["gameover"]: sounds["gameover"].set_volume(0.5)

# ----------------------------
# Game data
# ----------------------------
grid = [[-1 for _ in range(GRID_H)] for _ in range(GRID_W)]
rescued = 0
moves = 0
GOAL_CHICKENS = 256  # default (will be set from menu)
current_pair = None
last_place_time = 0  # global

# Menü-Hintergrundbild
menu_bg = pygame.image.load(resource_path("assets/BG.png")).convert()
menu_bg = pygame.transform.smoothscale(menu_bg, (SCREEN_W, SCREEN_H))


# Hühner Bilder
chicken_images = []
for i in range(CHICKEN_TYPES):
    path = resource_path(f"assets/chicken{i}.png")
    img = pygame.image.load(path).convert_alpha()
    img = pygame.transform.smoothscale(img, (TILE_SIZE-4, TILE_SIZE-4))
    chicken_images.append(img)


# States
state = "menu"  # menu, playing, gameover, victory
gameover_played = False
victory_played = False

# Touchpad placement guard
mouse_was_pressed = False

# ----------------------------
# Helpers: game logic
# ----------------------------
def new_pair():
    c1, c2 = random.randint(0, CHICKEN_TYPES-1), random.randint(0, CHICKEN_TYPES-1)
    orientation = random.choice(["h", "v"])
    if orientation == "h":
        offsets = [(0,0,c1), (1,0,c2)]
    else:
        offsets = [(0,0,c1), (0,1,c2)]
    return offsets, orientation

def can_place(x, y, offsets):
    for ox, oy, _ in offsets:
        tx, ty = x + ox, y + oy
        if tx < 0 or tx >= GRID_W or ty < 0 or ty >= GRID_H: return False
        if grid[tx][ty] != -1: return False
    return True

def find_matches():
    matches = set()
    # horizontal
    for y in range(GRID_H):
        run_len = 1
        for x in range(1, GRID_W+1):
            if x < GRID_W and grid[x][y] != -1 and grid[x][y] == grid[x-1][y]:
                run_len += 1
            else:
                if run_len >= 3:
                    for k in range(run_len):
                        matches.add((x-1-k, y))
                run_len = 1
    # vertical
    for x in range(GRID_W):
        run_len = 1
        for y in range(1, GRID_H+1):
            if y < GRID_H and grid[x][y] != -1 and grid[x][y] == grid[x][y-1]:
                run_len += 1
            else:
                if run_len >= 3:
                    for k in range(run_len):
                        matches.add((x, y-1-k))
                run_len = 1
    return matches

# Pop-Animationen: Liste von Effekten
pop_effects = []  # jeder Eintrag: { "x": int, "y": int, "img": Surface, "t": float }


def place_pair(x, y, offsets):
    global rescued
    for ox, oy, c in offsets:
        tx, ty = x + ox, y + oy
        grid[tx][ty] = c
    # on place sound
    if sounds["place"]: sounds["place"].play()
    # resolve matches (no gravity)
    while True:
        matches = find_matches()
        if not matches:
            break
        for (mx, my) in matches:
            # Animation hinzufügen — Originalbild sichern
            if 0 <= grid[mx][my] < len(chicken_images):
                pop_effects.append({
                    "x": mx,
                    "y": my,
                    "img": chicken_images[grid[mx][my]].copy(),
                    "t": 0.0  # Zeitstempel für Animation
                })

            grid[mx][my] = -1
            rescued += 1
        
        # Match-Sound abspielen
        if sounds["match"]:
            sounds["match"].play()


def any_move_possible(offsets):
    for x in range(GRID_W):
        for y in range(GRID_H):
            if can_place(x, y, offsets):
                return True
    return False

def reset_game_to_menu():
    pygame.mixer.music.stop()
    global grid, rescued, moves, current_pair, state, gameover_played, victory_played, GOAL_CHICKENS
    grid = [[-1 for _ in range(GRID_H)] for _ in range(GRID_W)]
    rescued = 0
    moves = 0
    current_pair = new_pair()
    state = "menu"
    gameover_played = False
    victory_played = False
    


def start_game(goal):
    pygame.mixer.music.stop()
    global GOAL_CHICKENS, current_pair, next_pair, state, rescued, moves, gameover_played, victory_played
    GOAL_CHICKENS = goal
    grid[:] = [[-1 for _ in range(GRID_H)] for _ in range(GRID_W)]
    rescued = 0
    moves = 0
    current_pair = new_pair()
    next_pair = new_pair()  # das kommende Paar
    state = "playing"
    gameover_played = False
    victory_played = False

# ----------------------------
# UI (buttons/overlay)
# ----------------------------
def draw_button(rect, text, hover=False):
    color = BTN_HOVER if hover else BTN_BG
    pygame.draw.rect(screen, color, rect, border_radius=10)
    pygame.draw.rect(screen, (20,20,30), rect, 2, border_radius=10)
    lbl = font.render(text, True, WHITE)
    screen.blit(lbl, lbl.get_rect(center=rect.center))

def draw_game():
    # board
    screen.fill(BG)
    pygame.draw.rect(screen, PANEL, (PADDING-6, PADDING-6, GRID_W*TILE_SIZE+12, GRID_H*TILE_SIZE+12), border_radius=16)
    for x in range(GRID_W):
        for y in range(GRID_H):
            rect = pygame.Rect(PADDING + x*TILE_SIZE, PADDING + y*TILE_SIZE, TILE_SIZE-4, TILE_SIZE-4)
            draw_chicken(rect, grid[x][y])


    # preview (mouse)
    if current_pair is not None:
        mx, my = pygame.mouse.get_pos()
        gx = (mx - PADDING) // TILE_SIZE
        gy = (my - PADDING) // TILE_SIZE
        if 0 <= gx < GRID_W and 0 <= gy < GRID_H:
            valid = can_place(gx, gy, current_pair[0])
            if valid:
                alpha = 140
                tint = None
            else:
                alpha = 180
                tint = RED
            for ox, oy, c in current_pair[0]:
                rect = pygame.Rect(PADDING + (gx+ox)*TILE_SIZE, PADDING + (gy+oy)*TILE_SIZE, TILE_SIZE-4, TILE_SIZE-4)
                draw_chicken(rect, c, alpha=alpha, tint=tint)

    # next-pair box
    base_x = GRID_W*TILE_SIZE + PADDING*2 + 20
    base_y = PADDING + 40
    label = font.render("Nächstes Paar:", True, WHITE)
    screen.blit(label, (base_x, base_y-30))
    for ox, oy, c in next_pair[0]:
        rect = pygame.Rect(base_x + ox*TILE_SIZE, base_y + oy*TILE_SIZE, TILE_SIZE-4, TILE_SIZE-4)
        draw_chicken(rect, c)

    # info panel
    info_y = PADDING + GRID_H*TILE_SIZE + 20
    pygame.draw.rect(screen, PANEL, (PADDING-6, info_y-6, GRID_W*TILE_SIZE+12, INFO_PANEL_H), border_radius=16)
    text1 = font.render(f"Sortiert: {rescued}/{GOAL_CHICKENS}", True, ACCENT)
    text2 = font.render(f"Züge: {moves}", True, WHITE)
    screen.blit(text1, (PADDING+10, info_y+10))
    screen.blit(text2, (PADDING+10, info_y+40))

    # Pop-Animationen rendern
    update_and_draw_pop_effects(dt)


def draw_chicken(rect, chicken_id, alpha=255, tint=None):
    if chicken_id < 0:
        pygame.draw.rect(screen, (60,65,80), rect, border_radius=12)
        return
    img = chicken_images[chicken_id]
    if tint:
        # draw tinted version on the fly
        temp = img.copy()
        tint_surf = pygame.Surface(temp.get_size(), pygame.SRCALPHA)
        tint_surf.fill((*tint, alpha))
        temp.blit(tint_surf, (0,0), special_flags=pygame.BLEND_RGBA_MULT)
        temp.set_alpha(255 if alpha >= 255 else alpha)
        screen.blit(temp, rect)
    else:
        tmp = img.copy()
        tmp.set_alpha(alpha)
        screen.blit(tmp, rect)

def update_and_draw_pop_effects(dt):
    remove_list = []

    for eff in pop_effects:
        eff["t"] += dt / 220.0  # Animation dauert ca. 0.22s

        t = eff["t"]
        if t >= 1.0:
            remove_list.append(eff)
            continue

        # Position berechnen
        px = PADDING + eff["x"] * TILE_SIZE
        py = PADDING + eff["y"] * TILE_SIZE

        # Animation: größer -> kleiner + fade
        scale = 1.0 + (0.25 * (1 - t))        # Start 1.25 → End 1.0
        alpha = int(255 * (1 - t))           # Fade-out
        angle = (t * 25) - 12                # leichte Rotation (-12° → +12°)

        img = pygame.transform.rotozoom(eff["img"], angle, scale)
        img.set_alpha(alpha)

        # zentriert zeichnen
        rect = img.get_rect(center=(
            px + TILE_SIZE // 2,
            py + TILE_SIZE // 2
        ))

        screen.blit(img, rect.topleft)

    # fertige Effekte entfernen
    for eff in remove_list:
        pop_effects.remove(eff)


def draw_overlay(title, subtitle=None, color=ACCENT, bg_style="fancy"):
    """
    bg_style: 'fancy' -> gradient / painted background; 'solid' -> dark translucent
    """
    if bg_style == "fancy":
        # draw a nice radial-ish background
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        for i in range(160, 0, -8):
            alpha = int(180 * (i / 160))
            radius = int(max(SCREEN_W, SCREEN_H) * (i / 160))
            pygame.draw.circle(overlay, (20, 30, 40, alpha), (SCREEN_W//2, SCREEN_H//2), radius)
        screen.blit(overlay, (0,0))
    else:
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0,0,0,180))
        screen.blit(overlay, (0,0))

    # framed panel
    panel_w, panel_h = SCREEN_W * 0.8, 220
    panel = pygame.Rect((SCREEN_W - panel_w)//2, (SCREEN_H - panel_h)//2 - 20, panel_w, panel_h)
    pygame.draw.rect(screen, PANEL, panel, border_radius=18)
    pygame.draw.rect(screen, (40,40,50), panel, 4, border_radius=18)

    # Title and subtitle
    title_surf = font_big.render(title, True, color)
    screen.blit(title_surf, title_surf.get_rect(center=(SCREEN_W//2, panel.centery - 20)))
    if subtitle:
        sub = font.render(subtitle, True, WHITE)
        screen.blit(sub, sub.get_rect(center=(SCREEN_W//2, panel.centery + 34)))

# ----------------------------
# Menu UI: klickbare buttons
# ----------------------------

btn_w, btn_h = 320, 54
btn_easy = pygame.Rect((SCREEN_W//2 - btn_w//2, 220, btn_w, btn_h))
btn_mid  = pygame.Rect((SCREEN_W//2 - btn_w//2, 290, btn_w, btn_h))
btn_hard = pygame.Rect((SCREEN_W//2 - btn_w//2, 360, btn_w, btn_h))
btn_highscore = pygame.Rect((SCREEN_W//2 - btn_w//2, 430, btn_w, btn_h))


# ----------------------------
# Main loop
# ----------------------------

current_pair = new_pair()
running = True
music_on = True
name_input = ""
entering_name = False

while running:
    dt = clock.tick(FPS)
    mouse_pos = pygame.mouse.get_pos()
    mouse_pressed = pygame.mouse.get_pressed()[0]

    # --- Event-Loop: nur einmal pro Frame ---
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        # Globale Tastatur
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if state == "playing":
                    state = "menu"
                else:
                    running = False
            elif event.key == pygame.K_m:  # Musik an/aus
                music_on = not music_on
                if music_on and menu_music:
                    pygame.mixer.music.play(-1)
                else:
                    pygame.mixer.music.stop()

        # State-spezifische Events
        if state == "menu":
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if btn_easy.collidepoint(event.pos): start_game(128)
                elif btn_mid.collidepoint(event.pos): start_game(256)
                elif btn_hard.collidepoint(event.pos): start_game(512)
                elif btn_highscore.collidepoint(event.pos): state = "highscore"

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_e: start_game(128)
                elif event.key == pygame.K_m: start_game(256)
                elif event.key == pygame.K_h: start_game(512)
                elif event.key == pygame.K_s: state = "highscore"

        elif state == "playing":
            triggered = False
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                triggered = True
            elif event.type == pygame.MOUSEMOTION and mouse_pressed and not mouse_was_pressed:
                triggered = True

            if triggered:
                mx, my = pygame.mouse.get_pos()
                gx = (mx - PADDING) // TILE_SIZE
                gy = (my - PADDING) // TILE_SIZE
                if 0 <= gx < GRID_W and 0 <= gy < GRID_H and can_place(gx, gy, current_pair[0]):
                    current_time = pygame.time.get_ticks()
                    if triggered and current_time - last_place_time > 100:  # 100ms Sperre
                            place_pair(gx, gy, current_pair[0])
                            last_place_time = current_time
                            moves += 1
                            current_pair = next_pair
                            next_pair = new_pair()

                    if rescued >= GOAL_CHICKENS:
                        state = "victory"
                        name_input = ""
                        entering_name = False
                        if sounds["victory"]: sounds["victory"].play()
                    elif not any_move_possible(current_pair[0]):
                        state = "gameover"

            mouse_was_pressed = mouse_pressed

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    reset_game_to_menu()

        elif state == "gameover":
            if not gameover_played:
                if sounds["gameover"]: sounds["gameover"].play()
                gameover_played = True
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    reset_game_to_menu()

        elif state == "victory":
            if not victory_played:
                if sounds["victory"]: sounds["victory"].play()
                victory_played = True
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    state = "enter_name"
                    name_input = ""
                    entering_name = True
                elif event.key == pygame.K_r:
                    reset_game_to_menu()

        elif state == "enter_name" and entering_name:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN and name_input.strip():
                    add_score(name_input.strip(), rescued)
                    state = "highscore"
                    entering_name = False
                elif event.key == pygame.K_BACKSPACE:
                    name_input = name_input[:-1]
                elif event.unicode.isprintable():
                    name_input += event.unicode

        elif state == "highscore":
            if event.type == pygame.KEYDOWN and event.key == pygame.K_q:
                state = "menu"

    # --- State Drawing ---
    if state == "menu":
        screen.blit(menu_bg, (0,0))
        if music_on and not pygame.mixer.music.get_busy() and menu_music:
            try:
                pygame.mixer.music.load(menu_music)
                pygame.mixer.music.set_volume(0.45)
                pygame.mixer.music.play(-1)
            except Exception: pass
        title = font_title.render("Sort the CHICKENS!", True, ACCENT)
        screen.blit(title, title.get_rect(center=(SCREEN_W//2, 120)))
        mx, my = mouse_pos
        draw_button(btn_easy, "Easy — 128 Hühner", btn_easy.collidepoint((mx,my)))
        draw_button(btn_mid,  "Medium — 256 Hühner", btn_mid.collidepoint((mx,my)))
        draw_button(btn_hard, "Hardcore — 512 Hühner", btn_hard.collidepoint((mx,my)))
        draw_button(btn_highscore, "Highscores", btn_highscore.collidepoint(mouse_pos))
        hint = font.render("Wähle per Klick oder Taste: E / M / H / S", True, WHITE)
        screen.blit(hint, hint.get_rect(center=(SCREEN_W//2, 520)))

    elif state == "playing":
        draw_game()
        base_x = GRID_W*TILE_SIZE + PADDING*2 + 20
        base_y = PADDING + 125
        label_hint = font.render(f"Musik: {'AN' if music_on else 'AUS'}  (Taste M)", True, GREY)
        screen.blit(label_hint, (base_x, base_y + 70))

    elif state == "gameover":
        draw_game()
        draw_overlay("GAME OVER", "Drücke [R] zum Neustart", color=RED, bg_style="fancy")

    elif state == "victory":
        draw_game()
        draw_overlay("Alle Hühner ordentlich sortiert!", "Drücke [Enter] für Highscore", color=ACCENT, bg_style="fancy")

    elif state == "enter_name":
        draw_game()
        draw_overlay("Gib deinen Namen ein:", f"Name: {name_input}", color=ACCENT)

    elif state == "highscore":
        screen.blit(menu_bg, (0,0))
        if music_on and not pygame.mixer.music.get_busy() and menu_music:
            try:
                pygame.mixer.music.load(menu_music)
                pygame.mixer.music.set_volume(0.45)
                pygame.mixer.music.play(-1)
            except Exception: pass
        title = font_title.render("Highscores", True, ACCENT)
        screen.blit(title, title.get_rect(center=(SCREEN_W//2, 80)))
        scores = load_scores()
        start_y = 150
        for i, entry in enumerate(scores):
            txt = font.render(f"{i+1}. {entry['name']} — {entry['score']}", True, WHITE)
            screen.blit(txt, txt.get_rect(center=(SCREEN_W//2, start_y + i*30)))
        hint = font.render("Drücke [Q] für Hauptmenü", True, WHITE)
        screen.blit(hint, hint.get_rect(center=(SCREEN_W//2, SCREEN_H-60)))

    pygame.display.flip()



pygame.quit()
sys.exit()
