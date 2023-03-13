import socket
import json
import sqlite3
from datetime import datetime, timedelta
import asyncio
import time


def send(scheduler, data):
    data = json.dumps(data)
    scheduler.sendall(data.encode())
    print("Sent")

def create_db():
    conn = sqlite3.connect('post-db.sqlite')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE posts 
                    (text TEXT, 
                    image_url TEXT,
                    date TEXT,
                    user_id INTEGER,
                    post_id INTEGER PRIMARY KEY AUTOINCREMENT)''')
    conn.commit()
    conn.close()


def get_posts(scheduler, user_id):
    #Function code 21
    conn = sqlite3.connect('post-db.sqlite')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM posts WHERE user_id=?', (user_id,))
    posts = []
    for row in cursor.fetchall():
        post = {
            'text': row[0],
            'image_url': row[1],
            'date': row[2],
            'user_id': row[3],
            'post_id': row[4]
        }
        posts.append(post)

    data = {'status':"SUCCEED", 'posts':posts}
    send(scheduler, data)


def add_post(scheduler, text, image_url, date, user_id):
    #Function code 22
    #ATOMICITY!
    
    conn = sqlite3.connect('post-db.sqlite')
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO posts 
                    (text, image_url, date, user_id)
                    VALUES (?, ?, ?, ?)''', 
                    (text, image_url, date, user_id))
    post_id = cursor.lastrowid

    data = {'status':"SUCCEED", 'post_id':post_id}
    send(scheduler, data)
    while True:
        print("Waiting permission to commit")
        request = scheduler.recv(1024).decode()
        if not request:
            break
        request = json.loads(request)
        if request['status'] == "COMMIT":
            print("Commit")
            conn.commit()
            conn.close()
            return
        if request['status'] == "ROLLBACK":
            print("Rollback")
            conn.close()
            return
    
def get_n_of_posts(scheduler, user_id):
    
    conn = sqlite3.connect('post-db.sqlite')
    cursor = conn.cursor()

    seven_days_ago = datetime.now() - timedelta(days=7)
    cursor.execute('SELECT COUNT(*) FROM posts WHERE strftime("%s", date) >= strftime("%s", ?)', 
                   (seven_days_ago.strftime('%Y-%m-%d %H:%M:%S'),))
    n_posts = cursor.fetchone()[0]

    # Close the connection
    conn.close()

    data = {'status':"SUCCEED", 'n_posts':n_posts}
    send(scheduler, data)


def operation(scheduler, request):
    if request['function'] == 21:
        user_id = request['user_id']
        get_posts(scheduler, user_id)
    if request['function'] == 22:
        text = request['text']
        image_url = request['image_url']
        date = request['date']
        user_id = request['user_id']
        add_post(scheduler, text, image_url, date, user_id)
    if request['function'] == 23:
        user_id = request['user_id']
        get_n_of_posts(scheduler, user_id)

async def with_timeout(scheduler, request):
    """Timeout frame"""
    try:
        loop = asyncio.get_running_loop()
        result = await asyncio.wait_for(loop.run_in_executor(None, operation, scheduler, request), timeout=10.0)
    except asyncio.TimeoutError:
        print("Function timed out")
        send(scheduler, {'status':"Failed"})



def main():
    host = ''  # Symbolic name, all available interfaces
    port = 8001  # Arbitrary non-privileged port

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((host, port))
    s.listen(1)
    print(f"Server 2 listening on port {port}")

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
