# ███████  ██████  ██████  ███    ███ ██████   █████  ██████
# ██      ██    ██ ██   ██ ████  ████ ██   ██ ██   ██ ██   ██
# █████   ██    ██ ██████  ██ ████ ██ ██████  ███████ ██████
# ██      ██    ██ ██   ██ ██  ██  ██ ██   ██ ██   ██ ██   ██
# ██       ██████  ██   ██ ██      ██ ██████  ██   ██ ██   ██


'''
    Formbar: An interactive classroom management tool focused on lesson pacing
        and formative assessment. Formbar excels in a Computer Science class
        environment, but provides tools to any class with web-enabled devices
        with a network connection to the Formbar host for each student.

        Formbar was designed for Raspberry Pi 4, but can run without physical
        add-ons on a Windows PC.
'''


#  ██████  ██████  ███    ██ ███████ ██  ██████  ██    ██ ██████   █████  ████████ ██  ██████  ███    ██
# ██      ██    ██ ████   ██ ██      ██ ██       ██    ██ ██   ██ ██   ██    ██    ██ ██    ██ ████   ██
# ██      ██    ██ ██ ██  ██ █████   ██ ██   ███ ██    ██ ██████  ███████    ██    ██ ██    ██ ██ ██  ██
# ██      ██    ██ ██  ██ ██ ██      ██ ██    ██ ██    ██ ██   ██ ██   ██    ██    ██ ██    ██ ██  ██ ██
#  ██████  ██████  ██   ████ ██      ██  ██████   ██████  ██   ██ ██   ██    ██    ██  ██████  ██   ████


from config import *

#Permission levels are as follows:
# 0 - teacher
# 1 - mod
# 2 - student
# 3 - anyone
# 4 - banned

NEWACCOUNTPERMISSIONS = 3

#Importing external modules
from flask import Flask, redirect, url_for, request, render_template
from werkzeug.utils import secure_filename
from websocket_server import WebsocketServer
from cryptography.fernet import Fernet
import pandas, json, csv
import random, sys, os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame
import time, math
import threading
import logging
import traceback
import sqlite3
if ONRPi:
    import board, neopixel

#Importing customs modules
from modules import letters
from modules import sfx
from modules import bgm
from modules.colors import colors, hex2dec
from modules import lessons
from modules import sessions
from key import key
if ONRPi:
    from modules import ir

#Set the websocket port for chat and live actions
WSPORT=9001

# Change the built-in logging for flask
flasklog = logging.getLogger('werkzeug')
flasklog.setLevel(logging.ERROR)

#Display IP address to console for user connection
print("[info] " +'Running formbar server on:' + ip)


# ██       ██████   █████  ██████  ██ ███    ██  ██████
# ██      ██    ██ ██   ██ ██   ██ ██ ████   ██ ██
# ██      ██    ██ ███████ ██   ██ ██ ██ ██  ██ ██   ███
# ██      ██    ██ ██   ██ ██   ██ ██ ██  ██ ██ ██    ██
# ███████  ██████  ██   ██ ██████  ██ ██   ████  ██████


#Scan the sfx and bgm folders
sfx.updateFiles()
bgm.updateFiles()
#Start up pygame for sfx and bgm
pygame.init()

#Start the neopixel tracker
if ONRPi:
    #Create a list of neopixels if we are on an RPi
    pixels = neopixel.NeoPixel(board.D21, MAXPIX, brightness=1.0, auto_write=False)
else:
    #Create an empty list as long as our MAXPIX if not on RPi
    pixels = [(0,0,0)]*MAXPIX


#Start a new flask server for http service
app = Flask(__name__)

sD = sessions.Session(ip)

#Start encryption tools
cipher = Fernet(key)

# Dictionary words for hangman game
words = json.loads(open(os.path.dirname(os.path.abspath(__file__)) + "/data/words.json").read())

banList = []
helpList = {}
blockList = []
colorDict = {
        '14': (255, 255, 0),
        '15': (196, 150, 128),
        '16': (255, 96, 0),
        '56': (0, 192, 192),
        }



# ███████ ██    ██ ███    ██  ██████ ████████ ██  ██████  ███    ██ ███████
# ██      ██    ██ ████   ██ ██         ██    ██ ██    ██ ████   ██ ██
# █████   ██    ██ ██ ██  ██ ██         ██    ██ ██    ██ ██ ██  ██ ███████
# ██      ██    ██ ██  ██ ██ ██         ██    ██ ██    ██ ██  ██ ██      ██
# ██       ██████  ██   ████  ██████    ██    ██  ██████  ██   ████ ███████


'''
#For testing potential animation features
def aniTest():
    if not ONRPi:
        global pixels
    fillBar((0,0,0))
    for i in range(0, BARPIX - 40):
        pixRange = range(i+20, i + 40)
        pixRange2 = range(i, i + 20)
        for j, pix in enumerate(pixRange):
            pixels[pix] = blend(pixRange, j, colors['blue'], colors['red'])
        for j, pix in enumerate(pixRange2):
            pixels[pix] = blend(pixRange2, j, colors['green'], colors['blue'])
        if ONRPi:
            pixels.show()

@app.route('/anitest')
def endpoint_anitest():
    if len(threading.enumerate()) < 5:
        threading.Thread(target=aniTest, daemon=True).start()
        return 'testing...'
    else:
        return 'Too many threads'
'''

def dbug(message='Checkpoint Reached'):
    global DEBUG
    if DEBUG:
        print("[DEBUG] " + str(message))

def newStudent(remote, username, bot=False):
    global NEWACCOUNTPERMISSIONS
    if not remote in sD.studentDict:
        sD.studentDict[remote] = {
            'name': username,
            'thumb': '',
            'letter': '',
            'textRes': '',
            'perms': 3,
            'oldPerms': 3,
            'progress': [],
            'complete': False,
            'tttGames': [],
            'quizRes': [],
            'essayRes': '',
            'bot': bot,
            'help': False,
            'breakReq': False,
            'excluded': False,
            'preferredHomepage': None
        }
        #Track if the teacher is logged in
        teacher = False

        #Check each student so far to make sure that none of them have teacher perms
        for user in sD.studentDict:
            if sD.studentDict[user]['perms'] == 0:
                teacher = True

        #Login bots as guest
        if bot:
            print("[info] " +"Bot successful login. Made them a guest: " + username)
            sD.studentDict[remote]['perms'] = sD.settings['perms']['anyone']

        #Login as teacher if there is no teacher yet
        elif not teacher:
            print("[info] " +username + " logged in. Made them the teacher...")
            sD.studentDict[remote]['perms'] = sD.settings['perms']['admin']

        #Login other users as guests (students until database is installed)
        else:
            print("[info] " +username + " logged in.")
            sD.studentDict[remote]['perms'] = NEWACCOUNTPERMISSIONS

        #Overwrite permissions with those retrieved from database here
        #Open and connect to database
        db = sqlite3.connect(os.path.dirname(os.path.abspath(__file__)) + '/data/database.db')
        dbcmd = db.cursor()
        userFound = dbcmd.execute("SELECT * FROM users WHERE username=:uname", {"uname": username}).fetchall()
        db.close()
        for user in userFound:
            if username in user:
                if not teacher:
                    sD.studentDict[remote]['perms'] = sD.settings['perms']['admin']
                else:
                    sD.studentDict[remote]['perms'] = int(user[3])

        playSFX("sfx_up02")

def flushUsers():
    for user in list(sD.studentDict):
        if not sD.studentDict[user]['perms'] == sD.settings['perms']['admin']:
            del sD.studentDict[user]
    playSFX("sfx_splash01")

#Erases student(s) answer(s) by name and category
#Returns True if successful, and False if it failed
def refreshUsers(selectedStudent='', category=''):
    for student in sD.studentDict:
        if selectedStudent:
            student = selectedStudent
        if category:
            try:
                sD.studentDict[student][category] = ''
                return True
            except Exception as e:
                print("[error] " +e)
                return False
        else:
            sD.studentDict[student]['thumb'] = '',
            sD.studentDict[student]['letter'] = '',
            sD.studentDict[student]['progress'] = [],
            sD.studentDict[student]['complete'] = False,
            sD.studentDict[student]['quizRes'] = [],
            sD.studentDict[student]['essayRes'] = ''
            return True

def changeMode(newMode='', direction='next'):
    index = sD.settings['modes'].index(sD.settings['barmode'])
    if newMode in sD.settings['modes']:
        sD.settings['barmode'] = newMode
    elif newMode:
        return "[warning] " + 'Invalid mode.'
    else:
        if direction == 'next':
            index += 1
        elif direction == 'prev':
            index -= 1
        else:
            return "[warning] " + 'Invalid direction. Needs next or prev.'
        if index >= len(sD.settings['modes']):
            index = 0
        elif index < 0:
            index =len(sD.settings['modes']) - 1
        sD.settings['barmode'] = sD.settings['modes'][index]
    if sD.settings['barmode'] == 'tutd':
        tutdBar()
    elif sD.settings['barmode'] == 'abcd':
        abcdBar()
    elif sD.settings['barmode'] == 'text':
        textBar()
    elif sD.settings['barmode'] == 'essay' or sD.settings['barmode'] == 'quiz':
        completeBar()
    elif sD.settings['barmode'] == 'progress':
        if sD.lesson:
            percFill(sD.lesson.checkProg(stripUser('admin')))
    elif sD.settings['barmode'] == 'playtime':
        clearString()
        showString(sD.activePhrase)
    return 'Changed mode to ' + (newMode or direction) + '.'

#This function Allows you to choose and play whatever sound effect you want
def playSFX(sound):
    try:
        pygame.mixer.Sound(sfx.sound[sound]).play()
        return "Succesfully played: "
    except:
        return "Invalid format: "

def stopSFX():
    pygame.mixer.Sound.stop()

# This function allows you to choose wich background music you want
def startBGM(bgm_filename, volume=sD.bgm['volume']):
    sD.bgm['paused'] = True
    pygame.mixer.music.load(bgm.bgm[bgm_filename])
    pygame.mixer.music.set_volume(volume)
    pygame.mixer.music.play(loops=-1)
    playSFX("sfx_pickup01")

#This function stops BGM
def stopBGM():
    sD.bgm['paused'] = False
    pygame.mixer.music.stop()
    sD.bgm['nowplaying'] = ''
    playSFX("sfx_pickup01")

#This function stops BGM
def rewindBGM():
    pygame.mixer.music.rewind()
    playSFX("sfx_pickup01")

def playpauseBGM(state='none'):
    if pygame.mixer.music.get_busy():
        if type(state) is bool:
            sD.bgm['paused'] = state
        sD.bgm['paused'] = not sD.bgm['paused']
        if sD.bgm['paused']:
            pygame.mixer.music.pause()
        else:
            pygame.mixer.music.unpause()
    playSFX("sfx_pickup01")

def volBGM(value):
    sD.bgm['volume'] = pygame.mixer.music.get_volume()
    if value == 'up':
        sD.bgm['volume'] += 0.1
    elif value == 'down':
        sD.bgm['volume'] -= 0.1
    else:
        sD.bgm['volume'] = value
    if sD.bgm['volume'] > 1.0:
        sD.bgm['volume'] = 1.0
    if sD.bgm['volume'] < 0:
        sD.bgm['volume'] = 0.0
    pygame.mixer.music.set_volume(sD.bgm['volume'])
    playSFX("sfx_pickup01")

def str2bool(strng):
    strng.lower()
    if strng == 'true':
        return True
    elif strng == 'false':
        return False
    else:
        return strng

def fadein(irange, current, color):
    return [int(x * (current / len(irange))) for x in color]

def fadeout(irange, current, color):
    return [int(x * ((len(irange) - current) / len(irange))) for x in color]

