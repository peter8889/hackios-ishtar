#!/usr/bin/env python3
"""Print the modem/IPA SoC addresses of a Qualcomm phone as HakiOS boot-args, from its device tree.

usage: tools/soc-args.py DEVICE-TREE.dtb

The kernel's modem and IPA drivers (bsd/dev/hakios.mpss.c, hakios.ipa.c) carry the first phone's
addresses as defaults and take any that differ from boot-args soc_* (see soc_override there). This
reads a phone's own flattened device tree -- /sys/firmware/fdt on a rooted phone, or the dtb a port
already has -- and prints the soc_* it needs, which devices/<name>/soc.args holds and the run
scripts pass along. Only numbers are read out; no part of the tree is copied.

The first phone (POCO X5 Pro, SM7325) and a newer one (Xiaomi 13 Ultra, SM8550) describe the same
hardware differently, so the lookups here are made by what a node *is* rather than by one exact
spelling:

  - a compatible is matched by its family: "qcom,ipa" also matches "qcom,sm8550-ipa", and
    "qcom,aoss-qmp" also matches "qcom,sm8550-aoss-qmp" (the SoC's own name is in front);
  - the IPA's registers are taken from the pair named "ipa-reg" or "ipa-base" and the GSI's from
    the pair named "gsi" or "gsi-base" -- SM7325 names them "ipa-base"/"gsi-base" and puts the
    IPA's registers 0x40000 into the region, SM8550 names them "ipa-reg"/"gsi" and points at the
    registers themselves;
  - the address and size cells are counted from the node's own #address-cells/#size-cells, which
    its parent sets: the tree under /soc uses one of each, the reserved-memory under it two;
  - a reserved-memory node is found by what it holds (the command DB, the modem's memory, the
    IPA's firmware area), not by its name, which differs between the two SoCs;
  - the IPA's SMMU streams are read from the iommus of whichever node carries them (SM7325 has
    two child nodes, SM8550 has them on the IPA's own node).

Everything a node offers under more than one name is used at most once: the first match wins.
"""
import struct
import sys


def nodes_of(blob):
    if blob[:4] != b'\xd0\x0d\xfe\xed':
        sys.exit('soc-args.py: not a flattened device tree')
    off_struct, off_strings = struct.unpack('>II', blob[8:16])
    size_strings, = struct.unpack('>I', blob[32:36])
    strings = blob[off_strings:off_strings + size_strings]
    out, path, at = {}, [], off_struct
    while True:
        token, = struct.unpack('>I', blob[at:at + 4])
        at += 4
        if token == 1:                                  # FDT_BEGIN_NODE
            end = blob.index(b'\0', at)
            path.append(blob[at:end].decode())
            at = (end + 4) & ~3
            out['/'.join(path)] = {}
        elif token == 2:                                # FDT_END_NODE
            path.pop()
        elif token == 3:                                # FDT_PROP
            length, name_off = struct.unpack('>II', blob[at:at + 8])
            at += 8
            name = strings[name_off:strings.index(b'\0', name_off)].decode()
            out['/'.join(path)][name] = blob[at:at + length]
            at = (at + length + 3) & ~3
        elif token == 9:                                # FDT_END
            return out
        elif token != 4:                                # 4 = FDT_NOP
            sys.exit(f'soc-args.py: unexpected token {token}')


def compat_list(props):
    return [c.decode() for c in props.get('compatible', b'').split(b'\0') if c]


def compat_name(compatible):
    """The compatible's name without its vendor: "qcom,sm8550-ipa" -> "sm8550-ipa"."""
    return compatible.split(',', 1)[1] if ',' in compatible else compatible


def family(compatible):
    """The compatible without the SoC's own name in front of it: "qcom,sm8550-ipa" -> "ipa"."""
    rest = compat_name(compatible)
    # the SoC's name is a model number: sm8550, sc7280, sm8250, ...
    parts = rest.split('-', 1)
    if len(parts) == 2 and parts[0][:2] in ('sm', 'sc', 'ms') and parts[0][2:].isdigit():
        return parts[1]
    return rest


def find(nodes, *compatibles):
    """The first node whose compatible is one of these, by family: "qcom,ipa" matches "qcom,sm8550-ipa"."""
    wanted = {compat_name(c) for c in compatibles}
    for path, props in nodes.items():
        for compatible in compat_list(props):
            name = compat_name(compatible)
            if name in wanted or family(compatible) in wanted:
                return path, props
    return None, None


def find_all(nodes, *compatibles):
    """Every node whose compatible is one of these, by family."""
    wanted = {compat_name(c) for c in compatibles}
    out = []
    for path, props in nodes.items():
        for compatible in compat_list(props):
            name = compat_name(compatible)
            if name in wanted or family(compatible) in wanted:
                out.append((path, props))
                break
    return out


def find_named(nodes, leaf):
    """The node whose last path component begins with `leaf` (e.g. apps-smmu@..., several SMMUs share a compatible)."""
    for path, props in nodes.items():
        if path.rsplit('/', 1)[-1].split('@', 1)[0] == leaf:
            return path, props
    return None, None


