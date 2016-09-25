import random
import os
import shelve
import sys

#from src import utils

Creatures = []
Items = []
Location_Storage = []


class Player(object):

    def __init__(self, locations, startLoc):
        self.inventory = [Fist()]
        self.score = 0
        self.visitedPlaces = {}
        self.locationStack = []
        self.location = startLoc
        self.locations = locations
        for i in self.locations:
            self.visitedPlaces[i] = False
        self.health = 100
        self.hasLight = False
        self.location.giveInfo(True, self.hasLight)

    def die(self, restart=True):
        print('GAME OVER.')
        print('Your score was {0}.'.format(self.score))
        if restart:
            self.restart('', '', True)
        sys.exit(0)

    def sayLocation(self):
        print('You are in {0}.'.format(self.location.name))

    def changeScore(self, amount):
        self.score += amount
        if amount > 0:
            print('Your score was increased by {0}.'.format(amount))
        elif amount < 0:
            print('Your score was decreased by {0}.'.format(amount * -1))

    def fight(self, baddie):
        def typingError():
            print('Since you can\'t type, you\'re forced to retreat.')
            self.changeScore(-1)
        weapon = None
        while True:
            print('What do you want to do?')
            # Enumerate strings
            numberStrings("Attack", "Retreat")
            choice = input('#')
            if choice not in ['1', '2']:
                typingError()
                return 'retreat', baddie.hp
            elif choice.startswith('2'):
                print('You cowardly run away.')
                self.changeScore(-1)
                return 'retreat', baddie.hp
            elif choice.startswith('1'):
                if weapon is None:
                    print('Choose your weapon.')
                    weapons = []
                    for item in self.inventory:
                        if isinstance(item, Weapon):
                            print('{0}: {1} power'.format(
                                item.name, item.power))
                            weapons.append(item)
                    choice = input('Weapon: ')
                    for i in weapons:
                        if choice == i.name:
                            weapon = i
                            break
                    if weapon is None:
                        typingError()
                        return 'retreat', baddie.hp
                self.health -= baddie.power
                baddie.hp -= weapon.power
                if self.health > 0 and baddie.hp > 0:
                    print('Your health is {0}.'.format(self.health))
                    print('The {0}\'s health is {1}.'.format(
                        baddie.name, baddie.hp))
                elif self.health < 1 and baddie.hp > 0:
                    print('You died.')
                    self.die()
                elif baddie.hp < 1 and self.health > 0:
                    print('The {0} has been defeated!'.format(baddie.name))
                    self.changeScore(1)
                    self.location.items += baddie.die()
                    return 'win'
                else:
                    print('Both you and the {0} died!'.format(baddie.name))
                    self.die()

    def canCarry(self, itemToTake):
        weight = itemToTake.weight
        for item in self.inventory:
            weight += item.weight
        # return True if player can carry item
        return weight <= 100

    # Command functions called in game.py

    def clrscn(self, action, noun):
        clrscn()

    def take(self, action, noun):
        def takeItem(i):
            self.location.items.remove(i)
            self.inventory.append(i)
            print('{0} taken.'.format(i.name))

        weightstring = 'You are carrying too much weight already. Try dropping something.'
        if noun == '':
            print('What do you want to take?')
        else:
            item = getItemFromName(noun, self.location.items, self)
            if item and not isinstance(item, InteractableItem) and \
                    (not self.location.dark or self.hasLight):
                if self.canCarry(item):
                    takeItem(item)
                else:
                    print(weightstring)
            elif noun == 'all':
                for i in self.location.items[:]:
                    if not isinstance(i, InteractableItem):
                        if self.canCarry(i):
                            takeItem(i)
                        else:
                            print(weightstring)
                # if len(self.location.items) > 1:
                #   takeItem(self.location.items[0])
            elif self.location.dark and not self.hasLight:
                print('There\'s no way to tell if that is here because'
                      ' it is too dark.')
            else:
                print('You can\'t pick up {0} {1}.'.format(
                    getIndefArticle(noun), noun))

    def drop(self, action, noun):
        def dropItem(i):
            self.location.items.append(i)
            self.inventory.remove(i)
            print('{} dropped.'.format(i.name))
        if noun == '':
            print('Say what you want to drop.')
        else:
            if noun == 'fist':
                print('You can\'t drop your own fist, silly!')
                return
            item = getItemFromName(noun, self.inventory, self)
            if item:
                dropItem(item)
            elif noun == 'all':
                for i in self.inventory[:]:
                    if i.name != 'fist':
                        dropItem(i)
            else:
                print('You do not have a {} to drop.'.format(noun))

    def look(self, action, noun):
        if self.hasLight and not inInventory(Lantern, self):
            self.hasLight = False
        if noun == '' or noun == 'around':
            self.location.giveInfo(True, self.hasLight)
        else:
            item = getItemFromName(noun, self.inventory, self)
            if item:
                if item.name == 'sword':
                    # Make sword glow if an enemy is in an adjacent room
                    glowing = False
                    for i in self.location.creatures:
                        if isinstance(i, Baddie):
                            item.examine(True)
                            return
                    if not glowing:
                        for exit in self.location.exits:
                            for creature in self.location.exits[exit].creatures:
                                if isinstance(creature, Baddie):
                                    item.examine(True)
                                    return
                    if not glowing:
                        item.examine(False)
                else:
                    item.examine()
            else:
                print('You do not have {0}'.format(noun))

    def go(self, action, noun='', Location=None, history=True):
        def fightCheck():
            if len(self.location.creatures) > 0:
                for i in self.location.creatures[:]:
                    if isinstance(i, Baddie):
                        result = self.fight(i)
                        if result[0] == 'retreat':
                            if len(result) > 1:
                               i.hp = result[1]
                            self.back('', '')
                        else:
                            self.location.creatures.remove(i)
        if self.hasLight and not inInventory(Lantern, self):
            self.hasLight = False 
        if Location is not None:
            locToGoTo = Location
            isLoc = True
        else:
            isDirection = False
            isLoc = False
            try:
                locToGoTo = self.location.exits[noun]
            except KeyError:
                pass
            for direction in ['north', 'south', 'east', 'west', 'up',
                              'down', 'northwest', 'northeast',
                              'southwest', 'southeast']:
                if direction == noun:
                    isDirection = True
                    break
                elif direction in self.location.exits:
                    if self.location.exits[direction].name.lower() == noun:
                        locToGoTo = self.location.exits[direction]
                        break
            if not isDirection and not isLoc and action != 'say':
                print('You must specify a valid direction.')
                return
            elif action == 'say':
                # Get right Location from list called locations
                for i in self.locations:
                    if i.name == 'Home':
                        locToGoTo = i
                        break
            elif noun in self.location.exits:
                # Get right Location from list called locations
                loc = None
                # loc = self.locations[self.index(
                # self.location.exits[noun])]
                for i in self.locations:
                    if self.location.exits[noun] == i:
                        loc = i
                if loc:
                    for i in self.locations:
                        if i == loc:
                            locToGoTo = i
                            break
            elif isLoc:
                pass
            else:
                print('There is no exit in that direction.')
                return
        if locToGoTo is not None:
            if self.location.history and history:
                self.locationStack.append(self.location)
            self.location = locToGoTo
            if not self.visitedPlaces[self.location]:
                self.location.giveInfo(True, self.hasLight)
                self.visitedPlaces[self.location] = True
            else:
                self.location.giveInfo(False, self.hasLight)
            if (not self.location.dark) or (self.hasLight):
                fightCheck()
        else:
            print('Something went wrong.')

    def back(self, action, noun):
        try:
            self.go('', '', Location=self.locationStack[-1])
            self.locationStack.pop()
        except IndexError:
            print("There is not a previous location you can go to.")

    def help(self, action, noun):
        print('I can only understand what you say if you first type an'
              ' action and then a noun (if necessary).', end='')
        print(' My vocabulary is limited. If one word doesn\'t work,'
              ' try a synonym. If you get stuck, check the documentati'
              'on.')

    def say(self, action, noun):
        if noun == 'xyzzy':
            if inInventory(Mirror, self):
                if self.location.name == 'Start':
                    self.changeScore(1)
                print('You vanished and reappeared in your house.\n')
                self.go(action, noun)
            else:
                print('There was a flash of light...and your score was'
                      ' mysteriously lowered by one.')
                self.score -= 1
        else:
            print('You said "{}" but nothing happened.'.format(noun))

    def quit(self, action, noun):
        resp = input('Are you sure you want to quit? Your progress '
                     'will be saved. [Y/n] ')
        if resp.lower().startswith('y') or resp.strip() == '':
            save = shelve.open('pag_save')
            save['player'] = self
            save['Creatures'] = Creatures
            save['locations'] = self.locations
            save['Items'] = Items
            save.close()
            self.die(False)
        else:
            print('Cancelled.')

    def restart(self, action, noun, force=False):
        def reset():
            for i in os.listdir():
                    if i.startswith('pag_save'):
                        os.remove(i)
                        
        if not force:
            resp = input('Are you sure you want to restart the game? [y/N] ')
            if resp.lower().startswith('y'):
                reset()
                print('Now run the game again.')
        else:
            reset()
        sys.exit(0)

    def show(self, action, noun):
        # TODO: Remove reduntant ifs
        if noun == 'inventory':
            if len(self.inventory) > 0:
                print('Inventory:')
                for item in self.inventory:
                    if isinstance(item, Food):
                        print('{0}: Restores {1} health,'.format(
                            item.name, item.health), end=' ')
                    elif isinstance(item, Weapon):
                        print('{0}: Deals {1} damage,'.format(
                            item.name, item.power), end=' ')
                    else:
                        print(item.name, end=': ')
                    print('weighs {} pounds.'.format(item.weight))
            else:
                print('There are no items in your inventory.')
        elif noun == 'location':
            print('You are at ' + self.location.name)
        elif noun == 'score':
            print('Your score is {}.'.format(self.score))
        elif noun == 'health':
            print('You have {} health.'.format(self.health))
        elif noun == 'exits':
            # TODO: Refactor into function
            self.location.displayExits()
        else:
            print('This isn\'t something I can show you.')

    def use(self, action, noun):
        if noun == 'magic mirror':
            hasMirror = False
            for item in self.inventory:
                if isinstance(item, Mirror):
                    hasMirror = True
                    break
            if hasMirror:
                print('The mirror exploded. A large shard of glass hit'
                      ' you in the face.')
                self.die()

    def open(self, action, noun):
        chest = None
        for i in self.location.items:
            if isinstance(i, Chest):
                chest = i
                break
        if chest:
            items = chest.open()
            self.location.items += items

    def hit(self, action, noun):
        chest = None
        for i in self.location.items:
            if isinstance(i, Chest):
                chest = i
                break
        if chest:
            for i in self.inventory:
                stick = True
                if isinstance(i, Stick):
                    stick = True
                    break
            if stick:
                print('You smashed the lock off the chest.')
                chest.locked = False
            else:
                print('You have nothing to break the chest with.')
        else:
            print('Hitting doesn\'t help.')

    def eat(self, action, noun):
        item = None
        for i in self.inventory:
            if i.name == noun:
                item = i
        if item:
            if isinstance(item, Food):
                print('You ate the {0} and gained {1} health.'.format(
                    item.name, item.health))
                self.health += item.health
                self.inventory.remove(item)
            else:
                print('Sorry, that isn\'t food.')
        else:
            print('You don\'t have that.')

    def light(self, action, noun):
        if inInventory(Lantern, self) and not self.hasLight:
            print('Your lantern bursts in green flame that illuminates'
                  ' the room.')
            self.hasLight = True
            if self.location.dark:
                # history=False so the same location isn't saved back into self.locationStack
                self.go('go', Location=self.location, history=False)
        elif inInventory(Lantern, self):
            print('Your light is already lit.')
        else:
            print('You need a light source!')


