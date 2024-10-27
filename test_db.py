import sqlite3
import hashlib
con = sqlite3.connect('SILA.sqlite3')
cursor = con.cursor()



#cursor.execute("INSERT INTO users VALUES(13, 'david', 'd80fe41fbae10666b82db57eaf1a47ebaf3204f0f6385fb260b0db70e933ae9f', 3, 'Москва', 'Головной офис', 'Администратор', '');")


#print(hashlib.sha256('cp-sila-good'.encode()).hexdigest())
cursor.execute("SELECT * FROM chunk_embeddings")
#cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
#cursor.execute("INSERT INTO documents(text, meta_data_h, meta_data_source) VALUES(?, ?, ?)")
#cursor.execute("UPDATE users SET email = REPLACE(email, 'admin', 'admin1');")
print(cursor.fetchall())

con.commit()
con.close()