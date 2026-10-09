import pygame
from dataclasses import dataclass
from typing import Tuple

@dataclass
class BookData:
    title: str = "Untitled"
    width: int = 28
    height: int = 112
    thickness: int = 28
    color: Tuple[int,int,int] = (220, 180, 140)
    x: int = 0
    y: int = 0
    rotation: int = 0
    horizontal: bool = False

    @property
    def w(self):
        return 112 if self.horizontal else 28
    @property
    def h(self):
        return 28 if self.horizontal else 112

class Book:
    def __init__(self, data: BookData):
        self.data = data
        self.vy = 0.0
        self.vx = 0.0
        self.is_falling = False
        self.shelf_id = 0
        self.is_rotating = False
        self.rotation = 0.0
        self.rotation_progress = 0.0
        self.will_be_vertical = False
        self.pivot_x = 0
        self.pivot_y = 0
        self.original_horizontal = False

    def get_rect(self) -> pygame.Rect:
        if self.is_rotating:
            prog = self.rotation_progress
            cur_w = int(112 * (1-prog) + 28 * prog)
            cur_h = int(28 * (1-prog) + 112 * prog)
            return pygame.Rect(self.data.x, self.data.y, cur_w, cur_h)
        return pygame.Rect(self.data.x, self.data.y, self.data.w, self.data.h)

    def draw(self, screen: pygame.Surface, alpha=255):
        rect = self.get_rect()
        r,g,b = self.data.color
        if self.is_rotating and self.original_horizontal:
            prog = max(0.0, min(1.0, self.rotation_progress))
            angle = prog * 90
            surf = pygame.Surface((112, 28), pygame.SRCALPHA)
            surf.fill((r,g,b))
            pygame.draw.rect(surf, (0,0,0), (0,0,112,28), 1)
            rotated = pygame.transform.rotate(surf, -angle)
            rot_rect = rotated.get_rect(center=rect.center)
            screen.blit(rotated, rot_rect)
        else:
            pygame.draw.rect(screen, (r,g,b), rect)
            pygame.draw.rect(screen, (0,0,0), rect, 1)
            if not self.data.horizontal:
                pygame.draw.line(screen, (0,0,0), (rect.x+5, rect.y), (rect.x+5, rect.bottom), 1)

class PhantomBook(Book):
    def draw(self, screen, is_valid: bool):
        color = (50, 255, 50) if is_valid else (255, 50, 50)
        rect = self.get_rect()
        s = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        s.fill((*color, 90))
        pygame.draw.rect(s, (*color, 200), (0,0, rect.width, rect.height), 2)
        screen.blit(s, (rect.x, rect.y))
