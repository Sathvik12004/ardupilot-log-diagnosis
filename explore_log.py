from pymavlink import mavutil
import collections

# Loads the log
mlog = mavutil.mavlink_connection('VTOL hover test.bin')

# Counts all message types in the log
msg_types = collections.Counter()

while True:
    msg = mlog.recv_match(blocking=False)
    if msg is None:
        break
    msg_types[msg.get_type()] += 1

# Prints what's available in this log
print("\n=== Message Types Found in Log ===")
for msg_type, count in sorted(msg_types.items()):
    print(f"{msg_type:20s} : {count} messages")