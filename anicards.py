import configparser
import io
import json
import os
import random
from io import BytesIO
from os.path import exists

import PySimpleGUI as sg
import requests
from PIL import Image


version = "v1.0.2"

workingFolder = os.getcwd() + "\\"
animeImagesFolder = workingFolder + "AnimeImages\\"
characterImagesFolder = workingFolder + "CharacterImages\\"
dataFolder = workingFolder + "Data\\"
uiFolder = workingFolder + "UI\\"
url = 'https://graphql.anilist.co'

if not exists(animeImagesFolder):
    os.mkdir(animeImagesFolder)
if not exists(characterImagesFolder):
    os.mkdir(characterImagesFolder)
if not exists(dataFolder):
    os.mkdir(dataFolder)

layoutPopup = [
    [sg.Text("Anilist Username"), sg.InputText()],
    [sg.Button('Ok'), sg.Button('Cancel')]
]

usernameQuery = '{{User(name: "{}"){{id}}}}'

config = configparser.ConfigParser()
if exists(workingFolder + "config.ini"):
    config.read(workingFolder + "config.ini")
else:
    config['DEFAULT'] = {
        'Hide Duplicates': 'yes'
    }
    config['User'] = {
        'AnilistID': '0'
    }

    windowPopup = sg.Window("Anicards " + version, layoutPopup)
    while True:
        event, values = windowPopup.read()
        if event == sg.WIN_CLOSED or event == 'Cancel':
            break
        response = requests.post(url, json={'query': usernameQuery.format(values[0])})
        responseDict = json.loads(response.text)
        config["User"]["AnilistID"] = str(responseDict["data"]["User"]["id"])
        windowPopup.close()

    with open(workingFolder + "config.ini", 'w') as configfile:
        config.write(configfile)

if exists(dataFolder + "exclusions.txt"):
    with open(dataFolder + "exclusions.txt", 'r') as file:
        animeExclusions = [line.rstrip('\n') for line in file]
else:
    open(dataFolder + "exclusions.txt", 'w')
    animeExclusions = []

if exists(dataFolder + "packs.json"):
    packsFile = open(dataFolder + "packs.json")
    packsOpened = json.load(packsFile)
    packsFile.close()
else:
    packsOpened = {}

if exists(dataFolder + "collection.json"):
    collectionFile = open(dataFolder + "collection.json")
    cardCollection = json.load(collectionFile)
    collectionFile.close()
else:
    cardCollection = {}

if exists(dataFolder + "rarecollection.json"):
    rarecollectionFile = open(dataFolder + "rarecollection.json")
    rarecardCollection = json.load(rarecollectionFile)
    rarecollectionFile.close()
else:
    rarecardCollection = {}

mainCharactersList = []
supportCharactersList = []

goldOverlay = Image.open(uiFolder + "rainbow.png")
silverOverlay = Image.open(uiFolder + "silver.png")
maskImage = Image.open(uiFolder + "mask.png").convert("RGBA")

class Anime:
    def __init__(self, id, englishTitle, romajiTitle, format, imageURL, progress):
        self.id = str(id)
        self.englishTitle = englishTitle
        self.romajiTitle = romajiTitle
        self.format = format
        self.image = imageURL
        self.progress = progress

    def __str__(self):
        return self.getTitle()

    def __lt__(self, obj):
        return ((self.getTitle().lower()) < (obj.getTitle().lower()))
  
    def __gt__(self, obj):
        return ((self.getTitle().lower()) > (obj.getTitle().lower()))
  
    def __le__(self, obj):
        return ((self.getTitle().lower()) <= (obj.getTitle().lower()))
  
    def __ge__(self, obj):
        return ((self.getTitle().lower()) >= (obj.getTitle().lower()))
  
    def __eq__(self, obj):
        return (self.getTitle().lower() == obj.getTitle().lower())

    def getTitle(self):
        if (self.englishTitle is not None):
            return self.englishTitle
        else:
            return self.romajiTitle

    def pullImage(self):
        if not exists(animeImagesFolder + str(self.id) + ".png"):
            response = requests.get(self.image)
            image = Image.open(BytesIO(response.content))
            image = image.resize((248, 354))
            image.save(animeImagesFolder + str(self.id) + ".png")

    def shouldExclude(self):
        return self.format == "MOVIE" or self.progress == 0 or self.id in animeExclusions

