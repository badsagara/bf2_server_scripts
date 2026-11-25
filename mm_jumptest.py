# mm_jumptest.py - JumpTest 0.1.3: FOR A TEST SERVER ONLY - a practice kit for jumps.
# A Multiplay ModManager module (ModManager 1.0 or later, Python 2.3 of BF2 1.5). Standalone: it does not need
# mm_flbus. It never asks the game for all objects of a type (getObjectsOfType).
#
# Sagara 15.11.2026 21:59 / 22:06:
#   - endless stamina (the soldier templates' sprint values, through the console - to be tested);
#   - no damage at all: the soldiers' maximum health raised through the console and kept full (a fall does not kill);
#   - points: save where you stand under a name and go back to it (each player his own, kept in a file);
#   - a Vodnik in front of you on a command;
#   - back to your point by itself after a missed jump;
#   - a jump meter (up, across, time in the air) and a distance meter between two places you stand on.
#
# Commands (chat; every player may use them unless TEST_ADMINS names who may; the answers go into the chat):
#   !j                  the list
#   !j state            what is on, your points, your marks
#   !j save [name]      save where you stand (name: default "1"); it becomes your active point
#   !j go [name]        go to the point (default: your active point); it becomes your active point
#   !j list             your points
#   !j del <name>       forget a point
#   !j auto [on|off|m]  back to the active point by itself after a missed jump: a jump or fall started within
#                       AUTO_RANGE 30 m of the point and no more than 1 m below it, landing more than AUTO_DROP 2 m
#                       below it -> AUTO_DELAY 1 s later back on the point (a number sets your drop in metres)
#   !j meter [on|off]   a line after every jump / fall: up, landed higher or lower, across, time in the air
#   !j a / !j b         mark where you stand as A / B; after B: straight distance, across the ground, height
#   !j + / !j -         mark your last jump good / missed (!j + 7 - jump #7); every jump gets a number
#   !j cmp              your last missed jump against your last good one from the same place (within CMP_NEAR m):
#                       what differs - take-off point, speed, direction, turning, run-up, push-off, ping
#   !j cmp all          all your good jumps against all your missed ones from that place (averages and spread)
#   !j cmp <a> <b>      jump #b against jump #a
#   !j info [n]         everything recorded about your last jump (or #n)
#   !j jumps            your last jumps with their numbers and marks
#   !j v                a Vodnik VEH_AHEAD 4 m in front of you; again - the same Vodnik moved to you
#   !j stamina [on|off|read]   the sprint values of the soldier templates (on at the round start if STAMINA 1)
#   !j god [on|off|read]       the maximum health raised and kept full (on at the round start if GOD 1)
#   !j con <line>       any console line and its answer
#   !jj [m]             a big jump: an arc m forward (where you look, across the ground) with its top m up (default
#                       JJ_DIST 8, at most JJ_MAX 200). The server cannot push a soldier, so the module draws the flight
#                       itself: every server frame it puts you on the next point of the arc (the game's gravity 14.73).
#                       A wall or a roof on the way stops you there and lets you go. No jump lines / records and no
#                       auto-return during it; when you stand again: how far from the start you landed.
#
# INSTALL (test server)
#   1. Copy this file to <server folder>/admin/modules/mm_jumptest.py
#   2. modmanager.con:   modmanager.loadModule "mm_jumptest"
#   3. Restart the server; jumptest.log (server folder) should say "jumptest 0.1.3 loaded".
# Settings (modmanager.con lines under the loadModule lines, e.g.  mm_jumptest.AUTO_DROP 3): below.
#
# The jump recorder (0.1.2). The server does not see keys - only how the soldier moves. Every server frame
# (FRAME_EVERY) the module keeps each player's position and facing for the last KEEP s and through a jump. At the
# landing it finds, to one frame (~0.03 s): the take-off frame (Space), the speed then (sprint ~7 m/s = Shift, run
# ~3.9, slow ~2), the way he moved against where he looked (forward = W, forward-left = W+A, ...), the turning before
# and in the air (the mouse), the run-up, the push-off, the top, the landing. The crouch (Ctrl) is not seen.
# jumptest.log gets a JUMP line and the frames (t from the take-off, x/y/z, facing) for every jump and fall.
#
# History
# 0.1.3 (2026-11-19) !jj [m]: an arc m forward with its top m up, drawn frame by frame (Sagara 19.11: "!jj - stribaye na
#                    8 metriv"; arc forward and up, '!jj <m>' up to 200 m, the look across the ground only, everybody).
# 0.1.2 (2026-11-15) the jump recorder: every jump and fall numbered and measured from every server frame;
#                    !j + / !j - (Sagara marks it himself), !j cmp (in the chat and the log), !j info, !j jumps.
# 0.1.1 (2026-11-15) the test of 0.1.0: the answers to the player only (host.sgl_sendTextMessage) did not show - now
#                    into the chat with his name (SAY_PRIVATE 0); a move straight to a point was stopped by the first
#                    wall on the line (the auto-return stopped half-way at a house and he fell) - now up 60 m, across,
#                    down (as fldm), checked 0.25 s later and tried once more straight; no jump lines while moving.
# 0.1.0 (2026-11-15) first version.

__version__ = 0.13

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

__description__ = 'JumpTest v0.1.3 (ModManager module, test servers only)'

import bf2
import host
import sys

VERSION = '0.1.3'

# ------------------------------------------------------------------ settings
TEST_ADMINS = ''          # names that may use the commands, comma-separated ('' - anybody)
SOLDIERS = 'us_light_soldier,us_heavy_soldier,mec_light_soldier,mec_heavy_soldier'   # + every soldier seen
SOLDIER_TYPE = 'Soldier'  # the template type for ObjectTemplate.activeSafe
STAMINA = 1               # 1: endless stamina put on at the round start
STAMINA_SET = 'SprintRecoverTime 0.1;SprintDissipationTime 100000;SprintLossAtJump 0'   # ';' between
STAMINA_READ = 'SprintRecoverTime,SprintDissipationTime,SprintLimit,SprintLossAtJump,SprintFactor'
GOD = 1                   # 1: no damage - put on at the round start
GOD_SET = 'armor.maxHitPoints 10000;armor.hitPoints 10000'
GOD_READ = 'armor.maxHitPoints,armor.hitPoints'
GOD_HP = 10000.0          # health kept (a soldier with less is set to this)
GOD_BOTS = 0              # 1: bots kept full too
HEAL_EVERY = 0.2          # s
SAMPLE = 0.05             # s: how often a jump is looked for (the 0.1.0 detection)
FRAME_EVERY = 0.02        # s: the recorder's look (in practice every server frame, ~30 a second)
KEEP = 3.0                # s of frames kept before a take-off
RUNUP_LOG = 1.5           # s of run-up written to the log with each jump
RUNUP_MIN = 1.0           # m/s: slower than this = the run-up starts here
STAND_MAX = 0.5           # m/s: slower = standing
RUN_MIN = 2.6             # m/s: run from here (the game: run 3.9, crouch 2.0, prone 0.8)
SPRINT_MIN = 5.0          # m/s: sprint from here (not yet full speed below SPRINT_FULL)
SPRINT_FULL = 6.5         # m/s: full sprint (the game: 7.0)
CMP_NEAR = 10.0           # m: jumps compared only when they took off this near each other
JUMPS_MAX = 300           # jumps kept per player
FRAMES_LOG = 1            # 1: the frames of every jump into the log
GRAVITY = 9.81            # m/s2: falling at least half of this = in the air
UP_SPEED = 3.0            # m/s up from the ground = a jump
AIR_MIN = 0.25            # s: shorter is not a jump (steps, stairs)
AIR_MAX = 10.0            # s
TP_STEP = 4.0             # m in one look = a teleport or a respawn, not a jump
AUTO = 1                  # auto-return on for everybody at first
AUTO_DROP = 2.0           # m below the point = a missed jump
AUTO_FROM = 1.0           # m: the jump must start no more than this below the point
AUTO_RANGE = 30.0         # m across the ground from the point
AUTO_DELAY = 1.0          # s after the landing
METER = 1                 # the jump meter on for everybody at first
POINTS_FILE = 'jumptest_points.txt'
TP_UP = 0.3               # m: put this much above a point
SKY = 60.0                # m: a move goes up this much over the higher place, across, then down
MOVE_STEP = 0.1           # s between the steps of a move
DIRECT_NEAR = 3.0         # m: nearer than this (and within 1 m of height) - one straight step
ARRIVE_CHECK = 0.25       # s after the last step: there? (else once more straight; short - he may walk on)
TP_OK = 2.0               # m: arrived
VEHICLE = 'JEP_VODNIK'
VEH_AHEAD = 4.0           # m in front of you
VEH_UP = 0.5              # m above your feet
JJ_DIST = 8.0             # m: '!jj' with no number - forward, and the top this high
JJ_MAX = 200.0            # m at most
JJ_MIN = 1.0              # m at least
JJ_GRAVITY = 14.73        # m/s2 for the drawn arc (the game's own, measured in the demos)
JJ_HIT = 0.5              # m: the frame after a step he is this far off it (across, or above it on the way down)
                          # = a wall / a roof stopped him -> the flight ends there
JJ_SETTLE = 10.0          # s at most to wait for him to stand again after the flight
SAY_PRIVATE = 0           # 0: to everybody (with the name); 1: host.sgl_sendTextMessage - showed nothing (test 15.11)
CHAT_MAX = 170
LOG_FILE = 'jumptest.log'
BAD = ['not found', 'unknown', 'error', 'invalid', 'no such', 'could not', 'too few']

S = {'on': 0, 'timers': [], 'tick': None, 'last_heal': 0.0, 'stamina': 0, 'god': 0,
     'want_stamina': 1, 'want_god': 1,   # put on again at every round start (off by command)
     'tweak': {},          # (template lower, property) -> (template, value before)
     'seen': [],           # soldier templates seen
     'ps': {},             # player name -> his state
     'points': {}}         # player name -> {point name: (x, y, z, yaw)}

