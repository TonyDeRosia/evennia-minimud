# Evennia: The RPG

**Play Here** https://example.com

### What is this?

Evennia is a game engine/framework for making online multiplayer text games, such as MUDs.

*This* game is an attempt to make a small but fully-functional RPG-style MUD with as little custom code as possible, relying as much as possible on the existing community-contributed packages. 

### Okay... but why?

I wanted to see just how doable it would be for a brand new game developer to get a typical full game out the door - both for my own curiosity, and to show to other people who might want to make their own games!

One of the selling points of Evennia, besides how flexible and easy to customize it is, is the fact that you can have a server set up and online within minutes. But part of that "flexible and easy to customize" angle means that it tries to be as unopinionated as possible and have as few of the kinds of mechanics that make a game unique defined out of the box. The community contribs, on the other hand, are stand-alone add-ons that can be as opinionated as the contributors want, so if they suit your game vision, you can just put them right in.

### Can I use this to make my own game?

Yes!! Please do! There's installation instructions further down, and be sure to check out the [Evennia website](https://evennia.com).

### This game is okay but it would be better if it had <something else>....

You are absolutely correct!

Since my goal was to write as little custom code as possible, most of the mechanics are as minimal as I could get away with. But the code is all here and free for the taking - if you like part of it but want it to be better, make it better!


## Coins and Currency

This game uses four types of coins. They convert as follows:

```
1 Silver = 100 Copper
1 Gold  = 10 Silver  = 1,000 Copper
1 Platinum = 100 Gold = 1,000 Silver = 100,000 Copper
```

Typical uses for each coin are roughly:

- **Copper** – everyday expenses like a meal or a night at a cheap inn.
- **Silver** – standard goods, basic gear or routine services.
- **Gold** – quality equipment or costly services such as a house or mount.
- **Platinum** – rare, high value purchases or very large transactions.


## Installation and Setup

I set this up to make it reasonably easy to install and set up, but I had to make a decision between "write a bunch more code" and "add a couple more steps" and since my goal was to write *less* code.... Well, you've got a couple more steps.

First, you need to install Python 3.11 and have git in your command line. Then, cd to your programming folder (or make one and cd in) and follow these steps to download and install:

*(If you know what any of the steps do and want to do them differently, feel free.)*

#### Windows
```
git clone https://github.com/InspectorCaracal/evennia-minimud.git
cd evennia-minimud
py -m venv .venv
.venv\Scripts\activate
pip install .
py -m evennia
evennia migrate
evennia start
```

#### Linux & Mac
```
git clone https://github.com/InspectorCaracal/evennia-minimud.git
cd evennia-minimud
python -m venv .venv
source .venv/bin/activate
pip install .
evennia migrate
evennia start
```

That last step will prompt you to set up an initial admin, or superuser, account for the game. It also creates an initial test character.

*If you forget your password, you can change it from outside the game with `evennia changepassword youraccount` at any time - just make sure to reload the game with `evennia reload` so it will take effect.*

Once you've done that and it finishes starting up, set up the XYZGrid map plugin and the starter town with the following:

```
evennia xyzgrid init
evennia xyzgrid add world.maps.starter_town
evennia xyzgrid spawn
```

Enter `Y` to start the map building, wait a bit for that to finish, then:

    evennia reload
		
Finally, open your web browser and go to `localhost:4001` to get to the game's webpage, log in, and then click the big `Play in the browser!` button....

You're connected to the game! Use the `ic` command to connect to your test character in order to finish the last piece of setup. Once you're in Limbo, enter:

    batchcmd initial_build

to create the "overworld" map and do some finishing touches to the town's set-up.

## Building your Own Game

You want to make your own game? Awesome! The code here should help give you something to start from, but you should also check out the excellent Evennia docs - especially the [tutorial walkthrough](https://www.evennia.com/docs/latest/Howtos/Beginner-Tutorial/Beginner-Tutorial-Overview.html). It covers working with Evennia, developing within Evennia, and a walkthrough of building a full game within Evennia. (It's still in-progress but is *mostly* complete.)

If you wind up having any issues or questions working with Evennia, [the Discord community](https://discord.gg/AJJpcRUhtF) is small but active and there's almost always someone around who's happy to help newcomers.

### NPC Creation Menu

You can quickly set up non-player characters using `@cnpc start <key>`. This
opens an interactive menu where you enter the description, type, level and other
details. Follow the prompts, review the summary at the end and confirm to create
your NPC. You can later update them with `@cnpc edit <npc>`.

See the `cnpc` help entry for a full breakdown of every menu option.

While editing, there's a step to manage triggers using a numbered menu. Choose
`Add trigger` to create a new reaction, `Delete trigger` to remove one, `List
triggers` to review them and `Finish` when done.
See the `triggers` help entry for the list of events and possible reactions.

## Weapon Creation and Inspection

Builders can quickly create melee weapons with the `cweapon` command.

```
cweapon [/unidentified] <name> <slot> <damage> [weight] [stat_mods] <description>
```

Damage may be a flat number or an `NdN` dice value. The item's key never
changes, even if multiple weapons share the same name. Instead, a lowercase
alias and a numbered alias like `name-1`, `name-2`, and so on are added
silently.

These aliases let you reference duplicates. For example:

```text
cweapon "epee" mainhand 1d4 2 STR+1 A sharp epee.
cweapon "epee" offhand 2d6 3 STR+1, Attack Power+2 A balanced offhand blade.
inspect epee-2
```

Modifiers use the form `Stat+Value` separated by commas. Quote names that
contain spaces or ANSI colour codes, as shown above.

Add `/unidentified` before the name to create the weapon unidentified.

When a weapon is identified, `inspect` shows its damage, slot, any bonuses and
effects, so `inspect epee-2` will display the full details of the second
"Epee" you created.


## Merchants and Shopping

NPCs can act as merchants if they use the `Merchant` typeclass. A merchant keeps
sale stock in an internal storage container and offers the commands `list`,
`buy`, `sell` and `sell all` to nearby players. Selling items automatically adds
them to the merchant's stock. Prices are based on the item's value with optional
markups or discounts. Buying or selling adjusts both your coin pouch and the
merchant's purse. Stand in the same room as the merchant and use these commands
to interact with them.

## Banking

Banker NPCs can hold your money securely. Use `bank` to check your balance,
`deposit <amount> <currency>` to store coins and `withdraw <amount> <currency>`
to take them back out.
