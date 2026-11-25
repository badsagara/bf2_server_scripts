# mm_baseheal.py - BaseHeal 1.0.0: each side's main base on a Battlefield 2 server - its soldiers and the vehicles
# they sit in are healed there, and an enemy who still kills there is killed - as a Multiplay ModManager module on the
# =FL= bus mm_flbus (ModManager 1.0 or later, Python 2.3 of BF2 1.5)
#
# The light variant of baseshield. Sagara, 08.11: "a separate variant that does not take shots out of the air, only
# heals infantry and vehicles in its zone + kills those who managed to kill somebody in the zone". Most of
# baseshield's load was the shots: every projectile every frame, and every player every 0.1 s to tell whose a shot
# is. BaseHeal asks for no projectile at all, and follows the players by the game's events.
#
# In a zone of a side (ZONES; Karkand 64: Gas Station - US, Factory - MEC):
#   - a soldier of that side hurt there (not killed) gets his health back to what it was; a moment later his health
#     dips by SOLDIER_NUDGE and comes back, so that his screen shows it;
#   - a vehicle of that side with its crew in it (a soldier of that side) gets its health back to what it was.
#     Empty vehicles and stationary weapons (machine guns, TOW / HJ-8, artillery) are not healed;
#   - health of KEEP_LOW 1 or lower is never given back: a script set it (mm_noarmor_v2's "BOOM": 0.01; a vehicle
#     punished here: 1);
#   - punished - killed, and everybody is told why ("[BaseHeal] Name killed for killing Name2 in the MEC base from
#     outside it"):
#       an enemy who, from outside the zone, kills a soldier of that side in it;
#       an enemy who, inside the zone, kills a soldier of that side (anywhere);
#       an enemy who, from outside the zone, destroys a vehicle of that side in it (stationary weapons not counted).
#     Kills by C4, mines, claymores and artillery are not counted (SKIP). Killing an enemy from inside one's own zone is
#     defence: never punished. More kills by the same player within SAME_ATTACK 2 s: punished once. No warnings, no
#     kick. On foot: health 0 (man down; put down again if a medic revives him within KEEP_DOWN 20 s). In a vehicle or
#     on a gun: its health is set to VEH_HP_LEFT 1 - it burns out, and everybody in it dies with it, or when he gets
#     out (a soldier sitting in a vehicle is never set: baseshield 2.0.6).
#
# How it follows the players (the load). Whether a player is alive, his side and the vehicle he is in come from the
# game's events (spawn, death, getting in / out, changing sides); each player is checked again once every SAFE_EVERY
# 2 s in case an event was missed. His place is read only as often as he could reach his own zone: within HEAL_MARGIN
# 5 m of it (or in it) every look, with his health; farther away once in the time he needs to come within 5 m (on foot
# V_FOOT 10 m/s, in a ground vehicle V_GROUND 40, in an aircraft V_AIR 150), and at least every MAX_GAP 2 s. A player
# is asked whether he is alive before anything else (the game is never asked about a player who is not alive:
# baseshield 2.0.1). The other side is not followed: where a killer stood is asked when he kills. The game is never
# asked for every vehicle (that broke mm_noarmor_v2: baseshield 2.0.14), nor for the projectiles.
#
# INSTALL
#   1. Copy this file and mm_flbus.py (1.0 or later) to <server folder>/admin/modules/
#   2. modmanager.con: add  modmanager.loadModule "mm_baseheal"  and take out the line of mm_baseshield (never both:
#      they would heal and punish twice).
#   3. Restart the server.
#   4. baseheal.log (server folder): "baseheal 1.0.0 loaded", at a Karkand 64 round "round on strike_at_karkand 64:
#      2 zones"; flbus.log: "baseheal joined".
# Settings: modmanager.con, mm_baseheal.<NAME> <value>. The zones: ZONES below (the same as baseshield's).
#
# History
# 1.0.0 (2026-11-08) First. baseshield 2.0.16's zones, healing and kill rules, without the shots; vehicles with a crew
#   healed; punished = killed only, with the reason in the chat; SKIP for both rules; [BaseHeal].

__version__ = 1.0

__required_modules__ = {
	'modmanager': 1.0,
	'mm_flbus': 1.0
}

__supports_reload__ = False

__supported_games__ = {
	'bf2': True,
	'bf2142': False,
	'bfheroes': False,
	'bfp4f': False
}

__description__ = 'BaseHeal v1.0.0 (ModManager module, on mm_flbus)'

import bf2
import host
import mm_flbus as BUS

VERSION = '1.0.0'

# ------------------------------------------------------------------ settings
# Protected zones per map, as BF2 AutoAdmin zone lines. The key: the map's name and size ('strike_at_karkand 64': only
# on Karkand 64), or the name alone (every size of that map). The size running is read from the server's map list.
#   id, side, x, height, z, [], size x, size height, size z, rotation, name
#   - a box round (x, height, z) of that size; side 1 or 2 = the side it protects (Karkand: 1 MEC, 2 US); 0 = both
#   - rotation must be 0 (a turned box is not supported: it is taken as not turned, with a line in the log)
ZONES = {
    'strike_at_karkand 64': [
        '0,2,-161,161,-225,[],300,100,300,0,Base (Gas station)',
        '1,1,220,153.7,168,[],140,50,132,0, Factory Mec',
    ],
}
HEAL = 1               # 1: a soldier of the zone's side hurt in the zone gets his health back (to what it was)
HEAL_VEHICLES = 1      # 1: ... and a vehicle of the zone's side with its crew in it (not empty ones, not stationary)
SOLDIER_NUDGE = 1.0    # a moment after, his health dips by this much and comes back, so his screen shows it (0: off)
KEEP_LOW = 1.0         # health this low (or lower, above 0) is never given back: a script set it (mm_noarmor_v2: 0.01)
PUNISH = 1             # 1: the kills below are punished (killed, the reason in the chat)
PUNISH_IN = 1          # 1: an enemy INSIDE a zone who kills a soldier of the zone's side (anywhere) is punished too
PUNISH_WRECKS = 1      # 1: an enemy who destroys a vehicle of the zone's side in it from outside is punished too
SKIP = ('c4', 'mine', 'claymore', 'usart_', 'ars_', 'artillery')   # weapons not counted (laid explosives, commander)
SAME_ATTACK = 2.0      # s: more kills / wrecks by the same player within this time are punished once (a shell, a crew)
MSG_OUT = '[BaseHeal] %s killed for killing %s in the %s base from outside it'       # killer, victim, base
MSG_IN = '[BaseHeal] %s killed for killing %s from inside the %s base'               # killer, victim, base
MSG_WRECK = '[BaseHeal] %s killed for destroying a %s in the %s base from outside it'  # killer, kind, base
TEAM_NAMES = {1: 'MEC', 2: 'US'}   # when the game does not give a side's name
CHECK_EVERY = 0.02     # s: how often the players near their zones are looked at (the server's frame: ~0.03 s)
HEAL_MARGIN = 5.0      # m: a player this close to (or in) his own side's zone: his place and health read every look
V_FOOT = 10.0          # m/s: how fast a player on foot can come to his zone (his place is read as often as needed)
V_GROUND = 40.0        # m/s: ... in a ground vehicle (or on a gun)
V_AIR = 150.0          # m/s: ... in an aircraft
MAX_GAP = 2.0          # s: everybody's place is read at least this often
SAFE_EVERY = 2.0       # s: each player is checked again this often (alive, side, vehicle) in case an event was missed
VEH_HP_LEFT = 1.0      # the punished vehicle's health is set to this (it burns out); 0: its health is left
VEH_GRACE = 15.0       # s: kills / wrecks by a punished crew are not counted for this long, or till they spawn again
VEH_CHECK = 12.0       # s: a check this long (and 1 s) after punishing a crew: dead or alive, the vehicle's health
KEEP_DOWN = 20.0       # s: a punished soldier (man down) revived by a medic within this time is put down again
CHAT_POS = 0           # 1: "!pos" tells the player where he stands; "!baseheal" what runs (anybody can use them)
CHAT_MAX = 180         # characters: a longer chat line is split (a too long one crashed the server: baseshield 2.0.2)
TEST_CHAT = 0          # 1: chat lines for a test (each soldier / vehicle healed, each kill not counted)
TEST_COMMANDS = 0      # 1 (a TEST server only - anybody can use them): "!tp <point>", "!mark <name>", "!endround", "!help"
TP_POINTS = {          # name: (x, height, z) - a little above the ground (Karkand)
    'us': (-150.6, 163.5, -271.1),        # the US base (Gas station), by its vehicles - inside the US zone
    'usedge': (-201.0, 161.5, -114.0),    # the north edge of the US base - inside the US zone (80 m from usout)
    'usout': (-207.0, 158.3, -35.2),      # the road north of the US base - outside the US zone
    'mec': (161.6, 155.2, 152.3),         # the Factory - inside the MEC zone
    'mecedge': (158.0, 155.0, 224.0),     # the north-west edge of the Factory - inside the MEC zone (22 m from mecout)
    'mecout': (147.6, 155.0, 243.6),      # north-west of the Factory - outside the MEC zone
    'mecmg': (141.8, 158.5, 161.0),       # by the MEC machine gun (mec_bipod) 8 m west of the Factory - outside
}
LOG_FILE = 'baseheal.log'   # in the server folder; '' - no log

