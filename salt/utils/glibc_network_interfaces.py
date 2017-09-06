#!/usr/bin/python

from socket import AF_INET, AF_INET6, AF_PACKET, inet_ntop
from ctypes import (
    Structure, Union, POINTER,
    pointer, byref, get_errno, cast,
    c_ushort, c_byte, c_ubyte, c_void_p, c_char_p, c_uint, c_int, c_uint16, c_uint32
)
import ctypes.util
import ctypes

class struct_sockaddr(Structure):
    _fields_ = [
        ('sa_family', c_ushort),
        ('sa_data', c_ubyte * 14),]

class struct_sockaddr_in(Structure):
    _fields_ = [
        ('sin_family', c_ushort),
        ('sin_port', c_uint16),
        ('sin_addr', c_byte * 4)]

class struct_sockaddr_in6(Structure):
    _fields_ = [
        ('sin6_family', c_ushort),
        ('sin6_port', c_uint16),
        ('sin6_flowinfo', c_uint32),
        ('sin6_addr', c_byte * 16),
        ('sin6_scope_id', c_uint32)]

class struct_sockaddr_ll(Structure):
    _fields_ = [
        ('sll_family', c_ushort),
        ('sll_protocol', c_ushort),
        ('sll_ifindex', c_int),
        ('sll_hatype', c_ushort),
        ('sll_pkttype', c_ubyte),
        ('sll_halen', c_ubyte),
        ('sll_addr', c_ubyte * 8)]

class union_ifa_ifu(Union):
    _fields_ = [
        ('ifu_broadaddr', POINTER(struct_sockaddr)),
        ('ifu_dstaddr', POINTER(struct_sockaddr)),]

class struct_ifaddrs(Structure):
    pass
struct_ifaddrs._fields_ = [
    ('ifa_next', POINTER(struct_ifaddrs)),
    ('ifa_name', c_char_p),
    ('ifa_flags', c_uint),
    ('ifa_addr', POINTER(struct_sockaddr)),
    ('ifa_netmask', POINTER(struct_sockaddr)),
    ('ifa_ifu', union_ifa_ifu),
    ('ifa_data', c_void_p),]

def glibc_network_interfaces():
    libc = ctypes.CDLL(ctypes.util.find_library('c'))
    ifap = POINTER(struct_ifaddrs)()
    ifs = {}
    ok = libc.getifaddrs(byref(ifap))
    if ok != 0:
        return ifs
    try:
        entry = ifap
        while entry:
            ifa = entry.contents

            name = ifa.ifa_name
            label = name

            secondary = (name.find(":") != -1)
            if secondary: name = name.split(':')[0]

            family = ifa.ifa_addr.contents.sa_family

            if name not in ifs: ifs[name] = {}
            if_attrs = ifs[name]

            type = None
            if family == AF_INET:
                type = 'inet'
                addr_sa = cast(ifa.ifa_addr, POINTER(struct_sockaddr_in)).contents
                thing = {'address': inet_ntop(family, addr_sa.sin_addr), 'label': label}
                if ifa.ifa_netmask:
                    netmask_sa = cast(ifa.ifa_netmask, POINTER(struct_sockaddr_in)).contents
                    thing['netmask'] = inet_ntop(family, netmask_sa.sin_addr)
                if ifa.ifa_ifu.ifu_broadaddr:
                    broad_sa = cast(ifa.ifa_ifu.ifu_broadaddr, POINTER(struct_sockaddr_in)).contents
                    thing['broadcast'] = inet_ntop(family, broad_sa.sin_addr)
            elif family == AF_INET6:
                type = 'inet6'
                sa = cast(ifa.ifa_addr, POINTER(struct_sockaddr_in6)).contents
                thing = {'address': inet_ntop(family, sa.sin6_addr)}
                if ifa.ifa_netmask:
                    netmask_sa = cast(ifa.ifa_netmask, POINTER(struct_sockaddr_in6)).contents
                    thing['prefixlen'] = netmask_sa.sin6_addr[0:].count(-1) * 8 # todo
            elif family == AF_PACKET:
                ll = cast(ifa.ifa_addr, POINTER(struct_sockaddr_ll)).contents
                data = ll.sll_addr
                if_attrs['hwaddr'] = ':'.join('%02x' % b for b in data[:6])

            IFF_UP = 1

            if type: thing['up'] = bool(ifa.ifa_flags & IFF_UP)

            if secondary:
                thing['type'] = type
                type = 'secondary'

            if type:
                if type not in if_attrs: if_attrs[type] = []
                if_attrs[type].append(thing)

            entry = ifa.ifa_next

        return ifs
    finally:
        libc.freeifaddrs(ifap)
