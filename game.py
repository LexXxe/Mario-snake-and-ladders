import pygame
import random
import sys
import os
import math
from pygame import mixer

# Initialize pygame
pygame.init()
mixer.init()

# Load and play background music
try:
    pygame.mixer.music.load("assets/main.wav")
    pygame.mixer.music.play(-1)
except:
    pass

# Screen configuration
WIDTH, HEIGHT = 900, 900
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Super Mario Snakes & Ladders")

# Colors (Mario theme)
RED = (227, 38, 54)
GREEN = (34, 177, 76)
BLUE = (0, 120, 215)
WHITE = (255, 255, 255)
BROWN = (139, 69, 19)
YELLOW = (255, 242, 0)
BLACK = (0, 0, 0)
PINK = (255, 105, 180)
VIOLET = (148, 0, 211)

dice_animation = False
dice_animation_frames = 0
dice_animation_values = []
dice_animation_speed = 5  # Velocidad de la animación (frames por cambio)
dice_final_value = 1


snake_animation = None
ladder_animation = None
current_animation_path = []
current_animation_index = 0
animation_speed = 2  # Velocidad de la animación (píxeles por frame)

# Animation tuning: smaller delta => slower/smoother
ANIMATION_STEP_DELTA = 0.35  # amount of path-indices advanced per frame (fractional for interpolation)
MOVE_STEP_MS = 300  # milliseconds per board-step when moving a player
last_move_tick = 0

# Smooth movement state
move_anim_active = False
move_path = []  # list of (sx, sy, ex, ey) per cell-step in board coordinates
move_step_index = 0
move_step_progress = 0.0
move_last_time = 0

current_animation = None
animation_path = []
animation_step = 0
animation_player = None
animation_type = None

def start_animation(player_index, start_pos, end_pos, anim_type):
    """Inicia una animación de serpiente o escalera"""
    global current_animation, animation_path, animation_step, animation_player, animation_type
    
    # Obtener posiciones físicas
    start_row, start_col = get_cell_position(start_pos)
    end_row, end_col = get_cell_position(end_pos)
    
    start_physical_row = BOARD_SIZE - 1 - start_row
    end_physical_row = BOARD_SIZE - 1 - end_row
    # Coordenadas en espacio del tablero (superficie lógica)
    start_x = start_col * CELL_SIZE + CELL_SIZE // 2
    start_y = start_physical_row * CELL_SIZE + CELL_SIZE // 2
    end_x = end_col * CELL_SIZE + CELL_SIZE // 2
    end_y = end_physical_row * CELL_SIZE + CELL_SIZE // 2
    
    # Crear camino de animación
    animation_path = []
    # Increase steps for smoother motion
    steps = 60 if anim_type == "snake" else 45
    for i in range(steps + 1):
        t = i / steps
        if anim_type == "snake":
            # Curved path for snakes (board coordinates)
            x = start_x + (end_x - start_x) * t
            y = start_y + (end_y - start_y) * t - (CELL_SIZE * 2) * math.sin(math.pi * t)
        else:
            # Straight path for ladders
            x = start_x + (end_x - start_x) * t
            y = start_y + (end_y - start_y) * t
        animation_path.append((x, y))
    
    # Configurar animación
    current_animation = True
    animation_step = 0
    animation_player = player_index
    animation_type = anim_type
    
    # Reproducir sonido
    if anim_type == "snake" and snake_sound:
        snake_sound.play()
    elif anim_type == "ladder" and ladder_sound:
        ladder_sound.play()

def start_snake_animation(player_index, start_pos, end_pos):
    """Inicia la animación para caer por una serpiente"""
    global snake_animation, current_animation_path, current_animation_index
    
    # Obtener posiciones físicas
    start_row, start_col = get_cell_position(start_pos)
    end_row, end_col = get_cell_position(end_pos)
    
    start_physical_row = BOARD_SIZE - 1 - start_row
    end_physical_row = BOARD_SIZE - 1 - end_row
    # Coordenadas en espacio del tablero (superficie lógica)
    start_x = start_col * CELL_SIZE + CELL_SIZE // 2
    start_y = start_physical_row * CELL_SIZE + CELL_SIZE // 2
    end_x = end_col * CELL_SIZE + CELL_SIZE // 2
    end_y = end_physical_row * CELL_SIZE + CELL_SIZE // 2
    
    # Create smoothed path (no blocking delays)
    current_animation_path = []
    steps = 60
    for i in range(steps + 1):
        t = i / steps
        x = start_x + (end_x - start_x) * t
        y = start_y + (end_y - start_y) * t - (CELL_SIZE * 2) * math.sin(math.pi * t)
        current_animation_path.append((x, y))
    snake_animation = player_index
    current_animation_index = 0
    players[player_index]["pixel_position_board"] = current_animation_path[0]
    players[player_index]["position"] = end_pos
    if snake_sound:
        snake_sound.play()

def start_ladder_animation(player_index, start_pos, end_pos):
    """Inicia la animación para subir por una escalera"""
    global ladder_animation, current_animation_path, current_animation_index
    
    # Obtener posiciones físicas
    start_row, start_col = get_cell_position(start_pos)
    end_row, end_col = get_cell_position(end_pos)
    
    start_physical_row = BOARD_SIZE - 1 - start_row
    end_physical_row = BOARD_SIZE - 1 - end_row
    # Coordenadas en espacio del tablero (superficie lógica)
    start_x = start_col * CELL_SIZE + CELL_SIZE // 2
    start_y = start_physical_row * CELL_SIZE + CELL_SIZE // 2
    end_x = end_col * CELL_SIZE + CELL_SIZE // 2
    end_y = end_physical_row * CELL_SIZE + CELL_SIZE // 2
    
    # Create smoothed path for ladder (no blocking)
    current_animation_path = []
    steps = 45
    for i in range(steps + 1):
        t = i / steps
        x = start_x + (end_x - start_x) * t
        y = start_y + (end_y - start_y) * t
        current_animation_path.append((x, y))
    ladder_animation = player_index
    current_animation_index = 0
    players[player_index]["pixel_position_board"] = current_animation_path[0]
    players[player_index]["position"] = end_pos
    if ladder_sound:
        ladder_sound.play()


