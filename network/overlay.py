#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging
import random
import socket
import threading
import uuid

import mpd
import mpd.playlist
import network
from network.connection_waiter import ConnectionWaiter
from network.group import GroupLeader, GroupPeer
from network.peer import Peer
import proto
from signalqueue import QueueSet
from bounded_dict import BoundedDict

N_NEIGHBOURS = 2  # number of neighbours every node tries to have


class Overlay(threading.Thread):
    '''Takes care of joining, managing and searching the Gnutella-like overlay.'''
    def __init__(self, entrypeers):
        self.logger = logging.getLogger("overlay")

        self.listenaddress = network.get_address()

        self.state = {
            'neighbours': [],
            'joining': None,  # has data when we are currently trying to join
            'pings': dict(),
            'group': None,
            'group_pings': BoundedDict(16384),
            'group_candidates': dict()
        }

        self.queues = QueueSet()
        self.cmdqueue = self.queues.New()  # commands by the user

        self.queue_to_peer = dict()  # remember which queue was used for which peer

        # open up our own listen socket
        self.logger.debug('setting up socket')
        self.listen = socket.socket()
        self.logger.debug('trying to listen on {}'.format(self.listenaddress))

        self.listen.bind(network.parse_address(self.listenaddress))
        self.listen.listen(10)
        self.logger.info('server socket established')

        # the queue that will be used for signalling new connections
        self.listenQ = self.queues.New()

        self.listen_thread = ConnectionWaiter(self.listen, self.listenQ)
        self.listen_thread.start()

        # connect to the overlay
        if entrypeers:
            self.cmdqueue.put('join {}'.format(" ".join(entrypeers)))

        threading.Thread.__init__(self, daemon=True)

    def put_cmd(self, cmd):
        self.cmdqueue.put(cmd)

    def find_group(self):
        """Send a group ping to identify groups"""
        ping_id = uuid.uuid4()
        message = proto.GroupPing(ping_id)
        self.state['group_pings'][ping_id] = None
        for p in self.state['neighbours']:
            p.send(message)

    def _listen_event(self, data):
        self.logger.info('new incoming peer connection')

        # create new objects for communication
        new_queue = self.queues.New()
        new_peer = Peer.from_connection(data, new_queue)

        # remember the Peer and the queue
        self.queue_to_peer[new_queue] = new_peer

        # start the peer thread
        new_peer.start()

    def _user_event(self, data):
        self.logger.debug('received user command: {}'.format(data))
        args = data.split()
        cmd = args[0]

        if cmd == 'join':
            # Join the overlay using the given entry peers
            if self.state['joining'] is not None:
                self.logger.error('already joining, ignore command.')
                return

            if len(self.state['neighbours']) == N_NEIGHBOURS:
                self.logger.error("already connected, don't join.")
                return

            self.logger.info('joining the overlay')
            self.state['joining'] = {'candidates': args[1:]}

            new_queue = self.queues.New()
            for entry_addr in self.state['joining']['candidates']:
                self.state['joining']['candidates'].remove(entry_addr)
                try:
                    self.logger.info('trying to join via {}'.format(entry_addr))
                    new_peer = Peer(entry_addr, new_queue)
                    new_peer.connect()
                    break
                except OSError as e:
                    self.logger.warning('cannot join via {} ({})'.format(entry_addr, e))
            else:
                self.logger.error('no entry peer available, cannot join')
                self.state['joining'] = None
                self.queues.remove(new_queue)
                return

            self.queue_to_peer[new_queue] = new_peer
            new_peer.start()

            ping_id = str(uuid.uuid4())
            self.state['joining']['current_entry'] = new_peer
            self.state['joining']['ping_id'] = ping_id

            new_peer.send(proto.Ping(ping_id, 3))

        elif cmd.startswith('s'):
            self.print_status()

        elif cmd.startswith('g') and len(args) > 1:
            group_cmd = args[1]
            if group_cmd == 'new':
                self.state['group'] = GroupLeader()
            elif group_cmd == 'join':
                if len(args[2:]) > 2:
                    self.state['group'] = GroupPeer(args[-1])
                elif self.state['group_candidates']:
                    best = max(self.state['group_candidates'].keys())
                    self.state['group'] = GroupPeer(self.state['group_candidates'][best])
                    self.state['group_candidates'] = dict()
            elif group_cmd == 'find':
                self.find_group()
            elif self.state['group']:
                if group_cmd == 'leave':
                    self.state['group'].leave()
                    self.state['group'] = None
                elif group_cmd == 'music':
                    self.state['group'].show_music()
                elif group_cmd == 'play':
                    try:
                        index = int(args[-1])
                    except ValueError:
                        index = 0
                    self.state['group'].play(index)
                elif group_cmd == 'add':
                    try:
                        self.state['group'].add_song(int(args[-1]))
                    except ValueError:
                        self.logger.warn("invalid song index")

        else:
            self.logger.error('unknown user command: {}'.format(cmd))
            print('\n  '.join(('[Commands]',
                               'join <peer> -- join overlay',
                               's[tatus] -- print status information',
                               'q[uit]')))
            print('\n  g[roup] '.join(('[Group commands]',
                                       'new -- create a new group',
                                       'find -- find available groups',
                                       'join -- join the best known group',
                                       'music -- list group music',
                                       'add <song_no> -- add song to group playlist',
                                       'play [number] -- start playing song from group playlist')))

    def _peer_event(self, inqueue, data):
        peer = self.queue_to_peer[inqueue]
        self.logger.info('received {} <- {}'.format(type(data), peer))

        # peer event handlers
        def close():
            self.logger.info('connection closed')

            peer = self.queue_to_peer[inqueue]
            if self.state['joining'] is not None and peer == self.state['joining']['current_entry']:
                self.logger.error('error joining, entry died')
                if len(self.state['joining']['candidates']) > 0:
                    self.logger.info('more entries to try')
                    self.cmdqueue.put(('join',
                                       self.state['joining']['candidates']))
                    self.state['joining'] = None
                else:
                    self.logger.error('joining finally failed.')

            # TODO remove from pongs pending list and trigger
            # processing

            # TODO if neighbour, try to reconnect (peer may have closed
            # it, unaware of the fact that it's a neighbour of ours)

            # TODO if group leader, leave group
            # (problem: map peer to group communication)

            if peer in self.state['neighbours']:
                self.logger.debug('forgetting peer {}] as a neighbour'.format(peer))
                self.state['neighbours'].remove(peer)

            del self.queue_to_peer[inqueue]

        def ping():
            p_id = data.get_id()
            ttl = data.get_ttl()

            # is this my ping?
            # TODO

            # neighbours we'd have to wait for
            dependencies = [x for x in self.state['neighbours'] if x != peer]

            if ttl == 0 or len(dependencies) == 0:
                # do not recurse
                peer.send(proto.Pong(p_id))
                if peer not in self.state['neighbours']:
                    # keep connection to neighbours alive
                    peer.disconnect()
                return

            # is it a new ping?
            if p_id in self.state['pings']:
                self.logger.debug('already know ping {}, send empty Pong'
                                  .format(p_id))
                peer.send(proto.Pong(p_id))
                return

            self.state['pings'][p_id] = {
                'from': peer,
                'pending': dependencies,  # pongs we're waiting for
                'collected': set(),  # peers collected by pongs
            }

            for n in self.state['pings'][p_id]['pending']:
                self.logger.debug('forwarding ping'.format(n))
                n.send(proto.Ping(p_id, ttl - 1))

        def pong():
            p_id = data.get_id()
            addrs = data.get_peers()

            if self.state['joining'] is not None and peer == self.state['joining']['current_entry']:
                neighbourset = {peer.get_address_str()} | addrs
                self.logger.debug('got possible neighbours: {}'.
                                  format(neighbourset))

                # choose random neighbours
                neighbourlist = list(neighbourset)
                random.shuffle(neighbourlist)

                forcing = True

                for n in neighbourlist:
                    if len(self.state['neighbours']) >= N_NEIGHBOURS:
                        break
                    self.logger.debug('trying peer {} as a neighbour'.format(n))

                    new_queue = self.queues.New()
                    try:
                        new_peer = Peer(n, new_queue)
                        new_peer.connect()
                        # TODO only successful if remote peer also
                        # wants to be our neighbour
                    except OSError as e:
                        self.logger.warning('neighbour {} does not work ({})'
                                            .format(n, e))
                        continue
                    self.logger.debug('peer {} added as a neighbour'.format(n))
                    self.state['neighbours'].append(new_peer)
                    new_peer.start()
                    new_peer.send(proto.Neighbour(force=forcing))
                    self.queue_to_peer[new_queue] = new_peer

                    forcing = False

                # don't need to close connection, since the peer
                # triggered closing it

                self.state['joining'] = None
                return

            if p_id not in self.state['pings']:
                self.logger.warning('unexpected PONG from {}'.format(peer))
                return

            if peer not in self.state['pings'][p_id]['pending']:
                self.logger.warning('unexpected PONG from {} (not pending)'.format(peer))

            self.state['pings'][p_id]['pending'].remove(peer)
            self.state['pings'][p_id]['collected'].add(peer.get_address_str())
            self.state['pings'][p_id]['collected'] |= (addrs)

            if len(self.state['pings'][p_id]['pending']) == 0:
                self.logger.debug('got all pending PONGs')

                self.state['pings'][p_id]['from'].send(proto.Pong(
                    p_id, self.state['pings'][p_id]['collected']
                ))

                if self.state['pings'][p_id]['from'] not in self.state['neighbours']:
                    # keep connection to neighbours alive
                    self.state['pings'][p_id]['from'].disconnect()

                # TODO already delete pings entry ??
                del self.state['pings'][p_id]

        def neighbour():
            if peer in self.state['neighbours']:
                self.logger.debug('already have it as a neighbour')
                return

            if len(self.state['neighbours']) >= N_NEIGHBOURS:
                if data.force:
                    self.logger.debug("accept as neighbour because we have to")
                else:
                    self.logger.debug('we have enough neighbours')
                    return

            self.logger.debug('peer {} added as a neighbour'.format(peer))
            self.state['neighbours'].append(peer)
            peer.send(proto.Neighbour())

        def sample():
            score = mpd.music.check_sample(data.hashes)
            self.logger.debug('score for sample is {}'.format(score))

        def group_ping():
            if data.ping_id in self.state['group_pings']:
                # We've seen this ping, do nothing
                self.logger.debug('known ping -> ignore')
            else:
                # We've not seen this ping, flood
                self.state['group_pings'][data.ping_id] = peer
                data.ttl -= 1
                for p in self.state['neighbours']:
                    if p != peer:
                        p.send(data)

                if self.state['group']:
                    # We're in a group, so we should answer
                    self.logger.debug('reply with group pong to {}'.format(peer.address))
                    music = self.state['group'].music
                    if isinstance(self.state['group'], GroupLeader):
                        m = proto.GroupPong(data.ping_id, network.get_group_address(), music)
                    elif isinstance(self.state['group'], GroupPeer):
                        m = proto.GroupPong(data.ping_id, self.state['group'].leader, music)
                    peer.send(m)

        def group_pong():
            if data.ping_id in self.state['group_pings']:
                # pong is excpected
                original_sender = self.state['group_pings'][data.ping_id]
                if original_sender:
                    # reverse path route pong
                    self.logger.debug('reverse route pong to {}'.format(original_sender.address))
                    original_sender.send(data)
                else:
                    # we pinged
                    self.logger.debug('received pong with group candidate {}'.format(data.leader))
                    score = mpd.music.check_sample(data.music)
                    self.logger.debug('score for pong is {}'.format(score))
                    if score > 0:
                        self.state['group_candidates'][score] = data.leader

        # assign handlers to data types
        handlers = {
                type(None): close,
                proto.Ping: ping,
                proto.Pong: pong,
                proto.Neighbour: neighbour,
                proto.Sample: sample,
                proto.GroupPing: group_ping,
                proto.GroupPong: group_pong
        }

        # dispatch handler
        handlers[type(data)]()

    def run(self):
        while True:
            (inqueue, data) = self.queues.get()

            # determine, what kind of event occured
            if inqueue == self.listenQ:
                # new peer established a connection to us
                self._listen_event(data)

            elif inqueue == self.cmdqueue:
                # command from the user
                self._user_event(data)

            elif inqueue in self.queue_to_peer:
                # message from another peer
                self._peer_event(inqueue, data)

            else:
                self.logger.error('unknown input: {}'.format(data))

    def print_status(self):
        print('[Peers]')
        print('\n'.join(':'.join(p.address) for p in self.state['neighbours']))

        print('[Group]')
        if self.state['group']:
            print('*{}*'.format(len(self.state['group'].music)))
            if isinstance(self.state['group'], GroupLeader):
                print('*leader*')
            elif isinstance(self.state['group'], GroupPeer):
                print('*peer*')
                print(self.state['group'].leader, '*leader*')
            print('\n'.join(self.state['group'].peers))
        else:
            print('*none*')

        print('[Playlist]')
        print('\n'.join('{}: {}  {}'.format(i, s.artist, s.title)
                        for (i, s) in enumerate(mpd.playlist.get())))
