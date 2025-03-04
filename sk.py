import secrets

# Generate a random secret key
secret_key = secrets.token_hex(24)  # 24 bytes = 48 characters in hex
print(secret_key)