def blend(irange, current, color1, color2):
    blendColor = fadein(irange, current, color2)
    for i, rgb in enumerate(blendColor):
        blendColor[i] += fadeout(irange, current, color1)[i]
    return blendColor

def addBlock():
    if not ONRPi:
        global pixels
    if blockList[-1][0] in colorDict:
        pixels[len(blockList)-1] = colorDict[blockList[-1][0]]
    else:
        pixels[len(blockList)-1] = colors['default']
    if ONRPi:
        pixels.show()

def fillBlocks():
    if not ONRPi:
        global pixels
    for i, block in enumerate(blockList):
        if block[0] in colorDict:
            pixels[i] = colorDict[block[0]]
        else:
            pixels[i] = colors['default']
    if ONRPi:
        pixels.show()

def percFill(amount, fillColor=colors['green'], emptyColor=colors['red']):
    if not ONRPi:
        global pixels
    if amount > 100 and amount < 0 and type(amount) is not int:
        raise TypeError("Out of range. Must be between 0 - 1 or 0 - 100.")
    else:
        pixRange = math.ceil(BARPIX * (amount * 0.01))
        for pix in range(0, BARPIX):
            if pix <= pixRange:
                pixels[pix] = fillColor
            else:
                pixels[pix] = emptyColor
        if ONRPi:
            pixels.show()
    if sD.settings['captions']:
        clearString()
        showString("PROG " + str(sD.lesson.checkProg(stripUser('admin'))))
    if ONRPi:
        pixels.show()

def fillBar(color=colors['default'], stop=BARPIX, start=0):
    if not ONRPi:
        global pixels
    #If you provide no args, the whole bar is made the default color
    #If you provide one arg, the whole bar will be that color
    #If you provide two args, the bar will be that color until the stop point
    #If you provide three args, pixels between the stop and start points will be that color
    for pix in range(start, stop):
        pixels[pix] = color

def repeatMode():
    if sD.settings['barmode'] == 'tutd':
        # Clear thumbs
        for student in sD.studentDict:
            sD.studentDict[student]['thumb'] = ''
        tutdBar()
    elif sD.settings['barmode'] == 'abcd':
        # Clear answers
        for student in sD.studentDict:
            sD.studentDict[student]['letter'] = ''
        abcdBar()
    elif sD.settings['barmode'] == 'text':
        # Clear bar
        for student in sD.studentDict:
            sD.studentDict[student]['textRes'] = ''
        textBar()
    elif sD.settings['barmode'] == 'essay' or sD.settings['barmode'] == 'quiz' :
        # Clear thumbs
        for student in sD.studentDict:
            sD.studentDict[student]['complete'] = ''
        completeBar()
    elif sD.settings['barmode'] == 'progress':
        for student in sD.studentDict:
            for task in sD.lesson.progList[step['Prompt']]['task']:
                sD.studentDict[student]['progress'].append(False)
        percFill(sD.lesson.checkProg(stripUser('admin')))
    elif sD.settings['barmode'] == 'playtime':
        sD.activePhrase = ''
        clearString()
        showString(sD.activePhrase)
    playSFX("sfx_success01")

#This function clears(default) the color from the formbar
def clearBar():
    if not ONRPi:
        global pixels
    #fill with default color to clear bar
    for pix in range(0, BARPIX):
        pixels[pix] = colors['default']

def clearString():
    if not ONRPi:
        global pixels
    for i in range(BARPIX, MAXPIX):
        pixels[i] = colors['bg']

def showString(toShow, startLocation=0, fg=colors['fg'], bg=colors['bg']):
    for i, letter in enumerate(toShow.lower()):
        printLetter(letter, (i * (8 * 6)) + ((startLocation * 48) + BARPIX), fg, bg)
    if ONRPi:
        pixels.show()

def printLetter(letter, startLocation, fg=colors['fg'], bg=colors['bg']):
    if not ONRPi:
        global pixels
    if (MAXPIX - startLocation) >= 48:
        if letter in letters.ASCIIdict:
            for i, pull_row in enumerate(letters.ASCIIdict[letter]):
                #temporary variable (keeps it from permanently flipping letter pixels)
                row = []
                for pix in pull_row:
                    row.append(pix)
                # If this is an even row, reverse direction
                if not i%2:
                    row.reverse()
                for j, pixel in enumerate(row):
                    pixPoint = startLocation + (i*8)
                    if pixel:
                        pixels[pixPoint + j] = fg
                    else:
                        pixels[pixPoint + j] = bg
                pixPoint = startLocation + (i + (8*5))
                for j in range(pixPoint, pixPoint + 4):
                    pixels[j] = bg

        else:
            print("[warning] " + "Warning! Letter ", letter, " not found.")
    else:
        print("[warning] " + "Warning! Not enough space for this letter!")

#Shows results of test when done with abcdBar
def abcdBar():
    if not ONRPi:
        global pixels
    results = [] # Create empty results list
    clearBar()
    #Go through IP list and see what each IP sent as a response
    for student in sD.studentDict:
        #if the survey answer is a valid a, b, c, or d:
        if sD.studentDict[student]['letter'] in ['a', 'b', 'c', 'd']:
            #add this result to the results list
            results.append(sD.studentDict[student]['letter'])
    #The number of results is how many have complete the survey
    complete = len(results)
    #calculate the chunk length for each student
    chunkLength = math.floor(BARPIX / sD.settings['numStudents'])
    #Sort the results by "alphabetical order"
    results.sort()
    #Loop through each result, and show the correct color
    for index, result in enumerate(results):
        #Calculate how long this chunk will be and where it starts
        pixRange = range((chunkLength * index), (chunkLength * index) + chunkLength)
        #Fill in that chunk with the correct color
        if result == 'a':
            answerColor = colors['red']
        elif result == 'b':
            answerColor = colors['blue']
        elif result == 'c':
            answerColor = colors['yellow']
        elif result == 'd':
            answerColor = colors['green']
        else:
            answerColor = colors['default']
        for i, pix in enumerate(pixRange):
            #If it's the first pixel of the chunk, make it a special color
            if i == 0:
                pixels[pix] = colors['student']
            else:
                if sD.settings['blind'] and complete != sD.settings['numStudents']:
                    pixels[pix] = fadein(pixRange, i, colors['blind'])
                else:
                    pixels[pix] = fadein(pixRange, i, answerColor)

    if sD.settings['captions']:
        clearString()
        showString("ABCD " + str(complete) + "/" + str(sD.settings['numStudents']))
    if ONRPi:
        pixels.show()

#it takes the students picked answer and puts the required color for that specific choice
def tutdBar():
    if not ONRPi:
        global pixels
    if sD.settings['autocount']:
        autoStudentCount()
    upFill = upCount = downFill = downCount = wiggleFill = wiggleCount = 0
    complete = 0
    for x in sD.studentDict:
        if sD.studentDict[x]['perms'] == sD.settings['perms']['student'] and sD.studentDict[x]['thumb']:
            if sD.studentDict[x]['thumb'] == 'up':
                upFill += 1
                upCount += 1
            elif sD.studentDict[x]['thumb'] == 'down':
                downFill += 1
                downCount += 1
            elif sD.studentDict[x]['thumb'] == 'wiggle':
                wiggleFill += 1
                wiggleCount += 1
            complete += 1
    for pix in range(0, BARPIX):
        pixels[pix] = colors['default']
    if sD.settings['showinc']:
        chunkLength = math.floor(BARPIX / sD.settings['numStudents'])
    else:
        chunkLength = math.floor(BARPIX / complete)
    for index, ip in enumerate(sD.studentDict):
        pixRange = range((chunkLength * index), (chunkLength * index) + chunkLength)
        if upFill > 0:
            for i, pix in enumerate(pixRange):
                if i == 0:
                    pixels[pix] = colors['student']
                else:
                    if sD.settings['blind'] and complete != sD.settings['numStudents']:
                        pixels[pix] = fadein(pixRange, i, colors['blind'])
                    else:
                        pixels[pix] = fadein(pixRange, i, colors['green'])
            upFill -= 1
        elif wiggleFill > 0:
            for i, pix in enumerate(pixRange):
                if i == 0:
                    pixels[pix] = colors['student']
                else:
                    if sD.settings['blind'] and complete != sD.settings['numStudents']:
                        pixels[pix] = fadein(pixRange, i, colors['blind'])
                    else:
                        pixels[pix] = fadein(pixRange, i, colors['cyan'])
            wiggleFill -= 1
        elif downFill > 0:
            for i, pix in enumerate(pixRange):
                if i == 0:
                    pixels[pix] = colors['student']
                else:
                    if sD.settings['blind'] and complete != sD.settings['numStudents']:
                        pixels[pix] = fadein(pixRange, i, colors['blind'])
                    else:
                        pixels[pix] = fadein(pixRange, i, colors['red'])
            downFill -= 1
    if sD.settings['captions']:
        clearString()
        showString("TUTD " + str(complete) + "/" + str(sD.settings['numStudents']))
        if ONRPi:
            pixels.show()
    if upCount >= sD.settings['numStudents']:
        if ONRPi:
            pixels.fill((0,0,0))
        else:
            pixels = [(0,0,0)] * MAXPIX
        playSFX("sfx_success01")
        for i, pix in enumerate(range(0, BARPIX)):
                pixels[pix] = blend(range(0, BARPIX), i, colors['blue'], colors['red'])
        if sD.settings['captions']:
            clearString()
            showString("MAX GAMER!", 0, colors['purple'])
    elif downCount >= sD.settings['numStudents']:
        playSFX("wompwomp")
    elif wiggleCount >= sD.settings['numStudents']:
        playSFX("bruh")
    #The Funny Number
    elif sD.settings['numStudents'] == 9 and complete == 6:
        playSFX("clicknice")
    elif complete:
        playSFX("sfx_blip01")
    if ONRPi:
        pixels.show()

#Show how many students have submitted text responses
def textBar():
    if not ONRPi:
        global pixels
    if sD.settings['autocount']:
        autoStudentCount()
    complete = fill = 0
    for x in sD.studentDict:
        if sD.studentDict[x]['perms'] == sD.settings['perms']['student'] and sD.studentDict[x]['textRes']:
            complete += 1
            fill += 1
    for pix in range(0, BARPIX):
        pixels[pix] = colors['default']
    if sD.settings['showinc']:
        chunkLength = math.floor(BARPIX / sD.settings['numStudents'])
    else:
        chunkLength = math.floor(BARPIX / complete)
    for index, ip in enumerate(sD.studentDict):
        pixRange = range((chunkLength * index), (chunkLength * index) + chunkLength)
        if fill > 0:
            for i, pix in enumerate(pixRange):
                if i == 0:
                    pixels[pix] = colors['student']
                else:
                    pixels[pix] = fadein(pixRange, i, colors['white'])
            fill -= 1
    if sD.settings['captions']:
        clearString()
        showString("TEXT " + str(complete) + "/" + str(sD.settings['numStudents']))
        if ONRPi:
            pixels.show()
    if complete >= sD.settings['numStudents']:
        if ONRPi:
            pixels.fill((0,0,0))
        else:
            pixels = [(0,0,0)] * MAXPIX
        playSFX("sfx_success01")
        for i, pix in enumerate(range(0, BARPIX)):
                pixels[pix] = blend(range(0, BARPIX), i, colors['blue'], colors['red'])
        if sD.settings['captions']:
            clearString()
            showString("MAX GAMER!", 0, colors['purple'])
    #The Funny Number
    elif sD.settings['numStudents'] == 9 and complete == 6:
        playSFX("clicknice")
    elif complete:
        playSFX("sfx_blip01")
    if ONRPi:
        pixels.show()

def countComplete():
    complete = 0
    for student in sD.studentDict:
        if sD.studentDict[student]['complete']:
            complete += 1
    return complete