def u32(value, index=0):
    return struct.unpack_from('>I', value, index * 4)[0]


def cell_counts(nodes, path):
    """The address and size cells in force at a node: the nearest ancestor's that has them (the
    root's defaults are 2 and 1). A node's own #address-cells applies to its children, so the
    search starts at the node's parent."""
    address_cells, size_cells = 2, 1
    parts = path.split('/')
    for i in range(len(parts) - 1, 0, -1):
        ancestor = '/'.join(parts[:i])
        props = nodes.get(ancestor)
        if not props:
            continue
        if '#address-cells' in props:
            address_cells = u32(props['#address-cells'])
        if '#size-cells' in props:
            size_cells = u32(props['#size-cells'])
        if '#address-cells' in props or '#size-cells' in props:
            break
    return address_cells, size_cells


def reg_pairs(nodes, path, props):
    """The node's reg as (address, size) pairs, with the address and size cells it is written with.

    A cell is 32 bits and a multi-cell number is written most significant word first, so a two-cell
    address is the first cell shifted up and the second one as it is.
    """
    reg = props.get('reg')
    if not reg:
        return []
    address_cells, size_cells = cell_counts(nodes, path)
    cells = len(reg) // 4
    step = address_cells + size_cells
    if step == 0:
        return []
    out = []
    for i in range(0, cells - step + 1, step):
        address = 0
        for c in range(address_cells):
            address |= u32(reg, i + c) << (32 * (address_cells - 1 - c))
        size = 0
        for c in range(size_cells):
            size |= u32(reg, i + address_cells + c) << (32 * (size_cells - 1 - c))
        out.append((address, size))
    return out


