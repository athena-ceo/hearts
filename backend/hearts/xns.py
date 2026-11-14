# Copyright (c) 2026 Athena Decision Systems SAS.
"""XNS as Medley speaks it, for one machine on a NetHub: IDP packets, SPP connections and Courier calls.

A NetHub is Maiko's virtual Ethernet (maiko/src/ether_nethub.c): each machine holds one TCP connection, and a
packet is a 2-byte length followed by that many bytes of Ethernet frame.  A `Wire` is the house's end of one
such connection.  It answers only frames addressed to the house, so machines on the hub never reach each other.

What is here follows Medley's own implementation (sources/SPP, sources/COURIER, lispusers/COURIERSERVE in the
260810 release), which is the only other end it has been run against:

- IDP: no checksum (65535, which Medley accepts), network 0 on both sides.
- SPP: both directions of opening, acknowledgements, the allocation window, retransmission, the END exchange.
  No attention packets and no bulk data.
- Courier version 3: calls in both directions, RETURN, ABORT and REJECT.  No expedited (single packet) calls.
"""
from __future__ import annotations

import asyncio
import logging
import socket as socketlib
import struct

log = logging.getLogger("hearts.xns")

XNS = b"\x06\x00"  # The Ethernet type of an IDP packet.
BROADCAST = b"\xff" * 6
TYPE_SPP = 5
COURIER_SOCKET = 5
SYSTEM, SEND_ACK, ATTENTION, EOM = 0x80, 0x40, 0x20, 0x10
DS_COURIER, DS_END, DS_END_REPLY = 0, 254, 255
MAX_DATA = 534  # An IDP packet is at most 576 bytes: 30 of header, 12 of SPP header.
WINDOW = 8
RESEND_AFTER = 1.5
GIVE_UP_AFTER = 120.0
CALL, REJECT, RETURN, ABORT = 0, 1, 2, 3
COURIER_VERSION = 3


def later(a, b):
    """True if sequence number a comes after b.  They are 16 bits and wrap."""
    return 0 < ((a - b) & 0xFFFF) < 0x8000


class Closed(ConnectionError):
    pass


# Courier values --------------------------------------------------------------------------------------------------
class Writer:
    def __init__(self):
        self.data = bytearray()

    def word(self, n):
        self.data += struct.pack(">H", n & 0xFFFF)
        return self

    def long(self, n):
        self.data += struct.pack(">I", n)
        return self

    def boolean(self, b):
        return self.word(1 if b else 0)

    def string(self, s):
        raw = s.encode("latin-1", "replace")[:1000]
        self.word(len(raw))
        self.data += raw + (b"\0" if len(raw) % 2 else b"")
        return self

    def sequence(self, items, put):
        self.word(len(items))
        for item in items:
            put(self, item)
        return self

    def bytes(self):
        return bytes(self.data)


class Reader:
    """Reads a Courier message.  Anything short or over-long raises ValueError."""

    def __init__(self, data):
        self.data, self.at = data, 0

    def _take(self, n):
        if self.at + n > len(self.data):
            raise ValueError("the message is too short")
        part = self.data[self.at:self.at + n]
        self.at += n
        return part

    def word(self):
        return struct.unpack(">H", self._take(2))[0]

    def integer(self):
        return struct.unpack(">h", self._take(2))[0]

    def long(self):
        return struct.unpack(">I", self._take(4))[0]

    def boolean(self):
        return self.word() != 0

    def string(self, limit=200):
        n = self.word()
        if n > limit:
            raise ValueError("a string is too long")
        text = self._take(n).decode("latin-1")
        if n % 2:
            self._take(1)
        return text

    def sequence(self, get, limit=64):
        n = self.word()
        if n > limit:
            raise ValueError("a sequence is too long")
        return [get(self) for _ in range(n)]


class CourierError(Exception):
    """An ABORT (a declared error, with its number and arguments) or a REJECT from the other end."""

    def __init__(self, kind, number=None, body=b""):
        super().__init__(f"{kind} {number}")
        self.kind, self.number, self.body = kind, number, body


