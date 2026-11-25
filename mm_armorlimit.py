# mm_armorlimit.py - ArmorLimit 1.0.0: no tanks and APCs while fewer than 12 people play (Strike at Karkand only).
# A Multiplay ModManager module (ModManager 1.0 or later, Python 2.3 of BF2 1.5). Standalone: it does not need
# mm_flbus. It never asks the game for all objects of a type (getObjectsOfType).
#
# Under LIMIT 12 people (connected players, bots not counted), at once:
#   - nobody can get into a T-90, M1A2, BTR-90 or LAV-25: their entry points get entry radius 0 (console, live);
#   - their engines are stopped (torque / max speed / acceleration 0, console, live) - every vehicle of those kinds;
#   - every tank / APC somebody sits in is moved, with its crew, to its own spawn spot (the spot where it was first
#     got into; T-90 / BTR-90 - the factory, M1A2 / LAV-25 - the gas station, whoever sits in it; a vehicle whose spot
#     is not known goes to a spot of its kind, even if a vehicle stands there); one already at its spot stays;
#   - whoever was moved is put back on foot where he was when he gets out (once more 1.5 m higher if the game put
#     him more than 5 m away).
# LIMIT or more: entry and engines back to the values read before (or the ones the tests read, if a read gives 0);
# the vehicles stay where they are; the places to put players back are forgotten. Guns and MGs are not touched.
# Chat:  [ArmorLimit] 11 players: tanks and APCs closed and stopped until 12
#        [ArmorLimit] <names>: your tank/APC was moved to base until 12 players
#        [ArmorLimit] 12 players: tanks and APCs open
# The number of people is looked at ROUND_DELAY 15 s after a round starts, when a player joins or leaves, and every
# CHECK_EVERY 5 s while a round is played. Not on another map than Karkand (there it only puts back what it changed).
#
# Made from the tests with mm_armortest 0.1.0 - 0.3.0 on the test server (14.11.2026): getting a player out of a
# vehicle from Python is impossible; entry radius 0, the engine values, the moves with the crew, the own spots and
# the put-back work. Sagara 14.11: 17:59 the idea, 18:10 / 20:21 / 20:51 the answers, 22:06 no gun blocking, 22:10
# go-ahead. It is meant to replace mm_noarmor_v2 - never load both (mm_noarmor_v2 blows the armour up).
#
# Admin command (only names in ADMINS; '' - nobody, the default; '*' - anybody, for a test server only):
#   !al            what it sees now: people, pretended number, open / closed, spots known, places to put back
#   !al <n>        pretend there are n people (to test alone)
#   !al real       the real number again
#
# INSTALL
#   1. Copy this file to <server folder>/admin/modules/mm_armorlimit.py
#   2. modmanager.con:   modmanager.loadModule "mm_armorlimit"   - and take out  modmanager.loadModule "mm_noarmor_v2"
#   3. Restart the server; armorlimit.log (server folder) should say "armorlimit 1.0.0 loaded".
# Settings (modmanager.con lines under the loadModule lines, e.g.  mm_armorlimit.ADMINS "*"): below.
#
# History
# 1.0.0 (2026-11-14) first version.

__version__ = 1.0

__required_modules__ = {
	'modmanager': 1.0
}

__supports_reload__ = False

__supported_games__ = {
	'bf2': True,
	'bf2142': False,
	'bfheroes': False,
	'bfp4f': False
}

__description__ = 'ArmorLimit v1.0.0 (ModManager module)'

import bf2
import host
import sys

VERSION = '1.0.0'

