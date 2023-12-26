import os
from ruamel.yaml import YAML

def saveToFile(filePath: str, obj: object) -> bool:
    # try:
        folder = os.path.dirname(filePath)
        os.makedirs(folder, exist_ok=True)

        with open(filePath, 'w') as file:
            YAML().dump(obj.__dict__, file)
            return True
    # except Exception as e:
    #     print(e)
    #     return False
    
def loadFromFile(path: str) -> object:
    try:
        with open(path, 'r') as file:
            return YAML().load(file)
    except Exception as e:
        print(e)
        return False
