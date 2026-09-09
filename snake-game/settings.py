import pygame

# Grid / window
CELL_SIZE = 20
GRID_WIDTH = 20
GRID_HEIGHT = 20
WINDOW_WIDTH = CELL_SIZE * GRID_WIDTH
WINDOW_HEIGHT = CELL_SIZE * GRID_HEIGHT

# Timing
MOVE_INTERVAL_MS = 120  # snake moves every 120 ms

# Colors
BG_COLOR = (0, 0, 0)
GRID_COLOR = (40, 40, 40)
SNAKE_COLOR = (0, 255, 0)
SNAKE_HEAD_COLOR = (0, 200, 0)
FOOD_COLOR = (255, 0, 0)
TEXT_COLOR = (255, 255, 255)

# Directions
UP = (0, -1)
DOWN = (0, 1)
LEFT = (-1, 0)
RIGHT = (1, 0)

# Keys mapping (pygame key -> direction)
KEY_TO_DIR = {
    pygame.K_w: UP,
    pygame.K_UP: UP,
    pygame.K_s: DOWN,
    pygame.K_DOWN: DOWN,
    pygame.K_a: LEFT,
    pygame.K_LEFT: LEFT,
    pygame.K_d: RIGHT,
    pygame.K_RIGHT: RIGHT,
}