# ------------------------------------------------------------------ settings
LIMIT = 12                # fewer people than this: tanks and APCs closed and stopped
MAP = 'karkand'           # works only on a map whose name holds this
CHECK_EVERY = 5.0         # s: how often the number of people is looked at (also on join / leave)
ROUND_DELAY = 1.0        # s after a round starts: the first look (players are still loading before it)
ADMINS = 'MysteryOrNot'               # names that may use '!al', comma-separated; '' - nobody; '*' - anybody (test server)
SAY = 1                   # 1: the [ArmorLimit] lines into the chat
TP_UP = 0.5               # m: a moved vehicle is put this much above its spot
AT_SPOT = 3.0             # m: a vehicle this near its spot is not moved
SPOT_NEAR = 15.0          # m: getting in this near a spot = the vehicle came from that spot
FREE_DIST = 6.0           # m: a spot with another occupied tank / APC this near is not free
HOME_UP = 0.5             # m: a player put back where he was - this much above that place
EXIT_DELAY = 0.5          # s after he gets out: then he is put back (if he is on foot - not a seat change)
PUT_CHECK = 0.2           # s after putting him back: is he there?
PUT_RETRY_DIST = 5.0      # m: farther than this - put him again, PUT_RETRY_UP higher (once)
PUT_RETRY_UP = 1.5        # m
ENTRY_NAMES = ('USAPC_LAV25_EntryPoint_Front,usapc_lav25_EntryPoint_Rear,USTNK_M1A2_EntryPoint_Front,'
               'USTNK_M1A2_EntryPoint_Rear,rutnk_t90_EntryPoint,rutnk_t90_EntryPoint_Rear,apc_btr90_EntryPoint,'
               'apc_btr90_EntryPoint_Rear')
ENGINE_NAMES = ('USAPC_LAV25_Engine,USAPC_LAV25_WaterEngine,APC_BTR90_Engine,apc_btr90_WaterEngine,'
                'USTNK_M1A2_Engine,RUTNK_T90_Engine')
ENGINE_ZERO = 'setTorque 0;setMaxSpeed 0/0/0;setAcceleration 0/0/0'   # what stops an engine, ';' between
LOG_CONSOLE = 0           # 1: every console line and its answer into the log too
CHAT_MAX = 170            # a chat line is split at this length (a 297-character line crashed a server)
LOG_FILE = 'armorlimit.log'
BAD = ['not found', 'unknown', 'error', 'invalid', 'no such', 'could not', 'too few']

# the values the tests read (14.11.2026) - used when a read gives nothing or 0
RADIUS_OPEN = [('usapc_lav25', 3.0), ('ustnk_m1a2', 4.0), ('rutnk_t90', 3.5), ('apc_btr90', 3.3)]
ENGINE_OPEN = {
    'usapc_lav25_engine': {'setTorque': '225', 'setMaxSpeed': '0/0/10000', 'setAcceleration': '0/0/10'},
    'apc_btr90_engine': {'setTorque': '250', 'setMaxSpeed': '0/0/10000', 'setAcceleration': '0/0/10'},
    'ustnk_m1a2_engine': {'setTorque': '10', 'setMaxSpeed': '4/0/10', 'setAcceleration': '50/0/10'},
    'rutnk_t90_engine': {'setTorque': '10', 'setMaxSpeed': '4/0/10', 'setAcceleration': '50/0/10'},
    'usapc_lav25_waterengine': {'setTorque': '15', 'setMaxSpeed': '300/1/10', 'setAcceleration': '300/0.1/10'},
    'apc_btr90_waterengine': {'setTorque': '15', 'setMaxSpeed': '300/1/10', 'setAcceleration': '300/0.1/10'}
}

# Karkand 64 spawn spots (GamePlayObjects): (x, y, z, heading, place)
SPOTS = {
    'mec_tank': [(197.112, 152.696, 203.275, -89.373, 'factory')],
    'us_tank': [(-172.823, 161.298, -309.137, 90.0, 'gas station')],
    'mec_apc': [(206.537, 152.696, 145.500, -92.841, 'factory'), (227.415, 152.696, 180.309, -90.0, 'factory')],
    'us_apc': [(-146.453, 161.298, -268.604, 0.0, 'gas station'), (-133.931, 161.298, -291.715, -90.0, 'gas station')]
}
KINDS = [('rutnk_t90', 'mec_tank'), ('apc_btr90', 'mec_apc'), ('ustnk_m1a2', 'us_tank'), ('usapc_lav25', 'us_apc')]

