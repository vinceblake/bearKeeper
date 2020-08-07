#!/users/vince/.venv/BearWrangler/bin/python3
import gkeepapi, os, datetime, sqlite3, json, re
from subprocess import Popen, PIPE
from urllib.parse import quote
from time import mktime, localtime

# Global Variables 
home = os.path.expanduser("~")
bearDbFile = f'{home}/Library/Group Containers/9K33E3U3T4.net.shinyfrog.bear/Application Data/database.sqlite'
keepCredFile = f'{home}/.vault/gkeep'
metaDbFile = 'meta.db'
timeZoneFix = -18000 # EST timezone adjustment. See here for yours (don't use DST): https://www.epochconverter.com/timezones
now = datetime.datetime.now().timestamp()

def xcall(url): # Simple wrapper method to run xcalls
    r = Popen(['xcall.app/Contents/MacOS/xcall',
        '-url', f'"{url}"'
        ], stdout=PIPE)

    stdout = r.communicate()
    return str(stdout[0].decode('ascii')).strip().replace(" ","")

def checkForBears(): # Check to see if Bear is running and kill it if so.
    stdout = None
    r = Popen('pgrep Bear', shell=True, stdout=PIPE, stderr=PIPE)
    stdout = r.communicate()
    stdout = str(stdout[0].decode('ascii')).strip().replace(" ","")
    bears = re.findall(r"\d{4}", stdout)
    
    if bears:
        killBear()
        return True
    else:
        return False

def killBear(): # Kill the Bear process.
    r = Popen(['osascript',
        '-e', 'quit app "BEAR"'
        ], stdout=PIPE)

    stdout = r.communicate()
    return str(stdout[0].decode('ascii')).strip().replace(" ","")

def create_connection(db_file): # Establish SQLITE database connection cursor
    """ create a database connection to the SQLite database
        specified by the db_file
    :param db_file: database file
    :return: Connection or None
    """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
    except:
        print("Failed to establish connection")
        return None

    return conn

def fixBearTime(coredata_timestamp): # Fucking Macs thinking they live on different time than Unix.
    dst = localtime().tm_isdst
    if dst == 1:
        adjustment = abs(timeZoneFix)
    else:
        adjustment = abs(timeZoneFix) - 3600

    coredata_start_date = datetime.datetime(2001, 1, 1, 0, 0, 0, 0, tzinfo=None)
    coredata_start_unix = float(mktime(coredata_start_date.timetuple()))
    unix_timestamp = coredata_start_unix + coredata_timestamp - adjustment
    return unix_timestamp

def fixKeepTime(coredata_timestamp): # Google Keep ignores DST and Bear doesn't. Hence this function.
    dst = localtime().tm_isdst
    if dst == 1:
        adjustment = abs(timeZoneFix) - 3600
    else:
        adjustment = abs(timeZoneFix)

    coredata_timestamp = coredata_timestamp - adjustment
    return adjustment

def getGoogleCredsFromFile(file): # Retrieve Google credentials from file.
    with open(file, 'r') as f:
        creds = f.readlines()

    user = creds[0].rstrip()
    pwd = creds[1].rstrip()
    return [user,pwd]

def tagJoiner(tags): # Join tags together into a comma-separated string
    strTags = ""
    for tag in tags:
        strTags = strTags + f',{str(tag).replace("#","").rstrip()}'
    return strTags[1:len(strTags)]

def setKeepLabelsFromTags(keepNote,tags): # Convert tags from tagJoiner() into Keep labels: 
    for label in keepNote.labels.all():
        keepNote.labels.remove(label)

    for tag in tags.split(','):
        label = None
        label = keep.findLabel(tag)

        if hasattr(label, 'id'):
            keepNote.labels.add(label)

        else:
            label = keep.createLabel(tag)
            keepNote.labels.add(label)

    return keepNote.labels

def getNumberOfMetaTableRows(): # Get number of rows in our metaNotes table.
    meta.execute('select * from metaNotes')
    return len(meta.fetchall())

