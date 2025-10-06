# -*- coding: utf-8 -*-
import base64
import fnmatch
import json
import os
import re
import requests
import shutil
import struct
import sys
import UnityPy
import webbrowser
import subprocess
from InquirerPy import prompt
from PIL import Image
from tqdm import tqdm
from json_to_skel import json_to_skel
from pathlib import Path

import maintenance_info_pb2

RDXVersion = '1.0.0'
UnityPy.config.FALLBACK_UNITY_VERSION = '2022.3.22f1'

# Folders and paths
base_path = Path(__file__).parent

mods_folder = "mods/"
mods_folder_path = base_path.joinpath(mods_folder)

asset_bundles_folder = "bundles/"
asset_bundles_folder_path = base_path.joinpath(asset_bundles_folder)

asset_bundles_modded_folder = "bundles_modded/"
asset_bundles_modded_folder_path = base_path.joinpath(asset_bundles_modded_folder)

astc_encoder_dir = base_path.joinpath("astc_encoder")
if sys.platform.startswith("win"):
    _astc_candidates = [
        astc_encoder_dir.joinpath("astcenc-sse2.exe"),
        astc_encoder_dir.joinpath("astcenc-neon.exe"),
    ]
else:
    _astc_candidates = [
        astc_encoder_dir.joinpath("astcenc-sse2"),
        astc_encoder_dir.joinpath("astcenc-neon"),
    ]

astc_encoder_binary_path = next((p for p in _astc_candidates if p.exists()), _astc_candidates[0])

astc_encode_tmp_folder = "tmp/"
astc_encode_tmp_folder_path = base_path.joinpath(astc_encode_tmp_folder)

skeleton_data_bundles_paths = []

def get_cdn_version(quality):
    url = "https://mt.bd2.pmang.cloud/MaintenanceInfo"

    # Define the headers
    headers = {
        'accept': '*/*',
        'accept-encoding': 'gzip',
        'connection': 'close',
        'content-type': 'multipart/form-data',
        'host': 'mt.bd2.pmang.cloud',
        'user-agent': 'UnityPlayer/2022.3.22f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)',
    }
    data = 'EAQ='
    response = requests.put(url, headers=headers, data=data)

    base64_data = response.json()['data']
    binary_data = base64.b64decode(base64_data)

    response = maintenance_info_pb2.MaintenanceInfoResponse()  # Change type if needed
    response.ParseFromString(binary_data)

    return response.market_info.bundle_version if quality == 'HD' else response.market_info.bundle_version_sd

def download_catalog(quality, version):
    # Define the filename based on the quality
    filename = base_path.joinpath(f"catalog_{version}.json")

    # Check if the file exists in the current directory
    if filename.exists():
        return 0
    
    pattern = 'catalog_*.json'
    for root, dirs, files in os.walk(base_path):
        for file in files:
            if fnmatch.fnmatch(file, pattern):
                file_path = Path(root).joinpath(file)
                try:
                    os.remove(file_path)
                except:
                    pass
        break

    # Define the download URL
    url = f"https://cdn.bd2.pmang.cloud/ServerData/Android/{quality}/{version}/catalog_alpha.json"
    
    # Download the file
    print(" Downloading new catalog...")
    response = requests.get(url)

    if response.status_code == 200:
        with open(filename, 'wb') as file:
            file.write(response.content)
        return 1
    else:
        return -1

# Helper functions to simulate SerializationUtilities
class SerializationUtilities:
    class ObjectType:
        AsciiString = 0
        UnicodeString = 1
        UInt16 = 2
        UInt32 = 3
        Int32 = 4
        Hash128 = 5
        Type = 6
        JsonObject = 7
        
def read_int32_from_byte_array(byte_array, offset):
    return struct.unpack_from('<i', byte_array, offset)[0]