# ------------------------------------------------------------------ state
S = {'on': 0, 'timers': [], 'tick': None,
     'closed': None,      # None - not known (load / round start), 0 open, 1 closed
     'last': 0,           # the last state put on the templates (kept over rounds): 1 closed
     'playing': None,     # 1 while a round is played, 0 before / after it, None - not known yet
     'touched': 0,        # 1 once a template was changed (only then is anything put back)
     'fake': None,        # the pretended number of people ('!al <n>')
     'radius': {},        # entry point name -> the radius to put back
     'engine': {},        # (engine name lower, property) -> the value to put back
     'vhome': [],         # (vehicle, kind, spot index) - its own spot
     'home': {},          # player name -> where he was before the move
     'wait': 0.0}         # no look before this wall time (round start + ROUND_DELAY)

# ------------------------------------------------------------------ log, chat, console
def err_text():
    t, v = sys.exc_info()[:2]
    return '%s: %s' % (t, v)

def stamp():
    try:
        import time
        return time.strftime('%Y-%m-%d %H:%M:%S')
    except:
        try:
            return '%.1f' % host.timer_getWallTime()
        except:
            return '?'

def log(text):
    if not LOG_FILE:
        return
    try:
        f = open(LOG_FILE, 'a')
        try:
            f.write('%s  %s\n' % (stamp(), text))
        finally:
            f.close()
    except:
        pass

def chat_line(text):
    try:
        host.rcon_invoke('game.sayAll "%s"' % text.replace('"', "'"))
    except:
        pass

def say(text):
    log('chat: [ArmorLimit] ' + text)
    if not SAY:
        return
    text = '[ArmorLimit] ' + text
    while len(text) > CHAT_MAX:
        cut = text.rfind(' ', 0, CHAT_MAX)
        if cut < 40:
            cut = CHAT_MAX
        chat_line(text[:cut])
        text = '  ' + text[cut:].strip()
    chat_line(text)

def console(line):
    try:
        a = host.rcon_invoke(line)
    except:
        a = 'ERROR: ' + err_text()
    if a is None:
        a = ''
    a = str(a).replace('\r', ' ').replace('\n', ' ').strip()
    if LOG_CONSOLE:
        log('  > %s  ->  %s' % (line, a or '(no answer)'))
    return a

def bad_answer(a):
    low = a.lower()
    for b in BAD:
        if low.find(b) >= 0:
            return 1
    return 0

def now():
    try:
        return host.timer_getWallTime()
    except:
        return 0.0

def later(delay, func, data):
    # func(data) after delay seconds (bf2.Timer); the timer kept until it has run
    box = {}
    def run(d, box=box, func=func):
        try:
            func(d)
        except:
            log('timer: ' + err_text())
        t = box.get('t')
        if t is not None:
            try:
                S['timers'].remove(t)
            except:
                pass
            try:
                t.destroy()
            except:
                pass
    try:
        t = bf2.Timer(run, delay, 1, data)
        box['t'] = t
        S['timers'].append(t)
    except:
        log('could not make a timer: ' + err_text())

def words(text, sep):
    out = []
    for w in str(text).split(sep):
        w = w.strip()
        if w:
            out.append(w)
    return out

# ------------------------------------------------------------------ players and vehicles
def name_of(p):
    try:
        return p.getName()
    except:
        return '?'

def tpl(o):
    try:
        return str(o.templateName)
    except:
        return '?'

def pos(o):
    try:
        q = o.getPosition()
        return (float(q[0]), float(q[1]), float(q[2]))
    except:
        return None

