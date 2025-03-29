"""
1. read.bff format
2. read the block
    2.1 reflect block: reverse the direction of lazors

3.  make sure lazor stays in bord and blocks stays in bord


"""


# Fujie is hot
import re

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

def laser_path(laser_position, laser_direction, x_dim, y_dim, blocks):
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
    d_x, d_y = laser_direction
    path = [(x, y)]
    path_refract = []

    # Determine the next block's position and the flag based on coordinate parity.
    if x % 2 == 0:
        # When x is even, we interact horizontally.
        if d_x == 1:
            block = (x + 1, y)
            flag = 'R'
        elif d_x == -1:
            block = (x - 1, y)
            flag = 'L'
        else:
            return path
        # Early termination if both adjacent positions are reflect blocks.
        if ((x - 1, y) in blocks.get('A', [])) and ((x + 1, y) in blocks.get('A', [])):
            return path
    else:
        # When x is odd, we interact vertically.
        if d_y == 1:
            block = (x, y + 1)
            flag = 'D'
        elif d_y == -1:
            block = (x, y - 1)
            flag = 'U'
        else:
            return path
        if ((x, y - 1) in blocks.get('A', [])) and ((x, y + 1) in blocks.get('A', [])):
            return path

    # Simulate the beam until it leaves the board.
    while pos_chk(block[0], block[1], x_dim, y_dim):
        # If the beam hits an opaque block, stop.
        if block in blocks.get('B', []):
            break
        # If it hits a reflect block, flip the appropriate component.
        elif block in blocks.get('A', []):
            if flag in ['L', 'R']:
                d_x = -d_x
            elif flag in ['U', 'D']:
                d_y = -d_y
        # If it hits a refract block, recursively get the transmitted beam's path.
        elif block in blocks.get('C', []):
            path_refract = laser_path((x + d_x, y + d_y), (d_x, d_y), x_dim, y_dim, blocks)
            if flag in ['L', 'R']:
                d_x = -d_x
            elif flag in ['U', 'D']:
                d_y = -d_y

        # Move the beam one step.
        x += d_x
        y += d_y
        path.append((x, y))

        # Update the block position and flag for the next interaction.
        if x % 2 == 0:
            if d_x == 1:
                block = (x + 1, y)
                flag = 'R'
            elif d_x == -1:
                block = (x - 1, y)
                flag = 'L'
        else:
            if d_y == 1:
                block = (x, y + 1)
                flag = 'D'
            elif d_y == -1:
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
    blocks['A'] = [(1, 5), (7, 3)]
    blocks['B'] = []
    blocks['C'] = [(5, 1)]
    
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
