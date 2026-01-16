#!/usr/bin/env python3
"""Party Planner CLI - Manage contacts and send personalized text messages."""

import json
import os
import subprocess
import sys

try:
    from dotenv import load_dotenv
    import anthropic
    load_dotenv()
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    HAS_AI = ANTHROPIC_API_KEY and ANTHROPIC_API_KEY != "your-api-key-here"
except ImportError:
    HAS_AI = False
    ANTHROPIC_API_KEY = None

APP_DIR = os.path.dirname(os.path.abspath(__file__))
LISTS_DIR = os.path.join(APP_DIR, "lists")
CONTACTS_CACHE_FILE = os.path.join(APP_DIR, "mac_contacts_cache.json")


def ensure_lists_dir():
    """Ensure the lists directory exists."""
    if not os.path.exists(LISTS_DIR):
        os.makedirs(LISTS_DIR)


def load_cached_contacts():
    """Load contacts from local cache."""
    if not os.path.exists(CONTACTS_CACHE_FILE):
        return None
    try:
        with open(CONTACTS_CACHE_FILE, "r") as f:
            data = json.load(f)
            return data.get("contacts", [])
    except (json.JSONDecodeError, IOError):
        return None


def save_contacts_cache(contacts):
    """Save contacts to local cache."""
    with open(CONTACTS_CACHE_FILE, "w") as f:
        json.dump({"contacts": contacts}, f, indent=2)


def get_existing_lists():
    """Get all existing contact list names."""
    ensure_lists_dir()
    lists = []
    for f in os.listdir(LISTS_DIR):
        if f.endswith(".json"):
            lists.append(f[:-5])  # Remove .json extension
    return sorted(lists)


def load_list(name):
    """Load contacts from a named list."""
    filepath = os.path.join(LISTS_DIR, f"{name}.json")
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, "r") as f:
            data = json.load(f)
            return data.get("contacts", [])
    except (json.JSONDecodeError, IOError):
        return []


def save_list(name, contacts):
    """Save contacts to a named list."""
    ensure_lists_dir()
    filepath = os.path.join(LISTS_DIR, f"{name}.json")
    with open(filepath, "w") as f:
        json.dump({"contacts": contacts}, f, indent=2)


def fetch_contacts_from_mac():
    """Fetch all contacts from Mac Contacts app and save to cache."""
    print("Syncing contacts from Mac Contacts app (this may take a moment)...")

    # Use JavaScript for Automation (JXA) - much faster than AppleScript
    jxa_script = '''
    const app = Application("Contacts");
    const people = app.people();
    const results = [];
    for (let i = 0; i < people.length; i++) {
        try {
            const p = people[i];
            const name = p.name();
            const phones = p.phones();
            if (phones.length > 0) {
                results.push(name + "|" + phones[0].value());
            }
        } catch(e) {}
    }
    results.join("\\n");
    '''
    try:
        result = subprocess.run(
            ["osascript", "-l", "JavaScript", "-e", jxa_script],
            capture_output=True,
            text=True,
            timeout=300
        )
        if result.returncode != 0:
            print(f"Error loading contacts: {result.stderr}")
            return []

        contacts = []
        for line in result.stdout.strip().split("\n"):
            if "|" in line:
                parts = line.split("|")
                if len(parts) >= 2:
                    full_name = parts[0].strip()
                    first_name = full_name.split()[0] if full_name else ""
                    contacts.append({
                        "name": full_name,
                        "first_name": first_name,
                        "phone": parts[1].strip()
                    })

        save_contacts_cache(contacts)
        print(f"Synced {len(contacts)} contacts.\n")
        return contacts
    except subprocess.TimeoutExpired:
        print("Loading contacts timed out. Try again or check Contacts app permissions.")
        return []
    except Exception as e:
        print(f"Error: {e}")
        return []


def get_all_contacts(force_refresh=False):
    """Get contacts from cache, or fetch from Mac if needed."""
    if not force_refresh:
        cached = load_cached_contacts()
        if cached is not None:
            print(f"Using {len(cached)} cached contacts. (Type 'sync' to refresh from Mac Contacts)\n")
            return cached

    return fetch_contacts_from_mac()