def pos_text(q):
    if q is None:
        return '?'
    return '%.1f/%.1f/%.1f' % (q[0], q[1], q[2])

def hdist(a, b):
    dx = float(a[0]) - float(b[0])
    dz = float(a[2]) - float(b[2])
    return (dx * dx + dz * dz) ** 0.5

def top_of(o):
    k = 0
    while o is not None and k < 10:
        try:
            par = o.getParent()
        except:
            par = None
        if par is None:
            return o
        o = par
        k = k + 1
    return o

def alive(p):
    try:
        return p.isAlive()
    except:
        return 0

def is_bot(p):
    try:
        return p.isAIPlayer()
    except:
        return 0

def soldier_of(p):
    try:
        return p.getDefaultVehicle()
    except:
        return None

def in_vehicle(p):
    # (1 / 0, the vehicle object or None): getVehicle() is the soldier when he is on foot
    try:
        v = p.getVehicle()
        s = p.getDefaultVehicle()
    except:
        return 0, None
    if v is None or s is None:
        return 0, None
    if tpl(v).lower() == tpl(s).lower():
        return 0, None
    return 1, v

def kind_of(top):
    t = tpl(top).lower()
    for a, k in KINDS:
        if t == a or t.startswith(a):
            return k
    return None

def crew_of(top):
    out = []
    try:
        for q in top.getOccupyingPlayers():
            out.append(q)
    except:
        pass
    return out

def names_of(L):
    out = []
    for q in L:
        out.append(name_of(q))
    return out

def map_name():
    try:
        return str(bf2.gameLogic.getMapName())
    except:
        return '?'

def map_ok():
    return map_name().lower().find(str(MAP).lower()) >= 0

def people():
    n = 0
    try:
        L = bf2.playerManager.getPlayers()
    except:
        log('could not read the players: ' + err_text())
        return -1
    for q in L:
        if is_bot(q):
            continue
        try:
            if not q.isConnected():
                continue
        except:
            continue
        n = n + 1
    return n

def occupied_armour():
    # [(top, crew)] - every tank / APC somebody alive sits in, found through the players
    out = []
    seen = []
    try:
        L = bf2.playerManager.getPlayers()
    except:
        return out
    for p in L:
        n = name_of(p)
        if n in seen or not alive(p):
            continue
        inv, v = in_vehicle(p)
        if not inv:
            continue
        top = top_of(v)
        if kind_of(top) is None:
            continue
        crew = crew_of(top)
        names = names_of(crew)
        if n not in names:
            crew.append(p)
            names.append(n)
        seen.extend(names)
        out.append((top, crew))
    return out

# ------------------------------------------------------------------ spots and moves
def spot_text(kind, k):
    return '%s %d (%s)' % (kind.replace('_', ' '), k + 1, SPOTS[kind][k][4])

def own_spot(top):
    for e in S['vhome']:
        if e[0] is top:
            return e
    return None

def pick_spot(kind, top, crew, taken, others):
    # (index, why): its own spot, else a free one, else one not taken now, else the first
    L = SPOTS[kind]
    def busy(k, L=L, others=others, taken=taken, kind=kind):
        if (kind, k) in taken:
            return 1
        for q in others:
            if q is not None and hdist(q, L[k]) < float(FREE_DIST):
                return 1
        return 0
    e = own_spot(top)
    if e is not None and e[1] == kind and e[2] < len(L) and (kind, e[2]) not in taken:
        return e[2], 'its own spot'
    for k in range(len(L)):
        if not busy(k):
            return k, 'free'
    for k in range(len(L)):
        if (kind, k) not in taken:
            return k, 'a vehicle may stand there'
    return 0, 'every spot taken'

