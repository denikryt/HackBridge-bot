import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

TOKEN = os.environ.get("token")
MONGODB_URI = os.environ.get("mongodb_uri")
DB_NAME = "HackBridge"
AVATAR_COLLECTION_NAME = os.environ.get("avatar_collection_name")
DEFAULT_AVATAR = ":monkey_face:"

AVATAR_EMOJIS = [
    ":monkey_face:", ":monkey:", ":gorilla:", ":orangutan:", ":dog:", ":guide_dog:", ":service_dog:", 
    ":poodle:", ":wolf:", ":raccoon:", ":cat:", ":black_cat:", ":lion:", ":tiger:", 
    ":leopard:", ":horse:", ":unicorn:", ":zebra:", ":deer:", ":bison:", ":cow:", ":ox:", ":water_buffalo:", 
    ":pig:", ":boar:", ":pig_nose:", ":ram:", ":goat:", ":camel:", 
    ":llama:", ":giraffe:", ":elephant:", ":mammoth:", ":rhinoceros:", ":hippopotamus:", ":mouse:", ":rat:", 
    ":hamster:", ":rabbit:", ":chipmunk:", ":beaver:", ":hedgehog:", ":bat:", ":bear:", ":polar_bear:", 
    ":koala:", ":sloth:", ":otter:", ":skunk:", ":kangaroo:", ":badger:", ":turkey:", ":chicken:", 
    ":rooster:", ":hatching_chick:", ":baby_chick:", ":bird:", ":penguin:", ":dove:", ":eagle:", 
    ":duck:", ":swan:", ":owl:", ":flamingo:", ":peacock:", ":parrot:", ":whale:", ":dolphin:", ":seal:", 
    ":fish:", ":tropical_fish:", ":blowfish:", ":shark:", ":octopus:", ":snail:", ":butterfly:", ":bug:", 
    ":ant:", ":beetle:", ":lady_beetle:", ":cricket:", ":cockroach:", ":spider:", ":spider_web:", ":scorpion:", 
    ":mosquito:", ":fly:", ":worm:", ":microbe:", ":turtle:", ":snake:", ":lizard:", ":crocodile:"
]