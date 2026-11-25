# mm_armortest.py - ArmorTest 0.3.0: FOR A TEST SERVER ONLY - test commands for mm_armorlimit, Karkand 64 only:
# a tank / APC moved with its crew to its own spawn spot, kept there (its engine stopped through the console, or
# pulled back), its main gun and missile launcher blocked through the console (which property does it is what this
# version is for), the crew put back where they were when they get out, and the whole "fewer than 12 players" scene
# with a pretended number of players. A Multiplay ModManager module (ModManager 1.0 or later, Python 2.3 of BF2 1.5).
# Standalone: it does not need mm_flbus. It never asks the game for all objects of a type (getObjectsOfType).
#
# What 0.1.0 found (14.11): a player cannot be put OUT of a vehicle from Python (his soldier moved beside it, his side
# changed - he stays in); keeping players OUT works: the entry points of a template set to entry radius 0 (console).
# Sagara 14.11 20:05: so when there are fewer than 12, move the armour with its crew to its spawn spot, do not let it
# drive away, and when they get out, put them back where they were. 20:21: yes, put them back where they were;
# the factory cannot be taken on the =FL= server (always MEC); armour nobody sits in stays where it is; they may shoot;
# at once. 20:44 (test of 0.2.0): the engine stops it better than the pin; block the guns of the tanks and APCs;
# moving onto a spot where a vehicle stands rams it. 20:51: block the main gun and the missile launcher; a T-90 goes
# to the MEC base and an M1A2 to the US base even when the other side took it; a vehicle whose own spot is not known
# goes to a spot of its kind even if it may ram; chat text OK.
#
# The spawn spots (GamePlayObjects of Karkand 64): T-90 and BTR-90 - the factory; M1A2 and LAV-25 - the gas station.
#   MEC tank   197.1/152.7/203.3   (factory)        US tank   -172.8/161.3/-309.1  (gas station)
#   MEC APC 1  206.5/152.7/145.5   (factory)        US APC 1  -146.5/161.3/-268.6  (gas station)
#   MEC APC 2  227.4/152.7/180.3   (factory)        US APC 2  -133.9/161.3/-291.7  (gas station)
#
# Commands, typed in the chat by a name in TEST_ADMINS ('' - anybody):
#   !ar                  the list
#   !ar state            where you are: on foot or in a vehicle, its template, position, heading, health, crew
#   !ar count            players on the server: all, people, bots
#   !ar spots            the six spots and how far each is from you
#   !ar tp [1|2]         the tank / APC you sit in moved, with whoever sits in it, to the spot of its kind (1 / 2 - which
#                        APC spot; without it: the vehicle's own spot - where it was first got into - else the spot
#                        where one of its crew got in, else a free one, else the first). Everybody in it is remembered
#                        where he was; when he gets out he is put back there (on foot; again 1.5 m higher if the
#                        game put him more than 5 m away)
#   !ar mark             remember where you are (in a vehicle: the vehicle; on foot: you)
#   !ar back             in a vehicle: the vehicle moved to the mark; on foot: you moved to the mark
#   !ar pin [m|off]      the vehicle you sit in is pulled back to where it is now whenever it is more than m metres
#                        (PIN_DIST 3) away - looked at every PIN_EVERY 0.25 s - until all its crew are out;
#                        'off' - every pin off
#   !ar engine 0         ENGINE_ZERO (e.g. setTorque 0) on the engines found by '!ar tree' (and ENGINE_NAMES),
#                        through the console: every vehicle of that kind at once; the values before are read first
#   !ar engine back      the values read before put back
#   !ar engine set <property> <value>   one property on those engines (to try others by hand)
#   !ar gun read         the values of GUN_READ (fire.roundsPerMinute, ammo.reloadTime ...) of the guns GUN_NAMES (main
#                        guns and missile launchers of the four kinds) into the log - nothing changed
#   !ar gun rpm|reload|mag|all   one way to block firing on those guns, through the console (every vehicle of the kind
#                        at once; the values before are read first): rpm - fire.roundsPerMinute 1; reload -
#                        ammo.reloadTime 3600; mag - ammo.magSize 0; all - rpm and reload. Then try to fire
#   !ar gun set <property> <value>   one property on those guns (to try others by hand)
#   !ar gun back         the values read before put back
#   !ar tree             the parts of the vehicle you sit in: all into the log; the entry points and engines remembered
#   !ar entry <r> [tpl]  entry radius r on the entry points of the last '!ar tree' (or the template tpl);
#                        '!ar entry back' - the radius read before (a restart of the server puts it back anyway)
#   !ar sim <n> [way] [gun]   pretend there are n people. Under LIMIT 12: entry radius 0 on every entry point known
#                        (ENTRY_NAMES and those found by '!ar tree'), every tank / APC with somebody in it moved to its
#                        spot, kept there by 'engine' (default STOP), 'pin', 'both' or 'none', its guns blocked by the
#                        gun way (rpm / reload / mag / all; default: the last one tried with '!ar gun'; 'none' - not),
#                        the [ArmorLimit] chat lines. LIMIT or more: entry back, engines back, guns back, pins off, the
#                        [ArmorLimit] "open" line
#   !ar con <line>       any console line (host.rcon_invoke) and its answer
# After a move the chat and the log say, CHECKS 0.1 / 0.5 / 1.5 / 3 s later: in the vehicle or not, where, how far from
# the spot, how much higher, health. Every EnterVehicle / ExitVehicle is logged.
#
# INSTALL (test server)
#   1. Copy this file to <server folder>/admin/modules/mm_armortest.py (in place of 0.2.0)
#   2. modmanager.con:   modmanager.loadModule "mm_armortest"   (already there)
#   3. Restart the server; armortest.log (server folder) should say "armortest 0.3.0 loaded".
# Settings (modmanager.con lines, e.g.  mm_armortest.TEST_ADMINS "MysteryOrNot"): below.
#
# History
# 0.3.0 (2026-11-14) guns: '!ar gun' read / ways to block / set / back, and in '!ar sim'; every vehicle remembered with
#                    its own spot (the object passed when it is got into is the same object later - 0.2.0 test) and
#                    moved back there, so no ram; T-90 / BTR-90 always to the factory, M1A2 / LAV-25 to the gas
#                    station; a vehicle already at its spot is not moved; the put-back looked at again 0.2 s later and
#                    tried once more 1.5 m higher if more than 5 m off; engine is the default way of '!ar sim'; all the
#                    entry points and engines of the four kinds known from the start (Sagara 14.11 20:44 / 20:51).
# 0.2.0 (2026-11-14) moving armour with its crew to its spawn spot, pin, engine, putting the crew back, the scene with
#                    a pretended count (Sagara 14.11 20:05 / 20:21). The ways that failed in 0.1.0 (e1, e2, auto) are
#                    gone.
# 0.1.0 (2026-11-14) first version (Sagara 14.11 19:24: "let us make the test module").