# full health of the vehicles one can drive or fly (BF2 1.5's object files): a check that a soldier's getDamage used on
# a vehicle reads the vehicle, not the soldier
VEH_HP = {
    'aav_tunguska': 1000.0, 'aav_type95': 1000.0, 'ahe_ah1z': 875.0, 'ahe_havoc': 875.0, 'ahe_z10': 875.0,
    'air_f35b': 825.0, 'air_j10': 825.0, 'air_su30mkk': 750.0, 'apc_btr90': 1000.0, 'apc_wz551': 1000.0,
    'boat_rib': 750.0, 'chthe_z8': 1350.0, 'jeep_faav': 750.0, 'jep_mec_paratrooper': 750.0, 'jep_nanjing': 1000.0,
    'jep_paratrooper': 750.0, 'jep_vodnik': 1000.0, 'ruair_mig29': 825.0, 'ruair_su34': 900.0, 'rutnk_t90': 1000.0,
    'the_mi17': 1350.0, 'tnk_type98': 1000.0, 'usaav_m6': 1000.0, 'usair_f15': 900.0, 'usair_f18': 825.0,
    'usapc_lav25': 1000.0, 'usjep_hmmwv': 1000.0, 'usthe_uh60': 1350.0, 'ustnk_m1a2': 1000.0,
}
# what a vehicle is called in the chat (by its template's name)
KIND_WORDS = [('tnk', 'tank'), ('apc', 'APC'), ('aav', 'AA vehicle'), ('ahe', 'helicopter'), ('the_', 'helicopter'),
              ('air', 'plane'), ('jep', 'jeep'), ('jeep', 'jeep'), ('boat', 'boat')]
AIR_WORDS = ['air_', 'ahe_', 'the_', 'heli', 'parachute']

# ------------------------------------------------------------------ state
F = None
P = {}     # player index -> his record

S = {'on': 0, 'zones': [], 'has': {}, 'zkey': None, 'znote': None, 'size': None, 'order': [], 'sync_t': -99.0,
     'safe_t': 0.0, 'safe_i': 0, 'safe_acc': 0.0, 'sold': {}, 'vrec': {}, 'owner': {}, 'last': {}, 'pending': {},
     'down': {}, 'burning': {}, 'spawned': {}, 'checks': [], 'borrow': {}, 'bfun': None, 'vread': {}, 'punished_veh': {},
     'stat': {}, 'marks': {}, 'told': {}, 'missed_n': 0, 'n': {}}

def new_counts():
    return {'calls': 0, 'pos': 0, 'hp': 0, 'vhp': 0, 'safe': 0, 'heal': 0, 'vheal': 0, 'out': 0, 'in': 0, 'wreck': 0,
            'skip': 0, 'same': 0, 'nochat': 0, 'missed': 0, 'low': 0}

S['n'] = new_counts()

def calls(k):
    S['n']['calls'] = S['n']['calls'] + k

def count(name):
    S['n'][name] = S['n'][name] + 1

# ------------------------------------------------------------------ log, chat
def log(text):
    try:
        rt = BUS.now() - BUS.S['round_t']
    except:
        rt = 0.0
    line = '[%7.2f]  %s' % (rt, text)
    if F is not None:
        F.log(line)
    else:
        BUS.write_log(LOG_FILE, line)

def err_text():
    return BUS.err_text()

def now():
    return BUS.now()

def tell_once(key, text):
    if key not in S['told']:
        S['told'][key] = 1
        log(text)

TAG = '[BaseHeal %s test]' % VERSION

def say(text):
    # one chat line to all - split into lines of at most CHAT_MAX characters
    try:
        text = str(text).replace('"', "'")
        parts = []
        while len(text) > CHAT_MAX:
            cut = text.rfind(' ', 0, CHAT_MAX)
            if cut < CHAT_MAX / 3:
                cut = CHAT_MAX
            parts.append(text[:cut])
            text = '  ' + text[cut:].lstrip()
        parts.append(text)
        for t in parts:
            host.rcon_invoke('game.sayAll "%s"' % t)
    except:
        log('chat failed: ' + err_text())

def test_say(text):
    if TEST_CHAT:
        say(TAG + ' ' + text)

def fmt(msg, args):
    try:
        return msg % args
    except:
        return msg

# ------------------------------------------------------------------ zones
def map_size(mp):
    # the size (16 / 32 / 64) of the map running, from the server's map list; None when it cannot be told
    entries = []
    try:
        txt = str(host.rcon_invoke('maplist.list') or '')
    except:
        txt = ''
    for line in txt.split('\n'):
        try:
            idx, rest = line.split(':', 1)
            f = rest.replace('"', ' ').split()
            entries.append((int(idx.strip()), f[0].lower(), int(f[2])))
        except:
            pass
    cur = None
    try:
        cur = int(str(host.rcon_invoke('maplist.currentMap')).strip())
    except:
        cur = None
    sizes = []
    for i, name, size in entries:
        if name == mp:
            if cur is not None and i == cur:
                return size
            if size not in sizes:
                sizes.append(size)
    if len(sizes) == 1:
        return sizes[0]
    return None

def zone_key(mp, size):
    # (the ZONES key for this map and size or None, a note for the log or None)
    sized = []
    for k in ZONES.keys():
        f = k.split()
        if len(f) == 2 and f[0].lower() == mp:
            sized.append(k)
    if size is not None:
        for k in sized:
            if k.split()[1] == str(size):
                return k, None
    if mp in ZONES:
        return mp, None
    if size is None and len(sized) == 1:
        return sized[0], 'the map size could not be read from the map list - %s taken' % sized[0]
    if sized:
        return None, 'zones are set for %s only - this is %s %s: no zones' % (', '.join(sized), mp, size or '(size unknown)')
    return None, None

def parse_zone(line):
    # -> zone dict, or None (logged)
    try:
        f = line.split(',')
        if len(f) < 11 or f[5].strip() != '[]':
            raise ValueError('not "id, side, x, height, z, [], size x, size height, size z, rotation, name"')
        side = int(f[1])
        x, h, z = float(f[2]), float(f[3]), float(f[4])
        sx, sh, sz = float(f[6]), float(f[7]), float(f[8])
        rot = float(f[9])
        name = ','.join(f[10:]).strip() or ('zone ' + f[0].strip())
        if rot != 0:
            log('zone %s: rotation %s is not supported - taken as 0' % (name, f[9].strip()))
        return {'name': name, 'side': side, 'x0': x - sx / 2, 'x1': x + sx / 2, 'h0': h - sh / 2, 'h1': h + sh / 2,
                'z0': z - sz / 2, 'z1': z + sz / 2}
    except:
        log('zone line not understood: %r (%s)' % (line, err_text()))
        return None

