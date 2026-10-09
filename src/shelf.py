import pygame, json, pathlib
from typing import List

class ShelfSystem:
    def __init__(self, config_path: pathlib.Path):
        data = json.loads(config_path.read_text(encoding="utf-8"))[0]
        self.name = data["name"]
        self.x = data["x"]
        self.y = data["y"]
        self.width = data["width"]
        self.height = data["height"]
        self.shelf_count = data["shelves"]
        self.thickness = data["shelf_thickness"]
        self._calc_shelves()

    def _calc_shelves(self):
        inner_h = self.height - self.thickness
        step = inner_h / self.shelf_count
        self.shelves_y = [int(self.y + i*step) for i in range(self.shelf_count+1)]
        self.police_rects = []
        for i in range(self.shelf_count):
            top = self.shelves_y[i] + self.thickness
            bottom = self.shelves_y[i+1]
            # +2px запас для перфекционизма - чтобы влезла еще одна книга как на скрине
            self.police_rects.append(pygame.Rect(self.x+10, top-1, self.width-20, bottom-top+2))

    def draw(self, screen):
        pygame.draw.rect(screen, (120,100,90), (self.x, self.y, self.width, self.height))
        pygame.draw.rect(screen, (200,190,180), (self.x+5, self.y+5, self.width-10, self.height-10))
        for y in self.shelves_y:
            pygame.draw.rect(screen, (150,130,120), (self.x, y, self.width, self.thickness))
        for r in self.police_rects:
            pygame.draw.rect(screen, (210,205,195), r)

    def is_inside_any_shelf(self, rect: pygame.Rect) -> bool:
        return any(pr.contains(rect) for pr in self.police_rects)
