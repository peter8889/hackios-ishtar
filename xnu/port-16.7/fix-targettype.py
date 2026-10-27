#!/usr/bin/env python3
"""Make hw.targettype work on this kernel, so that a user space of iOS 16.6 or later can be run
on it: launchd asks the kernel for the board's target type (hw.targettype) and gives up without
it ("failed to query hardware target").

XNU has the sysctl already (iokit/Kernel/IOPMrootDomain.cpp: SYSCTL_PROC(_hw, OID_AUTO,
targettype, ...)), but its handler takes the value from the property "target-type" of the root
domain in the IORegistry's service plane, and nothing puts it there on this port: the device
tree's tree hangs in the device tree's plane. The device tree's root does say "target-type" (the
loader copies that property from the phone's own device tree, so it is the phone's own answer:
"D22" on the iPhone X), so the handler is taught to read it from there.

usage: fix-targettype.py [ROOT]      (ROOT is the kernel's source tree)
"""
import io
import sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else '.'

p = ROOT + '/iokit/Kernel/IOPMrootDomain.cpp'
s = io.open(p, encoding='utf-8').read()

NEW = r'''static int
sysctl_targettype SYSCTL_HANDLER_ARGS
{
	IOService * root;
	OSSharedPtr<OSObject>  obj;
	OSData *    data;
	char        tt[32];
	DTEntry     entry;
	const void * value;
	unsigned int size;

	tt[0] = '\0';
	/*
	 * The root of the device tree says it ("target-type"). The loader copies that property
	 * from the phone's own device tree, so this is the phone's own answer ("D22" on the
	 * iPhone X). It is read here rather than from the root domain's property, because the
	 * device tree's tree hangs in the device tree's plane of the IORegistry and nothing
	 * copies its root's properties to the service plane on this port.
	 */
	if (SecureDTFindEntry("name", "device-tree", &entry) == kSuccess &&
	    SecureDTGetProperty(entry, "target-type", &value, &size) == kSuccess) {
		strlcpy(tt, (const char *)value, sizeof(tt));
		if (tt[0] != '\0') {
			return sysctl_io_string(req, tt, 0, 0, NULL);
		}
	}
	root = IOService::getServiceRoot();
	if (root && (obj = root->copyProperty(gIODTTargetTypeKey))) {
		if ((data = OSDynamicCast(OSData, obj.get()))) {
			strlcpy(tt, (const char *) data->getBytesNoCopy(), sizeof(tt));
		}
	}
	return sysctl_io_string(req, tt, 0, 0, NULL);
}'''

i = s.find('static int\nsysctl_targettype SYSCTL_HANDLER_ARGS')
j = s.find('SYSCTL_PROC(_hw, OID_AUTO, targettype', i)
assert i >= 0 and j > i, 'IOPMrootDomain.cpp: the handler is not where this patch expects it'
s = s[:i] + NEW + '\n' + s[j:]
print('IOPMrootDomain.cpp: the handler reads the device tree')

old = '#include <IOKit/IODeviceTreeSupport.h>'
new = '#include <IOKit/IODeviceTreeSupport.h>\n#include <pexpert/device_tree.h>'
if '#include <pexpert/device_tree.h>' not in s:
    assert old in s, 'IOPMrootDomain.cpp: the includes are not the ones this patch knows'
    s = s.replace(old, new, 1)
    print('IOPMrootDomain.cpp: the device tree header included')

io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