PI = 3.14159265358979

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

def pieces(text):
    out = []
    while len(text) > CHAT_MAX:
        cut = text.rfind(' ', 0, CHAT_MAX)
        if cut < 40:
            cut = CHAT_MAX
        out.append(text[:cut])
        text = '  ' + text[cut:].strip()
    out.append(text)
    return out

def say_all(text):
    for part in pieces('[Jump] ' + text):
        try:
            host.rcon_invoke('game.sayAll "%s"' % part.replace('"', "'"))
        except:
            pass

def tell(p, text):
    # into the chat with his name (SAY_PRIVATE 1: to him only - that showed nothing in the test)
    log('to %s: %s' % (name_of(p), text))
    if not text.startswith(name_of(p)):
        text = '%s: %s' % (name_of(p), text)
    if SAY_PRIVATE:
        try:
            idx = int(p.index)
            for part in pieces('[Jump] ' + text):
                host.sgl_sendTextMessage(idx, 10, 1, part, 0)
            return
        except:
            log('private message failed (%s) - to everybody' % err_text())
    say_all(text)

def console(line):
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
    for x in L:
        if x.lower() == name.lower():
            return
    L.append(name)

# ------------------------------------------------------------------ maths
def sin_(a):
    # a in radians
    a = a % (2.0 * PI)
    if a > PI:
        a = a - 2.0 * PI
    term = a
    s = a
    a2 = a * a
    k = 1
    while k < 9:
        term = -term * a2 / ((2.0 * k) * (2.0 * k + 1.0))
        s = s + term
        k = k + 1
    return s

def cos_(a):
    return sin_(a + PI / 2.0)

def hdist(a, b):
    dx = float(a[0]) - float(b[0])
    dz = float(a[2]) - float(b[2])
    return (dx * dx + dz * dz) ** 0.5

def dist3(a, b):
    dx = float(a[0]) - float(b[0])
    dy = float(a[1]) - float(b[1])
    dz = float(a[2]) - float(b[2])
    return (dx * dx + dy * dy + dz * dz) ** 0.5

def atan_(x):
    # |x| <= 1, error under 0.1 deg
    ax = abs(x)
    return PI / 4.0 * x - x * (ax - 1.0) * (0.2447 + 0.0663 * ax)

def heading_of(dx, dz):
    # degrees, 0 = +z, 90 = +x (as the soldiers' facing: x += sin, z += cos)
    if abs(dx) < 1e-9 and abs(dz) < 1e-9:
        return 0.0
    if abs(dz) >= abs(dx):
        a = atan_(dx / dz)
        if dz < 0:
            a = a + PI
    else:
        a = PI / 2.0 - atan_(dz / dx)
        if dx < 0:
            a = a + PI
    return norm180(a * 180.0 / PI)

def norm180(a):
    a = float(a) % 360.0
    if a > 180.0:
        a = a - 360.0
    return a

# ------------------------------------------------------------------ players
def name_of(p):
    try:
        return p.getName().strip()
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

def health(o):
    try:
        return float(o.getDamage())
    except:
        return None

def ps(p):
    n = name_of(p)
    st = S['ps'].get(n)
    if st is None:
        st = {'active': None, 'auto': int(AUTO), 'drop': float(AUTO_DROP), 'meter': int(METER), 'a': None,
              'veh': None, 'js': {'state': None}, 'healed': 0, 'jumps': 0,
              'jj': None,         # a '!jj' flight under way
              'raw': [],          # the recorder's frames: (t, x, y, z, facing)
              'dup': None,        # the last frame skipped as the same place
              'jl': [],           # recorded jumps (dicts), the last JUMPS_MAX
              'tt': -1.0,         # when the detection last looked
              'last_land': None}  # when the last recorded jump / fall landed
        S['ps'][n] = st
    return st

def points_of(n):
    d = S['points'].get(n)
    if d is None:
        d = {}
        S['points'][n] = d
    return d

# ------------------------------------------------------------------ points file
def load_points():
    try:
        f = open(POINTS_FILE, 'r')
    except:
        log('no points file yet (%s)' % POINTS_FILE)
        return
    k = 0
    try:
        for line in f.readlines():
            w = line.rstrip('\r\n').split('\t')
            if len(w) < 6:
                continue
            try:
                points_of(w[0])[w[1]] = (float(w[2]), float(w[3]), float(w[4]), float(w[5]))
                k = k + 1
            except:
                pass
    finally:
        f.close()
    log('%d points read from %s' % (k, POINTS_FILE))

def save_points():
    try:
        f = open(POINTS_FILE, 'w')
        try:
            names = list(S['points'].keys())
            names.sort()
            for n in names:
                d = S['points'][n]
                keys = list(d.keys())
                keys.sort()
                for k in keys:
                    x, y, z, yaw = d[k]
                    f.write('%s\t%s\t%.3f\t%.3f\t%.3f\t%.1f\n' % (n, k, x, y, z, yaw))
        finally:
            f.close()
    except:
        log('could not write %s: %s' % (POINTS_FILE, err_text()))

# ------------------------------------------------------------------ templates (stamina, health)
def soldier_names():
    L = []
    for t in words(SOLDIERS, ','):
        add_name(L, t)
    for t in S['seen']:
        add_name(L, t)
    return L

def prop_list(text):
    out = []
    for part in words(text, ';'):
        w = part.split(None, 1)
        if len(w) == 2:
            out.append((w[0], w[1]))
    return out

def activate(t):
    a = console('ObjectTemplate.activeSafe %s %s' % (SOLDIER_TYPE, t))
    if a and bad_answer(a):
        log('%s: the console said "%s" - left alone' % (t, a))
        return 0
    return 1

def tweak_read(props):
    out = []
    for t in soldier_names():
        if not activate(t):
            out.append('%s: not found' % t)
            continue
        vals = []
        for prop in words(props, ','):
            vals.append('%s=%s' % (prop, console('ObjectTemplate.%s' % prop) or '-'))
        out.append('%s: %s' % (t, ' '.join(vals)))
    return out

def tweak_set(props):
    # -> number of templates changed; the values before kept (the first read) for tweak_back
    k = 0
    for t in soldier_names():
        if not activate(t):
            continue
        done = 0
        for prop, val in props:
            key = (t.lower(), prop)
            if key not in S['tweak']:
                before = console('ObjectTemplate.%s' % prop)
                if not before or bad_answer(before):
                    log('%s %s: nothing read ("%s") - not set' % (t, prop, before))
                    continue
                S['tweak'][key] = (t, before)
            console('ObjectTemplate.%s %s' % (prop, val))
            after = console('ObjectTemplate.%s' % prop)
            log('%s %s -> %s (before "%s", reads "%s")' % (t, prop, val, S['tweak'][key][1], after))
            done = 1
        k = k + done
    return k

def tweak_back(props):
    k = 0
    for prop, val in props:
        keys = list(S['tweak'].keys())
        keys.sort()
        for key in keys:
            if key[1] != prop:
                continue
            t, before = S['tweak'][key]
            if not activate(t):
                continue
            console('ObjectTemplate.%s %s' % (prop, before))
            del S['tweak'][key]
            k = k + 1
    return k

def stamina_on():
    k = tweak_set(prop_list(STAMINA_SET))
    S['stamina'] = 1
    S['want_stamina'] = 1
    log('stamina ON on %d soldier templates' % k)
    return k

def stamina_off():
    k = tweak_back(prop_list(STAMINA_SET))
    S['stamina'] = 0
    S['want_stamina'] = 0
    log('stamina OFF (%d values back)' % k)
    return k

def god_on():
    k = tweak_set(prop_list(GOD_SET))
    S['god'] = 1
    S['want_god'] = 1
    log('god ON on %d soldier templates' % k)
    return k

def god_off():
    k = tweak_back(prop_list(GOD_SET))
    S['god'] = 0
    S['want_god'] = 0
    # health back to normal for everybody alive
    try:
        for p in bf2.playerManager.getPlayers():
            s = soldier_of(p)
            if s is not None and alive(p):
                try:
                    s.setDamage(100.0)
                except:
                    pass
    except:
        pass
    log('god OFF (%d values back, health set 100)' % k)
    return k

def see_soldier(p):
    s = soldier_of(p)
    if s is None:
        return
    t = tpl(s)
    if t == '?':
        return
    for x in soldier_names():
        if x.lower() == t.lower():
            return
    S['seen'].append(t)
    log('new soldier template seen: %s' % t)
    if S['stamina']:
        tweak_set(prop_list(STAMINA_SET))
    if S['god']:
        tweak_set(prop_list(GOD_SET))

def heal_one(p):
    if not alive(p):
        return
    s = soldier_of(p)
    if s is None:
        return
    h = health(s)
    if h is None or h >= float(GOD_HP) - 0.5:
        return
    try:
        s.setDamage(float(GOD_HP))
    except:
        log('setDamage on %s failed: %s' % (name_of(p), err_text()))
        return
    st = ps(p)
    st['healed'] = st['healed'] + 1
    if st['healed'] <= 5:
        log('%s: health %.1f -> set %g, reads %s' % (name_of(p), h, float(GOD_HP), health(s)))