def completeBar():
    complete = countComplete()
    if sD.settings['captions']:
        clearString()
        showString("DONE " + str(complete) + "/" + str(sD.settings['numStudents']))
    if ONRPi:
        pixels.show()

def autoStudentCount():
    sD.settings['numStudents'] = 0
    for user in sD.studentDict:
        if sD.studentDict[user]['perms'] == 2:
            sD.settings['numStudents'] += 1
    if sD.settings['numStudents'] == 0:
        sD.settings['numStudents'] = 1

def stripUser(perm, exclude=True):
    newList = {}
    for student in sD.studentDict:
        if sD.studentDict[student]['perms'] > sD.settings['perms'][perm]:
            if exclude and sD.studentDict[student]['perms'] < 4:
                newList[student] = sD.studentDict[student]
    return newList

def stripUserData(perm='', sList={}):
    newList = sList
    for student in sD.studentDict:
        newList[student] = {}
        newList[student]['name'] = sD.studentDict[student]['name']
        newList[student]['perms'] = sD.studentDict[student]['perms']
        newList[student]['complete'] = sD.studentDict[student]['complete']
    return newList

def chatUsers():
    newList = {}
    for student in sD.studentDict:
        if 'wsID' in sD.studentDict[student].keys():
            newList[student] = {}
            newList[student]['name'] = sD.studentDict[student]['name']
            newList[student]['perms'] = sD.studentDict[student]['perms']
            newList[student]['wsID'] = sD.studentDict[student]['wsID']
    return newList

def updateStep():
    step = sD.lesson.steps[sD.currentStep]
    if step['Type'] == 'Resource':
        sD.wawdLink = sD.lesson.links[int(step['Prompt'])]['URL']
    elif step['Type'] == 'TUTD':
        sD.settings['barmode'] = 'tutd'
        sD.activePrompt = step['Prompt']
    elif step['Type'] == 'Essay': ##
        sD.settings['barmode'] = 'essay'
        sD.activePrompt = step['Prompt']
    elif step['Type'] == 'survey':
        sD.settings['barmode'] = 'survey'
        sD.activeQuiz = sD.lesson.quizList[step['Prompt']]
        surveyIndex = int(sD.activeQuiz['name'].split(' ', 1))
        sD.activePrompt = sD.activeQuiz['questions'][surveyIndex]
    elif step['Type'] == 'Quiz':
        sD.activeQuiz = sD.lesson.quizList[step['Prompt']]
        sD.settings['barmode'] = 'quiz'
        sD.wawdLink = '/quiz'
    elif step['Type'] == 'Progress':
        sD.settings['barmode'] = 'progress'
        sD.activeProgress = sD.lesson.progList[step['Prompt']]
        for student in sD.studentDict:
            sD.studentDict[student]['progress'] = []
            for task in sD.activeProgress['task']:
                sD.studentDict[student]['progress'].append(False)
        sD.wawdLink = '/progress'
    changeMode(sD.settings['barmode'])


# ███████ ███    ██ ██████  ██████   ██████  ██ ███    ██ ████████ ███████
# ██      ████   ██ ██   ██ ██   ██ ██    ██ ██ ████   ██    ██    ██
# █████   ██ ██  ██ ██   ██ ██████  ██    ██ ██ ██ ██  ██    ██    ███████
# ██      ██  ██ ██ ██   ██ ██      ██    ██ ██ ██  ██ ██    ██         ██
# ███████ ██   ████ ██████  ██       ██████  ██ ██   ████    ██    ███████


'''
    /
    Redirect to either basic or advanced mode based on the user's preference
'''
@app.route('/')
def endpoint_root():
    ##Also check database
    if not request.remote_addr in sD.studentDict:
        return redirect('/login')
    username = sD.studentDict[request.remote_addr]['name']
    #If no preferred homepage is set, check the database
    if not sD.studentDict[request.remote_addr]['preferredHomepage']:
        db = sqlite3.connect(os.path.dirname(os.path.abspath(__file__)) + '/data/database.db')
        dbcmd = db.cursor()
        dbData = dbcmd.execute("SELECT * FROM users WHERE username=:uname", {"uname": username}).fetchall()
        db.close()
        if len(dbData):
            pm = dbData[0][6]
            sD.studentDict[request.remote_addr]['preferredHomepage'] = pm
    if sD.studentDict[request.remote_addr]['preferredHomepage'] == 'advanced':
        return redirect('/advanced')
    if sD.studentDict[request.remote_addr]['preferredHomepage'] == 'basic':
        return redirect('/basic')
    return redirect('/setdefault')

@app.route('/2048')
def endpoint_2048():
    if not request.remote_addr in sD.studentDict:
        return redirect('/login?forward=' + request.path)
    if sD.studentDict[request.remote_addr]['perms'] > sD.settings['perms']['games']:
        return redirect(sD.mainPage + "?alert=You do not have high enough permissions to do this right now.")
    else:
        username = sD.studentDict[request.remote_addr]['name']
        db = sqlite3.connect(os.path.dirname(os.path.abspath(__file__)) + '/data/database.db')
        dbcmd = db.cursor()
        highScore = dbcmd.execute("SELECT * FROM scores WHERE username=:uname AND game='2048' ORDER BY score DESC", {"uname": username}).fetchone()
        db.close()
        if highScore:
            highScore = highScore[3]
        else:
            highScore = 0
        return render_template('2048.html', highScore = highScore)

#  █████
# ██   ██
# ███████
# ██   ██
# ██   ██


'''
/abcd
'''
@app.route('/abcd')
def endpoint_abcd():
    if not request.remote_addr in sD.studentDict:
        return redirect('/login?forward=' + request.path)
    if sD.studentDict[request.remote_addr]['perms'] > sD.settings['perms']['student']:
        return "You do not have high enough permissions to do this right now."
    else:
        ip = request.remote_addr
        vote = request.args.get('vote')
        if vote:
            if sD.settings['barmode'] == 'abcd':
                if vote in ["a", "b", "c", "d"]:
                    if sD.studentDict[request.remote_addr]['letter'] != vote:
                        sD.studentDict[request.remote_addr]['letter'] = vote
                        playSFX("sfx_blip01")
                        abcdBar()
                        return "Thank you for your tasty bytes... (" + vote + ")"
                    else:
                        return "You've already submitted an answer... (" + sD.studentDict[request.remote_addr]['letter'] + ")"
                elif vote == 'oops':
                    if sD.studentDict[request.remote_addr]['letter']:
                        sD.studentDict[request.remote_addr]['letter'] = ''
                        playSFX("sfx_hit01")
                        abcdBar()
                        return "I won\'t mention it if you don\'t"
                    else:
                        return "You don't have an answer to erase."
                else:
                    return "Bad arguments..."
            else:
                return "Not in ABCD mode."
        else:
            return redirect("/")

'''
    /addfighteropponent
'''
@app.route('/addfighteropponent')
def endpoint_addfighteropponent():
    code = request.args.get('code')
    name = request.args.get('name')
    sD.fighter['match' + code]['opponent'] = name #Set "opponent" of object to arg "name"

'''
/addfile
'''
@app.route('/addfile', methods = ['POST', 'GET'])
def endpoint_addfile():
    if not request.remote_addr in sD.studentDict:
        return redirect('/login?forward=' + request.path)
    else:
        if request.method == 'POST':
            title = request.form['title']
            file = request.form['file']
            list = request.form['list']
            print("Title: " + title)
            print("Filename: " + file)
            print("List: " + list)
            return 'File submitted to teacher.'
        else:
            return render_template('addfile.html')

@app.route('/advanced')
def endpoint_advanced():
    if not request.remote_addr in sD.studentDict:
        return redirect('/login')
    page = request.args.get('page') or ''
    mainPage = sD.mainPage.lstrip("/")
    username = sD.studentDict[request.remote_addr]['name']
    sfx.updateFiles()
    sounds = []
    music = []
    for key, value in sfx.sound.items():
        sounds.append(key)
    for key, value in bgm.bgm.items():
        music.append(key)
    return render_template('advanced.html', page = page, mainPage = mainPage, username = username, sfx = sounds, bgm = music)

@app.route('/api')
def endpoint_api():
    return "New API endpoint"

# ██████
# ██   ██
# ██████
# ██   ██
# ██████


'''
    /basic
    A simplified homepage for beginners
'''
@app.route('/basic')
def endpoint_basic():
    if not request.remote_addr in sD.studentDict:
        return redirect('/login?forward=' + request.path)
    sounds = []
    music = []
    for key, value in sfx.sound.items():
        sounds.append(key)
    for key, value in bgm.bgm.items():
        music.append(key)
    return render_template("basic.html", sfx = sounds, bgm = music)


'''
    /bgm
    This endpoint leads to the Background music page
'''
@app.route('/bgm')
def endpoint_bgm():
    if not request.remote_addr in sD.studentDict:
        return redirect('/login?forward=' + request.path)
    if sD.studentDict[request.remote_addr]['perms'] > sD.settings['perms']['bgm']:
        return "You do not have high enough permissions to do this right now."
    else:
        bgm.updateFiles()
        bgm_file = request.args.get('file')
        if bgm_file:
            if bgm_file == 'random':
                bgm_file = random.choice(list(bgm.bgm.keys()))
            if bgm_file in bgm.bgm:
                if time.time() - sD.bgm['lastTime'] >= 60 or sD.studentDict[request.remote_addr]['perms'] <= sD.settings['perms']['mod']:
                    sD.bgm['lastTime'] = time.time()
                    bgm_volume = request.args.get('volume')
                    try:
                        if request.args.get('volume'):
                            bgm_volume = float(bgm_volume)
                    except:
                        print("[warning] " + "Could not convert volume to float. Setting to default.")
                        bgm_volume = 0.5
                    sD.bgm['nowplaying']= bgm_file
                    if bgm_volume and type(bgm_volume) is float:
                        startBGM(bgm_file, bgm_volume)
                    else:
                        startBGM(bgm_file)
                    return 'Playing: ' + bgm_file
                else:
                    return "It has only been " + str(int(time.time() - sD.bgm['lastTime'])) + " seconds since the last song started. Please wait at least 60 seconds."
            else:
                return "Cannot find that filename!"
        elif request.args.get('voladj'):
            if request.args.get('voladj') == 'up':
                volBGM('up')
                return 'Music volume increased by one increment.'
            elif request.args.get('voladj') == 'down':
                volBGM('down')
                return 'Music volume decreased by one increment.'
            else:
                try:
                    bgm_volume = float(request.args.get('voladj'))
                    volBGM(bgm_volume)
                    return 'Music volume set to ' + request.args.get('voladj') + '.'
                except:
                    return 'Invalid voladj. Use \'up\', \'down\', or a number from 0.0 to 1.0.'
        elif request.args.get('playpause'):
            playpauseBGM()
            if sD.bgm['paused']:
                return 'Music resumed.'
            else:
                return 'Music paused.'
        elif request.args.get('rewind'):
            rewindBGM()
            return 'Music rewound.'
        else:
            resString = '<a href="/bgmstop">Stop Music</a>'
            resString += '<h2>Now playing: ' + sD.bgm['nowplaying'] + '</h2>'
            resString += '<h2>List of available background music files:</h2><ul>'
            for key, value in bgm.bgm.items():
                resString += '<li><a href="/bgm?file=' + key + '">' + key + '</a></li>'
            resString += '</ul> You can play them by using \'<b>/bgm?file=&lt;sound file name&gt;&volume=&lt;0.0 - 1.0&gt;\'</b>'
            resString += '<br><br>You can stop them by using \'<b>/bgmstop</b>\''
            return render_template("general.html", content = resString, style = '<style>ul {columns: 2; -webkit-columns: 2; -moz-columns: 2;}</style>')

'''
    /bgmstop
    Stops the current background Music
'''
@app.route('/bgmstop')
def endpoint_bgmstop():
    sD.bgm['paused'] = False
    stopBGM()
    return 'Stopped music...'

