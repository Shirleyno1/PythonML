"""
Simple Snake game using Pygame

Controls:
- Arrow keys or WASD to move
- R to restart after game over
- Q or ESC to quit

Run: python snake_game.py
Requires: pygame
"""
import pygame
import sys
import random

# Config
CELL_SIZE = 20
GRID_WIDTH = 20
GRID_HEIGHT = 20
WINDOW_WIDTH = CELL_SIZE * GRID_WIDTH
WINDOW_HEIGHT = CELL_SIZE * GRID_HEIGHT
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


def draw_grid(surface):
    for x in range(0, WINDOW_WIDTH, CELL_SIZE):
        pygame.draw.line(surface, GRID_COLOR, (x, 0), (x, WINDOW_HEIGHT))
    for y in range(0, WINDOW_HEIGHT, CELL_SIZE):
        pygame.draw.line(surface, GRID_COLOR, (0, y), (WINDOW_WIDTH, y))


def random_food_position(snake):
    all_positions = [(x, y) for x in range(GRID_WIDTH) for y in range(GRID_HEIGHT)]
    available = list(set(all_positions) - set(snake))
    if not available:
        return None
    return random.choice(available)


class SnakeGame:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Snake")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, 36)
        self.small_font = pygame.font.SysFont(None, 24)

        self.reset()

        # Custom event for movement so movement is independent of frame rate
        self.MOVE_EVENT = pygame.USEREVENT + 1
        pygame.time.set_timer(self.MOVE_EVENT, MOVE_INTERVAL_MS)

    def reset(self):
        start_x = GRID_WIDTH // 2
        start_y = GRID_HEIGHT // 2
        self.snake = [(start_x, start_y), (start_x - 1, start_y), (start_x - 2, start_y)]
        self.direction = RIGHT
        self.next_direction = RIGHT
        self.food = random_food_position(self.snake)
        self.score = 0
        self.game_over = False

    def handle_key(self, key):
        if key in (pygame.K_UP, pygame.K_w):
            if self.direction != DOWN:
                self.next_direction = UP
        elif key in (pygame.K_DOWN, pygame.K_s):
            if self.direction != UP:
                self.next_direction = DOWN
        elif key in (pygame.K_LEFT, pygame.K_a):
            if self.direction != RIGHT:
                self.next_direction = LEFT
        elif key in (pygame.K_RIGHT, pygame.K_d):
            if self.direction != LEFT:
                self.next_direction = RIGHT
        elif key == pygame.K_r:
            if self.game_over:
                self.reset()
        elif key in (pygame.K_q, pygame.K_ESCAPE):
            pygame.quit()
            sys.exit()

    def move_snake(self):
        if self.game_over:
            return
        self.direction = self.next_direction
        head_x, head_y = self.snake[0]
        dx, dy = self.direction
        new_head = (head_x + dx, head_y + dy)

        # Check collisions with walls
        x, y = new_head
        if x < 0 or x >= GRID_WIDTH or y < 0 or y >= GRID_HEIGHT:
            self.game_over = True
            return

        # Check collision with self
        if new_head in self.snake:
            self.game_over = True
            return

        # Add new head
        self.snake.insert(0, new_head)

        # Check food
        if self.food and new_head == self.food:
            self.score += 1
            self.food = random_food_position(self.snake)
        else:
            # remove tail
            self.snake.pop()

    def draw_cell(self, pos, color):
        x, y = pos
        rect = pygame.Rect(x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE)
        pygame.draw.rect(self.screen, color, rect)

    def draw(self):
        self.screen.fill(BG_COLOR)
        draw_grid(self.screen)

        # Draw food
        if self.food:
            self.draw_cell(self.food, FOOD_COLOR)

        # Draw snake
        if self.snake:
            # head
            self.draw_cell(self.snake[0], SNAKE_HEAD_COLOR)
            # body
            for seg in self.snake[1:]:
                self.draw_cell(seg, SNAKE_COLOR)

        # Score
        score_surf = self.small_font.render(f"Score: {self.score}", True, TEXT_COLOR)
        self.screen.blit(score_surf, (5, 5))

        if self.game_over:
            self.draw_game_over()

        pygame.display.flip()

    def draw_game_over(self):
        s = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        s.fill((0, 0, 0, 150))
        self.screen.blit(s, (0, 0))

        msg = "Game Over"
        sub = "Press R to restart or Q to quit"
        msg_surf = self.font.render(msg, True, TEXT_COLOR)
        sub_surf = self.small_font.render(sub, True, TEXT_COLOR)

        msg_rect = msg_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 20))
        sub_rect = sub_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 20))

        self.screen.blit(msg_surf, msg_rect)
        self.screen.blit(sub_surf, sub_rect)

    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.KEYDOWN:
                    self.handle_key(event.key)
                elif event.type == self.MOVE_EVENT:
                    self.move_snake()

            self.draw()
            self.clock.tick(60)


if __name__ == "__main__":
    game = SnakeGame()
    game.run()
