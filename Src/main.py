import pygame as pg
import sys, random
import numpy as np

from gui import *
from Enemy import Enemy
from Player import Player
from Level import Level
from numba import njit, prange


# === Constants ===
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
H_RES = 120
V_RES = 200
HALF_V_RES = V_RES // 2
FOV = 60
TEXTURE_SIZE = 64
SCALE = H_RES / FOV
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
BLUE = (0, 0, 255)
LIGHT_GRAY = (159, 168, 175)
GREEN = (0, 255, 0)
FPS = 60
POWERUPS = ["SUPER STRENGTH", "SUPER CHARGE", "SUPER ARMOR"]
GUNS = ["Pistol", "Shotgun", "AK-47", "Electrorifle","Quarkinator"]
ROT_SENSITIVITY = 0.05
BRIGHTNESS = 1.4
MAP_SIZE = 99
SONGLIST = ["TTFAF.ogg", "BEATIT.ogg", "100.ogg"]

# === Global objects ===
running = True
player = Player(0, 0)
sliders = []
options_clicked = False
pyramids = []
item_list = []
timer = 0
loot_banner_data = {"items": [], "start_time": 0}
for _ in range(5):
    pyramids.append([random.uniform(-500, 500), random.uniform(-500, 500), 1, 8])

# === Asset Preloading ===
pg.init()
pg.font.init()
screen = pg.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pg.HWSURFACE | pg.DOUBLEBUF)

height_map = np.zeros((MAP_SIZE, MAP_SIZE), dtype=np.float32)

# Generate smooth hills with sine/cosine + noise
for y in range(MAP_SIZE):
    for x in range(MAP_SIZE):
        val = (
            np.sin(x * 0.15) * 0.5 +
            np.cos(y * 0.15) * 0.5 +
            np.random.uniform(-0.1, 0.1)
        )
        height_map[x, y] = np.sign(val) * (abs(val) ** 1.5) * 1.2

# Preload images once and convert to display format
SPRITESHEET = pg.image.load("Textures/spritesheet_1.png").convert_alpha()
BG_TILE = pg.image.load("Textures/sand2.png").convert()
LOGO = pg.image.load("Textures/logo.png").convert_alpha()
GUY = pg.transform.scale(pg.image.load("Textures/guy.png").convert_alpha(), (100, 100))
FLOOR_IMG = pg.image.load("Textures/sand.png").convert()
FLOOR_ARRAY = (pg.surfarray.array3d(FLOOR_IMG) / 255.0).astype(np.float32)
SKYBOX_TEXTURE = pg.image.load("Textures/skybox.jpg").convert_alpha()
SKYBOX_TEXTURE = pg.transform.scale(SKYBOX_TEXTURE, (360, V_RES))
SKYBOX = pg.surfarray.array3d(SKYBOX_TEXTURE).astype(np.float32) / 255.0
ITEM_IMGS = {"cactus":pg.image.load("Textures/cactus.png").convert_alpha(), "crate":pg.image.load("Textures/crate.png").convert_alpha()}
SHOOT = pg.transform.scale(pg.image.load("Textures/shoot.png").convert_alpha(), (100, 100))

# Gun preloading
GUN_IMG = pg.image.load("Textures/Weapons/pistol.png").convert_alpha()
GUN_IMG_SCALED = pg.transform.scale(GUN_IMG, (GUN_IMG.get_width()*2, GUN_IMG.get_height()*2))

# Loot tables
LOOTTABLE_CRATE = {
    "Burger": 20,
    "Pizza": 20,
    "Steel Knive":10,
    "Flashlight": 5,
    "Shotgun":15,
    "Pharoah's Robes": 1,
    "Osiris's Totem": 1,
    "AK-47": 8,
    "Ammo": 20
}

# Music & sounds
pg.mixer.music.load("Sounds/title.ogg")
gunshot = pg.mixer.Sound("Sounds/gun.ogg")

# === Precompute trig for raycasting. make sure types are specified ===
ray_angles = np.deg2rad(np.linspace(-FOV/2, FOV/2, H_RES))
sin_vals = np.sin(ray_angles).astype(np.float32)
cos_vals = np.cos(ray_angles).astype(np.float32)
cos_correction = np.cos(ray_angles).astype(np.float32)