@app.route('/bitshifter')
def endpoint_bitshifter():
    if not request.remote_addr in sD.studentDict:
        return redirect('/login?forward=' + request.path)
    if sD.studentDict[request.remote_addr]['perms'] > sD.settings['perms']['games']:
        return redirect(sD.mainPage + "?alert=You do not have high enough permissions to do this right now.")
    else:
        username = sD.studentDict[request.remote_addr]['name']
        db = sqlite3.connect(os.path.dirname(os.path.abspath(__file__)) + '/data/database.db')
        dbcmd = db.cursor()
        highScore = dbcmd.execute("SELECT * FROM scores WHERE username=:uname AND game='bitshifter' ORDER BY score DESC", {"uname": username}).fetchone()
        db.close()
        if highScore:
            highScore = highScore[3]
        else:
            highScore = 0
        return render_template('bitshifter.html', highScore = highScore)

'''
    /break
    For when a student is temporarily unable to participate
'''

@app.route('/break')
def endpoint_break():
    if not request.remote_addr in sD.studentDict:
        return redirect('/login?forward=' + request.path)
    if sD.studentDict[request.remote_addr]['perms'] == sD.settings['perms']['teacher']:
        return redirect(sD.mainPage + "?alert=Teachers can't request bathroom breaks.")
    else:
        name = request.args.get('name') or sD.studentDict[request.remote_addr]['name'].strip()
        if name in helpList:
            ticket = helpList[name]
        else:
            ticket = ''
        if request.args.get('action') == 'request':
            if name in helpList:
                return redirect(request.path + "?alert=You already have a help ticket or break request in." )
            else:
                helpList[name] = '<i>Requested a bathroom break</i>'
                sD.studentDict[request.remote_addr]['help'] = True
                sD.studentDict[request.remote_addr]['breakReq'] = True
                playSFX("sfx_pickup02")
                return redirect(request.path + "?alert=Your request was sent. The teacher still needs to approve it.")
        elif request.args.get('action') == 'end':
            #Find the student whose username matches the "name" argument
            for student in sD.studentDict:
                if sD.studentDict[student]['name'].strip() == name:
                    if sD.studentDict[student]['excluded']:
                        sD.studentDict[student]['excluded'] = False
                        sD.studentDict[student]['perms'] = sD.studentDict[request.remote_addr]['oldPerms']
                        ##Commented out because WebSocket server isn't working
                        #server.send_message(sD.studentDict[student], json.dumps(packMSG('alert', student, 'server', 'Your break was ended.')))
                        return render_template("break.html", excluded = sD.studentDict[request.remote_addr]['excluded'], ticket = ticket)
                    else:
                        return redirect(request.path + "?alert=This student is not currently taking a bathroom break.")
            return 'Student not found.'
        else:
            return render_template("break.html", excluded = sD.studentDict[request.remote_addr]['excluded'], ticket = ticket)


#  ██████
# ██
# ██
# ██
#  ██████

@app.route('/changemode')
def endpoint_changemode():
    newMode = request.args.get('newMode') or ''
    direction = request.args.get('direction') or 'next'
    print(newMode)
    print(direction)
    return changeMode(newMode, direction)

'''
    /chat
    This endpoint allows students and teacher to chat realTime.
'''
@app.route('/chat')
def endpoint_chat():
    if not request.remote_addr in sD.studentDict:
        return redirect('/login?forward=' + request.path)
    db = sqlite3.connect(os.path.dirname(os.path.abspath(__file__)) + '/data/database.db')
    dbcmd = db.cursor()
    messages = dbcmd.execute("SELECT * FROM messages").fetchall()
    db.close()
    return render_template("chat.html", username = sD.studentDict[request.remote_addr]['name'], messages = json.dumps(messages))

@app.route('/cleartable')
def endpoint_cleartable():
    if not request.remote_addr in sD.studentDict:
        return redirect('/login?forward=' + request.path)
    if sD.studentDict[request.remote_addr]['perms'] > sD.settings['perms']['teacher']:
        return "You do not have high enough permissions to do this right now."
    table = request.args.get('table')
    if table:
        db = sqlite3.connect(os.path.dirname(os.path.abspath(__file__)) + '/data/database.db')
        dbcmd = db.cursor()
        dbcmd.execute("DELETE FROM " + table)
        db.commit()
        db.close()
        playSFX("sfx_explode01")
        return "Data in " + table + " deleted."
    else:
        return "Missing table argument."

'''
    /color
    Change the color of the entire bar
    Query Parameters:
        hex = six hexadecimal digit rgb color (prioritizes over RGB)
        r, g, b = provide three color values between 0 and 255
'''
@app.route('/color')
def endpoint_color():
    if not request.remote_addr in sD.studentDict:
        return redirect('/login?forward=' + request.path)
    elif sD.studentDict[request.remote_addr]['perms'] > sD.settings['perms']['bar']:
        return "You do not have high enough permissions to do this right now."
    else:
        try:
            r = int(request.args.get('r'))
            g = int(request.args.get('g'))
            b = int(request.args.get('b'))
        except:
            r = ''
            g = ''
            b = ''
        hex = request.args.get('hex')
        if hex and hex2dec(hex):
            fillBar(hex2dec(hex))
        elif not r == '' and not b == '' and not g == '':
            fillBar((r, g, b))
        else:
            return "Bad ArgumentsTry <b>/color?hex=FF00FF</b> or <b>/color?r=255&g=0&b=255</b>"
        if ONRPi:
            pixels.show()
        return "Color sent!"


@app.route('/countdown')
def endpoint_countdown():
    return 'This feature is not available yet.'

@app.route('/createaccount', methods = ['POST'])
def endpoint_createaccount():
    if not request.remote_addr in sD.studentDict:
        return redirect('/login?forward=' + request.path)
    if sD.studentDict[request.remote_addr]['perms'] > sD.settings['perms']['teacher']:
        return "You do not have high enough permissions to do this right now."
    name = request.args.get('name')
    password = request.args.get('password')
    passwordCrypt = cipher.encrypt(password.encode())
    db = sqlite3.connect(os.path.dirname(os.path.abspath(__file__)) + '/data/database.db')
    dbcmd = db.cursor()
    dbcmd.execute("INSERT INTO users (username, password, permissions, bot) VALUES (?, ?, ?, ?)", (name, passwordCrypt, sD.settings['perms']['anyone'], "False"))
    db.commit()
    db.close()
    return 'Account created.'

@app.route('/createfightermatch')
def endpoint_createfightermatch():
    code = request.args.get('code')
    name = request.args.get('name')
    sD.fighter['match' + code] = {} #Create new object for match
    sD.fighter['match' + code]['creator'] = name #Set "creator" of object to arg "name"
    return 'Match ' + code + ' created by ' + name + '.'

# ██████
# ██   ██
# ██   ██
# ██   ██
# ██████


'''
    /DEBUG
'''
@app.route('/debug')
def endpoint_debug():
    return render_template('debug.html')

# ███████
# ██
# █████
# ██
# ███████


'''
@app.route('/emptyblocks')
def endpoint_emptyblocks():
    blockList = []
    if ONRPi:
        pixels.fill((0,0,0))
    else:
        pixels = [(0,0,0)] * MAXPIX
    if ONRPi:
        pixels.show()
    return "Emptied blocks"
'''

# ███████
# ██
# █████
# ██
# ██


'''
    /fighter
'''
@app.route('/fighter')
def endpoint_fighter():
    if not request.remote_addr in sD.studentDict:
        return redirect('/login?forward=' + request.path)
    if sD.studentDict[request.remote_addr]['perms'] > sD.settings['perms']['games']:
        return redirect(sD.mainPage + "?alert=You do not have high enough permissions to do this right now.")
    else:
        #return render_template('fighter.html', username = sD.studentDict[request.remote_addr]['name'])
        return redirect(sD.mainPage + "?alert=Fighter will be ready to play soon.")

'''
    /flush
'''
@app.route('/flush')
def endpoint_flush():
    if not request.remote_addr in sD.studentDict:
        return redirect('/login?forward=' + request.path)
    if sD.studentDict[request.remote_addr]['perms'] > sD.settings['perms']['admin']:
        return "You do not have high enough permissions to do this right now."
    else:
        flushUsers()
        sD.refresh()
        return "Session was restarted."

#  ██████
# ██
# ██   ███
# ██    ██
#  ██████


@app.route('/getbgm')
def endpoint_getbgm():
    if not request.remote_addr in sD.studentDict:
        return '{"error": "You are not logged in."}'
    if sD.studentDict[request.remote_addr]['perms'] > sD.settings['perms']['api']:
        return '{"error": "Insufficient permissions."}'
    else:
        return '{"bgm": "' + str(sD.bgm['nowplaying']) + '", "paused": "' + str(sD.bgm['paused']) + '", "volume": "' + str(sD.bgm['volume']) + '"}'

@app.route('/getfightermatches')
def endpoint_getfightermatches():
    if not request.remote_addr in sD.studentDict:
        return '{"error": "You are not logged in."}'
    if sD.studentDict[request.remote_addr]['perms'] > sD.settings['perms']['api']:
        return '{"error": "Insufficient permissions."}'
    else:
        return json.dumps(sD.fighter)

@app.route('/getip')
def endpoint_getip():
    if not request.remote_addr in sD.studentDict:
        return '{"error": "You are not logged in."}'
    if sD.studentDict[request.remote_addr]['perms'] > sD.settings['perms']['api']:
        return '{"error": "Insufficient permissions."}'
    else:
        return '{"ip": "'+ ip +'"}'

#Sends back your student information
@app.route('/getme')
def endpoint_getme():
    if not request.remote_addr in sD.studentDict:
        return '{"error": "You are not logged in."}'
    if sD.studentDict[request.remote_addr]['perms'] > sD.settings['perms']['api']:
        return '{"error": "Insufficient permissions."}'
    else:
        return json.dumps(sD.studentDict[request.remote_addr])

@app.route('/getmode')
def endpoint_getmode():
    if not request.remote_addr in sD.studentDict:
        return '{"error": "You are not logged in."}'
    if sD.studentDict[request.remote_addr]['perms'] > sD.settings['perms']['api']:
        return '{"error": "Insufficient permissions."}'
    else:
        return '{"mode": "'+ str(sD.settings['barmode']) +'"}'

@app.route('/getpermissions')
def endpoint_getpermissions():
    if not request.remote_addr in sD.studentDict:
        return '{"error": "You are not logged in."}'
    if sD.studentDict[request.remote_addr]['perms'] > sD.settings['perms']['api']:
        return '{"error": "Insufficient permissions."}'
    else:
        return json.dumps(sD.settings['perms'])

@app.route('/getphrase')
def endpoint_getphrase():
    if not request.remote_addr in sD.studentDict:
        return '{"error": "You are not logged in."}'
    if sD.studentDict[request.remote_addr]['perms'] > sD.settings['perms']['api']:
        return '{"error": "Insufficient permissions."}'
    else:
        return '{"phrase": "'+ str(sD.activePhrase) +'"}'

#Shows the different colors the pixels take in the virtualbar.
@app.route('/getpix')
def endpoint_getpix():
    if not request.remote_addr in sD.studentDict:
        return '{"error": "You are not logged in."}'
    if sD.studentDict[request.remote_addr]['perms'] > sD.settings['perms']['api']:
        return '{"error": "Insufficient permissions."}'
    else:
        if not ONRPi:
            global pixels
        return '{"pixels": "'+ str(pixels[:BARPIX]) +'"}'

