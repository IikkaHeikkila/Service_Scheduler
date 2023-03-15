import socket
import json
import asyncio
from datetime import datetime
import time

def send_receive(server, data):
    data = json.dumps(data)
    server.sendall(data.encode())
    print("sent to {}: {}".format(str(server), data))
    message_json = server.recv(1024).decode()
    message = json.loads(message_json)
    return message


async def send_receive_async(server, data):
    data = json.dumps(data)
    server.sendall(data.encode())
    print("sent: ", data)
    message_json = server.recv(1024).decode()
    message = json.loads(message_json)
    return message

async def load_user_page(server1, server2, user_id):
    # To run this ugly monster: asyncio.run(load_user_page(server1, server2, user_id))
    """Asks information of user. User info from server1 and posts info from server2"""

    data1 = {'function':11, 'user_id':user_id}
    data2 = {'function':21, 'user_id':user_id}
    
    print("We splitted to two")
    tasks = [
        asyncio.create_task(send_receive_async(server1, data1)),
        asyncio.create_task(send_receive_async(server2, data2))
    ]
    response1, response2 = await asyncio.gather(*tasks)
    print("User's home page: ", response1, response2)


def create_a_post(server1, server2, text, image_url, user_id, date=datetime.now()):
    """First creates the post in server 2, then updates user's latest post (id) in server1
    (not in parallel, because post_id is autoincremented in server2).
    satisfies the ATOMICITY condition"""

    data = {'function':22, 'text':text, 'image_url':image_url, 'user_id':user_id, 'date':str(date)}
    response_2 = send_receive(server2, data)
    if response_2['status'] != "SUCCEED":
        print("Failed: server2")
        return
    data = {'function':12,'user_id':user_id, 'post_id':response_2['post_id']}
    response_1 = send_receive(server1, data)
    if response_1['status'] != "SUCCEED":
        print("Failed: server1")
        return
    print("Ready to commit!")
    commit_transactions([server1, server2], {'status':"COMMIT"})
    print("New post ({}) created for user ({})".format(response_2['post_id'], user_id))


def update_user_information(server1, server2, user_id):
    """Updates user's information"""
    data = {'function':23, 'user_id':user_id}
    response_2 = send_receive(server2, data)
    print("Received from s2: ", response_2)
    if response_2['status'] != "SUCCEED":
        print("Failed: server2")
        return
    data = {'function':13,'user_id':user_id, 'n_posts':response_2['n_posts']}
    response_1 = send_receive(server1, data)
    print("Received from s1: ", response_1)
    if response_1['status'] != "SUCCEED":
        print("Failed: server1")
        return
    print()
    print("User's ({}) information updated".format(user_id))


def commit_transactions(servers: list, status):
    status = json.dumps(status)
    for server in servers:
        server.sendall(status.encode())

def main():
    host1 = 'server1'
    port1 = 8000

    host2 = 'server2'
    port2 = 8001

    time.sleep(5)   #Prevents failure of setuping servers
    print("sleeping")

    server1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server1.connect((host1, port1))

    server2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server2.connect((host2, port2))

    """Some examples"""
    text = "I'm gonna write a new book"
    image_url = "Fake url"
    user_id = 1
    create_a_post(server1, server2, text, image_url, user_id)
    update_user_information(server1, server2, user_id)
    asyncio.run(load_user_page(server1, server2, user_id))
    
main()