class Creature(object):
    ''' Supply a name, the creature's health, a description, and
        the items it drops. Set dropItems to a dict with the
        format {item: drop chance percentage}
    '''
    def __init__(self, name, hp, description, dropItems={}):
        self.name = name
        self.description = description
        self.hp = hp
        self.dropItems = dropItems
        Creatures.append(self)

    def describe(self):
        assert self.description != '', 'There must be a description.'
        print(self.description)

    def die(self):
        # Run when creature is killed
        itemsToDrop = []
        if len(self.dropItems) > 0:
            for i in self.dropItems:
                randomResult = random.randint(0, 100)
                if randomResult <= self.dropItems[i] and randomResult > 0:
                    itemsToDrop.append(i)
        if len(itemsToDrop) > 0:
            print('The {0} dropped {1} on its death.'.format(self.name, ', '.join([i.name for i in itemsToDrop])))
        return itemsToDrop


class Snail(Creature):

    def __init__(self):
        super().__init__(name='snail',
                         hp=2,
                         description='There is a snail on the ground.')


class Baddie(Creature):

    def __init__(self, name, hp, description, power, dropItems={}):
        super().__init__(name, hp, description, dropItems)
        assert type(power) == int or type(power) == float
        self.power = power


class Orc(Baddie):

    def __init__(self):
        super().__init__(name='orc',
                         hp=50,
                         description='There is an orc in '
                                     'the room.',
                         power=random.randint(20, 50))


