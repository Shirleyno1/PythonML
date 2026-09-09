import random


def random_food_position(snake, grid_width, grid_height):
    """Return a random free cell not occupied by the snake."""
    all_positions = [(x, y) for x in range(grid_width) for y in range(grid_height)]
    available = list(set(all_positions) - set(snake))
    if not available:
        return None
    return random.choice(available)