# SPP -------------------------------------------------------------------------------------------------------------
class Spp:
    """One sequenced packet connection.  send() and receive() carry whole messages."""

    def __init__(self, wire, my_socket, peer_socket, my_id, peer_id=0):
        self.wire, self.my_socket, self.peer_socket = wire, my_socket, peer_socket
        self.my_id, self.peer_id = my_id, peer_id
        self.seq = 0  # The next data packet's number.
        self.ack = 0  # The next number expected from the other end.
        self.peer_alloc = 0  # The highest number the other end will take.
        self.unacked = {}  # seq -> (control, datastream type, data)
        self.buffer = bytearray()
        self.messages = asyncio.Queue()
        self.established = asyncio.Event()
        self.window = asyncio.Event()
        self.closed = False
        self.end_sent = False
        self.heard = asyncio.get_event_loop().time()
        self.resender = asyncio.create_task(self._resend())

    def _put(self, control, dstype, seq, data=b""):
        head = struct.pack(">BBHHHHH", control, dstype, self.my_id, self.peer_id, seq, self.ack,
                           (self.ack + WINDOW - 1) & 0xFFFF)
        self.wire.send_idp(TYPE_SPP, self.peer_socket, self.my_socket, head + data)

    def probe(self):
        self._put(SYSTEM | SEND_ACK, 0, self.seq)

    def _acknowledge(self):
        self._put(SYSTEM, 0, self.seq)

    def packet(self, src_socket, payload):
        if len(payload) < 12 or self.closed:
            return
        control, dstype, src_id, dst_id, seq, ack, alloc = struct.unpack(">BBHHHHH", payload[:12])
        data = payload[12:]
        if dst_id not in (0, self.my_id):
            return
        if self.peer_id == 0:  # The answer to our opening packet: a server answers from a socket of its own.
            self.peer_id, self.peer_socket = src_id, src_socket
        elif src_id != self.peer_id:
            return
        self.heard = asyncio.get_event_loop().time()
        first = not self.established.is_set()
        for s in [s for s in self.unacked if later(ack, s)]:
            del self.unacked[s]
        if first or later(alloc, self.peer_alloc):
            self.peer_alloc = alloc
        self.established.set()
        self.window.set()
        if control & SYSTEM:
            if control & SEND_ACK:
                self._acknowledge()
            return
        if seq == self.ack:
            self.ack = (self.ack + 1) & 0xFFFF
            if dstype == DS_END:
                self._data(0, DS_END_REPLY, b"")
                self.close()
                return
            if dstype == DS_END_REPLY:
                if self.end_sent:
                    self._data(0, DS_END_REPLY, b"")
                self.close()
                return
            if not control & ATTENTION:
                self.buffer += data
                if len(self.buffer) > 8000 or self.messages.qsize() > 32:  # More than any honest caller sends.
                    self.close()
                    return
                if control & EOM:
                    self.messages.put_nowait(bytes(self.buffer))
                    self.buffer.clear()
        self._acknowledge()  # Also for a packet seen before, or one that came early: say where we are.

    def _data(self, control, dstype, data):
        seq = self.seq
        self.seq = (seq + 1) & 0xFFFF
        self.unacked[seq] = (control | SEND_ACK, dstype, data)
        self._put(control, dstype, seq, data)

    async def send(self, data, eom=True):
        chunks = [data[i:i + MAX_DATA] for i in range(0, len(data), MAX_DATA)] or [b""]
        for i, chunk in enumerate(chunks):
            while later(self.seq, self.peer_alloc) and not self.closed:
                self.window.clear()
                await self.window.wait()
            if self.closed:
                raise Closed("the connection closed")
            last = i == len(chunks) - 1
            control = (EOM if last and eom else 0) | (SEND_ACK if last or self.seq == self.peer_alloc else 0)
            self._data(control, DS_COURIER, chunk)

    async def receive(self):
        message = await self.messages.get()
        if message is None:
            self.messages.put_nowait(None)
            raise Closed("the connection closed")
        return message

    async def _resend(self):
        try:
            while not self.closed:
                await asyncio.sleep(RESEND_AFTER)
                now = asyncio.get_event_loop().time()
                if not self.unacked:
                    self.heard = now
                    continue
                if now - self.heard > GIVE_UP_AFTER:
                    log.info("no answer on a connection; closing it")
                    self.close()
                    return
                for seq in sorted(self.unacked, key=lambda s: (s - self.seq) & 0xFFFF):
                    control, dstype, data = self.unacked[seq]
                    self._put(control, dstype, seq, data)
        except asyncio.CancelledError:
            pass

    async def finish(self):
        """Close politely: END, and the other end answers END-REPLY."""
        if not self.closed and self.established.is_set():
            self.end_sent = True
            self._data(EOM, DS_END, b"")
            for _ in range(20):
                if self.closed:
                    break
                await asyncio.sleep(0.1)
        self.close()

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.unacked.clear()
        self.messages.put_nowait(None)
        self.window.set()
        self.established.set()
        if self.resender is not asyncio.current_task():
            self.resender.cancel()
        self.wire.forget(self)