@app.route('/getquizname')
def endpoint_getquizname():
    if not request.remote_addr in sD.studentDict:
        return '{"error": "You are not logged in."}'
    if sD.studentDict[request.remote_addr]['perms'] > sD.settings['perms']['api']:
        return '{"error": "Insufficient permissions."}'
    else:
        if sD.activeQuiz:
            return '{"quizname": "'+ str(sD.activeQuiz['name']) +'"}'
        else:
            return '{"error": "No quiz is currently loaded."}'

#This endpoints shows the actions the students did EX:TUTD up
@app.route('/getstudents')
def endpoint_getstudents():
    if not request.remote_addr in sD.studentDict:
        return '{"error": "You are not logged in."}'
    if sD.studentDict[request.remote_addr]['perms'] <= sD.settings['perms']['admin']:
        return json.dumps(sD.studentDict)
    elif sD.studentDict[request.remote_addr]['perms'] <= sD.settings['perms']['api']:
        return json.dumps(stripUserData())
    else:
        return '{"error": "Insufficient permissions."}'

@app.route('/getword')
def endpoint_getword():
    if request.args.get('number'):
        try:
            number = int(request.args.get('number'))
            wordlist = []
            for i in range(number):
                wordlist.append(random.choice(list(words.keys())))
                return json.dumps(wordlist)
        except Exception as e:
            print("[error] " + "Could not convert number. " + str(e))
            return "Could not convert number. " + str(e)
    else:
        word = random.choice(list(words.keys()))
        return str(word)

# ██   ██
# ██   ██
# ███████
# ██   ██
# ██   ██


#This endpoint takes you to the hangman game
@app.route('/hangman')
def endpoint_hangman():
    if not request.remote_addr in sD.studentDict:
        return redirect('/login?forward=' + request.path)
    if sD.studentDict[request.remote_addr]['perms'] > sD.settings['perms']['games']:
        return redirect(sD.mainPage + "?alert=You do not have high enough permissions to do this right now.")
    else:
        if sD.lesson:
            if sD.lesson.vocab:
                wordObj = sD.lesson.vocab
        else:
            #Need more generic words here
            wordObj = {
                'place': 'your',
                'words': 'here'
            }
        username = sD.studentDict[request.remote_addr]['name']
        db = sqlite3.connect(os.path.dirname(os.path.abspath(__file__)) + '/data/database.db')
        dbcmd = db.cursor()
        highScore = dbcmd.execute("SELECT * FROM scores WHERE username=:uname AND game='hangman' ORDER BY score DESC", {"uname": username}).fetchone()
        db.close()
        if highScore:
            highScore = highScore[3]
        else:
            highScore = 0
        return render_template("hangman.html", wordObj=wordObj, highScore = highScore)

@app.route('/help')
def endpoint_help():
    if not request.remote_addr in sD.studentDict:
        return redirect('/login?forward=' + request.path)
    if sD.studentDict[request.remote_addr]['perms'] == sD.settings['perms']['teacher']:
        return redirect(sD.mainPage + "?alert=Teachers can't send help tickets.")
    else:
        if request.args.get('action') == "send":
            name = sD.studentDict[request.remote_addr]['name']
            name = name.strip()
            if name in helpList:
                return redirect("/help?alert=You already have a help ticket or break request in. If your problem is time-sensitive, or your last ticket was not cleared, please get the teacher's attention manually." )
            else:
                helpList[name] = request.args.get('message') or '<i>Sent a help ticket</i>'
                sD.studentDict[request.remote_addr]['help'] = True
                playSFX("sfx_up04")
                return redirect("/help?alert=Your ticket was sent. Keep working on the problem the best you can while you wait." )
        else:
            return render_template("help.html")

# ██
# ██
# ██
# ██
# ███████

@app.route('/leaderboards')
def endpoint_leaderboards():
    if not request.remote_addr in sD.studentDict:
        return redirect('/login?forward=' + request.path)
    game = request.args.get('game') or ''
    db = sqlite3.connect(os.path.dirname(os.path.abspath(__file__)) + '/data/database.db')
    dbcmd = db.cursor()
    data = dbcmd.execute("SELECT * FROM scores ORDER BY score DESC").fetchall()
    db.close()
    return render_template("leaderboards.html", game = game, data = json.dumps(data))

'''
    /lesson
    (Teacher)
    GET: This will take you to the lesson management page.
        QUERY PARAMS:
    POST: Submit a lesson excel spreadsheet for upload.
            (This needs validation on upload!)
'''
@app.route('/lesson', methods = ['POST', 'GET'])
def endpoint_lesson():
    if not request.remote_addr in sD.studentDict:
        return redirect('/login?forward=' + request.path)
    elif sD.studentDict[request.remote_addr]['perms'] > sD.settings['perms']['bar']:
        return redirect(sD.mainPage + "?alert=You do not have high enough permissions to do this right now.")
    else:
        if request.method == 'POST':
            if not request.files['file']:
                return 'Lesson file required.'
            else:
                f = request.files['file']
                f.save(os.path.join('lessondata', secure_filename(f.filename.strip(' '))))
                return redirect('/lesson')
        elif request.args.get('load'):
            try:
                sD.refresh()
                sD.lessonList = lessons.updateFiles()
                sD.lesson = lessons.readBook(request.args.get('load'))
                return redirect('/lesson')
            except Exception as e:
                print(traceback.format_exc())
                print("[error] " + e)
                return '<b>Error:</b> ' + str(e)
        elif request.args.get('action'):
            if request.args.get('action') == 'next':
                sD.currentStep += 1
                if sD.currentStep >= len(sD.lesson.steps):
                    sD.currentStep = len(sD.lesson.steps)
                    return 'End of lesson!'
                else:
                    updateStep()
                    return redirect('/lesson')
            elif request.args.get('action') == 'prev':
                sD.currentStep -= 1
                if sD.currentStep <= 0:
                    sD.currentStep = 0
                    return 'Already at start of lesson!'
                else:
                    updateStep()
                    return redirect('/lesson')
            elif request.args.get('action') == 'unload':
                sD.refresh()
                return 'Unloaded lesson.'
            elif request.args.get('action') == 'upload':
                return render_template('general.html', content='<form method=post enctype=multipart/form-data><input type=file name=file accept=".xlsx"><input type=submit value=Upload></form>')
            else:
                return redirect('/lesson')
        else:
            if not sD.lesson:
                sD.lessonList = lessons.updateFiles()
                resString = '<a href="/lesson?action=upload">Upload a Lesson</a><br>'
                resString += '<ul>'
                for lesson in sD.lessonList:
                    resString += '<li><a href="/lesson?load=' + lesson + '">' + lesson + '</a></li>'
                resString +='</ul>'
                return render_template('general.html', content=resString)
            else:
                resString = '<a href="/lesson?action=prev">Last Step</a>'
                resString += '<a href="/lesson?action=next">Next Step</a><br>'
                resString += '<a href="/lesson?action=unload">Unload Lesson</a>'
                resString += '<h2>Current Step: ' + str(sD.lesson.steps[sD.currentStep]['Prompt']) + '</h2>'
                resString += '<table>'
                #Agenda
                for i, item in enumerate(sD.lesson.agenda):
                    resString += '<tr>'
                    if not i:
                        for col in item:
                            resString += '<td class="header">' + col + '</td>'
                        resString += '</tr><tr>'
                    for col in item:
                        resString += '<td class="row">' + str(item[col]) + '</td>'
                    resString += '</div>'
                #Steps
                for i, item in enumerate(sD.lesson.steps):
                    resString += '<tr>'
                    if not i:
                        for col in item:
                            resString += '<td class="header">' + col + '</td>'
                        resString += '</tr><tr>'
                    for col in item:
                        resString += '<td class="row">' + str(item[col]) + '</td>'
                    resString += '</div>'
                #Objectives
                for i, item in enumerate(sD.lesson.objectives):
                    resString += '<tr>'
                    if not i:
                        for col in item:
                            resString += '<td class="header">' + col + '</td>'
                        resString += '</tr><tr>'
                    for col in item:
                        resString += '<td class="row">' + str(item[col]) + '</td>'
                    resString += '</div>'
                #Resources
                for i, item in enumerate(sD.lesson.links):
                    resString += '<tr>'
                    if not i:
                        for col in item:
                            resString += '<td class="header">' + col + '</td>'
                        resString += '</tr><tr>'
                    for col in item:
                        resString += '<td class="row">' + str(item[col]) + '</td>'
                    resString += '</div>'
                updateStep()
                return render_template('general.html', content=resString, style='<style>.header{font-weight: bold;}.row:nth-child(odd){background-color: #aaaaaa;}.row:nth-child(even){background-color: #cccccc;}.entry{}</style>')

'''
    /login
    Handles logging into the Formbar
'''
@app.route('/login', methods = ['POST', 'GET'])
def endpoint_login():
    remote = request.remote_addr
    if remote in banList:
        return "This IP is in the banlist."
    else:
        if request.method == 'POST':
            username = request.form['username']
            username = username.strip()
            password = request.form['password']
            passwordCrypt = cipher.encrypt(password.encode()) #Required to be bytes?
            userType = request.form['userType']
            forward = request.form['forward']
            bot = request.form['bot']
            bot = bot.lower() == "true"


            if userType == "login":
                if username and password:
                    #Open and connect to database
                    db = sqlite3.connect(os.path.dirname(os.path.abspath(__file__)) + '/data/database.db')
                    dbcmd = db.cursor()
                    userFound = dbcmd.execute("SELECT * FROM users WHERE username=:uname", {"uname": username}).fetchall()
                    db.close()
                    if userFound:
                        for user in userFound:
                            if username in user:
                                #Check if the password is correct
                                if password == cipher.decrypt(user[2]).decode():
                                    newStudent(remote, username, bot=bot)
                                    if bot:
                                        return json.dumps({'status': 'success'})
                                    if forward:
                                        return redirect(forward, code=302)
                                    else:
                                        return redirect('/', code=302)
                                else:
                                    if bot:
                                        return json.dumps({'status': 'failed', 'reason': 'credentials'})
                                    else:
                                        return redirect("/login?alert=Your password is incorrect.")
                    else:
                        return redirect("/login?alert=No users found with that username.")
                else:
                    return redirect("/login?alert=You need to enter a username and password.")

            elif userType == "new":
                #Open and connect to database
                db = sqlite3.connect(os.path.dirname(os.path.abspath(__file__)) + '/data/database.db')
                dbcmd = db.cursor()
                userFound = dbcmd.execute("SELECT * FROM users WHERE username=:uname", {"uname": username}).fetchall()
                db.close()
                if userFound:
                    return redirect("/login?alert=There is already a user with that name.")
                else:
                    db = sqlite3.connect(os.path.dirname(os.path.abspath(__file__)) + '/data/database.db')
                    dbcmd = db.cursor()
                    #Add user to database
                    userFound = dbcmd.execute("INSERT INTO users (username, password, permissions, bot) VALUES (?, ?, ?, ?)", (username, passwordCrypt, sD.settings['perms']['anyone'], str(bot)))
                    db.commit()
                    db.close()
                    newStudent(remote, username, bot=bot)
                    if forward:
                        return redirect(forward, code=302)
                    else:
                        return redirect('/', code=302)

            elif userType == "guest":
                #Open and connect to database
                db = sqlite3.connect(os.path.dirname(os.path.abspath(__file__)) + '/data/database.db')
                dbcmd = db.cursor()
                userFound = dbcmd.execute("SELECT * FROM users WHERE username=:uname", {"uname": username}).fetchall()
                db.close()
                if userFound:
                    return redirect("/login?alert=There is already a user with that name.")
                else:
                    newStudent(remote, username)
                    if forward:
                        return redirect(forward, code=302)
                    else:
                        return redirect('/', code=302)

        else:
            #If the user is logged in, log them out
            if remote in sD.studentDict:
                del sD.studentDict[request.remote_addr]
                playSFX('sfx_laser01')
            if request.args.get('name'): ##needs update
                newStudent(remote, request.args.get('name'))
                return redirect('/', code=302)
            return render_template("login.html")