def read_object_from_byte_array(key_data, data_index):
    try:
        object_type = key_data[data_index]
        data_index += 1
        
        if object_type == SerializationUtilities.ObjectType.AsciiString:
            num = struct.unpack_from('<i', key_data, data_index)[0]
            data_index += 4
            return key_data[data_index:data_index + num].decode('ascii')
        
        elif object_type == SerializationUtilities.ObjectType.UnicodeString:
            num = struct.unpack_from('<i', key_data, data_index)[0]
            data_index += 4
            return key_data[data_index:data_index + num].decode('utf-16')
            
        elif object_type == SerializationUtilities.ObjectType.JsonObject:
            num3 = key_data[data_index]
            data_index += 1
            json_assembly = key_data[data_index:data_index + num3].decode('ascii')
            data_index += num3
            num4 = key_data[data_index]
            data_index += 1
            json_type = key_data[data_index:data_index + num4].decode('ascii')
            data_index += num4
            num5 = struct.unpack_from('<i', key_data, data_index)[0]
            data_index += 4
            json_data = key_data[data_index:data_index + num5].decode('utf-16')
            return json.loads(json_data)
        
        else:
            return object_type

    except Exception as ex:
        print(f"Exception: {ex}")

    return None

def parse_catalog(version, required_assets):
    catalog = base_path.joinpath(f"catalog_{version}.json")

    required_assets = {asset.lower() for asset in (required_assets or [])}
    asset_hits = {}
    bundle_names = set()
    resolved_paths = set()

    with open(catalog, 'r', encoding='utf-8') as file:
        data = json.load(file)

    # Decode base64 data for bucket data
    bucket_array = base64.b64decode(data['m_BucketDataString'])
    num_buckets = struct.unpack_from('<i', bucket_array, 0)[0]  # Read number of buckets
    dependency_map = [None] * num_buckets
    data_offsets = []
    index = 4

    for i in range(num_buckets):
        data_offset = read_int32_from_byte_array(bucket_array, index)
        index += 4
        num_entries = read_int32_from_byte_array(bucket_array, index)
        index += 4
        entries = []
        for _ in range(num_entries):
            entry_index = read_int32_from_byte_array(bucket_array, index)
            index += 4
            entries.append(entry_index)
        data_offsets.append(data_offset)
        dependency_map[i] = entries

    key_array = base64.b64decode(data['m_KeyDataString'])
    keys = [None] * len(data_offsets)
    for idx, offset in enumerate(data_offsets):
        keys[idx] = read_object_from_byte_array(key_array, offset)

    extra_data = base64.b64decode(data['m_ExtraDataString'])
    entry_data = base64.b64decode(data['m_EntryDataString'])
    number_of_entries = read_int32_from_byte_array(entry_data, 0)
    index = 4

    bundles = {}
    entries = []

    for m in range(number_of_entries):
        #num1 = read_int32_from_byte_array(entry_data, index)
        index += 4
        num2 = read_int32_from_byte_array(entry_data, index)
        index += 4
        num3 = read_int32_from_byte_array(entry_data, index)
        index += 4
        #num4 = read_int32_from_byte_array(entry_data, index)
        index += 4
        num5 = read_int32_from_byte_array(entry_data, index)
        index += 4
        num6 = read_int32_from_byte_array(entry_data, index)
        index += 4
        #num7 = read_int32_from_byte_array(entry_data, index)
        index += 4

        entries.append({ 'dependency_index': num3 })

        raw_key = keys[num6] if num6 < len(keys) else ''
        key = str(raw_key).lower()

        if num2 == 1 and num5 >= 0:
            temp_data = read_object_from_byte_array(extra_data, num5)
            bundle_path = asset_bundles_folder_path.joinpath(temp_data['m_BundleName'], temp_data['m_Hash'], '__data')
            bundles[m] = {
                'bundle_name': temp_data['m_BundleName'],
                'path': str(bundle_path),
                'bundle_key': str(raw_key),
                'size': temp_data['m_BundleSize']
            }
            continue

        if not key or not required_assets:
            continue

        asset_name = Path(key).name.lower()
        if asset_name in required_assets and asset_name not in asset_hits:
            asset_hits[asset_name] = (m, str(raw_key))

    def resolve_bundle_info(entry_index):
        if entry_index in bundles:
            return bundles[entry_index]
        if entry_index < 0 or entry_index >= len(entries):
            return None
        dep_idx = entries[entry_index]['dependency_index']
        if dep_idx < 0 or dep_idx >= len(dependency_map):
            return None
        deps = dependency_map[dep_idx] or []
        for dep_entry in deps:
            info = bundles.get(dep_entry)
            if info:
                return info
        return None

    for asset_name in sorted(required_assets):
        entry_info = asset_hits.get(asset_name)
        if not entry_info:
            continue

        entry_index, bundle_key = entry_info
        info = resolve_bundle_info(entry_index)
        if not info:
            continue

        bundle_names.add(info['bundle_name'])
        bundle_path = Path(info['path'])

        if not bundle_path.exists():
            download_name = info['bundle_key'] or bundle_path.name
            download_name = re.sub(r'_[a-f0-9]+(?=\.bundle)', '', download_name)
            url = f"https://cdn.bd2.pmang.cloud/ServerData/Android/{quality}/{version}/{download_name}"
            response = requests.get(url, stream=True)

            bundle_path.parent.mkdir(parents=True, exist_ok=True)
            with open(bundle_path, 'wb') as file:
                with tqdm(desc=f" Downloading {download_name}...", ascii=" ##########", bar_format="{desc} {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt}", colour="green", total=info['size']) as pbar:
                    for chunk in response.iter_content(chunk_size=1024 * 64):
                        if chunk:
                            file.write(chunk)
                            pbar.update(len(chunk))
            print("")

        if bundle_path not in resolved_paths:
            skeleton_data_bundles_paths.append(str(bundle_path))
            resolved_paths.add(bundle_path)

    return list(bundle_names)