def reg_by_name(nodes, path, props, *names):
    """The address of the reg pair with one of these reg-names, if the node names its pairs."""
    names_in = props.get('reg-names')
    if not names_in:
        return None
    pairs = reg_pairs(nodes, path, props)
    for i, name in enumerate([n.decode() for n in names_in.split(b'\0') if n]):
        if name in names and i < len(pairs):
            return pairs[i][0]
    return None


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    # the output is read by scripts and compared byte for byte: the line ending does not depend on
    # the machine this runs on
    sys.stdout.reconfigure(newline='\n')
    nodes = nodes_of(open(sys.argv[1], 'rb').read())
    args = []
    used = set()                                  # the nodes already read, so that one node is not used twice

    def take(path):
        if path in used:
            return None
        used.add(path)
        return path

    # --- the IPA and the GSI ---------------------------------------------------------------------
    # SM7325: reg-names "ipa-base" (the region's start; the registers the driver maps are 0x40000
    # into it) and "gsi-base" (the GSI's base, given directly).
    # SM8550: reg-names "ipa-reg" (the registers themselves), "ipa-shared" and "gsi".
    path, ipa = find(nodes, 'qcom,ipa')
    if ipa:
        pairs = reg_pairs(nodes, path, ipa)
        ipa_base = reg_by_name(nodes, path, ipa, 'ipa-reg')
        gsi_base = reg_by_name(nodes, path, ipa, 'gsi', 'gsi-base')
        ipa_sram = reg_by_name(nodes, path, ipa, 'ipa-shared')
        if ipa_base is None:
            # the old naming: the region starts at the first pair and the registers are 0x40000 in
            ipa_base = reg_by_name(nodes, path, ipa, 'ipa-base')
            if ipa_base is not None:
                ipa_base += 0x40000
            elif pairs:
                ipa_base = pairs[0][0] + 0x40000
        if gsi_base is None and len(pairs) > 1:
            gsi_base = pairs[1][0]
        if ipa_base is not None:
            args.append(('soc_ipa_base', ipa_base))
        if gsi_base is not None:
            args.append(('soc_gsi_base', gsi_base))
        if ipa_sram is not None:
            args.append(('soc_ipa_sram', ipa_sram))
        take(path)

    # The IPA's iommus: which SMMU its streams go through, and the streams themselves. They are
    # (phandle, stream id, mask) groups -- three cells each, the number the SMMU's #iommu-cells
    # says. SM7325 puts one group on each of two child nodes (the application processors' and the
    # UC's); SM8550 puts both on the IPA's own node.
    def iommu_groups(props):
        iommus = props.get('iommus')
        if not iommus or len(iommus) < 8:
            return []
        cells = len(iommus) // 4
        stride = 3
        phandle = u32(iommus, 0)
        for other_path, other in nodes.items():
            if 'phandle' in other and u32(other['phandle']) == phandle:
                count = other.get('#iommu-cells')
                if count:
                    stride = 1 + u32(count)
                break
        return [(u32(iommus, i), u32(iommus, i + 1)) for i in range(0, cells - stride + 1, stride)]

    groups = []
    for path, props in find_all(nodes, 'qcom,ipa-smmu-ap-cb'):
        groups = iommu_groups(props)
        if groups:
            break
    if not groups and ipa:
        groups = iommu_groups(ipa)

    # --- the mailboxes and the controller --------------------------------------------------------
    def block(compatibles, arg, index=0):
        path, props = find(nodes, *compatibles)
        if path and take(path):
            pairs = reg_pairs(nodes, path, props)
            if len(pairs) > index:
                args.append((arg, pairs[index][0]))

    block(['qcom,ipcc'], 'soc_ipcc')              # the IPCC mailbox
    block(['qcom,aoss-qmp'], 'soc_aoss')          # the AOSS mailbox (its compatible names the SoC)

    # the RPMh controller: the application processors' is the one whose third driver (drv-2) the
    # tree names; the others (the AOP's, the CDSP's) have only one.
    for path, props in find_all(nodes, 'qcom,rpmh-rsc'):
        if 'reg-names' not in props:
            continue
        names = [n.decode() for n in props['reg-names'].split(b'\0') if n]
        if 'drv-2' not in names:
            continue
        pairs = reg_pairs(nodes, path, props)
        if len(pairs) > 2:
            args.append(('soc_rsc', pairs[2][0]))
        break

    # The application processors' SMMU: the IPA's streams go through it, so it is the one its
    # iommus point at. (On a tree that names it "iommu@..." rather than "apps-smmu@..." -- as
    # upstream Linux's does -- the name alone would not find it.)
    if groups:
        smmu_phandle = groups[0][0]
        for path, props in nodes.items():
            if 'phandle' in props and u32(props['phandle']) == smmu_phandle:
                pairs = reg_pairs(nodes, path, props)
                if pairs:
                    args.append(('soc_apps_smmu', pairs[0][0]))
                break

    # --- the memory addresses --------------------------------------------------------------------
    # The command DB and the modem's region are reserved-memory nodes; their names differ between
    # the SoCs ("cmd_db@..." on SM7325, "aop-cmd-db-region@..." on SM8550), so they are found by what
    # they hold: the command DB says so in its compatible, and the modem's memory is the region the
    # IPA's firmware and the modem's image are in.
    by_phandle = {}
    for path, props in nodes.items():
        if 'phandle' in props:
            by_phandle[u32(props['phandle'])] = (path, props)

    def reserved_by_compatible(compatibles, arg):
        path, props = find(nodes, *compatibles)
        if path and take(path):
            pairs = reg_pairs(nodes, path, props)
            if pairs:
                args.append((arg, pairs[0][0]))

    reserved_by_compatible(['qcom,cmd-db'], 'soc_cmd_db')

    def reserved_by_name(leaves, arg):
        for leaf in leaves:
            path, props = find_named(nodes, leaf)
            if path and take(path):
                pairs = reg_pairs(nodes, path, props)
                if pairs:
                    args.append((arg, pairs[0][0]))
                    return

    reserved_by_name(['mpss', 'mpss-region'], 'soc_mpss_mem')       # the modem's memory
    reserved_by_name(['ipa_gsi', 'ipa-gsi-region'], 'modem_ipa_fw_at')  # where the IPA's firmware is loaded

    path, smem = find(nodes, 'qcom,smem')
    if path and take(path) and 'memory-region' in smem:
        target = by_phandle.get(u32(smem['memory-region']))
        if target:
            pairs = reg_pairs(nodes, target[0], target[1])
            if pairs:
                args.append(('soc_smem', pairs[0][0]))
    path, imem = find(nodes, 'qcom,msm-imem', 'qcom,imem')
    if path and take(path):
        pairs = reg_pairs(nodes, path, imem)
        if pairs:
            args.append(('soc_imem', pairs[0][0] & ~0x1fffff))    # the 2 MB block that holds it

    # --- the IPA's streams ------------------------------------------------------------------------
    # SM8550 puts both streams on the IPA's own node; SM7325 puts one on each of two child nodes
    # (the application processors' and the UC's), so each is looked for on its own node too.
    if groups:
        args.append(('soc_ipa_stream', groups[0][1]))
    if len(groups) > 1:
        args.append(('soc_ipa_stream_uc', groups[1][1]))
    else:
        for path, props in find_all(nodes, 'qcom,ipa-smmu-uc-cb'):
            uc = iommu_groups(props)
            if uc:
                args.append(('soc_ipa_stream_uc', uc[0][1]))
                break
    # --- the PAS identifiers and the IPA's firmware name --------------------------------------------
    def pas_id(leaves, arg):
        for leaf in leaves:
            path, props = find_named(nodes, leaf)
            if path and take(path) and 'qcom,pas-id' in props:
                args.append((arg, u32(props['qcom,pas-id'])))
                return

    pas_id(['qcom,mss'], 'soc_pas_mpss')
    pas_id(['qcom,ipa_fws'], 'soc_pas_ipa')

    ipa_fw_name = None
    for path, props in nodes.items():
        if 'qcom,firmware-name' in props and 'ipa_fws' in path:
            ipa_fw_name = props['qcom,firmware-name'].split(b'\0')[0].decode()
            break

    for name, value in args:
        print(f'{name}={value:#x}')
    if ipa_fw_name:
        print(f'soc_ipa_fw={ipa_fw_name}')
    if not args:
        sys.exit('soc-args.py: found none of the expected nodes; is this the phone\'s own device tree?')


if __name__ == '__main__':
    main()