def zone_at(pos, side=None):
    # the first zone the point (x, height, z) is in (that protects side, when side is given), or None
    if pos is None:
        return None
    for z in S['zones']:
        if z['x0'] <= pos[0] <= z['x1'] and z['z0'] <= pos[2] <= z['z1'] and z['h0'] <= pos[1] <= z['h1']:
            if side is None or z['side'] == 0 or z['side'] == side:
                return z
    return None

def zone_dist(q, side):
    # m from q to the nearest zone of side, on the map (0 inside it, any height); None: that side has no zone here
    best = None
    for z in S['zones']:
        if z['side'] != 0 and z['side'] != side:
            continue
        dx = max(z['x0'] - q[0], 0.0, q[0] - z['x1'])
        dz = max(z['z0'] - q[2], 0.0, q[2] - z['z1'])
        d = (dx * dx + dz * dz) ** 0.5
        if best is None or d < best:
            best = d
    return best

def where(pos):
    return '(x %.0f, z %.0f)' % (pos[0], pos[2])

# ------------------------------------------------------------------ the game's objects and players
def obj_key(o):
    if o is None:
        return None
    try:
        return o.token
    except:
        return None

def root_of(o):
    try:
        r = bf2.objectManager.getRootParent(o)
        if r is not None:
            return r
    except:
        pass
    return o

def tpl(o):
    try:
        return str(o.templateName)
    except:
        return '?'

def read_hp(o):
    try:
        v = o.getDamage()
        if v is None:
            return None
        return float(v)
    except:
        return None

def apart(p, q):
    return abs(p[0] - q[0]) + abs(p[1] - q[1]) + abs(p[2] - q[2])

def players():
    calls(1)
    try:
        return bf2.playerManager.getPlayers()
    except:
        return []

def team_of(p):
    calls(1)
    try:
        return int(p.getTeam())
    except:
        return None

def is_alive(p):
    calls(1)
    try:
        return p.isAlive() and 1 or 0
    except:
        return 0

def man_down(p):
    try:
        return p.isManDown() and 1 or 0
    except:
        return None

def player_name(p):
    try:
        return p.getName().strip()
    except:
        return '?'

def team_name(side):
    try:
        n = bf2.gameLogic.getTeamName(side)
        if n:
            return str(n)
    except:
        pass
    return TEAM_NAMES.get(side, 'side %s' % side)

def kind_word(name):
    n = name.lower()
    for w, k in KIND_WORDS:
        if n.find(w) >= 0:
            return k
    return 'vehicle'

def is_air(name):
    n = name.lower()
    for w in AIR_WORDS:
        if n.find(w) >= 0:
            return 1
    return 0

def ride_of(p, alive=0):
    # (the root of the vehicle he sits in, or None; his soldier) - only for a living player: the game must not be
    # asked for the vehicle of a player who is not alive (baseshield 2.0.1). alive 1: the caller has just asked.
    s = v = None
    if not alive and not is_alive(p):
        return None, None
    calls(2)
    try:
        s = p.getDefaultVehicle()
        v = p.getVehicle()
    except:
        pass
    try:
        if v is not None and s is not None:
            kv, ks = obj_key(v), obj_key(s)
            if kv is not None and ks is not None:
                if kv != ks:
                    calls(1)
                    return root_of(v), s
                return None, s
            if v.templateName.lower() != s.templateName.lower():
                calls(1)
                return root_of(v), s
    except:
        pass
    return None, s

def place_now(r):
    # where a player is now (asked of the game): his vehicle's place, or his soldier's; not alive: his last place
    p = r['p']
    if not is_alive(p):
        return r['pos']
    v, s = ride_of(p, 1)
    o = v
    if o is None:
        o = s
    if o is None:
        return r['pos']
    calls(1)
    try:
        q = o.getPosition()
        return (float(q[0]), float(q[1]), float(q[2]))
    except:
        return r['pos']

# ------------------------------------------------------------------ the players' records (kept by the game's events)
def new_rec(p, idx):
    return {'p': p, 'idx': idx, 'name': player_name(p), 'team': None, 'alive': 0, 'soldier': None, 'veh': None,
            'vkey': None, 'vname': '', 'pos': None, 'pos_t': -99.0, 'next': 0.0, 'near': 0}

def rec_of(p, make=1):
    try:
        idx = p.index
    except:
        return None
    r = P.get(idx)
    if r is None:
        if not make:
            return None
        r = new_rec(p, idx)
        r['team'] = team_of(p)
        P[idx] = r
        if idx not in S['order']:
            S['order'].append(idx)
    else:
        r['p'] = p
    return r

def drop_heal(idx):
    if idx in S['sold']:
        del S['sold'][idx]

def set_ride(r, v, s, t):
    # what he sits in (v: the vehicle's root object, or None: on foot) and his soldier (s, or None: unchanged)
    if s is not None:
        r['soldier'] = s
    k = None
    name = ''
    if v is not None:
        if obj_key(v) is not None and obj_key(v) == obj_key(r['soldier']):
            v = None
        else:
            k = obj_key(v)
            name = tpl(v)
    if k != r['vkey'] or (v is None) != (r['veh'] is None):
        r['veh'], r['vkey'], r['vname'] = v, k, name
        r['next'] = 0.0
        if v is not None and k is not None and r['team'] is not None:
            S['owner'][k] = r['team']      # (a vehicle's side: its last crew's)

def set_dead(r):
    r['alive'] = 0
    r['soldier'], r['veh'], r['vkey'], r['vname'] = None, None, None, ''
    r['near'] = 0
    drop_heal(r['idx'])

def missed(r, what):
    count('missed')
    S['missed_n'] = S['missed_n'] + 1
    if S['missed_n'] <= 20:
        log('%s: %s (seen by the check every %.0f s - the event was missed)' % (r['name'], what, SAFE_EVERY))

def sync_players(t):
    # the players the game has now: new ones get a record (alive, side, vehicle asked), gone ones are dropped
    S['sync_t'] = t
    have = {}
    for p in players():
        try:
            idx = p.index
        except:
            continue
        have[idx] = 1
        r = P.get(idx)
        if r is None or (r['p'] is not p and r['name'] != player_name(p)):
            r = new_rec(p, idx)
            r['team'] = team_of(p)
            P[idx] = r
            if is_alive(p):
                r['alive'] = 1
                v, s = ride_of(p, 1)
                set_ride(r, v, s, t)
        else:
            r['p'] = p
    for idx in list(P.keys()):
        if idx not in have:
            del P[idx]
            drop_heal(idx)
    order = list(have.keys())
    order.sort()
    S['order'] = order

def check_one(r, t):
    # the check every SAFE_EVERY s: what the events should have told
    p = r['p']
    S['n']['safe'] = S['n']['safe'] + 1
    tm = team_of(p)
    if tm is not None and tm != r['team']:
        if r['team'] is not None:
            missed(r, 'side %s -> %s' % (r['team'], tm))
        r['team'] = tm
        drop_heal(r['idx'])
        r['next'] = 0.0
    al = is_alive(p)
    if not al:
        if r['alive']:
            missed(r, 'not alive')
            set_dead(r)
        return
    v, s = ride_of(p, 1)
    if not r['alive']:
        missed(r, 'alive')
        r['alive'] = 1
        r['next'] = 0.0
    if s is not None and obj_key(s) != obj_key(r['soldier']):
        r['soldier'] = s
        drop_heal(r['idx'])
    if obj_key(v) != r['vkey']:
        if v is None:
            missed(r, 'on foot (was in a %s)' % (r['vname'] or 'vehicle'))
        else:
            missed(r, 'in a %s' % tpl(v))
        set_ride(r, v, None, t)