def move(top, crew, kind, k, why):
    # -> 1 if moved
    x, y, z, yaw, place = SPOTS[kind][k]
    q0 = pos(top)
    target = (x, y + float(TP_UP), z)
    if q0 is not None and hdist(q0, target) < float(AT_SPOT):
        log('  %s (%s) already at %s - not moved' % (tpl(top), ', '.join(names_of(crew)), spot_text(kind, k)))
        return 0
    try:
        top.setPosition(target)
    except:
        log('  %s: setPosition failed: %s' % (tpl(top), err_text()))
        return 0
    try:
        top.setRotation((float(yaw), 0.0, 0.0))
    except:
        log('  %s: setRotation failed: %s' % (tpl(top), err_text()))
    for c in crew:
        n = name_of(c)
        if q0 is not None and n not in S['home']:
            S['home'][n] = q0
    log('  %s moved from %s to %s (%s); crew: %s' % (tpl(top), pos_text(q0), spot_text(kind, k), why,
        ', '.join(names_of(crew)) or 'nobody'))
    if crew:
        later(0.5, look_after_move, (crew[0], target))
    return 1

def look_after_move(data):
    p, target = data
    inv, v = in_vehicle(p)
    if not inv:
        log('  0.5 s after the move: %s is not in a vehicle (alive %s)' % (name_of(p), alive(p)))
        return
    q = pos(top_of(v))
    if q is None:
        return
    log('  0.5 s after the move: %s in %s at %s, %.1f m from the spot, %+.1f m higher' % (name_of(p), tpl(top_of(v)),
        pos_text(q), hdist(q, target), q[1] - target[1]))

def move_all():
    arm = occupied_armour()
    taken = []
    moved = []
    k_moved = 0
    i = 0
    for top, crew in arm:
        kind = kind_of(top)
        others = []
        j = 0
        for o, c in arm:
            if j != i:
                others.append(pos(o))
            j = j + 1
        k, why = pick_spot(kind, top, crew, taken, others)
        taken.append((kind, k))
        if move(top, crew, kind, k, why):
            k_moved = k_moved + 1
            for c in crew:
                if not is_bot(c) and name_of(c) not in moved:
                    moved.append(name_of(c))
        i = i + 1
    return len(arm), k_moved, moved

# ------------------------------------------------------------------ putting players back
def after_exit(p):
    n = name_of(p)
    inv, v = in_vehicle(p)
    if inv:
        return
    h = S['home'].get(n)
    if h is None:
        return
    del S['home'][n]
    if not alive(p):
        log('%s got out dead - not put back' % n)
        return
    target = (h[0], h[1] + float(HOME_UP), h[2])
    try:
        soldier_of(p).setPosition(target)
    except:
        log('putting %s back failed: %s' % (n, err_text()))
        return
    log('%s got out - put back where he was (%s)' % (n, pos_text(h)))
    later(float(PUT_CHECK), put_check, (p, target, n))

def put_check(data):
    p, target, n = data
    if not alive(p):
        return
    inv, v = in_vehicle(p)
    if inv:
        return
    s = soldier_of(p)
    q = pos(s)
    if q is None:
        return
    d = hdist(q, target)
    if d <= float(PUT_RETRY_DIST):
        return
    t2 = (target[0], target[1] + float(PUT_RETRY_UP), target[2])
    try:
        s.setPosition(t2)
    except:
        log('putting %s back again failed: %s' % (n, err_text()))
        return
    log('%s was %.1f m away (at %s) - put back again %.1f m higher' % (n, d, pos_text(q), float(PUT_RETRY_UP)))

# ------------------------------------------------------------------ the templates
def number_in(a):
    for w in a.replace('=', ' ').split():
        try:
            return float(w)
        except:
            pass
    return None

def radius_fallback(t):
    low = t.lower()
    for a, r in RADIUS_OPEN:
        if low.startswith(a):
            return r
    return 3.0

def engine_fallback(t, prop):
    d = ENGINE_OPEN.get(t.lower())
    if d is None:
        return None
    return d.get(prop)