def gColor(color="white"): # Pick a Google Keep note color given a string:
    if not color or color == "white":
        return gkeepapi.node.ColorValue.White 
    elif color == "red":
        return gkeepapi.node.ColorValue.Red 
    elif color == "blue":
        return gkeepapi.node.ColorValue.Blue
    elif color == "brown":
        return gkeepapi.node.ColorValue.Brown 
    elif color == "darkblue":
        return gkeepapi.node.ColorValue.DarkBlue
    elif color == "teal":
        return gkeepapi.node.ColorValue.Teal
    elif color == "orange":
        return gkeepapi.node.ColorValue.Orange 
    elif color == "yellow":
        return gkeepapi.node.ColorValue.Yellow
    elif color == "green":
        return gkeepapi.node.ColorValue.Green 
    elif color == "pink":
        return gkeepapi.node.ColorValue.Pink
    elif color == "purple":
        return gkeepapi.node.ColorValue.Purple 
    elif color == "gray":
        return gkeepapi.node.ColorValue.Gray 
    return gkeepapi.node.ColorValue.White 

def setLastUpdated(timestamp):
    meta.execute("UPDATE metaNotes SET lastUpdated=?", (timestamp,))
    metadb.commit()

def clearProcessSourceFromMetaDB():
    meta.execute("UPDATE metaNotes SET processSource=?", (None,))
    metadb.commit()

def qualifyForProcessing(id, timestamp):
    if "-" in id:
        metaRow = meta.execute(f"SELECT * from metaNotes where bearID = ?", (id,) ).fetchone()
    elif "." in id:
        metaRow = meta.execute(f"SELECT * from metaNotes where keepID = ?", (id,) ).fetchone()

    try:
        lastUpdated = float(metaRow[14])
    except:
        lastUpdated = 0.0

    if lastUpdated <= timestamp:
        return True 

    return False

def sendBearNotesToMetaDB():
    bearNotes = bear.execute("SELECT * FROM ZSFNOTE WHERE ZARCHIVED=0").fetchall()
    for row in bearNotes:
        bearID = row[34]
        bearModTime = fixBearTime( row[24] )

        if qualifyForProcessing(bearID,bearModTime):
            print(f"{bearID} qualified for processing.")     
            bearModTime = fixBearTime( row[24] )
            bearTitle = str(row[33]).rstrip()
            bearText = str(row[32]).rstrip()

            bearTrashed = int(0)
            if row[16]:
                bearTrashed = 1
            bearArchived = int(0)
            if row[3]:
                bearArchived = 1

            row = meta.execute("SELECT * FROM metaNotes WHERE bearID=?", (bearID,)).fetchone()
            if row: # This means we need to update an existing row, rather than insert a new one.
                meta.execute(
                    "update metaNotes SET bearModTime=?, bearTitle=?, bearText=?, bearTrashed=?, bearArchived=? where bearID=?",
                    (bearModTime, bearTitle, bearText, bearTrashed, bearArchived, bearID)
                )    
                metadb.commit()

            else: # This means the note is new to us, so we have to create a new row
                meta.execute(
                "insert into metaNotes (bearID,bearModTime,bearTitle,bearText,bearTrashed,bearArchived,lastUpdated) values (?,?,?,?,?,?,?)",
                (bearID,bearModTime,bearTitle,bearText,bearTrashed,bearArchived,0)
                )
            metadb.commit()
        else:
            continue
    return 0

def sendKeepNotesToMetaDB():
    keepNotes = keep.find(archived=False, trashed=False)
    for keepNote in keepNotes:
        keepID = keepNote.id
        keepModTime = fixKeepTime( keepNote.timestamps.edited.timestamp() )
        if qualifyForProcessing(keepID,keepModTime):
            print(f"{keepID} qualified for processing.") 
            keepTitle = str(keepNote.title).rstrip()
            keepText = str(keepNote.text).rstrip()

            keepTrashed = 0
            if keepNote.trashed == True:
                keepTrashed = 1
            keepArchived = 0
            if keepNote.archived == True:
                keepArchived = 1

            keepColor = str(keepNote.color).replace("ColorValue.","").rstrip()
        
            row = meta.execute("SELECT * FROM metaNotes WHERE keepID=?", (keepID,)).fetchone()
            # Do the following if we've seen this note before (i.e. it currently exists in our metaNotes table):
            if row: 
                meta.execute(
                    "UPDATE metaNotes SET keepModTime=?, keepTitle=?, keepText=?, keepTrashed=?, keepArchived=?, keepColor=? WHERE keepID=?", 
                    (keepModTime, keepTitle, keepText, keepTrashed, keepArchived, keepColor, keepID)
                ) 
             # Otherwise, if this is a brand new note (i.e. it does not currently exist in our metaNotes table):         
            else: 
                meta.execute(
                "insert into metaNotes (keepID,keepModTime,keepTitle,keepText,keepTrashed,keepArchived,keepColor,lastUpdated) values (?,?,?,?,?,?,?,?)",
                (keepID,keepModTime,keepTitle,keepText,keepTrashed,keepArchived,keepColor,float(0.0))
                )
            
            metadb.commit()
    return 0