def safe_step(t):
    if t - S['sync_t'] >= SAFE_EVERY:
        sync_players(t)
    n = len(S['order'])
    if not n:
        return
    dt = t - S['safe_t']
    S['safe_t'] = t
    if dt < 0 or dt > 1.0:
        dt = CHECK_EVERY
    S['safe_acc'] = S['safe_acc'] + n * dt / SAFE_EVERY
    k = int(S['safe_acc'])
    S['safe_acc'] = S['safe_acc'] - k
    if k > n:
        k = n
    while k > 0:
        k = k - 1
        i = S['safe_i'] % n
        S['safe_i'] = i + 1
        r = P.get(S['order'][i])
        if r is not None:
            check_one(r, t)

# ------------------------------------------------------------------ events
def ev_connect(p, *rest):
    if not S['on'] or not S['zones']:
        return
    try:
        idx = p.index
    except:
        return
    r = new_rec(p, idx)
    r['team'] = team_of(p)
    P[idx] = r
    drop_heal(idx)
    if idx not in S['order']:
        S['order'].append(idx)

def ev_disconnect(p, *rest):
    try:
        idx = p.index
    except:
        return
    if idx in P:
        del P[idx]
    drop_heal(idx)
    for d in (S['pending'], S['down']):
        if idx in d:
            del d[idx]

def ev_spawn(p, soldier=None, *rest):
    if not S['on'] or not S['zones']:
        return
    try:
        r = rec_of(p)
        if r is None:
            return
        t = now()
        idx = r['idx']
        r['name'] = player_name(p)
        r['team'] = team_of(p)
        s = soldier
        if s is None:
            calls(1)
            try:
                s = p.getDefaultVehicle()
            except:
                s = None
        r['alive'] = 1
        r['soldier'] = s
        r['veh'], r['vkey'], r['vname'] = None, None, ''
        r['near'] = 0
        r['next'] = 0.0
        drop_heal(idx)
        S['spawned'][idx] = t
        if r['name'] in S['burning']:
            del S['burning'][r['name']]       # (spawned again: his kills count again)
        for d in (S['pending'], S['down']):
            if idx in d:
                del d[idx]
    except:
        log('PlayerSpawn: ' + err_text())

def ev_death(p, *rest):
    try:
        r = rec_of(p, 0)
        if r is not None:
            set_dead(r)
    except:
        log('PlayerDeath: ' + err_text())

def ev_revived(p, *rest):
    try:
        r = rec_of(p, 0)
        if r is not None:
            r['next'] = 0.0
            drop_heal(r['idx'])
    except:
        pass

def ev_enter(p, vehicle=None, *rest):
    if not S['on'] or not S['zones'] or vehicle is None:
        return
    try:
        r = rec_of(p)
        if r is None:
            return
        calls(1)
        set_ride(r, root_of(vehicle), None, now())
    except:
        log('EnterVehicle: ' + err_text())

def ev_exit(p, vehicle=None, *rest):
    if not S['on'] or not S['zones']:
        return
    try:
        r = rec_of(p, 0)
        if r is not None:
            set_ride(r, None, None, now())
    except:
        log('ExitVehicle: ' + err_text())

def ev_team(p, *rest):
    if not S['on'] or not S['zones']:
        return
    try:
        r = rec_of(p)
        if r is None:
            return
        tm = team_of(p)
        if tm != r['team']:
            log('%s: side %s -> %s' % (r['name'], r['team'], tm))
            r['team'] = tm
            drop_heal(r['idx'])
            r['next'] = 0.0
    except:
        log('PlayerChangeTeams: ' + err_text())

# ------------------------------------------------------------------ the look every CHECK_EVERY s
def read_place(r, t):
    # his place now (his vehicle's, or his soldier's) - asked only after asking whether he is alive
    p = r['p']
    if not is_alive(p):
        if r['alive']:
            missed(r, 'not alive')
            set_dead(r)
        return None
    o = r['veh']
    if o is None:
        o = r['soldier']
    if o is None:
        v, s = ride_of(p, 1)
        set_ride(r, v, s, t)
        o = v
        if o is None:
            o = s
        if o is None:
            return None
    q = None
    calls(1)
    try:
        q = o.getPosition()
        q = (float(q[0]), float(q[1]), float(q[2]))
    except:
        q = None
    if q is None or abs(q[0]) + abs(q[1]) + abs(q[2]) < 0.01:
        # (the object he was in is gone, or waits at 0, 0, 0): ask him again
        v, s = ride_of(p, 1)
        set_ride(r, v, s, t)
        o = v
        if o is None:
            o = s
        if o is None:
            return None
        calls(1)
        try:
            q = o.getPosition()
            q = (float(q[0]), float(q[1]), float(q[2]))
        except:
            return None
    r['pos'], r['pos_t'] = q, t
    S['n']['pos'] = S['n']['pos'] + 1
    return q

def gap(r, d):
    # s till his place must be read again: the time he needs to come within HEAL_MARGIN of his zone
    v = V_FOOT
    if r['veh'] is not None:
        v = V_GROUND
        if is_air(r['vname']):
            v = V_AIR
    g = (d - HEAL_MARGIN) / max(v, 0.1)
    if g < CHECK_EVERY:
        g = CHECK_EVERY
    if g > MAX_GAP:
        g = MAX_GAP
    return g

def look(t):
    if not S['zones']:
        return
    if S['pending']:
        run_pending(t)
    if S['down']:
        run_down(t)
    if S['checks']:
        run_checks(t)
    safe_step(t)
    vs = {}
    for idx in S['order']:
        r = P.get(idx)
        if r is None or not r['alive'] or not S['has'].get(r['team']):
            continue
        if not r['near'] and t < r['next'] - 0.001:
            continue
        q = read_place(r, t)
        if q is None:
            r['next'] = t + 0.5
            continue
        d = zone_dist(q, r['team'])
        if d is None:
            r['next'] = t + MAX_GAP
            continue
        if d <= HEAL_MARGIN:
            r['near'] = 1
            if HEAL:
                heal_soldier(r, q, t)
            if HEAL_VEHICLES and r['veh'] is not None and r['vkey'] is not None and r['vkey'] not in vs:
                vs[r['vkey']] = (r, q)
            continue
        if r['near']:
            r['near'] = 0
            drop_heal(idx)                    # (far from his zone: his health is read again when he comes near)
        r['next'] = t + gap(r, d)
    for k in list(S['vrec'].keys()):
        if k not in vs:
            del S['vrec'][k]                  # (no crew of its side near: read again when there is)
    for k in vs.keys():
        heal_vehicle(k, vs[k][0], vs[k][1], t)

