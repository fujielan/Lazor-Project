"""
1. read.bff format
2. read the block
    2.1 reflect block: reverse the direction of lazors

3.  make sure lazor stays in bord and blocks stays in bord


"""


# Fujie is hot
import re
import itertools
from collections import deque

class Block:

    def __init__(self, type: str, transparent: bool = False, reflective : bool = False, fixed : bool = False):
        self.type = type
        self.transparent = transparent
        self.reflective = reflective
        self.fixed = fixed

    def is_fixed(self):
        return self.fixed

    def is_transparent(self):
        return self.transparent

    def is_reflective(self):
        return self.reflective
    
    def __repr__(self):
        return f"<{self.type} - {'FIXED' if self.fixed else 'UNFIXED'}, " \
               f"{'TRANSPARENT' if self.transparent else 'OPAQUE'}, " \
               f"{'REFLECTIVE' if self.reflective else 'NON-REFLECTIVE'}>"

    def __str__(self):
        return repr(self)

BLOCK_TYPES = {
    "BLANK": Block("BLANK", transparent=True),
    "OPAQUE": Block("OPAQUE"),
    "REFLECT": Block("REFLECT", reflective=True),
    "REFRACT": Block("REFRACT", transparent=True, reflective=True),
    "FIXED_BLANK": Block("FIXED_BLANK", transparent=True, fixed=True),
    "FIXED_OPAQUE": Block("FIXED_OPAQUE", fixed=True),
    "FIXED_REFLECT": Block("FIXED_REFLECT", reflective=True, fixed=True),
    "FIXED_REFRACT": Block("FIXED_REFRACT", transparent=True, reflective=True, fixed=True),
}


def read_bff(filename):
    """
    Reads a .bff file and returns four elements:
      - GRID: a 2D numeric grid where:
          0 = gap,
          1 = allowed position (open cell) for a movable block,
          2 = fixed reflect block (A),
          3 = fixed opaque block (B),
          4 = fixed refract block (C),
          5 = cell where blocks cannot be placed.
      - inventory: a dictionary of available movable blocks (e.g., {'A':3, 'C':1}).
      - lasers: a dictionary with keys 'position' and 'direction' (each a list of tuples).
      - points_position: a list of target point coordinates.
    """
    # Ensure the filename ends with ".bff"
    if not filename.endswith(".bff"):
        filename += ".bff"
    with open(filename, "r") as f:
        content = f.read()

    # --- Parse the grid ---
    grid_pattern = r'GRID START(.*?)GRID STOP'
    grid_match = re.search(grid_pattern, content, re.DOTALL)
    if not grid_match:
        raise ValueError("GRID section not found in file.")
    grid_text = grid_match.group(1).strip()
    grid_lines = grid_text.splitlines()

    # Each line should be tokens separated by spaces (e.g., "o B o")
    grid_tokens = [line.split() for line in grid_lines]
    rows = len(grid_tokens)
    columns = len(grid_tokens[0])

    # Create a numeric grid with dimensions 2*rows+1 x 2*columns+1
    GRID = [[0 for _ in range(2 * columns + 1)] for _ in range(2 * rows + 1)]

    # Map tokens to numbers:
    token_map = {'o': 1, 'A': 2, 'B': 3, 'C': 4, 'x': 5}
    for r in range(rows):
        for c in range(columns):
            token = grid_tokens[r][c]
            if token in token_map:
                # Place the value at the center of the cell.
                GRID[2 * r + 1][2 * c + 1] = token_map[token]


    # --- Parse inventory, lasers and target points ---
    inventory = {}
    lasers = {"position": [], "direction": []}
    points_position = []
    
    # Start searching after "GRID STOP" line
    lines = content.splitlines()
    i = lines.index("GRID STOP")

    # Matching all the three types of data with regular expressions
    inv_pattern = r'^[ABC]'
    laser_pattern = r'^L'
    points_pattern = r'^P'

    while i < len(lines):
        line = lines[i].strip()
        if re.match(inv_pattern, line):
            parts = line.split()
            inventory[parts[0]] = int(parts[1])
        elif re.match(laser_pattern, line):
            parts = line.split()
            lasers["position"].append((int(parts[1]), int(parts[2])))
            lasers["direction"].append((int(parts[3]), int(parts[4])))
        elif re.match(points_pattern, line):
            parts = line.split()
            points_position.append((int(parts[1]), int(parts[2])))
        i += 1

    return GRID, inventory, lasers, points_position

def pos_chk(x, y, x_dim, y_dim):
    """
    Checks if the coordinate (x, y) is within the grid boundaries.
    """
    return 0 <= x <= x_dim and 0 <= y <= y_dim

def generate_block_placements(GRID, inventory):

    possible_pos = [(x, y) for x , row in enumerate(GRID)
                    for y, val in enumerate(row) if val == 1]
    
    block_types = list(inventory.keys())
    total_count = sum(inventory.values())

    all_position_combinations = itertools.combinations(possible_pos, total_count)
    all_schemes = []

    for position_comb in all_position_combinations:
        type_permutations = []
        index = 0
        
        for block_type in block_types:
            count = inventory[block_type] 
            type_permutations.append(itertools.permutations(position_comb[index:index+count]))
            index += count
        
        for perm in itertools.product(*type_permutations):
            scheme = {block_types[i]: list(perm[i]) for i in range(len(block_types))}
            all_schemes.append(scheme)
    
    return all_schemes



