import os
import subprocess
import json
import requests
import configparser

# Read config file
config = configparser.ConfigParser()
config.read('config.ini', encoding='utf-8')

def run_command(command):

    # return stdout, if return code is not 0, raise exception conteins stderr and return code
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(result.stderr, result.returncode)
    return result.stdout



# iter over all sections
for section in config.sections():
    # skip default section
    if section == 'DEFAULT':
        continue

    print(f'Processing section: {section}')
    section_path = os.path.join(config[section]['store_path'], config[section]['folder_name'].format(section))
    os.makedirs(section_path, exist_ok=True)


    # format date YYYY-MM-DD to YYYYMMDD
    date_str = config[section]['date'].replace('-', '')
    try:
        print('requiring json data')
        json_str = run_command(f"yt-dlp -J https://www.youtube.com/{config[section]['channel_id']} --dateafter {date_str}")
        json_data = json.loads(json_str)
    except Exception as e:
        print(f"Error: {e}")
        continue
    
    # find the newest video release date in entries[].upload_date in YYYYMMDD format
    orig_date = int(date_str)

    # date_int: latest video release date (from config), str store to date_str
    date_int = int(date_str)

    # first level entries may contains many channel entries
    entries = []
    for entry in json_data['entries']:
        # if entry is a channel, append all entries to entries
        if 'entries' in entry:
            entries.extend(entry['entries'])
        else:
            entries.append(entry)

    for entry in entries:
        entry_date = entry['upload_date']
        # find the newest video release date
        if int(entry_date) > date_int:
            date_int = int(entry['upload_date'])
            date_str = entry['upload_date']
        
        if int(entry_date) > orig_date:
            print(entry['title'])
            if entry['title'].find(config[section]['title_contains']) < 0:
                print('title not match filter, skip')
                continue
            # download thumbnail in entry.thumbnails[N].url where N is entry.thumbnails.perfernece is 0
            thumbnail_url = next(filter(lambda x: x['preference'] == 0, entry['thumbnails']))['url']
            res = requests.get(thumbnail_url)


            metadata_path = os.path.join(section_path, config[section]['metadata_folder'])
            os.makedirs(metadata_path, exist_ok=True)
            with open(os.path.join(metadata_path, f"{entry_date}_{entry['id']}{os.path.splitext(thumbnail_url)[1]}"), 'wb') as f:
                f.write(res.content)
            
            # download metadata
            os.system(f"yt-dlp -j \"https://youtu.be/{entry['id']}\" > \"{metadata_path}\\{entry_date}_{entry['id']}.json\"")

            # download video
            os.system(f"yt-dlp -o \"{section_path}\\{entry_date}_{entry['title']}[{entry['id']}].%(ext)s\" \"https://youtu.be/{entry['id']}\"")

    # update config file
    config[section]['date'] = date_str[:4] + '-' + date_str[4:6] + '-' + date_str[6:]
    with open('config.ini', 'w', encoding='utf-8') as configfile:
        config.write(configfile)