def clean_old_bundles(old_bundle_names, new_bundle_names):
    print(" Cleaning old bundles...")
    for old_name in old_bundle_names:
        if not old_name in new_bundle_names:
            shutil.rmtree(asset_bundles_folder_path.joinpath(old_name))

def parse_asset_bundles():
    asset_bundles = {}
    
    file_count = len(skeleton_data_bundles_paths)
    with tqdm(desc=" Parsing bundles...", ascii=" ##########", bar_format="{desc} {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt}", colour="green", total=file_count) as pbar:
        for file_path in skeleton_data_bundles_paths:
            pbar.update(1)
            # Load asset bundle and filter for TextAsset or Texture2D
            env = UnityPy.load(file_path)
            bundle_content = {
                path: obj for path, obj in env.container.items()
                if obj.type.name in ["TextAsset", "Texture2D"] and hasattr(obj, 'path_id')
            }
            # Only add the bundle to the dictionary if it has valid assets
            if bundle_content:
                asset_bundles[file_path] = bundle_content
                
    return asset_bundles

def parse_mods():
    rename_rules = {
        ".skel": ".skel.bytes",
        ".skel.txt": ".skel.bytes",
        ".atlas": ".atlas.txt"
    }
    
    mods_files = {}
    duplicate_files = {}
    json_to_skel_files = {}
    
    file_count = sum(len(files) for _, _, files in os.walk(mods_folder_path))
    with tqdm(desc=" Parsing mods...", ascii=" ##########", bar_format="{desc} {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt}", colour="green", total=file_count) as pbar:
        for root, _, files in os.walk(mods_folder_path):
            for file in files:
                pbar.update(1)
                if file.endswith(".modfile"):
                    continue
                
                mod_root = Path(root)
                mod_file_path = mod_root.joinpath(file)
                
                if file.endswith(".json"):
                    skel_file = file.replace(".json", ".skel")
                    if not mod_root.joinpath(skel_file).exists():
                        if not mod_root.joinpath(skel_file + ".bytes").exists():
                            json_to_skel_files[mod_file_path] = file
                    continue

                # Check if the file's extension matches any renaming rule
                for ext, new_ext in rename_rules.items():
                    if file.endswith(ext):
                        new_file = file.replace(ext, new_ext)
                        file = new_file  # Update the file variable to the new name
                        break
                
                mod_file_path = str(mod_file_path)
                if file in mods_files:
                    if mods_files[file] not in duplicate_files:
                        duplicate_files[mods_files[file]] = []
                    duplicate_files[mods_files[file]].append(mod_file_path)
                
                mods_files[file] = mod_file_path

    return mods_files, duplicate_files, json_to_skel_files

