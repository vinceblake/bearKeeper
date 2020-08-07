# BearKeeper
## USE AT YOUR OWN RISK
This can be generously be called an alpha release.  It seems stable when used as intended, but for the love of whatever it is that you love, make sure you have backups of your data before you let my amateur code mess with any important stuff. The most destructive action this thing is currently programmed to take is to send a note to the trash (from which it can be retrieved), but I have not tested this very extensively.

I cannot stress this enough: I AM NOT A PROFESSIONAL PROGRAMMER. I made this for myself, for fun, and it was way harder than I anticipated when I began. I hope it works for you, but seriously, use it at your own risk. Or better: don’t use it at all. Yet? Ever? I dunno.

Don’t skip the Initialization section, either. There’s a potentially dangerous process that I have not tested against a large number of notes.

You’ve been warned!

## Mission
I like Bear. It’s my favorite note taking app. I also like Android. You see the issue, I am sure.

I hate pretty much every note taking app on Android that I have tried. Google Keep™ is the one I hate the least. Although Keep is more like a board for sticky notes than a filing cabinet, I wanted something that would let me have my notes on all my devices and allow me to modify them from each. Enter BearKeeper.

## Explanation
BearKeeper is built around a SQLITE database that maintains metadata about notes in Bear and notes in Keep. Whenever BearKeeper is run, it will populate this table by first scanning the Bear database and then scanning Keep using the gkeepapi from kiwiz.

As long as notes exist in both places, BearKeeper will examine the last-updated timestamps for each and then use that information to determine if changes need to be synced from Bear to Keep or vice versa. Any note that does not yet exist in either location is treated as new and is simply created in the other space. The new note’s metadata is stored in the metaNotes table, and the process repeats.

## Initialization
You will need to rename the example_meta.db to meta.db. Or change the code to call it whatever you want.

This can’t work without a foundation. We need to know any given note’s unique identifier in Bear AND its corresponding unique identifier in Keep. Therefore, the first time this program is run, it requires an initialization process. This is what that looks like:

1. Import *all* notes from Keep into Bear.
2. Delete *all* existing notes from Keep.
3. With Keep now empty, *recreate* all notes in Keep from their copies in Bear.
	* We know all Bear IDs by default—they’re in the Bear database.
	* When a “new” note is created using the gkeepapi, we have its identifier and can store it in the metaNotes database.
	* **Note color will be preserved. Labels--as of this version--will not.**
4. After this process, we will know Bear’s unique identifier *and* Keep’s corresponding identifier for every one of our notes.

## Usage
Simply run the program whenever you want to sync your notes to both places. BearKeeper will, in order:

1. Retrieve all new notes from our Bear database and populate the metaNotes table with their information.
2. Retrieve all notes from Keep and populate the metaNotes table with their information.
3. Determine which notes only exist in one service and sync them to the other.
4. Compare timestamps for all other notes to determine where it was most recently updated. Sync changes from the more recently updated note to the less-recently updated note.

BearKeeper will ignore any notes whose most recent update came before the last time BearKeeper was run.

## Acknowledgements
[BearKeeper leverages the xcall app written by Martin Finke to create new notes in Bear.](https://github.com/robwalton/python-xcall)

[gkeepapi, written by Kai Zhong, is used to handle all interaction with Google Keep. This is an unofficial API which Google does not support or maintain, because they are the worst. Thanks Kai for making this possible.](https://github.com/kiwiz/gkeepapi)

## TO-DO
- Write code to build the database. Including a blank one for now.
- Fix labeling in Google Keep. This doesn’t function at all right now. /Bear/ with me. Ha. Ha.
- Build an automatic color-coding system for Bear Notes in Keep. e.g. this tag = this color.
- Manage note deletions. They are totally ignored for the moment.
- Manage titles / finding H1 on first line. You’ll know what I mean if you try to use this.
- Manage list conversions. Maybe. They are handled separately from regular text in Keep and I am not sure I care enough to address this.
- Handle note conflicts. These /may/ work in some fashion right now, it’s just that less-recent changes will get stomped on.
- Handle timezones better than I am currently.