# ------------------------------------------------------------------ jumps
def track(p, t):
    st = ps(p)
    js = st['js']
    if not alive(p):
        js['state'] = None
        return
    inv, v = in_vehicle(p)
    if inv:
        js['state'] = None
        return
    if now() < st.get('quiet', 0.0):
        js['state'] = None
        return
    s = soldier_of(p)
    q = pos(s)
    if q is None:
        return
    hp = health(s)
    last = js.get('q')
    lt = js.get('t')
    js['q'] = q
    js['t'] = t
    if js['state'] is None or last is None or lt is None or t - lt <= 0.001:
        js['state'] = 'ground'
        js['v'] = 0.0
        js['flat'] = 0
        js['fall'] = 0
        js['hp'] = hp
        js['qg'] = q
        js['tg'] = t
        return
    dt = t - lt
    if dist3(q, last) > float(TP_STEP):
        js['state'] = 'ground'
        js['v'] = 0.0
        js['fall'] = 0
        js['hp'] = hp
        js['qg'] = q
        js['tg'] = t
        return
    vy = (q[1] - last[1]) / dt
    acc = (vy - js['v']) / dt
    js['v'] = vy
    g = float(GRAVITY)
    if js['state'] == 'ground':
        start = 0
        kind = ''
        if vy > float(UP_SPEED):
            start = 1
            kind = 'jump'
        elif acc < -g * 0.5 and vy < -0.3:
            js['fall'] = js['fall'] + 1
            if js['fall'] >= 2:
                start = 1
                kind = 'fall'
        else:
            js['fall'] = 0
        if start:
            js['state'] = 'air'
            js['kind'] = kind
            if kind == 'fall' and js.get('qg') is not None:
                js['t0'] = js['tg']
                js['q0'] = js['qg']
            else:
                js['t0'] = (lt + t) / 2.0
                js['q0'] = last
            js['peak'] = max(last[1], q[1])
            js['v0'] = vy
            js['vmin'] = vy
            js['hp0'] = js.get('hp')
            js['hpmin'] = hp
            js['flat'] = 0
            js['contact'] = None
        elif js['fall'] == 0:
            js['qg'] = q
            js['tg'] = t
            js['hp'] = hp
        return
    # in the air
    if q[1] > js['peak']:
        js['peak'] = q[1]
    if vy < js['vmin']:
        js['vmin'] = vy
    if hp is not None and (js['hpmin'] is None or hp < js['hpmin']):
        js['hpmin'] = hp
    if acc > -g * 0.5:
        if js['flat'] == 0:
            js['contact'] = (q, t, last, lt)
        js['flat'] = js['flat'] + 1
    else:
        js['flat'] = 0
        js['contact'] = None
    if t - js['t0'] > float(AIR_MAX):
        js['state'] = 'ground'
        js['fall'] = 0
        js['qg'] = q
        js['tg'] = t
        js['hp'] = hp
        return
    if js['flat'] >= 2 and js['contact'] is not None:
        cq, ct, cl, clt = js['contact']
        js['state'] = 'ground'
        js['fall'] = 0
        js['qg'] = q
        js['tg'] = t
        js['hp'] = hp
        air = (clt + ct) / 2.0 - js['t0']
        if air < 0:
            air = 0.0
        landed(p, st, js, cq, air, (clt + ct) / 2.0)

def landed(p, st, js, ql, air, t_land=None):
    q0 = js['q0']
    kind = js['kind']
    gravity_seen = js['v0'] - js['vmin']
    if air < float(AIR_MIN) or gravity_seen < 2.0:
        return
    st['jumps'] = st['jumps'] + 1
    up = js['peak'] - q0[1]
    dh = ql[1] - q0[1]
    across = hdist(ql, q0)
    loss = ''
    if js.get('hp0') is not None and js.get('hpmin') is not None and js['hpmin'] < js['hp0'] - 0.5:
        loss = ', health -%.0f' % (js['hp0'] - js['hpmin'])
    rough = 'rough: air %.2f s, up %.2f m, %.2f m across, from %s to %s, peak %.2f, v0 %.1f m/s' % (air, up, across,
        pos_text(q0), pos_text(ql), js['peak'], js['v0'])
    rec = None
    try:
        rec = record_jump(p, st, js, kind, ql, t_land)
    except:
        log('%s: the recorder failed: %s' % (name_of(p), err_text()))
    num = ''
    take = ''
    if rec is not None:
        num = ' #%d' % rec['n']
        if rec['ok']:
            air = rec['air']
            up = rec['up']
            dh = rec['dh']
            across = rec['across']
            take = '; take-off %s' % move_text(rec)
    if dh >= 0:
        land = 'landed %.2f m higher' % dh
    else:
        land = 'landed %.2f m lower' % -dh
    if kind == 'jump':
        line = '%s: jump%s: %.2f s in the air, up %.2f m, %s, %.2f m across%s%s' % (name_of(p), num, air, up, land,
            across, loss, take)
    else:
        if take:
            take = '; no push-off, %s' % move_text(rec)
        line = '%s: fell%s: %.2f m in %.2f s, %.2f m across%s%s' % (name_of(p), num, -dh, air, across, loss, take)
    log('%s (%s)' % (line, rough))
    if rec is not None:
        log_record(p, rec)
    if st['meter']:
        tell(p, line)
    auto_check(p, st, q0, ql)

# ------------------------------------------------------------------ the jump recorder
def keep_frame(p, st, t):
    # every FRAME_EVERY: his position and facing; a frame the same as the last one (the game had not moved him
    # yet) is skipped unless 0.1 s passed (standing still)
    js = st['js']
    if not alive(p) or now() < st.get('quiet', 0.0):
        st['raw'] = []
        st['dup'] = None
        return
    inv, v = in_vehicle(p)
    if inv:
        st['raw'] = []
        st['dup'] = None
        return
    s = soldier_of(p)
    q = pos(s)
    if q is None:
        return
    r = rot(s)
    yaw = 0.0
    if r is not None:
        yaw = r[0]
    R = st['raw']
    f = (t, q[0], q[1], q[2], yaw)
    if R:
        last = R[-1]
        dt = t - last[0]
        if dt <= 0.0005:
            return
        d = dist3(q, (last[1], last[2], last[3]))
        if d > float(TP_STEP):
            R = []
            st['raw'] = R
        elif d < 0.0005 and dt < 0.1:
            # the same place: kept aside, so the last frame before he moves again is known
            st['dup'] = f
            return
        else:
            # he moves again after standing: the last frame he stood there first (so the take-off frame is exact);
            # not after one repeated frame while moving (a look between two game ticks)
            dup = st.get('dup')
            if dup is not None and dup[0] > last[0] and (dup[0] - last[0] >= 0.05 or (len(R) >= 2 and
                    dist3((R[-2][1], R[-2][2], R[-2][3]), (last[1], last[2], last[3])) < 0.0005)):
                R.append(dup)
    st['dup'] = None
    R.append(f)
    cut = t - float(KEEP)
    if js.get('state') == 'air' and js.get('t0') is not None:
        cut = js['t0'] - float(KEEP)
    i = 0
    while i < len(R) and R[i][0] < cut:
        i = i + 1
    if i:
        del R[:i]
    if len(R) > 2000:
        del R[:len(R) - 2000]

def idx_after(R, t):
    i = 0
    while i < len(R):
        if R[i][0] >= t - 1e-6:
            return i
        i = i + 1
    return None

def idx_before(R, t):
    i = len(R) - 1
    while i >= 0:
        if R[i][0] <= t + 1e-6:
            return i
        i = i - 1
    return None

def hspeed(R, i, j):
    # across the ground from frame i to frame j: (m/s, heading or None)
    dt = R[j][0] - R[i][0]
    if dt <= 0:
        return 0.0, None
    dx = R[j][1] - R[i][1]
    dz = R[j][3] - R[i][3]
    v = (dx * dx + dz * dz) ** 0.5 / dt
    if v < 0.3:
        return v, None
    return v, heading_of(dx, dz)

def vy_of(R, i):
    # up speed from frame i to i + 1
    if i + 1 >= len(R):
        return 0.0
    dt = R[i + 1][0] - R[i][0]
    if dt <= 0:
        return 0.0
    return (R[i + 1][2] - R[i][2]) / dt

def speed_name(v):
    if v < float(STAND_MAX):
        return 'standing'
    if v < float(RUN_MIN):
        return 'slow'
    if v < float(SPRINT_MIN):
        return 'run'
    if v < float(SPRINT_FULL):
        return 'sprint, not full'
    return 'sprint'

def way_name(off):
    # where he moved against where he looked -> (words, keys)
    if off is None:
        return '', ''
    a = abs(off)
    side = 'right'
    key = 'D'
    if off < 0:
        side = 'left'
        key = 'A'
    if a <= 20:
        return 'forward', 'W'
    if a <= 70:
        return 'forward-' + side, 'W+' + key
    if a <= 110:
        return side, key
    if a <= 160:
        return 'back-' + side, 'S+' + key
    return 'back', 'S'

def move_text(rec):
    v = rec['v_take']
    n = speed_name(v)
    if n == 'standing':
        return 'standing'
    w, k = way_name(rec['off'])
    if w:
        return '%s %.1f m/s %s (%s)' % (n, v, w, k)
    return '%s %.1f m/s' % (n, v)