__version__ = 0.3

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

__description__ = 'ArmorTest v0.3.0 (ModManager module, test servers only)'

import bf2
import host
import sys

VERSION = '0.3.0'

# ------------------------------------------------------------------ settings
TEST_ADMINS = ''          # names allowed to use the commands, comma-separated ('' - anybody)
ARMOR = 'rutnk_t90,ustnk_m1a2,apc_btr90,usapc_lav25'   # tanks and APCs (template names; also matched as a start)
LIMIT = 12                # '!ar sim': under this many people the armour is closed
STOP = 'engine'           # '!ar sim' without a way: engine / pin / both / none
TP_UP = 0.5               # m: a moved vehicle is put this much above the spot
HOME_UP = 0.5             # m: a player put back where he was - this much above that place
EXIT_DELAY = 0.5          # s after he gets out: then he is put back (if he is on foot - not a seat change)
SPOT_NEAR = 15.0          # m: getting in this near a spot = the vehicle came from that spot
FREE_DIST = 6.0           # m: a spot with another occupied tank / APC this near is not free
PIN_DIST = 3.0            # m: pulled back when farther than this (across the ground) from the pin
PIN_EVERY = 0.25          # s: how often the pins are looked at
ENTRY_NAMES = ('USAPC_LAV25_EntryPoint_Front,usapc_lav25_EntryPoint_Rear,USTNK_M1A2_EntryPoint_Front,'
               'USTNK_M1A2_EntryPoint_Rear,rutnk_t90_EntryPoint,rutnk_t90_EntryPoint_Rear,apc_btr90_EntryPoint,'
               'apc_btr90_EntryPoint_Rear')   # entry points (0.2.0 test; more from '!ar tree')
ENGINE_NAMES = ('USAPC_LAV25_Engine,USAPC_LAV25_WaterEngine,APC_BTR90_Engine,apc_btr90_WaterEngine,'
                'USTNK_M1A2_Engine,RUTNK_T90_Engine')   # engines (0.2.0 test; more from '!ar tree')
ENGINE_ZERO = 'setTorque 0;setMaxSpeed 0/0/0;setAcceleration 0/0/0'        # what '!ar engine 0' sets, ';' between
GUN_NAMES = ('RUTNK_T90_Barrel,USTNK_M1A2_Barrel,APC_BTR90__Barrel,APC_BTR90_HJ8Launcher,USAPC_LAV25_Barrel,'
             'USAPC_LAV25_TowLauncher')   # main guns and missile launchers (names from '!ar tree')
GUN_TYPE = 'GenericFireArm'   # the template type of those guns for ObjectTemplate.activeSafe
GUN_READ = ('fire.roundsPerMinute,fire.fireInput,fire.addFireRate,ammo.magSize,ammo.nrOfMags,ammo.reloadTime,'
            'ammo.autoReload,projectileTemplate,velocity')   # what '!ar gun read' reads
PUT_CHECK = 0.2           # s after putting a player back: look whether he is there
PUT_RETRY_DIST = 5.0      # m: farther than this from the place - put him again, PUT_RETRY_UP higher
PUT_RETRY_UP = 1.5        # m
OPEN_RADIUS = 3.0         # m: the entry radius put back when the one read before is 0 or not known
CHECKS = '0.1 0.5 1.5 3'  # s after a move: when to look again
SAY = 1                   # 1: results into the chat too
CHAT_MAX = 170            # a chat line is split at this length (a 297-character line crashed a server)
LOG_FILE = 'armortest.log'
BAD = ['not found', 'unknown', 'error', 'invalid', 'no such', 'could not']

# T-90 / BTR-90 - MEC, the factory; M1A2 / LAV-25 - US, the gas station: (x, y, z, heading, place)
SPOTS = {
    'mec_tank': [(197.112, 152.696, 203.275, -89.373, 'factory')],
    'us_tank': [(-172.823, 161.298, -309.137, 90.0, 'gas station')],
    'mec_apc': [(206.537, 152.696, 145.500, -92.841, 'factory'), (227.415, 152.696, 180.309, -90.0, 'factory')],
    'us_apc': [(-146.453, 161.298, -268.604, 0.0, 'gas station'), (-133.931, 161.298, -291.715, -90.0, 'gas station')]
}
KIND_ORDER = ['mec_tank', 'mec_apc', 'us_tank', 'us_apc']
KINDS = [('rutnk_t90', 'mec_tank'), ('apc_btr90', 'mec_apc'), ('ustnk_m1a2', 'us_tank'), ('usapc_lav25', 'us_apc')]

# ------------------------------------------------------------------ log, chat, console
S = {'on': 0, 'timers': [], 'tick': None, 'n': 0,
     'tree': [], 'tree_eng': [], 'entry_found': [], 'engine_found': [],
     'radius': {}, 'engine': {}, 'pins': [], 'home': {}, 'entered': {}, 'entered_obj': {}, 'mark': {},
     'closed': 0, 'stop': '', 'map_said': 0, 'gun': {}, 'gun_last': '', 'vhome': []}

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

def chat_split(text):
    while len(text) > CHAT_MAX:
        cut = text.rfind(' ', 0, CHAT_MAX)
        if cut < 40:
            cut = CHAT_MAX
        chat_line(text[:cut])
        text = '  ' + text[cut:].strip()
    chat_line(text)

def say(text, always=0):
    log('chat: ' + text)
    if not SAY and not always:
        return
    chat_split('[ArmorTest] ' + text)

def say_limit(text):
    # the line mm_armorlimit would say (always into the chat)
    log('chat: [ArmorLimit] ' + text)
    chat_split('[ArmorLimit] ' + text)

def console(line):
    # one console line; its answer cut to one line, logged
    try:
        a = host.rcon_invoke(line)
    except:
        a = 'ERROR: ' + err_text()
    if a is None:
        a = ''
    a = str(a).replace('\r', ' ').replace('\n', ' ').strip()
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

