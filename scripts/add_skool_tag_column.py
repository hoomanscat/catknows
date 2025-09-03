import sqlite3

DB = 'skool.db'
conn = sqlite3.connect(DB)
cur = conn.cursor()
try:
    cur.execute("ALTER TABLE members ADD COLUMN skool_tag TEXT")
    conn.commit()
    print('ALTER TABLE executed: skool_tag added')
except Exception as e:
    print('ALTER TABLE error:', e)
finally:
    conn.close()