class Ghost(Baddie):

    def __init__(self):
        super().__init__(name='ghost',
                         hp=99999999,
                         description='Wooooo',
                         power=0.01)


class GiantSpider(Baddie):

    def __init__(self):
        super().__init__(name='giant spider',
                         hp=500,
                         description='The spider is large and ugly.',
                         power=15,
                         dropItems={ToiletPaper(): 1})


class Bear(Baddie):

    def __init__(self):
        super().__init__(name='bear',
                         hp=200,
                         description='The bear growls at you.',
                         power=30)


class Item(object):
    """ Class used to instantinate Items
        It is the parent class of:
        - InteractableItem
        - Weapon

        Attributes Include:
        - A name (String)
        - A description (String)
        - A local description (String)
          - Used when 'look'ing
        - And a weight

        Methods Include:
        - player.examine()
          - Prints the description of object
    """

    def __init__(self, name, description, locDescription, weight):
        self.name = name
        self.description = description
        self.locDescription = locDescription
        self.weight = weight
        Items.append(self)

    def examine(self):
        print(self.description)


class InteractableItem(Item):
    """ Class used to instantiate an Item a player can
        interact with (like kicking)

        Attributes Include:
        - A name (String)
        - A description (String)
        - A local description (String)
          - Used when 'look'ing
        - And a weight
    """
    def __init__(self, name, description, locDescription, weight):
        super().__init__(name, description, locDescription, weight)


