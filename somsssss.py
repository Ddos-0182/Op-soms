import uuid
import qrcode
import sqlite3
from telethon import TelegramClient, events

# Telegram API Configuration
api_id = '20601861'  # Replace with your Telegram API ID
api_hash = '2a9c2fdd5723f7618e9d2ae7d3277212'  # Replace with your Telegram API Hash
phone_number = '+918618126576'  # Your phone number associated with the account

client = TelegramClient('session_name', api_id, api_hash)

# Database Setup (SQLite)
conn = sqlite3.connect('transactions.db')
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS transactions (
    transaction_id TEXT PRIMARY KEY,
    user_id TEXT,
    server TEXT,
    duration TEXT,
    amount REAL,
    verified INTEGER DEFAULT 0
)
""")
conn.commit()

# File to Store Server Keys
key_file = 'keys.txt'

# Key Prices
key_prices = {
    "magic_server": {
        "1_Day": 100,
        "3_Days": 250,
        "7_Days": 500
    },
    "not_available_server": {
        "1_month": 150000,
        "3_months": 3500000,
        "6_months": 6000000
    }
}

# Helper Functions
def generate_transaction_id():
    return str(uuid.uuid4())

def generate_upi_qr(upi_id, amount, transaction_id):
    upi_data = f"upi://pay?pa={upi_id}&pn=ServerPayment&am={amount}&cu=INR&tid={transaction_id}"
    qr = qrcode.make(upi_data)
    qr_path = f"qr_{transaction_id}.png"
    qr.save(qr_path)
    return qr_path

def assign_server_key(server, duration):
    with open(key_file, 'r') as f:
        keys = f.readlines()
    
    for line in keys:
        key_data = line.strip().split(" ", 1)
        if len(key_data) == 2 and key_data[1] == duration:
            key = key_data[0]
            keys.remove(line)
            
            # Save updated keys back
            with open(key_file, 'w') as f:
                f.writelines(keys)
            return key
    
    return None  # No keys available

# Event Handlers
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    try:
        # Fetch sender details
        sender = await event.get_sender()  # Fetch the sender object
        first_name = getattr(sender, "first_name", "User")  # Safely get the first_name attribute
        
        await event.reply(
            f"Hello, {first_name}!\n\n"
            "Welcome to the Server Key Payment Bot!\n\n"
            "Here are the commands you can use:\n"
            "- /buy - View available servers and their prices.\n"
            "- /buy <server> <duration> - Purchase a server key.\n"
            "- /verify <transaction_id> - Verify your payment and get your key.\n\n"
            "Enjoy our services!"
        )
    except Exception as e:
        print(f"Error fetching user details in /start: {e}")
        await event.reply("⚠️ Unable to fetch your details. Please try again.")

@client.on(events.NewMessage(pattern=r'/buy$'))
async def show_servers(event):
    available_servers = "Here are the available servers and their prices:\n\n"
    for server, durations in key_prices.items():
        available_servers += f"{server.replace('_', ' ').title()}:\n"
        for duration, price in durations.items():
            available_servers += f"  - {duration.replace('_', ' ').title()}: ₹{price}\n"
    
    available_servers += "\nTo purchase a server, use the command /buy <server> <duration>, for example:\n"
    available_servers += "/buy magic_server 1_Day or /buy not_available_server 3_months."
    
    await event.reply(available_servers)

@client.on(events.NewMessage(pattern=r'/buy (\w+) (\w+)'))
async def process_buy(event):
    user_id = event.sender_id
    message = event.message.message.split()
    
    if len(message) != 3:
        await event.reply("Usage: /buy <server> <duration>")
        return
    
    server = message[1]
    duration = message[2]

    if server not in key_prices or duration not in key_prices[server]:
        await event.reply("Invalid server or duration. Please check and try again.")
        return

amount = key_prices[server][duration]
    upi_id = "theycallmesoms@axl"  # Replace with your UPI ID
    transaction_id = generate_transaction_id()
    qr_path = generate_upi_qr(upi_id, amount, transaction_id)
    
    # Save transaction to database
    try:
        cursor.execute("INSERT INTO transactions VALUES (?, ?, ?, ?, ?, 0)", 
                       (transaction_id, user_id, server, duration, amount))
        conn.commit()
    except sqlite3.Error as e:
        await event.reply(f"Database error: {str(e)}")
        return

    # Send QR Code to User
    await client.send_file(user_id, qr_path, caption=(
        f"🔑 Server Selection: {server.replace('_', ' ').title()}\n"
        f"📅 Duration: {duration.replace('_', ' ').title()}\n"
        f"💵 Amount: ₹{amount}\n"
        f"📤 Transaction ID: {transaction_id}\n\n"
        f"📌 Scan this QR code to complete your payment via UPI."
    ))

@client.on(events.NewMessage(pattern='/verify (.+)'))
async def verify(event):
    transaction_id = event.pattern_match.group(1)
    cursor.execute("SELECT * FROM transactions WHERE transaction_id = ? AND verified = 0", (transaction_id,))
    transaction = cursor.fetchone()

    if transaction:
        user_id, server, duration, amount = transaction[1], transaction[2], transaction[3], transaction[4]
        key = assign_server_key(server, duration)
        
        if key:
            cursor.execute("UPDATE transactions SET verified = 1 WHERE transaction_id = ?", (transaction_id,))
            conn.commit()
            await client.send_message(
                user_id,
                f"✅ Payment verified!\nHere is your server key:\n\n{key}"
            )
            await event.reply(f"✅ Payment verified for user {user_id}. Key sent!")
        else:
            await event.reply("❌ No keys available for the selected server and duration.")
    else:
        await event.reply("❌ Invalid transaction ID or payment already verified.")

# Start the Client
async def main():
    try:
        await client.start()
        print("Bot is running...")
        await client.run_until_disconnected()
    except Exception as e:
        print(f"Unhandled exception: {e}")

if name == "main":
    import asyncio
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("Bot stopped.")