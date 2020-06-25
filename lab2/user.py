import redis
import atexit
import datetime
import logging
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning) 

CRED    = '\33[31m'
CGREEN  = '\33[32m'
CYELLOW = '\33[33m'
CBLUE   = '\33[34m'
CEND      = '\33[0m'
CBOLD     = '\33[1m'
CITALIC   = '\33[3m'

logging.basicConfig(filename="messanger.log", level=logging.INFO)


def login_menu(connection, login) -> int:
    user_id = connection.hget("users:", login)

    if not user_id:
        print("No user with such username exists. Please, register first")
        return -1

    connection.sadd("online:", login)
    logging.info(f"{datetime.datetime.now()} Actor: {login} Action: log in \n")

    return int(user_id)


def logout(connection, user_id) -> int:
    username = connection.hmget("user:%s" % user_id, ["login"])[0];
    logging.info(f"{datetime.datetime.now()} Actor: {username} Action: sign out \n")
    return connection.srem("online:", connection.hmget("user:%s" % user_id, ["login"])[0])


def new_message(connection, text, consumer, sender_id) -> int:
    try:
        message_id = int(connection.incr('message:id:'))
        consumer_id = int(connection.hget("users:", consumer))
    except TypeError:
        print("No user with %s username exists, can't send a message" % consumer)
        return

    pipeline = connection.pipeline(True)

    pipeline.hmset('message:%s' % message_id, {
        'text': text,
        'id': message_id,
        'sender_id': sender_id,
        'consumer_id': consumer_id,
        'status': "created"
    })

    pipeline.lpush("queue:", message_id)
    pipeline.hmset('message:%s' % message_id, {
        'status': 'queue'
    })

    pipeline.zincrby("sent:", 1, "user:%s" % connection.hmget("user:%s" % sender_id, ["login"])[0])
    pipeline.hincrby("user:%s" % sender_id, "queue", 1)
    pipeline.execute()

    return message_id

def register(connection, username):
    if connection.hget('users:', username):
        print(f"User {username} exists");
        return None

    user_id = connection.incr('user:id:')

    pipeline = connection.pipeline(True)

    pipeline.hset('users:', username, user_id)

    pipeline.hmset('user:%s' % user_id, {
        'login': username,
        'id': user_id,
        'queue': 0,
        'checking': 0,
        'blocked': 0,
        'sent': 0,
        'delivered': 0
    })
    pipeline.execute()
    logging.info(f"{datetime.datetime.now()} Actor: {username} Action: register \n")
    return user_id

def print_messages(connection, user_id):
    messages = connection.smembers("sentto:%s" % user_id)
    for message_id in messages:
        message = connection.hmget("message:%s" % message_id, ["sender_id", "text", "status"])
        sender_id = message[0]
        print(CRED)
        print("From: %s - %s" % (connection.hmget("user:%s" % sender_id, ["login"])[0], message[1]))
        print(CEND)
        if message[2] != "delivered":
            pipeline = connection.pipeline(True)
            pipeline.hset("message:%s" % message_id, "status", "delivered")
            pipeline.hincrby("user:%s" % sender_id, "sent", -1)
            pipeline.hincrby("user:%s" % sender_id, "delivered", 1)
            pipeline.execute()


def main_menu() -> int:
    print(CBLUE, 3 * "*", CYELLOW, "Main menu", CBLUE, 3 * "*")
    print("1. Register")
    print("2. Login")
    print("3. Exit", CGREEN)
    print("Enter number: ", CEND)
    return int(input())


def user_menu() -> int:
    print(CBLUE, 3 * "*", CYELLOW, "Userr menu", CBLUE, 3 * "*")
    print("1. Log out")
    print("2. Inbox")
    print("3. Create message")
    print("4. Statistics", CGREEN)
    print("Enter number: ", CEND)
    return int(input())

def is_user_signed_in(current_user_id):
    return current_user_id != -1

def user_menu_flow(connection, current_user_id):
    while True:
        choice = user_menu()

        if choice == 1:
            logout(connection, current_user_id)
            connection.publish('users', "User %s signed out" % connection.hmget("user:%s" % current_user_id, ["login"])[0])
            break;

        elif choice == 2:
            print_messages(connection, current_user_id)

        elif choice == 3:
            try:
                print(CGREEN)
                print("Type your message:", CEND)
                message = input()
                print(CGREEN)
                print("Type the username of the reciever:", CEND)
                recipient = input()
                print(CGREEN)
                if new_message(connection, message, current_user_id, recipient):
                    print("Sending message...", CEND)
            except ValueError:
                print(CRED, "User with such login wasn`t found!", CEND)

        elif choice == 4:
            current_user = connection.hmget("user:%s" % current_user_id,['queue', 'checking', 'blocked', 'sent', 'delivered'])
            print("In queue: %s\nChecking: %s\nBlocked: %s\nSent: %s\nDelivered: %s" %tuple(current_user))
        else:
            print("Please select correct option [1-4]")

def main():
    def exit_handler():
        logout(connection, current_user_id)

    atexit.register(exit_handler)
    connection = redis.Redis(charset="utf-8", decode_responses=True)

    while True:
        choice = main_menu()

        if choice == 1:
            print(CGREEN, "Enter login what you want to register:", CEND)
            login = input()
            register(connection, login)

        elif choice == 2:
            print(CGREEN, "Enter your login:", CEND)
            login=input()
            current_user_id = login_menu(connection, login)
            if is_user_signed_in(current_user_id):
                username = connection.hmget("user:%s" % current_user_id, ["login"])[0];
                connection.publish('users', "User %s signed in" % username)
                user_menu_flow(connection, current_user_id)

        elif choice == 3:
            print(CGREEN,"Exiting...",CEND)
            break;

        else:
            print("Please select correct option [1-3]")


if __name__ == '__main__':
    main()