# ███    ███
# ████  ████
# ██ ████ ██
# ██  ██  ██
# ██      ██


'''
    /minesweeper
'''
@app.route('/minesweeper')
def endpoint_minesweeper():
    if not request.remote_addr in sD.studentDict:
        return redirect('/login?forward=' + request.path)
    elif sD.studentDict[request.remote_addr]['perms'] > sD.settings['perms']['games']:
        return redirect(sD.mainPage + "?alert=You do not have high enough permissions to do this right now.")
    else:
        cols = 20
        rows = 20
        dense = 10
        if request.args.get('cols'):
            cols = request.args.get('cols')
        if request.args.get('rows'):
            rows = request.args.get('rows')
        if request.args.get('dense'):
            dense = request.args.get('dense')
        username = sD.studentDict[request.remote_addr]['name']
        db = sqlite3.connect(os.path.dirname(os.path.abspath(__file__)) + '/data/database.db')
        dbcmd = db.cursor()
        bestTime = dbcmd.execute("SELECT * FROM scores WHERE username=:uname AND game='minesweeper' ORDER BY score ASC", {"uname": username}).fetchone()
        db.close()
        if bestTime:
            bestTime = bestTime[3]
        else:
            bestTime = 0
        return render_template("mnsw.html", cols=cols, rows=rows, dense=dense, bestTime=bestTime)

'''
    /mobile
    Homepage for mobile devices
'''
@app.route('/mobile')
def endpoint_mobile():
    if not request.remote_addr in sD.studentDict:
        return redirect('/login?forward=' + request.path)
    sounds = []
    music = []
    for key, value in sfx.sound.items():
        sounds.append(key)
    for key, value in bgm.bgm.items():
        music.append(key)
    return render_template("mobile.html", sfx = sounds, bgm = music)

# ███    ██
# ████   ██
# ██ ██  ██
# ██  ██ ██
# ██   ████


#This endpoint allows the teacher to check tickets that students send for help.
@app.route('/needshelp')
def endpoint_needshelp():
    if not request.remote_addr in sD.studentDict:
        return redirect('/login?forward=' + request.path)
    if sD.studentDict[request.remote_addr]['perms'] > sD.settings['perms']['admin']:
        return redirect(sD.mainPage + "?alert=You do not have high enough permissions to do this right now.")
    else:
        remove = request.args.get('remove')
        '''
        if bool(helpList):
            if ONRPi:
                pixels.fill(colors['red'])
            else:
                pixels = [colors['red']] * MAXPIX
        else:
            if ONRPi:
                pixels.fill((0, 0, 0))
            else:
                pixels = [(0,0,0)] * MAXPIX
        if ONRPi:
            pixels.show()
        '''
    if remove:
        if remove in helpList:
            #Seacrch through each student
            for student in sD.studentDict:
                #If the name with no whitespaces equals the name we want to remove
                name = sD.studentDict[student]['name'].strip()
                if name == remove:
                    #Remove the help flag from their user and break loop
                    sD.studentDict[student]['help'] = False
                    if request.args.get('acceptBreak'):
                        sD.studentDict[student]['excluded'] = True
                        sD.studentDict[student]['oldPerms'] = sD.studentDict[request.remote_addr]['perms'] #Get the student's current permissions so they can be restored later
                        sD.studentDict[student]['perms'] = sD.settings['perms']['anyone']
                    ##Commented out because WebSocket server isn't working
                        #server.send_message(sD.studentDict[student], json.dumps(packMSG('alert', name, 'server', 'The teacher accepted your break request.')))
                    #elif helpList[name] == "<i>Requested a bathroom break</i>":
                        #server.send_message(sD.studentDict[student], json.dumps(packMSG('alert', name, 'server', 'The teacher rejected your break request.')))
            del helpList[remove]
            return redirect("/needshelp")
        else:
            return "Couldn't find ticket for: " + remove + "."
    else:
        resString = '<meta http-equiv="refresh" content="5">'
        if not helpList:
            resString += "No tickets yet. <button class='inline popOut' onclick='location.reload();'>Try Again</button>"
        else:
            for ticket in helpList:
                resString += "<span class='ticket'><b>" + ticket + ":</b> " + helpList[ticket]
                if helpList[ticket] == '<i>Requested a bathroom break</i>':
                    resString += " <button class='inline popOut' onclick='window.location = \"/needshelp?remove=" + ticket + "&acceptBreak=true\"'>Accept</button> <button class='inline popOut' onclick='window.location = \"/needshelp?remove=" + ticket + "\"'>Reject</button>"
                else:
                    resString += " <button class='inline popOut' onclick='window.location = \"/needshelp?remove=" + ticket + "\"'>Remove</button>"
                resString += "</span>"
        return render_template("needshelp.html", list = resString)

# ██████
# ██   ██
# ██████
# ██
# ██


@app.route('/perc')
def endpoint_perc():
    if not request.remote_addr in sD.studentDict:
        return redirect('/login?forward=' + request.path)
    elif sD.studentDict[request.remote_addr]['perms'] > sD.settings['perms']['bar']:
        return "You do not have high enough permissions to do this right now."
    else:
        percAmount = request.args.get('amount')
        try:
            percAmount = int(percAmount)
            percFill(percAmount)
        except:
            return "<b>amount</b> must be an integer between 0 and 100 \'/perc?amount=<b>50</b>\'"
        return "Set perecentage to: " + str(percAmount) + "."

'''
    /profile
'''
@app.route('/profile')
def endpoint_profile():
    if not request.remote_addr in sD.studentDict:
        return redirect('/login?forward=' + request.path)
    elif sD.studentDict[request.remote_addr]['perms'] >= sD.settings['perms']['banned']:
        return redirect(sD.mainPage + "?alert=You do not have high enough permissions to do this right now.")
    else:
        name = request.args.get('user') or sD.studentDict[request.remote_addr]['name']
        for x in sD.studentDict:
            user = sD.studentDict[x]
            if user['name'].strip() == name:
                username = sD.studentDict[request.remote_addr]['name']
                db = sqlite3.connect(os.path.dirname(os.path.abspath(__file__)) + '/data/database.db')
                dbcmd = db.cursor()
                highScores = {
                    "2048": dbcmd.execute("SELECT * FROM scores WHERE username=:uname AND game='2048' ORDER BY score DESC", {"uname": user['name']}).fetchone(),
                    "hangman": dbcmd.execute("SELECT * FROM scores WHERE username=:uname AND game='hangamn' ORDER BY score DESC", {"uname": user['name']}).fetchone()
                }
                db.close()
                return render_template("profile.html", username = user['name'], perms = sD.settings['permname'][user['perms']], bot = user['bot'], highScores = json.dumps(highScores))
        #If there are no matches
        return "There are no users with that name."

'''
    /progress
'''
@app.route('/progress', methods = ['POST', 'GET'])
def endpoint_progress():
    if not request.remote_addr in sD.studentDict:
        return redirect('/login?forward=' + request.path)
    #elif sD.studentDict[request.remote_addr]['perms'] > sD.settings['perms']['bar']:
    #     return redirect(sD.mainPage + "?alert=You do not have high enough permissions to do this right now.")
    else:
        if request.args.get('check'):
            try:
                check = int(request.args.get('check'))
                sD.studentDict[request.remote_addr]['progress'][check] = not sD.studentDict[request.remote_addr]['progress'][check]
                percAmount = sD.lesson.checkProg(sD.studentDict)
                if sD.settings['barmode'] == 'progress':
                    percFill(percAmount)
                return str(check) + " was toggled."
            except Exception as e:
                print("[error] " + e)
                return '<b>Error:</b> ' + str(e)
        else:
            if sD.activeProgress:
                return render_template('progress.html', progress=sD.activeProgress)
            else:
                return 'There is no progress tracker active right now.'

#  ██████
# ██    ██
# ██    ██
# ██ ▄▄ ██
#  ██████
#     ▀▀


#takes you to a quiz(literally)
@app.route('/quiz', methods = ['POST', 'GET'])
def endpoint_quiz():
    if not request.remote_addr in sD.studentDict:
        return redirect('/login?forward=' + request.path)
    elif sD.studentDict[request.remote_addr]['perms'] > sD.settings['perms']['student']:
        return redirect(sD.mainPage + "?alert=You do not have high enough permissions to do this right now.")
    else:
        if request.method == 'POST':
            messageOut = packMSG('alert', 'all', 'server', 'The teacher started a quiz.<br><button onclick="window.location=\"/quiz\"">Open quiz</button>')
            server.send_message_to_all(json.dumps(messageOut))
            resString = '<ul>'
            for i, answer in enumerate(request.form):
                resString += '<li>' + str(i) + ': '
                if sD.activeQuiz['keys'][i] == int(request.form[answer]):
                    sD.studentDict[request.remote_addr]['quizRes'].append(True)
                    resString += '<b>Correct!</b></li>'
                else:
                    sD.studentDict[request.remote_addr]['quizRes'].append(False)
                    resString += 'Incorrect</li>'
                    sD.studentDict[request.remote_addr]['complete'] = True
                    return render_template('general.html', content=resString)
        elif sD.activeQuiz:
            return render_template('quiz.html', quiz=sD.activeQuiz)
        else:
            return redirect(sD.mainPage + "?alert=No quiz is currently loaded.")
            return render_template('chat.html', message='No quiz is currently loaded.')

# ███████
# ██
# ███████
#      ██
# ███████

@app.route('/savescore', methods = ['POST'])
def endpoint_savescore():
    if not request.remote_addr in sD.studentDict:
        return redirect('/login?forward=' + request.path)
    game = request.args.get("game")
    score = request.args.get("score")
    if game and score:
        username = sD.studentDict[request.remote_addr]['name']
        db = sqlite3.connect(os.path.dirname(os.path.abspath(__file__)) + '/data/database.db')
        dbcmd = db.cursor()
        dbcmd.execute("INSERT INTO scores (game, username, score) VALUES (?, ?, ?)", (game, username, score))
        db.commit()
        db.close()
        return "Score saved to database."
    else:
        return "Missing arguments."


@app.route('/say')
def endpoint_say():
    if not request.remote_addr in sD.studentDict:
        return redirect('/login?forward=' + request.path)
    elif sD.studentDict[request.remote_addr]['perms'] > sD.settings['perms']['bar']:
        return "You do not have high enough permissions to do this right now."
    else:
        sD.activePhrase = request.args.get('phrase')
        fgColor = request.args.get('fg')
        bgColor = request.args.get('bg')
        if sD.activePhrase:
            if hex2dec(fgColor) and hex2dec(bgColor):
                clearString()
                showString(sD.activePhrase, 0, hex2dec(fgColor), hex2dec(bgColor))
            else:
                clearString()
                showString(sD.activePhrase)
                if ONRPi:
                    pixels.show()
            return "Set phrase to: " + str(sD.activePhrase) + "."
        else:
            return "<b>phrase</b> must contain a string. \'/say?phrase=<b>\'hello\'</b>\'"