def interactive_contact_search(all_contacts, selected_contacts):
    """Interactive search and selection of contacts. Returns (selected_contacts, all_contacts)."""
    print("=" * 50)
    print("Search and add contacts to your party list")
    print("Commands: 'list' | 'sync' | 'done' | or type to search")
    print("=" * 50)

    while True:
        print(f"\nParty list: {len(selected_contacts)} contact(s)")
        query = input("\n\033[1;94mSEARCH YOUR CONTACTS:\033[0m (or 'list'/'sync'/'done'): ").strip()

        if query.lower() == 'done':
            break

        if query.lower() == 'sync':
            all_contacts = fetch_contacts_from_mac()
            if all_contacts:
                print("Contacts refreshed from Mac Contacts app.")
            continue

        if query.lower() == 'list':
            if not selected_contacts:
                print("\n(No contacts added yet)")
            else:
                print("\n--- Current Party List ---")
                for i, c in enumerate(selected_contacts, 1):
                    print(f"  {i}. {c['name']} - {c['phone']}")
            continue

        if not query:
            continue

        # Check if input is numbers (selection)
        if query.replace(",", "").replace(" ", "").isdigit():
            # This is a selection from previous search
            print("(Enter a search term first, then select by number)")
            continue

        # Search contacts
        matches = [c for c in all_contacts if query.lower() in c['name'].lower()]

        if not matches:
            print(f"No contacts found matching '{query}'")
            continue

        # Show matches
        print(f"\nFound {len(matches)} match(es):")
        for i, contact in enumerate(matches, 1):
            already_added = any(c['phone'] == contact['phone'] for c in selected_contacts)
            marker = " [added]" if already_added else ""
            print(f"  {i}. {contact['name']} - {contact['phone']}{marker}")

        # Get selection
        print("\nEnter numbers to add (e.g., 1,3,5), 'a' for all, or press Enter to search again:")
        selection = input("> ").strip().lower()

        if not selection:
            continue

        if selection == 'a':
            to_add = matches
        else:
            try:
                indices = [int(x.strip()) - 1 for x in selection.split(",")]
                to_add = [matches[i] for i in indices if 0 <= i < len(matches)]
            except (ValueError, IndexError):
                print("Invalid selection.")
                continue

        # Add selected contacts
        added_count = 0
        for contact in to_add:
            if not any(c['phone'] == contact['phone'] for c in selected_contacts):
                selected_contacts.append(contact)
                print(f"  + Added {contact['name']}")
                added_count += 1

        if added_count == 0:
            print("  (All selected contacts already in list)")

    return selected_contacts


def rainbow_text(text):
    """Make text rainbow colored using ANSI codes."""
    colors = [
        '\033[91m',  # red
        '\033[92m',  # green
        '\033[96m',  # cyan
        '\033[94m',  # blue
        '\033[95m',  # magenta
    ]
    reset = '\033[0m'
    result = ""
    color_idx = 0
    for char in text:
        if char != ' ':
            result += colors[color_idx % len(colors)] + char
            color_idx += 1
        else:
            result += char
    return result + reset


def select_or_create_list():
    """First step: select existing list or create new one."""
    print("\n" + "=" * 50)
    print("         " + rainbow_text("PARTY PLANNER"))
    print("Welcome to Party Planning. Create a new list if you have none, then create a text draft, and we will text everyone individually using the messages app on your mac.")
    print("=" * 50)

    existing = get_existing_lists()

    if existing:
        print("\nExisting party lists:")
        for i, name in enumerate(existing, 1):
            contacts = load_list(name)
            print(f"  {i}. {name} ({len(contacts)} contacts)")
        print(f"\n  N. Create new list")
        print(f"  V. View a list's contacts")
        print()

        choice = input("Select a list, 'N' for new, or 'V' to view: ").strip().lower()

        if choice == 'n':
            return create_new_list()
        elif choice == 'v':
            view_choice = input("Enter list number to view: ").strip()
            try:
                idx = int(view_choice) - 1
                if 0 <= idx < len(existing):
                    list_name = existing[idx]
                    contacts = load_list(list_name)
                    print(f"\n--- {list_name} ---")
                    if not contacts:
                        print("  (No contacts)")
                    else:
                        for i, c in enumerate(contacts, 1):
                            print(f"  {i}. {c['name']} - {c['phone']}")
                else:
                    print("Invalid number.")
            except ValueError:
                print("Invalid input.")
            return select_or_create_list()
        else:
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(existing):
                    list_name = existing[idx]
                    contacts = load_list(list_name)
                    print(f"\nLoaded '{list_name}' with {len(contacts)} contacts.")
                    return list_name, contacts
            except ValueError:
                pass
            print("Invalid choice.")
            return select_or_create_list()
    else:
        print("\nNo existing party lists found.")
        print("Let's create your first one!\n")
        return create_new_list()