# === GUI UTILS ===
class Slider:
    def __init__(self, x, y, width, height, max_value=100, min_value=0, start_value=50):
        self.rect = pg.Rect(x, y, width, height)
        self.handle_rect = pg.Rect(x, y - (height // 2), 10, height * 2)
        self.min_value = min_value
        self.max_value = max_value
        self.value = start_value
        self.dragging = False
        self.update_handle_from_value()

    def update_handle_from_value(self):
        ratio = (self.value - self.min_value) / (self.max_value - self.min_value)
        self.handle_rect.centerx = self.rect.x + int(ratio * self.rect.width)

    def update_value_from_handle(self):
        ratio = (self.handle_rect.centerx - self.rect.x) / self.rect.width
        self.value = int(self.min_value + ratio * (self.max_value - self.min_value))

    def handle_event(self, event):
        if event.type == pg.MOUSEBUTTONDOWN and self.handle_rect.collidepoint(event.pos):
            self.dragging = True
        elif event.type == pg.MOUSEBUTTONUP:
            self.dragging = False
        elif event.type == pg.MOUSEMOTION and self.dragging:
            self.handle_rect.centerx = max(self.rect.x, min(event.pos[0], self.rect.x + self.rect.width))
            self.update_value_from_handle()

    def draw(self, screen):
        pg.draw.rect(screen, (200, 200, 200), self.rect, border_radius=3)
        pg.draw.rect(screen, (100, 100, 255), self.handle_rect, border_radius=3)
        font = pg.font.SysFont("Arial", 20)
        val_surf = font.render(str(self.value), True, (0, 0, 0))
        screen.blit(val_surf, (self.rect.right + 15, self.rect.y - 10))

button_color = (0, 255, 0)
button_hover_color = (170, 170, 170)

def draw_text(screen, text, size, color, pos):
    font = pg.font.SysFont("Arial", size)
    surface = font.render(text, True, color)
    screen.blit(surface, pos)

def draw_button(player, screen, text, rect):
    mouse_pos = pg.mouse.get_pos()
    mouse_click = pg.mouse.get_pressed()
    is_hovered = rect.collidepoint(mouse_pos)
    font = pg.font.SysFont("Arial", 20)
    color = button_hover_color if is_hovered else button_color
    pg.draw.rect(screen, color, rect, border_radius=10)
    text_surf = font.render(text, True, (0, 0, 0))
    text_rect = text_surf.get_rect(center=rect.center)
    screen.blit(text_surf, text_rect)
    if is_hovered and mouse_click[0]:
        if text == 'Quit Game':
            pg.quit(); sys.exit(0)
        elif text == 'Play Game':
            global sliders
            sliders = []
            pg.mixer.music.pause()
            player.paused = False
            player.spawn()
        elif text == 'Options':
            global options_clicked
            options_clicked = True

def render_main_menu(player, screen):
    if not options_clicked:
        for y in range(0, SCREEN_HEIGHT, BG_TILE.get_height()):
            for x in range(0, SCREEN_WIDTH, BG_TILE.get_width()):
                screen.blit(BG_TILE, (x, y))
        draw_text(screen, "John Mcaffe's Pyramid Assult", 40, (222, 100, 20), (190, 20))
        draw_text(screen, "John Mccaffe Shoots Egypt for some reason", 25, (255, 200, 200), (200, 80))
        button_rects = [pg.Rect(270, 250, 300, 60),
                        pg.Rect(270, 350, 300, 60),
                        pg.Rect(270, 450, 300, 60)]
        draw_button(player, screen, "Play Game", button_rects[0])
        draw_button(player, screen, "Options", button_rects[1])
        draw_button(player, screen, "Quit Game", button_rects[2])
        screen.blit(GUY, (SCREEN_WIDTH // 2 -40, 110))
    else:
        render_options(screen)

def render_options(screen):
    screen.fill((155, 255, 155))
    draw_text(screen, "Options Menu", 30, (0, 0, 0), (280, 10))
    draw_text(screen, "Max FPS: ", 22, (0, 0, 0), (100, 140))
    draw_text(screen, "Graphics: ", 22, (0, 0, 0), (100, 200))
    if not sliders:
        sliders.append(Slider(260, 150, 200, 8, max_value=240, min_value=30, start_value=FPS))
    for slider in sliders:
        slider.draw(screen)

### RAYCASTING FUNCTION - Tried to label sorry if its hard to read ###
# init the frame buffer
_frame_buffer = np.zeros((H_RES, V_RES, 3), dtype=np.float32) # store frame info of pixel (pos color)
_frame_buffer.flags.writeable = True

@njit(fastmath=True)
def render_frame(frame_buffer, posx, posy, rot,
                 ray_angles, cos_correction, skybox, floor_array,
                 H_RES, V_RES, HALF_V_RES, height_map, map_size):
    for i in range(H_RES):
        angle = rot + ray_angles[i]
        sin_a = np.sin(angle)
        cos_a = np.cos(angle)
        cos2 = cos_correction[i]
        row = int(np.rad2deg(angle) % 359)

        # Draw skybox
        for v in range(V_RES):
            frame_buffer[i, v, 0] = skybox[row, v, 0]
            frame_buffer[i, v, 1] = skybox[row, v, 1]
            frame_buffer[i, v, 2] = skybox[row, v, 2]

        # Now draw floor and hills with proper vertical height sampling:
        for v in range(HALF_V_RES+1, V_RES):
            # Calculate distance from player for this pixel (using projection)
            # We invert v because screen y=0 is top
            # The ratio corresponds to how far from center line downward the pixel is
            # Formula modified for vertical perspective and height check
            
            # Screen y relative to center
            screen_y = v - HALF_V_RES
            
            # Distance from player based on screen vertical position and FOV
            distance = (HALF_V_RES * BRIGHTNESS) / screen_y / cos2

            # Calculate world coords at this distance along the ray
            world_x = posx + cos_a * distance
            world_y = posy + sin_a * distance

            # Wrap into map
            map_x = int(world_x) % map_size
            map_y = int(world_y) % map_size

            # Height of terrain here
            terrain_height = height_map[map_x, map_y]

            # Compute height of pixel in "world height space"
            # You can scale height to pixels, e.g., * 20 as before
            pixel_height = int(terrain_height * 20)

            # Calculate screen height of the terrain surface relative to center
            surface_screen_y = HALF_V_RES - pixel_height

            # Only draw pixel if current pixel is at or below terrain surface (floor or hill)
            if v >= surface_screen_y:
                # Sample floor texture coords
                tx = int(world_x * TEXTURE_SIZE) % TEXTURE_SIZE
                ty = int(world_y * TEXTURE_SIZE) % TEXTURE_SIZE

                for c in range(3):
                    col = floor_array[tx, ty, c]
                    frame_buffer[i, v, c] = min(1.0, max(0.0, col))

    return frame_buffer


### ITEM RENDERING ###

def render_items(screen, player):
    for x, y, item_type in item_list:
        dx, dy = x - player.x, y - player.y
        distance = np.hypot(dx, dy)
        if distance < 0.01:
            continue

        # Angle of item relative to player rotation
        angle = np.arctan2(dy, dx) - player.rot
        angle = (angle + np.pi) % (2 * np.pi) - np.pi  # normalize

        if -np.deg2rad(FOV / 2) <= angle <= np.deg2rad(FOV / 2):
            scale = max(1, int(500 / (distance + 0.0001)))
            img = ITEM_IMGS[item_type]
            item_scaled = pg.transform.smoothscale(img, (scale, scale))
            screen_x = int((angle / np.deg2rad(FOV)) * SCREEN_WIDTH + SCREEN_WIDTH // 2)
            rect = item_scaled.get_rect(center=(screen_x, SCREEN_HEIGHT // 2))
            screen.blit(item_scaled, rect)

def render_pyramids(screen, player):
    for x, y, height, base in pyramids:
        dx, dy = x - player.x, y - player.y
        distance = np.hypot(dx, dy)
        if distance < 0.1:  # Skip if too close
            continue

        angle = np.arctan2(dy, dx) - player.rot
        angle = (angle + np.pi) % (2 * np.pi) - np.pi  # normalize

        if -np.deg2rad(FOV/2) <= angle <= np.deg2rad(FOV/2):
            scale = max(1, int(400 / (distance + 0.001)))
            screen_x = int((angle / np.deg2rad(FOV)) * SCREEN_WIDTH + SCREEN_WIDTH//2)
            base_screen_y = SCREEN_HEIGHT//2 + int(distance * 2)  # ground anchor
            top_screen_y = base_screen_y - int(height * scale)

            color = (210, 180, 140)  # sandy color
            pg.draw.polygon(screen, color, [
                (screen_x - scale, base_screen_y),
                (screen_x + scale, base_screen_y),
                (screen_x, top_screen_y)
            ])
def loot_banner(items):
    global loot_banner_data
    loot_banner_data["items"] = items
    loot_banner_data["start_time"] = pg.time.get_ticks()
    

def item_collect(player, pickup_radius=0.5):
    global item_list
    collected = []

    new_items = []
    for x, y, item_type in item_list:
        distance = np.hypot(x - player.x, y - player.y)

        # Use circular collision for pickup
        if distance <= pickup_radius:
            collected.append(item_type)
            if item_type == "cactus":
                player.damage(5)
            elif item_type == "crate":
                loot = generate_loot(LOOTTABLE_CRATE, 5)
                for i in loot:
                    if i == "Pharoah's Robes":
                        player.armor = 500
                player.inventory.extend(loot)
                loot_banner(loot)  
        else:
            new_items.append((x, y, item_type))

    item_list = new_items
    return collected if collected else "Empty"

def generate_loot(LOOTTABLE, times):
    l = []
    for x in range(times):
        l.append(random.choices(list(LOOTTABLE.keys()), weights=list(LOOTTABLE.values()), k=1)[0])
    return l
### GUN ANIMATION ###
def animate_gun(screen):
    gun_pos_x = SCREEN_WIDTH // 2
    gun_pos_y_base = SCREEN_HEIGHT - 90
    time = pg.time.get_ticks() / 5000
    offset_y = int(10 * np.sin(time * 2 * np.pi))
    gun_rect = GUN_IMG_SCALED.get_rect(center=(gun_pos_x, gun_pos_y_base + offset_y))
    screen.blit(GUN_IMG_SCALED, gun_rect)

### GAME LOOP ###
def init(running):
    global item_list, timer
    pg.display.set_caption("Python Raycasting Game - Dead Man's Draw")
    clock = pg.time.Clock()
    level = Level(player.level)
    pg.mixer.music.play(-1)

    # Generate items
    for _ in range(30): item_list.append([np.random.uniform(-100, 100), np.random.uniform(-100, 100), "cactus"] ) 
    for _ in range(10): item_list.append([np.random.uniform(-100, 100), np.random.uniform(-100, 100), "crate"] ) 


    while running:
        for e in pg.event.get():
            if e.type == pg.QUIT:
                return
            if options_clicked:
                for slider in sliders:
                    slider.handle_event(e)
        if player.spawned and not player.paused and not player.dead:
            frame = render_frame(_frame_buffer, player.x, player.y, player.rot,
                     ray_angles, cos_correction,
                     SKYBOX, FLOOR_ARRAY,
                     H_RES, V_RES, HALF_V_RES, height_map,
                     MAP_SIZE)
            surf = pg.surfarray.make_surface((frame * 255).astype(np.uint8))
            surf = pg.transform.scale(surf, (SCREEN_WIDTH, SCREEN_HEIGHT))
            screen.blit(surf, (0, 0))

            pg.draw.rect(screen, LIGHT_GRAY, (0, 0, SCREEN_WIDTH, 100))
            draw_text(screen, f"Health: {player.health}", 30, (255, 0, 0), (0, 20))
            draw_text(screen, f"Armor: {player.armor}", 30, (0, 0, 255), (0, 50))
            draw_text(screen, f"Ammo: {player.ammo}", 30, (0, 255, 255), (600, 20))
            draw_text(screen, f"Gun: {player.weapon}", 30, (0, 205, 255), (600, 50))
            screen.blit(GUY, (SCREEN_WIDTH // 2 -40, 0))

            if loot_banner_data["items"]:
                elapsed = pg.time.get_ticks() - loot_banner_data["start_time"]
                if elapsed < 3000:  # 2 seconds
                    for i, item in enumerate(loot_banner_data["items"]):
                        draw_text(screen, f"x1: {item}", 30, (255, 255, 0),
                                (SCREEN_WIDTH // 3, 200 + 40 * i))
                else:
                    loot_banner_data["items"] = []  

            render_items(screen, player)
            item_collect(player)
            render_pyramids(screen, player)
            animate_gun(screen)
            if player.health <= 0:
                player.dead = True
            if player.inventory_open:
                draw_text(screen, str(player.inventory), 30, (0, 0, 0), (SCREEN_WIDTH // 2, 300))
        else:
            render_main_menu(player, screen)

        p = player.move()
        dt=clock.tick(FPS)
        if p == 'shoot':
            timer += dt
            if timer >= player.gundelay and player.ammo > 0:
                gunshot.play()
                player.ammo-=1
                screen.blit(SHOOT, ( SCREEN_WIDTH // 2 -39, 390))
                timer = 0
        draw_text(screen, "FPS: " + str(round(clock.get_fps(), 2)), 20, (0, 0, 0), (0, 0))
        pg.display.flip()

if __name__ == "__main__":
    init(running)
    pg.quit()
    sys.exit(0)