def add_name(L, name):
    # a template name into L once (case does not matter)
    for x in L:
        if x.lower() == name.lower():
            return
    L.append(name)

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

def rot(o):
    try:
        r = o.getRotation()
        return (float(r[0]), float(r[1]), float(r[2]))
    except:
        return None

def pos_text(q):
    if q is None:
        return '?'
    return '%.1f/%.1f/%.1f' % (q[0], q[1], q[2])

def rot_text(r):
    if r is None:
        return '?'
    return '%.0f/%.0f/%.0f' % (r[0], r[1], r[2])

def hdist(a, b):
    # metres across the ground (x and z)
    dx = float(a[0]) - float(b[0])
    dz = float(a[2]) - float(b[2])
    return (dx * dx + dz * dz) ** 0.5

def top_of(o):
    # the top object (a gunner's seat is a part of the vehicle)
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

def is_armor(v):
    t = tpl(top_of(v)).lower()
    for a in words(ARMOR, ','):
        a = a.lower()
        if t == a or t.startswith(a):
            return 1
    return 0

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

def is_bot(p):
    try:
        return p.isAIPlayer()
    except:
        return 0

def health(o):
    try:
        return o.getDamage()
    except:
        return None

def map_name():
    try:
        return str(bf2.gameLogic.getMapName())
    except:
        return '?'

def on_karkand():
    if map_name().lower().find('karkand') >= 0:
        return 1
    say('the spots are for Strike at Karkand only - this map is %s' % map_name(), 1)
    return 0

def state_text(p):
    team = '?'
    try:
        team = str(p.getTeam())
    except:
        pass
    if not alive(p):
        return '%s: DEAD (side %s)' % (name_of(p), team)
    s = soldier_of(p)
    inv, v = in_vehicle(p)
    if inv:
        top = top_of(v)
        same = ''
        o = S['entered_obj'].get(name_of(p))
        if o is not None:
            eq = '?'
            try:
                eq = str(int(o == top))
            except:
                pass
            same = '; same object as when he got in: == %s, is %d' % (eq, int(o is top))
        own = ''
        e = own_spot(top)
        if e is not None:
            own = '; its own spot: %s' % spot_text(e[1], e[2])
        return '%s: IN %s (seat %s) at %s, heading %s, health %s, crew: %s; side %s%s%s' % (
            name_of(p), tpl(top), tpl(v), pos_text(pos(top)), rot_text(rot(top)), health(top),
            ', '.join(names_of(crew_of(top))) or 'nobody', team, same, own)
    return '%s: ON FOOT at %s, heading %s, health %s, side %s' % (name_of(p), pos_text(pos(s)), rot_text(rot(s)),
        health(s), team)

def occupied_armour():
    # [(top, crew)] - every tank / APC somebody sits in, found through the players (never getObjectsOfType)
    out = []
    seen = []
    try:
        L = bf2.playerManager.getPlayers()
    except:
        log('could not read the players: ' + err_text())
        return out
    for p in L:
        n = name_of(p)
        if n in seen or not alive(p):
            continue
        inv, v = in_vehicle(p)
        if not inv or not is_armor(v):
            continue
        top = top_of(v)
        crew = crew_of(top)
        names = names_of(crew)
        if n not in names:
            crew.append(p)
            names.append(n)
        seen.extend(names)
        out.append((top, crew))
    return out

def checks_list():
    L = []
    for w in str(CHECKS).replace(',', ' ').split():
        try:
            L.append(float(w))
        except:
            pass
    return L or [0.5]

# ------------------------------------------------------------------ moves and the looks after them
def watch_move(p, target, what):
    S['n'] = S['n'] + 1
    n = S['n']
    log('#%d %s - to %s; before: %s' % (n, what, pos_text(target), state_text(p)))
    for d in checks_list():
        later(d, look_move, (p, n, what, d, target))
    return n

def look_move(data):
    p, n, what, d, target = data
    if not alive(p):
        txt = '%s DEAD' % name_of(p)
    else:
        inv, v = in_vehicle(p)
        if inv:
            o = top_of(v)
            where = 'IN %s' % tpl(o)
        else:
            o = soldier_of(p)
            where = 'ON FOOT'
        q = pos(o)
        if q is None:
            txt = '%s %s, no position' % (name_of(p), where)
        else:
            txt = '%s %s at %s: %.1f m from the target, %+.1f m higher, heading %s, health %s' % (
                name_of(p), where, pos_text(q), hdist(q, target), q[1] - float(target[1]), rot_text(rot(o)),
                health(o))
            if inv:
                txt = txt + ', crew: %s' % (', '.join(names_of(crew_of(o))) or 'nobody')
    log('#%d %s - %.1f s later: %s' % (n, what, d, txt))
    say('#%d +%.1f s: %s' % (n, d, txt))

def spot_text(kind, k):
    x, y, z, yaw, place = SPOTS[kind][k]
    return '%s %d (%s)' % (kind.replace('_', ' '), k + 1, place)

def own_spot(top):
    # (top, kind, index) remembered when the vehicle was first got into at a spot, or None
    for e in S['vhome']:
        if e[0] is top:
            return e
    return None

def pick_spot(kind, top, crew, taken, others):
    # (index, why): its own spot, else where one of the crew got in, else a free one, else one not taken now
    L = SPOTS[kind]
    t = tpl(top).lower()
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
    for c in crew:
        r = S['entered'].get(name_of(c))
        if r and r[0] == t and r[1] is not None and r[1] < len(L) and not busy(r[1]):
            return r[1], 'where %s got in' % name_of(c)
    for k in range(len(L)):
        if not busy(k):
            return k, 'free'
    for k in range(len(L)):
        if (kind, k) not in taken:
            return k, 'a vehicle may stand there - may ram'
    return 0, 'every spot taken - may ram'

def pin_spots():
    out = []
    for pn in S['pins']:
        if pn['spot'] is not None:
            out.append(pn['spot'])
    return out

