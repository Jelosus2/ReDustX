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
from google.protobuf import text_format
from google.protobuf.message import DecodeError
from InquirerPy import prompt
from PIL import Image
from tqdm import tqdm
from json_to_skel import json_to_skel

import maintenance_info_pb2

RDXVersion = '1.0.0'
UnityPy.config.FALLBACK_VERSION_WARNED = True
UnityPy.config.FALLBACK_UNITY_VERSION = '2022.3.22f1'

def get_base_path():
    if getattr(sys, 'frozen', False):  # If running as a bundled exe
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(__file__)  # If running as a .py script


# Folders and paths
mods_folder = "mods/"
mods_folder_path = os.path.join(get_base_path(), mods_folder)

asset_bundles_folder = "bundles/"
asset_bundles_folder_path = os.path.join(get_base_path(), asset_bundles_folder)

asset_bundles_modded_folder = "bundles_modded/"
asset_bundles_modded_folder_path = os.path.join(get_base_path(), asset_bundles_modded_folder)

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
    filename = os.path.join(get_base_path(), f"catalog_{version}.json")

    # Check if the file exists in the current directory
    if os.path.isfile(filename):
        return 0
    
    pattern = 'catalog_*.json'
    for root, dirs, files in os.walk(get_base_path()):
        for file in files:
            if fnmatch.fnmatch(file, pattern):
                file_path = os.path.join(root, file)
                try:
                    os.remove(file_path)
                except:
                    pass
        break

    # Define the download URL
    url = f"https://cdn.bd2.pmang.cloud/ServerData/Android/{quality}/{version}/catalog_alpha.json"
    
    # Download the file
    print(f" Downloading new catalog...")
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
            
        return None

    except Exception as ex:
        print(f"Exception: {ex}")

    return None

def parse_catalog(version, new_catalog):
    # Define the filename based on the quality
    catalog = os.path.join(get_base_path(), f"catalog_{version}.json")

    with open(catalog, 'r', encoding='utf-8') as file:
        data = json.load(file)
        
    # Decode base64 data for bucket data
    bucket_array = base64.b64decode(data['m_BucketDataString'])
    num_buckets = struct.unpack_from('<i', bucket_array, 0)[0]  # Read number of buckets
    data_offsets = []
    index = 4

    # Extract dataOffset for each bucket (skip entries)
    for i in range(num_buckets):
        data_offset = read_int32_from_byte_array(bucket_array, index)  # Read dataOffset
        index += 4  # Skip past the dataOffset
        num_entries = read_int32_from_byte_array(bucket_array, index)  # Read the number of entries
        index += 4 + num_entries * 4  # Skip past the entries (each entry is 4 bytes)
    
        # Store the dataOffset
        data_offsets.append(data_offset)

    # Decode key data (which is used to populate array6)
    key_array = base64.b64decode(data['m_KeyDataString'])
    keys = [None] * len(data_offsets)

    # Extract objects using dataOffset from key data
    for idx, offset in enumerate(data_offsets):
        o = read_object_from_byte_array(key_array, offset)
        keys[idx] = o

    extra_data = base64.b64decode(data['m_ExtraDataString']);
    entry_data = base64.b64decode(data['m_EntryDataString']);
    number_of_entries = read_int32_from_byte_array(entry_data, 0);
    index = 4
    for m in range(number_of_entries):
        #num1 = read_int32_from_byte_array(entry_data, index);
        index += 4;
        #num2 = read_int32_from_byte_array(entry_data, index);
        index += 4;
        #num3 = read_int32_from_byte_array(entry_data, index);
        index += 4;
        #num4 = read_int32_from_byte_array(entry_data, index);
        index += 4;
        num5 = read_int32_from_byte_array(entry_data, index);
        index += 4;
        num6 = read_int32_from_byte_array(entry_data, index);
        index += 4;
        #num7 = read_int32_from_byte_array(entry_data, index);
        index += 4;

        key = str(keys[num6])
        if not key.startswith("common-skeleton-data") or not key.endswith("bundle"):
            continue
        
        # {"m_Hash":"eeedd74194fc5b7e39a5141f6c9a208c","m_Crc":0,"m_Timeout":30,"m_ChunkedTransfer":false,"m_RedirectLimit":5,"m_RetryCount":5,"m_BundleName":"ecdfc15b23580667fa12c0d51a05db61","m_AssetLoadMode":0,"m_BundleSize":51931760,"m_UseCrcForCachedBundles":true,"m_UseUWRForLocalBundles":false,"m_ClearOtherCachedVersionsWhenLoaded":true}
        data = read_object_from_byte_array(extra_data, num5)
        bundle_path = os.path.join(asset_bundles_folder_path, data['m_BundleName'], data['m_Hash'], '__data')
        skeleton_data_bundles_paths.append(bundle_path)
        
        if os.path.isfile(bundle_path):
            if catalog == 0:
                continue
            if os.path.getsize(bundle_path) == data['m_BundleSize']:
                continue
        
        # Download the bundle
        bundle_name = re.sub(r'_[a-f0-9]+(?=\.bundle)', '', key)    
        url = f"https://cdn.bd2.pmang.cloud/ServerData/Android/{quality}/{version}/{bundle_name}"    
        response = requests.get(url, stream=True)    
        
        os.makedirs(os.path.dirname(bundle_path), exist_ok=True)
        with open(bundle_path, 'wb') as file:
            # Create a progress bar
            with tqdm(desc=f" Downloading {bundle_name}...", ascii=" ##########", bar_format="{desc} {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt}", colour="green", total=data['m_BundleSize']) as pbar:
                # Write the file in chunks
                for chunk in response.iter_content(chunk_size=1024 * 64):
                    if chunk:  # filter out keep-alive new chunks
                        file.write(chunk)
                        # Update the progress bar with the size of the chunk
                        pbar.update(len(chunk))
        print("")
            
            
    