def update_animation():
    """Actualiza la animación en curso"""
    global animation_step, current_animation
    
    if not current_animation:
        return
    # Advance by a fractional delta for smooth interpolation
    animation_step += ANIMATION_STEP_DELTA

    if animation_step < len(animation_path) - 1:
        i0 = int(animation_step)
        t = animation_step - i0
        # Ease in-out (smoothstep)
        et = t * t * (3 - 2 * t)
        x0, y0 = animation_path[i0]
        x1, y1 = animation_path[i0 + 1]
        x = x0 + (x1 - x0) * et
        y = y0 + (y1 - y0) * et
        players[animation_player]["pixel_position_board"] = (x, y)
    else:
        # Finish animation
        players[animation_player]["pixel_position_board"] = None
        current_animation = False
        animation_step = 0

        # Update logical position (if not already set)
        if animation_type == "snake":
            end_pos = snakes.get(players[animation_player]["position"], players[animation_player]["position"])
        else:
            end_pos = ladders.get(players[animation_player]["position"], players[animation_player]["position"])
        players[animation_player]["position"] = end_pos

        # Check special tiles
        if players[animation_player]["position"] in special_tiles:
            handle_special_tile(players[animation_player]["position"])

        global game_state
        game_state = "check_position"

# Game settings
BOARD_SIZE = 10
# CELL_SIZE and board origin will be calculados dinámicamente
CELL_SIZE = 70
BOARD_ORIGIN_X = 50
BOARD_ORIGIN_Y = 50
BOARD_WIDTH = BOARD_SIZE * CELL_SIZE
BOARD_HEIGHT = BOARD_SIZE * CELL_SIZE


