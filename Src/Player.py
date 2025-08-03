import pygame as pg
import sys
import numpy as np


class Player:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.rot = 0
        self.pos = pg.Vector2(x, y)
        self.inventory = []
        self.inventory_open = False
        self.weapon = "Pistol"
        self.unlocked_weapons = ["Pistol"]
        self.ammo = 20
        self.gundelay = 300
        self.health = 100
        self.armor = 100
        self.spawned = False
        self.dead = False
        self.level = 0
        self.currentLevelComplete = False
        self.config = {
        "Max Fps": 60,
        "Graphics": "High", 
        "Brightness": 0,
        "Vsync": False
        }
        self.paused = False
    def spawn(self): # start level
        self.spawned = True
    def select_weapon():
        pass
    def move(self):
        keys = pg.key.get_pressed()
        if keys[pg.K_LEFT] or keys[ord('a')]:
            self.rot -= 0.1
        if keys[pg.K_RIGHT] or keys[ord('d')]:
            self.rot += 0.1
        if keys[pg.K_UP] or keys[ord('w')]: # we use sin and cos of the angle we are facing to move in that direction
            self.y = self.y  + np.sin(self.rot)*.1
            self.x = self.x  + np.cos(self.rot)*.1
        if keys[pg.K_DOWN] or keys[ord('s')]: 
            self.y = self.y  - np.sin(self.rot)*.1
            self.x = self.x  - np.cos(self.rot)*.1
        if keys[pg.K_ESCAPE]:
            self.paused = True
        if keys[pg.K_SPACE]:            
            return "shoot"
        if keys[pg.K_i]:
            self.inventory_open = not self.inventory_open
            print(self.inventory)
        if keys[pg.K_t]:
            if not self.unlocked_weapons:
                return
            current = self.unlocked_weapons.index(self.weapon)
            current = (current+1) % len(self.unlocked_weapons)
            self.weapon = self.unlocked_weapons[current]

            
        
    def eat(self, food):
        pass
    def damage(self, amount):
        if self.armor - amount <= 0:
            self.health -= abs(self.armor - amount)
        else:
            self.armor -= amount