def create_new_list():
    """Create a new contact list by selecting from Mac contacts."""
    name = input("Name for this party list: ").strip()
    if not name:
        print("Name cannot be empty.")
        return create_new_list()

    # Check if name already exists
    if name in get_existing_lists():
        print(f"A list named '{name}' already exists.")
        overwrite = input("Overwrite? (y/n): ").strip().lower()
        if overwrite != 'y':
            return create_new_list()

    print()
    all_contacts = get_all_contacts()

    if not all_contacts:
        print("No contacts found. You can add contacts manually later.")
        selected = []
    else:
        selected = interactive_contact_search(all_contacts, [])

    save_list(name, selected)
    print(f"\nCreated '{name}' with {len(selected)} contacts.")
    return name, selected


def view_contacts(contacts):
    """Display all contacts."""
    if not contacts:
        print("\nNo contacts in your party list yet.")
        return
    print("\n--- Party Contacts ---")
    for i, contact in enumerate(contacts, 1):
        print(f"  {i}. {contact['name']} - {contact['phone']}")
    print(f"\nTotal: {len(contacts)} contact(s)")


def add_more_contacts(list_name, contacts):
    """Add more contacts from Mac Contacts."""
    all_contacts = get_all_contacts()
    if not all_contacts:
        print("No contacts available.")
        return contacts

    contacts = interactive_contact_search(all_contacts, contacts)
    save_list(list_name, contacts)
    return contacts


def add_contact_manually(list_name, contacts):
    """Add a contact by manual entry."""
    print("\n--- Add Contact Manually ---")
    name = input("Name: ").strip()
    if not name:
        print("Name cannot be empty.")
        return contacts

    phone = input("Phone number: ").strip()
    if not phone:
        print("Phone number cannot be empty.")
        return contacts

    contacts.append({"name": name, "phone": phone})
    save_list(list_name, contacts)
    print(f"Added {name} to your party list!")
    return contacts


def remove_contact(list_name, contacts):
    """Remove a contact from the list."""
    if not contacts:
        print("\nNo contacts to remove.")
        return contacts

    view_contacts(contacts)
    print("\nEnter number to remove, or 'c' to cancel:")
    choice = input("> ").strip().lower()

    if choice == 'c':
        return contacts

    try:
        index = int(choice) - 1
        if 0 <= index < len(contacts):
            removed = contacts.pop(index)
            save_list(list_name, contacts)
            print(f"Removed {removed['name']} from your party list.")
        else:
            print("Invalid number.")
    except ValueError:
        print("Invalid input.")

    return contacts


def draft_message(template, contact):
    """Substitute placeholders in template with contact info."""
    first_name = contact.get('first_name') or contact['name'].split()[0] if contact['name'] else ""
    return template.format(
        name=first_name,
        first_name=first_name,
        phone=contact['phone']
    )


def generate_ai_message(event_description, contact, vibe="fun and casual"):
    """Use Claude to generate a personalized party invitation."""
    if not HAS_AI:
        return None

    first_name = contact.get('first_name') or contact['name'].split()[0]

    prompt = f"""You are a hype-master party invitation writer. Your job is to craft SHORT, punchy text messages that make people EXCITED to come to an event.

RULES:
- Keep it under 160 characters (it's a text message!)
- Use the person's first name naturally
- Match the vibe requested but always bring energy
- No hashtags, no emojis overload (1-2 max if any)
- Sound like a real friend texting, not a robot
- Make them feel like they'd be missing out if they don't come
- Don't include any greeting like "Hey" at the start - jump right in

EVENT: {event_description}
RECIPIENT'S FIRST NAME: {first_name}
VIBE: {vibe}

Write ONE text message. Just the message, nothing else."""

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text.strip()
    except Exception as e:
        print(f"AI generation failed: {e}")
        return None


