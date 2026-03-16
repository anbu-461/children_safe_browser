import os

def block_all_outbound():
    print("Blocking all internet access...")
    os.system("netsh advfirewall set allprofiles firewallpolicy blockinbound,blockoutbound")

def allow_all_outbound():
    print("Allowing internet access...")
    os.system("netsh advfirewall set allprofiles firewallpolicy blockinbound,allowoutbound")
