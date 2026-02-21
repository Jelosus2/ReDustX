import re
import shutil
from PIL import Image

def texture_sort_key(file_prefix, filename):
    if filename == f"{file_prefix}.png":
        return 1
    
    match = re.search(r'_(\d+)\.png$', filename)
    if match:
        return int(match.group(1))
    
    return float('inf')

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

def generate_operations(base_dir, file_prefix, target_pngs):
    """Automatically scans a directory and generates merge/copy operations."""
    all_files_in_dir = base_dir.iterdir()
    png_files = [f.name for f in all_files_in_dir if f.name.startswith(file_prefix) and f.name.endswith('.png')]
    png_files.sort(key=lambda name: texture_sort_key(file_prefix, name))

    operations = []
    source_pngs_for_backup = png_files[:]

    target_pngs = sorted(set(target_pngs), key=lambda name: texture_sort_key(file_prefix, name))

    if len(target_pngs) >= len(png_files):
        for source_name in png_files:
            operations.append({"type": "copy", "sources": [source_name], "output": source_name})
        return operations, source_pngs_for_backup

    for index, output_name in enumerate(target_pngs):
        if index < len(target_pngs) - 1:
            operations.append({"type": "copy", "sources": [png_files[index]], "output": output_name})
            continue

        remaining_sources = png_files[index:]
        op_type = "merge" if len(remaining_sources) > 1 else "copy"
        operations.append({"type": op_type, "sources": remaining_sources, "output": output_name})
        
    return operations, source_pngs_for_backup

def shift_bounds_line_x(line, x_offset):
    if not line.strip().startswith('bounds:'):
        return line

    try:
        parts = line.strip().split(':')
        coords = parts[1].strip().split(',')
        x, y, w, h = [int(c.strip()) for c in coords]
        x += x_offset
        return f" bounds: {x},{y},{w},{h}"
    except Exception:
        return line

def merge_textures(mod_dir_path, old_mods_dir_path, target_pngs):
    """Processes all assets for a single mod directory in-place."""

    atlas_files = list(mod_dir_path.glob("*.atlas"))
    if not atlas_files:
        return -1
    
    original_atlas_path = atlas_files[0]
    file_prefix = original_atlas_path.stem

    # 1. Generate operations and get a list of all pngs to be processed
    operations, all_source_pngs = generate_operations(mod_dir_path, file_prefix, target_pngs)
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
            source_images = []
            for image_name in sources:
                image_path = str(old_dir.joinpath(image_name))
                image = Image.open(image_path).convert('RGBA')
                source_images.append((image_name, image))

            widths = [image.size[0] for _, image in source_images]
            heights = [image.size[1] for _, image in source_images]
            new_width = sum(widths)
            new_height = max(heights)

            new_img = Image.new('RGBA', (new_width, new_height))

            atlas_sections = []
            filter_line = None
            x_offset = 0
            for image_name, image in source_images:
                new_img.paste(image, (x_offset, 0))

                original_data = atlas_db.get(image_name)
                if original_data:
                    if filter_line is None:
                        filter_line = original_data['filter_line']

                    if x_offset == 0:
                        atlas_sections.append(original_data['sprites'])
                    else:
                        shifted_lines = [shift_bounds_line_x(line, x_offset) for line in original_data['sprites'].split('\n')]
                        atlas_sections.append('\n'.join(shifted_lines))

                x_offset += image.size[0]

            new_img.save(output_path)

            for _, image in source_images:
                image.close()

            if not atlas_sections:
                continue

            new_block_content = [output_name, f" size: {new_width},{new_height}", filter_line or "filter:Linear,Linear", '\n'.join(atlas_sections)]
            final_atlas_blocks.append('\n'.join(new_block_content))

    # 5. Write final Atlas file to the mod directory
    final_atlas_path = mod_dir_path.joinpath(f"{file_prefix}.atlas")
    with open(final_atlas_path, 'w', encoding='utf-8') as f:
        f.write('\n\n'.join(final_atlas_blocks))
    
    return 1
