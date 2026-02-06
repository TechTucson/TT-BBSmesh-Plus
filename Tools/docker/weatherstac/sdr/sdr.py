import subprocess, sqlite3, time, whisper

DB="/data/weather.db"
AUDIO="/tmp/audio.wav"

FREQS=["162.400M","162.425M","162.450M","162.475M","162.500M","162.525M","162.550M"]

model=whisper.load_model("base")

db=sqlite3.connect(DB,check_same_thread=False)
c=db.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS messages(
 id INTEGER PRIMARY KEY,
 ts DATETIME DEFAULT CURRENT_TIMESTAMP,
 freq TEXT,
 type TEXT,
 content TEXT
)
""")

while True:
  for f in FREQS:

    rtl=["rtl_fm","-f",f,"-M","fm","-s","22050","-r","22050","-"]
    sox=["sox","-t","raw","-r","22050","-e","signed","-b","16","-c","1","-",AUDIO,"trim","0","25"]

    p1=subprocess.Popen(rtl,stdout=subprocess.PIPE)
    p2=subprocess.Popen(sox,stdin=p1.stdout)
    p2.wait()
    p1.kill()

    same=subprocess.run(["multimon-ng","-a","SAME",AUDIO],capture_output=True,text=True)
    if same.stdout.strip():
        c.execute("INSERT INTO messages(freq,type,content) VALUES(?,?,?)",(f,"same",same.stdout))
        db.commit()

    r=model.transcribe(AUDIO)["text"].strip()
    if r:
        c.execute("INSERT INTO messages(freq,type,content) VALUES(?,?,?)",(f,"voice",r))
        db.commit()

    time.sleep(2)
