import os
keys = (
    'DISCORD_WEBHOOK_KPIS',
    'DISCORD_WEBHOOK_KPI',
    'DISCORD_WEBHOOK_STATUS',
    'DISCORD_WEBHOOK_URL',
)
for k in keys:
    v = os.getenv(k)
    if v:
        print(f"{k} => SET (prefix: {v[:60]})")
    else:
        print(f"{k} => MISSING")