def associate_mods_with_bundles(asset_bundles, mods_files):
    matched_mods = {}
    with tqdm(desc=" Preparing files associations...", ascii=" ##########", bar_format="{desc} {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt}", colour="green", total=len(mods_files)) as pbar:
        for bundle_path, bundle_content in asset_bundles.items():
            for mod_filename, mod_filepath in mods_files.items():
                if mod_filename in bundle_content:
                    pbar.update(1)
                    if bundle_path not in matched_mods:
                        matched_mods[bundle_path] = []
                    matched_mods[bundle_path].append((mod_filename, mod_filepath))
                
        matched_files = {mod_filename for mods in matched_mods.values() for mod_filename, _ in mods}
        unmatched_mods = {mod_filename: mod_filepath for mod_filename, mod_filepath in mods_files.items() if mod_filename not in matched_files}
        pbar.update(len(unmatched_mods))

    if unmatched_mods:
        print()
        print(" \033[33mCould not find matching asset bundles for the following files:\033[0m")
        for mod_filename, mod_filepath in unmatched_mods.items():
            print(f" - {mod_filepath}")
        print()
        
    return matched_mods

def clear_modded_folder():
    """Delete all files in the modded folder."""
    if asset_bundles_modded_folder_path.exists():
        shutil.rmtree(asset_bundles_modded_folder_path)  # Delete the folder and all its contents
    asset_bundles_modded_folder_path.mkdir(parents=True)  # Recreate the folder

def astc_encode_image(file_path, block):
    file_path = Path(file_path)
    output_path = astc_encode_tmp_folder_path.joinpath(file_path.name.replace(file_path.suffix, ".astc"))

    if not astc_encode_tmp_folder_path.exists():
        astc_encode_tmp_folder_path.mkdir(parents=True, exist_ok=True)

    args = [str(astc_encoder_binary_path), "-cs", str(file_path), str(output_path), block, "-medium", "-yflip", "-decode_unorm8", "-silent"]
    try:
        subprocess.check_call(args)

        with open(output_path, "rb") as f:
            data = f.read()[16:]

        os.remove(output_path)
        return data
    except Exception as e:
        print()
        print(" \033[31mAn error occured compressing the textures, make sure the path to the png files doesn't contain non-ASCII characters such as Chinese characters\033[0m")
        print()
        raise(e)