class Character:
    def __init__(self, id, first, last, imageURL):
        self.id = str(id)
        self.first = first
        self.last = last
        self.image = imageURL

    def __str__(self):
        return self.getName()

    def __eq__(self, obj):
        return (self.id == obj.id)

    def getName(self):
        if self.first is not None and self.last is not None:
            return self.first + " " + self.last
        elif self.first is not None:
            return self.first
        elif self.last is not None:
            return self.last
        else:
            return "unnamed character"
    
    def shouldExclude(self):
        return "default.jpg" in self.image

    def getRole(self):
        if isMainCharacter(self.id):
            return "MAIN"
        else:
            return "SUPPORTING"

    def getImagePath(self):
        if isMainCharacter(self.id):
            return characterImagesFolder + self.id + "M.png"
        else:
            return characterImagesFolder + self.id + "S.png"

    def pullImage(self):
        if not exists(self.getImagePath()):
            response = requests.get(self.image)
            image = Image.open(BytesIO(response.content)).convert("RGBA")
            image = image.resize((315, 450))
            if self.getRole() == "MAIN":
                image.paste(goldOverlay, (0,0), mask = maskImage)
            else:
                image.paste(silverOverlay, (0,0), mask = maskImage)
            image.save(self.getImagePath())

def fetchCharacterInfo(id):
    x = 1
    while True:
        characterRepsonse = requests.post(url, json={'query': characterQuery.format(id, x)})
        charDict = json.loads(characterRepsonse.text)
        charactersList = charDict['data']['Media']['characters']["edges"]
        
        windowLoadingBar = createLoadingWindow(len(charactersList)-1, "Downloading page {0} of characters {1}/{2}".format(x, 1, len(charactersList)-1))
        progressBar = windowLoadingBar['progress']
        windowLoadingBar.read(timeout=0)
        prog = 0

        if len(charactersList) == 0:
            windowLoadingBar.close()
            break
        else:
            for character in charactersList:
                c = Character(character["node"]["id"], character["node"]["name"]["first"], character["node"]["name"]["last"], character["node"]["image"]["large"])
                if c.shouldExclude():
                    continue
                if character["role"] == "MAIN":
                    mainCharactersList.append(c)
                else:
                    supportCharactersList.append(c)
                c.pullImage()
                prog += 1
                progressBar.update(prog)
                windowLoadingBar["-ProgressText-"].update("Downloading page {0} of characters: {1}/{2}".format(x, prog + 1, len(charactersList)-1))
        windowLoadingBar.close()
        x += 1

def pullCharacter():
    if random.randint(1, 5) == 5:
        return random.choice(mainCharactersList)
    else:
        return random.choice(supportCharactersList)

def isMainCharacter(characterID):
    for c in mainCharactersList:
        if c.id == characterID:
            return True
    return False

def getImagePathForCharacter(characterID):
        if isMainCharacter(characterID):
            return characterImagesFolder + characterID + "M.png"
        else:
            return characterImagesFolder + characterID + "S.png"

def addPullToCollection(animeID, characterID):
    if animeID in cardCollection:
        if characterID in cardCollection[animeID]:
            cardCollection[animeID][characterID] += 1
        else:
            cardCollection[animeID][characterID] = 1
    else:
        cardCollection[animeID] = {characterID : 1}

def addPullToRareCollection(animeID, characterID):
    if animeID in rarecardCollection:
        if characterID in rarecardCollection[animeID]:
            rarecardCollection[animeID][characterID] += 1
        else:
            rarecardCollection[animeID][characterID] = 1
    else:
        rarecardCollection[animeID] = {characterID : 1}

def sortAnimeLists():
    global animeHasPacksList
    global animeNoPacksList
    animeHasPacksList = []
    animeNoPacksList = []
    for item in allAnimeDict:
        anime = Anime(item["media"]["id"], item["media"]["title"]["english"], item["media"]["title"]["romaji"], item["media"]["format"], item["media"]["coverImage"]["extraLarge"], item["progress"])
        if anime.shouldExclude():
            continue
        if anime.id not in packsOpened:
            packsOpened[anime.id] = 0
        if anime.id in packsOpened and packsOpened[anime.id] < anime.progress:
            animeHasPacksList.append(anime)
        else:
            animeNoPacksList.append(anime)
    animeHasPacksList.sort()
    animeNoPacksList.sort()

def resizeAsBytesIO(imageToResize, x, y):
    imageToResize.resize((x, y), Image.ANTIALIAS)
    bio = io.BytesIO()
    imageToResize.save(bio, format='PNG')
    del imageToResize
    return bio.getvalue()

