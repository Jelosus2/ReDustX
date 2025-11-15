import re
import shutil
from PIL import Image

def parse_atlas(atlas_path):
    atlas_database = {}
    try:
        with open(atlas_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        return None

    blocks = re.split(r'\n(?=[^\n]+\.png\n)', content.strip())
    
    for block_text in blocks:
        block_text = block_text.strip()
        if not block_text:
            continue
        
        lines = block_text.split('\n')
        block_name = lines[0]
        
        data = {'sprites': []}
        sprite_lines = []
        
        for line in lines[1:]:
            if line.strip().startswith('size:'):
                data['size_line'] = line
            elif line.strip().startswith('filter:'):
                data['filter_line'] = line
            else:
                sprite_lines.append(line)

        data['sprites'] = '\n'.join(sprite_lines)
        atlas_database[block_name] = data
        
    return atlas_database

def generate_operations(base_dir, file_prefix):
    """Automatically scans a directory and generates merge/copy operations."""
    all_files_in_dir = base_dir.iterdir()
    png_files = [f.name for f in all_files_in_dir if f.name.startswith(file_prefix) and f.name.endswith('.png')]

    def sort_key(filename):
        if filename == f"{file_prefix}.png":
            return 1
        match = re.search(r'_(\d+)\.png$', filename)
        if match:
            return int(match.group(1))
        return float('inf')

    png_files.sort(key=sort_key)

    operations = []
    source_pngs_for_backup = png_files[:]
    i = 0
    pair_index = 1
    while i < len(png_files):
        if pair_index == 1:
            output_filename = f"{file_prefix}.png"
        else:
            output_filename = f"{file_prefix}_{pair_index}.png"
            
        if i + 1 < len(png_files):
            op = {"type": "merge", "sources": [png_files[i], png_files[i+1]], "output": output_filename}
            operations.append(op)
            i += 2
        else:
            op = {"type": "copy", "sources": [png_files[i]], "output": output_filename}
            operations.append(op)
            i += 1
        pair_index += 1
        
    return operations, source_pngs_for_backup

def merge_textures(mod_dir_path, old_mods_dir_path):
    """Processes all assets for a single mod directory in-place."""

    atlas_files = list(mod_dir_path.glob("*.atlas"))
    if not atlas_files:
        return -1
    
    original_atlas_path = atlas_files[0]
    file_prefix = original_atlas_path.stem

    # 1. Generate operations and get a list of all pngs to be processed
    operations, all_source_pngs = generate_operations(mod_dir_path, file_prefix)
    if not operations:
        return 0

    # 2. Parse original Atlas
    atlas_db = parse_atlas(original_atlas_path)
    if not atlas_db:
        return -2

    # 3. Create old_mods directory and move original files
    old_dir = old_mods_dir_path.joinpath(mod_dir_path.name)
    old_dir.mkdir(parents=True, exist_ok=True)
    
    # Move original atlas
    shutil.move(str(original_atlas_path), str(old_dir.joinpath(original_atlas_path.name)))
    # Move all source pngs
    for png_file in all_source_pngs:
        shutil.move(str(mod_dir_path.joinpath(png_file)), str(old_dir.joinpath(png_file)))

    final_atlas_blocks = []

    # 4. Process all image operations
    for op in operations:
        op_type = op['type']
        sources = op['sources']
        output_name = op['output']
        # Output path is now the original mod directory
        output_path = str(mod_dir_path.joinpath(output_name))
        
        if op_type == 'copy':
            source_path = str(old_dir.joinpath(sources[0])) # Read from old_mods dir
            shutil.copy(source_path, output_path)
            original_data = atlas_db.get(sources[0])
            if original_data:
                new_block = [output_name, original_data['size_line'], original_data['filter_line'], original_data['sprites']]
                final_atlas_blocks.append('\n'.join(new_block))

        elif op_type == 'merge':
            img1_name, img2_name = sources[0], sources[1]
            # Read from old_mods dir
            img1_path, img2_path = str(old_dir.joinpath(img1_name)), str(old_dir.joinpath(img2_name))
            img1 = Image.open(img1_path)
            img2 = Image.open(img2_path)
            w1, h1 = img1.size
            w2, h2 = img2.size
            
            new_width = w1 + w2
            new_height = max(h1, h2)

            new_img = Image.new('RGBA', (new_width, new_height))
            new_img.paste(img1, (0, 0))
            new_img.paste(img2, (w1, 0))
            new_img.save(output_path)

            img1_data = atlas_db.get(img1_name)
            img2_data = atlas_db.get(img2_name)
            if not img1_data or not img2_data: continue

            modified_sprites_img2 = []
            for line in img2_data['sprites'].split('\n'):
                if line.strip().startswith('bounds:'):
                    try:
                        parts = line.strip().split(':')
                        coords = parts[1].strip().split(',')
                        x, y, w, h = [int(c.strip()) for c in coords]
                        x += w1
                        modified_sprites_img2.append(f" bounds: {x},{y},{w},{h}")
                    except: modified_sprites_img2.append(line)
                else: modified_sprites_img2.append(line)
            
            new_block_content = [output_name, f" size: {new_width},{new_height}", img1_data['filter_line'], img1_data['sprites'], '\n'.join(modified_sprites_img2)]
            final_atlas_blocks.append('\n'.join(new_block_content))

    # 5. Write final Atlas file to the mod directory
    final_atlas_path = mod_dir_path.joinpath(f"{file_prefix}.atlas")
    with open(final_atlas_path, 'w') as f:
        f.write('\n\n'.join(final_atlas_blocks))
    
    return 1