class Chest(InteractableItem):

    def __init__(self, items, locked):
        super().__init__(name='chest',
                         description='You shouldn\'t see this.',
                         locDescription='A treasure chest is on the ground.',
                         weight=100)
        assert type(items) == list
        self.items = items
        self.locked = locked

    def open(self):
        if self.locked:
            print('The chest cannot be opened because it it locked.')
            return []
        else:
            print('The chest is empty now.')
            for item in self.items:
                print(item.locDescription)
            backupItems = self.items[:]
            self.items = []
            return backupItems


class Weapon(Item):

    def __init__(self, name, description, locDescription, weight, power):
        super().__init__(name, description, locDescription, weight)
        assert type(power) == int
        self.power = power


class Sword(Weapon):

    def __init__(self):
        super().__init__(name='sword',
                         description='The sword is small and has an el'
                         'vish look to it.',
                         locDescription='There is a small sword here.',
                         weight=75,
                         power=random.randint(90, 150))

    def examine(self, glowing):
        print(self.description, end='')
        if glowing:
            print(' It is glowing light blue.')
        else:
            print()


class Fist(Weapon):

    def __init__(self):
        super().__init__(name='fist',
                         description='Your fist looks puny, but it\'s'
                         ' better than no weapon.',
                         locDescription='There is a bug if you are '
                         'reading this.',
                         weight=0,
                         power=10)