# Function to replace files in the asset bundle with the corresponding mod files
def replace_files_in_bundles(matched_mods, quality):
    clear_modded_folder()
    
    errors = []
    file_count = sum(len(mods) for _, mods in matched_mods.items())
    with tqdm(desc=" Repacking assets...", ascii=" ##########", bar_format="{desc} {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt}", colour="green", total=file_count) as pbar:
        for bundle_path, mods in matched_mods.items():
            env = UnityPy.load(bundle_path)
            for mod_filename, mod_filepath in mods:
                for path, obj in env.container.items():
                    if path == mod_filename:
                        try:
                            data = obj.read()
                            # Replace content with the mod file
                            if obj.type.name == "Texture2D":
                                try:
                                    new_texture = Image.open(mod_filepath).convert('RGBA')  # Open image only once
                                except IOError as e:
                                    errors.append(f" Failed to open image file {mod_filepath}")
                                    continue  # Skip if there's an issue with the image

                                astc_data = astc_encode_image(mod_filepath, "4x4" if quality == "HD" else "8x8")
                                data.m_Width = new_texture.width
                                data.m_Height = new_texture.height
                                data.m_TextureFormat = UnityPy.enums.TextureFormat.ASTC_RGB_4x4 if quality == "HD" else UnityPy.enums.TextureFormat.ASTC_RGB_8x8
                                data.image_data = astc_data
                                data.m_CompleteImageSize = len(astc_data)
                                data.m_MipCount = 1
                                data.m_StreamData.offset = 0
                                data.m_StreamData.size = 0
                                data.m_StreamData.path = ""
                            elif obj.type.name == "TextAsset":
                                with open(mod_filepath, "rb") as f:
                                    data.m_Script = f.read().decode(errors="surrogateescape")
                            else:
                                continue
                            pbar.update(1)
                            data.save()
                        except Exception as e:
                            pbar.close()
                            print()
                            print(f" \033[31mAn error occured with {mod_filepath}\033[0m")
                            print()
                            raise(e)
                    
            # Get the relative path from the original bundles folder
            relative_path = Path(bundle_path).relative_to(asset_bundles_folder_path)
            # Create the full path in the modded folder
            modded_bundle_path = asset_bundles_modded_folder_path.joinpath(relative_path)
            # Ensure the directories exist
            modded_folder = modded_bundle_path.parent
            modded_folder.mkdir(parents=True, exist_ok=True)
            
            with open(modded_bundle_path, "wb") as f:
                f.write(env.file.save(packer="lz4"))
            
    return errors

def convert_json_mods(skip_blurb=False):
    if not skip_blurb:
        clear()
        print()
        print(" Repacking bundles can only be done with .skel files, not .json files.")
        print(" You should check with the original modder if they provide .skel files for those mods.")
        print(" However, ReDustX comes with a JSON to SKEL Converter (this tool, still in beta).")
        print()

        convert_choices = [
            {
                "type": "list",
                "name": "conversion",
                "message": "Would you like to convert those files - if any - with ReDustX?\n  -------------  ",
                "pointer": "  >",
                "qmark": " ",
                "choices": ["Convert", "Cancel"],
            }
        ]
        answer = prompt(convert_choices)
        conversion = answer["conversion"] or 'Cancel'
        if conversion == "Cancel":
            return
        
    if not mods_folder_path.exists():
        mods_folder_path.mkdir(parents=True, exist_ok=True)
        
    json_to_skel_files = {}
    
    file_count = sum(len(files) for _, _, files in os.walk(mods_folder_path))
    for root, _, files in os.walk(mods_folder_path):
        for file in files:
            if not file.endswith(".json"):
                continue
            
            mod_root = Path(root)
            mod_file_path = mod_root.joinpath(file)
            skel_file = file.replace(".json", ".skel")
            if not mod_root.joinpath(skel_file).exists():
                if not mod_root.joinpath(skel_file + ".bytes").exists():
                    json_to_skel_files[str(mod_file_path)] = file
                    
    if not json_to_skel_files:
        print()
        print(" \033[33mNothing to convert!\033[0m")
        print()
        input(" Press any key...")
        return
        
    errored_files = {}
    file_count = len(json_to_skel_files)
    with tqdm(desc=" Converting mods...", ascii=" ##########", bar_format="{desc} {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt}", colour="green", total=file_count) as pbar:
        for file, name in json_to_skel_files.items():
            pbar.desc = f" Converting {name}"
            
            input_json = file
            output_skel = file.replace(".json", ".skel")

            # Convert the file
            try:
                json_to_skel(input_json, output_skel)
            except Exception as e:
                try:
                    os.remove(output_skel)
                except:
                    pass
                errored_files[input_json] = e
                
            pbar.update(1)
            
    if errored_files:
        print()
        print(" \033[31mA fatal error occured while trying to convert the following files:\033[0m")
        for file, error in errored_files.items():
            print(f" - {file}")
            print(f"   {error}")
            print()
        print(" Please open an issue in the repository or contact me via Discord about this.")
        print()
        input(" Press any key...")
        
    print()
    print(" \033[33mConversion is complete!")
    print(" You can now restart the repacking process.\033[0m")
    print()
    print(" Note that this tool is still experimental and might not work for every mod.")
    print(" If you have issues with some automatically converted mods, open an issue in the repository or contact me via Discord.")
    print()
    input(" Press any key...")
    return