def move(top, crew, kind, k, why):
    # the vehicle with its crew to spot k of its kind; everybody in it remembered where he was
    # -> (target or None, 1 if moved)
    x, y, z, yaw, place = SPOTS[kind][k]
    q0 = pos(top)
    target = (x, y + float(TP_UP), z)
    if q0 is not None and hdist(q0, target) < float(PIN_DIST):
        log('  move: %s already at %s (%.1f m) - not moved' % (tpl(top), spot_text(kind, k), hdist(q0, target)))
        return target, 0
    try:
        top.setPosition(target)
    except:
        log('  move: setPosition on %s failed: %s' % (tpl(top), err_text()))
        say('the move failed - see %s' % LOG_FILE, 1)
        return None, 0
    try:
        top.setRotation((float(yaw), 0.0, 0.0))
    except:
        log('  move: setRotation on %s failed: %s' % (tpl(top), err_text()))
    for c in crew:
        n = name_of(c)
        if q0 is not None and n not in S['home']:
            S['home'][n] = q0
    log('  move: %s from %s to %s (%s); crew: %s' % (tpl(top), pos_text(q0), spot_text(kind, k), why,
        ', '.join(names_of(crew)) or 'nobody'))
    if crew:
        watch_move(crew[0], target, 'tp %s -> %s, %s' % (tpl(top), spot_text(kind, k), why))
    return target, 1

# ------------------------------------------------------------------ pins
def add_pin(crew, at, heading, dist, spot, label):
    S['n'] = S['n'] + 1
    pn = {'id': S['n'], 'crew': list(crew), 'at': at, 'rot': heading, 'dist': float(dist), 'spot': spot,
          'pulls': 0, 'label': label}
    S['pins'].append(pn)
    log('pin #%d %s: at %s, heading %s, %.1f m; crew: %s' % (pn['id'], label, pos_text(at), rot_text(heading),
        float(dist), ', '.join(names_of(crew)) or 'nobody'))
    start_tick()
    return pn

def start_tick():
    if S['tick'] is not None:
        return
    try:
        t = bf2.Timer(tick, float(PIN_EVERY), 1, None)
        t.setRecurring(float(PIN_EVERY))
        S['tick'] = t
    except:
        log('could not make the pin timer: ' + err_text())

def stop_tick():
    t = S['tick']
    S['tick'] = None
    if t is not None:
        try:
            t.destroy()
        except:
            pass

def tick(data=None):
    if not S['on']:
        stop_tick()
        return
    keep = []
    for pn in S['pins']:
        try:
            if pin_one(pn):
                keep.append(pn)
        except:
            log('pin #%d: %s' % (pn['id'], err_text()))
            keep.append(pn)
    S['pins'] = keep
    if not keep:
        stop_tick()

def pin_one(pn):
    # 0: the pin is over (nobody of its crew sits in a tank / APC any more)
    top = None
    for c in pn['crew']:
        if not alive(c):
            continue
        inv, v = in_vehicle(c)
        if inv and is_armor(v):
            top = top_of(v)
            break
    if top is None:
        log('pin #%d %s: nobody of its crew in it any more - off after %d pulls' % (pn['id'], pn['label'],
            pn['pulls']))
        say('pin #%d off (crew out; pulled back %d times)' % (pn['id'], pn['pulls']))
        return 0
    q = pos(top)
    if q is None:
        return 1
    d = hdist(q, pn['at'])
    if d <= pn['dist']:
        return 1
    try:
        top.setPosition(pn['at'])
        if pn['rot'] is not None:
            top.setRotation(pn['rot'])
    except:
        log('pin #%d: the pull failed: %s' % (pn['id'], err_text()))
        return 1
    pn['pulls'] = pn['pulls'] + 1
    if pn['pulls'] <= 5 or pn['pulls'] % 20 == 0:
        log('pin #%d: %s was %.1f m away at %s - pulled back (%d)' % (pn['id'], tpl(top), d, pos_text(q),
            pn['pulls']))
    if pn['pulls'] == 1 or pn['pulls'] % 20 == 0:
        say('pin #%d: %s pulled back (%d times so far)' % (pn['id'], tpl(top), pn['pulls']))
    return 1

def drop_player(n):
    # n out of every pin's crew and his place to go back to forgotten
    for pn in S['pins']:
        keep = []
        for c in pn['crew']:
            if name_of(c) != n:
                keep.append(c)
        pn['crew'] = keep
    if n in S['home']:
        del S['home'][n]

# ------------------------------------------------------------------ engines and entry points
def entry_names():
    L = []
    for t in words(ENTRY_NAMES, ','):
        add_name(L, t)
    for t in S['entry_found']:
        add_name(L, t)
    return L

def engine_names():
    L = []
    for t in words(ENGINE_NAMES, ','):
        add_name(L, t)
    for t in S['engine_found']:
        add_name(L, t)
    return L

def zero_list():
    out = []
    for part in words(ENGINE_ZERO, ';'):
        w = part.split(None, 1)
        if len(w) == 2:
            out.append((w[0], w[1]))
    return out

def number_in(a):
    for w in a.replace('=', ' ').split():
        try:
            return float(w)
        except:
            pass
    return None

def set_radius(t, r, quiet=0):
    a = console('ObjectTemplate.activeSafe EntryPoint %s' % t)
    if a and bad_answer(a):
        log('%s: the console said "%s" - not changed' % (t, a))
        if not quiet:
            say('%s: the console said "%s" - not changed' % (t, a))
        return 0
    before = console('ObjectTemplate.setEntryRadius')
    if t not in S['radius']:
        S['radius'][t] = number_in(before)
    b = console('ObjectTemplate.setEntryRadius %s' % r)
    after = console('ObjectTemplate.setEntryRadius')
    txt = '%s: entry radius -> %s (read before: "%s", after: "%s"%s)' % (t, r, before or '-', after or '-',
        (b and '; it said "%s"' % b) or '')
    if quiet:
        log(txt)
    else:
        say(txt)
    return 1

def radius_back(quiet=0):
    k = 0
    for t in list(S['radius'].keys()):
        r = S['radius'][t]
        if r is None or r <= 0:
            log('%s: the radius before was %s - %g put back' % (t, r, float(OPEN_RADIUS)))
            r = float(OPEN_RADIUS)
        k = k + set_radius(t, '%g' % r, quiet)
    S['radius'] = {}
    return k

