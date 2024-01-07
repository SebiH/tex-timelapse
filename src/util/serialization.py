import os
from ruamel.yaml import YAML

def saveToFile(filePath: str, obj: object) -> bool:
        folder = os.path.dirname(filePath)
        os.makedirs(folder, exist_ok=True)

        with open(filePath, 'w') as file:
            YAML().dump(obj.__dict__, file)
    
def loadFromFile(path: str) -> object:
    with open(path, 'r') as file:
        return YAML().load(file)