@app.route('/segment')
def endpoint_segment():
    if not ONRPi:
        global pixels
    if not request.remote_addr in sD.studentDict:
        return redirect('/login?forward=' + request.path)
    elif sD.studentDict[request.remote_addr]['perms'] > sD.settings['perms']['bar']:
        return "You do not have high enough permissions to do this right now."
    else:
        type = request.args.get('type')
        hex = request.args.get('hex')
        hex2 = request.args.get('hex2')
        start = request.args.get('start')
        end = request.args.get('end')
        if not hex:
            return "Bad ArgumentsTry <b>/segment?start=0&end=10&hex=FF00FF</b> (you need at least one color)"
        if not hex2dec(hex):
            return "Bad ArgumentsTry <b>/segment?start=0&end=10&hex=FF00FF</b> (you did not use a proper hexadecimal color)"
        if not start or not end:
            return "Bad ArgumentsTry <b>/segment?start=0&end=10&hex=FF00FF</b> (you need a start and end point)"
        else:
            try:
                start = int(start)
                end = int(end)
            except:
                return "Bad ArgumentsTry <b>/segment?start=0&end=10&hex=FF00FF</b> (start and end must be and integer)"
        if start > BARPIX or end > BARPIX:
            return "Bad ArgumentsTry <b>/segment?start=0&end=10&hex=FF00FF</b> (Your start or end was higher than the number of pixels: " + str(BARPIX) + ")"
        pixRange = range(start, end)
        if type == 'fadein':
            for i, pix in enumerate(pixRange):
                pixels[pix] = fadein(pixRange, i, hex2dec(hex))
        elif type == 'fadeout':
            for i, pix in enumerate(pixRange):
                pixels[pix] = fadeout(pixRange, i, hex2dec(hex))
        elif type == 'blend':
            if not hex:
                return "Bad ArgumentsTry <b>/segment?start=0&end=10&hex=FF00FF&hex2=#00FF00</b> (you need at least two colors)"
            if not hex2dec(hex):
                return "Bad ArgumentsTry <b>/segment?start=0&end=10&hex=FF00FF&hex2=#00FF00</b> (you did not use a proper hexadecimal color)"
            else:
                for i, pix in enumerate(pixRange):
                    pixels[pix] = blend(pixRange, i, hex2dec(hex), hex2dec(hex2))
        elif type == 'color':
                for i, pix in enumerate(pixRange):
                    pixels[pix] = hex2dec(hex)
        else:
            if hex2dec(hex):
                fillBar(hex2dec(hex))
            else:
                return "Bad ArgumentsTry <b>/color?hex=FF00FF</b> or <b>/color?r=255&g=0&b=255</b>"
        if ONRPi:
            pixels.show()
        return "Color sent!"

'''
@app.route('/sendblock')
def endpoint_sendblock():
    if not sD.settings['barmode'] == 'blockchest':
        return "Not in blockchest sD.settings['barmode']"
    blockId = request.args.get("id")
    blockData = request.args.get("data")
    if blockId and blockData:
        if blockId in colorDict:
            blockList.append([blockId, blockData])
            addBlock()
            #fillBlocks()
            return "Got Block: " + blockId + ", " + blockData
        else:
            return "Bad block Id"
    else:
        return "Bad Arguments. Requires 'id' and 'data'"
'''

#Choose whether you want to use basic or expert mode
@app.route('/setdefault', methods = ['POST', 'GET'])
def endpoint_setdefault():
    if not request.remote_addr in sD.studentDict:
        return redirect('/login?forward=' + request.path)
    if request.method == 'POST':
        if request.form['mode'] == 'basic' or request.form['mode'] == 'advanced':
            sD.studentDict[request.remote_addr]['preferredHomepage'] = request.form['mode']
            db = sqlite3.connect(os.path.dirname(os.path.abspath(__file__)) + '/data/database.db')
            dbcmd = db.cursor()
            dbcmd.execute("UPDATE users SET preferredHomepage=:mode WHERE username=:uname", {"uname": sD.studentDict[request.remote_addr]['name'], "mode": request.form['mode']})
            db.commit()
            db.close()
        else:
            return 'Invalid mode.'
        return redirect('/')
    else:
        return render_template('setdefault.html', pm = sD.studentDict[request.remote_addr]['preferredHomepage'])

#This endpoint is exclusive only to the teacher.
@app.route('/settings', methods = ['POST', 'GET'])
def endpoint_settings():
    if not request.remote_addr in sD.studentDict:
        return redirect('/login?forward=' + request.path)
    elif sD.studentDict[request.remote_addr]['perms'] > sD.settings['perms']['admin']:
        return redirect(sD.mainPage + "?alert=You do not have high enough permissions to do this right now.")
    else:
        resString = ''
        #Loop through every arg that was sent as a query parameter
        for arg in request.args:
            #See if you save the
            argVal = str2bool(request.args.get(arg))
            #if the argVal resolved to a boolean value
            if isinstance(argVal, bool):
                if arg in sD.settings:
                    sD.settings[arg] = argVal
                    resString += 'Set <i>' + arg + '</i> to: <i>' + str(argVal) + "</i>"
                else:
                    resString += 'There is no setting that takes \'true\' or \'false\' named: <i>' + arg + "</i>"
            else:
                try:
                    argInt = int(request.args.get(arg))
                    if arg in sD.settings['perms']:
                        if argInt > 4 or argInt < 0:
                            resString += "Permission value out of range! "
                        else:
                            sD.settings['perms'][arg] = argInt
                except:
                    pass

        ###
        ### Everything past this point uses the old method of changing settings. Needs updated
        ###

        if request.args.get('students'):
            sD.settings['numStudents'] = int(request.args.get('students'))
            if sD.settings['numStudents'] == 0:
                sD.settings['autocount'] = True
                autoStudentCount()
            else:
                sD.settings['autocount'] = False
                resString += 'Set <i>numStudents</i> to: ' + str(sD.settings['numStudents'])
        if request.args.get('barmode'):
            if request.args.get('barmode') in sD.settings['modes']:
                sD.settings['barmode'] = request.args.get('barmode')
                resString += 'Set <i>mode</i> to: ' + sD.settings['barmode']
            else:
                resString += 'No setting called ' + sD.settings['barmode']
        if resString == '':
            return render_template("settings.html")
        else:
            playSFX("sfx_pickup01")
            resString += ""
            return resString

#This endpoint leads to the Sound Effect page
@app.route('/sfx')
def endpoint_sfx():
    if not request.remote_addr in sD.studentDict:
        return redirect('/login?forward=' + request.path)
    if sD.studentDict[request.remote_addr]['perms'] > sD.settings['perms']['sfx']:
        return "You do not have high enough permissions to do this right now."
    else:
        sfx.updateFiles()
        sfx_file = request.args.get('file')
        if sfx_file in sfx.sound:
            playSFX(sfx_file)
            return 'Playing: ' + sfx_file
        else:
            resString = '<h2>List of available sound files:</h2><ul>'
            for key, value in sfx.sound.items():
                resString += '<li><a href="/sfx?file=' + key + '">' + key + '</a></li>'
            resString += '</ul> You can play them by using \'/sfx?file=<b>&lt;sound file name&gt;</b>\''
            return render_template("general.html", content = resString, style = '<style>ul {columns: 2; -webkit-columns: 2; -moz-columns: 2;}</style>')

'''
    /speedtype
'''
@app.route('/speedtype')
def endpoint_speedtype():
    if not request.remote_addr in sD.studentDict:
        return redirect('/login?forward=' + request.path)
    elif sD.studentDict[request.remote_addr]['perms'] > sD.settings['perms']['games']:
        return redirect(sD.mainPage + "?alert=You do not have high enough permissions to do this right now.")
    else:
        username = sD.studentDict[request.remote_addr]['name']
        db = sqlite3.connect(os.path.dirname(os.path.abspath(__file__)) + '/data/database.db')
        dbcmd = db.cursor()
        highScore = dbcmd.execute("SELECT * FROM scores WHERE username=:uname AND game='speedtype' ORDER BY score DESC", {"uname": username}).fetchone()
        db.close()
        if highScore:
            highScore = highScore[3]
        else:
            highScore = 0
        return render_template("speedtype.html", highScore = highScore)

#Start a thumbs survey
@app.route('/startsurvey')
def endpoint_startsurvey():
    if not request.remote_addr in sD.studentDict:
        return redirect('/login?forward=' + request.path)
    elif sD.studentDict[request.remote_addr]['perms'] > sD.settings['perms']['mod']:
        return "You do not have high enough permissions to do this right now."
    else:
        if not request.args.get('type'):
            return "You need a survey type."
        type = request.args.get('type')
        if not (type == 'tutd' or type == 'abcd' or type == 'text'):
            return "Invalid survey type."
        changeMode(type)
        repeatMode()
        return 'Started a new ' + type + ' survey.'

# ████████
#    ██
#    ██
#    ██
#    ██

'''
/textresponse
'''
@app.route('/textresponse')
def endpoint_textresponse():
    if not request.remote_addr in sD.studentDict:
        return redirect('/login?forward=' + request.path)
    else:
        response = request.args.get('response')
        if sD.settings['barmode'] == 'text':
            sD.studentDict[request.remote_addr]['textRes'] = response
            textBar()
            return "Response submitted."
        else:
            return "Not in text response mode."


#Tic Tac Toe
@app.route('/ttt')
def endpoint_ttt():
    if not request.remote_addr in sD.studentDict:
        return redirect('/login?forward=' + request.path)
    if sD.studentDict[request.remote_addr]['perms'] > sD.settings['perms']['student']:
        return redirect(sD.mainPage + "?alert=You do not have high enough permissions to do this right now.")
    else:
        opponent = request.args.get('opponent')

        #Loop through all existing games
        for game in sD.ttt:
            #If the user and the opponent is in an existing player list
            if sD.studentDict[request.remote_addr]['name'] in game.players and opponent in game.players:
                #Then you have found the right game and can edit it here
                return render_template("ttt.html", game = str(game))
                #return the response here


        #Creating a new game
        for student in sD.studentDict:
            if sD.studentDict[student]['name'] == opponent:
                sD.ttt.append(sessions.TTTGame([sD.studentDict[request.remote_addr]['name'], opponent]))
                return render_template("ttt.html", game = json.dumps(sD.ttt[-1].__dict__))


        #If there is no game with these players
        return redirect(sD.mainPage + "?alert=No game found")

'''
    /tutd
    Thumbs-Up-Thumbs-Down page (Thumbspanel)
'''
@app.route('/tutd')
def endpoint_tutd():
    if not request.remote_addr in sD.studentDict:
        return redirect('/login?forward=' + request.path)
    else:
        ip = request.remote_addr
        thumb = request.args.get('thumb')
        if thumb:
            if sD.settings['barmode'] == 'tutd':
                # print("[info] " + "Recieved " + thumb + " from " + name + " at ip: " + ip)
                if thumb in ['up', 'down', 'wiggle']:
                    if sD.studentDict[request.remote_addr]['thumb'] != thumb:
                        sD.studentDict[request.remote_addr]['thumb'] = thumb
                        tutdBar()
                        return "Thank you for your tasty bytes... (" + thumb + ")"
                    else:
                        return "You've already submitted this answer... (" + thumb + ")"
                elif thumb == 'oops':
                    if sD.studentDict[request.remote_addr]['thumb']:
                        sD.studentDict[request.remote_addr]['thumb'] = ''
                        playSFX("sfx_hit01")
                        tutdBar()
                        return "I won\'t mention it if you don\'t"
                    else:
                        return "You don't have an answer to erase."
                else:
                    return "Bad ArgumentsTry <b>/tutd?thumb=wiggle</b>You can also try <b>down</b> and <b>up</b> instead of <b>wiggle</b>"
            else:
                return "Not in TUTD mode."
        else:
            return redirect("/")

# ██    ██
# ██    ██
# ██    ██
# ██    ██
#  ██████