def engine_set(names, props, quiet=0):
    k = 0
    for t in names:
        a = console('ObjectTemplate.activeSafe Engine %s' % t)
        if a and bad_answer(a):
            log('%s: the console said "%s" - not changed' % (t, a))
            if not quiet:
                say('%s: the console said "%s" - not changed' % (t, a))
            continue
        for prop, val in props:
            before = console('ObjectTemplate.%s' % prop)
            key = (t.lower(), prop)
            if key not in S['engine']:
                S['engine'][key] = (t, before)
            b = console('ObjectTemplate.%s %s' % (prop, val))
            after = console('ObjectTemplate.%s' % prop)
            txt = '%s %s -> %s (read before: "%s", after: "%s"%s)' % (t, prop, val, before or '-', after or '-',
                (b and '; it said "%s"' % b) or '')
            if quiet:
                log(txt)
            else:
                say(txt)
        k = k + 1
    return k

def engine_back(quiet=0):
    k = 0
    keys = list(S['engine'].keys())
    keys.sort()
    for key in keys:
        t, before = S['engine'][key]
        prop = key[1]
        if not before or bad_answer(before):
            txt = '%s %s: the value before is not known ("%s") - a restart puts it back' % (t, prop, before)
            log(txt)
            if not quiet:
                say(txt)
            continue
        console('ObjectTemplate.activeSafe Engine %s' % t)
        console('ObjectTemplate.%s %s' % (prop, before))
        after = console('ObjectTemplate.%s' % prop)
        txt = '%s %s back to %s (reads "%s")' % (t, prop, before, after or '-')
        if quiet:
            log(txt)
        else:
            say(txt)
        k = k + 1
    S['engine'] = {}
    return k

# ------------------------------------------------------------------ guns
GUN_WAYS = {
    'rpm': [('fire.roundsPerMinute', '1')],
    'reload': [('ammo.reloadTime', '3600')],
    'mag': [('ammo.magSize', '0')],
    'all': [('fire.roundsPerMinute', '1'), ('ammo.reloadTime', '3600')]
}
GUN_WAY_ORDER = ['rpm', 'reload', 'mag', 'all']

def gun_names():
    L = []
    for t in words(GUN_NAMES, ','):
        add_name(L, t)
    return L

def gun_activate(t):
    a = console('ObjectTemplate.activeSafe %s %s' % (GUN_TYPE, t))
    if a and bad_answer(a):
        log('%s: the console said "%s" - left alone' % (t, a))
        return 0
    return 1

def gun_read():
    names = gun_names()
    short = []
    for t in names:
        if not gun_activate(t):
            short.append('%s: not found' % t)
            continue
        vals = []
        for prop in words(GUN_READ, ','):
            a = console('ObjectTemplate.%s' % prop)
            vals.append('%s=%s' % (prop, a or '-'))
        log('gun %s: %s' % (t, ', '.join(vals)))
        short.append('%s: %s' % (t, ' '.join(vals[:1] + vals[3:6])))
    say('guns read (all in the log): %s' % '; '.join(short))

def gun_set(props, quiet=0):
    k = 0
    names = gun_names()
    for t in names:
        if not gun_activate(t):
            if not quiet:
                say('%s: not found - not changed' % t)
            continue
        done = 0
        for prop, val in props:
            before = console('ObjectTemplate.%s' % prop)
            if not before or bad_answer(before):
                txt = '%s %s: nothing read ("%s") - not set' % (t, prop, before)
                log(txt)
                if not quiet:
                    say(txt)
                continue
            key = (t.lower(), prop)
            if key not in S['gun']:
                S['gun'][key] = (t, before)
            b = console('ObjectTemplate.%s %s' % (prop, val))
            after = console('ObjectTemplate.%s' % prop)
            txt = '%s %s -> %s (read before: "%s", after: "%s"%s)' % (t, prop, val, before, after or '-',
                (b and '; it said "%s"' % b) or '')
            if quiet:
                log(txt)
            else:
                say(txt)
            done = 1
        k = k + done
    return k

def gun_back(quiet=0):
    k = 0
    keys = list(S['gun'].keys())
    keys.sort()
    for key in keys:
        t, before = S['gun'][key]
        prop = key[1]
        if not gun_activate(t):
            continue
        console('ObjectTemplate.%s %s' % (prop, before))
        after = console('ObjectTemplate.%s' % prop)
        txt = '%s %s back to %s (reads "%s")' % (t, prop, before, after or '-')
        if quiet:
            log(txt)
        else:
            say(txt)
        k = k + 1
    S['gun'] = {}
    return k

def cmd_gun(p, w):
    a = ''
    if len(w) > 2:
        a = w[2].lower()
    if a == 'read':
        gun_read()
        return
    if a == 'back':
        if not S['gun']:
            say('nothing to put back')
            return
        gun_back()
        return
    if a in GUN_WAYS:
        props = GUN_WAYS[a]
        S['gun_last'] = a
    elif a == 'set' and len(w) > 4:
        props = [(w[3], ' '.join(w[4:]))]
    else:
        say("'!ar gun read', '!ar gun rpm|reload|mag|all', '!ar gun set <property> <value>' or '!ar gun back'")
        return
    names = gun_names()
    k = gun_set(props)
    say('%d of %d guns changed (%s) - now try to fire the main gun and the missile' % (k, len(names),
        ', '.join(names)))

# ------------------------------------------------------------------ the commands
def walk_tree(o, depth, out):
    if depth > 6 or len(out) > 400:
        return
    try:
        ch = o.getChildren()
    except:
        ch = None
    if not ch:
        return
    for c in ch:
        out.append((depth, tpl(c)))
        walk_tree(c, depth + 1, out)

def cmd_tree(p):
    inv, v = in_vehicle(p)
    if not inv:
        say('%s is not in a vehicle' % name_of(p))
        return
    top = top_of(v)
    out = []
    walk_tree(top, 1, out)
    log('parts of %s (%d):' % (tpl(top), len(out)))
    for d, t in out:
        log('  %s%s' % ('  ' * (d - 1), t))
    entry = []
    eng = []
    for d, t in out:
        low = t.lower()
        if low.find('entry') >= 0:
            add_name(entry, t)
        if low.find('engine') >= 0:
            add_name(eng, t)
    S['tree'] = entry
    S['tree_eng'] = eng
    for t in entry:
        add_name(S['entry_found'], t)
    for t in eng:
        add_name(S['engine_found'], t)
    say('%s: %d parts (all in the log); entry points: %s; engines: %s' % (tpl(top), len(out),
        ', '.join(entry) or 'none named so', ', '.join(eng) or 'none named so'))

