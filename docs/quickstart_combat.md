# Quickstart: Combat

Follow these steps to see two characters fight using the built-in combat system.

## 1. Run the Evennia server

From the project root run:

```bash
evennia migrate
evennia start
```

Create your superuser account when prompted and connect using the web client or any telnet client.

## 2. Create two characters

Open two client connections. For each connection use the `ic` command to create and puppet a character. If the name does not already exist `ic <name>` will create it for you. New characters appear in the start room, so both should be together immediately. If needed you can move them with `@teleport`.

## 3. Start combat

From one of the characters run:

```
attack <target>
```

Replace `<target>` with the other character's name. The `attack` command queues the first action and combat rounds begin automatically every few seconds until one combatant falls or flees.