class Mirror(Item):

    def __init__(self):
        super().__init__(name='magic mirror',
                         description='The mirror is round and you can '
                         'see your reflection clearly. Under the glass'
                         ' is an inscription that says "XYZZY."',
                         locDescription='There is a small mirror lying'
                         ' on the ground.',
                         weight=2)


class ToiletPaper(Item):

    def __init__(self):
        super().__init__(name='toilet paper',
                         description='The toilet paper is labeled "X-t'
                         'raSoft.',
                         locDescription='A roll of toilet paper is in '
                         'the room.',
                         weight=1)


class Stick(Item):

    def __init__(self):
        super().__init__(name='stick',
                         description='The stick is long and thick. It '
                         'looks like it would be perfect '
                         'for bashing things with.',
                         locDescription='There is a random stick on '
                         'the ground.',
                         weight=3)


class Paper(Item):

    def __init__(self, text=''):
        super().__init__(name='paper',
                         description=text,
                         locDescription='On a table is a paper labeled'
                                        ' NOTICE.',
                         weight=1)


class Coconuts(Item):

    def __init__(self):
        super().__init__(name='coconut halves',
                         description='The coconuts make a noise like '
                                     'horse hooves when banged together.',
                         locDescription='Also on the table are two coc'
                                     'onut halves that look like they '
                                     'probably were carried here by a '
                                     'swallow.',
                         weight=2)


class Lantern(Item):

    def __init__(self):
        super().__init__(name='lantern',
                         description='The lantern is black and is powered'
                         ' by an unknown source.',
                         locDescription='There is a lantern here.',
                         weight=5)


class Food(Item):

    def __init__(self, name, description, locDescription, weight, health):
        super().__init__(name, description, locDescription, weight)
        self.health = health


class HealthPot(Food):

    def __init__(self):
        super().__init__(name='health potion',
                         description='The potion looks disgusting but '
                                     'is probably good for you.',
                         locDescription='There is a health potion here.',
                         weight=2,
                         health=100)


class Bread(Food):

    def __init__(self):
        super().__init__(name='bread',
                         description='The bread is slightly stale but '
                         'looks wholesome.',
                         locDescription='There is a loaf of bread.',
                         weight=1,
                         health=30)
#from src.classes import *

Location_Storage = []


class Location(object):
    """ Class used to instantiate objects

        Attributes Include:
         - A name (String)
         - Any items (List)
         - Any creatures (List)
         - Any exits (Dict)
         - A description (String)
         - If the player can use 'back' to return (Bool)
         - If room name should be shown when exiting (Bool)
         - And if it's dark (Bool)
    """
    def __init__(self, name, items, creatures, exits={},
                 description='', history=True, showNameWhenExit=False,
                 dark=False):
        # exit needs to be a dict with keys north, south, east, west,
        # up, down
        assert type(items) == list
        assert (type(exits) == dict or exits is None)
        for i in exits:
            assert isinstance(exits[i], Location)
            assert i in ['north', 'south', 'east', 'west', 'up', 'down',
                         'northwest', 'northeast', 'southwest', 'southeast']
        self.name = name
        self.items = items
        self.creatures = creatures
        self.description = description
        Location_Storage.append(self)
        self.exits = exits
        self.history = history
        self.showNameWhenExit = showNameWhenExit
        self.dark = dark

    def giveInfo(self, fullInfo, light):
        assert self.description != '', 'There must be a description.'
        if self.dark and not light:
            print('It is too dark to see anything. However, you are '
                  'not likely to be eaten by a grue. What do you think'
                  ' this is, Zork?')
            return
        elif fullInfo:
            print(self.description)
            print()
            # directions = ['north', 'south', 'east', 'west', 'up', 'down']
            self.displayExits()
        else:
            print('You are in {}.'.format(self.name))
        print()

        Entity_Stack = []
        # TODO: Refactor
        for item in self.items:
            Entity_Stack.append(item)
            if item.locDescription != '':
                print(item.locDescription)
            else:
                if len(Entity_Stack) > 1:
                    if Entity_Stack[-1].name == item.name:
                        print('There are {0} {1}s'.format(len(Entity_Stack),
                            item.name))
                else:
                    print('There is {0} {1}'.format(
                        getIndefArticle(item.name), item.name))
        if len(self.items) > 0:
            print()
        Entity_Stack = []
        if len(self.creatures) > 0:
            for creature in self.creatures:
                Entity_Stack.append(creature)
            if len(Entity_Stack) > 1:
                if Entity_Stack[-1].name == creature.name:
                    print('There are {0} {1}s here'.format(len(Entity_Stack),
                        creature.name))
            else:
                print('There is {0} {1} here.'.format(
                    getIndefArticle(creature.name), creature.name))

    def displayExits(self):
        for i in self.exits:
            if self.exits[i].showNameWhenExit:
                if i == 'up' or i == 'down':
                    print('{} is {}.'.format(self.exits[i].name, i))
                else:
                    print('{} is to the {}.'.format(self.exits[i].name, i))
            else:
                print('There is an exit {0}.'.format(i))
        if len(self.exits) == 0:
            print('There does not appear to be an exit.')