# Courier ---------------------------------------------------------------------------------------------------------
class CourierClient:
    """Calls a Courier server on the other machine, one call at a time."""

    def __init__(self, spp):
        self.spp = spp
        self.first = True
        self.lock = asyncio.Lock()

    @property
    def closed(self):
        return self.spp.closed

    async def call(self, program, version, procedure, arguments=b""):
        """The result's bytes.  CourierError for an ABORT or a REJECT; Closed if the connection is gone."""
        async with self.lock:
            head = Writer().word(CALL).word(0).long(program).word(version).word(procedure).bytes()
            await self.spp.send(head + arguments)
            message = await self.spp.receive()
            if self.first:  # Medley's server sends its version range with no end of message: it leads the first reply.
                message = message[4:]
                self.first = False
            r = Reader(message)
            kind = r.word()
            r.word()
            if kind == RETURN:
                return message[4:]
            if kind == ABORT:
                raise CourierError("abort", r.word(), message[6:])
            raise CourierError("reject", r.word() if len(message) >= 6 else None)


async def serve_courier(spp, handler):
    """Answer Courier calls on a connection the other machine opened.

    handler(program, version, procedure, Reader) returns the result's bytes, or raises CourierError("abort", n, body)
    or CourierError("reject", n).  It may be a coroutine function.
    """
    try:
        first = await spp.receive()
        low, high = struct.unpack(">HH", first[:4]) if len(first) >= 4 else (0, 0)
        await spp.send(struct.pack(">HH", COURIER_VERSION, COURIER_VERSION), eom=False)
        if not low <= COURIER_VERSION <= high:
            return
        pending = first[4:]
        while True:
            message = pending or await spp.receive()
            pending = b""
            try:
                r = Reader(message)
                kind, transaction = r.word(), r.word()
                if kind != CALL:
                    raise ValueError("not a call")
                program, version, procedure = r.long(), r.word(), r.word()
            except ValueError:
                return
            try:
                result = handler(program, version, procedure, r)
                if asyncio.iscoroutine(result):
                    result = await result
                reply = Writer().word(RETURN).word(transaction).bytes() + (result or b"")
            except CourierError as e:
                if e.kind == "abort":
                    reply = Writer().word(ABORT).word(transaction).word(e.number).bytes() + e.body
                else:
                    reply = Writer().word(REJECT).word(transaction).word(e.number if e.number is not None else 0xFFFF).bytes()
            except ValueError:  # Arguments that don't read as the procedure's types.
                reply = Writer().word(REJECT).word(transaction).word(3).bytes()
            except Exception:  # A fault of ours: tell the caller, and keep serving.
                log.exception("a Courier call failed (program %s, procedure %s)", program, procedure)
                reply = Writer().word(REJECT).word(transaction).word(0xFFFF).bytes()
            await spp.send(reply)
    except Closed:
        pass
    finally:
        spp.close()