def cmd_entry(p, arg, arg2):
    if not arg:
        say("'!ar entry <radius> [template]' or '!ar entry back'")
        return
    if arg.lower() == 'back':
        if not S['radius']:
            say('nothing to put back')
            return
        radius_back()
        return
    try:
        float(arg)
    except:
        say('the radius must be a number')
        return
    if arg2:
        names = [arg2]
    else:
        names = S['tree']
    if not names:
        say("no entry points known - '!ar tree' in the vehicle first, or name the template")
        return
    for t in names:
        set_radius(t, arg)
    say('now get out and try to get in again')

def cmd_engine(p, w):
    a = ''
    if len(w) > 2:
        a = w[2].lower()
    if a == 'back':
        if not S['engine']:
            say('nothing to put back')
            return
        engine_back()
        return
    names = []
    for t in S['tree_eng']:
        add_name(names, t)
    for t in engine_names():
        add_name(names, t)
    if a == '0':
        props = zero_list()
    elif a == 'set' and len(w) > 4:
        props = [(w[3], ' '.join(w[4:]))]
    else:
        say("'!ar engine 0', '!ar engine back' or '!ar engine set <property> <value>'")
        return
    if not props:
        say('ENGINE_ZERO has nothing to set')
        return
    k = engine_set(names, props)
    say('%d of %d engines changed (%s) - now try to drive' % (k, len(names), ', '.join(names)))

def cmd_count():
    try:
        L = bf2.playerManager.getPlayers()
    except:
        say('could not read the players: ' + err_text())
        return
    n = 0
    bots = 0
    people = 0
    conn = 0
    for q in L:
        n = n + 1
        ai = 0
        try:
            ai = q.isAIPlayer()
        except:
            pass
        if ai:
            bots = bots + 1
        else:
            people = people + 1
            try:
                if q.isConnected():
                    conn = conn + 1
            except:
                pass
    say('players: %d - people %d (connected %d), bots %d' % (n, people, conn, bots))

def cmd_spots(p):
    inv, v = in_vehicle(p)
    if inv:
        o = top_of(v)
    else:
        o = soldier_of(p)
    q = pos(o)
    parts = []
    for kind in KIND_ORDER:
        k = 0
        for s in SPOTS[kind]:
            d = '?'
            if q is not None:
                d = '%.0f m' % hdist(q, s)
            parts.append('%s %s' % (spot_text(kind, k), d))
            log('spot %s at %.1f/%.1f/%.1f heading %g' % (spot_text(kind, k), s[0], s[1], s[2], s[3]))
            k = k + 1
    say('you at %s; spots: %s' % (pos_text(q), '; '.join(parts)))

def cmd_tp(p, arg):
    inv, v = in_vehicle(p)
    if not inv:
        say('%s is not in a vehicle' % name_of(p))
        return
    if not on_karkand():
        return
    top = top_of(v)
    kind = kind_of(top)
    if kind is None:
        say('%s is not a tank / APC of Karkand' % tpl(top))
        return
    crew = crew_of(top)
    if name_of(p) not in names_of(crew):
        crew.append(p)
    L = SPOTS[kind]
    if arg:
        try:
            k = int(arg) - 1
        except:
            k = -1
        if k < 0 or k >= len(L):
            say('%s has %d spot(s)' % (kind.replace('_', ' '), len(L)))
            return
        why = 'asked'
    else:
        mine = names_of(crew)
        others = []
        for o, c in occupied_armour():
            if not [x for x in names_of(c) if x in mine]:
                others.append(pos(o))
        k, why = pick_spot(kind, top, crew, pin_spots(), others)
    target, moved = move(top, crew, kind, k, why)
    if target is not None and not moved:
        say('%s is at %s already' % (tpl(top), spot_text(kind, k)))

def cmd_mark(p):
    inv, v = in_vehicle(p)
    if inv:
        o = top_of(v)
        what = tpl(o)
    else:
        o = soldier_of(p)
        what = 'you on foot'
    q = pos(o)
    if q is None:
        say('no position')
        return
    S['mark'][name_of(p)] = (q, rot(o))
    say('marked: %s at %s, heading %s' % (what, pos_text(q), rot_text(rot(o))))

def cmd_back(p):
    m = S['mark'].get(name_of(p))
    if not m:
        say("no mark - '!ar mark' first")
        return
    q, r = m
    inv, v = in_vehicle(p)
    if inv:
        o = top_of(v)
        target = (q[0], q[1] + float(TP_UP), q[2])
        what = 'back: %s to the mark' % tpl(o)
    else:
        o = soldier_of(p)
        target = (q[0], q[1] + float(HOME_UP), q[2])
        what = 'back: %s on foot to the mark' % name_of(p)
    watch_move(p, target, what)
    try:
        o.setPosition(target)
        if inv and r is not None:
            o.setRotation(r)
    except:
        log('  back: failed: ' + err_text())
        say('back failed - see %s' % LOG_FILE, 1)

def cmd_pin(p, arg):
    if arg.lower() == 'off':
        k = len(S['pins'])
        S['pins'] = []
        stop_tick()
        say('%d pin(s) off' % k)
        return
    inv, v = in_vehicle(p)
    if not inv:
        say('%s is not in a vehicle' % name_of(p))
        return
    dist = float(PIN_DIST)
    if arg:
        try:
            dist = float(arg)
        except:
            say("'!ar pin [metres]' or '!ar pin off'")
            return
    top = top_of(v)
    crew = crew_of(top)
    if name_of(p) not in names_of(crew):
        crew.append(p)
    q = pos(top)
    if q is None:
        say('the vehicle has no position')
        return
    pn = add_pin(crew, q, rot(top), dist, None, tpl(top))
    say('pin #%d: %s held at %s (%.1f m) until its crew are out - now try to drive' % (pn['id'], tpl(top),
        pos_text(q), dist))

def cmd_sim(p, w):
    try:
        n = int(w[2])
    except:
        say("'!ar sim <players> [engine|pin|both|none] [rpm|reload|mag|all|none]'")
        return
    way = str(STOP).lower()
    if len(w) > 3:
        way = w[3].lower()
    if way not in ('pin', 'engine', 'both', 'none'):
        say('the way is engine, pin, both or none')
        return
    gun = S['gun_last']
    if len(w) > 4:
        gun = w[4].lower()
    if gun not in GUN_WAYS:
        gun = ''
    if n < int(LIMIT):
        close_scene(n, way, gun)
    else:
        open_scene(n)