def sendBearNoteFromMetaToKeep(row):
    metaID = row[0]
    modTime = now
    title = str(row[5])
    text = str(row[7])
    trashed = int(row[9])
    archived = int(row[11])
    #tags = tagJoiner( re.findall(r"\#[^\s#].*", text) )
    color = str(row[13])

    keepNote = keep.createNote(title,text)
    keepID = keepNote.id 
    keepNote.color = gColor(color)

    #setKeepLabelsFromTags(keepNote, tags)

    if trashed > 0:
        keepNote.trash()
    if archived > 0:
        keepNote.archived = True
    
    meta.execute(
        "UPDATE metaNotes SET keepID=?, keepModTime=?, keepTitle=?, keepText=?, keepTrashed=?, keepArchived=?, keepColor=?, lastUpdated=? WHERE metaID=?",
        (keepID, now, title, text, trashed, archived, color, modTime, metaID)
    )
    metadb.commit()
    return keepID

def sendKeepNoteFromMetaToBear(row):
    metaID = row[0]
    modTime = now
    title = str(row[6])
    text = str(row[8])
    trashed = row[10]
    archived = row[12]
    color = row[13]

    create = f'bear://x-callback-url/create?&text={quote(text)}&open_note=no&show_window=no&timestamp=no'
    bearCall = xcall(create)
    bearID = json.loads(bearCall)['identifier']

    meta.execute(
        "UPDATE metaNotes SET bearID=?, bearModTime=?, bearTitle=?, bearText=?, bearTrashed=?, bearArchived=?, keepColor=?, lastUpdated=? where metaID=?",
        (bearID, modTime, title, text, trashed, archived, color, now, metaID)
    )
    metadb.commit()

    
    return bearID

def sendKeepNoteFromKeepToBear(keepNote):
    keepID = keepNote.id        
    title = str(keepNote.title).rstrip()
    if len(title) < 1:
        title = 'UNTITLED' #TODO: Check first line for H1 and set that as title
    text = str(keepNote.text).rstrip()
    color = str(keepNote.color).replace("ColorValue.","").lower()
    modTime = fixKeepTime( keepNote.timestamps.edited.timestamp() )

    trashed = 0
    if keepNote.trashed == True:
        trashed = 1
    archived = 0
    if keepNote.archived == True:
        archived = 1

    create = f'bear://x-callback-url/create?&text={quote(text)}&open_note=no&show_window=no&timestamp=no'
    bearCall = xcall(create)
    bearID = json.loads(bearCall)['identifier']

    columns = "bearID, keepID, bearModTime, keepModTime, bearTitle, keepTitle, bearText, keepText, bearTrashed, keepTrashed, bearArchived, keepArchived, keepColor, lastUpdated"
    meta.execute(
        f"insert into metaNotes ({columns}) values (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (bearID,keepID,modTime,modTime,title,title,text,text,trashed,trashed,archived,archived,color,now)
    )
    metadb.commit()

    newMetaRow = meta.execute(f'SELECT * FROM metaNotes WHERE bearID = "{bearID}"').fetchone()
    return newMetaRow

def syncBearNoteToKeep(row):
    keepID = row[2]
    title = row[5]
    text = row[7]
    trashed = int(row[9])
    archived = int(row[11])
    #tags = tagJoiner( re.findall(r"\#[^\s#].*", text) )
    color = str(row[13])

    keepNote = keep.get(keepID)
    keepNote.title = title 
    keepNote.text = text 
    keepNote.color = gColor(color)

    #setKeepLabelsFromTags(keepNote, tags)

    if trashed > 0:
        keepNote.trash()
    if archived > 0:
        keepNote.archived()

    meta.execute("UPDATE metaNotes SET lastUpdated=? where keepID=?", (now,keepID))
    metadb.commit()
    
def syncKeepNoteToBear(row):
    bearID = str(row[1])
    keepID = str(row[2])
    title = str(row[6])
    text = str(row[8])
    trashed = int(row[10])
    archived = int(row[12])
    color = str(row[13])

    bear.execute(
        "update ZSFNOTE set ZTITLE=?, ZSUBTITLE=?, ZTEXT=?, ZTRASHED=?, ZARCHIVED=? where ZUNIQUEIDENTIFIER=?",
        (title, text, text, trashed, archived, bearID)
    )
    beardb.commit()

    meta.execute(
        "update metaNotes set keepColor=?, lastUpdated=? where keepID=?",
        (color, now, keepID)
    )
    metadb.commit()