def zero_like(a):
    # 1 if every number in a ('0.1', '0/0/0') is 0.1 or less - an engine stopped already
    parts = words(a, '/')
    if not parts:
        return 1
    for w in parts:
        try:
            if float(w) > 0.1001:
                return 0
        except:
            return 0
    return 1

def zero_list():
    out = []
    for part in words(ENGINE_ZERO, ';'):
        w = part.split(None, 1)
        if len(w) == 2:
            out.append((w[0], w[1]))
    return out

def activate(kind, t):
    a = console('ObjectTemplate.activeSafe %s %s' % (kind, t))
    if a and bad_answer(a):
        log('%s %s: the console said "%s" - left alone' % (kind, t, a))
        return 0
    return 1

def close_templates():
    S['touched'] = 1
    ne = 0
    for t in words(ENTRY_NAMES, ','):
        if not activate('EntryPoint', t):
            continue
        if t not in S['radius']:
            r = number_in(console('ObjectTemplate.setEntryRadius'))
            if r is None or r <= 0:
                log('%s: radius read %s - %g will be put back' % (t, r, radius_fallback(t)))
                r = radius_fallback(t)
            S['radius'][t] = r
        console('ObjectTemplate.setEntryRadius 0')
        ne = ne + 1
    ng = 0
    for t in words(ENGINE_NAMES, ','):
        if not activate('Engine', t):
            continue
        for prop, val in zero_list():
            key = (t.lower(), prop)
            if key not in S['engine']:
                before = console('ObjectTemplate.%s' % prop)
                if not before or bad_answer(before) or zero_like(before):
                    fb = engine_fallback(t, prop)
                    log('%s %s: read "%s" - %s will be put back' % (t, prop, before, fb))
                    before = fb
                if before is None:
                    continue
                S['engine'][key] = (t, before)
            console('ObjectTemplate.%s %s' % (prop, val))
        ng = ng + 1
    return ne, ng

def open_templates():
    ne = 0
    for t in words(ENTRY_NAMES, ','):
        if not activate('EntryPoint', t):
            continue
        r = S['radius'].get(t)
        if r is None:
            r = radius_fallback(t)
        console('ObjectTemplate.setEntryRadius %g' % r)
        ne = ne + 1
    ng = 0
    for t in words(ENGINE_NAMES, ','):
        if not activate('Engine', t):
            continue
        k = 0
        for prop, val in zero_list():
            e = S['engine'].get((t.lower(), prop))
            if e is not None:
                back = e[1]
            else:
                back = engine_fallback(t, prop)
            if back is None:
                log('%s %s: no value to put back' % (t, prop))
                continue
            console('ObjectTemplate.%s %s' % (prop, back))
            k = 1
        ng = ng + k
    return ne, ng

# ------------------------------------------------------------------ open / closed
def check(data=None):
    if not S['on']:
        return
    try:
        check_now()
    except:
        log('check: ' + err_text())

def check_now():
    if S['playing'] == 0 or now() < S['wait']:
        return
    if not map_ok():
        if S['last'] and S['touched']:
            ne, ng = open_templates()
            log('map %s is not %s - entry back on %d, engines back %d' % (map_name(), MAP, ne, ng))
        S['closed'] = 0
        S['last'] = 0
        return
    real = people()
    if real < 0:
        return
    n = real
    if S['fake'] is not None:
        n = S['fake']
    want = int(n < int(LIMIT))
    if S['closed'] is not None and want == S['closed']:
        return
    if want:
        close_now(n, real)
    else:
        open_now(n, real)

def close_now(n, real):
    ne, ng = close_templates()
    S['closed'] = 1
    S['last'] = 1
    say('%d players: tanks and APCs closed and stopped until %d' % (n, int(LIMIT)))
    found, k, moved = move_all()
    if moved:
        say('%s: your tank/APC was moved to base until %d players' % (', '.join(moved), int(LIMIT)))
    log('CLOSED at %d people (real %d): entry 0 on %d entry points, %d engines stopped; %d tanks/APCs with crews, '
        '%d moved' % (n, real, ne, ng, found, k))