def show_help():
    clear()
    print(" How to use this tool")
    print()
    print(" 1. Put all the mods you want to use inside the mods/ folder of ReDustX.")
    print("    Note that only mods with .skel files are supported. Those with .json files will not work.")
    print()
    print(" 2. Select Repack in the main menu of ReDustX and wait until the process is over.")
    print()
    print(" 3. Copy all the content from the bundles_modded/ folder of ReDustX to your phone:")
    print("    Android/data/com.neowizgames.game.browndust2/files/UnityCache/Shared/")
    print()
    print(" 4. Enjoy.")
    print()
    print(" Note: if it still doesn't work open an issue in the repository or contact Jelosus1 in Discord")
    print()
    input(" Press any key...")

def show_about():
    clear()
    print(" About ReDustX")
    print()
    print(" ReDustX is an Asset Bundle Repacker for the game Brown Dust 2.")
    print(" It automates the replacement of modded textures and animation files into the game's asset bundles.")
    print(" This is useful to repack modded characters and cutscenes to be used on the Android version of the game.")
    print()
    print(" This tool was written by Jelosus1, the creator of BrownDust2 L2D Viewer website and Synae, the creator of BrownDustX.")
    print(" B2D L2D Viewer is a website where you can check and download character animations.")
    print(" BDX is a non-intrusive PC Client Mod for Brown Dust 2 which respects the game's fairness.")
    print()
    print(" You can support Jelosus1 and their work on Ko-Fi: https://www.ko-fi.com/jelosus1")
    print(" You can support Synae and their work on Ko-Fi: https://www.ko-fi.com/synae")
    print()
    input(" Press any key...")

def clear():
    # Check the platform
    if os.name == 'nt':  # For Windows
        os.system('cls')
    else:  # For macOS and Linux (os.name is 'posix')
        os.system('clear')
        

