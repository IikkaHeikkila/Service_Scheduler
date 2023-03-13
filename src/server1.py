import socket
import json
import sqlite3
from datetime import datetime
import asyncio
import time

def send(scheduler, data):
    data = json.dumps(data)
    scheduler.sendall(data.encode())
    print("Sent")

def create_db():
    conn = sqlite3.connect('user-db.sqlite')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE users 
                    (name TEXT, 
                    age INTEGER, 
                    birthday TEXT, 
                    description TEXT, 
                    profile_picture_url TEXT, 
                    latest_post INTEGER,
                    n_recent_posts, INTEGER,
                    user_id INTEGER PRIMARY KEY AUTOINCREMENT)''')
    conn.commit()
    conn.close()

def add_user(name, age, birthday, description, profile_picture_url, 
             latest_post=None, number_of_posts=0):
    
    conn = sqlite3.connect('user-db.sqlite')
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO users 
                    (name, age, birthday, description, profile_picture_url, 
                    latest_post, n_recent_posts)
                    VALUES (?, ?, ?, ?, ?, ?, ?)''', 
                    (name, age, birthday, description, profile_picture_url, 
                    latest_post, number_of_posts))
    conn.commit()
    conn.close()



def get_user_info(scheduler, user_id):
    #Function code 11

    conn = sqlite3.connect('user-db.sqlite') 
    cursor = conn.cursor() 
    cursor.execute('SELECT * FROM users WHERE user_id=?', (user_id,)) 
    row = cursor.fetchone()
    conn.close() 
    if not row:
        info = {'name': None, 'age': None, 'description': None,
                'profile_picture_url': None,'n_recent_posts': None}
    else:
        info = {'name': row[0], 'age': row[1], 'description': row[3],
                'profile_picture_url': row[4],'n_recent_posts': row[6]}

    data = {'status':"SUCCEED", 'info':info}
    send(scheduler, data)


def update_latest_post(scheduler, user_id, post_id):
    #Function code 12

    conn = sqlite3.connect('user-db.sqlite')
    cursor = conn.cursor() 
    cursor.execute('UPDATE users SET latest_post=? WHERE user_id=?', (post_id, user_id)) 

    data = {'status':"SUCCEED"}
    send(scheduler, data)
    while True:
        print("Waiting permission")
        request = scheduler.recv(1024).decode()
        if not request:
            break
        request = json.loads(request)
        if request['status'] == "COMMIT":
            conn.commit()
            print("Commit")
            conn.commit()
            return
        if request['status'] == "ROLLBACK":
            print("Rollback")
            conn.commit()
            return   
    

def update_user_info(scheduler, user_id, n_posts):
    #Function code 13
    """Updates number of posts (last week) 
    and users age based on users birthday"""

    conn = sqlite3.connect('user-db.sqlite')
    cursor = conn.cursor()
    current_year = datetime.now().year
    #Not running this right now
    #cursor.execute('UPDATE users SET age = ? - strftime("%Y", birthday) WHERE user_id = ?', (current_year, user_id))
    cursor.execute('UPDATE users SET n_recent_posts=? WHERE user_id=?', (n_posts, user_id))
    
    conn.commit()
    conn.close()

    data = {'status':"SUCCEED"}
    send(scheduler, data)


def operation(scheduler, request):
    """Choosing the operation"""
    if request['function'] == 11:
        user_id = request['user_id']
        get_user_info(scheduler, user_id)   
    if request['function'] == 12:
        user_id = request['user_id']
        post_id = request['post_id']
        data = update_latest_post(scheduler, user_id, post_id)   
    if request['function'] == 13:
        user_id = request['user_id']
        n_posts = request['n_posts']
        update_user_info(scheduler, user_id, n_posts) 

async def with_timeout(scheduler, request):
    """Timeout frame"""
    try:
        loop = asyncio.get_running_loop()
        result = await asyncio.wait_for(loop.run_in_executor(None, operation, scheduler, request), timeout=10.0)
    except asyncio.TimeoutError:
        print("Function timed out")
        send(scheduler, {'status':"Failed"})

def main():
    host = ''  
    port = 8000  

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((host, port))
    s.listen(1)
    print(f"Server 1 listening on port {port}")

    conn, addr = s.accept()
    print(f"Connected by {addr}")


    while True:
        print("waiting...")
        request = conn.recv(1024).decode()
        if not request:
            break
        request = json.loads(request)
        print(f"Received request: {request}")  

        asyncio.run(with_timeout(conn, request))
    
main()            