# ------------------------------------------------------------------ soldiers: health back
def heal_soldier(r, q, t):
    idx = r['idx']
    if idx in S['down'] or idx in S['pending']:
        drop_heal(idx)                        # (a punished soldier: not healed)
        return
    s = r['soldier']
    if s is None:
        return
    calls(1)
    hp = read_hp(s)
    S['n']['hp'] = S['n']['hp'] + 1
    if hp is None:
        return
    rec = S['sold'].get(idx)
    if rec is None:
        S['sold'][idx] = {'hp': hp, 'nudge': None, 'nudged': 0, 'low': 0}
        return
    if rec['nudged']:
        rec['nudged'] = 0
        if abs(hp - (rec['hp'] - SOLDIER_NUDGE)) < 0.01:
            calls(1)
            try:
                s.setDamage(rec['hp'])        # (the dip back up: done)
            except:
                pass
            return
    z = zone_at(q, r['team'])
    if z is not None and hp < rec['hp'] - 0.5:
        if hp <= KEEP_LOW:
            if hp > 0.0 and not rec['low']:
                rec['low'] = 1
                count('low')
                log('%s (side %s) in %s: health %.2f - that low is set by a script (mm_noarmor_v2: 0.01): not given '
                    'back' % (r['name'], r['team'], z['name'], hp))
            rec['hp'] = hp
            return
        calls(1)
        try:
            s.setDamage(rec['hp'])
        except:
            tell_once('soldier set', 'soldier setDamage failed: ' + err_text())
            rec['hp'] = hp
            return
        count('heal')
        log('%s (side %s) hurt in %s at %s: health %.0f, back to %.0f' % (r['name'], r['team'], z['name'], where(q), hp,
            rec['hp']))
        test_say('%s hurt in %s: %.0f -> back to %.0f' % (r['name'], z['name'], hp, rec['hp']))
        if SOLDIER_NUDGE > 0:
            rec['nudge'] = t + 0.2
        return
    if rec['nudge'] is not None and t >= rec['nudge'] and z is not None and abs(hp - rec['hp']) < 0.01:
        rec['nudge'] = None
        calls(1)
        try:
            s.setDamage(rec['hp'] - SOLDIER_NUDGE)
            rec['nudged'] = 1
        except:
            pass
        return
    rec['hp'] = hp                            # (healed by a medic, or hurt outside the zone: that is his health now)

# ------------------------------------------------------------------ vehicles: health back
def health_calls(v, name, r):
    # (read, set, how) for the vehicle v, or (None, None, why not). Its own calls (the first round after a server
    # start), else the functions behind a soldier's calls used on the vehicle (baseshield 2.0.8) - the first time for
    # each kind of vehicle only READ, and used only when what they read is the vehicle's, not the soldier's own value
    g, st = getattr(v, 'getDamage', None), getattr(v, 'setDamage', None)
    if g is not None and st is not None:
        return g, st, 'its own calls'
    b = S['borrow'].get(name)
    if b is not None and b[0] == 'no':
        return None, None, b[1]
    sold = r['soldier']
    if S['bfun'] is None:
        if sold is None:
            return None, None, 'no soldier to take the calls from'
        try:
            fg, fs = BUS.func_of(sold.getDamage), BUS.func_of(sold.setDamage)
        except:
            return None, None, "a soldier's calls cannot be looked at (%s)" % err_text()
        if fg is None or fs is None:
            why = "a soldier's calls are not plain methods (%r)" % (getattr(sold, 'getDamage', None),)
            S['borrow'][name] = ('no', why)
            return None, None, why
        S['bfun'] = (fg, fs)
    fg, fs = S['bfun']
    if b is None:
        calls(2)
        try:
            hp = float(fg(v))
            own = float(sold.getDamage())
        except:
            why = "a soldier's getDamage does not work on it (%s)" % err_text()
            S['borrow'][name] = ('no', why)
            return None, None, why
        full = VEH_HP.get(name)
        if not (0.0 < hp <= 20000.0) or (abs(hp - own) < 0.01 and (full is None or abs(full - hp) > 0.5)):
            why = "a soldier's getDamage reads %.1f on it (his own soldier: %.1f) - not the vehicle's" % (hp, own)
            S['borrow'][name] = ('no', why)
            return None, None, why
        S['borrow'][name] = ('read', '')
        log("%s: no calls of its own; a soldier's getDamage reads %.0f on it (full %s): used" % (name, hp, full))
    return (lambda: fg(v)), (lambda x: fs(v, x)), "a soldier's calls"

def heal_vehicle(k, r, q, t):
    v = r['veh']
    name = r['vname'].lower()
    if k in S['punished_veh']:
        return
    if not BUS.is_vehicle(name):
        if name not in S['stat']:
            S['stat'][name] = 1
            log('%s: a stationary weapon (not a vehicle one can drive or fly) - not healed' % name)
        return
    z = zone_at(q, r['team'])
    g, st, how = health_calls(v, name, r)
    if g is None:
        tell_once('vh ' + name, '%s: its health cannot be read (%s) - not healed' % (name, how))
        return
    calls(1)
    try:
        hp = float(g())
    except:
        tell_once('vhr ' + name, '%s: reading its health failed (%s): %s' % (name, how, err_text()))
        return
    S['n']['vhp'] = S['n']['vhp'] + 1
    rec = S['vrec'].get(k)
    if rec is None:
        S['vrec'][k] = {'hp': hp, 'low': 0}
        return
    if z is not None and hp < rec['hp'] - 0.5:
        if hp <= KEEP_LOW:
            if hp > 0.0 and not rec['low']:
                rec['low'] = 1
                count('low')
                log('%s (side %s, %s in it) in %s: health %.2f - that low is set by a script (mm_noarmor_v2: 0.01): '
                    'not given back' % (name, r['team'], r['name'], z['name'], hp))
            rec['hp'] = hp
            return
        b = S['borrow'].get(name)
        sold = r['soldier']
        own0 = None
        if b is not None and b[0] == 'read' and sold is not None:
            own0 = read_hp(sold)              # (the first time a soldier's call sets one of this kind: did it set his?)
        calls(1)
        try:
            st(rec['hp'])
        except:
            tell_once('vhs ' + name, '%s: setting its health failed (%s): %s' % (name, how, err_text()))
            rec['hp'] = hp
            return
        if own0 is not None:
            own1 = read_hp(sold)
            if own1 is not None and abs(own1 - own0) > 0.01:
                S['borrow'][name] = ('no', 'it changed the soldier, not the vehicle')
                try:
                    sold.setDamage(own0)
                except:
                    pass
                log("%s: a soldier's setDamage changed HIS SOLDIER (%.0f -> %.0f), not the vehicle - put back; this "
                    "kind is not healed any more this round" % (name, own0, own1))
                return
            S['borrow'][name] = ('ok', '')
        count('vheal')
        log('%s (side %s, %s in it) hurt in %s at %s: health %.0f, back to %.0f (%s)' % (name, r['team'], r['name'],
            z['name'], where(q), hp, rec['hp'], how))
        test_say('%s (%s) hurt in %s: %.0f -> back to %.0f' % (name, r['name'], z['name'], hp, rec['hp']))
        return
    rec['hp'] = hp                            # (repaired, or hurt outside the zone: that is its health now)

# ------------------------------------------------------------------ punishment: killed, the reason in the chat
def kill_soldier(p):
    # a soldier ON FOOT: health 0 = man down (he dies after sv.manDownTime); revived within KEEP_DOWN: put down again.
    # Never for a soldier in a vehicle (baseshield 2.0.6: he stayed alive and froze when he got out)
    if not is_alive(p):
        return 0
    calls(2)
    try:
        s = p.getDefaultVehicle()
        s.setDamage(0.0)
        t = now()
        S['down'][p.index] = (p, t + 1.0, t + KEEP_DOWN)
        return 1
    except:
        log('%s: could not be killed (%s)' % (player_name(p), err_text()))
        return 0

def set_vehicle_hp(v, vname, ra):
    # the punished vehicle's health set to VEH_HP_LEFT (it burns out); what happened, as text
    if not VEH_HP_LEFT:
        return 'its health left (VEH_HP_LEFT 0)'
    g, st, how = health_calls(v, vname, ra)
    if g is None:
        return 'its health could NOT be set: %s' % how
    calls(3)
    try:
        before = float(g())
        st(float(VEH_HP_LEFT))
        after = float(g())
    except:
        S['borrow'][vname] = ('no', 'setting failed: ' + err_text())
        return 'setting its health failed (%s): %s' % (how, err_text())
    S['vread'][obj_key(v)] = g
    return 'health %.0f -> %.0f (%s)' % (before, after, how)

