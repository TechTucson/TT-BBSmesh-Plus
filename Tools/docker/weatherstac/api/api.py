from fastapi import FastAPI, WebSocket
import sqlite3, asyncio

DB="/data/weather.db"

app=FastAPI()

@app.get("/latest")
def latest():
    db=sqlite3.connect(DB)
    r=db.execute("SELECT * FROM messages ORDER BY id DESC LIMIT 1").fetchone()
    return r

@app.get("/history")
def history(limit:int=50):
    db=sqlite3.connect(DB)
    return db.execute("SELECT * FROM messages ORDER BY id DESC LIMIT ?",(limit,)).fetchall()

@app.websocket("/ws")
async def ws(ws:WebSocket):
    await ws.accept()
    last=0
    while True:
        db=sqlite3.connect(DB)
        r=db.execute("SELECT id,content FROM messages WHERE id>?",(last,)).fetchall()
        for m in r:
            last=m[0]
            await ws.send_text(m[1])
        await asyncio.sleep(2)

@app.get("/")
def dashboard():
    return """
<html>
<body>
<h2>Weather Monitor</h2>
<div id=log></div>
<script>
ws=new WebSocket("ws://"+location.host+"/ws");
ws.onmessage=e=>log.innerHTML+=e.data+"<br>";
</script>
</body>
</html>
"""