# The wire --------------------------------------------------------------------------------------------------------
class Wire:
    """The house's end of one machine's NetHub connection."""

    MAX_INCOMING = 4

    def __init__(self, reader, writer, mac, handler):
        self.reader, self.writer, self.mac, self.handler = reader, writer, mac, handler
        self.peer = None  # The other machine's host number, from its first packet to us.
        self.incoming = {}  # its socket -> Spp, for connections it opened to our Courier socket
        self.outgoing = {}  # our socket -> Spp
        self.next_socket = 3000
        self.next_id = 1
        self.closed = False
        self.servers = set()
        sock = writer.get_extra_info("socket")
        if sock is not None:
            sock.setsockopt(socketlib.IPPROTO_TCP, socketlib.TCP_NODELAY, 1)

    async def run(self):
        """Read frames until the machine goes away."""
        try:
            while True:
                size = int.from_bytes(await self.reader.readexactly(2), "big")
                if size < 14 or size > 1600:
                    return
                self.frame(await self.reader.readexactly(size))
        except (asyncio.IncompleteReadError, ConnectionError, OSError):
            pass
        finally:
            self.close()

    def frame(self, frame):
        if frame[12:14] != XNS or frame[0:6] not in (self.mac, BROADCAST) or len(frame) < 44:
            return
        packet = frame[14:]
        length = int.from_bytes(packet[2:4], "big")
        if length < 30 or length > len(packet) or packet[10:16] != self.mac:
            return
        src_host, src_socket = packet[22:28], int.from_bytes(packet[28:30], "big")
        dst_socket = int.from_bytes(packet[16:18], "big")
        if self.peer is None:
            self.peer = bytes(src_host)
        elif src_host != self.peer:
            return
        if packet[5] != TYPE_SPP:
            return
        body = bytes(packet[30:length])
        spp = self.outgoing.get(dst_socket)
        if spp is None and dst_socket == COURIER_SOCKET:
            spp = self.incoming.get(src_socket)
            if spp is None:
                spp = self._accept(src_socket, body)
        if spp is not None:
            spp.packet(src_socket, body)

    def _accept(self, src_socket, body):
        """A machine opening a connection to our Courier socket: its first packet names no connection of ours."""
        if len(body) < 12 or len(self.incoming) >= self.MAX_INCOMING:
            return None
        src_id, dst_id = struct.unpack(">HH", body[2:6])
        if dst_id != 0 or src_id == 0:
            return None
        spp = Spp(self, COURIER_SOCKET, src_socket, self._new_id(), src_id)
        self.incoming[src_socket] = spp
        task = asyncio.create_task(serve_courier(spp, self.handler))
        self.servers.add(task)
        task.add_done_callback(self.servers.discard)
        return spp

    def _new_id(self):
        self.next_id = self.next_id % 0xFFFF + 1
        return self.next_id

    async def open(self, timeout=20.0):
        """A Courier client on the other machine's Courier server (COURIER.START.SERVER there)."""
        if self.peer is None or self.closed:
            raise Closed("the machine has not been heard from")
        self.next_socket = 3000 + (self.next_socket - 2999) % 20000
        spp = Spp(self, self.next_socket, COURIER_SOCKET, self._new_id())
        self.outgoing[spp.my_socket] = spp
        try:
            deadline = asyncio.get_event_loop().time() + timeout
            while not spp.established.is_set():
                if asyncio.get_event_loop().time() > deadline:
                    raise Closed("its Courier server did not answer")
                spp.probe()
                try:
                    await asyncio.wait_for(spp.established.wait(), 1.0)
                except asyncio.TimeoutError:
                    pass
            if spp.closed:
                raise Closed("the connection closed")
            await spp.send(struct.pack(">HH", COURIER_VERSION, COURIER_VERSION))
        except Closed:
            spp.close()
            raise
        return CourierClient(spp)

    def send_idp(self, kind, dst_socket, src_socket, body):
        if self.closed or self.peer is None:
            return
        packet = (b"\xff\xff" + struct.pack(">HBB", 30 + len(body), 0, kind)
                  + bytes(4) + self.peer + struct.pack(">H", dst_socket)
                  + bytes(4) + self.mac + struct.pack(">H", src_socket) + body)
        if len(packet) % 2:
            packet += b"\0"
        frame = self.peer + self.mac + XNS + packet
        try:  # One write: Maiko reads the length and the frame together, and drops a frame that comes in two parts.
            self.writer.write(len(frame).to_bytes(2, "big") + frame)
        except Exception:
            self.close()

    def forget(self, spp):
        if self.outgoing.get(spp.my_socket) is spp:
            del self.outgoing[spp.my_socket]
        for key, value in list(self.incoming.items()):
            if value is spp:
                del self.incoming[key]

    def close(self):
        if self.closed:
            return
        self.closed = True
        for spp in list(self.incoming.values()) + list(self.outgoing.values()):
            spp.close()
        try:
            self.writer.close()
        except Exception:
            pass