def syncRowFromProcessSource(row):
    metaID = row[0]
    source = row[15]

    if source == "bear":
        dest = "keep"
        title = str(row[5])
        text = str(row[7])
        trashed = int(row[9])
        archived = int(row[11])

    elif source == "keep":
        dest = "bear"
        title = str(row[6])
        text = str(row[8])
        trashed = int(row[10])
        archived = int(row[12])

    else:
        print(f"{metaID} should not be here.")
        return False

    meta.execute(
        f"update metaNotes SET {dest}Title=?, {dest}Text=?, {dest}Trashed=?, {dest}Archived=? WHERE metaID=?",
        (title, text, trashed, archived, metaID)
    )
    metadb.commit()

def processMetaNotesForSync():
    clearProcessSourceFromMetaDB()
    metaNotes = meta.execute("SELECT * FROM metaNotes").fetchall() 
    for metaNote in metaNotes:
        metaID = metaNote[0]
        lastUpdated = metaNote[14]
        source = None

        try:
            bearModTime = float(metaNote[3])
        except:
            bearModTime = 0.0

        try:
            keepModTime = float(metaNote[4])
        except:
            keepModTime = 0.0
       
        if (keepModTime < bearModTime) and (bearModTime >= lastUpdated):
            source = "bear"

        elif (keepModTime > bearModTime) and (keepModTime >= lastUpdated):
            source = "keep"

        if source:
            meta.execute(
                f"update metaNotes SET processSource=? WHERE metaID=?",
                (source, metaID)
            )
        
    metadb.commit()
    
    rows = meta.execute("SELECT * FROM metaNotes where processSource is NOT NULL").fetchall()
    for row in rows:
        syncRowFromProcessSource(row)
    return rows

def performNoteSync(notes):
    bearsAbout = 0
    for note in notes:
        if note[15] == "bear":
            if note[2]:
                syncBearNoteToKeep(note)
            else:
                sendBearNoteFromMetaToKeep(note)
                
        elif note[15] == "keep":
            if bearsAbout == 0:
                checkForBears() # This will find the Bear process and kill it. Bear can't be running when we modify its database.
                bearsAbout = 1
            if note[1]: # i.e. This note has a bearID, so it should be updated in Bear, not created.
                syncKeepNoteToBear(note)
            else: # i.e. This is a new Keep Note since last we run, so let's send it over.
                sendKeepNoteFromMetaToBear(note)

        else:
            print(f"{note[0]} is being processed and it should not be. performNoteSync() is failing.")
    
    if bearsAbout == 1:
        r = Popen(['open', '/Applications/Bear.app'])
        r.communicate()

def db_init():
    for label in keep.labels():
        keep.deleteLabel(label.id)

    for keepNote in keep.find(archived=False, trashed=False):
        sendKeepNoteFromKeepToBear(keepNote)
        keepNote.trash()

    sendBearNotesToMetaDB()
    bearNotes = meta.execute("SELECT * FROM metaNotes").fetchall()
    for row in bearNotes:
        sendBearNoteFromMetaToKeep(row)

    meta.execute(
        "UPDATE metaNotes SET bearModTime=?, keepModTime=?, lastUpdated=?",
        (now,now,now)
    )
    metadb.commit()
    setLastUpdated(now)
    keep.sync()

def db_sync():
    sendBearNotesToMetaDB()
    sendKeepNotesToMetaDB()

    notes = processMetaNotesForSync()
    performNoteSync(notes)
    
    setLastUpdated(now)
    clearProcessSourceFromMetaDB()
    keep.sync()

if __name__ == '__main__': 
    # Bear database
    beardb = create_connection(bearDbFile)
    bear = beardb.cursor()

    # Google Keep API
    keep = gkeepapi.Keep()
    keepCreds = getGoogleCredsFromFile(keepCredFile)
    keep.login(keepCreds[0], keepCreds[1])

    # Meta database
    metadb = create_connection(metaDbFile)
    meta = metadb.cursor() 

    metaRows = getNumberOfMetaTableRows()
    if metaRows < 1:
        db_init()
    else:
        db_sync()