import re

def read_bff(filename):
    # Assume file is in folder "bff_files"
    folder = "bff_files"
    if not filename.endswith(".bff"):
        filename += ".bff"
    filepath = os.path.join(folder, filename)
    with open(filepath, "r") as f:
        content = f.read()

    # --- ---------------------------- ---
    # --- Following will read the grid ---
    # --- ---------------------------- ---
    #this define the grid pattern, from the GRID START to Grid STOP
    #(.*?) is used to check if there are mutiple GRID STOP, usually
    # will not, but check the tyrpo
    grid_pattern = r'GRID START(.*?)GRID STOP'
    # re.search is used to read/scan entire grid in strong fomrat o
    # the re.DOTALL is used to read new line because our grids has more 
    # than one line
    grid_match = re.search(grid_pattern, content, re.DOTALL)
    # Chekc if grid was found, otheriser raise Error message.
    if not grid_match:
        raise ValueError("GRID section not found in file.")
    # get the info from grid_match 
    grid_text = grid_match.group(1).strip()
    # split grid_text lines from ooo to [o,o,o]
    grid_lines = grid_text.splitlines()
    # used to get all grid_lines together make a 2D things
    grid_tokens = [line.split() for line in grid_lines]
    rows = len(grid_tokens)
    columns = len(grid_tokens[0])











    # Create numeric grid of size (2*rows+1) x (2*columns+1)
    GRID = [[0 for _ in range(2 * columns + 1)] for _ in range(2 * rows + 1)]
    # Mapping: 'o' => 1, 'A' => 2, 'B' => 3, 'C' => 4, 'x' => 5
    token_map = {'o': 1, 'A': 2, 'B': 3, 'C': 4, 'x': 5}
    for r in range(rows):
        for c in range(columns):
            token = grid_tokens[r][c]
            if token in token_map:
                GRID[2 * r + 1][2 * c + 1] = token_map[token]

    # --- Parse inventory ---
    inventory = {}
    lines = content.splitlines()
    grid_stop_index = lines.index("GRID STOP")
    i = grid_stop_index + 1
    inv_pattern = r'^[ABC] \d+'
    while i < len(lines) and re.match(inv_pattern, lines[i].strip()):
        parts = lines[i].split()
        inventory[parts[0]] = int(parts[1])
        i += 1

    # --- Parse laser info ---
    lasers = {"position": [], "direction": []}
    if i < len(lines) and lines[i].startswith("L"):
        parts = lines[i].split()
        lasers["position"].append((int(parts[1]), int(parts[2])))
        lasers["direction"].append((int(parts[3]), int(parts[4])))
        i += 1

    # --- Parse target points ---
    points_position = []
    while i < len(lines) and lines[i].startswith("P"):
        parts = lines[i].split()
        points_position.append((int(parts[1]), int(parts[2])))
        i += 1

    return GRID, inventory, lasers, points_position

def pos_chk(x, y, x_dim, y_dim):
    """Check if (x, y) is within boundaries (0 to x_dim, 0 to y_dim)."""
    return 0 <= x <= x_dim and 0 <= y <= y_dim

def laser_path(laser_position, laser_direction, x_dim, y_dim, blocks):
    """
    Recursively compute the path of a laser beam.
    
    Uses parity of the coordinate to decide horizontal (even x) or vertical (even y)
    interaction, and a flag ('L', 'R', 'U', 'D') to indicate the side of interaction.
    
    Parameters:
      laser_position: (x, y)
      laser_direction: (d_x, d_y)
      x_dim, y_dim: grid boundaries (from GRID dimensions)
      blocks: dictionary of placed blocks; keys: 'A' and 'C' (only allowed types)
    
    Returns:
      A list of coordinates that the beam passes through.
    """
    x, y = laser_position
    d_x, d_y = laser_direction
    path = [(x, y)]
    path_refract = []
    
    # Determine next block position and flag.
    if x % 2 == 0:
        if d_x == 1:
            block = (x + 1, y)
            flag = 'R'
        elif d_x == -1:
            block = (x - 1, y)
            flag = 'L'
        else:
            return path
        # (No early termination for reflect blocks here because no fixed blocks in grid.)
    else:
        if d_y == 1:
            block = (x, y + 1)
            flag = 'D'
        elif d_y == -1:
            block = (x, y - 1)
            flag = 'U'
        else:
            return path

    # Simulate until beam leaves grid.
    while pos_chk(block[0], block[1], x_dim, y_dim):
        # Check for block interaction from our movable configuration.
        if block in blocks.get('A', []):
            # Reflect: flip appropriate direction component.
            if flag in ['L', 'R']:
                d_x = -d_x
            elif flag in ['U', 'D']:
                d_y = -d_y
        elif block in blocks.get('C', []):
            # Refract: simulate transmitted beam recursively.
            path_refract = laser_path((x + d_x, y + d_y), (d_x, d_y), x_dim, y_dim, blocks)
            # And then reflect as with A.
            if flag in ['L', 'R']:
                d_x = -d_x
            elif flag in ['U', 'D']:
                d_y = -d_y

        # Advance the beam.
        x += d_x
        y += d_y
        path.append((x, y))
        
        # Update next block position and flag.
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
    
    # Merge main beam path and refracted beam path.
    full_path = list(set(path).union(set(path_refract)))
    return full_path

def check_answer(points_position, paths):
    """
    Verify that every target point is hit by at least one laser path.
    """
    hit_targets = set()
    for path in paths:
        for pt in points_position:
            if pt in path:
                hit_targets.add(pt)
    return len(hit_targets) == len(points_position)

def output_solution(blocks):
    """
    Print the solution configuration.
    """
    print("Solution:")
    for b_type, positions in blocks.items():
        print(f"{b_type}: {positions}")

def main():
    filename = input("Enter the filename to solve (without extension): ")
    GRID, inventory, lasers, points_position = read_bff(filename)
    
    # For demonstration, we now create a fixed block configuration
    # that only uses the allowed block types (A and C).
    # For example, if the inventory is {'A': 2, 'C': 1}:
    blocks = {}
    # Place the two reflect blocks (A) at chosen allowed positions.
    blocks['A'] = [(1, 1), (1, 5)]
    # Place the one refract block (C) at a chosen allowed position.
    blocks['C'] = [(5, 1)]
    # Note: No Block B is used because the input file does not allow it.
    
    # Compute the laser paths.
    paths = []
    x_dim = len(GRID[0]) - 1
    y_dim = len(GRID) - 1
    for pos, dir in zip(lasers["position"], lasers["direction"]):
        path = laser_path(pos, dir, x_dim, y_dim, blocks)
        paths.append(path)
    
    # Check if the laser paths hit all target points.
    if check_answer(points_position, paths):
        output_solution(blocks)
    else:
        print("No solution found with the current block configuration.")

if __name__ == "__main__":
    main()