def laser_path(laser_position, laser_direction, x_dim, y_dim, block_list):
    """
    Recursively computes the path of a laser beam.
    
    The simulation uses the parity of the current coordinate to decide how to
    determine the next block interaction and a "flag" (e.g., 'L', 'R', 'U', 'D')
    to indicate which side of a cell the beam is approaching.
    
    Parameters:
      laser_position: tuple (x, y) – starting coordinate of the beam.
      laser_direction: tuple (d_x, d_y) – initial direction.
      x_dim, y_dim: grid boundaries.
      blocks: dictionary of block placements:
              blocks['A'], blocks['B'], blocks['C'] are lists of coordinates.
    
    Returns:
      A list of coordinates that the beam passes through.
    """
    x, y = laser_position
    dx, dy = laser_direction
    path = [(x, y)]
    path_refract = []

    # Determine the next block's position and the flag based on coordinate parity.
    if x % 2 == 0:
        # When x is even, we interact horizontally.
        if dx == 1:
            block = (x + 1, y)
            flag = 'R'
        elif dx == -1:
            block = (x - 1, y)
            flag = 'L'
        else:
            return path
        # Early termination if both adjacent positions are reflect blocks.
        if ((x - 1, y) in block_list.get('A', [])) and ((x + 1, y) in block_list.get('A', [])):
            return path
    else:
        # When x is odd, we interact vertically.
        if dy == 1:
            block = (x, y + 1)
            flag = 'D'
        elif dy == -1:
            block = (x, y - 1)
            flag = 'U'
        else:
            return path
        if ((x, y - 1) in block_list.get('A', [])) and ((x, y + 1) in block_list.get('A', [])):
            return path

    # Simulate the beam until it leaves the board.
    while pos_chk(block[0], block[1], x_dim, y_dim):
        # If the beam hits an opaque block, stop.
        if block in block_list.get('B', []):
            break
        # If it hits a reflect block, flip the appropriate component.
        elif block in block_list.get('A', []):
            if flag in ['L', 'R']:
                dx = -dx
            elif flag in ['U', 'D']:
                dy = -dy
        # If it hits a refract block, recursively get the transmitted beam's path.
        elif block in block_list.get('C', []):
            path_refract = laser_path((x + dx, y + dy), (dx, dy), x_dim, y_dim, block_list)
            if flag in ['L', 'R']:
                dx = -dx
            elif flag in ['U', 'D']:
                dy = -dy

        # Move the beam one step.
        x += dx
        y += dy
        path.append((x, y))

        # Update the block position and flag for the next interaction.
        if x % 2 == 0:
            if dx == 1:
                block = (x + 1, y)
                flag = 'R'
            elif dx == -1:
                block = (x - 1, y)
                flag = 'L'
        else:
            if dy == 1:
                block = (x, y + 1)
                flag = 'D'
            elif dy == -1:
                block = (x, y - 1)
                flag = 'U'

    # Merge the main beam path with any additional refracted path.
    full_path = list(set(path).union(set(path_refract)))
    return full_path

def check_answer(points_position, paths):
    """
    Checks if every target point (in points_position) is hit by at least one laser path.
    
    Parameters:
      points_position: list of target coordinates.
      paths: list of paths (each path is a list of coordinates) from each laser.
    
    Returns:
      True if every target is hit; False otherwise.
    """
    hit_targets = set()
    for path in paths:
        for pt in points_position:
            if pt in path:
                hit_targets.add(pt)
    return len(hit_targets) == len(points_position)

def output_solution(blocks):
    """
    Outputs the solution configuration.
    
    For this demonstration, we simply print out the blocks dictionary.
    """
    print("Solution:")
    for b_type, positions in blocks.items():
        print(f"{b_type}: {positions}")

def main():
    filename = input("Enter the filename to solve (without extension): ")
    GRID, inventory, lasers, points_position = read_bff(filename)
    
    # For this refined version, we use a fixed block configuration as an example.
    # (A full solver would iterate through placements over allowed positions.)
    blocks = {}
    # Example configuration (based on the correct code hint):
    # blocks['A'] = [(1, 5), (7, 3)]
    # blocks['B'] = []
    # blocks['C'] = [(5, 1)]
    
    # Compute the laser paths for each laser.
    paths = []
    x_dim = len(GRID[0]) - 1
    y_dim = len(GRID) - 1
    for pos, dir in zip(lasers["position"], lasers["direction"]):
        path = laser_path(pos, dir, x_dim, y_dim, blocks)
        paths.append(path)
    
    if check_answer(points_position, paths):
        output_solution(blocks)
    else:
        print("No solution found with the current block configuration.")

if __name__ == "__main__":
    main()