def open_now(n, real):
    homes = len(S['home'])
    S['home'] = {}
    if S['touched']:
        ne, ng = open_templates()
    else:
        ne, ng = 0, 0
    was = S['last']
    S['closed'] = 0
    S['last'] = 0
    if was:
        say('%d players: tanks and APCs open' % n)
    log('OPEN at %d people (real %d): entry back on %d entry points, %d engines back; places forgotten %d' % (
        n, real, ne, ng, homes))

# ------------------------------------------------------------------ events
def on_enter(player, vehicle=None, *rest):
    if not S['on']:
        return
    try:
        top = top_of(vehicle)
        kind = kind_of(top)
        if kind is None:
            return
        q = pos(top)
        if q is not None and own_spot(top) is None:
            j = 0
            for s in SPOTS[kind]:
                if hdist(q, s) < float(SPOT_NEAR):
                    S['vhome'].append((top, kind, j))
                    if len(S['vhome']) > 60:
                        del S['vhome'][0]
                    break
                j = j + 1
        if S['closed'] == 1:
            log('%s got into %s at %s while closed (entry radius 0?)' % (name_of(player), tpl(top), pos_text(q)))
    except:
        log('EnterVehicle: ' + err_text())

def on_exit(player, vehicle=None, *rest):
    if not S['on']:
        return
    try:
        if name_of(player) in S['home']:
            later(float(EXIT_DELAY), after_exit, player)
    except:
        log('ExitVehicle: ' + err_text())

def on_killed(victim, *rest):
    if not S['on']:
        return
    try:
        n = name_of(victim)
        if n in S['home']:
            del S['home'][n]
    except:
        pass

def on_join(player, *rest):
    if not S['on']:
        return
    later(1.0, check, None)

def on_leave(player, *rest):
    if not S['on']:
        return
    try:
        n = name_of(player)
        if n in S['home']:
            del S['home'][n]
    except:
        pass
    later(1.0, check, None)

def on_status(status):
    if not S['on']:
        return
    try:
        if status == bf2.GameStatus.Playing:
            if S['playing'] != 1:
                S['vhome'] = []
                S['home'] = {}
                S['closed'] = None
                S['wait'] = now() + float(ROUND_DELAY) - 0.05
                log('round on %s (%s; first look in %.0f s)' % (map_name(),
                    (map_ok() and 'ArmorLimit works here') or 'not this map', float(ROUND_DELAY)))
                later(float(ROUND_DELAY), check, None)
            S['playing'] = 1
        else:
            S['playing'] = 0
    except:
        log('status: ' + err_text())

def may_admin(name):
    a = str(ADMINS).strip()
    if not a:
        return 0
    if a == '*':
        return 1
    me = name.strip().lower()
    for n in words(a, ','):
        n = n.lower()
        if me == n or me.endswith(' ' + n):
            return 1
    return 0

def on_chat(playerId, text, channel=None, flags=None):
    if not S['on'] or not str(ADMINS).strip():
        return
    try:
        s = str(text)
    except:
        return
    i = s.lower().find('!al')
    if i < 0:
        return
    w = s[i:].split()
    if not w or w[0].lower() != '!al':
        return
    try:
        p = bf2.playerManager.getPlayerByIndex(int(playerId))
    except:
        p = None
    if p is None or not may_admin(name_of(p)):
        return
    try:
        a = ''
        if len(w) > 1:
            a = w[1].lower()
        if a == 'real':
            S['fake'] = None
            log('%s: "!al real"' % name_of(p))
            check_now()
        elif a:
            try:
                n = int(a)
            except:
                say("'!al', '!al <players>' or '!al real'")
                return
            S['fake'] = n
            log('%s: "!al %d" - pretending %d people' % (name_of(p), n, n))
            check_now()
        st = 'not known'
        if S['closed'] == 1:
            st = 'CLOSED'
        elif S['closed'] == 0:
            st = 'open'
        fake = 'no'
        if S['fake'] is not None:
            fake = str(S['fake'])
        say('people %d, pretended %s, %s; own spots known %d, players to put back %d (%s)' % (people(), fake, st,
            len(S['vhome']), len(S['home']), ', '.join(S['home'].keys()) or 'nobody'))
    except:
        log('!al: ' + err_text())