def kill_player(ra, t):
    # 1 when he is killed now: on foot - man down; in a vehicle (or on a gun) - everybody in it as soon as they are on
    # foot, and the vehicle's health VEH_HP_LEFT; 0 when there is nothing to do (already dead / down)
    p = ra['p']
    name = ra['name']
    if not is_alive(p):
        log('%s: already dead - nothing done' % name)
        return 0
    v, s = ride_of(p, 1)
    if v is None:
        if man_down(p):
            log('%s: already man down - nothing done' % name)
            return 0
        if not kill_soldier(p):
            return 0
        S['checks'].append((t + 1.0, [p], None, name, t))
        log('%s: killed (on foot)' % name)
        return 1
    k = obj_key(v)
    vname = tpl(v).lower()
    inside = [p]
    try:
        ai = p.index
    except:
        ai = None
    for q in players():
        try:
            if q.index == ai or not is_alive(q):
                continue
        except:
            continue
        v2, s2 = ride_of(q, 1)
        if v2 is not None and obj_key(v2) == k:
            inside.append(q)
    names = []
    for q in inside:
        names.append(player_name(q))
        try:
            S['pending'][q.index] = (q, player_name(q), t)
        except:
            pass
    text = set_vehicle_hp(v, vname, ra)
    if k is not None:
        S['punished_veh'][k] = 1              # (never healed)
    for n in names:
        S['burning'][n] = t + VEH_GRACE
    log('%s punished in the %s (%s): killed when on foot; %s' % (name, vname, ', '.join(names), text))
    test_say('%s (%s): %s' % (vname, name, text))
    S['checks'].append((t + 1.0, inside, v, name, t))
    S['checks'].append((t + VEH_CHECK, inside, v, name, t))
    return 1

def punish(ra, z, kind, what, other, t):
    # kind 'out' / 'in' / 'wreck'; what: for the log; other: the victim's name, or the vehicle's kind
    name = player_name(ra['p'])
    ra['name'] = name
    if t < S['burning'].get(name, 0.0):
        log('%s %s - just after his vehicle was punished: not counted' % (name, what))
        test_say('%s %s - just punished in his vehicle: not counted' % (name, what))
        return
    last = S['last'].get(name)
    S['last'][name] = t
    if last is not None and t - last < SAME_ATTACK:
        count('same')
        log('%s %s - the same attack (punished once)' % (name, what))
        return
    count(kind)
    log('%s (side %s) %s: punished' % (name, ra['team'], what))
    if not kill_player(ra, t):
        count('nochat')
        return
    base = team_name(z['side'])
    if kind == 'in':
        say(fmt(MSG_IN, (name, other, base)))
    elif kind == 'wreck':
        say(fmt(MSG_WRECK, (name, other, base)))
    else:
        say(fmt(MSG_OUT, (name, other, base)))

def skipped(w):
    low = w.lower()
    for k in SKIP:
        if low.find(k) >= 0:
            return k
    return None

def ev_killed(victim, attacker=None, weapon=None, *rest):
    # PlayerKilled: a soldier of a zone's side killed in it from outside, or killed by an enemy inside the zone
    if not S['on'] or not S['zones']:
        return
    try:
        rv = rec_of(victim)
        if rv is None:
            return
        rv['next'] = 0.0
        if not PUNISH or attacker is None or attacker is victim:
            return
        ra = rec_of(attacker)
        if ra is None or ra['idx'] == rv['idx']:
            return
        vt, at = rv['team'], ra['team']
        if vt is None:
            vt = rv['team'] = team_of(victim)
        if at is None:
            at = ra['team'] = team_of(attacker)
        if vt is None or at is None or vt == at:
            return
        t = now()
        vpos = rv['pos']                      # (where he was last read: every look near his zone; farther away he
        w = ''                                #  cannot have come into it since)
        wn = ''
        try:
            wn = str(weapon.templateName)
            w = ' with ' + wn
        except:
            pass
        apos = place_now(ra)
        vname = player_name(victim)
        zi = None
        if PUNISH_IN:
            zi = zone_at(apos, vt)            # the killer INSIDE a zone of the victim's side
        z = zi
        kind = 'in'
        if z is None:
            z = zone_at(vpos, vt)             # the victim in his side's zone, the killer outside it
            kind = 'out'
        if z is None:
            return
        if kind == 'in':
            what = 'killed %s%s from INSIDE %s (he stood at %s; the victim at %s)' % (vname, w, z['name'],
                (apos and where(apos)) or '?', (vpos and where(vpos)) or '?')
        else:
            what = 'killed %s%s in %s from outside (he stood at %s)' % (vname, w, z['name'], (apos and where(apos))
                or '?')
        sk = skipped(wn)
        if sk:
            count('skip')
            log('%s %s - %s: not counted' % (ra['name'], what, sk))
            test_say('%s killed %s%s in %s - %s: not counted' % (ra['name'], vname, w, z['name'], sk))
            return
        punish(ra, z, kind, what, vname, t)
    except:
        log('PlayerKilled: ' + err_text())

def ev_destroyed(vehicle, attacker=None, *rest):
    # VehicleDestroyed: a vehicle of a zone's side destroyed in it by an enemy from outside
    if not S['on'] or not S['zones']:
        return
    try:
        r = root_of(vehicle)
        k = obj_key(r)
        name = tpl(r).lower()
        own = S['owner'].get(k)
        for d in (S['owner'], S['vrec'], S['punished_veh'], S['vread']):
            if k in d:
                del d[k]
        for rr in P.values():
            if rr['vkey'] is not None and rr['vkey'] == k:
                rr['veh'], rr['vkey'], rr['vname'], rr['next'] = None, None, '', 0.0
        if not PUNISH or not PUNISH_WRECKS or attacker is None or not BUS.is_vehicle(name):
            return                            # (stationary weapons, buildings: not counted; no attacker: the game's)
        try:
            pos = r.getPosition()
        except:
            pos = None
        if own is None:
            z0 = zone_at(pos)
            if z0 is not None:
                own = z0['side']              # (never used: the side of the zone it stands in - its base)
        if not own:
            return
        z = zone_at(pos, own)
        if z is None:
            return
        ra = rec_of(attacker)
        if ra is None:
            return
        at = ra['team']
        if at is None:
            at = ra['team'] = team_of(attacker)
        if at is None or at == own:
            return
        t = now()
        apos = place_now(ra)
        what = 'destroyed a %s (side %s) in %s at %s from outside (he stood at %s)' % (name, own, z['name'],
            (pos and where(pos)) or '?', (apos and where(apos)) or '?')
        if zone_at(apos) is z:
            log('%s destroyed a %s (side %s) in %s from INSIDE it - not punished (vehicles: only from outside)' % (
                ra['name'], name, own, z['name']))
            test_say('%s destroyed a %s from INSIDE %s - not punished' % (ra['name'], name, z['name']))
            return
        punish(ra, z, 'wreck', what, kind_word(name), t)
    except:
        log('VehicleDestroyed: ' + err_text())

# ------------------------------------------------------------------ punished players: killed on foot, kept down
def run_pending(t):
    # a punished crew member: killed as soon as he is on foot; forgotten when dead (or spawned again)
    for idx in list(S['pending'].keys()):
        p, name, t0 = S['pending'][idx]
        if not is_alive(p):
            del S['pending'][idx]
            log('%s: dead (%.1f s after the punishment)' % (name, t - t0))
            continue
        v, s = ride_of(p, 1)
        if v is not None:
            continue
        del S['pending'][idx]
        if man_down(p):
            continue
        kill_soldier(p)
        log('%s is on foot (%.1f s after the punishment): killed' % (name, t - t0))
        test_say('%s is on foot: killed' % name)
        S['checks'].append((t + 1.0, [p], None, name, t))