class BlackPit(Location):

    def __init__(self):
        super().__init__(name='A mountain of gold and jewels',
                         items=[],
                         creatures=[],
                         exits={},
                         description='You are in a dank, dirty pit. Yo'
                                     'u don\'t know why you are here i'
                                     'nstead of being on a mountain of'
                                     ' gold and jewels.',
                         showNameWhenExit=True,
                         dark=True)
        self.firstTime = True

    def giveInfo(self, fullInfo, light):
        if self.firstTime:
            print('You run towards the amazing riches...without notici'
                  'ng the giant hole at your feet.')
            print()
            self.name = 'Black Pit'
            self.firstTime = False
            super().giveInfo(True, light)
        else:
            super().giveInfo(fullInfo, light)


class DarkTunnel(Location):

    def __init__(self):
        super().__init__(name='Dark Tunnel',
                         items=[],
                         creatures=[Orc(), Orc(), Orc(), Orc()],
                         exits={},
                         description='You are in a featureless dark tunnel.',
                         showNameWhenExit=False,
                         dark=True)


bathroom = Location('Bathroom', [ToiletPaper()], [], showNameWhenExit=True)
bathroom.description = 'There is a toilet and a sink here. They seem'\
                       ' out of place since this is 600 B.C.'
home = Location('Home', [Paper(), Lantern()], [],
                showNameWhenExit=True)
home.items[0].description = '''NOTICE:
These lands have recently become infested with the servants of evil.
Currently, the main problem is the Legendary Dragon of Nogard (the LDN),
a very powerful lizard that threatens to destroy everything we live for.
It would be greatly appreciated if you would help exterminate the
creatures currently endangering the world. There may be some reward to
anyone who defeats the Legendary Dragon of Nogard that has been ravaging
the nation.
We have left a weapon for you in a nearby chest that might be locked in
a chest. You may have to break it open. We really didn't plan this very well.'''
home.description = 'You are in a familiar cabin made out of logs. '\
                   'There is a pleasantly warm fire in the fireplace '\
                   'and a comfortable-looking armchair beside it.'
start = Location('Start', [Mirror()], [], history=False)
start.description = 'You are in a small room with concrete walls and '\
                    'no windows.'
closet = Location('Closet', [Stick()], [], showNameWhenExit=True)
closet.description = 'You are in a closet that is full of cobwebs.'
attic = Location('Attic', [Bread(), HealthPot()], [GiantSpider()],
                 showNameWhenExit=True, dark=True)
attic.description = 'The attic has been obviously unused for many year'\
                    's. There are large spiderwebs everywhere.'
