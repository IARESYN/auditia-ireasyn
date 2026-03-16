from passlib.context import CryptContext
import sys

try:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    test_pw = "Short123"
    print(f"Testing bcrypt for password: {test_pw}")
    hashed = pwd_context.hash(test_pw)
    print(f"Hashed: {hashed}")
    verified = pwd_context.verify(test_pw, hashed)
    print(f"Verified: {verified}")
    
    long_pw = "a" * 73
    print(f"Testing long password (73 chars)")
    try:
        hashed_long = pwd_context.hash(long_pw)
        print("Long password hashed successfully (unexpected for pure bcrypt but passlib might truncate or handle it)")
    except Exception as e:
        print(f"Caught expected error for long password: {type(e).__name__}: {e}")
except Exception as e:
    print(f"Diagnostic failed: {type(e).__name__}: {e}")
    sys.exit(1)