def close_scene(n, way, gun=''):
    if not on_karkand():
        return
    log('sim %d (%s): close' % (n, way))
    names = entry_names()
    shut = 0
    for t in names:
        shut = shut + set_radius(t, '0', 1)
    eng = 0
    engs = engine_names()
    if way in ('engine', 'both'):
        eng = engine_set(engs, zero_list(), 1)
    guns = 0
    if gun:
        guns = gun_set(GUN_WAYS[gun], 1)
    S['closed'] = 1
    S['stop'] = way
    what = ['closed']
    if way in ('engine', 'both'):
        what.append('stopped')
    if gun:
        what.append('guns locked')
    if len(what) > 1:
        what = ', '.join(what[:-1]) + ' and ' + what[-1]
    else:
        what = what[0]
    say_limit('%d players: tanks and APCs %s until %d' % (n, what, int(LIMIT)))
    arm = occupied_armour()
    taken = pin_spots()
    moved = []
    vehicles = 0
    notmoved = 0
    pins = 0
    i = 0
    for top, crew in arm:
        kind = kind_of(top)
        target = None
        spot = None
        if kind is None:
            log('  %s: not a Karkand tank / APC - not moved' % tpl(top))
        else:
            others = []
            j = 0
            for o, c in arm:
                if j != i:
                    others.append(pos(o))
                j = j + 1
            k, why = pick_spot(kind, top, crew, taken, others)
            target, did = move(top, crew, kind, k, why)
            if target is not None:
                spot = (kind, k)
                taken.append(spot)
                if did:
                    vehicles = vehicles + 1
                    for c in crew:
                        if not is_bot(c) and name_of(c) not in moved:
                            moved.append(name_of(c))
        if target is None:
            notmoved = notmoved + 1
            target = pos(top)
            heading = rot(top)
        else:
            heading = (float(SPOTS[kind][spot[1]][3]), 0.0, 0.0)
        if way in ('pin', 'both') and target is not None:
            add_pin(crew, target, heading, PIN_DIST, spot, tpl(top))
            pins = pins + 1
        i = i + 1
    if moved:
        say_limit('%s: your tank/APC was moved to base until %d players' % (', '.join(moved), int(LIMIT)))
    say('sim %d (%s, guns %s): entry 0 on %d of %d entry points; engines %d of %d; guns %d of %d; moved %d, not '
        'moved %d; pins %d' % (n, way, gun or 'none', shut, len(names), eng, len(engs), guns, len(gun_names()),
        vehicles, notmoved, pins))

def open_scene(n):
    log('sim %d: open' % n)
    k = radius_back(1)
    e = engine_back(1)
    g = gun_back(1)
    pins = len(S['pins'])
    S['pins'] = []
    stop_tick()
    homes = len(S['home'])
    S['home'] = {}
    S['closed'] = 0
    S['stop'] = ''
    say_limit('%d players: tanks and APCs open' % n)
    say('sim %d: entry back on %d, engines back %d, guns back %d, pins off %d, places to put back forgotten %d' % (
        n, k, e, g, pins, homes))

# ------------------------------------------------------------------ events
def on_enter(player, vehicle=None, freeSoldier=None, *rest):
    if not S['on']:
        return
    try:
        top = top_of(vehicle)
        kind = kind_of(top)
        k = None
        q = pos(top)
        if kind is not None and q is not None:
            j = 0
            for s in SPOTS[kind]:
                if hdist(q, s) < float(SPOT_NEAR):
                    k = j
                j = j + 1
        n = name_of(player)
        if kind is not None:
            S['entered'][n] = (tpl(top).lower(), k)
            S['entered_obj'][n] = top
            if k is not None and own_spot(top) is None:
                S['vhome'].append((top, kind, k))
                if len(S['vhome']) > 60:
                    del S['vhome'][0]
                log('  %s: its own spot is %s' % (tpl(top), spot_text(kind, k)))
        at = ''
        if k is not None:
            at = ', at ' + spot_text(kind, k)
        log('EnterVehicle: %s into %s (top %s%s) at %s%s; freeSoldier=%s; crew: %s' % (n, tpl(vehicle), tpl(top),
            (is_armor(vehicle) and ', ARMOR') or '', pos_text(q), at, freeSoldier,
            ', '.join(names_of(crew_of(top))) or 'nobody'))
    except:
        log('EnterVehicle: ' + err_text())

def on_exit(player, vehicle=None, *rest):
    if not S['on']:
        return
    try:
        log('ExitVehicle: %s out of %s (top %s); %s' % (name_of(player), tpl(vehicle), tpl(top_of(vehicle)),
            state_text(player)))
        later(float(EXIT_DELAY), after_exit, player)
    except:
        log('ExitVehicle: ' + err_text())

def after_exit(p):
    n = name_of(p)
    inv, v = in_vehicle(p)
    if inv:
        log('%s: in %s %.1f s after getting out - a seat change, nothing done' % (n, tpl(v), float(EXIT_DELAY)))
        return
    h = S['home'].get(n)
    drop_player(n)
    if h is None:
        return
    if not alive(p):
        log('%s: dead - not put back' % n)
        return
    s = soldier_of(p)
    target = (h[0], h[1] + float(HOME_UP), h[2])
    watch_move(p, target, 'put back: %s where he was before the move' % n)
    try:
        s.setPosition(target)
    except:
        log('  put back: setPosition failed: ' + err_text())
        say('putting %s back failed - see %s' % (n, LOG_FILE), 1)
        return
    say('%s put back where he was before the move (%s)' % (n, pos_text(h)))
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
        log('%s: %.1f m from the place %.1f s after the put-back - fine' % (n, d, float(PUT_CHECK)))
        return
    t2 = (target[0], target[1] + float(PUT_RETRY_UP), target[2])
    log('%s: %.1f m from the place %.1f s after the put-back (at %s) - put again %.1f m higher' % (n, d,
        float(PUT_CHECK), pos_text(q), float(PUT_RETRY_UP)))
    watch_move(p, t2, 'put back again: %s, %.1f m higher' % (n, float(PUT_RETRY_UP)))
    try:
        s.setPosition(t2)
    except:
        log('  put back again: setPosition failed: ' + err_text())
        return
    say('%s was put %.0f m away by the game - put back again %.1f m higher' % (n, d, float(PUT_RETRY_UP)))

def on_killed(victim, *rest):
    if not S['on']:
        return
    try:
        n = name_of(victim)
        if n in S['home']:
            log('%s killed - his place to go back to forgotten' % n)
        drop_player(n)
    except:
        log('PlayerKilled: ' + err_text())

