#!/usr/bin/env python3
import random
import string
import argparse
import re
import sys
from functools import reduce
from enum import Enum

sys.path.insert(0, '/lib/blue-merle')
from at_send import send as at_send


class Modes(Enum):
    DETERMINISTIC = 1
    RANDOM = 2
    STATIC = 3


ap = argparse.ArgumentParser()
ap.add_argument("-v", "--verbose", help="Enables verbose output",
                action="store_true")
ap.add_argument("-g", "--generate-only", help="Only generates an IMEI rather than setting it",
                   action="store_true")
modes = ap.add_mutually_exclusive_group()
modes.add_argument("-d", "--deterministic", help="Switches IMEI generation to deterministic mode", action="store_true")
modes.add_argument("-s", "--static", help="Sets user-defined IMEI",
                   action="store")
modes.add_argument("-r", "--random", help="Sets random IMEI",
                   action="store_true")

# Example IMEI: 490154203237518
imei_length = 14  # without validation digit
imei_prefix = ["35674108", "35290611", "35397710", "35323210", "35384110",
               "35982748", "35672011", "35759049", "35266891", "35407115",
               "35538025", "35480910", "35324590", "35901183", "35139729",
               "35479164"]

verbose = False
mode = None

AT_RETRIES = 3


def get_imsi():
    output = at_send('AT+CIMI', retries=AT_RETRIES)
    if verbose:
        print(f'Output of AT+CIMI (Retrieve IMSI) command: {output}')
    imsi_d = re.findall(r'[0-9]{15}', output)
    if verbose:
        print("TEST: Read IMSI is", imsi_d)
    return "".join(imsi_d).encode()


def get_imei():
    output = at_send('AT+GSN', retries=AT_RETRIES)
    if verbose:
        print(f'Output of AT+GSN (Retrieve IMEI) command: {output}')
    imei_d = re.findall(r'[0-9]{15}', output)
    if verbose:
        print("TEST: Read IMEI is", imei_d)
    return "".join(imei_d).encode()


def set_imei(imei):
    # PCIe/MHI caution (RM520N-GL on GL-XE3000): AT+CFUN=1,1 forces a modem
    # reboot, and a modem reboot while the PCIe link is up can wedge the
    # host's PCIe port into an unrecoverable CmpltTO error storm -- the only
    # way out at that point is a full host reboot. We NEVER issue CFUN=1,1
    # here. AT+CFUN=0 / AT+CFUN=1 (no reset flag) is a functionality-mode
    # toggle, not a modem reboot, and is the safe way to bracket the EGMR
    # write. If the new IMEI isn't reflected immediately, we tell the
    # caller to reboot the ROUTER (not just the modem) rather than
    # retrying with a modem reset.
    import subprocess
    subprocess.run(["/etc/init.d/modemmanager", "stop"])
    at_send('AT+CFUN=0', retries=AT_RETRIES)

    cmd = 'AT+EGMR=1,7,"' + imei + '"'
    output = at_send(cmd, retries=AT_RETRIES)
    if verbose:
        print(f'Output of AT+EGMR (Set IMEI) command: {output}')

    at_send('AT+CFUN=1', retries=AT_RETRIES)
    subprocess.run(["/etc/init.d/modemmanager", "start"])

    new_imei = get_imei()
    if verbose:
        print(f"New IMEI: {new_imei} Old IMEI: {imei.encode()}")

    if new_imei == imei.encode():
        print("IMEI has been successfully changed.")
        return True
    else:
        print("IMEI write sent, but could not be verified immediately.")
        print("Reboot the ROUTER (not just the modem) and check again with 'blue-merle read-imei'.")
        return False


def generate_imei(imei_prefix, imsi_d):
    if (mode == Modes.DETERMINISTIC):
        random.seed(imsi_d)

    imei = random.choice(imei_prefix)
    if (verbose):
        print(f"IMEI prefix: {imei}")
    random_part_length = imei_length - len(imei)
    if (verbose):
        print(f"Length of the random IMEI part: {random_part_length}")
    imei += "".join(random.sample(string.digits, random_part_length))
    if (verbose):
        print(f"IMEI without validation digit: {imei}")

    iteration_1 = "".join([c if i % 2 == 0 else str(2*int(c)) for i, c in enumerate(imei)])
    sum = reduce((lambda a, b: int(a) + int(b)), iteration_1)
    validation_digit = (10 - int(str(sum)[-1])) % 10
    if (verbose):
        print(f"Validation digit: {validation_digit}")

    imei = str(imei) + str(validation_digit)
    if (verbose):
        print(f"Resulting IMEI: {imei}")

    return imei


def validate_imei(imei):
    if len(imei) != 14:
        print(f"NOT A VALID IMEI: {imei} - IMEI must be 14 characters in length")
        return False
    validation_digit = int(imei[-1])
    imei_verify = imei[0:14]
    if (verbose):
        print(imei_verify)

    iteration_1 = "".join([c if i % 2 == 0 else str(2*int(c)) for i, c in enumerate(imei_verify)])
    sum = reduce((lambda a, b: int(a) + int(b)), iteration_1)
    if (verbose):
        print(sum)

    validation_digit_verify = (10 - int(str(sum)[-1])) % 10
    if (verbose):
        print(validation_digit_verify)

    if validation_digit == validation_digit_verify:
        print(f"{imei} is CORRECT")
        return True

    print(f"NOT A VALID IMEI: {imei}")
    return False


if __name__ == '__main__':
    args = ap.parse_args()
    imsi_d = None
    if args.verbose:
        verbose = args.verbose
    if args.deterministic:
        mode = Modes.DETERMINISTIC
        imsi_d = get_imsi()
    if args.random:
        mode = Modes.RANDOM
    if args.static is not None:
        mode = Modes.STATIC
        static_imei = args.static

    if mode == Modes.STATIC:
        if validate_imei(static_imei):
            set_imei(static_imei)
        else:
            exit(-1)
    else:
        imei = generate_imei(imei_prefix, imsi_d)
        if (verbose):
            print(f"Generated new IMEI: {imei}")
        if not args.generate_only:
            if not set_imei(imei):
                exit(-1)

    exit(0)
