#!/usr/bin/env python3
"""Make hw.target answer on this kernel, so that a user space of iOS 16.6 or later can be run on
it: dyld asks the kernel for the hardware target and gives up without it ("failed to query
hardware target"), and nothing that needs dyld can start.

hw.target is answered by PEGetTargetName(), which asks the platform expert -- Apple's
IOPlatformExpert, which is not in the open source and is not there on this port: gIOPlatform is
null and the call fails, so the sysctl returns EINVAL. The device tree's root does say the
target type ("target-type", which the loader copies from the phone's own device tree, so it is the
phone's own answer: "D22" on the iPhone X), and that is what is used here.

usage: fix-hw-target.py [ROOT]      (ROOT is the kernel's source tree)
"""
import io
import sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else '.'

p = ROOT + '/bsd/kern/kern_mib.c'
s = io.open(p, encoding='utf-8').read()

OLD = r'''	case HW_TARGET:
		bzero(dummy, sizeof(dummy));
		if (!PEGetTargetName(dummy, 64)) {
			return EINVAL;
		}
		dummy[64] = 0;
		return SYSCTL_OUT(req, dummy, strlen(dummy) + 1);'''

NEW = r'''	case HW_TARGET:
		bzero(dummy, sizeof(dummy));
		if (!PEGetTargetName(dummy, 64)) {
			/*
			 * There is no platform expert on this port (Apple's is not in the open
			 * source), so the target is taken from the device tree instead: the root
			 * of it says "target-type", which the loader copies from the phone's own
			 * device tree ("D22" on the iPhone X). dyld asks for this and gives up
			 * without it, so nothing that needs dyld can start without it.
			 */
			DTEntry entry;
			const void * value;
			unsigned int size;

			if (SecureDTFindEntry("name", "device-tree", &entry) == kSuccess &&
			    SecureDTGetProperty(entry, "target-type", &value, &size) == kSuccess) {
				strlcpy(dummy, (const char *)value, sizeof(dummy));
				if (dummy[0] != '\0') {
					dummy[64] = 0;
					return SYSCTL_OUT(req, dummy, strlen(dummy) + 1);
				}
			}
			return EINVAL;
		}
		dummy[64] = 0;
		return SYSCTL_OUT(req, dummy, strlen(dummy) + 1);'''

assert OLD in s, 'kern_mib.c: the hw.target case is not the one this patch knows'
s = s.replace(OLD, NEW, 1)
io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('kern_mib.c: hw.target falls back to the device tree')