def may_test(name):
    if not TEST_ADMINS:
        return 1
    for n in words(TEST_ADMINS, ','):
        if n.lower() == name.lower():
            return 1
    return 0

HELP = ("'!ar state'; '!ar count'; '!ar spots'; '!ar tp [1|2]' - your tank/APC with its crew to its spot; "
        "'!ar mark' / '!ar back'; '!ar pin [m|off]'; '!ar engine 0|back' or 'engine set <property> <value>'; "
        "'!ar gun read|rpm|reload|mag|all|back' or 'gun set <property> <value>'; '!ar tree'; "
        "'!ar entry <r> [tpl]' / 'entry back'; '!ar sim <n> [engine|pin|both|none] [rpm|reload|mag|all|none]' - "
        "pretend n players; '!ar con <console line>'")

def on_chat(playerId, text, channel=None, flags=None):
    if not S['on']:
        return
    try:
        s = str(text)
    except:
        return
    i = s.lower().find('!ar')
    if i < 0:
        return
    w = s[i:].split()
    if not w or w[0].lower() != '!ar':
        return
    cmd = ''
    if len(w) > 1:
        cmd = w[1].lower()
    arg = ''
    if len(w) > 2:
        arg = w[2]
    arg2 = ''
    if len(w) > 3:
        arg2 = w[3]
    try:
        p = bf2.playerManager.getPlayerByIndex(int(playerId))
    except:
        p = None
    if p is None:
        return
    name = name_of(p)
    if not may_test(name):
        say('%s may not use the test commands (mm_armortest.TEST_ADMINS)' % name)
        return
    log('%s: "%s"' % (name, ' '.join(w)))
    try:
        if cmd == 'state':
            say(state_text(p))
        elif cmd == 'count':
            cmd_count()
        elif cmd == 'spots':
            cmd_spots(p)
        elif cmd == 'tp':
            cmd_tp(p, arg)
        elif cmd == 'mark':
            cmd_mark(p)
        elif cmd == 'back':
            cmd_back(p)
        elif cmd == 'pin':
            cmd_pin(p, arg)
        elif cmd == 'engine':
            cmd_engine(p, w)
        elif cmd == 'gun':
            cmd_gun(p, w)
        elif cmd == 'tree':
            cmd_tree(p)
        elif cmd == 'entry':
            cmd_entry(p, arg, arg2)
        elif cmd == 'sim':
            cmd_sim(p, w)
        elif cmd == 'con' and len(w) > 2:
            line = s[i:].split(None, 2)[2]
            a = console(line)
            say('console: %s -> %s' % (line, a or '(no answer)'))
        else:
            say(HELP, 1)
    except:
        log('command %s: %s' % (cmd, err_text()))
        say('the command failed - see %s' % LOG_FILE, 1)

def on_status(status):
    if not S['on']:
        return
    try:
        if status == bf2.GameStatus.Playing:
            k = len(S['pins'])
            S['pins'] = []
            stop_tick()
            S['home'] = {}
            S['entered'] = {}
            S['entered_obj'] = {}
            S['vhome'] = []
            log('round on %s (pins dropped %d; entry %s)' % (map_name(), k,
                (S['closed'] and "still CLOSED by '!ar sim' - '!ar sim 12' opens it") or 'as it was'))
    except:
        log('status: ' + err_text())

def armortest_init():
    if S['on']:
        return
    S['on'] = 1
    log('armortest %s loaded on %s (armour: %s; limit %d; stop %s; pin %.1f m / %.2f s; entry names: %s; engines: %s;'
        ' engine 0 = %s; guns (%s): %s; test admins: %s) - FOR A TEST SERVER ONLY' % (VERSION, map_name(), ARMOR,
        int(LIMIT), STOP, float(PIN_DIST), float(PIN_EVERY), ENTRY_NAMES, ENGINE_NAMES, ENGINE_ZERO, GUN_TYPE,
        GUN_NAMES, TEST_ADMINS or 'anybody'))
    for ev, fn in (('ChatMessage', on_chat), ('EnterVehicle', on_enter), ('ExitVehicle', on_exit),
                   ('PlayerKilled', on_killed)):
        try:
            host.registerHandler(ev, fn, 1)
        except:
            log('could not register %s: %s' % (ev, err_text()))
    try:
        host.registerGameStatusHandler(on_status)
    except:
        log('could not register the status handler: ' + err_text())

# ------------------------------------------------------------------ ModManager interface
configDefaults = {}
for _k in ['TEST_ADMINS', 'ARMOR', 'LIMIT', 'STOP', 'TP_UP', 'HOME_UP', 'EXIT_DELAY', 'SPOT_NEAR', 'FREE_DIST',
           'PIN_DIST', 'PIN_EVERY', 'ENTRY_NAMES', 'ENGINE_NAMES', 'ENGINE_ZERO', 'GUN_NAMES', 'GUN_TYPE', 'GUN_READ',
           'PUT_CHECK', 'PUT_RETRY_DIST', 'PUT_RETRY_UP', 'OPEN_RADIUS', 'CHECKS', 'SAY', 'CHAT_MAX', 'LOG_FILE']:
    configDefaults[_k] = globals()[_k]

class ArmorTest( object ):

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
        for k in ('TP_UP', 'HOME_UP', 'EXIT_DELAY', 'SPOT_NEAR', 'FREE_DIST', 'PIN_DIST', 'PIN_EVERY', 'OPEN_RADIUS',
                  'PUT_CHECK', 'PUT_RETRY_DIST', 'PUT_RETRY_UP'):
            try:
                g[k] = float(g[k])
            except:
                g[k] = configDefaults[k]
        for k in ('LIMIT', 'SAY', 'CHAT_MAX'):
            try:
                g[k] = int(g[k])
            except:
                g[k] = configDefaults[k]
        if g['PIN_EVERY'] < 0.05:
            g['PIN_EVERY'] = 0.05
        self.__state = 1
        armortest_init()
        try:
            self.mm.info( 'armortest %s is running - FOR A TEST SERVER ONLY (see %s)' % ( VERSION, LOG_FILE or 'no log' ) )
        except:
            pass

    def shutdown( self ):
        self.__state = 2
        S['on'] = 0
        stop_tick()

    def update( self ):
        pass

def mm_load( modManager ):
    return ArmorTest( modManager )