def run_down(t):
    # a punished soldier who is up again (a medic) within KEEP_DOWN: put down again
    for idx in list(S['down'].keys()):
        p, t1, t2 = S['down'][idx]
        if t > t2 or not is_alive(p):
            del S['down'][idx]
            continue
        if t < t1 or man_down(p):
            continue
        v, s = ride_of(p, 1)
        if v is not None or s is None:
            continue
        hp = read_hp(s)
        if hp is None or hp <= 0.0:
            continue
        try:
            s.setDamage(0.0)
        except:
            continue
        log('%s is up again (health %.0f) - put down again' % (player_name(p), hp))
        test_say('%s is up again (health %.0f): put down again' % (player_name(p), hp))

def vehicle_state(v):
    parts = []
    g = S['vread'].get(obj_key(v))
    if g is not None:
        try:
            parts.append('health %.0f' % float(g()))
        except:
            parts.append('health not read')
    try:
        if v.getIsWreck():
            parts.append('a WRECK')
    except:
        pass
    try:
        parts.append('at (%.0f, %.0f, %.0f)' % tuple(v.getPosition()))
    except:
        parts.append('gone')
    return ' '.join(parts)

def run_checks(t):
    # after a punishment: did it work? (the log; with TEST_CHAT the chat)
    keep = []
    for c in S['checks']:
        if t < c[0]:
            keep.append(c)
            continue
        al = []
        for p in c[1]:
            st = 'dead'
            try:
                again = S['spawned'].get(p.index, -1.0) > c[4]
            except:
                again = 0
            if again:
                st = 'dead (spawned again)'
            elif is_alive(p):
                if man_down(p):
                    st = 'MAN DOWN'
                else:
                    v, s = ride_of(p, 1)
                    st = (v is not None and 'ALIVE in the %s' % tpl(v).lower()) or 'ALIVE on foot'
            al.append('%s %s' % (player_name(p), st))
        vs = ''
        if c[2] is not None:
            vs = '; the vehicle: ' + vehicle_state(c[2])
        log('%.0f s after punishing %s: %s%s' % (t - c[4], c[3], ', '.join(al), vs))
        test_say('check: %s%s' % (', '.join(al), vs))
    S['checks'] = keep

# ------------------------------------------------------------------ chat
def chat_args(low, cmd):
    # the words after cmd in a chat line (the game may put a prefix such as HUD_TEXT_CHAT_TEAM in front)
    i = low.find(cmd)
    return low[i + len(cmd):].replace(',', ' ').split()

def point_of(args):
    # (x, height, z) and a name from '!tp' words, or (None, why)
    if len(args) >= 3:
        try:
            return (float(args[0]), float(args[1]) + 0.5, float(args[2])), '%s %s %s' % (args[0], args[1], args[2])
        except:
            return None, 'three numbers please: x height z (as !pos says)'
    if len(args) == 1:
        if args[0] in S['marks']:
            return S['marks'][args[0]], args[0]
        if args[0] in TP_POINTS:
            return TP_POINTS[args[0]], args[0]
    names = list(TP_POINTS.keys()) + list(S['marks'].keys())
    names.sort()
    return None, 'points: %s, or x height z' % ', '.join(names)

def end_round():
    # as the time limit ends a round (gpm_cq: more tickets wins, equal - nobody), else the next level
    t1 = t2 = 0
    try:
        t1, t2 = bf2.gameLogic.getTickets(1), bf2.gameLogic.getTickets(2)
    except:
        pass
    winner, how = 0, 0
    if t1 > t2:
        winner, how = 1, 3
    elif t2 > t1:
        winner, how = 2, 3
    try:
        host.sgl_endGame(winner, how)
        return 'ended (tickets %s : %s)' % (t1, t2)
    except:
        e = err_text()
        host.rcon_invoke('admin.runNextLevel')
        return 'sgl_endGame failed (%s) - admin.runNextLevel sent' % e

def test_command(p, low, r):
    # 1 if the chat line was one of the test commands
    who = player_name(p)
    if low.find('!help') >= 0:
        say(TAG + ' !pos, !tp us / usedge / usout / mec / mecedge / mecout / mecmg / <mark> / x height z, '
            '!mark <name>, !endround, !baseheal')
        return 1
    if low.find('!endround') >= 0:
        e = end_round()
        log('%s: !endround - %s' % (who, e))
        say('%s %s: round %s' % (TAG, who, e))
        return 1
    if low.find('!mark') >= 0:
        args = chat_args(low, '!mark')
        q = place_now(r)
        if q is None:
            return 1
        name = (args and args[0]) or ('m%d' % (len(S['marks']) + 1))
        S['marks'][name] = (q[0], q[1] + 0.5, q[2])
        log('%s: !mark %s = x %.1f, height %.1f, z %.1f' % (who, name, q[0], q[1], q[2]))
        say('%s %s: point "%s" = x %.1f, height %.1f, z %.1f - "!tp %s" goes there' % (TAG, who, name, q[0], q[1], q[2],
            name))
        return 1
    if low.find('!tp') >= 0:
        pt, name = point_of(chat_args(low, '!tp'))
        if pt is None:
            say('%s %s' % (TAG, name))
            return 1
        v, s = ride_of(p)
        o = v
        if o is None:
            o = s
        what = (v is not None and tpl(v).lower()) or 'soldier'
        try:
            o.setPosition(pt)
        except:
            say('%s %s: the game would not move the %s (%s)' % (TAG, who, what, err_text()))
            return 1
        q = o.getPosition()
        moved = apart(q, pt) < 5.0
        z = zone_at(pt)
        r['next'] = 0.0
        log('%s: !tp %s - %s moved to (%.1f, %.1f, %.1f)%s' % (who, name, what, q[0], q[1], q[2], (not moved and
            ' - NOT where asked (%.1f, %.1f, %.1f)' % pt) or ''))
        say('%s %s (%s) -> %s: x %.0f, z %.0f%s%s' % (TAG, who, what, name, q[0], q[2],
            (z and ' - in ' + z['name']) or ' - not in a zone', (not moved and ' (the game did not move it there)') or ''))
        return 1
    return 0

def ev_chat(playerid, text, channel=None, flags=None, *rest):
    if not S['on']:
        return
    if not CHAT_POS and not TEST_COMMANDS:
        return
    try:
        low = str(text).lower()
        if low.find('!') < 0 or low.find('[baseheal') >= 0 or int(playerid) < 0:
            return                            # (not the server's own lines: player -1)
        p = bf2.playerManager.getPlayerByIndex(playerid)
        if p is None:
            return
        r = rec_of(p)
        if r is None:
            return
        if not is_alive(p) and (low.find('!tp') >= 0 or low.find('!mark') >= 0 or low.find('!pos') >= 0):
            say('[BaseHeal %s] %s: spawn first' % (VERSION, player_name(p)))
            return
        if TEST_COMMANDS and test_command(p, low, r):
            return
        if not CHAT_POS:
            return
        if low.find('!baseheal') >= 0:
            say(status_text())
            return
        if low.find('!pos') < 0:
            return
        pos = place_now(r)
        if pos is None:
            return
        z = zone_at(pos)
        wh = 'not in a protected zone'
        if z is not None:
            wh = 'in %s (protects side %s)' % (z['name'], z['side'] or 'both')
        say('[BaseHeal %s] %s: x %.1f, height %.1f, z %.1f - %s' % (VERSION, player_name(p), pos[0], pos[1], pos[2], wh))
    except:
        log('chat: ' + err_text())

