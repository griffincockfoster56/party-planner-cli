# Party Planner - Automate Texting Your Group One on One

Planning events with friends is great, but whenever you text people in a group chat, most will just ignore it.

Party Planner is the solution to that. It is a mac app that lets you creates lists of contacts, enter a message template, and then automates texting your contacts with the Mac Messages app one on one to plan an event. When you text people one on one, they are way more likely to respond, as opposed to in a group chat.

Party Planner runs on the CLI and is very simple to get started with. Try it today!

## Features

- **Import contacts from Mac Contacts app** - Search and add people from your existing contacts
- **Create multiple party lists** - Save different groups for different events
- **Personalized messages** - Write one template, automatically swap in each person's name
- **Send via iMessage** - Messages go through your Mac's Messages app

## Requirements

- macOS (uses AppleScript to access Contacts and Messages)
- Python 3

## Installation

1. Clone this repo:
   ```bash
   git clone https://github.com/griffincockfoster56/party-planner-cli
   cd party-planner-cli
   ```

2. That's it! No dependencies required for basic usage.

## Usage

Run the app:
```bash
python3 party_planner.py
```

### First time setup

1. The app will prompt you to create a new party list
2. Give it a name (e.g., "Birthday Bash")
3. Your Mac contacts will be loaded (you'll need to grant permission)
4. Search for people by name and add them to your list

### Sending texts

1. Select your party list
2. Choose option 6 to send texts
3. Write your message using `{name}` as a placeholder:
   ```
   Hey {name}! Party at my place Friday at 8pm, you coming?
   ```
   **Pro tip:** Type `1` to instantly load the example template!

4. Review each message and press `S` to send, `N` to skip, or `Q` to quit

### Commands during contact search

- Type a name to search
- Enter numbers to add (e.g., `1,3,5` or `a` for all)
- `list` - View your current party list
- `sync` - Refresh contacts from Mac Contacts app
- `done` - Finish adding contacts

## Permissions

On first run, macOS will ask for permission to:
- Access your Contacts
- Control the Messages app

Grant these permissions for the app to work.

## File Structure

```
party-planner-cli/
├── party_planner.py          # Main app
├── mac_contacts_cache.json   # Cached contacts (created on first sync)
└── lists/                    # Your saved party lists
    └── My Party.json
```

## License

MIT
