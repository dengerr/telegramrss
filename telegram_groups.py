import pandas as pd

from go import client, cfg


def print_participants(group_username):
    participants = client.get_participants(group_username)

    # This code can be used to extracted upto 10k user's details
    # Let's get first name, last name and username

    firstname = []
    lastname = []
    username = []
    if len(participants):
        for x in participants:
            print(x)
            firstname.append(x.first_name)
            lastname.append(x.last_name)
            username.append(x.username)

    # list to data frame conversion

    data = {"first_name": firstname, "last_name": lastname, "user_name": username}

    userdetails = pd.DataFrame(data)
    print(userdetails)


def print_chats(chats):
    print(group_username)
    for chat in chats:
        print(chat.date, chat.id)
        print(chat.message)
        print()


def get_data_frame(chats):
    # Get message id, message, sender id, reply to message id, and timestamp
    message_id = []
    message = []
    sender = []
    reply_to = []
    time = []
    for chat in chats:
        message_id.append(chat.id)
        message.append(chat.message)
        sender.append(chat.from_id)
        reply_to.append(chat.reply_to_msg_id)
        time.append(chat.date)

    data = {
        "message_id": message_id,
        "message": message,
        "sender_ID": sender,
        "reply_to_msg_id": reply_to,
        "time": time,
    }
    df = pd.DataFrame(data)
    return df


group_username = cfg.get('groups', "group_name")

# Group name can be found in group link
# (Example group link : https://t.me/c0ban_global, group name = 'c0ban_global')