def status_text():
    names = []
    for z in S['zones']:
        names.append('%s (side %s)' % (z['name'], z['side'] or 'both'))
    what = []
    if HEAL:
        what.append('soldiers healed')
    if HEAL_VEHICLES:
        what.append('vehicles with a crew healed')
    if PUNISH:
        what.append('kills in a zone from outside%s%s: killed' % ((PUNISH_IN and ' / by an enemy inside') or '',
            (PUNISH_WRECKS and ' / vehicles destroyed from outside') or ''))
    wh = '%s %s' % (BUS.S['map'] or '?', S['size'] or '(size unknown)')
    none = S.get('znote') or 'no zones on this map'
    return '[BaseHeal %s] %s: %s%s; log %s' % (VERSION, wh, (names and 'zones ' + ', '.join(names)) or none,
                                      (what and '; ' + ', '.join(what)) or '', LOG_FILE or 'off')

# ------------------------------------------------------------------ rounds
def round_start(t):
    P.clear()
    for k in ['owner', 'sold', 'vrec', 'last', 'pending', 'down', 'burning', 'spawned', 'borrow', 'vread',
              'punished_veh', 'stat', 'has']:
        S[k] = {}
    S['checks'], S['order'], S['bfun'] = [], [], None
    S['sync_t'], S['safe_t'], S['safe_i'], S['safe_acc'], S['missed_n'] = -99.0, t, 0, 0.0, 0
    S['n'] = new_counts()
    mp = BUS.S['map'] or ''
    S['size'] = map_size(mp)
    key, note = zone_key(mp, S['size'])
    S['zkey'], S['znote'] = key, note
    if note:
        log(note)
    zones = []
    for line in ZONES.get(key, []):
        z = parse_zone(line)
        if z is not None:
            zones.append(z)
    S['zones'] = zones
    if not zones:
        log('round on %s %s (baseheal %s): no protected zones on this map - idle' % (mp, S['size'] or '(size unknown)',
            VERSION))
        return
    for z in zones:
        if z['side'] == 0:
            S['has'][1], S['has'][2] = 1, 1
        else:
            S['has'][z['side']] = 1
    sync_players(t)
    d = []
    for z in zones:
        d.append('%s (side %s: x %.0f..%.0f, z %.0f..%.0f, height %.0f..%.0f)' % (
            z['name'], z['side'] or 'both', z['x0'], z['x1'], z['z0'], z['z1'], z['h0'], z['h1']))
    log('round on %s %s (baseheal %s): %d zone%s (%s) - %s; %d players' % (mp, S['size'] or '(size unknown)', VERSION,
        len(zones), (len(zones) != 1 and 's') or '', key, '; '.join(d), len(S['order'])))
    if TEST_CHAT:
        say(status_text())

def round_end(t):
    if not S['zones']:
        return
    n = S['n']
    span = max(t - BUS.S['round_t'], 0.001)
    log('round summary: healed - soldiers %d, vehicles %d; punished - kills from outside %d, kills from inside %d, '
        'vehicles destroyed %d (%d of them already dead / down: nothing done); the same attack again %d; not counted '
        '(C4, mines, claymores, artillery) %d; health a script set so low, left %d; events missed %d' % (n['heal'],
        n['vheal'], n['out'], n['in'], n['wreck'], n['nochat'], n['same'], n['skip'], n['low'], n['missed']))
    log('asked of the game this round: ~%d times (%.0f a second) - places read %d (%.1f a second), soldiers\' health '
        '%d, vehicles\' health %d, players checked again %d' % (n['calls'], n['calls'] / span, n['pos'],
        n['pos'] / span, n['hp'], n['vhp'], n['safe']))
    if F is not None:
        log(F.load_line(t))
    S['zones'] = []

# ------------------------------------------------------------------ start
def baseheal_init():
    global F
    S['on'] = 1
    F = BUS.feature('baseheal', 'BaseHeal', LOG_FILE, 'BaseHeal')
    F.log_file = LOG_FILE
    F.maps = 'all'
    F.every = CHECK_EVERY
    F.look = look
    F.round_start = round_start
    F.round_end = round_end
    F.test_chat = TEST_CHAT
    for name, fn in (('PlayerKilled', ev_killed), ('VehicleDestroyed', ev_destroyed), ('PlayerSpawn', ev_spawn),
                     ('PlayerDeath', ev_death), ('PlayerRevived', ev_revived), ('EnterVehicle', ev_enter),
                     ('ExitVehicle', ev_exit), ('PlayerChangeTeams', ev_team), ('PlayerConnect', ev_connect),
                     ('PlayerDisconnect', ev_disconnect)):
        BUS.on_event(name, fn)
    if CHAT_POS or TEST_COMMANDS:
        BUS.on_event('ChatMessage', ev_chat)
    maps = []
    for mp in ZONES.keys():
        maps.append('%s %d' % (mp, len(ZONES[mp])))
    maps.sort()
    log('baseheal %s loaded, on mm_flbus %s (zones: %s; %s%s%s; health of %.0f or lower never given back; no '
        'projectile asked for; places read every look within %.0f m of one\'s own zone, farther as often as needed '
        '(on foot %.0f m/s, ground vehicle %.0f, aircraft %.0f), at least every %.0f s; everybody checked again every '
        '%.0f s%s%s)' % (VERSION, BUS.VERSION, ', '.join(maps) or 'none',
        (HEAL and "own soldiers' health kept") or 'soldiers not healed',
        (HEAL_VEHICLES and '; own vehicles with a crew healed (not empty ones, not stationary weapons)') or '',
        (PUNISH and '; killing in a zone from outside%s%s: killed, the reason in the chat (C4, mines, claymores, '
         'artillery not counted)' % ((PUNISH_IN and ', or an enemy in a zone killing its side') or '',
         (PUNISH_WRECKS and ', or destroying its vehicle there from outside') or '')) or '; nobody punished',
        KEEP_LOW, HEAL_MARGIN, V_FOOT, V_GROUND, V_AIR, MAX_GAP, SAFE_EVERY, (TEST_CHAT and '; TEST_CHAT on') or '',
        (TEST_COMMANDS and '; TEST_COMMANDS on: !tp !mark !endround') or ''))
    BUS.add(F)


# ------------------------------------------------------------------ ModManager interface
# The defaults are the values of the settings above. modmanager.con can override them: mm_baseheal.<NAME> <value>
configDefaults = {}
for _k in ['HEAL', 'HEAL_VEHICLES', 'SOLDIER_NUDGE', 'KEEP_LOW', 'PUNISH', 'PUNISH_IN', 'PUNISH_WRECKS', 'SAME_ATTACK',
           'MSG_OUT', 'MSG_IN', 'MSG_WRECK', 'CHECK_EVERY', 'HEAL_MARGIN', 'V_FOOT', 'V_GROUND', 'V_AIR', 'MAX_GAP',
           'SAFE_EVERY', 'VEH_HP_LEFT', 'VEH_GRACE', 'VEH_CHECK', 'KEEP_DOWN', 'CHAT_POS', 'CHAT_MAX', 'TEST_CHAT',
           'TEST_COMMANDS', 'LOG_FILE']:
    configDefaults[_k] = globals()[_k]

class BaseHeal( object ):

    def __init__( self, modManager ):
        self.mm = modManager
        self.__state = 0

    def init( self ):
        if 0 != self.__state:
            if 2 == self.__state:
                S['on'] = 1           # (handlers stay registered: the engine has no unregisterHandler)
                if F is not None:
                    F.look = look
                self.__state = 1
            return
        cfg = self.mm.getModuleConfig( configDefaults )
        g = globals()
        for k in configDefaults:
            try:
                g[k] = cfg[k]
            except:
                pass
        self.__state = 1
        baseheal_init()
        try:
            self.mm.info( 'baseheal %s is running on mm_flbus (see %s)' % ( VERSION, LOG_FILE or 'no log' ) )
        except:
            pass

    def shutdown( self ):
        self.__state = 2
        S['on'] = 0
        if F is not None:
            F.active = 0
            F.look = None

    def update( self ):
        pass

def mm_load( modManager ):
    return BaseHeal( modManager )