def armorlimit_init():
    if S['on']:
        return
    S['on'] = 1
    log('armorlimit %s loaded on %s (limit %d, map %s, check every %.1f s, first look %.0f s after a round start, '
        'admins: %s)' % (VERSION, map_name(), int(LIMIT), MAP, float(CHECK_EVERY), float(ROUND_DELAY), ADMINS or 'nobody'))
    for ev, fn in (('ChatMessage', on_chat), ('EnterVehicle', on_enter), ('ExitVehicle', on_exit),
                   ('PlayerKilled', on_killed), ('PlayerConnect', on_join), ('PlayerDisconnect', on_leave)):
        try:
            host.registerHandler(ev, fn, 1)
        except:
            log('could not register %s: %s' % (ev, err_text()))
    try:
        host.registerGameStatusHandler(on_status)
    except:
        log('could not register the status handler: ' + err_text())
    try:
        t = bf2.Timer(check, float(CHECK_EVERY), 1, None)
        t.setRecurring(float(CHECK_EVERY))
        S['tick'] = t
    except:
        log('could not make the check timer: ' + err_text())

# ------------------------------------------------------------------ ModManager interface
configDefaults = {}
for _k in ['LIMIT', 'MAP', 'CHECK_EVERY', 'ROUND_DELAY', 'ADMINS', 'SAY', 'TP_UP', 'AT_SPOT', 'SPOT_NEAR', 'FREE_DIST', 'HOME_UP',
           'EXIT_DELAY', 'PUT_CHECK', 'PUT_RETRY_DIST', 'PUT_RETRY_UP', 'ENTRY_NAMES', 'ENGINE_NAMES', 'ENGINE_ZERO',
           'LOG_CONSOLE', 'CHAT_MAX', 'LOG_FILE']:
    configDefaults[_k] = globals()[_k]

class ArmorLimit( object ):

    def __init__( self, modManager ):
        self.mm = modManager
        self.__state = 0

    def init( self ):
        if 0 != self.__state:
            return
        cfg = self.mm.getModuleConfig( configDefaults )
        g = globals()
        for k in configDefaults:
            try:
                g[k] = cfg[k]
            except:
                pass
        for k in ('CHECK_EVERY', 'ROUND_DELAY', 'TP_UP', 'AT_SPOT', 'SPOT_NEAR', 'FREE_DIST', 'HOME_UP', 'EXIT_DELAY', 'PUT_CHECK',
                  'PUT_RETRY_DIST', 'PUT_RETRY_UP'):
            try:
                g[k] = float(g[k])
            except:
                g[k] = configDefaults[k]
        for k in ('LIMIT', 'SAY', 'LOG_CONSOLE', 'CHAT_MAX'):
            try:
                g[k] = int(g[k])
            except:
                g[k] = configDefaults[k]
        if g['CHECK_EVERY'] < 1.0:
            g['CHECK_EVERY'] = 1.0
        self.__state = 1
        armorlimit_init()
        try:
            self.mm.info( 'armorlimit %s is running (see %s)' % ( VERSION, LOG_FILE or 'no log' ) )
        except:
            pass

    def shutdown( self ):
        self.__state = 2
        S['on'] = 0
        t = S['tick']
        S['tick'] = None
        if t is not None:
            try:
                t.destroy()
            except:
                pass

    def update( self ):
        pass

def mm_load( modManager ):
    return ArmorLimit( modManager )
