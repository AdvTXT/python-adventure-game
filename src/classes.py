"""Contains most classes used in the game."""

import random
import os
import shelve
import sys

from src import utils

Creatures = []
Items = []
Location_Storage = []


class Player(object):
    """
    The class for everything about the player.
    
    All public methods either return True or False. This value tells the game
    whether the command should increase the number of moves the player has
    taken.
    """
    def __init__(self, locations, location):
        self.inventory = [Fist()]
        self.score = 0
        self.visitedPlaces = {}
        self.locationStack = []
        self.location = location
        self.locations = locations
        for i in self.locations:
            self.visitedPlaces[i] = False
        self.health = 100
        self.hasLight = False
        self.location.giveInfo(True, self.hasLight)
        self.moves = 0

    def __str__(self):
        inventory = '\n'.join(['\t' + item.name for item in self.inventory])
        return f"You are in {self.location.name}.\n" + \
               f"You have {self.health} health points.\n" + \
               f"You have a score of {self.score} points.\n" + \
               "Inventory:\n" + \
               f"{inventory}"

    # Non-public class methods

    def _die(self, restart=True):
        print('GAME OVER.')
        print(f'Your score was {self.score}.')
        print(f'You used {self.moves} moves.')
        if restart:
            self.restart('', '', True)
        sys.exit(0)

    def _changeScore(self, amount):
        self.score += amount
        if amount > 0:
            print(f'Your score was increased by {amount}.')
        elif amount < 0:
            print(f'Your score was decreased by {amount * -1}.')

    def _fight(self, baddie):
        def typingError():
            print('Since you can\'t type, you\'re forced to retreat.')
            self._changeScore(-1)
        weapon = None
        while True:
            print('What do you want to do?')
            # Enumerate strings
            utils.numberStrings("Attack", "Retreat")
            choice = input('#')
            if choice not in ['1', '2']:
                typingError()
                return 'retreat', baddie.hp
            elif choice.startswith('2'):
                print('You cowardly run away.')
                self._changeScore(-1)
                return 'retreat', baddie.hp
            elif choice.startswith('1'):
                if weapon is None:
                    print('Choose your weapon.')
                    weapons = [i for i in self.inventory if isinstance(i, Weapon)]
                    for i in weapons:
                        print(f'{i.name}: {i.power} power')
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
                    print(f'Your health is {self.health}.')
                    print(f'The {baddie.name}\'s health is {baddie.hp}.')
                elif self.health < 1 and baddie.hp > 0:
                    print('You died.')
                    self._die()
                elif baddie.hp < 1 and self.health > 0:
                    print(f'The {baddie.name} has been defeated!')
                    self._changeScore(1)
                    self.location.items += baddie.die()
                    return 'win'
                else:
                    print(f'Both you and the {baddie.name} died!')
                    self._die()

    def _canCarry(self, itemToTake):
        weight = itemToTake.weight
        for item in self.inventory:
            weight += item.weight
        # return True if player can carry item
        return weight <= 100

    # Functions callable by the player in-game

    def clrscn(self, action, noun):
        utils.clrscn()
        return False

    def take(self, action, noun):
        def takeItem(i):
            self.location.items.remove(i)
            self.inventory.append(i)
            print(f'{i.name} taken.')

        weightstring = 'You are carrying too much weight already. Try dropping something.'
        if noun == '':
            print('What do you want to take?')
        else:
            item = utils.getItemFromName(noun, self.location.items, self)
            if item and not isinstance(item, InteractableItem) and \
                    (not self.location.dark or self.hasLight):
                if self._canCarry(item):
                    takeItem(item)
                    return True
                else:
                    print(weightstring)
            elif noun == 'all':
                for i in self.location.items[:]:
                    if not isinstance(i, InteractableItem):
                        if self._canCarry(i):
                            takeItem(i)
                            return True
                        else:
                            print(weightstring)
                # if len(self.location.items) > 1:
                #   takeItem(self.location.items[0])
            elif self.location.dark and not self.hasLight:
                print('There\'s no way to tell if that is here because'
                      ' it is too dark.')
            else:
                print(f'You can\'t pick up {utils.getIndefArticle(noun)} {noun}.')
        return False

    def drop(self, action, noun):
        def dropItem(i):
            self.location.items.append(i)
            self.inventory.remove(i)
            print(f'{i.name} dropped.')
        if noun == '':
            print('Say what you want to drop.')
        else:
            if noun == 'fist':
                print('You can\'t drop your own fist, silly!')
            item = utils.getItemFromName(noun, self.inventory, self)
            if item:
                dropItem(item)
                return True
            elif noun == 'all':
                for i in self.inventory[:]:
                    if i.name != 'fist':
                        dropItem(i)
                        return True
            else:
                print(f'You do not have a {noun} to drop.')
        return False

    def look(self, action, noun):
        """Display information about the current location or an item."""
        # Disable light if a lantern is not in the inventory
        if self.hasLight and not utils.inInventory(Lantern, self):
            self.hasLight = False
        if noun == '' or noun == 'around':
            self.location.giveInfo(True, self.hasLight)
        else:
            item = utils.getItemFromName(noun, self.inventory, self)
            if item:
                if item.name == 'sword':
                    # Make sword glow if an enemy is in an adjacent room
                    glowing = False
                    for i in self.location.creatures:
                        if isinstance(i, Baddie):
                            item.examine(True)
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
                print(f'You do not have {noun}')
                return False
        return True

    def go(self, action, noun='', Location=None, history=True):
        def fightCheck():
            if len(self.location.creatures) > 0:
                for i in self.location.creatures[:]:
                    if isinstance(i, Baddie):
                        result = self._fight(i)
                        if result[0] == 'retreat':
                            if len(result) > 1:
                               i.hp = result[1]
                            self.back('', '')
                        else:
                            self.location.creatures.remove(i)
        if self.hasLight and not utils.inInventory(Lantern, self):
            self.hasLight = False
        if Location is not None:
            destination = Location
            isLoc = True
        else:
            isDirection = False
            isLoc = False
            try:
                destination = self.location.exits[noun]
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
                        destination = self.location.exits[direction]
                        break
            if not isDirection and not isLoc and action != 'say':
                print('You must specify a valid direction.')
                return
            elif action == 'say':
                # Get right Location from list called locations
                for i in self.locations:
                    if i.name == 'Home':
                        destination = i
                        break
            elif noun in self.location.exits:
                # Get right Location from list called locations
                loc = None
                # loc = self.locations[self.locations.index(
                # self.location.exits[noun])]
                for i in self.locations:
                    if self.location.exits[noun] == i:
                        loc = i
                if loc:
                    for i in self.locations:
                        if i == loc:
                            destination = i
                            break
            elif isLoc:
                pass
            else:
                print('There is no exit in that direction.')
                return False
        if destination is not None:
            if self.location.history and history:
                self.locationStack.append(self.location)
            self.location = destination
            if not self.visitedPlaces[self.location]:
                self.location.giveInfo(True, self.hasLight)
                self.visitedPlaces[self.location] = True
            else:
                self.location.giveInfo(False, self.hasLight)
            if (not self.location.dark) or (self.hasLight):
                fightCheck()
        else:
            print('Something went wrong.')
            return False
        return True

    def back(self, action, noun):
        try:
            self.go('', '', Location=self.locationStack[-1])
            self.locationStack.pop()
        except IndexError:
            print("There is not a previous location you can go to.")
            return False
        return True

    def help(self, action, noun):
        print('I can only understand what you say if you first type an action \
                and then a noun (if necessary). My vocabulary is limited. If \
                one word doesn\'t work, try a synonym. If you get stuck, check\
                 the documentation.')
        return False

    def say(self, action, noun):
        if noun == 'xyzzy':
            if utils.inInventory(Mirror, self):
                if self.location.name == 'Start':
                    self._changeScore(1)
                print('You vanished and reappeared in your house.\n')
                self.go(action, noun)
            else:
                print('There was a flash of light...and your score was'
                      ' mysteriously lowered by one.')
                self.score -= 1
        else:
            print(f'You said "{noun}" but nothing happened.')
            return False
        return True

    def quit(self, action, noun):
        """Save progress and exit the game. Run on KeyboardInterrupt."""
        resp = input('Are you sure you want to quit? Your progress '
                     'will be saved. [Y/n] ')
        if resp.lower().startswith('y') or resp.strip() == '':
            save = shelve.open('save')
            save['player'] = self
            save['Creatures'] = Creatures
            save['locations'] = self.locations
            save['Items'] = Items
            save.close()
            self._die(False)
        else:
            print('Cancelled.')
        return False

    def restart(self, action, noun, force=False):
        """Deletes the save file."""
        def reset():
            for i in os.listdir():
                    if i.startswith('save'):
                        os.remove(i)

        if not force:
            resp = input('Are you sure you want to restart the game? [y/N] ')
            if resp.lower().startswith('y'):
                reset()
                print('Now run play.py again.')
        else:
            reset()
        sys.exit(0)

    def show(self, action, noun):
        """Gives information about different things."""
        # TODO: Remove redundant ifs
        if noun == 'inventory':
            if len(self.inventory) > 0:
                print('Inventory:')
                for item in self.inventory:
                    if isinstance(item, Food):
                        print(item, end=' ')
                    elif isinstance(item, Weapon):
                        print(item, end=' ')
                    else:
                        print(item.name, end=': ')
                    print(f'weighs {item.weight} pounds.')
            else:
                print('There are no items in your inventory.')
        elif noun == 'location':
            print('You are at ' + self.location.name)
        elif noun == 'score':
            print(f'Your score is {self.score}.')
        elif noun == 'health':
            print(f'You have {self.health} health.')
        elif noun == 'exits':
            # TODO: Refactor into function
            self.location.displayExits()
        elif noun == "all":
            print(self)
        else:
            print('This isn\'t something I can show you.')
        return False

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
                self._die()
        return True

    def open(self, action, noun):
        chest = None
        for i in self.location.items:
            if isinstance(i, Chest):
                chest = i
                break
        if chest:
            items = chest.open()
            self.location.items += items
            return True
        return False

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
                return True
            else:
                print('You have nothing to break the chest with.')
        else:
            print('Hitting doesn\'t help.')
        return False

    def eat(self, action, noun):
        item = None
        for i in self.inventory:
            if i.name == noun:
                item = i
        if item:
            if isinstance(item, Food):
                # Ensure that health can't go above 100
                if item.health + self.health > 100:
                    item.health = 100 - self.health
                print(f'You ate the {item.name} and gained {item.health} health.')
                self.health += item.health
                self.inventory.remove(item)
                return True
            else:
                print('Sorry, that isn\'t food.')
        else:
            print('You don\'t have that.')
        return False

    def light(self, action, noun):
        if utils.inInventory(Lantern, self) and not self.hasLight:
            print('Your lantern bursts in green flame that illuminates'
                  ' the room.')
            self.hasLight = True
            if self.location.dark:
                # history=False so the same location isn't saved back into self.locationStack
                self.go('go', Location=self.location, history=False)
            return True
        elif utils.inInventory(Lantern, self):
            print('Your light is already lit.')
        else:
            print('You need a light source!')
        return False


class Creature(object):
    '''
    Supply a name, the creature's health, a description, and
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
            print(f'The {self.name} dropped {", ".join([i.name for i in itemsToDrop])} on its death.')
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

    def __str__(self):
        return f'{self.name}: Deals {self.power} damage,'


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

    def __str__(self):
        return f"{self.name}: Restores {self.health} health,"

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