#This endpoint allows us to see which user(Student) is logged in.
@app.route('/users')
def endpoint_users():
    if not request.remote_addr in sD.studentDict:
        return redirect('/login?forward=' + request.path)
    if sD.studentDict[request.remote_addr]['perms'] > sD.settings['perms']['users']:
        return redirect(sD.mainPage + "?alert=You do not have high enough permissions to do this right now.")
    else:
        user = '';
        if request.args.get('name'):
            for key, value in sD.studentDict.items():
                if request.args.get('name') == sD.studentDict[key]['name']:
                    user = key
                    break
            if not user:
                return "That user was not found by their name."
        if request.args.get('ip'):
            if request.args.get('ip') in sD.studentDict:
                user = request.args.get('ip')
            else:
                return "That user was not found by their IP address."
        if user:
            if request.args.get('action'):
                action = request.args.get('action')
                if action == 'kick':
                    if user in sD.studentDict:
                        del sD.studentDict[user]
                        return "User removed"
                    else:
                        return "User not in list."
                if action == 'ban':
                    if user in sD.studentDict:
                        banList.append(user)
                        del sD.studentDict[user]
                        return "User removed and added to ban list."
                    else:
                        return "User not in list."
                if action == 'perm':
                    if request.args.get('perm'):
                        try:
                            perm = int(request.args.get('perm'))
                            if user in sD.studentDict:
                                if perm > 4 or perm < 0 :
                                    return "Permissions out of range."
                                else:
                                    sD.studentDict[user]['perms'] = perm
                                    #Open and connect to database
                                    db = sqlite3.connect(os.path.dirname(os.path.abspath(__file__)) + '/data/database.db')
                                    dbcmd = db.cursor()
                                    dbcmd.execute("UPDATE users SET permissions=:perms WHERE username=:uname", {"uname": sD.studentDict[user]['name'], "perms": sD.studentDict[user]['perms']})
                                    db.commit()
                                    db.close()
                                    print("[info] " + "")
                                    return "Changed user permission."
                            else:
                                return "User not in list."
                        except:
                            return "Perm was not an integer."
                if action == 'changePw':
                    password = request.args.get('password')
                    if password:
                        passwordCrypt = cipher.encrypt(password.encode())
                        db = sqlite3.connect(os.path.dirname(os.path.abspath(__file__)) + '/data/database.db')
                        dbcmd = db.cursor()
                        dbcmd.execute("UPDATE users SET password=:pw WHERE username=:uname", {"uname": sD.studentDict[user]['name'], "pw": passwordCrypt})
                        db.commit()
                        db.close()
                        return "Password reset."
                    else:
                        return "New password reqired."
                if action == 'delete':
                    db = sqlite3.connect(os.path.dirname(os.path.abspath(__file__)) + '/data/database.db')
                    dbcmd = db.cursor()
                    dbcmd.execute("DELETE FROM users WHERE username=:uname", {"uname": sD.studentDict[user]['name']})
                    db.commit()
                    db.close()
                    if user in sD.studentDict:
                        del sD.studentDict[user]
                    return "User deleted."
            if request.args.get('refresh'):
                refresh = request.args.get('refresh')
                if refresh == 'all':
                    if refreshUsers(user):
                        return "Removed all student responses."
                    else:
                        return "Error removing responses from all students."
                else:
                    if refreshUsers(user, refresh):
                        return "Removed " + refresh + " responses from " + user + "."
                    else:
                        return "Error removgin " + refresh + " responses from " + user + "."
            else:
                return "No action given."
        else:
            return render_template("users.html")

# ██    ██
# ██    ██
# ██    ██
#  ██  ██
#   ████


#This endpoint allows you to see the formbars IP with style and shows different colors.
@app.route('/virtualbar')
def endpoint_virtualbar():
    return render_template("virtualbar.html")

# ██     ██
# ██     ██
# ██  █  ██
# ██ ███ ██
#  ███ ███


#This will take the student to the current "What are we doing?" link
@app.route('/wawd')
def endpoint_wawd():
    content = ''
    if sD.activePrompt:
        content = '<h2>'
        if sD.lesson.steps[sD.currentStep]['Type']:
            content += '<b>'+sD.lesson.steps[sD.currentStep]['Type'] + ': </b>'
        content += '<i>' + sD.activePrompt+'</i></h2>'
    if sD.wawdLink:
        if sD.wawdLink[0] == "/":
            content += '<a href="' + str(sD.wawdLink) + '">Go to page</a>'
        else:
            content += '<h2>External Resource</h2><a href="' + str(sD.wawdLink) + '">' + str(sD.wawdLink) + '</a>'
    if not content:
        content = 'There is no active lesson right now.'
    return render_template('general.html', content = content)


# ██     ██ ███████ ██████  ███████  ██████   ██████ ██   ██ ███████ ████████ ███████
# ██     ██ ██      ██   ██ ██      ██    ██ ██      ██  ██  ██         ██    ██
# ██  █  ██ █████   ██████  ███████ ██    ██ ██      █████   █████      ██    ███████
# ██ ███ ██ ██      ██   ██      ██ ██    ██ ██      ██  ██  ██         ██         ██
#  ███ ███  ███████ ██████  ███████  ██████   ██████ ██   ██ ███████    ██    ███████


'''
    Websocket Setup
    https://github.com/Pithikos/python-websocket-server

    A message to or from the server should be a stringified JSON object:
    {
        type: <alert|userlist|help|message|fighter>,
        to: <*username*|server|all>,
        from: <*username*|server>,
        content: <message>
    }

'''

def packMSG(type, rx, tx, content):
    msgOUT = {
        "type": type,
        "to": rx,
        "from": tx,
        "content": content
        }
    return msgOUT

# Called for every client connecting (after handshake)
def new_client(client, server):
    try:
        sD.studentDict[client['address'][0]]['wsID'] = client['id']
        print("[info] " + sD.studentDict[client['address'][0]]['name'] + " connected and was given id %d" % client['id'])
        server.send_message_to_all(json.dumps(packMSG('alert', 'all', 'server', sD.studentDict[client['address'][0]]['name'] + " has joined the server...")))
        server.send_message_to_all(json.dumps(packMSG('userlist', 'all', 'server', chatUsers())))
    except Exception as e:
        print("[error] " + "Error finding user in list: " + str(e))

# Called for every client disconnecting
def client_left(client, server):
    print("[info] " + sD.studentDict[client['address'][0]]['name'] + " disconnected")
    del sD.studentDict[client['address'][0]]['wsID']
    #Send a message to every client that isn't THIS disconnecting client, telling them the user disconnected
    for i, user in enumerate(server.clients):
        if not server.clients[i] == client:
            server.send_message(server.clients[i], json.dumps(packMSG('alert', 'all', 'server', sD.studentDict[client['address'][0]]['name'] + " has left the server...")))
            server.send_message(server.clients[i], json.dumps(packMSG('userlist', 'all', 'server', chatUsers())))

# Called when a client sends a message
def message_received(client, server, message):
    try:
        message = json.loads(message)
        if message['type'] == 'fighter':
            for student in sD.studentDict:
                if sD.studentDict[student]['name'] == message['to'] or sD.studentDict[student]['name'] == message['from']:
                    for toClient in server.clients:
                        if toClient['id'] == sD.studentDict[student]['wsID']:
                            server.send_message(toClient, json.dumps(message))
                            break
        elif message['type'] == 'ttt':
            #For now, this will only forward the gamestate. We'll do validation later.
            #server.send_message(message.to, json.dumps(message))
            pass
        elif message['type'] == 'userlist':
            server.send_message(client, json.dumps(packMSG('userlist', sD.studentDict[client['address'][0]]['name'], 'server', chatUsers())))
        elif message['type'] == 'alert':
            server.send_message(client, json.dumps(packMSG('alert', sD.studentDict[client['address'][0]]['name'], 'server', 'Only the server can send alerts!')))
        elif message['type'] == 'help':
            name = sD.studentDict[client['address'][0]]['name']
            name = name.replace(" ", "")
            helpList[name] = message['content']
            playSFX("sfx_up04")
            server.send_message(client, json.dumps(packMSG('alert', sD.studentDict[client['address'][0]]['name'], 'server', 'Your help ticket was sent. Keep working on the problem while you wait!')))
        else:
            #Check for permissions
            if sD.studentDict[client['address'][0]]['perms'] > sD.settings['perms']['say']:
                messageOut = packMSG('alert', sD.studentDict[client['address'][0]]['name'], 'server', "You do not have permission to send text messages.")
                server.send_message(client, json.dumps(messageOut))
            else:
                #Checking max message length here
                if len(message['content']) > 252:
                    message['content'] = message['content'][:252]+'...'
                #Check recipients here
                if message['to'] == 'all':
                    messageOut =  packMSG('message', 'all', sD.studentDict[client['address'][0]]['name'], message['content'])
                    server.send_message_to_all(json.dumps(messageOut))
                else:
                    for student in sD.studentDict:
                        if sD.studentDict[student]['name'] == message['to'] or sD.studentDict[student]['name'] == message['from']:
                            for toClient in server.clients:
                                if toClient['id'] == sD.studentDict[student]['wsID']:
                                    messageOut =  packMSG('message', message['to'], sD.studentDict[client['address'][0]]['name'], message['content'])
                                    server.send_message(toClient, json.dumps(messageOut))
                                    break
                print("[info] " + message['from'] + " said to " + message['to'] + ": " + message['content'])
    except Exception as e:
        print("[error] " + 'Error: ' + str(e))


# ███████ ██ ███    ██  █████  ██          ██████   ██████   ██████  ████████
# ██      ██ ████   ██ ██   ██ ██          ██   ██ ██    ██ ██    ██    ██
# █████   ██ ██ ██  ██ ███████ ██          ██████  ██    ██ ██    ██    ██
# ██      ██ ██  ██ ██ ██   ██ ██          ██   ██ ██    ██ ██    ██    ██
# ██      ██ ██   ████ ██   ██ ███████     ██████   ██████   ██████     ██


#Startup stuff
sD.activePhrase = sD.ip
showString(sD.activePhrase)
if ONRPi:
    pixels.show()
if '--silent' not in str(sys.argv):
    playSFX("sfx_bootup02")

def start_flask():
    global DEBUG
    app.run(host='0.0.0.0', use_reloader=False, debug=DEBUG)

#This function activate chat and let students chat with one another.
def start_chat():
    server = WebsocketServer(WSPORT, host='0.0.0.0')
    server.set_fn_new_client(new_client)
    server.set_fn_client_left(client_left)
    server.set_fn_message_received(message_received)
    server.run_forever()

def start_IR():
    while True:
        ir.inData = ir.convertHex(ir.getBinary()) #Runs subs to get incomming hex value
        for button in range(len(ir.Buttons)):#Runs through every value in list
            if hex(ir.Buttons[button]) == ir.inData: #Checks this against incomming
                # print(ir.ButtonsNames[button]) #Prints corresponding english name for button
                if ir.ButtonsNames[button] == 'power':
                    flushUsers()
                elif ir.ButtonsNames[button] == 'func':
                    changeMode()
                elif ir.ButtonsNames[button] == 'repeat':
                    repeatMode()
                elif ir.ButtonsNames[button] == 'rewind':
                    rewindBGM()
                elif ir.ButtonsNames[button] == 'play_pause':
                    playpauseBGM()
                elif ir.ButtonsNames[button] == 'eq':
                    playSFX("sfx_up03")
                elif ir.ButtonsNames[button] == 'vol_up':
                    volBGM('up')
                elif ir.ButtonsNames[button] == 'vol_down':
                    volBGM('down')
                elif ir.ButtonsNames[button] == 'up':
                    sD.currentStep += 1
                    if sD.currentStep >= len(sD.lesson.steps):
                        sD.currentStep = len(sD.lesson.steps) - 1
                    playSFX("sfx_pickup01")
                elif ir.ButtonsNames[button] == 'down':
                    sD.currentStep -= 1
                    if sD.currentStep <= 0:
                        sD.currentStep = 0
                    playSFX("sfx_pickup01")

if __name__ == '__main__':
    chatApp = threading.Thread(target=start_chat, daemon=True)
    chatApp.start()#Starts up the chat feature
    #irApp = threading.Thread(target=start_IR, daemon=True)
    #irApp.start()#Starts up the chat feature
    # flaskApp = threading.Thread(target=start_flask)
    # flaskApp.start()
    # flaskApp.join()
    start_flask()