if __name__ == "__main__":
    while True:
        clear()
        
        print()
        print(f" ReDustX v{RDXVersion}")
        print(f" Created by Jelosus1 (https://www.ko-fi.com/jelosus1) and Synae (https://www.ko-fi.com/synae)")
        print()
        print(" THIS SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND.")
        print()
        print()
        
        # Create the prompt for user input
        questions = [
            {
                "type": "list",
                "name": "action",
                "message": "RDX Main Menu\n  -------------  ",
                "pointer": "  >",
                "qmark": " ",
                "choices": ["Repack", "Json2Skel Converter (Beta)", "Help", "About", "Ko-Fi", "Github Repository", "Exit"],
            }
        ]
    
        # Prompt the user with the choices
        answer = prompt(questions)
      
        # Handle the user's choice
        if answer["action"] == "Json2Skel Converter (Beta)":
            convert_json_mods()
            continue
        if answer["action"] == "Help":
            show_help()
            continue
        elif answer["action"] == "About":
            show_about()
            continue
        elif answer["action"] == "Ko-Fi":
            webbrowser.open("https://www.ko-fi.com/synae")
            webbrowser.open("https://www.ko-fi.com/jelosus1")
            continue
        elif answer["action"] == "Github Repository":
            webbrowser.open("https://github.com/Jelosus2/ReDustX")
            continue
        elif answer["action"] == "Exit":
            clear()
            print(" Cleaning up...")
            clear()
            sys.exit(0)
            
        print()
        
        # Check necessary folders
        if not asset_bundles_folder_path.exists():
            asset_bundles_folder_path.mkdir(parents=True, exist_ok=True)
        if not mods_folder_path.exists():
            mods_folder_path.mkdir(parents=True, exist_ok=True)        
    
        mods_files, duplicate_files, json_to_skel_files = parse_mods()
    
        if not mods_files:
            print()
            print(" \033[31mNo mods files were found. Aborting.\033[0m")
            print()
            input(" Press any key...")
            continue
        
        if duplicate_files:
            print()
            print(" \033[31mFound the following duplicated mods:\033[0m")
            for file1, files in duplicate_files.items():
                print(f" - {file1}")
                for file in files:
                    print(f" - {file}")
                print()
            print(" Please remove duplicates before retrying.")
            input(" Press any key...")
            continue
        
        if json_to_skel_files:
            print()
            print(" \033[33mFound the following .json mods:\033[0m")
            for file in json_to_skel_files.keys():
                print(f" - {file}")
            print()
            print(" Repacking bundles can only be done with .skel files, not .json files.")
            print(" You should check with the original modder if they provide .skel files for those mods.")
            print(" However, ReDustX comes with a JSON to SKEL Converter (beta version).")
            print()

            convert_choices = [
                {
                    "type": "list",
                    "name": "conversion",
                    "message": "Would you like to automatically convert those files with ReDustX?\n  -------------  ",
                    "pointer": "  >",
                    "qmark": " ",
                    "choices": ["Yes", "No", "Cancel"],
                }
            ]
            answer = prompt(convert_choices)
            conversion = answer["conversion"] or 'Cancel'
        
            if conversion == "Yes":
                convert_json_mods(skip_blurb=True)
                continue
            elif conversion == "Cancel":
                continue
        
        print()
        # User input regarding Quality
        quality_choices = [
            {
                "type": "list",
                "name": "quality",
                "message": "Which quality do you play with on your phone?\n  -------------  ",
                "pointer": "  >",
                "qmark": " ",
                "choices": ["FHD", "HD", "SD", "Cancel"],
            }
        ]
        answer = prompt(quality_choices)
        quality = "HD" if answer["quality"] == "FHD" else answer["quality"] or 'HD'
        
        if quality == "Cancel":
            continue
        
        print()
        cdn_version = get_cdn_version(quality)
        
        # -1: Error, 0: Catalog already exists, 1: New Catalog
        catalog = download_catalog(quality, cdn_version)

        if catalog == -1:
            print()
            print(" \033[31mCould not download bundles catalog. Aborting.\033[0m")
            print()
            input(" Press any key...")
            continue
        
        skeleton_data_bundles_paths = []
        old_bundle_names = [f.name for f in asset_bundles_folder_path.iterdir() if f.is_dir()]
        new_bundle_names = parse_catalog(cdn_version, mods_files.keys())

        if catalog == 1:
            clean_old_bundles(old_bundle_names, new_bundle_names)

        asset_bundles = parse_asset_bundles()
    
        if not asset_bundles:
            print()
            print(" \033[31mNo mods files were found. Aborting.\033[0m")
            print()
            input(" Press any key...")
            continue

        matched_mods = associate_mods_with_bundles(asset_bundles, mods_files)
    
        if not matched_mods:
            print()
            print(" \033[31mCouldn't find any corresponding asset bundle to repack the mods into. Aborting.\033[0m")
            print()
            input(" Press any key...")
            continue

        errors = replace_files_in_bundles(matched_mods, quality)
        
        if errors:
            print()
            print(" \033[31mSome files could not be repacked:\033[0m")
            for error in errors:
                print(f"- {error}")
            print()
            print(" Please try repacking again after removing the faulty mods.")
            print()
            input(" Press any key...")
            continue
        
        print()
        print(" \033[33mRepack complete.")
        print(" You can now copy the modded bundles to your game's installation on your phone:")
        print("    Android/data/com.neowizgames.game.browndust2/files/UnityCache/Shared/\033[0m")
        print()
        input(" Press any key...")
