import redis


client = redis.Redis(host='localhost', port=6379, db=0)

client.set('my_key', 'Hello, Redis!')

value = client.get('my_key')
print(value.decode('utf-8') if value else 'Key not found')