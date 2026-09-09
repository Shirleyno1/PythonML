import pygame
import sys
from settings import *
from utils import random_food_position


class SnakeGame:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Snake")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, 36)
        self.small_font = pygame.font.SysFont(None, 24)

        self.MOVE_EVENT = pygame.USEREVENT + 1
        pygame.time.set_timer(self.MOVE_EVENT, MOVE_INTERVAL_MS)

        self.reset()

    def reset(self):
        start_x = GRID_WIDTH // 2
        start_y = GRID_HEIGHT // 2
        self.snake = [(start_x, start_y), (start_x - 1, start_y), (start_x - 2, start_y)]
        self.direction = RIGHT
        self.next_direction = RIGHT
        self.food = random_food_position(self.snake, GRID_WIDTH, GRID_HEIGHT)
        self.score = 0
        self.game_over = False

    def handle_key(self, key):
        if key == pygame.K_r and self.game_over:
            self.reset()
        elif key in (pygame.K_q, pygame.K_ESCAPE):
            pygame.quit()
            sys.exit()
        elif key in KEY_TO_DIR:
            new_dir = KEY_TO_DIR[key]
            # prevent reversing
            if (new_dir[0] * -1, new_dir[1] * -1) != self.direction:
                self.next_direction = new_dir

    def move_snake(self):
        if self.game_over:
            return
        self.direction = self.next_direction
        head_x, head_y = self.snake[0]
        dx, dy = self.direction
        new_head = (head_x + dx, head_y + dy)

        # collisions
        x, y = new_head
        if x < 0 or x >= GRID_WIDTH or y < 0 or y >= GRID_HEIGHT:
            self.game_over = True
            return
        if new_head in self.snake:
            self.game_over = True
            return

        self.snake.insert(0, new_head)
        if self.food and new_head == self.food:
            self.score += 1
            self.food = random_food_position(self.snake, GRID_WIDTH, GRID_HEIGHT)
        else:
            self.snake.pop()

    def draw_cell(self, pos, color):
        x, y = pos
        rect = pygame.Rect(x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE)
        pygame.draw.rect(self.screen, color, rect)

    def draw(self):
        self.screen.fill(BG_COLOR)
        # grid
        for x in range(0, WINDOW_WIDTH, CELL_SIZE):
            pygame.draw.line(self.screen, GRID_COLOR, (x, 0), (x, WINDOW_HEIGHT))
        for y in range(0, WINDOW_HEIGHT, CELL_SIZE):
            pygame.draw.line(self.screen, GRID_COLOR, (0, y), (WINDOW_WIDTH, y))

        # food
        if self.food:
            self.draw_cell(self.food, FOOD_COLOR)

        # snake
        if self.snake:
            self.draw_cell(self.snake[0], SNAKE_HEAD_COLOR)
            for seg in self.snake[1:]:
                self.draw_cell(seg, SNAKE_COLOR)

        # score
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

    def update(self, events):
        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                self.handle_key(event.key)
            elif event.type == self.MOVE_EVENT:
                self.move_snake()

    def run(self):
        while True:
            events = pygame.event.get()
            self.update(events)
            self.draw()
            self.clock.tick(60)