def record_jump(p, st, js, kind, ql, t_land):
    R = list(st['raw'])
    dup = st.get('dup')
    if dup is not None and R and dup[0] > R[-1][0]:
        R.append(dup)
    t0 = js['t0']
    rec = {'n': 0, 'kind': kind, 'mark': None, 'ok': 0, 'point': None, 'ping': None, 'since': None}
    try:
        rec['ping'] = int(p.getPing())
    except:
        pass
    J = st['jl']
    n = 1
    if J:
        n = J[-1]['n'] + 1
    rec['n'] = n
    J.append(rec)
    if len(J) > int(JUMPS_MAX):
        del J[:len(J) - int(JUMPS_MAX)]
    if t_land is None:
        t_land = now()
    rec['frames'] = []
    if len(R) < 4:
        st['last_land'] = t_land
        return rec
    # the take-off frame: the last one on the ground before the push-off (a jump) / before he dropped (a fall)
    k0 = None
    k = 0
    while k < len(R) - 1:
        if R[k][0] < t0 - 0.3:
            k = k + 1
            continue
        if R[k][0] > t0 + 0.2:
            break
        if kind == 'jump' and vy_of(R, k) > float(UP_SPEED):
            k0 = k
            # already rising a little before (the frame came just after the push-off): the frame before
            while k0 > 0 and vy_of(R, k0 - 1) > 0.5 and R[k0][0] - R[k0 - 1][0] < 0.1 and R[k0][0] > t0 - 0.4:
                k0 = k0 - 1
            break
        k = k + 1
    if kind != 'jump':
        k = idx_after(R, t0)
        if k is not None:
            while k + 1 < len(R) and R[k + 1][0] < t0 + 0.2 and R[k + 1][2] - R[k][2] > -0.003:
                k = k + 1
            # the detection's last ground look may already be the first frame off the edge
            while k > 0 and R[k - 1][2] - R[k][2] > 0.003 and R[k][0] - R[k - 1][0] < 0.1 and R[k][0] > t0 - 0.2:
                k = k - 1
            k0 = k
    if k0 is None:
        k0 = idx_after(R, t0)
    if k0 is None or k0 >= len(R) - 2:
        st['last_land'] = t_land
        return rec
    # the landing frame: the fall stops at once (the frame in came down fast, the frame out does not)
    kl = None
    k = k0 + 2
    while k < len(R) - 1:
        if R[k][0] - R[k0][0] >= 0.1:
            v1 = vy_of(R, k - 1)
            v2 = vy_of(R, k)
            v3 = 0.0
            if k + 2 < len(R):
                v3 = vy_of(R, k + 1)
            if v1 < -0.2 and v2 - v1 > 0.3 and v2 > -0.5 and v3 > -0.5:
                kl = k
                break
        k = k + 1
    if kl is None:
        kl = idx_after(R, t_land)
        if kl is None:
            kl = len(R) - 1
        if kl <= k0:
            st['last_land'] = t_land
            return rec
    kp = k0
    k = k0
    while k <= kl:
        if R[k][2] > R[kp][2]:
            kp = k
        k = k + 1
    tk = R[k0][0]
    rec['ok'] = 1
    rec['t_take'] = tk
    rec['take'] = (R[k0][1], R[k0][2], R[k0][3])
    rec['land'] = (R[kl][1], R[kl][2], R[kl][3])
    rec['yaw_take'] = R[k0][4]
    rec['air'] = R[kl][0] - tk
    rec['up'] = R[kp][2] - R[k0][2]
    rec['t_top'] = R[kp][0] - tk
    rec['dh'] = R[kl][2] - R[k0][2]
    rec['across'] = hdist(rec['take'], rec['land'])
    rec['v0'] = vy_of(R, k0)
    # on the ground: the last frame before the take-off (the speed the jump carries on)
    kb = idx_before(R, tk - 0.03)
    rec['v_take'] = 0.0
    rec['head_take'] = None
    if kb is not None and kb < k0:
        rec['v_take'], rec['head_take'] = hspeed(R, kb, k0)
    rec['off'] = None
    if rec['head_take'] is not None and rec['v_take'] >= float(STAND_MAX):
        rec['off'] = norm180(rec['head_take'] - rec['yaw_take'])
    # in the air: the first 0.2 s and the last 0.2 s
    rec['v_air'] = None
    rec['head_air'] = None
    rec['v_late'] = None
    rec['head_late'] = None
    ka = k0 + 1
    kb2 = idx_after(R, R[ka][0] + 0.2)
    if kb2 is None or kb2 > kl:
        kb2 = kl
    if kb2 > ka:
        rec['v_air'], rec['head_air'] = hspeed(R, ka, kb2)
    kc = idx_after(R, R[kl][0] - 0.2)
    if kc is not None and kc < kl and kc >= ka:
        rec['v_late'], rec['head_late'] = hspeed(R, kc, kl)
    # facing: the turn in the last 0.5 s before the take-off and in the air
    rec['turn_before'] = None
    kt = idx_before(R, tk - 0.5)
    if kt is not None and kt < k0:
        rec['turn_before'] = norm180(R[k0][4] - R[kt][4])
    rec['turn_air'] = norm180(R[kl][4] - R[k0][4])
    # the run-up: back in 0.1 s steps while faster than RUNUP_MIN; at sprint speed while faster than SPRINT_MIN
    j = k0
    dist = 0.0
    vmax = rec['v_take']
    more = 0
    sprint_j = k0
    sprinting = 1
    prev = st.get('last_land')
    while 1:
        i = idx_before(R, R[j][0] - 0.1)
        if i is None or i >= j:
            more = 1
            break
        if prev is not None and R[i][0] < prev - 0.01:
            # the run-up starts at the last landing (a hop)
            if R[j][0] > prev + 0.01:
                i2 = idx_after(R, prev)
                if i2 is not None and i2 < j:
                    dist = dist + hdist((R[i2][1], 0, R[i2][3]), (R[j][1], 0, R[j][3]))
                    j = i2
            break
        v, h = hspeed(R, i, j)
        if v < float(RUNUP_MIN):
            break
        if sprinting and v >= float(SPRINT_MIN):
            sprint_j = i
        else:
            sprinting = 0
        dist = dist + hdist((R[i][1], 0, R[i][3]), (R[j][1], 0, R[j][3]))
        if v > vmax:
            vmax = v
        j = i
    rec['runup_t'] = tk - R[j][0]
    rec['runup_d'] = dist
    rec['runup_more'] = more and rec['runup_t'] > 0.05
    rec['vmax'] = vmax
    rec['sprint_t'] = tk - R[sprint_j][0]
    # how often the frames came (about 0.033 s = every game tick)
    D = []
    k = idx_after(R, tk - 1.0) or 0
    while k < kl and k + 1 < len(R):
        D.append(R[k + 1][0] - R[k][0])
        k = k + 1
    D.sort()
    rec['fdt'] = None
    if D:
        rec['fdt'] = D[len(D) // 2]
    if st.get('last_land') is not None and tk >= st['last_land'] - 0.05:
        rec['since'] = max(0.0, tk - st['last_land'])
    st['last_land'] = R[kl][0]
    if st.get('active'):
        pt = points_of(name_of(p)).get(st['active'])
        if pt is not None and hdist(pt, rec['take']) <= float(AUTO_RANGE):
            rec['point'] = st['active']
    # frames for the log
    if FRAMES_LOG:
        a = idx_after(R, tk - float(RUNUP_LOG))
        if a is None:
            a = 0
        b = kl + 3
        if b > len(R) - 1:
            b = len(R) - 1
        k = a
        while k <= b:
            rec['frames'].append(R[k])
            k = k + 1
    return rec

def opt(v, fmt, none='-'):
    if v is None:
        return none
    return fmt % v

def log_record(p, rec):
    n = name_of(p)
    if not rec['ok']:
        log('JUMP #%d %s %s: too few frames - only the rough numbers above' % (rec['n'], n, rec['kind']))
        return
    w, k = way_name(rec['off'])
    log('JUMP #%d %s %s: take-off t %.3f at %s facing %.1f | %s %.2f m/s heading %s (off %s%s) | run-up %s%.2f s '
        '%.1f m, max %.2f m/s, at sprint speed %.2f s | turned %s deg in the last 0.5 s | push-off %.2f m/s | air '
        '%.3f s, up %.3f m (top at %.3f s) | in the air %s -> %s m/s, heading %s -> %s, turned %+.1f deg | landed '
        '%s: %.2f m across, %+.2f m | since the last landing %s | ping %s | point %s | frames every %s s' % (rec['n'], n,
        rec['kind'],
        rec['t_take'], pos3(rec['take']), rec['yaw_take'], speed_name(rec['v_take']), rec['v_take'],
        opt(rec['head_take'], '%.1f'), opt(rec['off'], '%+.1f'), (w and ', %s %s' % (w, k)) or '',
        (rec['runup_more'] and 'at least ') or '', rec['runup_t'], rec['runup_d'], rec['vmax'], rec['sprint_t'],
        opt(rec['turn_before'], '%+.1f'), rec['v0'], rec['air'], rec['up'], rec['t_top'], opt(rec['v_air'], '%.2f'),
        opt(rec['v_late'], '%.2f'), opt(rec['head_air'], '%.1f'), opt(rec['head_late'], '%.1f'), rec['turn_air'],
        pos3(rec['land']), rec['across'], rec['dh'], opt(rec['since'], '%.2f s'), opt(rec['ping'], '%d'),
        rec['point'] or '-', opt(rec.get('fdt'), '%.3f')))
    F = rec.get('frames') or []
    t = rec['t_take']
    k = 0
    while k < len(F):
        part = []
        for f in F[k:k + 6]:
            part.append('%+.3f %.3f/%.3f/%.3f %.1f' % (f[0] - t, f[1], f[2], f[3], f[4]))
        log('  frames #%d: %s' % (rec['n'], '; '.join(part)))
        k = k + 6
    rec['frames'] = []

def pos3(q):
    return '%.3f/%.3f/%.3f' % (q[0], q[1], q[2])

def auto_check(p, st, q0, ql):
    if not st['auto'] or st['active'] is None:
        return
    pts = points_of(name_of(p))
    pt = pts.get(st['active'])
    if pt is None:
        return
    if hdist(q0, pt) > float(AUTO_RANGE):
        return
    if q0[1] < pt[1] - float(AUTO_FROM):
        return
    if ql[1] >= pt[1] - st['drop']:
        return
    log('%s: missed (landed %.1f m below "%s") - back in %.1f s' % (name_of(p), pt[1] - ql[1], st['active'],
        float(AUTO_DELAY)))
    later(float(AUTO_DELAY), auto_back, (p, st['active']))

def auto_back(data):
    p, k = data
    if not alive(p):
        return
    inv, v = in_vehicle(p)
    if inv:
        return
    pt = points_of(name_of(p)).get(k)
    if pt is None:
        return
    if go_to(p, pt, k):
        tell(p, 'missed - back to "%s"' % k)

def go_to(p, pt, label=''):
    # 0.1.0 put the soldier straight there; the game then drags him along the line and stops him at the first wall
    # (the test 15.11: the auto-return stopped half-way at a house and he fell). So, as fldm's sky route:
    # straight up SKY m over the higher of the two places, across, down - MOVE_STEP s apart; checked after the last.
    s = soldier_of(p)
    if s is None:
        return 0
    q = pos(s)
    x, y, z, yaw = pt
    target = (x, y + float(TP_UP), z)
    st = ps(p)
    st['jj'] = None
    st['quiet'] = now() + 3.0 * float(MOVE_STEP) + float(ARRIVE_CHECK) + 0.5
    st['js']['state'] = None
    st['moves'] = st.get('moves', 0) + 1
    n = st['moves']
    if q is None or (hdist(q, target) < float(DIRECT_NEAR) and abs(q[1] - target[1]) < 1.0):
        steps = [target]
    else:
        sky = max(q[1], target[1]) + float(SKY)
        steps = [(q[0], sky, q[2]), (x, sky, z), target]
    log('%s: move #%d to "%s" %s from %s in %d step(s)' % (name_of(p), n, label, pos_text(target), pos_text(q),
        len(steps)))
    k = 0
    for xyz in steps:
        if k == 0:
            move_step((p, xyz, yaw, n, k == len(steps) - 1))
        else:
            later(k * float(MOVE_STEP), move_step, (p, xyz, yaw, n, k == len(steps) - 1))
        k = k + 1
    later((len(steps) - 1) * float(MOVE_STEP) + float(ARRIVE_CHECK), arrive_check, (p, target, yaw, n, label, 0))
    return 1

def move_step(data):
    p, xyz, yaw, n, last = data
    st = ps(p)
    if st.get('moves') != n or not alive(p):
        return
    inv, v = in_vehicle(p)
    if inv:
        return
    s = soldier_of(p)
    try:
        s.setPosition(xyz)
    except:
        log('setPosition on %s failed: %s' % (name_of(p), err_text()))
        return
    if last:
        try:
            s.setRotation((yaw, 0.0, 0.0))
        except:
            pass
    st['js']['state'] = None

def arrive_check(data):
    p, target, yaw, n, label, tries = data
    st = ps(p)
    if st.get('moves') != n or not alive(p):
        return
    q = pos(soldier_of(p))
    if q is None:
        return
    d = dist3(q, target)
    if d <= float(TP_OK):
        log('%s: move #%d to "%s" took (%.1f m off)' % (name_of(p), n, label, d))
        return
    log('%s: move #%d to "%s" did not take: at %s, %.1f m off (try %d)' % (name_of(p), n, label, pos_text(q), d,
        tries + 1))
    if tries == 0:
        # once more, straight from where he is now
        st['quiet'] = now() + float(ARRIVE_CHECK) + 0.5
        move_step((p, target, yaw, n, 1))
        later(float(ARRIVE_CHECK), arrive_check, (p, target, yaw, n, label, 1))
    else:
        tell(p, 'could not get to "%s" (stopped %.0f m away)' % (label, d))

# ------------------------------------------------------------------ !jj: a big jump drawn frame by frame
def cmd_jj(p, arg):
    st = ps(p)
    if not alive(p):
        tell(p, 'not while dead')
        return
    q, yaw = where(p)
    if q is None:
        return
    d = float(JJ_DIST)
    note = ''
    if arg:
        try:
            d = float(str(arg).replace(',', '.'))
        except:
            tell(p, "'!jj' or '!jj <metres>' (%.0f to %.0f)" % (float(JJ_MIN), float(JJ_MAX)))
            return
    if d > float(JJ_MAX):
        d = float(JJ_MAX)
        note = ' (%.0f at most)' % d
    if d < float(JJ_MIN):
        d = float(JJ_MIN)
        note = ' (%.0f at least)' % d
    g = float(JJ_GRAVITY)
    vy0 = (2.0 * g * d) ** 0.5
    total = 2.0 * vy0 / g
    a = yaw * PI / 180.0
    st['moves'] = st.get('moves', 0) + 1
    st['jj'] = {'n': st['moves'], 't0': now(), 'q0': q, 'yaw': yaw, 'd': d, 'vy0': vy0, 'T': total,
                'dx': sin_(a), 'dz': cos_(a), 'last': None, 'lastvy': vy0, 'steps': 0, 'phase': 'fly',
                'off_h': [], 'off_y': [], 'still': 0, 'lq': None, 'tland': None}
    st['quiet'] = now() + total + 1.0
    st['js']['state'] = None
    st['raw'] = []
    st['dup'] = None
    warn = ''
    if not S['god']:
        warn = ' - god is off: the fall can kill'
    log('JJ %s: %.1f m forward and up from %s facing %.1f, %.2f s, up speed %.1f m/s%s' % (name_of(p), d,
        pos_text(q), yaw, total, vy0, note))
    tell(p, 'jump %.0f m forward, %.0f m up (%.1f s)%s%s' % (d, d, total, note, warn))

def jj_end(p, st, J, why):
    q = pos(soldier_of(p))
    n = len(J['off_y'])
    oy = J['off_y'][:]
    oy.sort()
    oh = J['off_h'][:]
    oh.sort()
    stats = ''
    if n:
        stats = ', off the drawn point a frame later: height median %+.2f (min %+.2f, max %+.2f), across median %.2f ' \
                'max %.2f m' % (oy[n // 2], oy[0], oy[-1], oh[n // 2], oh[-1])
    if q is not None:
        q0 = J['q0']
        log('JJ %s: %s at %s: %.1f m from the start, %+.1f m, %d steps%s' % (name_of(p), why, pos_text(q),
            hdist(q, q0), q[1] - q0[1], J['steps'], stats))
        if why == 'landed':
            tell(p, 'landed %.1f m from the start, %+.1f m' % (hdist(q, q0), q[1] - q0[1]))
    else:
        log('JJ %s: %s%s' % (name_of(p), why, stats))
    st['jj'] = None
    st['quiet'] = now() + 0.3
    st['js']['state'] = None

def jj_step(p, st, t):
    J = st['jj']
    if J['n'] != st.get('moves'):
        st['jj'] = None
        return
    if not alive(p):
        jj_end(p, st, J, 'ended - dead')
        return
    inv, v = in_vehicle(p)
    if inv:
        jj_end(p, st, J, 'ended - in a vehicle')
        return
    s = soldier_of(p)
    q = pos(s)
    if q is None:
        return
    if J['phase'] == 'fly':
        L = J['last']
        if L is not None:
            dh = hdist(q, L)
            dy = q[1] - L[1]
            J['off_h'].append(dh)
            J['off_y'].append(dy)
            if dh > float(JJ_HIT) or (J['lastvy'] < 0 and dy > float(JJ_HIT)):
                J['phase'] = 'land'
                J['tland'] = now()
                st['quiet'] = now() + 0.5
                log('JJ %s: stopped by something %.2f s into the flight at %s (%.1f m across, %+.1f m up off the '
                    'drawn point)' % (name_of(p), t - J['t0'], pos_text(q), dh, dy))
                tell(p, 'stopped by something at %.1f m from the start' % hdist(q, J['q0']))
                return
        tt = t - J['t0']
        last = 0
        if tt >= J['T']:
            tt = J['T']
            last = 1
        f = tt / J['T']
        q0 = J['q0']
        g = float(JJ_GRAVITY)
        xyz = (q0[0] + J['dx'] * J['d'] * f, q0[1] + J['vy0'] * tt - 0.5 * g * tt * tt, q0[2] + J['dz'] * J['d'] * f)
        try:
            s.setPosition(xyz)
        except:
            log('JJ %s: setPosition failed: %s' % (name_of(p), err_text()))
            st['jj'] = None
            return
        J['last'] = xyz
        J['lastvy'] = J['vy0'] - g * tt
        J['steps'] = J['steps'] + 1
        st['quiet'] = max(st.get('quiet', 0.0), now() + 0.5)
        if last:
            J['phase'] = 'land'
            J['tland'] = now()
        return
    # after the flight: no meter and no auto-return until he stands (5 frames in a row without 3 cm up or down)
    st['quiet'] = now() + 0.5
    lq = J['lq']
    J['lq'] = q
    if lq is not None and abs(q[1] - lq[1]) < 0.03:
        J['still'] = J['still'] + 1
    else:
        J['still'] = 0
    if J['still'] >= 5:
        jj_end(p, st, J, 'landed')
    elif now() - J['tland'] > float(JJ_SETTLE):
        jj_end(p, st, J, 'not standing after %.0f s' % float(JJ_SETTLE))

# ------------------------------------------------------------------ the tick
def tick(data=None):
    if not S['on']:
        return
    try:
        tick_now()
    except:
        log('tick: ' + err_text())

def tick_now():
    t = now()
    try:
        L = bf2.playerManager.getPlayers()
    except:
        return
    heal = 0
    if t - S['last_heal'] >= float(HEAL_EVERY) - 0.001:
        heal = 1
        S['last_heal'] = t
    for p in L:
        bot = is_bot(p)
        if not bot:
            st = ps(p)
            if st.get('jj') is not None:
                try:
                    jj_step(p, st, t)
                except:
                    log('jj %s: %s' % (name_of(p), err_text()))
                    st['jj'] = None
            try:
                keep_frame(p, st, t)
            except:
                log('frame %s: %s' % (name_of(p), err_text()))
            if t - st['tt'] >= float(SAMPLE) - 0.005:
                st['tt'] = t
                try:
                    track(p, t)
                except:
                    log('track %s: %s' % (name_of(p), err_text()))
        if heal and S['god'] and (not bot or GOD_BOTS):
            heal_one(p)

# ------------------------------------------------------------------ commands
def where(p):
    inv, v = in_vehicle(p)
    if inv:
        tell(p, 'get out of the vehicle first')
        return None, None
    s = soldier_of(p)
    q = pos(s)
    if q is None:
        tell(p, 'no position')
        return None, None
    r = rot(s)
    yaw = 0.0
    if r is not None:
        yaw = r[0]
    return q, yaw

def cmd_save(p, arg):
    q, yaw = where(p)
    if q is None:
        return
    k = arg or '1'
    n = name_of(p)
    points_of(n)[k] = (q[0], q[1], q[2], yaw)
    ps(p)['active'] = k
    save_points()
    log('%s saved "%s" at %s, heading %.0f' % (n, k, pos_text(q), yaw))
    tell(p, 'saved "%s" at %s (active)' % (k, pos_text(q)))

def cmd_go(p, arg):
    st = ps(p)
    k = arg or st['active']
    pts = points_of(name_of(p))
    if not k or k not in pts:
        tell(p, "no point %s - '!j save [name]' first" % (k and '"%s"' % k or ''))
        return
    inv, v = in_vehicle(p)
    if inv:
        tell(p, 'get out of the vehicle first')
        return
    if go_to(p, pts[k], k):
        st['active'] = k
        log('%s went to "%s" %s' % (name_of(p), k, pos_text(pts[k])))
        tell(p, 'at "%s" (active)' % k)

def cmd_list(p):
    pts = points_of(name_of(p))
    keys = list(pts.keys())
    keys.sort()
    if not keys:
        tell(p, "no points - '!j save [name]'")
        return
    parts = []
    for k in keys:
        x, y, z, yaw = pts[k]
        mark = ''
        if k == ps(p)['active']:
            mark = ' (active)'
        parts.append('%s %.0f/%.1f/%.0f%s' % (k, x, y, z, mark))
    tell(p, 'points: ' + '; '.join(parts))

def cmd_del(p, arg):
    pts = points_of(name_of(p))
    if not arg or arg not in pts:
        tell(p, "'!j del <name>' - one of your points")
        return
    del pts[arg]
    if ps(p)['active'] == arg:
        ps(p)['active'] = None
    save_points()
    tell(p, '"%s" forgotten' % arg)

def cmd_auto(p, arg):
    st = ps(p)
    a = arg.lower()
    if a == 'on':
        st['auto'] = 1
    elif a == 'off':
        st['auto'] = 0
    elif a:
        try:
            st['drop'] = float(a)
            st['auto'] = 1
        except:
            tell(p, "'!j auto on|off|<metres>'")
            return
    tell(p, 'auto-return %s (more than %.1f m below the active point "%s")' % ((st['auto'] and 'ON') or 'off',
        st['drop'], st['active'] or 'none yet'))

def cmd_meter(p, arg):
    st = ps(p)
    a = arg.lower()
    if a == 'on':
        st['meter'] = 1
    elif a == 'off':
        st['meter'] = 0
    tell(p, 'jump meter %s' % ((st['meter'] and 'ON') or 'off'))

def cmd_mark(p, which):
    q, yaw = where(p)
    if q is None:
        return
    st = ps(p)
    if which == 'a':
        st['a'] = q
        tell(p, 'A at %s' % pos_text(q))
        return
    a = st['a']
    if a is None:
        tell(p, "'!j a' first")
        return
    d = dist3(a, q)
    h = hdist(a, q)
    dh = q[1] - a[1]
    line = 'A -> B: %.2f m straight, %.2f m across, B %.2f m %s' % (d, h, abs(dh), (dh >= 0 and 'higher') or 'lower')
    log('%s: %s (A %s, B %s)' % (name_of(p), line, pos_text(a), pos_text(q)))
    tell(p, line)

def cmd_vehicle(p):
    q, yaw = where(p)
    if q is None:
        return
    a = yaw * PI / 180.0
    x = q[0] + sin_(a) * float(VEH_AHEAD)
    z = q[2] + cos_(a) * float(VEH_AHEAD)
    y = q[1] + float(VEH_UP)
    xyz = '%.2f/%.2f/%.2f' % (x, y, z)
    st = ps(p)
    old = st['veh']
    if old:
        b = console('Object.active %s' % old)
        if not (b and bad_answer(b)):
            console('Object.absolutePosition %s' % xyz)
            console('Object.rotation %.1f/0/0' % yaw)
            after = console('Object.absolutePosition')
            log('%s: Vodnik %s moved to %s (reads "%s")' % (name_of(p), old, xyz, after))
            tell(p, 'your Vodnik moved here (%s)' % old)
            return
        log('%s: Vodnik %s not found ("%s") - a new one' % (name_of(p), old, b))
    a1 = console('Object.create %s' % VEHICLE)
    oid = ''
    for w in a1.replace('(', ' ').replace(')', ' ').replace(':', ' ').split():
        if w.lower().startswith('id') and w[2:].isdigit():
            oid = w
    console('Object.absolutePosition %s' % xyz)
    console('Object.rotation %.1f/0/0' % yaw)
    console('Object.layer 1')
    st['veh'] = oid or None
    log('%s: Vodnik made: "%s" (id %s) at %s, heading %.0f; you at %s' % (name_of(p), a1, oid or '?', xyz, yaw,
        pos_text(q)))
    if a1 and bad_answer(a1):
        tell(p, 'the console said "%s"' % a1)
    else:
        tell(p, 'a Vodnik %.0f m in front of you (%s)' % (float(VEH_AHEAD), oid or 'no id'))

# ------------------------------------------------------------------ marks and comparing
def find_jump(st, arg):
    J = st['jl']
    if not J:
        return None
    if arg:
        try:
            n = int(str(arg).lstrip('#'))
        except:
            return None
        for r in J:
            if r['n'] == n:
                return r
        return None
    return J[-1]

def mark_word(m):
    if m == '+':
        return 'good'
    if m == '-':
        return 'missed'
    return 'not marked'

def cmd_mark_jump(p, sign, arg):
    st = ps(p)
    r = find_jump(st, arg)
    if r is None:
        if arg:
            tell(p, 'no jump #%s - \'!j jumps\' lists yours' % arg)
        else:
            tell(p, 'no jump recorded yet')
        return
    r['mark'] = sign
    good = len([x for x in st['jl'] if x['mark'] == '+'])
    bad = len([x for x in st['jl'] if x['mark'] == '-'])
    log('MARK #%d %s %s' % (r['n'], name_of(p), sign))
    tell(p, '#%d marked %s (%s) - %d good, %d missed so far' % (r['n'], mark_word(sign), short_text(r), good, bad))

def short_text(r):
    if not r['ok']:
        return r['kind']
    return '%s, %.2f m across, %+.2f m' % (r['kind'], r['across'], r['dh'])

def cmd_jumps(p):
    J = ps(p)['jl']
    if not J:
        tell(p, 'no jump recorded yet')
        return
    parts = []
    for r in J[-8:]:
        m = r['mark'] or ' '
        if r['ok']:
            parts.append('#%d%s %s %.1f m %.1f m/s' % (r['n'], m.strip() and ' ' + m or '', r['kind'], r['across'],
                r['v_take']))
        else:
            parts.append('#%d%s %s' % (r['n'], m.strip() and ' ' + m or '', r['kind']))
    tell(p, 'jumps: ' + '; '.join(parts))

def cmd_info(p, arg):
    r = find_jump(ps(p), arg)
    if r is None:
        tell(p, 'no such jump')
        return
    if not r['ok']:
        tell(p, '#%d %s (%s): too few frames recorded' % (r['n'], r['kind'], mark_word(r['mark'])))
        return
    run = '%s%.1f s / %.1f m' % ((r['runup_more'] and 'at least ') or '', r['runup_t'], r['runup_d'])
    tell(p, '#%d %s (%s): take-off %s facing %.0f; %s; at sprint speed %.1f s, run-up %s; turned %s deg in the '
         'last 0.5 s; push-off %.1f m/s' % (r['n'], r['kind'], mark_word(r['mark']), pos_text(r['take']),
         r['yaw_take'], move_text(r), r['sprint_t'], run, opt(r['turn_before'], '%+.0f'), r['v0']))
    tell(p, '#%d: %.2f s in the air, up %.2f m (top at %.2f s); in the air %s -> %s m/s, turned %+.0f deg; landed '
         '%.2f m across, %+.2f m; %sping %s' % (r['n'], r['air'], r['up'], r['t_top'], opt(r['v_air'], '%.1f'),
         opt(r['v_late'], '%.1f'), r['turn_air'], r['across'], r['dh'],
         (r['since'] is not None and r['since'] < 3.0 and '%.2f s after the last landing; ' % r['since']) or '',
         opt(r['ping'], '%d')))

def axis_of(g):
    if g['head_take'] is not None and g['v_take'] >= float(STAND_MAX):
        return g['head_take']
    return g['yaw_take']

def along_side(q, origin, axis):
    a = axis * PI / 180.0
    dx = q[0] - origin[0]
    dz = q[2] - origin[2]
    return dx * sin_(a) + dz * cos_(a), dx * cos_(a) - dz * sin_(a)

def lr(v, word_pos='right', word_neg='left'):
    if v >= 0:
        return word_pos
    return word_neg

def compare(b, g):
    # b against g (g is the reference): (what differs, what is the same, the result)
    diff = []
    same = []
    along, side = along_side(b['take'], g['take'], axis_of(g))
    dy = b['take'][1] - g['take'][1]
    parts = []
    if abs(along) >= 0.10:
        parts.append('%.2f m %s' % (abs(along), lr(along, 'later', 'earlier')))
    if abs(side) >= 0.10:
        parts.append('%.2f m more %s' % (abs(side), lr(side)))
    if abs(dy) >= 0.10:
        parts.append('%.2f m %s' % (abs(dy), lr(dy, 'higher', 'lower')))
    if parts:
        diff.append('take-off ' + ', '.join(parts))
    else:
        same.append('take-off point')
    dv = b['v_take'] - g['v_take']
    if abs(dv) >= 0.2:
        diff.append('%.1f m/s %s (%.1f / %.1f)' % (abs(dv), lr(dv, 'faster', 'slower'), b['v_take'], g['v_take']))
    else:
        same.append('speed %.1f m/s' % g['v_take'])
    wb, kb = way_name(b['off'])
    wg, kg = way_name(g['off'])
    if speed_name(b['v_take']) != speed_name(g['v_take']):
        diff.append('%s / %s' % (speed_name(b['v_take']), speed_name(g['v_take'])))
    if wb != wg:
        diff.append('moved %s / %s' % (wb or '-', wg or '-'))
    elif wg:
        same.append('moved %s (%s)' % (wg, kg))
    if b['head_take'] is not None and g['head_take'] is not None:
        d = norm180(b['head_take'] - g['head_take'])
        if abs(d) >= 2.0:
            diff.append('ran %.0f deg more to the %s' % (abs(d), lr(d)))
        else:
            same.append('direction')
    d = norm180(b['yaw_take'] - g['yaw_take'])
    if abs(d) >= 2.0:
        diff.append('looked %.0f deg more to the %s' % (abs(d), lr(d)))
    if b['turn_before'] is not None and g['turn_before'] is not None:
        if abs(b['turn_before'] - g['turn_before']) >= 3.0:
            diff.append('turned %+.0f deg in the last 0.5 s (%+.0f)' % (b['turn_before'], g['turn_before']))
        else:
            same.append('turning')
    if abs(b['runup_t'] - g['runup_t']) >= 0.2:
        diff.append('run-up %s%.1f s / %s%.1f s' % ((b['runup_more'] and '>') or '', b['runup_t'],
            (g['runup_more'] and '>') or '', g['runup_t']))
    if abs(b['sprint_t'] - g['sprint_t']) >= 0.2:
        diff.append('at sprint speed %.1f s / %.1f s' % (b['sprint_t'], g['sprint_t']))
    if b['kind'] != g['kind']:
        if b['kind'] == 'fall':
            diff.append('no push-off (ran off?) / a jump')
        else:
            diff.append('a jump / no push-off')
    elif b['kind'] == 'jump':
        if abs(b['v0'] - g['v0']) >= 0.3:
            diff.append('push-off %.1f / %.1f m/s' % (b['v0'], g['v0']))
        else:
            same.append('push-off %.1f m/s' % g['v0'])
        if abs(b['up'] - g['up']) >= 0.10:
            diff.append('up %.2f / %.2f m' % (b['up'], g['up']))
    if b['v_air'] is not None and g['v_air'] is not None and b['v_late'] is not None and g['v_late'] is not None:
        cb = b['v_late'] - b['v_air']
        cg = g['v_late'] - g['v_air']
        if abs(cb - cg) >= 0.3:
            diff.append('in the air %+.1f / %+.1f m/s' % (cb, cg))
    if abs(b['turn_air'] - g['turn_air']) >= 5.0:
        diff.append('turned %+.0f / %+.0f deg in the air' % (b['turn_air'], g['turn_air']))
    sb = b['since']
    sg = g['since']
    if (sb is not None and sb < 1.5) or (sg is not None and sg < 1.5):
        diff.append('after the last landing %s / %s' % (opt(sb, '%.2f s'), opt(sg, '%.2f s')))
    if b['ping'] is not None and g['ping'] is not None:
        if abs(b['ping'] - g['ping']) >= 20:
            diff.append('ping %d / %d' % (b['ping'], g['ping']))
        else:
            same.append('ping %d' % g['ping'])
    res = 'result %.2f / %.2f m across, %+.2f / %+.2f m' % (b['across'], g['across'], b['dh'], g['dh'])
    return diff, same, res

def cmd_cmp(p, args):
    st = ps(p)
    J = [r for r in st['jl'] if r['ok']]
    if args and args[0].lower() == 'all':
        cmp_all(p, st, J)
        return
    g = None
    b = None
    if len(args) >= 2:
        g = find_jump(st, args[0])
        b = find_jump(st, args[1])
        if g is None or b is None or not g['ok'] or not b['ok']:
            tell(p, "no such jumps (or too few frames) - '!j jumps' lists yours")
            return
    else:
        for r in J:
            if r['mark'] == '+':
                g = r
        if g is None:
            tell(p, "mark a good jump with '!j +' first")
            return
        for r in J:
            if r['mark'] == '-' and hdist(r['take'], g['take']) <= float(CMP_NEAR):
                b = r
        if b is None:
            tell(p, "no missed jump ('!j -') that took off within %.0f m of #%d" % (float(CMP_NEAR), g['n']))
            return
    diff, same, res = compare(b, g)
    head = '#%d (%s) against #%d (%s)' % (b['n'], mark_word(b['mark']), g['n'], mark_word(g['mark']))
    d = hdist(b['take'], g['take'])
    if d > float(CMP_NEAR):
        head = head + ' - %.0f m apart, not the same jump?' % d
    tell(p, '%s: %s' % (head, '; '.join(diff) or 'no difference the server can see'))
    tell(p, 'the same: %s. %s' % (', '.join(same) or '-', res))
    log('CMP #%d / #%d done' % (b['n'], g['n']))

def mean_sd(L):
    if not L:
        return None, None
    m = 0.0
    for x in L:
        m = m + x
    m = m / len(L)
    v = 0.0
    for x in L:
        v = v + (x - m) * (x - m)
    return m, (v / len(L)) ** 0.5

def cmp_all(p, st, J):
    g0 = None
    for r in J:
        if r['mark'] == '+':
            g0 = r
    if g0 is None:
        tell(p, "mark good jumps with '!j +' first")
        return
    G = [r for r in J if r['mark'] == '+' and hdist(r['take'], g0['take']) <= float(CMP_NEAR)]
    B = [r for r in J if r['mark'] == '-' and hdist(r['take'], g0['take']) <= float(CMP_NEAR)]
    if not B:
        tell(p, "no missed jumps ('!j -') within %.0f m of #%d" % (float(CMP_NEAR), g0['n']))
        return
    # the good ones' mean take-off is the origin, the last good one's way the axis
    XS = [r['take'][0] for r in G]
    YS = [r['take'][1] for r in G]
    ZS = [r['take'][2] for r in G]
    ox = mean_sd(XS)[0]
    oy = mean_sd(YS)[0]
    oz = mean_sd(ZS)[0]
    ax = axis_of(g0)
    def get(r, what, o=(ox, oy, oz), ax=ax):
        if what == 'along':
            return along_side(r['take'], o, ax)[0]
        if what == 'side':
            return along_side(r['take'], o, ax)[1]
        if what == 'head':
            if r['head_take'] is None:
                return None
            return norm180(r['head_take'] - ax)
        if what == 'yaw':
            return norm180(r['yaw_take'] - ax)
        return r.get(what)
    # (what, words, threshold, number format, unit, always shown)
    items = [('along', 'take-off (+ later / - earlier)', 0.10, '%+.2f', ' m', 1),
             ('side', 'to the side (+ right)', 0.10, '%+.2f', ' m', 0),
             ('v_take', 'speed', 0.2, '%.2f', ' m/s', 1),
             ('head', 'direction of the run', 2.0, '%+.1f', ' deg', 0),
             ('yaw', 'facing', 2.0, '%+.1f', ' deg', 0),
             ('turn_before', 'turn in the last 0.5 s', 3.0, '%+.1f', ' deg', 0),
             ('runup_t', 'run-up', 0.2, '%.2f', ' s', 0),
             ('sprint_t', 'at sprint speed', 0.2, '%.2f', ' s', 0),
             ('v0', 'push-off', 0.3, '%.2f', ' m/s', 0),
             ('up', 'up', 0.10, '%.2f', ' m', 0),
             ('ping', 'ping', 20, '%.0f', '', 0)]
    out = []
    rest = []
    for what, words_, thr, fmt, unit, always in items:
        gv = [x for x in [get(r, what) for r in G] if x is not None]
        bv = [x for x in [get(r, what) for r in B] if x is not None]
        if not gv or not bv:
            continue
        mg, sg = mean_sd(gv)
        mb, sb = mean_sd(bv)
        sfmt = fmt.replace('+', '')
        log('CMP all %s: good %s (spread %s, %d) / missed %s (spread %s, %d)' % (what, fmt % mg, sfmt % sg, len(gv),
            fmt % mb, sfmt % sb, len(bv)))
        if always or abs(mb - mg) >= thr or sb >= 2 * thr + sg:
            out.append('%s %s / %s%s (spread %s / %s)' % (words_, fmt % mb, fmt % mg, unit, sfmt % sb, sfmt % sg))
        else:
            rest.append(words_)
    kinds = len([r for r in B if r['kind'] == 'fall'])
    head = '%d missed against %d good (within %.0f m of #%d), missed / good' % (len(B), len(G), float(CMP_NEAR),
        g0['n'])
    if kinds:
        head = head + '; %d missed had no push-off' % kinds
    tell(p, '%s: %s' % (head, '; '.join(out)))
    if rest:
        tell(p, 'about the same: ' + ', '.join(rest))

def onoff_text(v):
    return (v and 'ON') or 'off'

def cmd_tweak(p, which, arg):
    a = arg.lower()
    if which == 'stamina':
        props_read = STAMINA_READ
        on, off, state = stamina_on, stamina_off, 'stamina'
    else:
        props_read = GOD_READ
        on, off, state = god_on, god_off, 'god'
    if a == 'read':
        for line in tweak_read(props_read):
            tell(p, line)
        return
    if a == 'on':
        k = on()
        tell(p, '%s ON (%d soldier templates; see %s)' % (which, k, LOG_FILE))
    elif a == 'off':
        k = off()
        tell(p, '%s off (%d values back)' % (which, k))
    else:
        tell(p, '%s %s' % (which, onoff_text(S[state])))

def cmd_state(p):
    st = ps(p)
    pts = points_of(name_of(p))
    good = len([x for x in st['jl'] if x['mark'] == '+'])
    bad = len([x for x in st['jl'] if x['mark'] == '-'])
    tell(p, 'stamina %s, god %s, auto-return %s (%.1f m), meter %s; points %d, active "%s"; A %s; Vodnik %s; '
         'jumps seen %d (recorded %d: %d good, %d missed)' % (onoff_text(S['stamina']), onoff_text(S['god']),
         onoff_text(st['auto']), st['drop'], onoff_text(st['meter']), len(pts), st['active'] or '-', pos_text(st['a']),
         st['veh'] or '-', st['jumps'], len(st['jl']), good, bad))

def may_test(name):
    if not TEST_ADMINS:
        return 1
    for n in words(TEST_ADMINS, ','):
        n = n.lower()
        me = name.lower()
        if me == n or me.endswith(' ' + n):
            return 1
    return 0

HELP = ("'!j save [name]' / '!j go [name]' / '!j list' / '!j del <name>' - your points; '!j auto on|off|<m>'; "
        "'!j meter on|off'; '!j +' / '!j -' - mark your last jump good / missed; '!j cmp' / '!j cmp all' / "
        "'!j cmp <a> <b>'; '!j info [n]'; '!j jumps'; '!j a' / '!j b' - distance; '!j v' - a Vodnik; "
        "'!j stamina on|off|read'; '!j god on|off|read'; '!j state'; '!jj [m]' - a jump m forward and m up")

def on_chat(playerId, text, channel=None, flags=None):
    if not S['on']:
        return
    try:
        s = str(text)
    except:
        return
    i = s.lower().find('!j')
    if i < 0:
        return
    w = s[i:].split()
    if not w or w[0].lower() not in ('!j', '!jj'):
        return
    try:
        p = bf2.playerManager.getPlayerByIndex(int(playerId))
    except:
        p = None
    if p is None:
        return
    if not may_test(name_of(p)):
        return
    cmd = ''
    if len(w) > 1:
        cmd = w[1].lower()
    arg = ''
    if len(w) > 2:
        arg = w[2]
    log('%s: "%s"' % (name_of(p), ' '.join(w)))
    if w[0].lower() == '!jj':
        try:
            cmd_jj(p, (len(w) > 1 and w[1]) or '')
        except:
            log('command %s: %s' % (' '.join(w), err_text()))
        return
    try:
        if cmd == 'save':
            cmd_save(p, arg)
        elif cmd == 'go':
            cmd_go(p, arg)
        elif cmd == 'list':
            cmd_list(p)
        elif cmd == 'del':
            cmd_del(p, arg)
        elif cmd == 'auto':
            cmd_auto(p, arg)
        elif cmd == 'meter':
            cmd_meter(p, arg)
        elif cmd in ('a', 'b'):
            cmd_mark(p, cmd)
        elif cmd in ('+', '-'):
            cmd_mark_jump(p, cmd, arg)
        elif cmd == 'cmp':
            cmd_cmp(p, w[2:])
        elif cmd == 'info':
            cmd_info(p, arg)
        elif cmd == 'jumps':
            cmd_jumps(p)
        elif cmd in ('v', 'vodnik'):
            cmd_vehicle(p)
        elif cmd in ('stamina', 'god'):
            cmd_tweak(p, cmd, arg)
        elif cmd == 'state':
            cmd_state(p)
        elif cmd == 'con' and len(w) > 2:
            line = s[i:].split(None, 2)[2]
            tell(p, 'console: %s -> %s' % (line, console(line) or '(no answer)'))
        else:
            tell(p, HELP)
    except:
        log('command %s: %s' % (cmd, err_text()))
        tell(p, 'the command failed - see %s' % LOG_FILE)

# ------------------------------------------------------------------ events
def on_spawn(player, *rest):
    if not S['on']:
        return
    try:
        see_soldier(player)
        st = ps(player)
        st['js']['state'] = None
        st['raw'] = []
        st['jj'] = None
        st['dup'] = None
        if S['god'] and (not is_bot(player) or GOD_BOTS):
            later(0.3, spawn_heal, player)
    except:
        log('PlayerSpawn: ' + err_text())

def spawn_heal(p):
    heal_one(p)

def on_status(status):
    if not S['on']:
        return
    try:
        if status == bf2.GameStatus.Playing:
            log('round on %s' % map_name())
            if S['want_stamina']:
                stamina_on()
            if S['want_god']:
                god_on()
            for st in S['ps'].values():
                st['veh'] = None
                st['js']['state'] = None
                st['raw'] = []
                st['jj'] = None
                st['dup'] = None
    except:
        log('status: ' + err_text())

def map_name():
    try:
        return str(bf2.gameLogic.getMapName())
    except:
        return '?'

def jumptest_init():
    if S['on']:
        return
    S['on'] = 1
    S['want_stamina'] = int(STAMINA)
    S['want_god'] = int(GOD)
    log('jumptest %s loaded on %s (stamina %s, god %s, auto %s %.1f m, meter %s, private %s, frames every %.3f s; '
        'test admins: %s) - FOR A TEST SERVER ONLY' % (VERSION, map_name(), STAMINA, GOD, AUTO, float(AUTO_DROP), METER,
        SAY_PRIVATE, float(FRAME_EVERY), TEST_ADMINS or 'anybody'))
    load_points()
    for ev, fn in (('ChatMessage', on_chat), ('PlayerSpawn', on_spawn)):
        try:
            host.registerHandler(ev, fn, 1)
        except:
            log('could not register %s: %s' % (ev, err_text()))
    try:
        host.registerGameStatusHandler(on_status)
    except:
        log('could not register the status handler: ' + err_text())
    try:
        t = bf2.Timer(tick, float(FRAME_EVERY), 1, None)
        t.setRecurring(float(FRAME_EVERY))
        S['tick'] = t
    except:
        log('could not make the timer: ' + err_text())

# ------------------------------------------------------------------ ModManager interface
configDefaults = {}
for _k in ['TEST_ADMINS', 'SOLDIERS', 'SOLDIER_TYPE', 'STAMINA', 'STAMINA_SET', 'STAMINA_READ', 'GOD', 'GOD_SET',
           'GOD_READ', 'GOD_HP', 'GOD_BOTS', 'HEAL_EVERY', 'SAMPLE', 'FRAME_EVERY', 'KEEP', 'RUNUP_LOG', 'RUNUP_MIN',
           'STAND_MAX', 'RUN_MIN', 'SPRINT_MIN', 'SPRINT_FULL', 'CMP_NEAR', 'JUMPS_MAX', 'FRAMES_LOG', 'GRAVITY', 'UP_SPEED', 'AIR_MIN', 'AIR_MAX',
           'TP_STEP', 'SKY', 'MOVE_STEP', 'DIRECT_NEAR', 'ARRIVE_CHECK', 'TP_OK', 'AUTO', 'AUTO_DROP', 'AUTO_FROM',
           'AUTO_RANGE', 'AUTO_DELAY', 'METER', 'POINTS_FILE', 'TP_UP',
           'VEHICLE', 'VEH_AHEAD', 'VEH_UP', 'JJ_DIST', 'JJ_MAX', 'JJ_MIN', 'JJ_GRAVITY', 'JJ_HIT', 'JJ_SETTLE',
           'SAY_PRIVATE', 'CHAT_MAX', 'LOG_FILE']:
    configDefaults[_k] = globals()[_k]

class JumpTest( object ):

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
        for k in ('GOD_HP', 'HEAL_EVERY', 'SAMPLE', 'FRAME_EVERY', 'KEEP', 'RUNUP_LOG', 'RUNUP_MIN', 'STAND_MAX',
                  'RUN_MIN', 'SPRINT_MIN', 'SPRINT_FULL', 'CMP_NEAR', 'GRAVITY', 'UP_SPEED', 'AIR_MIN', 'AIR_MAX', 'TP_STEP', 'SKY',
                  'MOVE_STEP', 'DIRECT_NEAR', 'ARRIVE_CHECK', 'TP_OK', 'AUTO_DROP',
                  'AUTO_FROM', 'AUTO_RANGE', 'AUTO_DELAY', 'TP_UP', 'VEH_AHEAD', 'VEH_UP', 'JJ_DIST', 'JJ_MAX',
                  'JJ_MIN', 'JJ_GRAVITY', 'JJ_HIT', 'JJ_SETTLE'):
            try:
                g[k] = float(g[k])
            except:
                g[k] = configDefaults[k]
        for k in ('STAMINA', 'GOD', 'GOD_BOTS', 'AUTO', 'METER', 'SAY_PRIVATE', 'CHAT_MAX', 'JUMPS_MAX', 'FRAMES_LOG'):
            try:
                g[k] = int(g[k])
            except:
                g[k] = configDefaults[k]
        if g['SAMPLE'] < 0.03:
            g['SAMPLE'] = 0.03
        if g['FRAME_EVERY'] < 0.01:
            g['FRAME_EVERY'] = 0.01
        if g['FRAME_EVERY'] > g['SAMPLE']:
            g['FRAME_EVERY'] = g['SAMPLE']
        self.__state = 1
        jumptest_init()
        try:
            self.mm.info( 'jumptest %s is running - FOR A TEST SERVER ONLY (see %s)' % ( VERSION, LOG_FILE ) )
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
    return JumpTest( modManager )