def recalc_layout(win_w, win_h):
    """Recalcula `CELL_SIZE`, `BOARD_ORIGIN_X/Y` y escala assets para mantener el juego centrado."""
    global WIDTH, HEIGHT, CELL_SIZE, BOARD_WIDTH, BOARD_HEIGHT, BOARD_ORIGIN_X, BOARD_ORIGIN_Y
    WIDTH, HEIGHT = win_w, win_h

    padding = int(min(WIDTH, HEIGHT) * 0.05)
    # Reservar un espacio inferior para UI (dados, textos)
    reserved_bottom = int(HEIGHT * 0.14)

    available_w = max(20, WIDTH - 2 * padding)
    available_h = max(20, HEIGHT - 2 * padding - reserved_bottom)

    max_board_pixel = min(available_w, available_h)

    # Forzar un mínimo razonable pero permitir que se reduzca para que quepa
    max_board_pixel = max(20, max_board_pixel)

    # Calcular CELL_SIZE para que el tablero quepa en el área disponible
    CELL_SIZE = max(4, max_board_pixel // BOARD_SIZE)
    BOARD_WIDTH = CELL_SIZE * BOARD_SIZE
    BOARD_HEIGHT = CELL_SIZE * BOARD_SIZE

    # Centrar en el área disponible (respetando padding y reserved_bottom)
    BOARD_ORIGIN_X = max(padding, (WIDTH - BOARD_WIDTH) // 2)
    # Colocar en Y de forma centrada dentro del área superior (sin invadir reserved_bottom)
    top_area_height = HEIGHT - reserved_bottom - padding
    BOARD_ORIGIN_Y = padding + max(0, (top_area_height - BOARD_HEIGHT) // 2)
    
    # Calcular dimensiones de renderizado (por si necesitamos escalar visualmente)
    global DISPLAY_CELL_SIZE, DISPLAY_BOARD_WIDTH, DISPLAY_BOARD_HEIGHT, DISPLAY_BOARD_ORIGIN_X, DISPLAY_BOARD_ORIGIN_Y
    # Ajuste para que la representación visual del tablero quepa en el área disponible
    available_w = WIDTH - 2 * padding
    available_h = HEIGHT - 2 * padding - reserved_bottom
    scale = min(1.0, available_w / max(1, BOARD_WIDTH), available_h / max(1, BOARD_HEIGHT))
    DISPLAY_CELL_SIZE = max(2, int(CELL_SIZE * scale))
    DISPLAY_BOARD_WIDTH = DISPLAY_CELL_SIZE * BOARD_SIZE
    DISPLAY_BOARD_HEIGHT = DISPLAY_CELL_SIZE * BOARD_SIZE
    DISPLAY_BOARD_ORIGIN_X = max(padding, (WIDTH - DISPLAY_BOARD_WIDTH) // 2)
    DISPLAY_BOARD_ORIGIN_Y = padding + max(0, (top_area_height - DISPLAY_BOARD_HEIGHT) // 2)

    # Reescalar background
    global background_img
    try:
        background_img = pygame.transform.scale(background_img_orig, (WIDTH, HEIGHT))
    except:
        pass
    # Reescalar sprites dependientes del tamaño de celda
    try:
        for p in players:
            try:
                target = max(16, int(DISPLAY_CELL_SIZE * 0.6))
                p['image_scaled'] = pygame.transform.smoothscale(p['image'], (target, target))
            except Exception:
                p['image_scaled'] = p['image']

        # Escalar dados para mostrarlos en la UI
        global dice_imgs_scaled
        dice_imgs_scaled = []
        dsize = max(20, int(DISPLAY_CELL_SIZE * 0.9))
        for img in dice_imgs:
            try:
                dice_imgs_scaled.append(pygame.transform.smoothscale(img, (dsize, dsize)))
            except Exception:
                dice_imgs_scaled.append(img)

        # Escalar powerups para que se adapten al tamaño de la celda
        for key in list(powerup_sprites.keys()):
            try:
                sz = max(16, DISPLAY_CELL_SIZE // 2)
                powerup_sprites[key] = pygame.transform.smoothscale(powerup_sprites[key], (sz, sz))
            except Exception:
                pass
    except Exception:
        # Silently ignore scaling errors to keep game running
        pass
def load_image(name, size=None):
    """Intentar cargar `assets/{name}.png`. Si no existe, generar un placeholder mejorado."""
    path = f"assets/{name}.png"
    if os.path.exists(path):
        try:
            img = pygame.image.load(path).convert_alpha()
            return pygame.transform.scale(img, size) if size else img
        except Exception:
            pass

    w, h = size if size else (80, 80)
    surf = pygame.Surface((w, h), pygame.SRCALPHA)

    lower = name.lower()

    # Character portraits: rounded badge with simple face and hat/flower
    if any(k in lower for k in ("mario", "luigi", "peach", "daisy")):
        # Choose color
        cmap = {'mario': (220, 20, 60), 'luigi': (20, 140, 20), 'peach': (255, 170, 200), 'daisy': (255, 220, 120)}
        col = (180, 180, 180)
        for k, c in cmap.items():
            if k in lower:
                col = c
                break
        pygame.draw.rect(surf, (240, 240, 240), (0, 0, w, h), border_radius=max(4, w//8))
        cx, cy = w//2, h//2
        r = min(w, h)//2 - 6
        pygame.draw.circle(surf, col, (cx, cy), r)
        pygame.draw.circle(surf, (0,0,0), (cx - r//3, cy - r//8), max(1, r//10))
        pygame.draw.circle(surf, (0,0,0), (cx + r//3, cy - r//8), max(1, r//10))
        # simple mouth
        pygame.draw.arc(surf, (120, 0, 0), (cx - r//2, cy, r, r//2), math.pi/8, math.pi - math.pi/8, 2)
        # hat or flower
        if 'mario' in lower or 'luigi' in lower:
            hat_col = (160, 20, 40) if 'mario' in lower else (20, 120, 20)
            pygame.draw.rect(surf, hat_col, (cx - r, cy - r - 4, r*2, r//2), border_radius=max(3, r//8))
        elif 'peach' in lower or 'daisy' in lower:
            pygame.draw.polygon(surf, (255, 200, 220), [(cx - r, cy - r//3), (cx, cy - r), (cx + r, cy - r//3)])
        return surf

    # Dice faces
    if lower.startswith('dice_'):
        try:
            val = int(lower.split('_')[1])
        except Exception:
            val = 1
        pygame.draw.rect(surf, (250,250,250), (0,0,w,h), border_radius=max(6, w//6))
        pygame.draw.rect(surf, (40,40,40), (0,0,w,h), 2, border_radius=max(6, w//6))
        pip = max(3, w//12)
        coords = {
            1: [(w//2, h//2)],
            2: [(w//4, h//4), (3*w//4, 3*h//4)],
            3: [(w//4, h//4), (w//2, h//2), (3*w//4, 3*h//4)],
            4: [(w//4, h//4), (w//4, 3*h//4), (3*w//4, h//4), (3*w//4, 3*h//4)],
            5: [(w//4, h//4), (w//4, 3*h//4), (w//2, h//2), (3*w//4, h//4), (3*w//4, 3*h//4)],
            6: [(w//4, h//6), (w//4, h//2), (w//4, 5*h//6), (3*w//4, h//6), (3*w//4, h//2), (3*w//4, 5*h//6)]
        }
        for (px, py) in coords.get(val, coords[1]):
            pygame.draw.circle(surf, (30,30,30), (px, py), pip)
        return surf

    # Snake head/body
    if 'snake_head' in lower:
        pygame.draw.ellipse(surf, (20,140,20), (0, h//6, w, h*2//3))
        pygame.draw.polygon(surf, (10,100,10), [(w-2, h//2), (w-8, h//2-6), (w-8, h//2+6)])
        pygame.draw.circle(surf, (255,255,255), (w*3//4, h//2 - h//8), max(1, w//20))
        return surf

    if 'snake_body' in lower:
        for i in range(0, w, max(6, w//8)):
            pygame.draw.ellipse(surf, (20,130,20), (i, h//6, max(8, w//5), h*2//3))
        return surf

    if 'ladder' in lower:
        rail_w = max(3, w//12)
        pygame.draw.rect(surf, (140,90,40), (w//8, 0, rail_w, h))
        pygame.draw.rect(surf, (140,90,40), (w - w//8 - rail_w, 0, rail_w, h))
        for i in range(1, 5):
            ry = i * h // 5
            pygame.draw.rect(surf, (170,120,60), (w//8 + rail_w + 2, ry - max(2,h//50), w - w//4 - 2*rail_w - 4, max(3, h//30)))
        return surf

    if 'background' in lower:
        for i in range(h):
            t = i / max(1, h)
            color = (int(240 - 30 * t), int(240 - 40 * t), int(255 - 20 * t))
            pygame.draw.line(surf, color, (0, i), (w, i))
        return surf

    # Generic placeholder: neutral rounded box with label
    pygame.draw.rect(surf, (230, 230, 230), (0, 0, w, h), border_radius=max(4, w//12))
    pygame.draw.rect(surf, (140,140,140), (0, 0, w, h), 2, border_radius=max(4, w//12))
    try:
        font = pygame.font.SysFont(None, max(12, w // 6))
        label = font.render(name, True, (50, 50, 50))
        surf.blit(label, (max(6, w//12), h - label.get_height() - max(6, h//12)))
    except Exception:
        pass
    return surf

# Load sounds
def load_sound(name):
    try:
        return mixer.Sound(f"assets/{name}.wav")
    except:
        return None

# Create assets directory if not exists
if not os.path.exists("assets"):
    os.makedirs("assets")

# Load images
mario_img = load_image("mario", (40, 40))
luigi_img = load_image("luigi", (40, 40))
peach_img = load_image("peach", (40, 40))
daisy_img = load_image("daisy", (40, 40))
yoshi_img = load_image("yoshi", (40, 40))
rosalina_img = load_image("rosalina", (40, 40))
dice_imgs = [load_image(f"dice_{i}", (60, 60)) for i in range(1, 7)]
# Mantener copia original del background para reescalar dinámicamente
background_img = load_image("mario_background", (WIDTH, HEIGHT))
background_img_orig = background_img.copy() if background_img else None

# Load snake and ladder sprites
snake_head_img = load_image("snake_head", (40, 40))
snake_body_img = load_image("snake_body", (40, 40))
ladder_top_img = load_image("ladder_top", (50, 30))
ladder_rung_img = load_image("ladder_rung", (90, 30))

# All available characters
all_characters = [
    {"name": "Mario", "image": mario_img, "color": RED},
    {"name": "Peach", "image": peach_img, "color": PINK},
    {"name": "Luigi", "image": luigi_img, "color": GREEN},
    {"name": "Yoshi", "image": yoshi_img, "color": BLACK},
    {"name": "Rosalina", "image": rosalina_img, "color": BLUE},
    {"name": "Daisy", "image": daisy_img, "color": YELLOW},
]

# Load sounds
dice_sound = load_sound("dice_roll")
ladder_sound = load_sound("ladder")
snake_sound = load_sound("snake")
win_sound = load_sound("win")
coin_sound = load_sound("coin")
star_sound = load_sound("star")
powerup_sound = load_sound("powerup")
flower_sound = load_sound("flower")
bowser_sound = load_sound("bowser")

# Fonts
font_large = pygame.font.SysFont("Arial", 36, bold=True)
font_medium = pygame.font.SysFont("Arial", 24)
font_small = pygame.font.SysFont("Arial", 18)

# Game board
board = list(range(1, 101))

# Snakes (tubes) and ladders (vines) {start: end}
snakes = {
    26:10,
    56: 1,
    60: 23,   # Bowser's tube
    75: 28,   # Piranha plant
    90: 48,   # Lava pit
    97: 87,    # Thwomp
    99: 63  # Bowser's castle

}

ladders = {
    
    3:20,
    6:14,
    11:28,
    15:34,
    22:37,
    24:67,
    49:67,
    61:78,
    81:98,
    88:91


}

# Special tiles
special_tiles = {
    5: {"type": "star", "effect": "extra_turn"},
    16: {"type": "mushroom", "effect": "move_forward", "value": 3},
    40: {"type": "mushroom", "effect": "move_forward", "value": 3},
    35: {"type": "flower", "effect": "move_forward", "value": 5},
    50: {"type": "coin", "effect": "move_forward", "value": 2},
    65: {"type": "coin", "effect": "move_forward", "value": 2},
    77: {"type": "bowser", "effect": "move_back", "value": 5},
    13: {"type": "bowser", "effect": "move_back", "value": 5},
    27: {"type": "bowser", "effect": "move_back", "value": 5},
   #98: {"type": "bowser", "effect": "move_back", "value": 5}
}

# Players

players = [
    {"name": "Mario", "position": 1, "image": mario_img, "color": RED, "immunity": False, "pixel_position_board": None},
    {"name": "Peach", "position": 1, "image": peach_img, "color": PINK, "immunity": False, "pixel_position_board": None},
    {"name": "Luigi", "position": 1, "image": luigi_img, "color": GREEN, "immunity": False, "pixel_position_board": None},
    {"name": "Yoshi", "position": 1, "image": yoshi_img, "color": WHITE, "immunity": False, "pixel_position_board": None},
    {"name": "Rosalina", "position": 1, "image": rosalina_img, "color": BLUE, "immunity": False, "pixel_position_board": None},
    {"name": "Daisy", "position": 1, "image": daisy_img, "color": YELLOW, "immunity": False, "pixel_position_board": None},
]

# Menu variables
menu_num_players = 2
menu_selected_indices = [0, 1, 2, 3, 4, 5]  # default selections, but will be adjusted
menu_current_selecting = 0  # which player's character is being selected

# Game state
current_player = 0
dice_value = 1
game_state = "menu"  # menu, rolling, moving, game_over
winner = None
animation_progress = 0
dice_rolled = False
move_target_steps = 0

def load_powerup_sprites():
    """Cargar sprites para los power-ups"""
    sprites = {}
    try:
        sprites["star"] = pygame.image.load("assets/star.png").convert_alpha()
        sprites["mushroom"] = pygame.image.load("assets/mushroom.png").convert_alpha()
        sprites["flower"] = pygame.image.load("assets/flower.png").convert_alpha()
        sprites["coin"] = pygame.image.load("assets/coin.png").convert_alpha()
        sprites["bowser"] = pygame.image.load("assets/bowser.png").convert_alpha()
    except:
        # Crear placeholders si no se encuentran los archivos
        sprites["star"] = pygame.Surface((30, 30), pygame.SRCALPHA)
        pygame.draw.polygon(sprites["star"], (255, 255, 0), [
            (15, 0), (20, 10), (30, 10), (22, 17),
            (25, 27), (15, 22), (5, 27), (8, 17),
            (0, 10), (10, 10)
        ])
        
        sprites["mushroom"] = pygame.Surface((30, 30), pygame.SRCALPHA)
        pygame.draw.ellipse(sprites["mushroom"], (255, 0, 0), (0, 0, 30, 20))
        pygame.draw.ellipse(sprites["mushroom"], (200, 200, 200), (0, 10, 30, 20))
        
        sprites["flower"] = pygame.Surface((30, 30), pygame.SRCALPHA)
        pygame.draw.circle(sprites["flower"], (255, 0, 0), (15, 15), 10)
        for i in range(8):
            angle = i * 45
            x = 15 + 15 * math.cos(math.radians(angle))
            y = 15 + 15 * math.sin(math.radians(angle))
            pygame.draw.circle(sprites["flower"], (255, 255, 0), (x, y), 7)
        
        sprites["coin"] = pygame.Surface((30, 30), pygame.SRCALPHA)
        pygame.draw.circle(sprites["coin"], (255, 215, 0), (15, 15), 12)
        pygame.draw.circle(sprites["coin"], (255, 255, 100), (15, 15), 10)
        
        sprites["bowser"] = pygame.Surface((30, 30), pygame.SRCALPHA)
        pygame.draw.rect(sprites["bowser"], (200, 0, 0), (5, 5, 20, 20))
        pygame.draw.circle(sprites["bowser"], (0, 0, 0), (10, 10), 3)
        pygame.draw.circle(sprites["bowser"], (0, 0, 0), (20, 10), 3)
    
    # Escalar los sprites a un tamaño uniforme
    for key in sprites:
        sprites[key] = pygame.transform.scale(sprites[key], (40, 40))
    
    return sprites

# Cargar sprites de power-ups al inicio del juego
powerup_sprites = load_powerup_sprites()

# Lista de dados escalados (se creará en recalc_layout)
dice_imgs_scaled = []

# Valores de display por defecto (se recalcularán en recalc_layout)
DISPLAY_CELL_SIZE = CELL_SIZE
DISPLAY_BOARD_WIDTH = BOARD_WIDTH
DISPLAY_BOARD_HEIGHT = BOARD_HEIGHT
DISPLAY_BOARD_ORIGIN_X = BOARD_ORIGIN_X
DISPLAY_BOARD_ORIGIN_Y = BOARD_ORIGIN_Y

# Calcular layout inicial
recalc_layout(WIDTH, HEIGHT)

def draw_snake(start_pos, end_pos):
    """Dibuja solo los sprites de serpiente con posicionamiento corregido"""
    start_row, start_col = get_cell_position(start_pos)
    end_row, end_col = get_cell_position(end_pos)
    
    # Convertir filas lógicas a físicas
    start_physical_row = BOARD_SIZE - 1 - start_row
    end_physical_row = BOARD_SIZE - 1 - end_row
    
    # Convertir a coordenadas físicas
    start_x = DISPLAY_BOARD_ORIGIN_X + start_col * DISPLAY_CELL_SIZE + DISPLAY_CELL_SIZE // 2
    start_y = DISPLAY_BOARD_ORIGIN_Y + start_physical_row * DISPLAY_CELL_SIZE + DISPLAY_CELL_SIZE // 2
    end_x = DISPLAY_BOARD_ORIGIN_X + end_col * DISPLAY_CELL_SIZE + DISPLAY_CELL_SIZE // 2
    end_y = DISPLAY_BOARD_ORIGIN_Y + end_physical_row * DISPLAY_CELL_SIZE + DISPLAY_CELL_SIZE // 2
    
    # Calcular ángulo y longitud
    dx, dy = end_x - start_x, end_y - start_y
    angle = math.degrees(math.atan2(dy, dx)) - 90
    length = math.hypot(dx, dy)
    
    # Dibujar cuerpo
    body_scaled = pygame.transform.scale(snake_body_img, (30, int(length)))
    body_rotated = pygame.transform.rotate(body_scaled, -angle)
    body_rect = body_rotated.get_rect(center=((start_x+end_x)/2, (start_y+end_y)/2))
    screen.blit(body_rotated, body_rect)
    
    # Dibujar cabeza
    head_rotated = pygame.transform.rotate(snake_head_img, -angle)
    head_rect = head_rotated.get_rect(center=(start_x, start_y))
    screen.blit(head_rotated, head_rect)


def draw_ladder(start_pos, end_pos):
    """Dibuja solo los sprites de escalera con posicionamiento corregido"""
    start_row, start_col = get_cell_position(start_pos)
    end_row, end_col = get_cell_position(end_pos)
    
    # Convertir filas lógicas a físicas
    start_physical_row = BOARD_SIZE - 1 - start_row
    end_physical_row = BOARD_SIZE - 1 - end_row
    
    # Convertir a coordenadas físicas
    start_x = DISPLAY_BOARD_ORIGIN_X + start_col * DISPLAY_CELL_SIZE + DISPLAY_CELL_SIZE // 2
    start_y = DISPLAY_BOARD_ORIGIN_Y + start_physical_row * DISPLAY_CELL_SIZE + DISPLAY_CELL_SIZE // 2
    end_x = DISPLAY_BOARD_ORIGIN_X + end_col * DISPLAY_CELL_SIZE + DISPLAY_CELL_SIZE // 2
    end_y = DISPLAY_BOARD_ORIGIN_Y + end_physical_row * DISPLAY_CELL_SIZE + DISPLAY_CELL_SIZE // 2
    
    # Calcular ángulo y longitud
    dx, dy = end_x - start_x, end_y - start_y
    angle = math.degrees(math.atan2(dy, dx))
    length = math.hypot(dx, dy)
    
    # Dibujar peldaños
    for i in range(1, 5):  # 4 peldaños
        ratio = i / 5
        rung_x = start_x + dx * ratio
        rung_y = start_y + dy * ratio
        rung_rotated = pygame.transform.rotate(ladder_rung_img, -angle)
        rung_rect = rung_rotated.get_rect(center=(rung_x, rung_y))
        screen.blit(rung_rotated, rung_rect)
    
    # Dibujar parte superior
    top_rotated = pygame.transform.rotate(ladder_top_img, -angle + 180)
    top_rect = top_rotated.get_rect(center=(end_x, end_y))
    screen.blit(top_rotated, top_rect)


def draw_snake_on_surface(surf, start_pos, end_pos):
    start_row, start_col = get_cell_position(start_pos)
    end_row, end_col = get_cell_position(end_pos)
    start_physical_row = BOARD_SIZE - 1 - start_row
    end_physical_row = BOARD_SIZE - 1 - end_row
    start_x = start_col * CELL_SIZE + CELL_SIZE // 2
    start_y = start_physical_row * CELL_SIZE + CELL_SIZE // 2
    end_x = end_col * CELL_SIZE + CELL_SIZE // 2
    end_y = end_physical_row * CELL_SIZE + CELL_SIZE // 2
    dx, dy = end_x - start_x, end_y - start_y
    angle = math.degrees(math.atan2(dy, dx)) - 90
    length = math.hypot(dx, dy)
    body_scaled = pygame.transform.scale(snake_body_img, (max(4, CELL_SIZE//2), int(length)))
    body_rotated = pygame.transform.rotate(body_scaled, -angle)
    body_rect = body_rotated.get_rect(center=((start_x+end_x)/2, (start_y+end_y)/2))
    surf.blit(body_rotated, body_rect)
    head_rotated = pygame.transform.rotate(snake_head_img, -angle)
    head_rect = head_rotated.get_rect(center=(start_x, start_y))
    surf.blit(head_rotated, head_rect)


def draw_ladder_on_surface(surf, start_pos, end_pos):
    start_row, start_col = get_cell_position(start_pos)
    end_row, end_col = get_cell_position(end_pos)
    start_physical_row = BOARD_SIZE - 1 - start_row
    end_physical_row = BOARD_SIZE - 1 - end_row
    start_x = start_col * CELL_SIZE + CELL_SIZE // 2
    start_y = start_physical_row * CELL_SIZE + CELL_SIZE // 2
    end_x = end_col * CELL_SIZE + CELL_SIZE // 2
    end_y = end_physical_row * CELL_SIZE + CELL_SIZE // 2
    dx, dy = end_x - start_x, end_y - start_y
    angle = math.degrees(math.atan2(dy, dx))
    length = math.hypot(dx, dy)
    for i in range(1, 5):
        ratio = i / 5
        rung_x = start_x + dx * ratio
        rung_y = start_y + dy * ratio
        rung_rotated = pygame.transform.rotate(ladder_rung_img, -angle)
        rung_rect = rung_rotated.get_rect(center=(rung_x, rung_y))
        surf.blit(rung_rotated, rung_rect)
    top_rotated = pygame.transform.rotate(ladder_top_img, -angle + 180)
    top_rect = top_rotated.get_rect(center=(end_x, end_y))
    surf.blit(top_rotated, top_rect)


def render_board_surface():
    """Renderiza el tablero completo en una superficie de tamaño (BOARD_WIDTH, BOARD_HEIGHT) y la devuelve."""
    surf = pygame.Surface((BOARD_WIDTH, BOARD_HEIGHT), pygame.SRCALPHA)
    # Draw grid and numbers
    for i in range(BOARD_SIZE):
        for j in range(BOARD_SIZE):
            logical_row = BOARD_SIZE - 1 - i
            if logical_row % 2 == 0:
                cell_num = logical_row * BOARD_SIZE + j + 1
            else:
                cell_num = (logical_row + 1) * BOARD_SIZE - j
            x = j * CELL_SIZE
            y = i * CELL_SIZE
            pygame.draw.rect(surf, WHITE, (x, y, CELL_SIZE, CELL_SIZE), 0)
            pygame.draw.rect(surf, BLACK, (x, y, CELL_SIZE, CELL_SIZE), 1)
            text = font_small.render(str(cell_num), True, BLACK)
            surf.blit(text, (x + 5, y + 5))

    # Draw snakes and ladders on surf
    for start, end in snakes.items():
        draw_snake_on_surface(surf, start, end)
    for start, end in ladders.items():
        draw_ladder_on_surface(surf, start, end)

    # Draw special tiles
    for tile_num, tile_data in special_tiles.items():
        row, col = get_cell_position(tile_num)
        physical_row = BOARD_SIZE - 1 - row
        x = col * CELL_SIZE + CELL_SIZE // 2
        y = physical_row * CELL_SIZE + CELL_SIZE // 2
        sprite_type = tile_data['type']
        if sprite_type in powerup_sprites:
            sprite = powerup_sprites[sprite_type]
            rect = sprite.get_rect(center=(x, y))
            surf.blit(sprite, rect)

    # Draw players onto surf
    for i, player in enumerate(players):
        if player.get('pixel_position_board') is not None:
            bx, by = player['pixel_position_board']
            img = player.get('image_scaled', player['image'])
            iw, ih = img.get_size()
            surf.blit(img, (bx - iw//2, by - ih//2))
        else:
            row, col = get_cell_position(player['position'])
            physical_row = BOARD_SIZE - 1 - row
            bx = col * CELL_SIZE + CELL_SIZE // 2 + (i * max(4, CELL_SIZE//6) - max(4, CELL_SIZE//12))
            by = physical_row * CELL_SIZE + CELL_SIZE // 2 - max(6, CELL_SIZE//6)
            img = player.get('image_scaled', player['image'])
            iw, ih = img.get_size()
            surf.blit(img, (bx - iw//2, by - ih//2 + 10))

    return surf

def draw_board():
    # Leave background white (do not draw background image)
    # background_img intentionally not blitted so the screen stays white

    # Render board into a surface and scale/blit to screen to avoid cropping
    board_surf = render_board_surface()
    try:
        scaled = pygame.transform.smoothscale(board_surf, (DISPLAY_BOARD_WIDTH, DISPLAY_BOARD_HEIGHT))
    except Exception:
        scaled = pygame.transform.scale(board_surf, (DISPLAY_BOARD_WIDTH, DISPLAY_BOARD_HEIGHT))
    screen.blit(scaled, (DISPLAY_BOARD_ORIGIN_X, DISPLAY_BOARD_ORIGIN_Y))

def get_cell_position(cell_num):
    """Convert cell number to board row and column"""
    # Fila lógica: 0 = inferior, 9 = superior
    row = (cell_num - 1) // BOARD_SIZE
    
    # Columna: depende de si la fila es par o impar
    if row % 2 == 0:  # Filas pares (desde abajo) van de izquierda a derecha
        col = (cell_num - 1) % BOARD_SIZE
    else:  # Filas impares (desde abajo) van de derecha a izquierda
        col = BOARD_SIZE - 1 - (cell_num - 1) % BOARD_SIZE
    
    return row, col

def draw_players():
    # Players are rendered into the board surface inside `render_board_surface`.
    return


def draw_dice():
    # Draw dice box
    ui_padding = max(10, int(min(WIDTH, HEIGHT) * 0.03))
    dice_box_size = max(60, int(CELL_SIZE * 1.4))
    dice_x = max(ui_padding, WIDTH - dice_box_size - ui_padding)
    dice_y = max(ui_padding, HEIGHT - dice_box_size - ui_padding)
    pygame.draw.rect(screen, WHITE, (dice_x, dice_y, dice_box_size, dice_box_size))
    pygame.draw.rect(screen, BLACK, (dice_x, dice_y, dice_box_size, dice_box_size), 3)
    
    # Determinar qué valor mostrar
    current_value = dice_value
    if dice_animation and dice_animation_values:
        # Calcular qué valor mostrar en la animación
        index = dice_animation_frames // dice_animation_speed
        if index < len(dice_animation_values):
            current_value = dice_animation_values[index]
    
    # Draw dice value
    if 1 <= current_value <= 6:
        img = dice_imgs_scaled[current_value - 1] if dice_imgs_scaled else dice_imgs[current_value - 1]
        iw, ih = img.get_size()
        screen.blit(img, (dice_x + (dice_box_size - iw)//2, dice_y + (dice_box_size - ih)//2))
    
    # Draw roll button if it's the player's turn
    if game_state == "rolling" and not dice_rolled and not dice_animation:
        roll_text = font_medium.render("Presiona espacio para tirar", True, BLACK)
        rt_x = dice_x - roll_text.get_width() - 10
        if rt_x < ui_padding:
            rt_x = ui_padding
        screen.blit(roll_text, (rt_x, dice_y + dice_box_size//2 - roll_text.get_height()//2))

def draw_game_info():

    # Current player info
    player = players[current_player]
    info_text = font_medium.render(f"Turno de {player['name']}", True, player["color"])
    screen.blit(info_text, (10, HEIGHT - 30 - info_text.get_height()))
    
    # Game instructions
    if game_state == "rolling":
        instruct_text = font_small.render("Presiona espacio para tirar el dado", True, BLACK)
        screen.blit(instruct_text, (20, HEIGHT -100))
    
    # Winner announcement
    if game_state == "game_over":
        # Fondo para el anuncio
        pygame.draw.rect(screen, BLACK, (WIDTH//2 - 150, HEIGHT//2 - 50, 300, 150))
        pygame.draw.rect(screen, RED, (WIDTH//2 - 145, HEIGHT//2 - 45, 290, 140), 3)
        
        winner_text = font_large.render(f"{winner} GANA!", True, YELLOW)
        screen.blit(winner_text, (WIDTH//2 - winner_text.get_width()//2, HEIGHT//2 - 20))
        
        # Restart button
        restart_rect = pygame.Rect(WIDTH//2 - 100, HEIGHT//2 + 20, 200, 40)
        pygame.draw.rect(screen, GREEN, restart_rect)
        pygame.draw.rect(screen, BLACK, restart_rect, 2)
        restart_text = font_medium.render("Reiniciar", True, BLACK)
        screen.blit(restart_text, (restart_rect.centerx - restart_text.get_width()//2, restart_rect.centery - restart_text.get_height()//2))
        
        # Exit button
        exit_rect = pygame.Rect(WIDTH//2 - 100, HEIGHT//2 + 70, 200, 40)
        pygame.draw.rect(screen, RED, exit_rect)
        pygame.draw.rect(screen, BLACK, exit_rect, 2)
        exit_text = font_medium.render("Salir", True, BLACK)
        screen.blit(exit_text, (exit_rect.centerx - exit_text.get_width()//2, exit_rect.centery - exit_text.get_height()//2))

def draw_menu():
    # Title
    title_text = font_large.render("Super Mario Snakes & Ladders", True, BLACK)
    screen.blit(title_text, (WIDTH//2 - title_text.get_width()//2, 50))
    
    # Number of players
    num_text = font_medium.render(f"Número de Jugadores: {menu_num_players}", True, BLACK)
    screen.blit(num_text, (WIDTH//2 - num_text.get_width()//2, 150))
    
    # Buttons for num players
    left_rect = pygame.Rect(WIDTH//2 - 190, 150, 40, 30)
    pygame.draw.rect(screen, BLUE, left_rect)
    pygame.draw.rect(screen, BLACK, left_rect, 2)
    left_text = font_medium.render("-", True, WHITE)
    screen.blit(left_text, (left_rect.centerx - left_text.get_width()//2, left_rect.centery - left_text.get_height()//2))
    
    right_rect = pygame.Rect(WIDTH//2 + 150, 150, 40, 30)
    pygame.draw.rect(screen, BLUE, right_rect)
    pygame.draw.rect(screen, BLACK, right_rect, 2)
    right_text = font_medium.render("+", True, WHITE)
    screen.blit(right_text, (right_rect.centerx - right_text.get_width()//2, right_rect.centery - right_text.get_height()//2))
    
    # Character selection
    y_offset = 250
    for i in range(menu_num_players):
        player_text = font_medium.render(f"Jugador {i+1}:", True, BLACK)
        screen.blit(player_text, (100, y_offset))
        
        # Selected character
        char = all_characters[menu_selected_indices[i]]
        screen.blit(char["image"], (250, y_offset - 10))
        name_text = font_small.render(char["name"], True, char["color"])
        screen.blit(name_text, (300, y_offset))
        
        # Prev button
        prev_rect = pygame.Rect(400, y_offset, 30, 30)
        pygame.draw.rect(screen, GREEN, prev_rect)
        pygame.draw.rect(screen, BLACK, prev_rect, 2)
        prev_text = font_small.render("<", True, WHITE)
        screen.blit(prev_text, (prev_rect.centerx - prev_text.get_width()//2, prev_rect.centery - prev_text.get_height()//2))
        
        # Next button
        next_rect = pygame.Rect(440, y_offset, 30, 30)
        pygame.draw.rect(screen, GREEN, next_rect)
        pygame.draw.rect(screen, BLACK, next_rect, 2)
        next_text = font_small.render(">", True, WHITE)
        screen.blit(next_text, (next_rect.centerx - next_text.get_width()//2, next_rect.centery - next_text.get_height()//2))
        
        y_offset += 60
    
    # Start button
    start_rect = pygame.Rect(WIDTH//2 - 130, HEIGHT - 100, 300, 50)
    pygame.draw.rect(screen, RED, start_rect)
    pygame.draw.rect(screen, BLACK, start_rect, 2)
    start_text = font_large.render("Empezar Juego", True, WHITE)
    screen.blit(start_text, (start_rect.centerx - start_text.get_width()//2, start_rect.centery - start_text.get_height()//2))

def roll_dice():
    global dice_value, dice_rolled, dice_animation, dice_animation_frames, dice_animation_values, dice_final_value
    
    # Generar valor final
    dice_final_value = random.randint(1, 6)
    
    # Iniciar animación
    dice_animation = True
    dice_animation_frames = 0
    dice_animation_values = []
    
    # Generar secuencia de animación (10 valores aleatorios)
    for _ in range(10):
        dice_animation_values.append(random.randint(1, 6))
    
    # Añadir el valor final al final de la animación
    dice_animation_values.append(dice_final_value)
    
    if dice_sound:
        dice_sound.play()
    dice_rolled = True


def move_player():
    global current_player, game_state, winner, animation_progress, move_target_steps, dice_value
    global move_anim_active, move_path, move_step_index, move_step_progress, move_last_time

    player = players[current_player]
    remaining = 100 - player["position"]
    steps = move_target_steps if move_target_steps > 0 else min(dice_value, remaining)

    # Initialize smooth move path when starting
    if not move_anim_active and steps > 0 and animation_progress == 0:
        move_path = []
        base_pos = player["position"]
        for s in range(1, steps + 1):
            start_cell = base_pos + s - 1
            end_cell = base_pos + s
            # compute board-space center for start and end
            sr, sc = get_cell_position(start_cell)
            er, ec = get_cell_position(end_cell)
            s_pr = BOARD_SIZE - 1 - sr
            e_pr = BOARD_SIZE - 1 - er
            sx = sc * CELL_SIZE + CELL_SIZE // 2 + (current_player * max(4, CELL_SIZE//6) - max(4, CELL_SIZE//12))
            sy = s_pr * CELL_SIZE + CELL_SIZE // 2 - max(6, CELL_SIZE//6)
            ex = ec * CELL_SIZE + CELL_SIZE // 2 + (current_player * max(4, CELL_SIZE//6) - max(4, CELL_SIZE//12))
            ey = e_pr * CELL_SIZE + CELL_SIZE // 2 - max(6, CELL_SIZE//6)
            move_path.append((sx, sy, ex, ey))
        move_anim_active = True
        move_step_index = 0
        move_step_progress = 0.0
        move_last_time = pygame.time.get_ticks()
        player["pixel_position_board"] = (move_path[0][0], move_path[0][1])

    # If there's an active smooth movement, advance it based on elapsed time
    if move_anim_active:
        now = pygame.time.get_ticks()
        dt = now - move_last_time
        move_last_time = now
        if MOVE_STEP_MS <= 0:
            frac = 1.0
        else:
            frac = dt / MOVE_STEP_MS
        move_step_progress += frac

        # Clamp and compute interpolation
        if move_step_progress >= 1.0:
            # finish this cell-step (may carry over to next)
            move_step_progress -= 1.0
            # advance logical position
            player["position"] = min(100, player["position"] + 1)
            move_step_index += 1
            if move_step_index >= len(move_path):
                # movement finished
                move_anim_active = False
                move_path = []
                move_step_index = 0
                move_step_progress = 0.0
                player["pixel_position_board"] = None
                animation_progress = 0
                move_target_steps = 0
                # Check for win
                if player["position"] >= 100:
                    player["position"] = 100
                    game_state = "game_over"
                    winner = player["name"]
                    if win_sound:
                        win_sound.play()
                    return
                game_state = "check_position"
                return

        # Interpolate current cell step
        if 0 <= move_step_index < len(move_path):
            sx, sy, ex, ey = move_path[move_step_index]
            t = move_step_progress
            # smoothstep easing
            et = t * t * (3 - 2 * t)
            x = sx + (ex - sx) * et
            y = sy + (ey - sy) * et
            player["pixel_position_board"] = (x, y)
            return

    # No movement to process
    return

def handle_special_tile(tile_num):
    global current_player, dice_rolled, game_state
    tile_data = special_tiles[tile_num]
    player = players[current_player]
    
    if tile_data["effect"] == "extra_turn":
        # El jugador mantiene el turno
        dice_rolled = False
        game_state = "rolling"
    elif tile_data["effect"] == "move_forward":
        player["position"] += tile_data["value"]
        # Volver a verificar la posición
        game_state = "check_position"
    elif tile_data["effect"] == "move_back":
        player["position"] = max(1, player["position"] - tile_data["value"])
        # Volver a verificar la posición
        game_state = "check_position"
    elif tile_data["effect"] == "immunity":
        player["immunity"] = True
        # Continuar con el turno
        game_state = "finalize_turn"
    elif tile_data["effect"] == "roll_again":
        dice_rolled = False
        game_state = "rolling"
    
    # Play sound based on tile type
    tile_type = tile_data["type"]
    if tile_type == "star" and star_sound:
        star_sound.play()
    elif tile_type == "mushroom" and powerup_sound:
        powerup_sound.play()
    elif tile_type == "flower" and flower_sound:
        flower_sound.play()
    elif tile_type == "coin" and coin_sound:
        coin_sound.play()
    elif tile_type == "bowser" and bowser_sound:
        bowser_sound.play()

def main():
    global game_state, dice_value, dice_rolled, current_player, animation_progress, screen
    global dice_animation, dice_animation_frames, dice_animation_values, dice_final_value
    global players, menu_num_players, menu_selected_indices
    
    clock = pygame.time.Clock()
    
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE and game_state == "rolling" and not dice_rolled and not dice_animation:
                    roll_dice()
                    game_state = "moving"
                    animation_progress = 0
                elif event.key == pygame.K_r and game_state == "game_over":
                    # Reset game
                    for player in players:
                        player["position"] = 1
                        player["immunity"] = False
                        player["pixel_position"] = None
                    current_player = 0
                    game_state = "rolling"
                    dice_rolled = False
                    animation_progress = 0
                    dice_animation = False
            
            if event.type == pygame.MOUSEBUTTONDOWN and game_state == "game_over":
                mouse_x, mouse_y = event.pos
                # Restart button
                restart_rect = pygame.Rect(WIDTH//2 - 100, HEIGHT//2 + 20, 200, 40)
                if restart_rect.collidepoint(mouse_x, mouse_y):
                    # Reset game
                    for player in players:
                        player["position"] = 1
                        player["immunity"] = False
                        player["pixel_position"] = None
                    current_player = 0
                    game_state = "rolling"
                    dice_rolled = False
                    animation_progress = 0
                    dice_animation = False
                # Exit button
                exit_rect = pygame.Rect(WIDTH//2 - 100, HEIGHT//2 + 70, 200, 40)
                if exit_rect.collidepoint(mouse_x, mouse_y):
                    pygame.quit()
                    sys.exit()
            
            if event.type == pygame.MOUSEBUTTONDOWN and game_state == "menu":
                mouse_x, mouse_y = event.pos
                # Num players buttons
                left_rect = pygame.Rect(WIDTH//2 - 190, 150, 40, 30)
                if left_rect.collidepoint(mouse_x, mouse_y):
                    menu_num_players = max(2, menu_num_players - 1)
                right_rect = pygame.Rect(WIDTH//2 + 150, 150, 40, 30)
                if right_rect.collidepoint(mouse_x, mouse_y):
                    menu_num_players = min(6, menu_num_players + 1)
                
                # Character selection buttons
                y_offset = 250
                for i in range(menu_num_players):
                    prev_rect = pygame.Rect(400, y_offset, 30, 30)
                    if prev_rect.collidepoint(mouse_x, mouse_y):
                        # Find previous available character
                        used = set(menu_selected_indices[:menu_num_players]) - {menu_selected_indices[i]}
                        for j in range(1, len(all_characters) + 1):
                            candidate = (menu_selected_indices[i] - j) % len(all_characters)
                            if candidate not in used:
                                menu_selected_indices[i] = candidate
                                break
                    next_rect = pygame.Rect(440, y_offset, 30, 30)
                    if next_rect.collidepoint(mouse_x, mouse_y):
                        # Find next available character
                        used = set(menu_selected_indices[:menu_num_players]) - {menu_selected_indices[i]}
                        for j in range(1, len(all_characters) + 1):
                            candidate = (menu_selected_indices[i] + j) % len(all_characters)
                            if candidate not in used:
                                menu_selected_indices[i] = candidate
                                break
                    y_offset += 60
                
                # Start button
                start_rect = pygame.Rect(WIDTH//2 - 130, HEIGHT - 100, 300, 50)
                if start_rect.collidepoint(mouse_x, mouse_y):
                    # Check for duplicates
                    selected = menu_selected_indices[:menu_num_players]
                    if len(set(selected)) == len(selected):
                        # No duplicates, start game
                        players = []
                        for idx in selected:
                            char = all_characters[idx]
                            players.append({
                                "name": char["name"],
                                "position": 1,
                                "image": char["image"],
                                "color": char["color"],
                                "immunity": False,
                                "pixel_position_board": None
                            })
                        game_state = "rolling"
                    else:
                        # Duplicates, maybe show message, but for now, just don't start
                        pass
        
        # Manejar animación del dado
        if dice_animation:
            dice_animation_frames += 1
            max_frames = len(dice_animation_values) * dice_animation_speed
            if dice_animation_frames >= max_frames:
                dice_animation = False
                dice_value = dice_final_value
                # Calcular cuántos pasos deben animarse realmente (no saltar a 100)
                remaining = 100 - players[current_player]["position"]
                move_target_steps = min(dice_value, remaining)
                animation_progress = 0
                if game_state == "moving":
                    move_player()
        
        # Actualizar animaciones de serpientes y escaleras
        if current_animation:
            update_animation()
        
        # Lógica de verificación de posición
        if game_state == "check_position":
            player = players[current_player]
            
            # Verificar serpientes/escaleras (a menos que tenga inmunidad)
            if not player["immunity"]:
                if player["position"] in snakes:
                    start_animation(current_player, player["position"], snakes[player["position"]], "snake")
                    game_state = "animation"
                elif player["position"] in ladders:
                    start_animation(current_player, player["position"], ladders[player["position"]], "ladder")
                    game_state = "animation"
            
            # Si no se activó animación, verificar power-ups
            if game_state == "check_position":
                if player["position"] in special_tiles:
                    handle_special_tile(player["position"])
                else:
                    game_state = "finalize_turn"
        
        # Lógica de movimiento
        if game_state == "moving" and not dice_animation:
            move_player()
        
        # Finalizar turno
        if game_state == "finalize_turn":
            player = players[current_player]
            player["immunity"] = False
            current_player = (current_player + 1) % len(players)
            game_state = "rolling"
            dice_rolled = False
        
        # Dibujado
        screen.fill(WHITE)
        if game_state == "menu":
            draw_menu()
        else:
            draw_board()
            draw_players()
            draw_dice()
            draw_game_info()
        
        pygame.display.flip()
        clock.tick(60)

if __name__ == "__main__":
    main()