def loadImages(animeID, startCardIndex):
    global totalCards

    if animeID not in rarecardCollection:
            rarecardCollection[animeID] = {}
    if animeID not in cardCollection:
        cardCollection[animeID] = {}

    allCardsIDs = []

    loadBlankImages()

    if values['-HIDE DUPES-']:
        totalCards = len(rarecardCollection[animeID]) + len(cardCollection[animeID])

        for card in rarecardCollection[animeID].keys():
            allCardsIDs.append(card)

        for card in cardCollection[animeID].keys():
            allCardsIDs.append(card)

        for x in range(min(4, totalCards - startCardIndex)):
            window["-CARD {}-".format(x)].update(getImagePathForCharacter(allCardsIDs[startCardIndex + x]))
    else:
        totalCards = packsOpened[animeID]

        for card in rarecardCollection[animeID].keys():
            for x in range(rarecardCollection[animeID][card]):
                allCardsIDs.append(card)

        for card in cardCollection[animeID].keys():
            for x in range(cardCollection[animeID][card]):
                allCardsIDs.append(card)

        for x in range(min(4, totalCards - startCardIndex)):
            window["-CARD {}-".format(x)].update(getImagePathForCharacter(allCardsIDs[startCardIndex + x]))

def loadBlankImages():
    for x in range(4):
        window["-CARD {}-".format(x)].update(uiFolder + "default.png")

def writeDataToFiles():
    packsFile = open(dataFolder + "packs.json", "w")
    packsJson = json.dumps(packsOpened)
    packsFile.write(packsJson)
    packsFile.close()

    collectionFile = open(dataFolder + "collection.json", "w")
    collectionJson = json.dumps(cardCollection)
    collectionFile.write(collectionJson)
    collectionFile.close()

    rarecollectionFile = open(dataFolder + "rarecollection.json", "w")
    rarecollectionJson = json.dumps(rarecardCollection)
    rarecollectionFile.write(rarecollectionJson)
    rarecollectionFile.close()

    with open(workingFolder + "config.ini", 'w') as configfile:
        config.write(configfile)

query = ''' query {{
  MediaListCollection(userId: {0}, type: ANIME, sort: MEDIA_TITLE_ENGLISH) {{
    lists {{
      entries {{
        media {{
          id
          title {{
            english
            romaji
          }}
          format
          coverImage {{
            extraLarge
          }}
        }}
        progress
      }}
    }}
  }}
}}'''

characterQuery = '''query {{
  Media (id:{0}){{
    characters(page:{1}, sort:ROLE) {{
      edges {{
        node {{
          id
          name {{
            first
            last
          }}
          image {{
            large
          }}
        }}
        role
      }}
    }}
  }}
}}'''

response = requests.post(url, json={'query': query.format(config["User"]["AnilistID"])})
responseDict = json.loads(response.text)

allAnimeDict = []

for item in responseDict['data']['MediaListCollection']['lists']:
    allAnimeDict += item["entries"]

animeHasPacksList = []
animeNoPacksList = []

sortAnimeLists()

def createLoadingWindow(maxValue, labelText):
    layoutLoadingBar = [[sg.Text(labelText, key="-ProgressText-")],
        [sg.ProgressBar(maxValue, orientation='h', size=(20, 20), key='progress')],]
    return sg.Window("AniCards " + version, layoutLoadingBar)

windowLoadingBar = createLoadingWindow(len(animeHasPacksList) + len(animeNoPacksList), "Downloading images from Anilist ")
progressBar = windowLoadingBar['progress']
event, values = windowLoadingBar.read(timeout=0)

prog = 0

for anime in animeHasPacksList:
    anime.pullImage()
    prog += 1
    progressBar.update(prog)
    windowLoadingBar["-ProgressText-"].update("Downloading images from Anilist: {0}/{1}".format(prog, len(animeHasPacksList) + len(animeNoPacksList)))

for anime in animeNoPacksList:
    anime.pullImage()
    prog += 1
    progressBar.update(prog)
    windowLoadingBar["-ProgressText-"].update("Downloading images from Anilist: {0}/{1}".format(prog, len(animeHasPacksList) + len(animeNoPacksList)))

windowLoadingBar.close()

anime_list_column = [
    [
        sg.Listbox(values=animeHasPacksList + animeNoPacksList, enable_events=True, size=(55, 27), key="-FILE LIST-")
    ],
]