backyard = Location('Backyard', [], [Snail()])
backyard.description = 'You are in the back yard of your house.'
frontyard = Location('Front Yard', [Chest([Sword()], True)], [])
frontyard.description = 'You are in your front yard.'
homenorth = Location('North of Home', [], [], showNameWhenExit=False)
homenorth.description = 'You are at the side of your house.'
homesouth = Location('South of Home', [], [], showNameWhenExit=False)
homesouth.description = 'You are at a side of your house with a window visible.'
creepyforest = Location('Creepy forest', [], [Ghost()], showNameWhenExit=True)
creepyforest.description = 'You are in a spooky forest.'
forest = Location('Forest', [], [Bear()], showNameWhenExit=True)
forest.description = 'You are in a forest. There is a sign that says '\
                     '"This is not the spooky forest of the East. Stay'\
                     ' away from there!"'
blackpit = BlackPit()
dtn = DarkTunnel()
dts = DarkTunnel()
deadend = Location(
    'Dead End', [], [], showNameWhenExit=True)
deadend.description = 'You are at a dead end.'
home.exits = {'north': bathroom, 'south': closet, 'east': backyard,
              'west': frontyard, 'up': attic}
bathroom.exits = {'south': home}
closet.exits = {'north': home}
attic.exits = {'down': home}
backyard.exits = {'west': home, 'east': creepyforest,
                  'northwest': homenorth, 'southwest': homesouth}
creepyforest.exits = {'west': backyard}
frontyard.exits = {'east': home, 'west': forest, 'northeast': homesouth,
                   'southeast': homesouth}
forest.exits = {'east': frontyard}
homenorth.exits = {'southwest': frontyard, 'southeast': backyard}
homesouth.exits = {'northwest': frontyard, 'northeast': backyard,
                   'south': blackpit}
blackpit.exits = {'north': dtn, 'south': dts}
dtn.exits = {'south': blackpit}
dts.exits = {'north': blackpit, 'south': deadend}
deadend.exits = {'north': dts}
#from src.words import verbs, nouns, extras, directions

# Input: Command you want parsed.
# Output/Return: List of parsed command.
def parseCommand(command):
    command = command.lower()
    # remove extra words
    splitCmd = command.split(' ')
    removing = []
    for word in splitCmd:
        if word in extras:
            removing.append(word)
    for word in removing:
        splitCmd.remove(word)
    command = ' '.join(splitCmd)
    parsedCommand = []
    # command must start with a verb
    noNoun = False
    verb = ''
    typedVerb = ''
    for i in verbs:
        if command.startswith(i + ' ') or command.strip() == i:
            verb = i
            typedVerb = i
        if command.strip() == i:
            noNoun = True
        else:
            for syn in verbs[i]:
                if command.startswith(syn + ' ') or (
                   command.strip() == syn):
                    verb = i
                    typedVerb = syn
                if command.strip() == syn:
                    noNoun = True
    if verb != '':
        parsedCommand.append(verb)
    else:
        # See if command is only a direction
        for i in directions:
            if command.strip() == i:
                # Return Verb, Noun
                return [None, i]
            else:
                for syn in directions[i]:
                    if command.strip() == syn:
                        return [None, i]
        print('What?')
        return
    # next is a noun
    noun = ''
    restOfCommand = ''
    if not noNoun:
        if len(command) > len(typedVerb) + 1:
            restOfCommand = command.split(typedVerb + ' ')[1]
            for i in {**nouns, **directions}:
                if restOfCommand == i:
                    noun = i
                else:
                    for syn in {**nouns, **directions}[i]:
                        if restOfCommand == syn:
                            noun = i
            if noun != '':
                parsedCommand.append(noun)
            else:
                print('I don\'t understand the noun "{0}."'.format(
                                                         restOfCommand))
                return
    return parsedCommand
import os

vowels = 'a e i o u'.split(' ')
consonants = 'b c d f g h j k l m n p q r s t v w x y z 1 2 3 4 \
                5 6 7 8 9 0'.split(' ')


def inInventory(itemClass, player):
    for item in player.inventory:
        if isinstance(item, itemClass):
            return True
    return False


def getItemFromName(itemName, itemList, player):
    for item in itemList:
        if itemName == item.name:
            return item
    return False


def getIndefArticle(noun):
    if noun[0] in vowels:
        return 'an'
    elif noun[0] in consonants:
        return 'a'


def clrscn():
    os.system("cls" if os.name == "nt" else "clear")