def parse_asset_bundles():
    asset_bundles = {}
    all_files = []
    
    #file_count = sum(len(files) for _, _, files in os.walk(asset_bundles_folder_path))
    file_count = len(skeleton_data_bundles_paths)
    with tqdm(desc=" Parsing bundles...", ascii=" ##########", bar_format="{desc} {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt}", colour="green", total=file_count) as pbar:
        #for root, _, files in os.walk(asset_bundles_folder_path):
            #for file in files:
        for file_path in skeleton_data_bundles_paths:
            pbar.update(1)
            #file_path = os.path.join(root, file)
            #if file_path.endswith("__data"):
            # Load asset bundle and filter for TextAsset or Texture2D
            env = UnityPy.load(file_path)
            bundle_content = {
                path: obj for path, obj in env.container.items()
                if obj.type.name in ["TextAsset", "Texture2D"] and hasattr(obj, 'path')
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
                
                mod_file_path = os.path.join(root, file)
                
                if file.endswith(".json"):
                    skel_file = file.replace(".json", ".skel")
                    if not os.path.isfile(os.path.join(root, skel_file)):
                        if not os.path.isfile(os.path.join(root, skel_file + ".bytes")):
                            json_to_skel_files[mod_file_path] = file
                    continue

                # Check if the file's extension matches any renaming rule
                for ext, new_ext in rename_rules.items():
                    if file.endswith(ext):
                        # old_file_path = os.path.join(root, file)
                        new_file = file.replace(ext, new_ext)
                        # new_file_path = os.path.join(root, new_file)
                        # if os.path.exists(new_file_path):
                        #     os.remove(new_file_path)
                        # os.rename(old_file_path, new_file_path)
                        # print(f" \033[33mRenamed {old_file_path} to {new_file_path}\033[0m")
                        file = new_file  # Update the file variable to the new name
                        # mod_file_path = os.path.join(root, file)
                        break
                
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
        print(f" \033[33mCould not find matching asset bundles for the following files:\033[0m")
        for mod_filename, mod_filepath in unmatched_mods.items():
            print(f" - {mod_filepath}")
        print()
        
    return matched_mods


def clear_modded_folder():
    """Delete all files in the modded folder."""
    if os.path.exists(asset_bundles_modded_folder_path):
        shutil.rmtree(asset_bundles_modded_folder_path)  # Delete the folder and all its contents
    os.makedirs(asset_bundles_modded_folder_path)  # Recreate the folder


# Function to replace files in the asset bundle with the corresponding mod files
def replace_files_in_bundles(matched_mods):
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
                                    new_texture = Image.open(mod_filepath).convert(mode='RGBA')  # Open image only once
                                except IOError as e:
                                    errors.append(f" Failed to open image file {mod_filepath}")
                                    continue  # Skip if there's an issue with the image

                                data.m_Width = new_texture.width
                                data.m_Height = new_texture.height

                                # argb_bytes = new_texture.tobytes("raw", "RGBA")
                                # data.image_data = argb_bytes
                                data.set_image(new_texture, UnityPy.enums.TextureFormat.RGBA32)
                                data.m_TextureSettings.m_FilterMode = 1
                            elif obj.type.name == "TextAsset":
                                with open(mod_filepath, "rb") as f:
                                    data.script = f.read()
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
        relative_path = os.path.relpath(bundle_path, asset_bundles_folder_path)
        # Create the full path in the modded folder
        modded_bundle_path = os.path.join(get_base_path(), asset_bundles_modded_folder, relative_path)
        # Ensure the directories exist
        modded_folder = os.path.dirname(modded_bundle_path)
        os.makedirs(modded_folder, exist_ok=True)
        
        with open(modded_bundle_path, "wb") as f:
            f.write(env.file.save("original"))
            
    return errors


def convert_json_mods(skip_blurb=False):
    if not skip_blurb:
        clear()
        print()
        print(" Repacking bundles can only be done with .skel files, not .json files.")
        print(" You should check with the original modder if they provide .skel files for those mods.")
        print(" However, ReDustX comes with a JSON to SKEL Converter (this tool, still in beta).")
        print()
        # User input regarding Quality
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
        
    if not os.path.exists(mods_folder_path):
        os.makedirs(mods_folder_path, exist_ok=True)
        
    json_to_skel_files = {}
    
    file_count = sum(len(files) for _, _, files in os.walk(mods_folder_path))
    for root, _, files in os.walk(mods_folder_path):
        for file in files:
            if not file.endswith(".json"):
                continue
            
            mod_file_path = os.path.join(root, file)
            skel_file = file.replace(".json", ".skel")
            if not os.path.isfile(os.path.join(root, skel_file)):
                if not os.path.isfile(os.path.join(root, skel_file + ".bytes")):
                    json_to_skel_files[mod_file_path] = file
                    
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
        print(f" \033[31mA fatal error occured while trying to convert the following files:\033[0m")
        for file, error in errored_files.items():
            print(f" - {file}")
            print(f"   {error}")
            print()
        print(f" Please send a bug report on Discord about this.")
        print()
        input(" Press any key...")
        
    print()
    print(" \033[33mConversion is complete!")
    print(" You can now restart the repacking process.\033[0m")
    print()
    print(" Note that this tool is still experimental and might not work for every mod.")
    print(" If you have issues with some automatically converted mods, send a bug report on Discord.")
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
    input(" Press any key...")
        

def show_about():
    clear()
    print(" About ReDustX")
    print()
    print(" ReDustX is an Asset Bundle Repacker for the game Brown Dust 2.")
    print(" It automates the replacement of modded textures and animation files into the game's asset bundles.")
    print(" This is useful to repack modded characters and cutscenes to be used on the Android version of the game.")
    print()
    print(" This tool was written by Synae, the creator of BrownDustX.")
    print(" BDX is a non-intrusive PC Client Mod for Brown Dust 2 which respects the game's fairness.")
    print()
    print(" You can support Synae and their work on Ko-Fi: https://www.ko-fi.com/synae")
    print(" You can also join the Discord server for BrownDustX and ReDustX: https://discord.gg/wNMuw2uFVW")
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
        print(f" Created by Synae (https://www.ko-fi.com/synae)")
        print()
        print(f" THIS SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND.")
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
                "choices": ["Repack", "Json2Skel Converter (Beta)", "Help", "About", "Ko-Fi", "Discord", "Exit"],
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
            continue
        elif answer["action"] == "Discord":
            webbrowser.open("https://discord.gg/wNMuw2uFVW")
            continue
        elif answer["action"] == "Exit":
            clear()
            print(" Cleaning up...")
            clear()
            sys.exit(0)
            
        print()
        
        # Check necessary folders
        if not os.path.exists(asset_bundles_folder_path):
            os.makedirs(asset_bundles_folder_path, exist_ok=True)
        if not os.path.exists(mods_folder_path):
            os.makedirs(mods_folder_path, exist_ok=True)
            
    
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
            # User input regarding Quality
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
                "choices": ["HD", "SD", "Cancel"],
            }
        ]
        answer = prompt(quality_choices)
        quality = answer["quality"] or 'HD'
        
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
        parse_catalog(cdn_version, catalog)
        


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

        errors = replace_files_in_bundles(matched_mods)
        
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