pack_opening_column = [
    [sg.Text("Select a pack from the list on the left", size=(30, 2), key="-TITLE-")],
    [sg.Image(uiFolder + "nopack.png", key="-ANIMEIMAGE-")],
    [sg.Button('Open Pack', size=(30,2), key="-OPEN PACK-")],
    [sg.Text(size=(30, 1), key="-PACKS LEFT-")]
]

card_pulled_column = [
    [sg.Image(uiFolder + "default.png", key="-PULLED CARD-")],
    [sg.Text(size=(30, 1), key="-CHARACTER NAME-")]
]

card_viewer = [
    [
        sg.Image(uiFolder + "default.png", key="-CARD 0-"),
        sg.Image(uiFolder + "default.png", key="-CARD 1-"),
        sg.Image(uiFolder + "default.png", key="-CARD 2-"),
        sg.Image(uiFolder + "default.png", key="-CARD 3-")
    ]
]

settings = [
    [
        sg.Checkbox("Hide duplicates", default=config["DEFAULT"]["Hide Duplicates"] == 'True', key="-HIDE DUPES-", enable_events=True)
    ]
]

# ----- Full layout -----
layout = [
    [
        sg.Column(anime_list_column),
        sg.Column(pack_opening_column),
        sg.Column(card_pulled_column, justification='c'),
        sg.Column(settings)
    ],
    [
        sg.Button("<", size=(3,3)),
        sg.Column(card_viewer),
        sg.Button(">", size=(3,3))
    ]
]

window = sg.Window("AniCards " + version, layout)

animeSelected = None
startCardIndex = 0
totalCards = 0

# Run the Event Loop
while True:
    event, values = window.read()
    if event == "Exit" or event == sg.WIN_CLOSED:
        break

    if event == "-FILE LIST-": 
        try:
            mainCharactersList.clear()
            supportCharactersList.clear()
            animeSelected = values["-FILE LIST-"][0]
            filename = animeImagesFolder + str(animeSelected.id) + ".png"

            fetchCharacterInfo(animeSelected.id)

            window["-TITLE-"].update(animeSelected)
            window["-ANIMEIMAGE-"].update(filename=filename)
            window["-PACKS LEFT-"].update("Unopened Packs: " + str(animeSelected.progress - packsOpened[animeSelected.id]))
            window["-PULLED CARD-"].update(filename=uiFolder + "default.png")
            window["-CHARACTER NAME-"].update("")

            startCardIndex = 0
            loadBlankImages()
            loadImages(animeSelected.id, startCardIndex)
            writeDataToFiles()

        except:
            pass

    elif event == "-OPEN PACK-":
        if packsOpened[animeSelected.id] != animeSelected.progress:
            packsOpened[animeSelected.id] += 1
            if random.randint(1, 10) == 10 or len(supportCharactersList) == 0:
                rarity = "Rare: "
                characterPulled = random.choice(mainCharactersList)
                addPullToRareCollection(animeSelected.id, characterPulled.id)
            else:
                rarity = "Common: "
                characterPulled = random.choice(supportCharactersList)
                addPullToCollection(animeSelected.id, characterPulled.id)
            loadImages(animeSelected.id, startCardIndex)
            window["-PACKS LEFT-"].update("Unopened Packs: " + str(animeSelected.progress - packsOpened[animeSelected.id]))
            window["-PULLED CARD-"].update(filename=getImagePathForCharacter(characterPulled.id))
            window["-CHARACTER NAME-"].update(rarity + characterPulled.getName())
            if animeSelected in animeHasPacksList and packsOpened[animeSelected.id] == animeSelected.progress:
                sortAnimeLists()
                window["-FILE LIST-"].update(values=animeHasPacksList + animeNoPacksList)
    
    elif event == "<":
        if startCardIndex != 0 and animeSelected is not None:
            startCardIndex -= 1
            loadImages(animeSelected.id, startCardIndex)
    
    elif event == ">":
        if startCardIndex + 4 < totalCards and animeSelected is not None:
            startCardIndex += 1
            loadImages(animeSelected.id, startCardIndex)

    elif event == "-HIDE DUPES-":
        config["DEFAULT"]["Hide Duplicates"] = str(values['-HIDE DUPES-'])
        if animeSelected is not None:
            startCardIndex = 0
            loadImages(animeSelected.id, startCardIndex)

window.close()

writeDataToFiles()