def numberStrings(*strings):
    for number, string in enumerate(strings):
        number += 1
        print(number, string)
    return

import os


# Input: File Name
# Output: Dict of type {Word: [Synonym, Synonym]}
def getWordList(filepath):
    if type(filepath) == str:
        txt = filepath.split('\n')
    else:
        txt = open(filepath).read().strip().split('\n')
    cInText = False
    for i in txt:
        if ':' in i:
            cInText = True
    if cInText:
        for line in txt:
            if ':' not in line:
                txt[txt.index(line)] = line + ':'
        words = {}
        for line in txt:
            index = line.split(':')[0]
            words[index] = line.split(':')[1].split(',')
            for syn in words[index]:
                if syn == '':
                    words[index].remove(syn)
    else:
        words = []
        for word in txt:
            words.append(word.strip())
    return words


verbs = getWordList('''take:pick up,grab
look:examine,see,read
attack:fight,confront,battle,engage
use
eat
jump:leap,hop
help:?
break:smash
quit:exit
say:speak
drop
go:move,travel
back:previous,prev,b
show:display
open
hit:strike,break
eat:consume,drink
light
restart:reset

clrscn:clear
''')
nouns = getWordList('''wand:staff,rod
sword:blade
monster:beast
magic mirror:mirror
around
xyzzy
it
the
inventory:items
location:current location,position
score:points
toilet paper:toilet tissue,toilet paper roll
fist
closet
bathroom
home:house
yard
stick
snail
ghost
chest:treasure chest,box
bread:loaf of bread
health
paper:notice,pamphlet,letter
lantern:lamp
all:everything
health potion:health pot,potion
coconut halves:coconuts
exits
''')
extras = getWordList('''the
that
this
those
in
out
at
into
to
''')
directions = getWordList('''up:u
down:d
west:w
north:n
south:s
east:e
southwest:sw
southeast:se
northwest:nw
northeast:ne
''')
#!/usr/bin/env python3.5
import os
import shelve
import sys
if os.name is not "nt":
    import readline

assert sys.version_info >= (3, 5), 'You must use at least Python 3.5.'

# Change directory to directory that includes play.py
os.chdir(os.path.dirname(os.path.abspath(__file__)))
# Below removes the save file for devel purposes
# os.system("rm save.db")

#from src import parser
#from src import locations
#from src import classes
#from src import utils


def main():
    """ Main Game Loop. """
    clrscn()

    sfExists = False
    for i in os.listdir():
        if i.startswith('pag_save'):
            sfExists = True
            break
    if sfExists:
        save = shelve.open('pag_save')
        player = save['player']
        Locations = save['locations']
        save.close()
        player.locations = Locations
        for i in Locations:
            player.visitedPlaces[i] = False
        player.location.giveInfo(True, player.hasLight)
    else:
        player = Player(Location_Storage, start)
    previousNoun = ''
    turns = 0
    darkTurn = 0
    # Main game loop
    while True:
        try:
            command = parseCommand(input('> '))
            if command is not None:
                action = command[0]
                if len(command) >= 2:
                    noun = command[1]
                else:
                    noun = ''
                if action is None and noun != '':
                    action = 'go'
                if previousNoun != '' and noun == 'it':
                    noun = previousNoun
                # Where game executes result.
                try:
                    # Player stuff happens here
                    # Ex: getattr(player, "go")(action, noun) -> player.go(action, noun)
                    commandResult = getattr(player, action)(action, noun)
                except AttributeError:
                    print('You can\'t do that here.')

                if noun != '':
                    previousNoun = noun
                else:
                    previousNoun = ''
                if player.location.dark and not player.hasLight:
                    if darkTurn < turns:
                        print('A grue magically appeared. However, since '
                              'this isn\'t Zork, the grue didn\'t eat you;'
                              ' it just killed you instead. So that\'s alr'
                              'ight.')
                        player.die()
                    else:
                        darkTurn = turns
                turns += 1
                if not player.location.dark or player.hasLight:
                    darkTurn = turns
        except KeyboardInterrupt:
            player.quit('', '')

# Run.
if __name__ == '__main__':
    main()