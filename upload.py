import requests
from dotenv import load_dotenv
import os
from tqdm import tqdm
from time import sleep
import json
import imagehash
from PIL import Image
from supabase import create_client, Client


load_dotenv()
access_token = os.getenv('IMGUR_ACCESS_TOKEN')
test_album_hash = os.getenv('IMGUR_TEST_ALBUM_HASH')

def init_supabase() -> Client:
    url: str = os.getenv("SUPABASE_URL")
    key: str = os.getenv("SUPABASE_KEY")
    return create_client(url, key)

def update_access_token():
    url = "https://api.imgur.com/oauth2/token"

    payload={'refresh_token': os.getenv('IMGUR_REFRESH_TOKEN'),
    'client_id': os.getenv('IMGUR_CLIENT_ID'),
    'client_secret': os.getenv('IMGUR_CLIENT_SECRET'),
    'grant_type': 'refresh_token'}
    files=[

    ]
    headers = {}

    response = requests.request("POST", url, headers=headers, data=payload, files=files)
    access_token = response.json()['access_token']
    print(access_token)
    #update the access token in the .env file
    with open('.env', 'r') as file:
        lines = file.readlines()
    with open('.env', 'w') as file:
        for line in lines:
            if line.startswith('IMGUR_ACCESS_TOKEN'):
                file.write(f'IMGUR_ACCESS_TOKEN = {access_token}\n')
                print('IMGUR_ACCESS_TOKEN updated successfully.')
            else:
                file.write(line)

def album_create(accessToken,album_title,album_description):
    url = "https://api.imgur.com/3/album"

    payload={
    'title': album_title,
    'description': album_description
    }
    files=[

    ]
    headers = {
    'Authorization': 'Bearer ' + accessToken
    }

    response = requests.request("POST", url, headers=headers, data=payload, files=files)

    print(response.text)

def image_upload(accessToken, image_path, title, description):
    url = "https://api.imgur.com/3/image"

    payload={'type': 'image',
    'title': title,
    'description': description}
    image_name = os.path.basename(image_path)
    files=[
    ('image',(image_name,open(image_path,'rb'),'image'))
    ]
    headers = {
    'Authorization': 'Bearer ' + accessToken
    }

    response = requests.request("POST", url, headers=headers, data=payload, files=files)

    #print(response.text)
    print(response.json()['data']['id'], response.json()['data']['deletehash'], response.json()['data']['link'])
    response_data = response.json()['data']
    return response_data['id'], response_data['deletehash'], response_data['link']

def album_add_image(accessToken,album_hash,image_id):
    url = "https://api.imgur.com/3/album/" + album_hash

    payload={'ids': image_id}
    files=[]
    headers = {
    'Authorization': 'Bearer ' + accessToken
    }

    response = requests.request("PUT", url, headers=headers, data=payload, files=files)
    #print(response.text)
    if response.status_code == 200:
        print("Success: image added to album.")
    else:
        print("Error: The operation failed.")
    
def upload_and_update_image(image_path, access_token, album_hash):
    image_name = os.path.basename(image_path)
    print(f"Uploading {image_name}...")
    image_id, deletehash, link = image_upload(access_token, image_path, image_name, "used for fracture detection app")
    sleep(1)
    print(f"Adding {image_name} to album...")
    album_add_image(access_token, album_hash, image_id)
    print(f"{image_name} added to album {album_hash} successfully.\n")

def get_image_hash(image_path):
    return str(imagehash.average_hash(Image.open(image_path)))

#update_access_token()
#album_create(os.getenv('IMGUR_ACCESS_TOKEN'),'Test Album','This is a test album')
#image_upload(os.getenv('IMGUR_ACCESS_TOKEN'),'./test.png','Test Image','This is a test image')
#album_add_image(access_token,test_album_hash,'Kq1DwuK')

folder_path = './images'
image_files = [f for f in os.listdir(folder_path) if f.endswith(('.png', '.jpg', '.jpeg'))]

# Initialize Supabase client
supabase = init_supabase()

for filename in tqdm(image_files, desc="Uploading images", unit="file"):
    image_path = os.path.join(folder_path, filename)
    image_hash = get_image_hash(image_path)

    dupplicated = False
    if os.path.exists('log.json'):
        with open('log.json', 'r') as log_file:
            try:
                existing_log_data = json.load(log_file)
                for entry in existing_log_data:
                    if entry['image_hash'] == image_hash:
                        print(f"Skipping {filename}, already exists in log.")
                        dupplicated = True
                        break
            except:
                pass

    if dupplicated:
        continue
    # if not dupplicated -> upload the image
    image_id, deletehash, link = image_upload(access_token, image_path, filename, "used for fracture detection app")
    
    # Update Supabase table
    supabase.table("images").insert({
        "imgur_id": image_id,
        "filename": filename,
        "image_hash": image_hash,
        "imgur_deletehash": deletehash,
        "imgur_url": link,
    }).execute()

    log_data = []
    log_data.append({
        'imgur_id': image_id,
        'filename': filename,
        'image_hash': image_hash,
        'imgur_deletehash': deletehash,
        'imgur_url': link
    })
    if os.path.exists('log.json'):
        with open('log.json', 'r') as log_file:
            try:
                existing_log_data = json.load(log_file)
            except:
                existing_log_data = []
    else:
        existing_log_data = []

    existing_log_data.extend(log_data)

    with open('log.json', 'w') as log_file:
        json.dump(existing_log_data, log_file, indent=4)


#upload_and_update_image(image_path, access_token, test_album_hash)