def send_imessage(phone, message):
    """Send a message via iMessage using AppleScript."""
    escaped_message = message.replace('\\', '\\\\').replace('"', '\\"')
    escaped_phone = phone.replace('\\', '\\\\').replace('"', '\\"')

    applescript = f'''
    tell application "Messages"
        set targetService to 1st account whose service type = iMessage
        set targetBuddy to participant "{escaped_phone}" of targetService
        send "{escaped_message}" to targetBuddy
    end tell
    '''
    try:
        result = subprocess.run(
            ["osascript", "-e", applescript],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode != 0:
            return False, result.stderr
        return True, None
    except Exception as e:
        return False, str(e)


def send_texts_flow(contacts):
    """Interactive flow for sending templated texts."""
    if not contacts:
        print("\nNo contacts in your party list. Add some first!")
        return

    print("\n" + "=" * 50)
    print("         TIME TO SEND SOME TEXTS")
    print("=" * 50)
    print()
    print("Write your message below. Use {name} and it'll be")
    print("swapped with each person's first name automatically.")
    print()
    print("Type '1' to use: Hey {name}! Party at my place Friday at 8, you in?")
    print()

    template = input("> ").strip()

    if template == "1":
        template = "Hey {name}! Party at my place Friday at 8, you in?"
        print(f"Using: {template}\n")

    if not template:
        print("Message cannot be empty.")
        return

    print(f"\n[Enter] or [S] to send / [E]dit / [N]ext / [Q]uit\n")

    sent_count = 0
    skipped_count = 0

    for i, contact in enumerate(contacts, 1):
        try:
            message = draft_message(template, contact)
        except KeyError as e:
            print(f"Invalid placeholder: {e}")
            return

        while True:
            print(f"--- {i}/{len(contacts)}: {contact['name']} ---")
            print(f"> {message}\n")

            choice = input("[Enter/S/E/N/Q]: ").strip().lower()

            if choice == 's' or choice == '':
                print("Sending...", end=" ")
                success, error = send_imessage(contact['phone'], message)
                print("Sent!" if success else f"Failed: {error}")
                if success:
                    sent_count += 1
                break
            elif choice == 'e':
                message = input("New msg: ").strip() or message
                print()
            elif choice == 'n':
                skipped_count += 1
                break
            elif choice == 'q':
                print(f"\nSent: {sent_count}, Skipped: {skipped_count + len(contacts) - i}")
                return

    print(f"\nDone! Sent: {sent_count}, Skipped: {skipped_count}")


def party_menu(list_name, contacts):
    """Main party planning menu after list selection."""
    while True:
        print("\n" + "=" * 50)
        print(f"  {list_name}")
        print(f"  {len(contacts)} contact(s) ready to party")
        print("=" * 50)

        print("\n  MANAGE YOUR LIST")
        print("  ----------------")
        print("  1. View contacts")
        print("  2. Add contacts (search)")
        print("  3. Add contact manually")
        print("  4. Remove contact")
        print("  5. Switch/create list")

        print("\n  ~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~")
        print("        \033[1m" + rainbow_text("READY TO MAKE IT HAPPEN?") + "\033[0m")
        print("  ~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~")
        print(f"  6. SEND THE TEXTS --> {len(contacts)} people are waiting!")
        print("      (your party starts here)")

        print("\n  0. Exit")
        print()

        choice = input("> ").strip()

        if choice == '1':
            view_contacts(contacts)
        elif choice == '2':
            contacts = add_more_contacts(list_name, contacts)
        elif choice == '3':
            contacts = add_contact_manually(list_name, contacts)
        elif choice == '4':
            contacts = remove_contact(list_name, contacts)
        elif choice == '5':
            return True  # Signal to go back to list selection
        elif choice == '6':
            send_texts_flow(contacts)
        elif choice == '0':
            print("\nGoodbye! Party on!")
            sys.exit(0)
        else:
            print("Invalid option.")

    return False


def main():
    """Main entry point."""
    while True:
        list_name, contacts = select_or_create_list()
        should_continue = party_menu(list_name, contacts)
        if not should_continue:
            break


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nGoodbye!")
        sys.exit(0)
